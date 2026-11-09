"""pygame.event emulation: a plain FIFO queue.

Like real pygame, posting synthetic events does NOT change pygame.key or
pygame.mouse state, so games must track input from the events themselves.
"""
from collections import deque

from . import (ACTIVEEVENT, KEYDOWN, KEYUP, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION,
               MOUSEWHEEL, NOEVENT, QUIT, TEXTINPUT, USEREVENT, VIDEORESIZE)

_NAMES = {
    NOEVENT: "NoEvent", QUIT: "Quit", KEYDOWN: "KeyDown", KEYUP: "KeyUp",
    TEXTINPUT: "TextInput", MOUSEMOTION: "MouseMotion", MOUSEBUTTONDOWN: "MouseButtonDown",
    MOUSEBUTTONUP: "MouseButtonUp", MOUSEWHEEL: "MouseWheel", ACTIVEEVENT: "ActiveEvent",
    VIDEORESIZE: "VideoResize",
}


class Event:
    def __init__(self, type, dict=None, **attrs):  # noqa: A002 - pygame argument names
        if dict is not None:
            attrs = {**dict, **attrs}
        if "type" in attrs:
            raise ValueError("redundant type field in event dict")
        self.__dict__.update(attrs)
        self.__dict__["type"] = int(type)

    @property
    def dict(self):
        return {k: v for k, v in self.__dict__.items() if k != "type"}

    def __repr__(self):
        return "<Event(%d-%s %s)>" % (self.type, event_name(self.type), self.dict)

    def __eq__(self, other):
        return isinstance(other, Event) and self.type == other.type and self.dict == other.dict

    def __bool__(self):
        return self.type != NOEVENT


EventType = Event

_queue = deque()
_blocked = set()
_grab = False
_next_custom = USEREVENT + 1


def _types(value):
    return set(value) if isinstance(value, (list, tuple, set)) else {value}


def post(event):
    if event.type in _blocked:
        return False
    _queue.append(event)
    return True


def get(eventtype=None, pump=True, exclude=None):
    want = None if eventtype is None else _types(eventtype)
    skip = set() if exclude is None else _types(exclude)
    out, keep = [], deque()
    while _queue:
        ev = _queue.popleft()
        ok = (want is None or ev.type in want) and ev.type not in skip
        (out if ok else keep).append(ev)
    _queue.extend(keep)
    return out


def poll():
    return _queue.popleft() if _queue else Event(NOEVENT)


def wait(timeout=0):
    return poll()


def peek(eventtype=None, pump=True):
    if eventtype is None:
        return bool(_queue)
    want = _types(eventtype)
    return any(ev.type in want for ev in _queue)


def clear(eventtype=None, pump=True):
    get(eventtype)


def pump():
    pass


def set_blocked(eventtype):
    if eventtype is None:
        return
    _blocked.update(_types(eventtype))


def set_allowed(eventtype):
    if eventtype is None:
        _blocked.clear()
    else:
        _blocked.difference_update(_types(eventtype))


def get_blocked(eventtype):
    return bool(_types(eventtype) & _blocked)


def set_grab(value):
    global _grab
    _grab = bool(value)


def get_grab():
    return _grab


def event_name(event_type):
    if event_type in _NAMES:
        return _NAMES[event_type]
    return "UserEvent" if event_type >= USEREVENT else "Unknown"


def custom_type():
    global _next_custom
    _next_custom += 1
    return _next_custom - 1
