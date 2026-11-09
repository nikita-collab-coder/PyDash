"""Anti-aliased vector drawing.

pygame's draw functions are not anti-aliased, and their thick lines and outlines
change thickness with the angle, which makes icons look crooked. Everything here is
drawn with filled shapes only, at 4x size, and then shrunk with smoothscale. That
gives smooth edges and even outlines. Finished images are cached, so each one is
drawn only once.
"""
import math

import pygame

from . import config as C

OUT = C.OUTLINE
CACHE_LIMIT = 1500
_cache = {}


def cached(key, build):
    img = _cache.get(key)
    if img is None:
        if len(_cache) >= CACHE_LIMIT:
            _cache.clear()
        img = _cache[key] = build()
    return img


def rgb(color):
    return int(color[0]), int(color[1]), int(color[2])


# ---------------------------------------------------------------- geometry
def _unit(dx, dy):
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d


def area(pts):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def grow(pts, d, limit=2.4):
    """Grow a simple polygon by d with sharp (mitred) corners.

    Corners sharper than the mitre limit are bevelled; their positions are returned
    as `tips` so the caller can round them off with a circle."""
    if d <= 0:
        return list(pts), []
    sign = 1.0 if area(pts) > 0 else -1.0
    n = len(pts)
    out, tips = [], []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[(i + 1) % n]
        ax, ay = _unit(x1 - x0, y1 - y0)
        bx, by = _unit(x2 - x1, y2 - y1)
        n1x, n1y = ay * sign, -ax * sign
        n2x, n2y = by * sign, -bx * sign
        dot = n1x * n2x + n1y * n2y
        if 1 + dot < 2.0 / (limit * limit):
            out.append((x1 + n1x * d, y1 + n1y * d))
            out.append((x1 + n2x * d, y1 + n2y * d))
            tips.append((x1, y1))
        else:
            k = d / (1 + dot)
            out.append((x1 + (n1x + n2x) * k, y1 + (n1y + n2y) * k))
    return out, tips


def stroke_poly(pts, width):
    """Polygon of a thick polyline with sharp mitred joins and flat ends."""
    h = width / 2.0
    left, right = [], []
    n = len(pts)
    for i in range(n):
        x, y = pts[i]
        if i == 0 or i == n - 1:
            (ax, ay), (bx, by) = (pts[0], pts[1]) if i == 0 else (pts[i - 1], pts[i])
            dx, dy = _unit(bx - ax, by - ay)
            mx, my = -dy, dx
        else:
            ax, ay = _unit(x - pts[i - 1][0], y - pts[i - 1][1])
            bx, by = _unit(pts[i + 1][0] - x, pts[i + 1][1] - y)
            n1x, n1y, n2x, n2y = -ay, ax, -by, bx
            dot = max(-0.8, n1x * n2x + n1y * n2y)
            mx, my = (n1x + n2x) / (1 + dot), (n1y + n2y) / (1 + dot)
        left.append((x + mx * h, y + my * h))
        right.append((x - mx * h, y - my * h))
    return left + right[::-1]


