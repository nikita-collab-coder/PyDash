"""pygame.image emulation (PNG/JPG through Pillow)."""
from PIL import Image

from . import SRCALPHA, Surface, error


def save(surface, filename, namehint=""):
    img = surface._img if surface._has_alpha else surface._img.convert("RGB")
    img.save(filename)


def load(filename, namehint=""):
    try:
        img = Image.open(filename)
        img.load()
    except Exception as exc:  # pygame raises pygame.error for unreadable files
        raise error(str(exc))
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA")
    return Surface(img.size, SRCALPHA if has_alpha else 0, _img=img)


def tobytes(surface, format="RGBA", flipped=False):  # noqa: A002
    img = surface._img.transpose(Image.FLIP_TOP_BOTTOM) if flipped else surface._img
    return img.convert(format).tobytes()


tostring = tobytes


def frombytes(data, size, format, flipped=False):  # noqa: A002
    img = Image.frombytes(format, size, data).convert("RGBA")
    if flipped:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    return Surface(img.size, SRCALPHA if "A" in format else 0, _img=img)


fromstring = frombytes
