"""Checks the API code paths without network or keys (mocked responses)."""
import ctranslate2  # noqa: F401
import os, sys
os.chdir(os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, 'src')
import numpy as np, requests
from utils import ConfigManager
ConfigManager.initialize()
import transcription as T

audio = np.zeros(16000 * 2, dtype=np.int16)
cfg = lambda *a: ConfigManager.set_config_value(*a)
cfg(True, 'model_options', 'use_api')

print('cyrillic:', T._to_latin('Љубав, њива, џеп, Ђорђе, ЋУТИ — утакница'))

# ElevenLabs: check the form we send, return Cyrillic text with a known mistake
sent = {}
class R:
    def raise_for_status(self): pass
    def json(self): return {'text': 'Утапница је била добра, кемит.'}
def fake_post(url, headers, data, files, timeout):
    sent.update(url=url, key=headers['xi-api-key'], data=data); return R()
requests.post = fake_post
os.environ['ELEVENLABS_API_KEY'] = 'test-key'
cfg('elevenlabs', 'model_options', 'api', 'provider'); cfg(None, 'model_options', 'api', 'model')
print('elevenlabs:', T.transcribe(audio))
print('  url', sent['url'], '| model', dict(sent['data'])['model_id'], '| lang', dict(sent['data'])['language_code'],
      '| keyterms', sum(1 for k, _ in sent['data'] if k == 'keyterms'))

# Groq without a key -> must fall back to the local model (stubbed)
os.environ.pop('GROQ_API_KEY', None)
cfg('groq', 'model_options', 'api', 'provider')
T.transcribe_local = lambda a, m=None, p=None: 'lokalni tekst'
T._fallback_local_model = lambda: 'stub-model'
print('groq no key:', T.transcribe(audio))
