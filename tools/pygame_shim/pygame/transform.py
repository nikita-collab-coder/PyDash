"""pygame.transform emulation."""
from PIL import Image

from . import SRCALPHA, Surface


def _wrap(src, img, flags=None):
    s = Surface(img.size, src._flags if flags is None else flags, _img=img)
    s._colorkey, s._surf_alpha = src._colorkey, src._surf_alpha
    return s


def _resize(surface, size, resample):
    w, h = int(size[0]), int(size[1])
    if w < 0 or h < 0:
        raise ValueError("Cannot scale to negative size")
    if w == 0 or h == 0 or surface.get_width() == 0 or surface.get_height() == 0:
        blank = Image.new("RGBA", (w, h), (0, 0, 0, 0 if surface._has_alpha else 255))
        return _wrap(surface, blank)
    return _wrap(surface, surface._img.resize((w, h), resample))


def scale(surface, size, dest_surface=None):
    return _resize(surface, size, Image.NEAREST)


def smoothscale(surface, size, dest_surface=None):
    return _resize(surface, size, Image.BILINEAR)


def _factor(surface, factor):
    fx, fy = (factor, factor) if isinstance(factor, (int, float)) else factor
    return surface.get_width() * fx, surface.get_height() * fy


def scale_by(surface, factor, dest_surface=None):
    return scale(surface, _factor(surface, factor))


def smoothscale_by(surface, factor, dest_surface=None):
    return smoothscale(surface, _factor(surface, factor))


def rotate(surface, angle):
    """Counter-clockwise rotation without filtering (like pygame.transform.rotate)."""
    if surface._has_alpha:
        fill = (0, 0, 0, 0)
    elif surface._colorkey is not None:
        fill = surface._colorkey
    elif surface.get_width() and surface.get_height():
        fill = surface._img.getpixel((0, 0))
    else:
        fill = (0, 0, 0, 255)
    img = surface._img.rotate(angle, resample=Image.NEAREST, expand=True, fillcolor=fill)
    return _wrap(surface, img)


def rotozoom(surface, angle, scale_factor):
    """Filtered rotate + scale; the result always has per-pixel alpha."""
    img = surface._img
    if scale_factor != 1:
        w = max(1, int(round(img.size[0] * scale_factor)))
        h = max(1, int(round(img.size[1] * scale_factor)))
        img = img.resize((w, h), Image.BICUBIC)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
    return _wrap(surface, img, surface._flags | SRCALPHA)


def flip(surface, flip_x, flip_y):
    img = surface._img.copy()
    if flip_x:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if flip_y:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    return _wrap(surface, img)
