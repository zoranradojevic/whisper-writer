import os
os.environ["TQDM_DISABLE"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from tqdm import tqdm as _tqdm
_tqdm.monitor_interval = 0
import io
import re
import yaml
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from openai import OpenAI

from utils import ConfigManager


def _load_corrections():
    """Load user's personal corrections from src/corrections.yaml.

    Returns (corrections, hotwords, keyterms). The optional `_hotwords` list holds the
    rare terms Whisper should be biased towards while listening; everything else is a
    plain wrong -> right substitution applied after transcription. Common words
    must stay out of the hotword list — biasing towards them costs accuracy.
    `_keyterms` are extra terms only for cloud models that take a term list
    (ElevenLabs), where common domain words like "utakmica" do help.
    """
    path = os.path.join('src', 'corrections.yaml')
    if not os.path.exists(path):
        return {}, [], []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        hotwords = [str(w) for w in (data.pop('_hotwords', None) or []) if w]
        keyterms = [str(w) for w in (data.pop('_keyterms', None) or []) if w]
        corrections = {str(k): str(v) for k, v in data.items() if k and v}
        return corrections, hotwords, keyterms
    except Exception as e:
        ConfigManager.console_print(f'Could not load corrections.yaml: {e}')
        return {}, [], []


def _apply_corrections(text, corrections):
    """Replace each key with its value, case-insensitive, whole-word match."""
    if not corrections or not text:
        return text
    for wrong, right in corrections.items():
        pattern = r'\b' + re.escape(wrong) + r'\b'
        # Keep a capital first letter (start of sentence) when the match had one.
        text = re.sub(pattern,
                      lambda m: right[:1].upper() + right[1:] if m.group(0)[:1].isupper() else right,
                      text, flags=re.IGNORECASE)
    return text

def create_local_model():
    """
    Create a local model using the faster-whisper library.
    """
    ConfigManager.console_print('Creating local model...')
    local_model_options = ConfigManager.get_config_section('model_options')['local']
    compute_type = local_model_options['compute_type']
    model_path = local_model_options.get('model_path')
    # 0 = all physical cores (faster-whisper alone would use only 4).
    cpu_threads = local_model_options.get('cpu_threads') or max(1, (os.cpu_count() or 8) // 2)

    if compute_type == 'int8':
        device = 'cpu'
        ConfigManager.console_print('Using int8 quantization, forcing CPU usage.')
    else:
        device = local_model_options['device']

    try:
        if model_path:
            ConfigManager.console_print(f'Loading model from: {model_path}')
            model = WhisperModel(model_path,
                                 device=device,
                                 compute_type=compute_type,
                                 cpu_threads=cpu_threads,
                                 download_root=None)  # Prevent automatic download
        else:
            model = WhisperModel(local_model_options['model'],
                                 device=device,
                                 compute_type=compute_type,
                                 cpu_threads=cpu_threads)
    except Exception as e:
        ConfigManager.console_print(f'Error initializing WhisperModel: {e}')
        ConfigManager.console_print('Falling back to CPU.')
        model = WhisperModel(model_path or local_model_options['model'],
                             device='cpu',
                             compute_type=compute_type,
                             cpu_threads=cpu_threads,
                             download_root=None if model_path else None)

    ConfigManager.console_print('Local model created.')
    return model

# Whisper keeps only the last ~223 prompt tokens. The initial prompt takes ~165,
# so the tail of the previous chunk must stay short (Serbian is ~2.3 chars/token).
_PREVIOUS_TEXT_CHARS = 120


def _build_prompt(previous_text=None):
    """Initial prompt, followed by the end of the previous chunk for context."""
    prompt = ConfigManager.get_config_section('model_options')['common']['initial_prompt'] or ''
    if previous_text:
        tail = previous_text.strip()
        if len(tail) > _PREVIOUS_TEXT_CHARS:
            tail = tail[-_PREVIOUS_TEXT_CHARS:]
            tail = tail[tail.find(' ') + 1:]  # don't start mid-word
        prompt = f'{prompt} {tail}'.strip()
    return prompt or None


def transcribe_local(audio_data, local_model=None, previous_text=None):
    """
    Transcribe an audio file using a local model.
    """
    if not local_model:
        local_model = create_local_model()
    model_options = ConfigManager.get_config_section('model_options')

    # Convert int16 to float32
    audio_data_float = audio_data.astype(np.float32) / 32768.0

    corrections, hotword_list, _ = _load_corrections()
    hotwords = ' '.join(hotword_list) if hotword_list else None

    response = local_model.transcribe(audio=audio_data_float,
                                      language=model_options['common']['language'],
                                      initial_prompt=_build_prompt(previous_text),
                                      condition_on_previous_text=model_options['local']['condition_on_previous_text'],
                                      temperature=model_options['common']['temperature'],
                                      vad_filter=model_options['local']['vad_filter'],
                                      hotwords=hotwords,)
    text = ''.join([segment.text for segment in list(response[0])])
    return _apply_corrections(text, corrections)

# provider: (base URL, environment variable with the key in .env, default model)
API_PROVIDERS = {
    'groq': ('https://api.groq.com/openai/v1', 'GROQ_API_KEY', 'whisper-large-v3'),
    'openai': ('https://api.openai.com/v1', 'OPENAI_API_KEY', 'gpt-4o-transcribe'),
    'elevenlabs': ('https://api.elevenlabs.io/v1', 'ELEVENLABS_API_KEY', 'scribe_v2'),
}
_API_TIMEOUT_SECONDS = 30

_CYRILLIC_TO_LATIN = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Ђ': 'Đ', 'Е': 'E', 'Ж': 'Ž', 'З': 'Z',
    'И': 'I', 'Ј': 'J', 'К': 'K', 'Л': 'L', 'Љ': 'Lj', 'М': 'M', 'Н': 'N', 'Њ': 'Nj', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'Ћ': 'Ć', 'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'C',
    'Ч': 'Č', 'Џ': 'Dž', 'Ш': 'Š',
}
_CYRILLIC_TO_LATIN.update({c.lower(): l.lower() for c, l in list(_CYRILLIC_TO_LATIN.items())})
_CYRILLIC_TABLE = str.maketrans(_CYRILLIC_TO_LATIN)


def _to_latin(text):
    """Serbian Cyrillic -> Latin. Cloud models often answer in Cyrillic for 'sr'."""
    return text.translate(_CYRILLIC_TABLE)


def _api_providers():
    """Providers to try in order: the main one, then the optional fallback."""
    api = ConfigManager.get_config_section('model_options')['api']
    providers = [(api.get('provider') or 'openai').lower()]
    fallback = (api.get('fallback_provider') or '').lower()
    if fallback and fallback not in providers:
        providers.append(fallback)
    return providers


def _api_settings(provider):
    api = ConfigManager.get_config_section('model_options')['api']
    default_url, key_variable, default_model = API_PROVIDERS[provider]
    is_main = provider == (api.get('provider') or 'openai').lower()
    # A custom base_url only makes sense for OpenAI-compatible local servers.
    base_url = (api.get('base_url') if provider == 'openai' else None) or default_url
    api_key = os.getenv(key_variable) or (api.get('api_key') if is_main else None)
    if not api_key:
        raise RuntimeError(f'No API key: add {key_variable}=... to the .env file')
    # The configured model belongs to the main provider; the fallback uses its default.
    model = (api.get('model') if is_main else None) or default_model
    return base_url, api_key, model


def _wav_bytes(audio_data):
    byte_io = io.BytesIO()
    sample_rate = ConfigManager.get_config_section('recording_options').get('sample_rate') or 16000
    sf.write(byte_io, audio_data, sample_rate, format='wav')
    return byte_io.getvalue()


def _transcribe_elevenlabs(wav, base_url, api_key, model, language, keyterms):
    # requests is only needed for this provider; imported here to keep startup lean.
    import requests
    form = [('model_id', model), ('tag_audio_events', 'false'), ('timestamps_granularity', 'none')]
    if language:
        form.append(('language_code', language))
    # Keyterms cost +20% but are the only way to bias Scribe (it takes no prompt).
    form += [('keyterms', term) for term in keyterms[:100]]
    response = requests.post(f'{base_url}/speech-to-text', headers={'xi-api-key': api_key},
                             data=form, files={'file': ('audio.wav', wav, 'audio/wav')},
                             timeout=_API_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get('text', '')


def transcribe_api(audio_data, previous_text=None, provider=None):
    """
    Transcribe audio with a cloud API (Groq, OpenAI or ElevenLabs, see API_PROVIDERS).
    """
    model_options = ConfigManager.get_config_section('model_options')
    language = model_options['common']['language']
    provider = provider or _api_providers()[0]
    base_url, api_key, model = _api_settings(provider)
    corrections, hotwords, keyterms = _load_corrections()
    wav = _wav_bytes(audio_data)

    if provider == 'elevenlabs':
        text = _transcribe_elevenlabs(wav, base_url, api_key, model, language, hotwords + keyterms)
    else:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=_API_TIMEOUT_SECONDS, max_retries=1)
        response = client.audio.transcriptions.create(
            model=model,
            file=('audio.wav', wav, 'audio/wav'),
            language=language,
            prompt=_build_prompt(previous_text),
            temperature=model_options['common']['temperature'],
        )
        text = response.text

    if language == 'sr':
        text = _to_latin(text)
    return _apply_corrections(text, corrections)

# Serbian filler words. Most of them are also real words ("ovaj trening", "to znači da"),
# so they are removed only when they stand alone: between commas or at the start
# of a sentence followed by a comma. Pure hesitation sounds go everywhere.
_FILLERS = r'(?:ovaj|ovaj ovaj|znači|kako se zove|kak se zove|kak zove|ono|e)'
_FILLER_INSIDE = re.compile(r',\s*' + _FILLERS + r'(?=\s*[,.!?…])', re.IGNORECASE)
_FILLER_START = re.compile(r'(^|[.!?…]\s+)' + _FILLERS + r'\s*,\s*(\w?)', re.IGNORECASE)
_HESITATION = re.compile(r'\b(?:e{2,}|a{2,}|m{2,}|hm+|mhm|eh)\b[,.]?\s*', re.IGNORECASE)


def _remove_fillers(text):
    previous = None
    while previous != text:  # fillers can repeat: "ovaj, znači, ovaj,"
        previous = text
        text = _HESITATION.sub('', text)
        text = _FILLER_INSIDE.sub('', text)
        # The word after a removed sentence-start filler now starts the sentence.
        text = _FILLER_START.sub(lambda m: m.group(1) + m.group(2).upper(), text)
    text = re.sub(r'\s+([,.!?])', r'\1', text)
    text = re.sub(r',\s*([,.!?])', r'\1', text)
    return re.sub(r'\s{2,}', ' ', text).strip()


# Ijekavian -> ekavian. Cloud models (and sometimes Whisper) write "vježbe, dio, poslije".
# A general "ije/je -> e" rule would wreck correct words (nije, akcije, pozicije, objekat),
# so this is a list of known word stems; a stem also matches with prefixes and endings
# (podijeliti, provjeriti, zagrijavanje). Order matters: longer stems first.
_EKAVIAN_WORDS = {  # whole words only
    'prije': 'pre', 'poslije': 'posle', 'poslijepodne': 'popodne', 'dvije': 'dve',
    'dio': 'deo', 'dijete': 'dete', 'cijeli': 'ceo',
    # "smije" is left alone: it is both "sme" (may) and "smeje" (laughs).
    # past tense of -jeti verbs: htio -> hteo
    'htio': 'hteo', 'vidio': 'video', 'želio': 'želeo', 'volio': 'voleo', 'živio': 'živeo',
    'razumio': 'razumeo', 'sjedio': 'sedeo', 'letio': 'leteo',
}
_EKAVIAN_STEMS = [
    ('zagrijavanj', 'zagrevanj'), ('zagrijava', 'zagreva'), ('zagrij', 'zagrej'),
    ('vježb', 'vežb'), ('mješ', 'meš'), ('mjes', 'mes'), ('vrijem', 'vrem'),
    ('djevoj', 'devoj'), ('djec', 'dec'), ('djet', 'det'),
    ('dijel', 'del'), ('djel', 'del'), ('tijel', 'tel'), ('tjel', 'tel'), ('ljel', 'lel'),
    ('cijel', 'cel'), ('cjel', 'cel'), ('cijen', 'cen'), ('cjen', 'cen'),
    ('lijep', 'lep'), ('ljep', 'lep'), ('bijel', 'bel'), ('riječ', 'reč'),
    ('riješ', 'reš'), ('rješ', 'reš'), ('vjer', 'ver'), ('mjer', 'mer'),
    ('mijenj', 'menj'), ('mjen', 'men'), ('sjet', 'set'), ('sjeć', 'seć'),
    ('sjever', 'sever'), ('sjed', 'sed'), ('sedje', 'sede'),
    ('pjesm', 'pesm'), ('pjev', 'pev'), ('pijes', 'pes'),
    ('lijev', 'lev'), ('lijek', 'lek'), ('uvijek', 'uvek'), ('čovjek', 'čovek'),
    ('svjež', 'svež'), ('bjež', 'bež'), ('bjeg', 'beg'), ('pobijed', 'pobed'), ('pobjed', 'pobed'),
    ('svijet', 'svet'), ('cvijet', 'cvet'), ('vjet', 'vet'), ('snijeg', 'sneg'),
    ('mlijek', 'mlek'), ('vijest', 'vest'), ('stoljeć', 'stoleć'), ('zvijezd', 'zvezd'),
    ('ljet', 'let'), ('sljede', 'slede'), ('slijed', 'sled'), ('srijed', 'sred'),
    ('odjeć', 'odeć'), ('griješ', 'greš'), ('grješ', 'greš'), ('bilješ', 'beleš'),
    ('uspje', 'uspe'), ('vidje', 'vide'), ('htje', 'hte'), ('razumje', 'razume'),
    ('živje', 'žive'), ('letje', 'lete'), ('željet', 'želet'), ('željel', 'želel'),
    ('željeo', 'želeo'), ('voljet', 'volet'), ('voljel', 'volel'), ('voljeo', 'voleo'),
    ('dje\\b', 'de'),  # gdje, ovdje, negdje, nigdje...
]
_EKAVIAN_RULES = (
    [(re.compile(r'\b' + w + r'\b', re.IGNORECASE), e) for w, e in _EKAVIAN_WORDS.items()]
    + [(re.compile(stem if stem.endswith('\\b') else stem, re.IGNORECASE), e)
       for stem, e in _EKAVIAN_STEMS]
)


def _to_ekavian(text):
    def keep_case(replacement):
        return lambda m: replacement[:1].upper() + replacement[1:] if m.group(0)[:1].isupper() else replacement
    for pattern, replacement in _EKAVIAN_RULES:
        text = pattern.sub(keep_case(replacement), text)
    return text


def post_process_transcription(transcription):
    """
    Apply post-processing to the transcription.
    """
    post_processing = ConfigManager.get_config_section('post_processing')
    if post_processing.get('ekavian'):
        transcription = _to_ekavian(transcription)
    if post_processing.get('remove_fillers'):
        transcription = _remove_fillers(transcription)
    transcription = transcription.strip()
    # Some cloud models leave the last sentence without a period.
    if transcription and transcription[-1].isalnum():
        transcription += '.'
    if post_processing['remove_trailing_period'] and transcription.endswith('.'):
        transcription = transcription[:-1]
    if post_processing['add_trailing_space']:
        transcription += ' '
    if post_processing['remove_capitalization']:
        transcription = transcription.lower()

    return transcription

def transcribe_raw(audio_data, local_model=None, previous_text=None):
    """
    Transcribe one piece of audio without post-processing. `previous_text` is what was
    transcribed just before it (when a long dictation is split into chunks).
    """
    if audio_data is None or len(audio_data) == 0:
        return ''

    global last_source
    if ConfigManager.get_config_value('model_options', 'use_api'):
        for provider in _api_providers():
            try:
                text = transcribe_api(audio_data, previous_text, provider)
                last_source = provider
                return text
            except Exception as e:
                # No internet, bad key, free quota used up... dictation must still work.
                ConfigManager.console_print(f'{provider} failed ({e}); trying the next option.')
        local_model = local_model or _fallback_local_model()
    last_source = 'local'
    return transcribe_local(audio_data, local_model, previous_text)


# Which service transcribed the last chunk ('elevenlabs', 'groq', 'local'...), for stats.
last_source = None


_fallback_model = None


def _fallback_local_model():
    """Local model for when the API fails; loaded on first use (takes a few seconds)."""
    global _fallback_model
    if _fallback_model is None:
        _fallback_model = create_local_model()
    return _fallback_model

def transcribe(audio_data, local_model=None):
    """
    Transcribe audio date using the OpenAI API or a local model, depending on config.
    """
    return post_process_transcription(transcribe_raw(audio_data, local_model))

