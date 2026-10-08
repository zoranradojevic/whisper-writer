import queue
import threading
import time
import traceback
import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad
from PyQt5.QtCore import QThread, QMutex, pyqtSignal
from collections import deque
from threading import Event

from transcription import transcribe_raw, post_process_transcription
from utils import ConfigManager

# Long dictations are transcribed in chunks while the user is still speaking, so after
# the stop only the last chunk is left. Chunks are cut in pauses, never mid-word.
# Whisper always encodes a 30 s window, so chunks close to that size waste nothing.
CHUNK_MIN_SECONDS = 15   # start looking for a pause after this much audio
CHUNK_MAX_SECONDS = 28   # cut here even without a proper pause
CHUNK_PAUSE_MS = 300     # silence this long counts as a pause

# The last recording is kept here (overwritten every time) for testing models on it.
LAST_RECORDING_PATH = 'last_recording.wav'


class ChunkTranscriber:
    """Transcribes audio chunks one after another on a background thread."""

    def __init__(self, local_model):
        self.local_model = local_model
        self.queue = queue.Queue()
        self.texts = []
        self.error = None
        self.chunk_count = 0
        self.thread = threading.Thread(target=self._work, daemon=True)
        self.thread.start()

    def submit(self, audio_data):
        self.chunk_count += 1
        self.queue.put(audio_data)

    def finish(self):
        """Wait for all submitted chunks and return the joined raw text."""
        self.queue.put(None)
        self.thread.join()
        if self.error:
            raise self.error
        return ' '.join(t.strip() for t in self.texts if t.strip())

    def cancel(self):
        self.queue.put(None)

    def _work(self):
        while True:
            audio_data = self.queue.get()
            if audio_data is None:
                return
            if self.error:
                continue
            try:
                previous_text = ' '.join(self.texts)
                self.texts.append(transcribe_raw(audio_data, self.local_model, previous_text))
            except Exception as e:
                self.error = e


