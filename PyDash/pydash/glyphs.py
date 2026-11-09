"""UI glyphs, difficulty faces, stars and coins, drawn with gfx (smooth, even outlines).

Glyph coordinates use a unit box from -1 to 1; `s` is pixels per unit, `t` is the
outline thickness in pixels. Multi-part glyphs share one outline.
"""
import math

from . import config as C
from . import gfx

OUT = C.OUTLINE
DIFFS = ("easy", "normal", "hard", "harder", "insane")


def _plus_pts(a=0.27, e=0.86):
    return [(-a, -e), (a, -e), (a, -a), (e, -a), (e, a), (a, a), (a, e), (-a, e), (-a, a), (-e, a), (-e, -a),
            (-a, -a)]


def _play(cv, P, s, col, t):
    cv.shapes([(col, P([(-0.55, -0.86), (0.95, 0.0), (-0.55, 0.86)]))], t)


def _pause(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.rect_pts(-0.7, -0.8, 0.48, 1.6))), (col, P(gfx.rect_pts(0.22, -0.8, 0.48, 1.6)))], t)


def _left(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.stroke_poly([(0.46, -0.8), (-0.3, 0.0), (0.46, 0.8)], 0.5)))], t)


def _back(cv, P, s, col, t):
    shaft = gfx.rect_pts(-0.2, -0.21, 1.0, 0.42)
    head = [(-0.88, 0.0), (-0.06, -0.74), (-0.06, 0.74)]
    cv.shapes([(col, P(shaft)), (col, P(head))], t)


def _right(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.stroke_poly([(-0.46, -0.8), (0.3, 0.0), (-0.46, 0.8)], 0.5)))], t)


def _plus(cv, P, s, col, t):
    cv.shapes([(col, P(_plus_pts()))], t)


def _close(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.move(_plus_pts(0.25, 0.98), rot=45)))], t)


def _home(cv, P, s, col, t):
    house = [(0.0, -0.92), (0.98, 0.02), (0.68, 0.02), (0.68, 0.88), (-0.68, 0.88), (-0.68, 0.02), (-0.98, 0.02)]
    cv.shapes([(col, P(gfx.rect_pts(0.4, -0.8, 0.26, 0.6))), (col, P(house))], t)
    cv.poly(OUT, P(gfx.rect_pts(-0.2, 0.34, 0.4, 0.56)))


def _retry(cv, P, s, col, t):
    r, a1 = 0.6, 250.0
    arc = gfx.stroke_poly(gfx.arc_pts(0.0, 0.0, r, -40.0, a1), 0.34)
    a = math.radians(a1)
    ex, ey, tx, ty, nx, ny = r * math.cos(a), r * math.sin(a), -math.sin(a), math.cos(a), math.cos(a), math.sin(a)
    head = [(ex + tx * 0.62, ey + ty * 0.62), (ex + nx * 0.47 - tx * 0.1, ey + ny * 0.47 - ty * 0.1),
            (ex - nx * 0.47 - tx * 0.1, ey - ny * 0.47 - ty * 0.1)]
    cv.shapes([(col, P(arc)), (col, P(head))], t)


def _edit(cv, P, s, col, t):
    w = 0.3

    def place(pts):
        return P(gfx.move([(u - 1.02, v) for u, v in pts], rot=-45))
    cv.shapes([((255, 214, 150), place([(0.0, 0.0), (0.52, -w), (0.52, w)])),
               (col, place(gfx.rect_pts(0.52, -w, 1.04, 2 * w))),
               ((176, 186, 210), place(gfx.rect_pts(1.56, -w, 0.16, 2 * w))),
               (C.PINK, place(gfx.rect_pts(1.72, -w, 0.32, 2 * w)))], t)
    cv.poly(C.shade(col, 0.8), place(gfx.rect_pts(0.52, w * 0.3, 1.04, w * 0.7)))
    cv.poly(OUT, place([(0.0, 0.0), (0.2, -w * 0.4), (0.2, w * 0.4)]))


def _trash(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.rect_pts(-0.24, -0.94, 0.48, 0.3))), (col, P(gfx.rect_pts(-0.82, -0.74, 1.64, 0.26))),
               (col, P([(-0.64, -0.4), (0.64, -0.4), (0.5, 0.9), (-0.5, 0.9)]))], t)
    for x in (-0.27, 0.0, 0.27):
        cv.poly(OUT, P(gfx.rect_pts(x - 0.06, -0.2, 0.12, 0.9)))


def _gear(cv, P, s, col, t):
    pts = []
    for i in range(8):
        a = i * 45.0
        for da, r in ((-15, 0.64), (-8, 0.96), (8, 0.96), (15, 0.64), (22.5, 0.64)):
            pts.append((r * math.cos(math.radians(a + da)), r * math.sin(math.radians(a + da))))
    cv.shapes([(col, P(pts))], t)
    cv.circle(OUT, P([(0, 0)])[0], 0.32 * s)
    cv.circle((0, 0, 0, 0), P([(0, 0)])[0], 0.32 * s - t)


