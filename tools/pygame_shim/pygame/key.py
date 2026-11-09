"""pygame.key emulation. State is never changed by posted events (same as pygame)."""
import pygame as _pg

_mods = 0
_repeat = (0, 0)
_SPECIAL = {
    _pg.K_SPACE: "space", _pg.K_RETURN: "return", _pg.K_ESCAPE: "escape",
    _pg.K_BACKSPACE: "backspace", _pg.K_TAB: "tab", _pg.K_DELETE: "delete",
    _pg.K_UP: "up", _pg.K_DOWN: "down", _pg.K_LEFT: "left", _pg.K_RIGHT: "right",
    _pg.K_LSHIFT: "left shift", _pg.K_RSHIFT: "right shift",
    _pg.K_LCTRL: "left ctrl", _pg.K_RCTRL: "right ctrl",
    _pg.K_LALT: "left alt", _pg.K_RALT: "right alt",
}
_SPECIAL.update({getattr(_pg, "K_F%d" % i): "f%d" % i for i in range(1, 13)})


class _Pressed:
    """Stand-in for ScancodeWrapper: every key reads as released."""

    def __getitem__(self, key):
        return False

    def __len__(self):
        return 512

    def __iter__(self):
        return iter([False] * 512)


def get_pressed():
    return _Pressed()


def get_mods():
    return _mods


def set_mods(mods):
    global _mods
    _mods = int(mods)


def get_focused():
    return True


def set_repeat(delay=0, interval=0):
    global _repeat
    _repeat = (int(delay), int(interval))


def get_repeat():
    return _repeat


def name(key, use_compat=True):
    if key in _SPECIAL:
        return _SPECIAL[key]
    if 32 < key < 127:
        return chr(key)
    return "unknown key"


def key_code(key_name):
    for code, label in _SPECIAL.items():
        if label == key_name:
            return code
    if len(key_name) == 1:
        return ord(key_name.lower())
    raise ValueError("unknown key name")


def start_text_input():
    pass


def stop_text_input():
    pass


def set_text_input_rect(rect):
    pass
