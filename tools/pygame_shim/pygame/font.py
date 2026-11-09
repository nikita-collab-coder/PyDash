"""pygame.font emulation on top of Pillow's FreeType bindings."""
import math
import os

from PIL import Image, ImageDraw, ImageFont

from . import SRCALPHA, Surface, _rgba, error

_CANDIDATES = [
    "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/google-droid-sans-fonts/DroidSans-Bold.ttf",
]
_DEFAULT = next((p for p in _CANDIDATES if os.path.exists(p)), None)
_init = False


def init():
    global _init
    _init = True


def quit():  # noqa: A001
    global _init
    _init = False


def get_init():
    return _init


def get_default_font():
    return "freesansbold.ttf"


def get_fonts():
    return ["liberationsans"]


def match_font(name, bold=False, italic=False):
    return _DEFAULT


class Font:
    def __init__(self, file=None, size=20):
        if not _init:
            raise error("font not initialized")
        path = _DEFAULT if file in (None, "freesansbold.ttf") else file
        if isinstance(path, str) and not os.path.exists(path):
            raise FileNotFoundError("No file '%s' found in working directory '%s'." % (path, os.getcwd()))
        self._size = max(1, int(size))
        self._font = ImageFont.truetype(path, self._size)
        self._ascent, self._descent = self._font.getmetrics()
        self._bold = self._italic = self._underline = False

    # ---- metrics
    def size(self, text):
        return (int(math.ceil(self._font.getlength(text))) if text else 0, self.get_height())

    def get_height(self):
        return self._ascent + self._descent

    def get_linesize(self):
        return self._ascent + self._descent

    def get_ascent(self):
        return self._ascent

    def get_descent(self):
        return -self._descent

    # ---- style flags (accepted, ignored)
    def set_bold(self, value):
        self._bold = bool(value)

    def get_bold(self):
        return self._bold

    def set_italic(self, value):
        self._italic = bool(value)

    def get_italic(self):
        return self._italic

    def set_underline(self, value):
        self._underline = bool(value)

    def get_underline(self):
        return self._underline

    # ---- rendering
    def render(self, text, antialias, color, background=None):
        if text is None:
            text = ""
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        if not isinstance(text, str):
            raise TypeError("text must be a unicode or bytes")
        if "\x00" in text:
            raise ValueError("A null character was found in the text")
        c = _rgba(color)
        w, h = self.size(text)
        mask = Image.new("L", (w, h), 0)
        if w:
            ImageDraw.Draw(mask).text((0, 0), text, font=self._font, fill=255, anchor="la")
        if not antialias:
            mask = mask.point(lambda v: 255 if v >= 128 else 0)
        if c[3] != 255:
            mask = mask.point(lambda v: v * c[3] // 255)
        img = Image.new("RGBA", (w, h), c[:3] + (0,))
        img.putalpha(mask)
        if background is None:
            return Surface((w, h), SRCALPHA, _img=img)
        bg = Image.new("RGBA", (w, h), _rgba(background)[:3] + (255,))
        bg.alpha_composite(img)
        return Surface((w, h), 0, _img=bg)


def SysFont(name, size, bold=False, italic=False):
    f = Font(None, size)
    f.set_bold(bold)
    f.set_italic(italic)
    return f
