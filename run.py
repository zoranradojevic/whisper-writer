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
subprocess.run([sys.executable, os.path.join('src', 'main.py')])
