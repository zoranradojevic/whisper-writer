"""Compare cloud providers on real recordings: speed + text side by side.

Usage:  .venv\\Scripts\\python.exe api-test\\compare.py groq elevenlabs [openai]
Keys come from .env (GROQ_API_KEY, ELEVENLABS_API_KEY, OPENAI_API_KEY).
Each recording is api-test\\*.wav; a matching *.local-turbo.txt is shown for reference.
"""
import ctranslate2  # noqa: F401
import glob, io, os, sys, time
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, 'src')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
import soundfile as sf
from utils import ConfigManager
ConfigManager.initialize()
import transcription as T

# Variants to try; (provider, model). Empty model = provider default.
VARIANTS = {
    'groq': [('groq', 'whisper-large-v3'), ('groq', 'whisper-large-v3-turbo')],
    'elevenlabs': [('elevenlabs', 'scribe_v2')],
    'openai': [('openai', 'gpt-4o-transcribe'), ('openai', 'gpt-4o-mini-transcribe')],
}

ConfigManager.set_config_value(True, 'model_options', 'use_api')
for wav in sorted(glob.glob('api-test/*.wav')):
    audio, sr = sf.read(wav, dtype='int16')
    print(f'\n######## {os.path.basename(wav)} ({len(audio)/sr:.0f} s)')
    ref = wav.replace('.wav', '.local-turbo.txt')
    if os.path.exists(ref):
        print(f'[lokalni turbo]\n{open(ref, encoding="utf-8").read().strip()}')
    for name in sys.argv[1:]:
        for provider, model in VARIANTS[name]:
            ConfigManager.set_config_value(provider, 'model_options', 'api', 'provider')
            ConfigManager.set_config_value(model, 'model_options', 'api', 'model')
            t = time.time()
            try:
                text = T.post_process_transcription(T.transcribe_api(audio))
            except Exception as e:
                text = f'GREŠKA: {e}'
            print(f'\n[{provider} {model}] {time.time() - t:.1f} s\n{text.strip()}', flush=True)
