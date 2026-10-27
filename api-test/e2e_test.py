"""End-to-end check of the real recording pipeline with the current config:
feeds a wav in real time through a fake microphone, then tests the fallback chain."""
import ctranslate2  # noqa: F401
import io, os, sys, threading, time
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, 'src')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
import numpy as np, soundfile as sf
from utils import ConfigManager
ConfigManager.initialize()
ConfigManager.console_print = staticmethod(lambda m: print(m, flush=True))
ConfigManager.set_config_value('press_to_toggle', 'recording_options', 'recording_mode')
import result_thread as rt
import transcription as T

rt.USAGE_STATS_PATH = 'api-test/usage_stats_test.csv'  # keep real stats clean
audio, sr = sf.read(sys.argv[1], dtype='int16')

class FakeStream:
    def __init__(self, samplerate, channels, dtype, blocksize, device, callback):
        self.cb, self.bs = callback, blocksize
    def __enter__(self):
        def feed():
            for i in range(0, len(audio) - self.bs, self.bs):
                self.cb(audio[i:i + self.bs].reshape(-1, 1), self.bs, None, None)
                time.sleep(self.bs / sr)
            thread.stop_recording()
            self.cb(np.zeros((self.bs, 1), dtype=np.int16), self.bs, None, None)
        threading.Thread(target=feed, daemon=True).start()
        return self
    def __exit__(self, *a):
        pass

rt.sd.InputStream = FakeStream
thread = rt.ResultThread(None)
thread.is_recording = True
thread.run()
print('stats row:', open(rt.USAGE_STATS_PATH, encoding='utf-8').read().splitlines()[-1])

print('\n--- fallback: broken ElevenLabs key -> Groq')
good = os.environ['ELEVENLABS_API_KEY']
os.environ['ELEVENLABS_API_KEY'] = 'sk_invalid'
clip = audio[:sr * 12]
print(T.transcribe_raw(clip), '| source:', T.last_source)
print('\n--- fallback: both broken -> local model')
os.environ['GROQ_API_KEY'] = 'gsk_invalid'
print(T.transcribe_raw(clip), '| source:', T.last_source)
os.environ['ELEVENLABS_API_KEY'] = good
