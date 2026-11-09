"""Minimal pygame emulation for headless visual checks (NOT part of PyDash).

Implements the subset of the pygame 2 API that PyDash uses on top of Pillow
and numpy, so frames can be rendered to PNG files in a sandbox without SDL.
Behaviour follows pygame 2 where it matters (int-truncating Rects, strict
color arguments, alpha blending formulas, draw functions that overwrite).
"""
import math
import os
import sys
import time as _time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SHIM = True


class error(RuntimeError):
    """Same name as pygame.error."""


# ------------------------------------------------------------------ flags
SWSURFACE = 0
HWSURFACE = 1
OPENGL = 2
RESIZABLE = 16
NOFRAME = 32
SCALED = 512
SRCCOLORKEY = 4096
RLEACCEL = 16384
SRCALPHA = 65536
DOUBLEBUF = 1073741824
FULLSCREEN = -2147483648

BLEND_RGB_ADD = BLEND_ADD = 1
BLEND_RGB_SUB = BLEND_SUB = 2
BLEND_RGB_MULT = BLEND_MULT = 3
BLEND_RGB_MIN = BLEND_MIN = 4
BLEND_RGB_MAX = BLEND_MAX = 5
BLEND_RGBA_ADD = 6
BLEND_RGBA_SUB = 7
BLEND_RGBA_MULT = 8
BLEND_RGBA_MIN = 9
BLEND_RGBA_MAX = 10
BLEND_PREMULTIPLIED = 17
BLEND_ALPHA_SDL2 = 18

# ------------------------------------------------------------------ events
NOEVENT = 0
QUIT = 256
KEYDOWN = 768
KEYUP = 769
TEXTEDITING = 770
TEXTINPUT = 771
MOUSEMOTION = 1024
MOUSEBUTTONDOWN = 1025
MOUSEBUTTONUP = 1026
MOUSEWHEEL = 1027
ACTIVEEVENT = 32768
VIDEORESIZE = 32769
VIDEOEXPOSE = 32770
WINDOWFOCUSLOST = 32785
USEREVENT = 32866

BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT = 1, 2, 3
BUTTON_WHEELUP, BUTTON_WHEELDOWN = 4, 5

# ------------------------------------------------------------------ keys (SDL2 values)
K_BACKSPACE, K_TAB, K_RETURN, K_ESCAPE, K_SPACE, K_DELETE = 8, 9, 13, 27, 32, 127
K_PLUS, K_COMMA, K_MINUS, K_PERIOD, K_SLASH, K_EQUALS = 43, 44, 45, 46, 47, 61
K_LEFTBRACKET, K_RIGHTBRACKET = 91, 93
for _i in range(10):
    globals()["K_%d" % _i] = 48 + _i
for _c in "abcdefghijklmnopqrstuvwxyz":
    globals()["K_" + _c] = ord(_c)
for _i in range(1, 13):
    globals()["K_F%d" % _i] = 1073741881 + _i
K_HOME, K_PAGEUP, K_END, K_PAGEDOWN = 1073741898, 1073741899, 1073741901, 1073741902
K_RIGHT, K_LEFT, K_DOWN, K_UP = 1073741903, 1073741904, 1073741905, 1073741906
K_KP_MINUS, K_KP_PLUS, K_KP_ENTER = 1073741910, 1073741911, 1073741912
K_LCTRL, K_LSHIFT, K_LALT, K_LGUI = 1073742048, 1073742049, 1073742050, 1073742051
K_RCTRL, K_RSHIFT, K_RALT, K_RGUI = 1073742052, 1073742053, 1073742054, 1073742055

KMOD_NONE = 0
KMOD_LSHIFT, KMOD_RSHIFT, KMOD_SHIFT = 1, 2, 3
KMOD_LCTRL, KMOD_RCTRL, KMOD_CTRL = 64, 128, 192
KMOD_LALT, KMOD_RALT, KMOD_ALT = 256, 512, 768
KMOD_LMETA, KMOD_RMETA, KMOD_META = 1024, 2048, 3072
KMOD_LGUI, KMOD_RGUI, KMOD_GUI = 1024, 2048, 3072

