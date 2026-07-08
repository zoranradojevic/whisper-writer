import os

from utils import ConfigManager


class AudioDucker:
    """
    Mutes every other application's audio session while recording, and
    restores it afterwards. Windows-only (uses pycaw / Core Audio); on other
    platforms or if pycaw is missing it silently does nothing.

    Only sessions that were audible get muted, so anything the user muted
    manually stays muted after restore. Our own process is skipped so the
    start/stop beeps remain audible.
    """

    def __init__(self):
        self._muted_sessions = []
        self._available = None  # lazily probed on first use

    def _pycaw_sessions(self):
        if self._available is False:
            return None
        try:
            from pycaw.pycaw import AudioUtilities
            sessions = AudioUtilities.GetAllSessions()
            self._available = True
            return sessions
        except Exception as e:
            if self._available is None:
                ConfigManager.console_print(f'Audio muting unavailable: {e}')
            self._available = False
            return None

    def mute_others(self):
        """Mute all audible audio sessions except our own process."""
        if self._muted_sessions:
            return  # already muted, don't stack
        sessions = self._pycaw_sessions()
        if not sessions:
            return
        own_pid = os.getpid()
        for session in sessions:
            try:
                if session.Process and session.Process.pid == own_pid:
                    continue
                volume = session.SimpleAudioVolume
                if volume and not volume.GetMute():
                    volume.SetMute(1, None)
                    self._muted_sessions.append(session)
            except Exception:
                continue
        if self._muted_sessions:
            ConfigManager.console_print(f'Muted {len(self._muted_sessions)} audio session(s) while recording.')

    def restore(self):
        """Unmute everything we muted."""
        if not self._muted_sessions:
            return
        for session in self._muted_sessions:
            try:
                session.SimpleAudioVolume.SetMute(0, None)
            except Exception:
                continue
        ConfigManager.console_print(f'Restored {len(self._muted_sessions)} audio session(s).')
        self._muted_sessions = []
