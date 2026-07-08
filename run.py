import os
import sys
import shutil
import subprocess
from dotenv import load_dotenv

# Tihi start (--silent iz WhisperWriter-silent.vbs, ili pythonw bez konzole):
# izlaz aplikacije ide u whisperwriter.log umesto u konzolu.
WINDOWLESS = ('--silent' in sys.argv) or (sys.stdout is None)
log_file = open('whisperwriter.log', 'a', encoding='utf-8', errors='replace') if WINDOWLESS else None

print('Starting WhisperWriter...')

for name in ('config.yaml', 'corrections.yaml'):
    target = os.path.join('src', name)
    example = os.path.join('src', f'{name}.example')
    if not os.path.exists(target) and os.path.exists(example):
        shutil.copyfile(example, target)
        print(f'Created {target} from template.')

load_dotenv()
# CREATE_NO_WINDOW: bez toga bi child (console-subsystem python) otvorio novu
# konzolu kada je run.py pokrenut preko pythonw. '-u' da log dobija ispis odmah.
# PYTHONIOENCODING: preusmeren stdout inace koristi cp1252, pa print teksta
# sa nasim slovima (c, s, z...) baca UnicodeEncodeError i ubija transkripciju.
env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
flags = subprocess.CREATE_NO_WINDOW if (WINDOWLESS and os.name == 'nt') else 0
result = subprocess.run([sys.executable, '-u', os.path.join('src', 'main.py')],
                        stdout=log_file, stderr=log_file, creationflags=flags, env=env)
if log_file:
    log_file.close()
if result.returncode != 0:
    code = result.returncode & 0xFFFFFFFF
    message = f'WhisperWriter se srusio! Izlazni kod: {result.returncode} (0x{code:08X})'
    if code == 0xC0000005:
        message += '\nOvo je Windows access violation - verovatno konflikt DLL biblioteka.'
    if WINDOWLESS:
        message += '\nDetalji su u whisperwriter.log u folderu aplikacije.'
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'WhisperWriter', 0x10)
        except Exception:
            pass
    else:
        print(message)