# ------------------------------------------------------------------ colors
_NAMED = {
    "white": (255, 255, 255, 255), "black": (0, 0, 0, 255),
    "red": (255, 0, 0, 255), "green": (0, 255, 0, 255), "blue": (0, 0, 255, 255),
    "yellow": (255, 255, 0, 255), "cyan": (0, 255, 255, 255),
    "magenta": (255, 0, 255, 255), "orange": (255, 165, 0, 255),
    "gray": (190, 190, 190, 255), "grey": (190, 190, 190, 255),
}


def _rgba(c):
    """Convert any pygame color argument to an (r, g, b, a) tuple of ints.

    Strict on purpose: float or out-of-range components raise, so bugs that
    real pygame would reject are caught in the sandbox too.
    """
    if isinstance(c, Color):
        return (c.r, c.g, c.b, c.a)
    if isinstance(c, str):
        s = c.strip().lower()
        if s.startswith("#") and len(s) in (7, 9):
            v = [int(s[i:i + 2], 16) for i in range(1, len(s), 2)]
            return tuple(v + [255] * (4 - len(v)))
        if s in _NAMED:
            return _NAMED[s]
        raise ValueError("invalid color name %r" % c)
    if isinstance(c, (int, np.integer)) and not isinstance(c, bool):
        c = int(c)
        return ((c >> 16) & 255, (c >> 8) & 255, c & 255, 255)
    try:
        t = tuple(c)
    except TypeError:
        raise TypeError("invalid color argument %r" % (c,))
    if len(t) not in (3, 4):
        raise ValueError("invalid color argument %r" % (c,))
    out = []
    for v in t:
        if not isinstance(v, (int, np.integer)) or isinstance(v, bool):
            raise TypeError("invalid color argument %r (components must be ints)" % (c,))
        if not 0 <= int(v) <= 255:
            raise ValueError("invalid color argument %r (out of range)" % (c,))
        out.append(int(v))
    if len(out) == 3:
        out.append(255)
    return tuple(out)


class Color:
    __slots__ = ("r", "g", "b", "a")

    def __init__(self, r=0, g=None, b=None, a=255):
        if g is None:
            r, g, b, a = _rgba(r)
        else:
            r, g, b, a = _rgba((r, g, b, a))
        self.r, self.g, self.b, self.a = r, g, b, a

    def __iter__(self):
        return iter((self.r, self.g, self.b, self.a))

    def __len__(self):
        return 4

    def __getitem__(self, i):
        return (self.r, self.g, self.b, self.a)[i]

    def __eq__(self, other):
        try:
            return tuple(self) == _rgba(other)
        except (TypeError, ValueError):
            return False

    def __hash__(self):
        return hash(tuple(self))

    def __repr__(self):
        return "Color(%d, %d, %d, %d)" % tuple(self)

    def lerp(self, other, t):
        o = _rgba(other)
        return Color(*[int(round(a + (b - a) * t)) for a, b in zip(self, o)])


# ------------------------------------------------------------------ Rect
def _rect_args(args):
    if len(args) == 1:
        a = args[0]
        if isinstance(a, Rect):
            return a.x, a.y, a.w, a.h
        if hasattr(a, "rect"):
            r = a.rect() if callable(a.rect) else a.rect
            return _rect_args((r,))
        a = tuple(a)
        if len(a) == 4:
            return a
        if len(a) == 2:
            return a[0][0], a[0][1], a[1][0], a[1][1]
    elif len(args) == 2:
        return args[0][0], args[0][1], args[1][0], args[1][1]
    elif len(args) == 4:
        return args
    raise TypeError("Argument must be rect style object")


