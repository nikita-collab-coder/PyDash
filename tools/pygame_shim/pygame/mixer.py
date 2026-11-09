"""pygame.mixer emulation: accepts sounds and validates buffers, plays nothing.

Set PYGAME_SHIM_NO_AUDIO=1 to simulate a machine without an audio device.
"""
import os

from . import error

_pre = (44100, -16, 2)
_init = None
_channels = 8


def pre_init(frequency=44100, size=-16, channels=2, buffer=512, *args, **kwargs):
    global _pre
    _pre = (frequency or 44100, size or -16, channels or 2)


def init(frequency=None, size=None, channels=None, buffer=None, *args, **kwargs):
    global _init
    if os.environ.get("PYGAME_SHIM_NO_AUDIO"):
        raise error("No available audio device")
    _init = (frequency or _pre[0], size or _pre[1], channels or _pre[2])


def quit():  # noqa: A001
    global _init
    _init = None


def get_init():
    return _init


def _check():
    if _init is None:
        raise error("mixer not initialized")


def stop():
    pass


def pause():
    pass


def unpause():
    pass


def fadeout(time):
    pass


def set_num_channels(count):
    global _channels
    _channels = int(count)


def get_num_channels():
    return _channels


def get_busy():
    return False


class Channel:
    def __init__(self, id=0):  # noqa: A002
        self.id = id
        self._volume = 1.0
        self._sound = None

    def play(self, sound, loops=0, maxtime=0, fade_ms=0):
        self._sound = sound

    def stop(self):
        self._sound = None

    def fadeout(self, time):
        self._sound = None

    def set_volume(self, value, right=None):
        self._volume = float(value)

    def get_volume(self):
        return self._volume

    def get_busy(self):
        return False


class Sound:
    def __init__(self, file=None, buffer=None, array=None):
        _check()
        if buffer is None and file is None:
            raise TypeError("Sound() needs a file or a buffer")
        freq, size, channels = _init
        self._frame = abs(size) // 8 * channels
        self._raw = bytes(buffer) if buffer is not None else b""
        if len(self._raw) % self._frame:
            raise ValueError("Buffer length (%d) is not a multiple of the frame size (%d)"
                             % (len(self._raw), self._frame))
        self._volume = 1.0
        self.play_count = 0

    def play(self, loops=0, maxtime=0, fade_ms=0):
        self.play_count += 1
        return Channel(0)

    def stop(self):
        pass

    def fadeout(self, time):
        pass

    def set_volume(self, value):
        self._volume = max(0.0, min(1.0, float(value)))

    def get_volume(self):
        return self._volume

    def get_length(self):
        return len(self._raw) / self._frame / _init[0]

    def get_raw(self):
        return self._raw


class _Music:
    """Stub for pygame.mixer.music."""

    def load(self, *a, **k):
        pass

    def play(self, *a, **k):
        pass

    def stop(self):
        pass

    def pause(self):
        pass

    def unpause(self):
        pass

    def fadeout(self, time):
        pass

    def set_volume(self, value):
        pass

    def get_volume(self):
        return 1.0

    def get_busy(self):
        return False


music = _Music()


# --- pause/unpause like pygame (state only: the emulator produces no sound)
def _channel_pause(self):
    self._paused = True


def _channel_unpause(self):
    self._paused = False


for _name, _fn in (("pause", _channel_pause), ("unpause", _channel_unpause)):
    if not hasattr(Channel, _name):
        setattr(Channel, _name, _fn)

if "pause" not in globals():
    def pause():
        pass

if "unpause" not in globals():
    def unpause():
        pass