class ResultThread(QThread):
    """
    A thread class for handling audio recording, transcription, and result processing.

    This class manages the entire process of:
    1. Recording audio from the microphone
    2. Detecting speech and silence
    3. Saving the recorded audio as numpy array
    4. Transcribing the audio
    5. Emitting the transcription result

    Signals:
        statusSignal: Emits the current status of the thread (e.g., 'recording', 'transcribing', 'idle')
        resultSignal: Emits the transcription result
    """

    statusSignal = pyqtSignal(str)
    resultSignal = pyqtSignal(str)

    def __init__(self, local_model=None):
        """
        Initialize the ResultThread.

        :param local_model: Local transcription model (if applicable)
        """
        super().__init__()
        self.local_model = local_model
        self.is_recording = False
        self.is_running = True
        self.sample_rate = None
        self.mutex = QMutex()

    def stop_recording(self):
        """Stop the current recording session."""
        self.mutex.lock()
        self.is_recording = False
        self.mutex.unlock()

    def stop(self):
        """Stop the entire thread execution."""
        self.mutex.lock()
        self.is_running = False
        self.mutex.unlock()
        self.statusSignal.emit('idle')
        self.wait()

    def run(self):
        """Main execution method for the thread."""
        try:
            if not self.is_running:
                return

            self.mutex.lock()
            self.is_recording = True
            self.mutex.unlock()

            self.statusSignal.emit('recording')
            ConfigManager.console_print('Recording...')
            transcriber = ChunkTranscriber(self.local_model)
            audio_data = self._record_audio(transcriber)

            if not self.is_running:
                transcriber.cancel()
                return

            if audio_data is None:
                transcriber.cancel()
                self.statusSignal.emit('idle')
                return

            self.statusSignal.emit('transcribing')
            ConfigManager.console_print('Transcribing...')

            # Measured from the stop: that is how long the user actually waits.
            start_time = time.time()
            result = post_process_transcription(transcriber.finish())
            end_time = time.time()
            if transcriber.chunk_count > 1:
                ConfigManager.console_print(f'Transcribed in {transcriber.chunk_count} chunks while recording.')

            transcription_time = end_time - start_time
            audio_duration = len(audio_data) / self.sample_rate if self.sample_rate else 0
            if audio_duration > 0:
                rtf = transcription_time / audio_duration
                speedup = 1 / rtf if rtf > 0 else 0
                ConfigManager.console_print(
                    f'Transcription completed in {transcription_time:.2f}s '
                    f'(audio: {audio_duration:.2f}s, RTF: {rtf:.2f}, '
                    f'{speedup:.1f}x realtime). Post-processed line: {result}'
                )
            else:
                ConfigManager.console_print(f'Transcription completed in {transcription_time:.2f} seconds. Post-processed line: {result}')

            if not self.is_running:
                return

            self.statusSignal.emit('idle')
            self.resultSignal.emit(result)

        except Exception as e:
            traceback.print_exc()
            self.statusSignal.emit('error')
            self.resultSignal.emit('')
        finally:
            self.stop_recording()

    def _record_audio(self, transcriber):
        """
        Record audio from the microphone, handing finished chunks to the transcriber.

        :return: numpy array of audio data, or None if the recording is too short
        """
        recording_options = ConfigManager.get_config_section('recording_options')
        self.sample_rate = recording_options.get('sample_rate') or 16000
        frame_duration_ms = 30  # 30ms frame duration for WebRTC VAD
        frame_size = int(self.sample_rate * (frame_duration_ms / 1000.0))
        silence_duration_ms = recording_options.get('silence_duration') or 900
        silence_frames = int(silence_duration_ms / frame_duration_ms)

        # 150ms delay before starting VAD to avoid mistaking the sound of key pressing for voice
        initial_frames_to_skip = int(0.15 * self.sample_rate / frame_size)

        # Create VAD only for recording modes that use it
        recording_mode = recording_options.get('recording_mode') or 'continuous'
        vad = None
        if recording_mode in ('voice_activity_detection', 'continuous'):
            vad = webrtcvad.Vad(2)  # VAD aggressiveness: 0 to 3, 3 being the most aggressive
            speech_detected = False
            silent_frame_count = 0

        # Separate VAD for chunking, so it works in every recording mode.
        chunk_vad = webrtcvad.Vad(2)
        chunk_min_frames = int(CHUNK_MIN_SECONDS * 1000 / frame_duration_ms)
        chunk_max_frames = int(CHUNK_MAX_SECONDS * 1000 / frame_duration_ms)
        pause_frames = int(CHUNK_PAUSE_MS / frame_duration_ms)
        chunk_start = 0      # index of the first frame not yet sent to the transcriber
        silent_run = 0       # consecutive non-speech frames
        last_pause_cut = 0   # frame index in the middle of the latest pause

        audio_buffer = deque(maxlen=frame_size)
        recording = []  # list of frames

        data_ready = Event()

        def audio_callback(indata, frames, time, status):
            if status:
                ConfigManager.console_print(f"Audio callback status: {status}")
            audio_buffer.extend(indata[:, 0])
            data_ready.set()

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16',
                            blocksize=frame_size, device=recording_options.get('sound_device'),
                            callback=audio_callback):
            while self.is_running and self.is_recording:
                data_ready.wait()
                data_ready.clear()

                if len(audio_buffer) < frame_size:
                    continue

                # Save frame
                frame = np.array(list(audio_buffer), dtype=np.int16)
                audio_buffer.clear()
                recording.append(frame)

                # Avoid trying to detect voice in initial frames
                if initial_frames_to_skip > 0:
                    initial_frames_to_skip -= 1
                    continue

                is_speech = chunk_vad.is_speech(frame.tobytes(), self.sample_rate)
                silent_run = 0 if is_speech else silent_run + 1
                if silent_run >= pause_frames:
                    last_pause_cut = len(recording) - silent_run // 2
                chunk_frames = len(recording) - chunk_start
                cut = None
                if chunk_frames >= chunk_min_frames and silent_run >= pause_frames:
                    cut = last_pause_cut
                elif chunk_frames >= chunk_max_frames:
                    # Fall back to the last pause only if it leaves a useful chunk.
                    cut = last_pause_cut if last_pause_cut - chunk_start >= chunk_min_frames // 3 else len(recording)
                if cut:
                    transcriber.submit(np.concatenate(recording[chunk_start:cut]))
                    chunk_start = cut

                if vad:
                    if is_speech:
                        silent_frame_count = 0
                        if not speech_detected:
                            ConfigManager.console_print("Speech detected.")
                            speech_detected = True
                    else:
                        silent_frame_count += 1

                    if speech_detected and silent_frame_count > silence_frames:
                        break

        audio_data = np.concatenate(recording) if recording else np.array([], dtype=np.int16)
        duration = len(audio_data) / self.sample_rate

        ConfigManager.console_print(f'Recording finished. Size: {audio_data.size} samples, Duration: {duration:.2f} seconds')

        min_duration_ms = recording_options.get('min_duration') or 100

        if (duration * 1000) < min_duration_ms:
            ConfigManager.console_print(f'Discarded due to being too short.')
            return None

        if chunk_start < len(recording):
            transcriber.submit(np.concatenate(recording[chunk_start:]))

        try:
            sf.write(LAST_RECORDING_PATH, audio_data, self.sample_rate)
        except Exception as e:
            ConfigManager.console_print(f'Could not save {LAST_RECORDING_PATH}: {e}')

        return audio_data