class Rect:
    """Integer rectangle with the same attribute names as pygame.Rect."""
    __slots__ = ("_x", "_y", "_w", "_h")

    def __init__(self, *args):
        x, y, w, h = _rect_args(args)
        self._x, self._y, self._w, self._h = int(x), int(y), int(w), int(h)

    # ---- primary attributes (floats are truncated like pygame 2)
    x = left = property(lambda s: s._x, lambda s, v: setattr(s, "_x", int(v)))
    y = top = property(lambda s: s._y, lambda s, v: setattr(s, "_y", int(v)))
    w = width = property(lambda s: s._w, lambda s, v: setattr(s, "_w", int(v)))
    h = height = property(lambda s: s._h, lambda s, v: setattr(s, "_h", int(v)))

    # ---- derived attributes
    @property
    def right(self):
        return self._x + self._w

    @right.setter
    def right(self, v):
        self._x = int(v) - self._w

    @property
    def bottom(self):
        return self._y + self._h

    @bottom.setter
    def bottom(self, v):
        self._y = int(v) - self._h

    @property
    def centerx(self):
        return self._x + self._w // 2

    @centerx.setter
    def centerx(self, v):
        self._x = int(v) - self._w // 2

    @property
    def centery(self):
        return self._y + self._h // 2

    @centery.setter
    def centery(self, v):
        self._y = int(v) - self._h // 2

    def _pair(getx, gety, setx, sety):
        def fget(self):
            return (getx.fget(self), gety.fget(self))

        def fset(self, v):
            setx.fset(self, v[0])
            sety.fset(self, v[1])
        return property(fget, fset)

    center = _pair(centerx, centery, centerx, centery)
    topleft = _pair(x, y, x, y)
    topright = _pair(right, y, right, y)
    bottomleft = _pair(x, bottom, x, bottom)
    bottomright = _pair(right, bottom, right, bottom)
    midtop = _pair(centerx, y, centerx, y)
    midbottom = _pair(centerx, bottom, centerx, bottom)
    midleft = _pair(x, centery, x, centery)
    midright = _pair(right, centery, right, centery)
    size = _pair(w, h, w, h)
    del _pair

    # ---- python protocol
    def __iter__(self):
        return iter((self._x, self._y, self._w, self._h))

    def __len__(self):
        return 4

    def __getitem__(self, i):
        return (self._x, self._y, self._w, self._h)[i]

    def __eq__(self, other):
        try:
            return tuple(self) == tuple(Rect(other))
        except (TypeError, ValueError, IndexError):
            return False

    __hash__ = None

    def __bool__(self):
        return self._w != 0 and self._h != 0

    def __repr__(self):
        return "<rect(%d, %d, %d, %d)>" % tuple(self)

    def __copy__(self):
        return Rect(self)

    # ---- methods
    def copy(self):
        return Rect(self)

    def update(self, *args):
        self.__init__(*args)

    def move(self, *d):
        dx, dy = d[0] if len(d) == 1 else d
        return Rect(self._x + int(dx), self._y + int(dy), self._w, self._h)

    def move_ip(self, *d):
        dx, dy = d[0] if len(d) == 1 else d
        self._x += int(dx)
        self._y += int(dy)

    def inflate(self, *d):
        dx, dy = d[0] if len(d) == 1 else d
        dx, dy = int(dx), int(dy)
        return Rect(self._x - int(dx / 2), self._y - int(dy / 2), self._w + dx, self._h + dy)

    def inflate_ip(self, *d):
        self.update(self.inflate(*d))

    def clamp(self, other):
        o = Rect(other)
        r = Rect(self)
        r.x = o.x + (o.w - r.w) // 2 if r.w >= o.w else min(max(r.x, o.x), o.right - r.w)
        r.y = o.y + (o.h - r.h) // 2 if r.h >= o.h else min(max(r.y, o.y), o.bottom - r.h)
        return r

    def clamp_ip(self, other):
        self.update(self.clamp(other))

    def clip(self, other):
        o = Rect(other)
        x0, y0 = max(self._x, o.x), max(self._y, o.y)
        x1, y1 = min(self.right, o.right), min(self.bottom, o.bottom)
        if x1 <= x0 or y1 <= y0:
            return Rect(self._x, self._y, 0, 0)
        return Rect(x0, y0, x1 - x0, y1 - y0)

    def union(self, other):
        o = Rect(other)
        x0, y0 = min(self._x, o.x), min(self._y, o.y)
        return Rect(x0, y0, max(self.right, o.right) - x0, max(self.bottom, o.bottom) - y0)

    def union_ip(self, other):
        self.update(self.union(other))

    def unionall(self, others):
        r = Rect(self)
        for o in others:
            r = r.union(o)
        return r

    def normalize(self):
        if self._w < 0:
            self._x += self._w
            self._w = -self._w
        if self._h < 0:
            self._y += self._h
            self._h = -self._h

    def contains(self, other):
        o = Rect(other)
        return (self._x <= o.x and self._y <= o.y and o.right <= self.right
                and o.bottom <= self.bottom)

    def collidepoint(self, *p):
        px, py = p[0] if len(p) == 1 else p
        return self._x <= px < self.right and self._y <= py < self.bottom

    def colliderect(self, other):
        o = Rect(other)
        return (self._x < o.right and o.x < self.right
                and self._y < o.bottom and o.y < self.bottom)

    def collidelist(self, rects):
        for i, r in enumerate(rects):
            if self.colliderect(r):
                return i
        return -1

    def collidelistall(self, rects):
        return [i for i, r in enumerate(rects) if self.colliderect(r)]