def _check(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.stroke_poly([(-0.78, 0.0), (-0.26, 0.52), (0.8, -0.6)], 0.42)))], t)


def _star(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.star_pts(0.0, 0.06, 0.98, 0.47)))], t)


def _music(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.ellipse_pts(-0.46, 0.6, 0.3, 0.22, rot=-22, steps=28))),
               (col, P(gfx.ellipse_pts(0.5, 0.44, 0.3, 0.22, rot=-22, steps=28))),
               (col, P(gfx.rect_pts(-0.32, -0.62, 0.16, 1.14))),
               (col, P(gfx.rect_pts(0.62, -0.92, 0.16, 1.28))),
               (col, P([(-0.32, -0.62), (0.78, -0.92), (0.78, -0.62), (-0.32, -0.32)]))], t)


def _sound(cv, P, s, col, t):
    body = [(-0.92, -0.3), (-0.5, -0.3), (-0.04, -0.76), (-0.04, 0.76), (-0.5, 0.3), (-0.92, 0.3)]
    cv.shapes([(col, P(body)),
               (col, P(gfx.stroke_poly(gfx.arc_pts(-0.04, 0.0, 0.44, -50, 50), 0.18))),
               (col, P(gfx.stroke_poly(gfx.arc_pts(-0.04, 0.0, 0.8, -50, 50), 0.18)))], t)


def _flag(cv, P, s, col, t):
    top = [(-0.5 + 1.38 * k / 8, -0.86 + 0.1 * math.sin(k / 8 * 2 * math.pi)) for k in range(9)]
    bottom = [(x, y + 0.92) for x, y in reversed(top)]
    cv.shapes([(col, P(gfx.rect_pts(-0.72, -0.94, 0.18, 1.74))), (col, P(gfx.rect_pts(-0.92, 0.74, 0.58, 0.18))),
               (col, P(top + bottom))], t)


def _cube(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.rect_pts(-0.8, -0.8, 1.6, 1.6)))], t)
    cv.poly(OUT, P(gfx.rect_pts(-0.42, -0.42, 0.84, 0.84)))
    cv.poly(col, P(gfx.rect_pts(-0.24, -0.24, 0.48, 0.48)))


def _list(cv, P, s, col, t):
    shapes = []
    for y in (-0.62, 0.0, 0.62):
        shapes += [(col, P(gfx.rect_pts(-0.92, y - 0.18, 0.36, 0.36))), (col, P(gfx.rect_pts(-0.38, y - 0.14, 1.3, 0.28)))]
    cv.shapes(shapes, t)


def _dot(cv, P, s, col, t):
    cv.shapes([(col, P(gfx.ellipse_pts(0, 0, 0.6, 0.6)))], t)


GLYPHS = {"play": _play, "pause": _pause, "left": _left, "back": _back, "right": _right, "plus": _plus,
          "close": _close, "home": _home, "retry": _retry, "edit": _edit, "trash": _trash, "gear": _gear,
          "check": _check, "star": _star, "music": _music, "sound": _sound, "sfx": _sound, "flag": _flag,
          "cube": _cube, "list": _list}


def icon(name, size, color=C.WHITE):
    """A glyph image; `size` is the glyph height. Names ending in _off get a red slash."""
    size = max(8, int(round(size)))
    return gfx.cached(("icon", name, size, gfx.rgb(color)), lambda: _icon(name, size, gfx.rgb(color)))


def _icon(name, size, color):
    t = max(1.6, size * 0.075)
    pad = int(math.ceil(t + 2))
    full = size + pad * 2
    cv = gfx.Canvas(full, full)
    s, c = size / 2.0, full / 2.0

    def P(pts):
        return gfx.move(pts, s, c, c)
    off = name.endswith("_off")
    GLYPHS.get(name[:-4] if off else name, _dot)(cv, P, s, color, t)
    if off:
        a, b = (c - 0.8 * s, c - 0.8 * s), (c + 0.8 * s, c + 0.8 * s)
        cv.line(OUT, a, b, 0.2 * s + 2 * t)
        cv.line(C.RED, a, b, 0.2 * s)
    return cv.done()


# ---------------------------------------------------------------- faces
def face(difficulty, r):
    r = max(6, int(round(r)))
    return gfx.cached(("face", difficulty, r), lambda: _face(difficulty, r))


