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

    Returns (corrections, hotwords). The optional `_hotwords` list holds the rare
    terms Whisper should be biased towards while listening; everything else is a
    plain wrong -> right substitution applied after transcription. Common words
    must stay out of the hotword list — biasing towards them costs accuracy.
    """
    path = os.path.join('src', 'corrections.yaml')
    if not os.path.exists(path):
        return {}, []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        hotwords = [str(w) for w in (data.pop('_hotwords', None) or []) if w]
        corrections = {str(k): str(v) for k, v in data.items() if k and v}
        return corrections, hotwords
    except Exception as e:
        ConfigManager.console_print(f'Could not load corrections.yaml: {e}')
        return {}, []


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

    corrections, hotword_list = _load_corrections()
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

def transcribe_api(audio_data, previous_text=None):
    """
    Transcribe an audio file using the OpenAI API.
    """
    model_options = ConfigManager.get_config_section('model_options')
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY') or None,
        base_url=model_options['api']['base_url'] or 'https://api.openai.com/v1'
    )

    # Convert numpy array to WAV file
    byte_io = io.BytesIO()
    sample_rate = ConfigManager.get_config_section('recording_options').get('sample_rate') or 16000
    sf.write(byte_io, audio_data, sample_rate, format='wav')
    byte_io.seek(0)

    response = client.audio.transcriptions.create(
        model=model_options['api']['model'],
        file=('audio.wav', byte_io, 'audio/wav'),
        language=model_options['common']['language'],
        prompt=_build_prompt(previous_text),
        temperature=model_options['common']['temperature'],
    )
    return response.text

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


def post_process_transcription(transcription):
    """
    Apply post-processing to the transcription.
    """
    post_processing = ConfigManager.get_config_section('post_processing')
    if post_processing.get('remove_fillers'):
        transcription = _remove_fillers(transcription)
    transcription = transcription.strip()
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

    if ConfigManager.get_config_value('model_options', 'use_api'):
        return transcribe_api(audio_data, previous_text)
    return transcribe_local(audio_data, local_model, previous_text)

def transcribe(audio_data, local_model=None):
    """
    Transcribe audio date using the OpenAI API or a local model, depending on config.
    """
    return post_process_transcription(transcribe_raw(audio_data, local_model))