# ------------------------------------------------------------------ blending
_RGBA_FLAGS = {BLEND_RGBA_ADD, BLEND_RGBA_SUB, BLEND_RGBA_MULT, BLEND_RGBA_MIN, BLEND_RGBA_MAX}
_BLEND_OPS = {
    BLEND_RGB_ADD: "add", BLEND_RGBA_ADD: "add", BLEND_RGB_SUB: "sub", BLEND_RGBA_SUB: "sub",
    BLEND_RGB_MULT: "mult", BLEND_RGBA_MULT: "mult", BLEND_RGB_MIN: "min", BLEND_RGBA_MIN: "min",
    BLEND_RGB_MAX: "max", BLEND_RGBA_MAX: "max",
}


def _blend(d, s, flags, s_alpha, d_alpha, surf_alpha, colorkey):
    """Blend source pixels onto destination pixels like pygame 2.

    d and s are (h, w, 4) int32 arrays; the new destination array is returned.
    """
    if not s_alpha:
        s = s.copy()
        s[..., 3] = 255
    if flags == 0:
        sa = s[..., 3:4]
        if colorkey is not None:
            key = np.all(s[..., :3] == np.array(colorkey[:3], dtype=np.int32), axis=-1, keepdims=True)
            sa = np.where(key, 0, sa)
        if surf_alpha is not None and surf_alpha < 255:
            sa = sa * surf_alpha // 255
        elif not s_alpha:
            # Opaque copy; colorkey pixels are skipped.
            out = d.copy()
            m = sa[..., 0] > 0
            out[m] = s[m]
            if not d_alpha:
                out[..., 3] = 255
            return out
        rgb = d[..., :3] + ((((s[..., :3] - d[..., :3]) * sa) + s[..., :3]) >> 8)
        if d_alpha:
            da = d[..., 3:4]
            a = sa + da - (sa * da) // 255
            empty = da == 0
            rgb = np.where(empty, s[..., :3], rgb)
            a = np.where(empty, sa, a)
        else:
            a = np.full_like(sa, 255)
        return np.clip(np.concatenate([rgb, a], axis=-1), 0, 255)
    if flags == BLEND_PREMULTIPLIED:
        sa = s[..., 3:4]
        rgb = s[..., :3] + d[..., :3] * (255 - sa) // 255
        a = sa + d[..., 3:4] * (255 - sa) // 255 if d_alpha else np.full_like(sa, 255)
        return np.clip(np.concatenate([rgb, a], axis=-1), 0, 255)
    op = _BLEND_OPS.get(flags)
    if op is None:
        raise error("unsupported blend flag %r" % (flags,))
    n = 4 if flags in _RGBA_FLAGS else 3
    a, b = d[..., :n], s[..., :n]
    if op == "add":
        r = np.minimum(a + b, 255)
    elif op == "sub":
        r = np.maximum(a - b, 0)
    elif op == "mult":
        r = (a * b + 255) >> 8
    elif op == "min":
        r = np.minimum(a, b)
    else:
        r = np.maximum(a, b)
    out = d.copy()
    out[..., :n] = r
    if not d_alpha:
        out[..., 3] = 255
    return out


