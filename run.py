import os
import sys
import shutil
import subprocess
from dotenv import load_dotenv

print('Starting WhisperWriter...')

cfg = os.path.join('src', 'config.yaml')
example = os.path.join('src', 'config.yaml.example')
if not os.path.exists(cfg) and os.path.exists(example):
    shutil.copyfile(example, cfg)
    print(f'Created {cfg} from template. Edit it to change language, hotkey, or model.')

load_dotenv()
subprocess.run([sys.executable, os.path.join('src', 'main.py')])
