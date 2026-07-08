# NOTE: ctranslate2 mora biti uvezen PRE PyQt5. Qt5Core.dll inače učita konfliktne
# verzije deljenih C/OpenMP DLL-ova pa C++ konstruktor ctranslate2.models.Whisper(...)
# pukne kao Windows access violation. Pre-loadovanje rezervise prave DLL-ove.
import ctranslate2  # noqa: F401

import os
import sys
import time

# Qt trazi "windows" platform plugin preko prefiksa ugradjenog u Qt5Core.dll;
# ako je taj zapis ostecen, prefix je prazan i app puca sa "Could not find the
# Qt platform plugin". Zato putanju do plugin-a postavljamo eksplicitno.
import PyQt5
_qt_plugins = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins')
if os.path.isdir(_qt_plugins):
    os.environ.setdefault('QT_PLUGIN_PATH', _qt_plugins)
    os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', os.path.join(_qt_plugins, 'platforms'))
from audioplayer import AudioPlayer
from pynput.keyboard import Controller
from PyQt5.QtCore import QObject, QProcess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox

from key_listener import KeyListener
from result_thread import ResultThread
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow
from ui.status_window import StatusWindow
from transcription import create_local_model
from input_simulation import InputSimulator
from audio_ducker import AudioDucker
from utils import ConfigManager


