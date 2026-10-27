"""First-time setup and API key entry, run by INSTALIRAJ.bat / PODESI-KLJUCEVE.bat.

    python src/setup_wizard.py install   # configs, local model, desktop shortcut, keys
    python src/setup_wizard.py keys      # only the API keys
"""
import io
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import requests
import soundfile as sf

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(APP_DIR)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ENV_PATH = '.env'
CONFIG_PATH = os.path.join('src', 'config.yaml')
LOCAL_MODEL = 'large-v3-turbo'


def ask_yes_no(question, default=True):
    hint = '[D/n]' if default else '[d/N]'
    answer = input(f'{question} {hint}: ').strip().lower()
    return default if not answer else answer in ('d', 'da', 'y', 'yes')


def copy_example_configs():
    """A fresh download has only the *.example files; without them the app would
    start with English defaults and a weak model."""
    for name in ('config.yaml', 'corrections.yaml'):
        target = os.path.join('src', name)
        if not os.path.exists(target):
            shutil.copy(target + '.example', target)
            print(f'  Napravljen {target} (srpska podešavanja).')


def download_local_model():
    print(f'  Skidam model {LOCAL_MODEL} (~1,6 GB, samo jednom)...')
    from faster_whisper import WhisperModel
    WhisperModel(LOCAL_MODEL, device='cpu', compute_type='int8')
    print('  Model je spreman.')


def create_shortcuts():
    """Desktop shortcuts: the app (silent start) and the corrections file."""
    shortcuts = [
        ('WhisperWriter', 'wscript.exe', f'"{os.path.join(APP_DIR, "WhisperWriter-silent.vbs")}"'),
        ('WhisperWriter ispravke', 'notepad.exe', f'"{os.path.join(APP_DIR, "src", "corrections.yaml")}"'),
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
    print('  Prečice "WhisperWriter" i "WhisperWriter ispravke" su na desktopu.')


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
        return 'ključ nije ispravan ili nema dozvolu "Speech to Text"'
    return None if r.ok else f'greška {r.status_code}: {r.text[:120]}'


def check_groq(key):
    r = requests.get('https://api.groq.com/openai/v1/models',
                     headers={'Authorization': f'Bearer {key}'}, timeout=30)
    if r.status_code == 401:
        return 'ključ nije ispravan'
    return None if r.ok else f'greška {r.status_code}: {r.text[:120]}'


def ask_key(name, prefix, help_lines, check, title=None):
    print(f'\n--- {title or name} ---')
    for line in help_lines:
        print(f'  {line}')
    while True:
        answer = input(f'Nalepi {name} ključ ({prefix}...) ili samo Enter da preskočiš: ')
        # Keys are plain ASCII; pasting can bring quotes, spaces or invisible characters.
        key = ''.join(ch for ch in answer if ch.isascii() and ch.isprintable() and ch not in ' "\'')
        if not key:
            return None
        try:
            problem = check(key)
        except requests.RequestException as e:
            problem = f'nema veze sa serverom ({e.__class__.__name__}) - proveri internet'
        except Exception as e:
            problem = f'neočekivana greška ({e})'
        if not problem:
            print('  ✓ Ključ radi.')
            return key
        print(f'  ✗ {problem}. Pokušaj ponovo.')


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
        text, count = re.subn(rf'^(\s*{key}:).*$', rf'\g<1> {value}', text, count=1, flags=re.M)
        if not count:
            raise RuntimeError(f'{key} not found in {CONFIG_PATH}')
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(text)


def setup_keys():
    print('\nBrzo prepoznavanje preko interneta: tekst stiže za ~2 sekunde i tačniji je.')
    print('Oba servisa su besplatna. NE unosi karticu ni na jednom sajtu - onda ništa ne može da se naplati.')
    elevenlabs = ask_key('ElevenLabs', 'sk_', [
        '1. Napravi nalog na https://elevenlabs.io (može preko Google naloga), plan ostavi Free.',
        '2. Levo dole klikni Developers, pa gore API Keys, pa Create Key.',
        '3. Kod "Speech to Text" izaberi Access, ostalo ostavi No Access. Klikni Create Key i kopiraj ključ.',
    ], check_elevenlabs)
    groq = ask_key('Groq', 'gsk_', [
        '1. Napravi nalog na https://console.groq.com (može preko Google naloga).',
        '2. Levo klikni API Keys, pa Create API Key, upiši ime i kopiraj ključ.',
    ], check_groq, title='Groq (rezerva kad potrošiš besplatne ElevenLabs sate)')

    keys = {k: v for k, v in (('ELEVENLABS_API_KEY', elevenlabs), ('GROQ_API_KEY', groq)) if v}
    if not keys:
        print('\nNijedan ključ nije unet - program radi lokalno, na tvom računaru.')
        return
    write_env(keys)
    main = 'elevenlabs' if elevenlabs else 'groq'
    fallback = 'groq' if elevenlabs and groq else 'null'
    set_config({'use_api': 'true', 'provider': main, 'fallback_provider': fallback})
    print(f'\nGotovo: glavni servis je {main}' + (', rezerva groq' if fallback == 'groq' else '')
          + ', a bez interneta radi lokalni model. Restartuj WhisperWriter ako je bio upaljen.')


def install():
    copy_example_configs()
    print('\nLokalni model radi bez interneta (i kao rezerva kad internet nestane).')
    if ask_yes_no('Skinuti ga sada? (~1,6 GB)'):
        download_local_model()
    if ask_yes_no('Napraviti prečice na desktopu?'):
        create_shortcuts()
    if ask_yes_no('\nPodesiti sada brzo prepoznavanje preko interneta (ElevenLabs/Groq)?'):
        setup_keys()
    print('\nInstalacija je završena. Pokreni WhisperWriter prečicom sa desktopa,'
          ' sačekaj ikonicu pored sata i klikni Start.')
    print('Uputstvo: UPUTSTVO.md u folderu programa.')


if __name__ == '__main__':
    {'install': install, 'keys': setup_keys}[sys.argv[1] if len(sys.argv) > 1 else 'install']()
