"""Player icons (16 sharp cube designs, two colours each), the ship, and cached
smooth sprites for level objects. Cube designs use a 0..100 unit square.
"""
from . import config as C
from . import gfx

OUT = C.OUTLINE
WHITE = (255, 255, 255)


class Pen:
    """Draws in 0..100 design units onto a canvas region."""

    def __init__(self, cv, k, ox=0.0, oy=0.0):
        self.cv, self.k, self.ox, self.oy = cv, k, ox, oy

    def pts(self, pts):
        return [(self.ox + x * self.k, self.oy + y * self.k) for x, y in pts]

    def box(self, color, x, y, w, h):
        self.cv.rect(color, self.ox + x * self.k, self.oy + y * self.k, w * self.k, h * self.k)

    def boxed(self, color, x, y, w, h, t):
        self.box(OUT, x - t, y - t, w + 2 * t, h + 2 * t)
        self.box(color, x, y, w, h)

    def poly(self, color, pts):
        self.cv.poly(color, self.pts(pts))

    def shapes(self, shapes, t):
        self.cv.shapes([(c, self.pts(p)) for c, p in shapes], t * self.k)

    def circle(self, color, x, y, r):
        self.cv.circle(color, (self.ox + x * self.k, self.oy + y * self.k), r * self.k)


def _classic(p, c1, c2):
    p.box(OUT, 24, 24, 52, 52)
    p.box(c2, 30, 30, 40, 40)
    p.box(OUT, 38, 38, 24, 24)
    p.box(c1, 43, 43, 14, 14)


def _visor(p, c1, c2):
    p.boxed(c2, 20, 30, 60, 17, 5)
    p.box(OUT, 34, 62, 32, 9)


def _dots(p, c1, c2):
    for x in (22, 58):
        p.box(OUT, x, 24, 20, 24)
        p.box(c2, x + 4, 28, 8, 8)
    p.box(OUT, 24, 63, 52, 10)


def _smile(p, c1, c2):
    for x in (27, 61):
        p.boxed(c2, x, 24, 12, 18, 4)
    p.poly(OUT, gfx.stroke_poly(gfx.arc_pts(50, 46, 27, 25, 155, steps=12), 9))


def _cross(p, c1, c2):
    p.shapes([(c2, gfx.stroke_poly([(22, 22), (78, 78)], 15)), (c2, gfx.stroke_poly([(78, 22), (22, 78)], 15))], 5)
    p.box(OUT, 36, 36, 28, 28)
    p.box(c1, 42, 42, 16, 16)


def _diamond(p, c1, c2):
    p.shapes([(c2, [(50, 16), (84, 50), (50, 84), (16, 50)])], 5)
    p.shapes([(c1, [(50, 36), (64, 50), (50, 64), (36, 50)])], 4)


def _corners(p, c1, c2):
    for x in (15, 67):
        for y in (15, 67):
            p.boxed(c2, x, y, 18, 18, 5)
    p.boxed(c2, 42, 42, 16, 16, 5)


def _plus(p, c1, c2):
    a, lo, hi = 10, 18, 82
    p.shapes([(c2, [(50 - a, lo), (50 + a, lo), (50 + a, 50 - a), (hi, 50 - a), (hi, 50 + a), (50 + a, 50 + a),
                    (50 + a, hi), (50 - a, hi), (50 - a, 50 + a), (lo, 50 + a), (lo, 50 - a), (50 - a, 50 - a)])], 5)


def _split(p, c1, c2):
    p.poly(c2, [(92, 8), (92, 92), (8, 92)])
    p.poly(OUT, gfx.stroke_poly([(4, 96), (96, 4)], 6))
    p.boxed(c2, 22, 22, 18, 18, 5)
    p.boxed(c1, 60, 60, 18, 18, 5)


def _stripes(p, c1, c2):
    for x in (17, 43, 69):
        p.boxed(c2, x, 16, 14, 68, 4)


def _target(p, c1, c2):
    for r, col in ((36, OUT), (31, c2), (21, OUT), (16, c1), (7, OUT)):
        p.circle(col, 50, 50, r)


def _robot(p, c1, c2):
    for x in (18, 56):
        p.boxed(c2, x, 22, 26, 20, 4)
        p.box(OUT, x + 9, 27, 8, 10)
    p.box(OUT, 22, 56, 56, 22)
    for i in range(4):
        p.box(c2, 26 + i * 13, 60, 9, 14)


def _checker(p, c1, c2):
    p.box(OUT, 12.5, 12.5, 75, 75)
    cell = 70 / 3.0
    for i in range(3):
        for j in range(3):
            p.box(c2 if (i + j) % 2 == 0 else c1, 15 + i * cell + 2.5, 15 + j * cell + 2.5, cell - 5, cell - 5)