class WhisperWriterApp(QObject):
    def __init__(self):
        """
        Initialize the application, opening settings window if no configuration file is found.
        """
        super().__init__()
        ConfigManager.initialize()
        self.transcription_history = []  # poslednje 3 izdiktirane recenice, najnovija prva
        # QApplication MORA da se kreira pre ucitavanja modela: create_local_model()
        # pokrece OpenMP thread pool-ove, pa Qt inicijalizacija posle toga povremeno
        # pukne kao tihi access violation (isti DLL konflikt kao kod import redosleda).
        self.app = QApplication(sys.argv)
        self.app.setWindowIcon(QIcon(os.path.join('assets', 'ww-logo.png')))
        # Tray ikonica se pravi PRE ucitavanja modela da korisnik odmah vidi
        # da se aplikacija pokrece (bitno za tihi start bez konzole).
        self.create_tray_icon()
        self.tray_icon.setToolTip('WhisperWriter - loading model...')
        self.app.processEvents()
        _mo = ConfigManager.get_config_section('model_options')
        self._preloaded_model = create_local_model() if not _mo.get('use_api') else None

        self.settings_window = SettingsWindow()
        self.settings_window.settings_closed.connect(self.on_settings_closed)
        self.settings_window.settings_saved.connect(self.restart_app)

        if ConfigManager.config_file_exists():
            self.initialize_components()
        else:
            print('No valid configuration file found. Opening settings window...')
            self.settings_window.show()

    def initialize_components(self):
        """
        Initialize the components of the application.
        """
        self.input_simulator = InputSimulator()
        self.audio_ducker = AudioDucker()

        self.key_listener = KeyListener()
        self.key_listener.add_callback("on_activate", self.on_activation)
        self.key_listener.add_callback("on_deactivate", self.on_deactivation)

        model_options = ConfigManager.get_config_section('model_options')
        model_path = model_options.get('local', {}).get('model_path')
        self.local_model = self._preloaded_model

        self.result_thread = None

        self.main_window = MainWindow()
        self.main_window.openSettings.connect(self.settings_window.show)
        self.main_window.startListening.connect(self.key_listener.start)
        self.main_window.closeApp.connect(self.exit_app)

        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.status_window = StatusWindow()

        self.create_tray_icon()
        self.main_window.show()

    def create_tray_icon(self):
        """
        Create (or rebuild) the system tray icon and its context menu.
        Called once before the model loads with a minimal menu, and again
        from initialize_components with the full menu.
        """
        if not hasattr(self, 'tray_icon'):
            self.tray_icon = QSystemTrayIcon(QIcon(os.path.join('assets', 'ww-logo.png')), self.app)

        self.tray_menu = QMenu()

        if getattr(self, 'main_window', None):
            show_action = QAction('WhisperWriter Main Menu', self.app)
            show_action.triggered.connect(self.main_window.show)
            self.tray_menu.addAction(show_action)

        if getattr(self, 'settings_window', None):
            settings_action = QAction('Open Settings', self.app)
            settings_action.triggered.connect(self.settings_window.show)
            self.tray_menu.addAction(settings_action)

        self.history_menu = QMenu('History (click = copy)', self.tray_menu)
        self.tray_menu.addMenu(self.history_menu)
        self.update_history_menu()

        exit_action = QAction('Exit', self.app)
        exit_action.triggered.connect(self.exit_app)
        self.tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.setToolTip('WhisperWriter')
        self.tray_icon.show()

    def cleanup(self):
        # getattr: Exit iz tray-a je moguc i pre initialize_components (dok se model ucitava)
        if getattr(self, 'key_listener', None):
            self.key_listener.stop()
        if getattr(self, 'input_simulator', None):
            self.input_simulator.cleanup()
        if getattr(self, 'audio_ducker', None):
            self.audio_ducker.restore()

    def exit_app(self):
        """
        Exit the application.
        """
        self.cleanup()
        QApplication.quit()

    def restart_app(self):
        """Restart the application to apply the new settings."""
        self.cleanup()
        QApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

    def on_settings_closed(self):
        """
        If settings is closed without saving on first run, initialize the components with default values.
        """
        if not os.path.exists(os.path.join('src', 'config.yaml')):
            QMessageBox.information(
                self.settings_window,
                'Using Default Values',
                'Settings closed without saving. Default values are being used.'
            )
            self.initialize_components()

    def on_activation(self):
        """
        Called when the activation key combination is pressed.
        """
        if self.result_thread and self.result_thread.isRunning():
            recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
            if recording_mode == 'press_to_toggle':
                self.result_thread.stop_recording()
            elif recording_mode == 'continuous':
                self.stop_result_thread()
            return

        self.start_result_thread()

    def on_deactivation(self):
        """
        Called when the activation key combination is released.
        """
        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'hold_to_record':
            if self.result_thread and self.result_thread.isRunning():
                self.result_thread.stop_recording()

    def start_result_thread(self):
        """
        Start the result thread to record audio and transcribe it.
        """
        if self.result_thread and self.result_thread.isRunning():
            return

        self.result_thread = ResultThread(self.local_model)
        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.result_thread.statusSignal.connect(self.status_window.updateStatus)
            self.status_window.closeSignal.connect(self.stop_result_thread)
        self.result_thread.statusSignal.connect(self.on_status_change)
        self.result_thread.resultSignal.connect(self.on_transcription_complete)
        self.result_thread.start()

    def on_status_change(self, status):
        """
        React to recording status: mute other apps' audio and play a short
        beep when recording starts, restore audio and beep when it stops.
        """
        beeps = ConfigManager.get_config_value('misc', 'recording_beeps')
        mute = ConfigManager.get_config_value('misc', 'mute_audio_while_recording')
        if status == 'recording':
            if mute:
                self.audio_ducker.mute_others()
            if beeps:
                self._play_sound('beep-start.wav')
        else:
            # 'transcribing' or 'idle' - recording is over either way
            if mute:
                self.audio_ducker.restore()
            if beeps and status == 'transcribing':
                self._play_sound('beep-stop.wav')

    def _play_sound(self, filename):
        """
        Play a sound file without blocking the UI thread.
        """
        try:
            # Referenca se cuva na self da GC ne bi prekinuo reprodukciju.
            self._beep_player = AudioPlayer(os.path.join('assets', filename))
            self._beep_player.play(block=False)
        except Exception as e:
            ConfigManager.console_print(f'Could not play {filename}: {e}')

    def stop_result_thread(self):
        """
        Stop the result thread.
        """
        if self.result_thread and self.result_thread.isRunning():
            self.result_thread.stop()

    def update_history_menu(self):
        """Rebuild the tray History submenu from the last transcriptions."""
        if not getattr(self, 'history_menu', None):
            return
        self.history_menu.clear()
        if not self.transcription_history:
            empty_action = QAction('(nothing dictated yet)', self.app)
            empty_action.setEnabled(False)
            self.history_menu.addAction(empty_action)
            return
        for text in self.transcription_history:
            words = text.split()
            label = ' '.join(words[:5])[:40]
            if label != text:
                label += '…'
            action = QAction(label, self.app)
            action.setToolTip(text)
            action.triggered.connect(lambda checked=False, t=text: self.app.clipboard().setText(t))
            self.history_menu.addAction(action)

    def remember_transcription(self, text):
        """Keep the last 3 transcriptions for the tray History menu."""
        text = text.strip()
        if not text:
            return
        self.transcription_history.insert(0, text)
        del self.transcription_history[3:]
        self.update_history_menu()

    def on_transcription_complete(self, result):
        """
        When the transcription is complete, type the result and start listening for the activation key again.
        """
        # Prvo zapamti u History - i ako kucanje pukne, tekst ostaje dostupan za copy.
        self.remember_transcription(result)
        self.input_simulator.typewrite(result)

        if ConfigManager.get_config_value('misc', 'noise_on_completion'):
            AudioPlayer(os.path.join('assets', 'beep.wav')).play(block=True)

        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous':
            self.start_result_thread()
        else:
            self.key_listener.start()

    def run(self):
        """
        Start the application.
        """
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    app = WhisperWriterApp()
    app.run()