# ------------------------------------------------------------------ Surface
class Surface:
    """An RGBA Pillow image plus pygame-like surface state."""

    def __init__(self, size, flags=0, depth=32, masks=None, _img=None):
        w, h = int(size[0]), int(size[1])
        if w < 0 or h < 0:
            raise error("Invalid resolution for Surface")
        self._flags = int(flags)
        self._has_alpha = bool(self._flags & SRCALPHA)
        self._surf_alpha = None
        self._colorkey = None
        if _img is None:
            _img = Image.new("RGBA", (w, h), (0, 0, 0, 0 if self._has_alpha else 255))
        self._img = _img

    def __repr__(self):
        w, h = self._img.size
        return "<Surface(%dx%dx32%s)>" % (w, h, " SRCALPHA" if self._has_alpha else "")

    # ---- info
    def get_size(self):
        return self._img.size

    def get_width(self):
        return self._img.size[0]

    def get_height(self):
        return self._img.size[1]

    def get_rect(self, **kw):
        r = Rect(0, 0, *self._img.size)
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def get_flags(self):
        return self._flags

    def get_bitsize(self):
        return 32

    def get_bytesize(self):
        return 4

    def lock(self):
        pass

    def unlock(self):
        pass

    def get_locked(self):
        return False

    # ---- copies / conversion
    def _clone(self, img, flags=None):
        s = Surface(img.size, self._flags if flags is None else flags, _img=img)
        s._surf_alpha, s._colorkey = self._surf_alpha, self._colorkey
        return s

    def copy(self):
        return self._clone(self._img.copy())

    def convert(self, *args):
        img = self._img.copy()
        img.putalpha(255)
        return self._clone(img, self._flags & ~SRCALPHA)

    def convert_alpha(self, *args):
        return self._clone(self._img.copy(), self._flags | SRCALPHA)

    def subsurface(self, *rect):
        r = Rect(*rect)
        if not self.get_rect().contains(r):
            raise ValueError("subsurface rectangle outside surface area")
        return self._clone(self._img.crop((r.x, r.y, r.right, r.bottom)))  # a copy, not a view

    # ---- alpha / colorkey
    def set_alpha(self, value, flags=0):
        self._surf_alpha = None if value is None else max(0, min(255, int(value)))

    def get_alpha(self):
        if self._surf_alpha is not None:
            return self._surf_alpha
        return 255 if self._has_alpha else None

    def set_colorkey(self, color=None, flags=0):
        self._colorkey = None if color is None else _rgba(color)

    def get_colorkey(self):
        return None if self._colorkey is None else Color(*self._colorkey)

    # ---- pixels
    def get_at(self, pos):
        x, y = int(pos[0]), int(pos[1])
        if not (0 <= x < self._img.size[0] and 0 <= y < self._img.size[1]):
            raise IndexError("pixel index out of range")
        return Color(*self._img.getpixel((x, y)))

    def set_at(self, pos, color):
        x, y = int(pos[0]), int(pos[1])
        if 0 <= x < self._img.size[0] and 0 <= y < self._img.size[1]:
            c = _rgba(color)
            self._img.putpixel((x, y), c if self._has_alpha else c[:3] + (255,))

    def _clip_box(self, rect):
        r = self.get_rect() if rect is None else Rect(rect).clip(self.get_rect())
        if r.w <= 0 or r.h <= 0:
            return None
        return (r.x, r.y, r.right, r.bottom)

    def fill(self, color, rect=None, special_flags=0):
        c = _rgba(color)
        if not self._has_alpha:
            c = c[:3] + (255,)
        box = self._clip_box(rect)
        if box is None:
            return Rect(0, 0, 0, 0)
        if special_flags:
            d = np.asarray(self._img.crop(box), dtype=np.int32)
            s = np.empty_like(d)
            s[...] = c
            out = _blend(d, s, special_flags, True, self._has_alpha, None, None)
            self._img.paste(Image.fromarray(out.astype(np.uint8), "RGBA"), box[:2])
        else:
            self._img.paste(c, box)
        return Rect(box[0], box[1], box[2] - box[0], box[3] - box[1])

    def blit(self, source, dest=(0, 0), area=None, special_flags=0):
        if isinstance(dest, Rect):
            dx, dy = dest.x, dest.y
        else:
            dx, dy = int(dest[0]), int(dest[1])
        sw, sh = source._img.size
        if area is None:
            ax, ay, aw, ah = 0, 0, sw, sh
        else:
            ax, ay, aw, ah = Rect(area)
            if ax < 0:
                dx, aw, ax = dx - ax, aw + ax, 0
            if ay < 0:
                dy, ah, ay = dy - ay, ah + ay, 0
            aw, ah = min(aw, sw - ax), min(ah, sh - ay)
        x0, y0 = max(dx, 0), max(dy, 0)
        x1 = min(dx + aw, self._img.size[0])
        y1 = min(dy + ah, self._img.size[1])
        if x1 <= x0 or y1 <= y0:
            return Rect(dx, dy, 0, 0)
        sx0, sy0 = ax + (x0 - dx), ay + (y0 - dy)
        src = source._img.crop((sx0, sy0, sx0 + (x1 - x0), sy0 + (y1 - y0)))
        plain = (special_flags == 0 and not source._has_alpha
                 and source._surf_alpha is None and source._colorkey is None)
        if plain:
            self._img.paste(src, (x0, y0))
        else:
            d = np.asarray(self._img.crop((x0, y0, x1, y1)), dtype=np.int32)
            s = np.asarray(src, dtype=np.int32)
            out = _blend(d, s, special_flags, source._has_alpha, self._has_alpha,
                         source._surf_alpha, source._colorkey)
            self._img.paste(Image.fromarray(out.astype(np.uint8), "RGBA"), (x0, y0))
        return Rect(x0, y0, x1 - x0, y1 - y0)

    def blits(self, blit_sequence, doreturn=1):
        out = [self.blit(*item) for item in blit_sequence]
        return out if doreturn else None

    def get_bounding_rect(self, min_alpha=1):
        if not self._has_alpha:
            return self.get_rect()
        a = np.asarray(self._img, dtype=np.uint8)[..., 3]
        ys, xs = np.nonzero(a >= min_alpha)
        if len(xs) == 0:
            return Rect(0, 0, 0, 0)
        return Rect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))


# ------------------------------------------------------------------ package API
_initialized = False


def init():
    global _initialized
    _initialized = True
    display.init()
    font.init()
    return (6, 0)


def quit():  # noqa: A001 - same name as pygame.quit
    global _initialized
    _initialized = False
    font.quit()
    display.quit()


def get_init():
    return _initialized


def get_sdl_version(linked=True):
    return (2, 28, 0)


from . import (display, draw, event, font, image, key, locals, mixer, mouse,  # noqa: E402
               time, transform, version)
from .event import Event  # noqa: E402

__version__ = version.ver
