"""pygame.mouse emulation (posted events do not move the cursor, same as pygame)."""
_pos = (0, 0)
_visible = True


def get_pos():
    return _pos


def set_pos(*pos):
    global _pos
    p = pos[0] if len(pos) == 1 else pos
    _pos = (int(p[0]), int(p[1]))


def get_pressed(num_buttons=3):
    return (False,) * num_buttons


def get_rel():
    return (0, 0)


def set_visible(value):
    global _visible
    previous, _visible = _visible, bool(value)
    return previous


def get_visible():
    return _visible


def set_cursor(*args, **kwargs):
    pass


def get_cursor():
    return None


def get_focused():
    return True