def _face(difficulty, r):
    level = DIFFS.index(difficulty) if difficulty in DIFFS else 1
    col = gfx.rgb(C.DIFFICULTY_COLORS.get(difficulty, C.GRAY))
    t = max(2.0, r * 0.09)
    size = 2 * (r + int(r * 0.5) + 2)
    cv = gfx.Canvas(size, size)
    c = size / 2.0
    s = float(r)

    def P(pts):
        return gfx.move(pts, s, c, c)

    def at(x, y):
        return c + x * s, c + y * s
    if level >= 4:
        for k in (-1, 1):
            cv.shapes([(C.shade(col, 0.72), P([(k * 0.4, -0.8), (k * 0.95, -1.34), (k * 0.82, -0.46)]))], t)
    cv.circle(OUT, (c, c), s + t)
    cv.circle(C.shade(col, 0.76), (c, c), s)
    cv.circle(col, at(0, -0.06), s * 0.94)
    cv.poly(C.lerp_color(col, C.WHITE, 0.5), P(gfx.ellipse_pts(-0.44, -0.56, 0.24, 0.12, rot=-35, steps=24)))
    for k in (-1, 1):
        ex, ey = k * 0.36, -0.12
        cv.shapes([(C.WHITE, P(gfx.ellipse_pts(ex, ey, 0.2, 0.25, steps=32)))], t * 0.8)
        if level >= 4:
            cv.circle(OUT, at(ex, ey + 0.04), 0.13 * s)
            cv.circle((226, 28, 48), at(ex, ey + 0.04), 0.085 * s)
        else:
            cv.circle(OUT, at(ex, ey + 0.04), 0.11 * s)
        cv.circle(C.WHITE, at(ex - 0.035, ey), 0.035 * s)
    if level >= 2:
        tilt = (0, 0, 0.08, 0.16, 0.24)[level]
        for k in (-1, 1):
            cv.line(OUT, at(k * 0.62, -0.52 - tilt * 0.25), at(k * 0.14, -0.42 + tilt), 0.13 * s)
    if level == 0:
        cv.poly(OUT, P([(-0.44, 0.22)] + gfx.arc_pts(0.0, 0.22, 0.44, 180, 0) + [(0.44, 0.22)]))
        cv.poly((255, 118, 150), P(gfx.ellipse_pts(0.0, 0.5, 0.17, 0.09, steps=24)))
    elif level == 1:
        cv.stroke(OUT, P(gfx.arc_pts(0.0, 0.12, 0.38, 30, 150)), 0.13 * s)
    elif level == 2:
        cv.line(OUT, at(-0.26, 0.48), at(0.26, 0.45), 0.13 * s)
    elif level == 3:
        cv.stroke(OUT, P(gfx.arc_pts(0.0, 0.82, 0.36, 215, 325)), 0.13 * s)
    else:
        cv.poly(OUT, P([(-0.48, 0.28), (0.48, 0.28), (0.3, 0.64), (-0.3, 0.64)]))
        for i in range(4):
            x0 = -0.4 + i * 0.2
            cv.poly(C.WHITE, P([(x0, 0.3), (x0 + 0.2, 0.3), (x0 + 0.1, 0.43)]))
    return cv.done()


# ---------------------------------------------------------------- stars and coins
def star(r, filled=True, color=C.GOLD):
    r = max(4, int(round(r)))
    return gfx.cached(("star", r, bool(filled), gfx.rgb(color)), lambda: _star_img(r, filled, gfx.rgb(color)))


def _star_img(r, filled, color):
    t = max(2.0, r * 0.13)
    size = 2 * (r + int(t * 2.6) + 2)
    cv = gfx.Canvas(size, size)
    c = size / 2.0
    col = color if filled else (40, 44, 70)
    cv.shapes([(col, gfx.star_pts(c, c + r * 0.06, r, r * 0.48))], t)
    inner = C.lerp_color(col, C.WHITE, 0.32) if filled else (58, 64, 96)
    cv.poly(inner, gfx.star_pts(c, c + r * 0.06, r * 0.52, r * 0.25))
    return cv.done()


def coin(r, got):
    r = max(4, int(round(r)))
    return gfx.cached(("coin", r, bool(got)), lambda: _coin(r, got))


def _coin(r, got):
    t = max(2.0, r * 0.13)
    size = 2 * (r + int(t) + 2)
    cv = gfx.Canvas(size, size)
    c = (size / 2.0, size / 2.0)
    rim, ring, face_col = ((255, 212, 60), (206, 140, 26), (255, 196, 40)) if got else \
        ((76, 84, 118), (40, 44, 70), (52, 58, 88))
    cv.circle(OUT, c, r + t)
    cv.circle(rim, c, r)
    cv.circle(ring, c, r * 0.76)
    cv.circle(face_col, c, r * 0.62)
    cv.poly(ring, gfx.star_pts(c[0], c[1] + r * 0.03, r * 0.42, r * 0.2))
    if got:
        cv.poly((255, 250, 220), gfx.ellipse_pts(c[0] - r * 0.42, c[1] - r * 0.44, r * 0.2, r * 0.1, rot=-40,
                                                 steps=20))
    return cv.done()