def _arrows(p, c1, c2):
    p.shapes([(c2, gfx.stroke_poly([(24, 26), (46, 50), (24, 74)], 12)),
              (c2, gfx.stroke_poly([(50, 26), (72, 50), (50, 74)], 12))], 4.5)


def _grin(p, c1, c2):
    p.shapes([(c2, [(18, 28), (44, 38), (44, 48), (18, 48)]), (c2, [(82, 28), (56, 38), (56, 48), (82, 48)])], 4.5)
    p.box(OUT, 18, 58, 64, 22)
    step = 56 / 6.0
    for i in range(6):
        x0 = 22 + i * step
        p.poly(WHITE, [(x0, 62), (x0 + step, 62), (x0 + step / 2, 71)])


def _window(p, c1, c2):
    p.box(OUT, 15, 15, 70, 70)
    for x in (20, 52.5):
        for y in (20, 52.5):
            p.box(c2, x, y, 27.5, 27.5)


DESIGNS = {"classic": _classic, "visor": _visor, "dots": _dots, "smile": _smile, "cross": _cross,
           "diamond": _diamond, "corners": _corners, "plus": _plus, "split": _split, "stripes": _stripes,
           "target": _target, "robot": _robot, "checker": _checker, "arrows": _arrows, "grin": _grin,
           "window": _window}


def draw_cube(p, design, c1, c2):
    """Sharp square: thick dark frame, c1 body, c2 details. No rounded corners."""
    p.box(OUT, 0, 0, 100, 100)
    p.box(c1, 8, 8, 84, 84)
    DESIGNS.get(design, _classic)(p, c1, c2)


def cube(design, c1, c2, size):
    size = max(8, int(round(size)))
    c1, c2 = gfx.rgb(c1), gfx.rgb(c2)

    def build():
        cv = gfx.Canvas(size, size)
        draw_cube(Pen(cv, size / 100.0), design, c1, c2)
        return cv.done()
    return gfx.cached(("cube", design, c1, c2, size), build)


def ship(design, c1, c2, u):
    """Ship image of 1.6u x 1.1u with the cube as its pilot."""
    u = max(8, int(round(u)))
    c1, c2 = gfx.rgb(c1), gfx.rgb(c2)

    def build():
        cv = gfx.Canvas(1.6 * u, 1.1 * u)
        t = max(1.5, u * 0.06)
        draw_cube(Pen(cv, u * 0.005, 0.52 * u, 0.03 * u), design, c1, c2)

        def P(pts):
            return [(x * u, y * u) for x, y in pts]
        hull = [(0.06, 0.5), (0.4, 0.42), (1.1, 0.42), (1.48, 0.7), (1.14, 1.0), (0.3, 1.02), (0.06, 0.86)]
        fin = [(0.12, 0.52), (0.1, 0.26), (0.4, 0.44)]
        cv.shapes([(c2, P(fin)), (c1, P(hull))], t)
        cv.shapes([(c2, P([(0.26, 0.66), (1.24, 0.68), (1.1, 0.84), (0.26, 0.86)]))], t * 0.8)
        return cv.done()
    return gfx.cached(("ship", design, c1, c2, u), build)


def sprite(key, w, h, shapes, t, outline=OUT, clear=None):
    """Cached outlined polygons (sprite-local pixel coordinates). `key` must describe the art."""
    def build():
        cv = gfx.Canvas(w, h, clear=clear or outline)
        cv.shapes(shapes, t, outline)
        return cv.done()
    return gfx.cached(("sprite",) + tuple(key), build)


def art(key, w, h, paint, clear=OUT):
    """Cached free-form art: paint(canvas) draws it once."""
    def build():
        cv = gfx.Canvas(w, h, clear=clear)
        paint(cv)
        return cv.done()
    return gfx.cached(("art",) + tuple(key), build)


DEFAULTS = {"icon": 0, "color1": 0, "color2": 7}


def _index(settings, key, n):
    try:
        return int(settings.get(key, DEFAULTS[key])) % n
    except (TypeError, ValueError):
        return DEFAULTS[key] % n


def style(settings):
    """(design, primary colour, secondary colour) chosen on the Icons screen."""
    n = len(C.ICON_COLORS)
    return (C.ICON_DESIGNS[_index(settings, "icon", len(C.ICON_DESIGNS))],
            C.ICON_COLORS[_index(settings, "color1", n)], C.ICON_COLORS[_index(settings, "color2", n)])
