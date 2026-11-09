"""pygame.display emulation: the window is just an off-screen Surface."""
from . import Surface, error

_surface = None
_caption = ("pygame window", "pygame window")
_init = False
frames = 0  # number of flip() calls, handy for tests


def init():
    global _init
    _init = True


def quit():  # noqa: A001
    global _init, _surface
    _init = False
    _surface = None


def get_init():
    return _init


def set_mode(size=(0, 0), flags=0, depth=0, display=0, vsync=0):
    global _surface, _init
    _init = True
    w, h = int(size[0]), int(size[1])
    if (w, h) == (0, 0):
        w, h = 1280, 720
    _surface = Surface((w, h), 0)
    _surface._flags = int(flags) & ~65536  # a window never has per-pixel alpha
    return _surface


def get_surface():
    return _surface


def set_caption(title, icontitle=None):
    global _caption
    _caption = (title, icontitle or title)


def get_caption():
    return _caption


def set_icon(surface):
    pass


def flip():
    global frames
    if _surface is None:
        raise error("video system not initialized")
    frames += 1


def update(*args):
    flip()


def get_window_size():
    return _surface.get_size() if _surface else (0, 0)


def get_desktop_sizes():
    return [(1920, 1080)]


def toggle_fullscreen():
    return 0


def get_driver():
    return "shim"


class _Info:
    current_w, current_h = 1920, 1080
    bitsize, bytesize = 32, 4


def Info():
    return _Info()
