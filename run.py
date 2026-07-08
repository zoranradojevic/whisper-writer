import os
import sys
import shutil
import subprocess
from dotenv import load_dotenv

print('Starting WhisperWriter...')

for name in ('config.yaml', 'corrections.yaml'):
    target = os.path.join('src', name)
    example = os.path.join('src', f'{name}.example')
    if not os.path.exists(target) and os.path.exists(example):
        shutil.copyfile(example, target)
        print(f'Created {target} from template.')

load_dotenv()
result = subprocess.run([sys.executable, os.path.join('src', 'main.py')])
if result.returncode != 0:
    code = result.returncode & 0xFFFFFFFF
    print(f'WhisperWriter se srusio! Izlazni kod: {result.returncode} (0x{code:08X})')
    if code == 0xC0000005:
        print('Ovo je Windows access violation - verovatno konflikt DLL biblioteka.')
