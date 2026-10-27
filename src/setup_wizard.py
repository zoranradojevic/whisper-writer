"""First-time setup and API key entry, run by INSTALIRAJ.bat / PODESI-KLJUCEVE.bat.

    python src/setup_wizard.py install   # language, configs, local model, shortcuts, keys
    python src/setup_wizard.py keys      # only the API keys

Messages are in Serbian when dictation is Serbian (or Croatian/Bosnian), else English.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import requests
import soundfile as sf
import yaml

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(APP_DIR)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ENV_PATH = '.env'
CONFIG_PATH = os.path.join('src', 'config.yaml')
CORRECTIONS_PATH = os.path.join('src', 'corrections.yaml')
LOCAL_MODEL = 'large-v3-turbo'

# Dictation language menu: (code or None for auto-detect, label, initial prompt).
LANGUAGES = [
    ('sr', 'Srpski', 'Diktiram na srpskom, latinicom, sa pravilnim znakovima interpunkcije.'),
    ('en', 'English', 'Dictation in English, with correct punctuation.'),
    ('de', 'Deutsch', 'Diktat auf Deutsch, mit korrekter Zeichensetzung.'),
    (None, 'Auto (mešano / mixed languages)', ''),
]
SERBIAN_UI = ('sr', 'hr', 'bs')

TEXTS = {
    'sr': {
        'yes_hint': '[D/n]', 'no_hint': '[d/N]',
        'config_created': '  Napravljena su podešavanja (src\\config.yaml, src\\corrections.yaml).',
        'model_intro': '\nLokalni model radi bez interneta (i kao rezerva kad internet nestane).',
        'model_ask': 'Skinuti ga sada? (~1,6 GB)',
        'model_downloading': '  Skidam model {model} (~1,6 GB, samo jednom)...',
        'model_ready': '  Model je spreman.',
        'shortcuts_ask': 'Napraviti prečice na desktopu?',
        'shortcuts_done': '  Prečice "WhisperWriter" i "WhisperWriter ispravke" su na desktopu.',
        'shortcut_fixes': 'WhisperWriter ispravke',
        'keys_ask': '\nPodesiti sada brzo prepoznavanje preko interneta (ElevenLabs/Groq)?',
        'done': '\nInstalacija je završena. Pokreni WhisperWriter prečicom sa desktopa, '
                'sačekaj ikonicu pored sata i klikni Start.\nUputstvo: UPUTSTVO.md u folderu programa.',
        'keys_intro': '\nBrzo prepoznavanje preko interneta: tekst stiže za ~2 sekunde i tačniji je.\n'
                      'Oba servisa su besplatna. NE unosi karticu ni na jednom sajtu - onda ništa ne može da se naplati.',
        'elevenlabs_help': [
            '1. Napravi nalog na https://elevenlabs.io (može preko Google naloga), plan ostavi Free.',
            '2. Levo dole klikni Developers, pa gore API Keys, pa Create Key.',
            '3. Kod "Speech to Text" izaberi Access, ostalo ostavi No Access. Klikni Create Key i kopiraj ključ.',
        ],
        'groq_title': 'Groq (rezerva kad potrošiš besplatne ElevenLabs sate)',
        'groq_help': [
            '1. Napravi nalog na https://console.groq.com (može preko Google naloga).',
            '2. Levo klikni API Keys, pa Create API Key, upiši ime i kopiraj ključ.',
        ],
        'key_ask': 'Nalepi {name} ključ ({prefix}...) ili samo Enter da preskočiš: ',
        'key_ok': '  ✓ Ključ radi.',
        'key_bad': '  ✗ {problem}. Pokušaj ponovo.',
        'key_invalid': 'ključ nije ispravan',
        'key_no_stt': 'ključ nije ispravan ili nema dozvolu "Speech to Text"',
        'key_offline': 'nema veze sa serverom ({error}) - proveri internet',
        'key_unexpected': 'neočekivana greška ({error})',
        'no_keys': '\nNijedan ključ nije unet - program radi lokalno, na tvom računaru.',
        'keys_done': '\nGotovo: glavni servis je {main}{fallback}, a bez interneta radi lokalni model. '
                     'Restartuj WhisperWriter ako je bio upaljen.',
        'fallback_note': ', rezerva groq',
        'language_kept': '  Podešavanja već postoje - zadržavam ih (jezik menjaš u src\\config.yaml: language).',
    },
    'en': {
        'yes_hint': '[Y/n]', 'no_hint': '[y/N]',
        'config_created': '  Settings created (src\\config.yaml, src\\corrections.yaml).',
        'model_intro': '\nThe local model works without internet (and as a backup when the internet is down).',
        'model_ask': 'Download it now? (~1.6 GB)',
        'model_downloading': '  Downloading model {model} (~1.6 GB, only once)...',
        'model_ready': '  The model is ready.',
        'shortcuts_ask': 'Create desktop shortcuts?',
        'shortcuts_done': '  Shortcuts "WhisperWriter" and "WhisperWriter corrections" are on the desktop.',
        'shortcut_fixes': 'WhisperWriter corrections',
        'keys_ask': '\nSet up fast online transcription now (ElevenLabs/Groq)?',
        'done': '\nInstallation finished. Start WhisperWriter from the desktop shortcut, '
                'wait for the icon next to the clock and click Start.\nGuide: README.md in the program folder.',
        'keys_intro': '\nFast online transcription: text arrives in ~2 seconds and is more accurate.\n'
                      'Both services are free. Do NOT add a payment card on either site - then nothing can be charged.',
        'elevenlabs_help': [
            '1. Create an account at https://elevenlabs.io (Google sign-in works), keep the Free plan.',
            '2. Bottom left click Developers, then API Keys at the top, then Create Key.',
            '3. Set "Speech to Text" to Access, leave the rest on No Access. Click Create Key and copy the key.',
        ],
        'groq_title': 'Groq (backup when the free ElevenLabs hours run out)',
        'groq_help': [
            '1. Create an account at https://console.groq.com (Google sign-in works).',
            '2. Click API Keys on the left, then Create API Key, give it a name and copy the key.',
        ],
        'key_ask': 'Paste your {name} key ({prefix}...) or just press Enter to skip: ',
        'key_ok': '  ✓ The key works.',
        'key_bad': '  ✗ {problem}. Try again.',
        'key_invalid': 'the key is not valid',
        'key_no_stt': 'the key is not valid or lacks the "Speech to Text" permission',
        'key_offline': 'cannot reach the server ({error}) - check your internet',
        'key_unexpected': 'unexpected error ({error})',
        'no_keys': '\nNo key entered - the program works locally, on your computer.',
        'keys_done': '\nDone: main service is {main}{fallback}; without internet the local model is used. '
                     'Restart WhisperWriter if it was running.',
        'fallback_note': ', backup groq',
        'language_kept': '  Settings already exist - keeping them (change the language in src\\config.yaml: language).',
    },
}
ui = 'sr'


def t(key, **kwargs):
    text = TEXTS[ui][key]
    return text.format(**kwargs) if kwargs and isinstance(text, str) else text


def configured_language():
    try:
        with open(CONFIG_PATH, encoding='utf-8') as f:
            return (yaml.safe_load(f) or {}).get('model_options', {}).get('common', {}).get('language')
    except (OSError, yaml.YAMLError):
        return None


def set_ui_language(language):
    global ui
    ui = 'sr' if language in SERBIAN_UI else 'en'


def read(prompt):
    """input() without the invisible byte-order mark some consoles and pastes add."""
    return input(prompt).replace('\ufeff', '').strip()


def ask_yes_no(question, default=True):
    answer = read(f'{question} {t("yes_hint") if default else t("no_hint")}: ').lower()
    return default if not answer else answer in ('d', 'da', 'y', 'yes', 'j', 'ja')


def ask_language():
    """Bilingual menu; returns (code or None, initial prompt)."""
    print('\nJezik diktiranja / Dictation language:')
    for number, (_, label, _) in enumerate(LANGUAGES, 1):
        print(f'  {number}. {label}')
    print(f'  {len(LANGUAGES) + 1}. Drugi / Other (fr, it, es, hr, ru, ...)')
    while True:
        answer = read('Izbor / Choice [1]: ') or '1'
        if answer.isdigit() and 1 <= int(answer) <= len(LANGUAGES):
            code, _, prompt = LANGUAGES[int(answer) - 1]
            return code, prompt
        if answer == str(len(LANGUAGES) + 1):
            code = read('Kod jezika / Language code (npr. / e.g. fr): ').lower()
            if re.fullmatch(r'[a-z]{2,3}', code):
                return code, ''
        print('  ?')


def create_configs(language, prompt):
    """A fresh download has only the *.example files; without a config the app would
    start with English defaults and a weak model."""
    shutil.copy(CONFIG_PATH + '.example', CONFIG_PATH)
    serbian = language == 'sr'
    set_config({
        'language': language or 'null',
        'initial_prompt': json.dumps(prompt, ensure_ascii=False) if prompt else 'null',
        # Serbian-only word lists (the app also checks the language).
        'ekavian': 'true' if serbian else 'false',
        'remove_fillers': 'true' if serbian else 'false',
    })
    if not os.path.exists(CORRECTIONS_PATH):
        if language in SERBIAN_UI:
            shutil.copy(CORRECTIONS_PATH + '.example', CORRECTIONS_PATH)
        else:
            with open(CORRECTIONS_PATH, 'w', encoding='utf-8') as f:
                f.write('# Personal corrections: when a word is misheard, add a line\n'
                        '#   wrong: right\n'
                        '# It applies to the next dictation, no restart needed.\n\n'
                        '# _keyterms: names and special terms the online service should expect.\n'
                        '_keyterms:\n  - WhisperWriter\n')
    print(t('config_created'))


def download_local_model():
    print(t('model_downloading', model=LOCAL_MODEL))
    from faster_whisper import WhisperModel
    WhisperModel(LOCAL_MODEL, device='cpu', compute_type='int8')
    print(t('model_ready'))


def create_shortcuts():
    """Desktop shortcuts: the app (silent start) and the corrections file."""
    shortcuts = [
        ('WhisperWriter', 'wscript.exe', f'"{os.path.join(APP_DIR, "WhisperWriter-silent.vbs")}"'),
        (t('shortcut_fixes'), 'notepad.exe', f'"{os.path.join(APP_DIR, CORRECTIONS_PATH)}"'),
    ]
    icon = os.path.join(APP_DIR, 'assets', 'ww-logo.ico')
    for name, target, arguments in shortcuts:
        script = (
            "$d=[Environment]::GetFolderPath('Desktop');"
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\"$d\\{name}.lnk\");"
            f"$s.TargetPath='{target}';$s.Arguments='{arguments}';"
            f"$s.WorkingDirectory='{APP_DIR}';$s.IconLocation='{icon}';$s.Save()"
        )
        subprocess.run(['powershell', '-NoProfile', '-Command', script], check=True)
    print(t('shortcuts_done'))


def _silence_wav():
    buffer = io.BytesIO()
    sf.write(buffer, np.zeros(8000, dtype=np.int16), 16000, format='wav')
    return buffer.getvalue()


def check_elevenlabs(key):
    """Half a second of silence: proves the key works and may use Speech to Text."""
    r = requests.post('https://api.elevenlabs.io/v1/speech-to-text', headers={'xi-api-key': key},
                      data={'model_id': 'scribe_v2'}, files={'file': ('t.wav', _silence_wav(), 'audio/wav')},
                      timeout=30)
    if r.status_code == 401:
        return t('key_no_stt')
    return None if r.ok else f'{r.status_code}: {r.text[:120]}'


def check_groq(key):
    r = requests.get('https://api.groq.com/openai/v1/models',
                     headers={'Authorization': f'Bearer {key}'}, timeout=30)
    if r.status_code == 401:
        return t('key_invalid')
    return None if r.ok else f'{r.status_code}: {r.text[:120]}'


def ask_key(name, prefix, help_lines, check, title=None):
    print(f'\n--- {title or name} ---')
    for line in help_lines:
        print(f'  {line}')
    while True:
        answer = read(t('key_ask', name=name, prefix=prefix))
        # Keys are plain ASCII; pasting can bring quotes, spaces or invisible characters.
        key = ''.join(ch for ch in answer if ch.isascii() and ch.isprintable() and ch not in ' "\'')
        if not key:
            return None
        try:
            problem = check(key)
        except requests.RequestException as e:
            problem = t('key_offline', error=e.__class__.__name__)
        except Exception as e:
            problem = t('key_unexpected', error=e)
        if not problem:
            print(t('key_ok'))
            return key
        print(t('key_bad', problem=problem))


def write_env(values):
    """Set keys in .env, keeping any other lines."""
    lines = open(ENV_PATH, encoding='utf-8').read().splitlines() if os.path.exists(ENV_PATH) else []
    for name, value in values.items():
        lines = [l for l in lines if not l.startswith(f'{name}=')] + [f'{name}={value}']
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def set_config(settings):
    """Change single `key: value` lines in config.yaml, keeping its comments."""
    text = open(CONFIG_PATH, encoding='utf-8').read()
    for key, value in settings.items():
        text, count = re.subn(rf'^(\s*{key}:).*$', lambda m: f'{m.group(1)} {value}', text,
                              count=1, flags=re.M)
        if not count:
            raise RuntimeError(f'{key} not found in {CONFIG_PATH}')
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(text)


def setup_keys():
    print(t('keys_intro'))
    elevenlabs = ask_key('ElevenLabs', 'sk_', t('elevenlabs_help'), check_elevenlabs)
    groq = ask_key('Groq', 'gsk_', t('groq_help'), check_groq, title=t('groq_title'))

    keys = {k: v for k, v in (('ELEVENLABS_API_KEY', elevenlabs), ('GROQ_API_KEY', groq)) if v}
    if not keys:
        print(t('no_keys'))
        return
    write_env(keys)
    main = 'elevenlabs' if elevenlabs else 'groq'
    fallback = 'groq' if elevenlabs and groq else 'null'
    set_config({'use_api': 'true', 'provider': main, 'fallback_provider': fallback})
    print(t('keys_done', main=main, fallback=t('fallback_note') if fallback == 'groq' else ''))


def install():
    if os.path.exists(CONFIG_PATH):
        set_ui_language(configured_language())
        print(t('language_kept'))
    else:
        language, prompt = ask_language()
        set_ui_language(language)
        create_configs(language, prompt)
    print(t('model_intro'))
    if ask_yes_no(t('model_ask')):
        download_local_model()
    if ask_yes_no(t('shortcuts_ask')):
        create_shortcuts()
    if ask_yes_no(t('keys_ask')):
        setup_keys()
    print(t('done'))


def keys():
    set_ui_language(configured_language())
    setup_keys()


if __name__ == '__main__':
    {'install': install, 'keys': keys}[sys.argv[1] if len(sys.argv) > 1 else 'install']()