def arc_pts(cx, cy, r, a0, a1, steps=None):
    """Points on a circular arc. Angles in degrees: 0 = right, 90 = down."""
    steps = steps or max(6, int(abs(a1 - a0) / 5))
    out = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def ellipse_pts(cx, cy, rx, ry, rot=0.0, steps=48):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for i in range(steps):
        a = 2 * math.pi * i / steps
        x, y = math.cos(a) * rx, math.sin(a) * ry
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def star_pts(cx, cy, r_out, r_in, n=5, rot=-90.0):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180.0 / n)
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def rect_pts(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def move(pts, scale=1.0, dx=0.0, dy=0.0, rot=0.0):
    """Rotate (degrees, clockwise on screen), scale, then shift a list of points."""
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [((x * c - y * s) * scale + dx, (x * s + y * c) * scale + dy) for x, y in pts]


# ---------------------------------------------------------------- canvas
class Canvas:
    """An oversized drawing surface. Coordinates and sizes are in final pixels."""

    def __init__(self, w, h, clear=OUT, ss=None):
        self.w, self.h = max(1, int(math.ceil(w))), max(1, int(math.ceil(h)))
        self.ss = ss or (4 if self.w * self.h <= 160000 else 2)
        self.surf = pygame.Surface((self.w * self.ss, self.h * self.ss), pygame.SRCALPHA)
        self.surf.fill((clear[0], clear[1], clear[2], 0))

    def _p(self, x, y):
        return int(round(x * self.ss)), int(round(y * self.ss))

    def _r(self, x, y, w, h):
        x0, y0 = self._p(x, y)
        x1, y1 = self._p(x + w, y + h)
        return pygame.Rect(x0, y0, max(1, x1 - x0), max(1, y1 - y0))

    def poly(self, color, pts):
        if len(pts) >= 3:
            pygame.draw.polygon(self.surf, color, [self._p(x, y) for x, y in pts])

    def circle(self, color, center, r):
        if r > 0:
            pygame.draw.circle(self.surf, color, self._p(*center), max(1, int(round(r * self.ss))))

    def ellipse(self, color, x, y, w, h):
        if w > 0 and h > 0:
            pygame.draw.ellipse(self.surf, color, self._r(x, y, w, h))

    def rect(self, color, x, y, w, h, r=0.0):
        if w <= 0 or h <= 0:
            return
        box = self._r(x, y, w, h)
        rad = int(round(max(0.0, min(r, w / 2.0, h / 2.0)) * self.ss))
        if rad > 0:
            pygame.draw.rect(self.surf, color, box, border_radius=rad)
        else:
            pygame.draw.rect(self.surf, color, box)

    def line(self, color, a, b, width, caps=True):
        """A thick line as a filled quad, optionally with round caps."""
        (x0, y0), (x1, y1) = a, b
        dx, dy = _unit(x1 - x0, y1 - y0)
        h = width / 2.0
        nx, ny = -dy * h, dx * h
        self.poly(color, [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])
        if caps:
            self.circle(color, a, h)
            self.circle(color, b, h)

    def stroke(self, color, pts, width, closed=False):
        """A polyline with round joins and round caps."""
        n = len(pts)
        for i in range(n if closed else n - 1):
            self.line(color, pts[i], pts[(i + 1) % n], width, caps=False)
        for p in pts:
            self.circle(color, p, width / 2.0)

    def shapes(self, shapes, t, outline=OUT):
        """Polygons that share one outline: every outline first, then every fill."""
        for _color, pts in shapes:
            big, tips = grow(pts, t)
            self.poly(outline, big)
            for p in tips:
                self.circle(outline, p, t)
        for color, pts in shapes:
            self.poly(color, pts)

    def boxed(self, color, x, y, w, h, t, outline=OUT):
        """A sharp-cornered rectangle with an outline of thickness t around it."""
        self.rect(outline, x - t, y - t, w + 2 * t, h + 2 * t)
        self.rect(color, x, y, w, h)

    def done(self):
        return pygame.transform.smoothscale(self.surf, (self.w, self.h))


# ---------------------------------------------------------------- UI pieces
def button(w, h, color, state="normal"):
    """Arcade button: soft drop shadow, dark outline, 3D lip and a glossy top.

    Returns (image, face) where face is the label area inside the image. The image
    is 2 px larger than the button on every side and has the shadow underneath."""
    return cached(("button", w, h, rgb(color), state), lambda: _button(w, h, rgb(color), state))


def _button(w, h, color, state):
    pad, drop = 2, 5
    cv = Canvas(w + pad * 2, h + pad * 2 + drop)
    t = 3.5 if h >= 48 else 3.0
    rad = max(7.0, min(18.0, h * 0.26))
    lip = max(4.0, min(9.0, h * 0.1))
    sink = 0.0
    if state == "pressed":
        sink, lip = lip * 0.6, lip * 0.4
    body = C.lerp_color(color, C.WHITE, 0.14) if state == "hover" else color
    x, y, hh = pad, pad + sink, h - sink
    cv.rect((OUT[0], OUT[1], OUT[2], 100), x, y + drop - sink, w, hh, rad)
    cv.rect(OUT, x, y, w, hh, rad)
    cv.rect(C.shade(body, 0.62), x + t, y + t, w - 2 * t, hh - 2 * t, rad - t)
    face_h = hh - 2 * t - lip
    cv.rect(body, x + t, y + t, w - 2 * t, face_h, rad - t)
    gloss_h = max(3.0, face_h * 0.28)
    inset = max(6.0, rad * 0.6)
    cv.rect(C.lerp_color(body, C.WHITE, 0.3), x + t + inset, y + t + 2.5, w - 2 * t - 2 * inset, gloss_h,
            gloss_h / 2)
    face = pygame.Rect(int(x + t), int(y + t), int(w - 2 * t), int(face_h))
    return cv.done(), face


def panel(w, h, color, edge, alpha, radius):
    def build():
        cv = Canvas(w, h, clear=edge)
        cv.rect(rgb(edge), 0, 0, w, h, radius)
        cv.rect((color[0], color[1], color[2], int(alpha)), 4, 4, w - 8, h - 8, max(0, radius - 4))
        return cv.done()
    return cached(("panel", w, h, rgb(color), rgb(edge), int(alpha), radius), build)


def bar_frame(w, h):
    def build():
        cv = Canvas(w + 8, h + 8)
        cv.rect(OUT, 0, 0, w + 8, h + 8, h / 2.0 + 4)
        cv.rect((42, 46, 78), 4, 4, w, h, h / 2.0)
        return cv.done()
    return cached(("barframe", w, h), build)


def bar_fill(w, h, color):
    def build():
        cv = Canvas(w, h, clear=color)
        cv.rect(rgb(color), 0, 0, w, h, h / 2.0)
        cv.rect(C.shade(color, 1.35), h * 0.4, h * 0.15, w - h * 0.8, max(2.0, h * 0.2), h * 0.1)
        return cv.done()
    return cached(("barfill", w, h, rgb(color)), build)


def frame(w, h, color, t=3.0, radius=10.0, fill=None):
    """A rounded frame (selection highlight); `fill` optionally fills the inside."""
    def build():
        cv = Canvas(w, h, clear=color)
        cv.rect(rgb(color), 0, 0, w, h, radius)
        cv.rect(fill if fill is not None else (0, 0, 0, 0), t, t, w - 2 * t, h - 2 * t, max(0.0, radius - t))
        return cv.done()
    return cached(("frame", w, h, rgb(color), t, radius, fill), build)
