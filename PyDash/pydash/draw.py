"""World rendering: backgrounds, level objects, player icons and particles."""
import math
import random

import pygame

from . import config as C
from . import gfx, skins
from .physics import SHAPES, SIZE, rotate_box

T = C.TILE
TAU = 2 * math.pi


class Camera:
    """Maps y-up world pixels to screen pixels."""

    def __init__(self, ground_y=C.GROUND_Y):
        self.x = 0.0
        self.y = 0.0
        self.ground_y = ground_y

    def sx(self, wx):
        return wx - self.x

    def sy(self, wy):
        return self.ground_y - (wy - self.y)

    def point(self, wx, wy):
        return (self.sx(wx), self.sy(wy))

    def box(self, x, y, w, h):
        """World box (x, y = bottom-left, y-up) to a screen Rect."""
        left = int(round(x - self.x))
        top = int(round(self.ground_y - (y + h - self.y)))
        return pygame.Rect(left, top, int(round(w)), int(round(h)))


_glow_cache = {}


def _glow(width, color):
    key = (width, color)
    surf = _glow_cache.get(key)
    if surf is None:
        surf = pygame.Surface((width, 24), pygame.SRCALPHA)
        for y in range(24):
            a = int(110 * max(0.0, 1 - abs(y - 12) / 12.0) ** 2)
            pygame.draw.line(surf, (*color, a), (0, y), (width, y))
        _glow_cache[key] = surf
    return surf


def draw_background(surf, cam, bg, ground, ceiling=False):
    w, h = surf.get_size()
    top = C.shade(bg, 0.6)
    bands = 10
    band_h = h / bands
    for i in range(bands):
        pygame.draw.rect(surf, C.lerp_color(top, bg, i / (bands - 1)), (0, int(i * band_h), w, int(band_h) + 2))
    # Parallax squares far behind the level.
    size = 150
    px = cam.x * 0.12
    light, dark = C.shade(bg, 1.1), C.shade(bg, 0.82)
    first = int(px // size) - 1
    for i in range(first, first + w // size + 3):
        for j in range(h // size + 1):
            v = ((i * 73856093) ^ (j * 19349663)) & 0xFF
            if v % 5 > 1:
                continue
            rect = (int(i * size - px) + 12, j * size + 12 - 40, size - 24, size - 24)
            pygame.draw.rect(surf, light if v % 2 else dark, rect, 5, border_radius=6)
    gy = int(cam.sy(0))
    if gy < h:
        pygame.draw.rect(surf, ground, (0, gy, w, h - gy))
        tile = 2 * T
        x = -(cam.x % tile)
        edge = C.shade(ground, 0.78)
        while x < w:
            pygame.draw.rect(surf, edge, (int(x), gy, tile, tile), 3)
            x += tile
        line = C.lerp_color(C.WHITE, ground, 0.12)
        surf.blit(_glow(w, line), (0, gy - 12))
        pygame.draw.line(surf, line, (0, gy), (w, gy), 3)
    if ceiling:
        cy = int(cam.sy(C.CEILING_ROWS * T))
        if cy > 0:
            pygame.draw.rect(surf, ground, (0, 0, w, cy))
            line = C.lerp_color(C.WHITE, ground, 0.12)
            surf.blit(_glow(w, line), (0, cy - 12))
            pygame.draw.line(surf, line, (0, cy), (w, cy), 3)


SPIKE_PTS = {
    "spike": [(0.06, 0.0), (0.94, 0.0), (0.5, 0.9)],
    "small_spike": [(0.16, 0.0), (0.84, 0.0), (0.5, 0.42)],
}
PORTAL_COLORS = {"portal_ship": C.PINK, "portal_cube": C.GREEN}


def rot_point(px, py, rot):
    """Rotate a tile-local point clockwise around the tile centre (same as physics)."""
    for _ in range((rot // 90) % 4):
        px, py = py, 1.0 - px
    return px, py


def object_palette(bg):
    fill = C.lerp_color((0, 0, 0), bg, 0.2)
    return fill, C.lerp_color(C.WHITE, bg, 0.06), C.lerp_color(fill, C.WHITE, 0.2)


def _q(color):
    """Colour rounded for sprite cache keys (theme fades would otherwise create endless sprites)."""
    return tuple(int(v) // 4 * 4 for v in color[:3])


def draw_object(surf, cam, o, t, bg, state=""):
    """Draw one level object. state: "" normal, "used" (orb/pad fired), "ghost" (coin already owned)."""
    fill, edge, detail = object_palette(bg)
    kind = o.type
    if kind in ("block", "slab"):
        bx, by, bw, bh = rotate_box(SHAPES[kind][1], o.rot)
        r = cam.box((o.x + bx) * T, (o.y + by) * T, bw * T, bh * T)
        pygame.draw.rect(surf, fill, r)
        inner = r.inflate(-16, -16)
        if inner.w > 6 and inner.h > 6:
            pygame.draw.rect(surf, detail, inner, 2)
        pygame.draw.rect(surf, edge, r, 2)
    elif kind in SPIKE_PTS:
        pad = 5
        local = []
        for px, py in SPIKE_PTS[kind]:
            qx, qy = rot_point(px, py, o.rot)
            local.append((pad + qx * T, pad + (1.0 - qy) * T))
        f, e = _q(fill), _q(edge)
        img = skins.sprite(("spike", kind, o.rot % 360, f, e), T + 2 * pad, T + 2 * pad, [(f, local)], 1.7, e)
        x, y = cam.point(o.x * T, (o.y + 1) * T)
        surf.blit(img, (int(round(x)) - pad, int(round(y)) - pad))
    elif kind == "pad":
        r = cam.box((o.x + 0.1) * T, o.y * T, 0.8 * T, 0.22 * T)
        color = C.lerp_color(C.GOLD, bg, 0.45) if state == "used" else C.GOLD
        line = C.lerp_color(color, bg, 0.35)
        for k in range(3):
            x = r.x + r.w * (k + 1) // 4
            length = 10 + 7 * math.sin(t * 9 + k * 2)
            pygame.draw.line(surf, line, (x, r.y - 5), (x, int(r.y - 5 - length)), 3)
        surf.blit(_pad_img(r.w, r.h, _q(color)), (r.x - 2, r.y - 2))
    elif kind == "orb":
        cx, cy = cam.point((o.x + 0.5) * T, (o.y + 0.5) * T)
        r = int(0.3 * T)
        color = C.lerp_color(C.GOLD, bg, 0.55) if state == "used" else C.GOLD
        ring = int(round(r + 7 + 4 * math.sin(t * 6 + o.x)))
        img = _orb_img(r, ring, _q(color), _q(C.lerp_color(C.WHITE, bg, 0.3)))
        surf.blit(img, img.get_rect(center=(int(round(cx)), int(round(cy)))))
    elif kind == "coin":
        cx, cy = cam.point((o.x + 0.5) * T, (o.y + 0.5) * T + 4 * math.sin(t * 3 + o.x))
        r = int(0.34 * T)
        spin = 0.25 + 0.75 * abs(math.cos(t * 2.4 + o.x * 0.4))
        w = max(4, int(2 * r * spin) // 2 * 2)
        img = _coin_img(r, w, state == "ghost")
        surf.blit(img, img.get_rect(center=(int(round(cx)), int(round(cy)))))
    elif kind in PORTAL_COLORS:
        rect = cam.box((o.x + 0.12) * T, o.y * T, 0.76 * T, 3 * T)
        pulse = int(round(4 * math.sin(t * 5 + o.x)))
        surf.blit(_portal_img(kind, rect.w, rect.h, pulse), (rect.x - 7, rect.y - 7))


CLEAR = (0, 0, 0, 0)


def _pad_img(w, h, color):
    def paint(cv):
        cv.rect(C.OUTLINE, 0, 0, w + 4, (h + 2) * 2, h + 2)
        cv.rect(color, 2, 2, w, h * 2, h)
        cv.rect(C.lerp_color(color, C.WHITE, 0.45), 2 + h * 0.6, 4, w - h * 1.2, 3, 1.5)
    return skins.art(("pad", w, h, color), w + 4, h + 2, paint)


def _orb_img(r, ring, color, ring_col):
    size = 2 * (r + 14)

    def paint(cv):
        c = (size / 2.0, size / 2.0)
        cv.circle(ring_col, c, ring + 1.1)
        cv.circle(CLEAR, c, ring - 1.1)
        cv.circle(C.OUTLINE, c, r + 3)
        cv.circle(color, c, r)
        cv.circle(C.WHITE, c, r * 0.5 + 1.6)
        cv.circle(color, c, r * 0.5 - 1.6)
        cv.circle(C.lerp_color(color, C.WHITE, 0.6), (c[0] - r * 0.42, c[1] - r * 0.42), r * 0.16)
    return skins.art(("orb", r, ring, color, ring_col), size, size, paint)


def _coin_img(r, w, ghost):
    color = (150, 170, 205) if ghost else C.GOLD

    def paint(cv):
        cv.ellipse(C.OUTLINE, 1, 1, w + 6, 2 * r + 6)
        cv.ellipse(color, 4, 4, w, 2 * r)
        iw, ih = w * 0.62, 2 * r * 0.62
        if iw > 7:
            cv.ellipse(C.shade(color, 0.75), 4 + (w - iw) / 2, 4 + (2 * r - ih) / 2, iw, ih)
            cv.ellipse(color, 7 + (w - iw) / 2, 7 + (2 * r - ih) / 2, iw - 6, ih - 6)
        if w > 10:
            cv.circle(C.WHITE, (4 + w * 0.3, 4 + r * 0.55), max(2.0, r / 6.0))
    return skins.art(("coin", r, w, ghost), w + 8, 2 * r + 8, paint)


def _portal_img(kind, w, h, pulse):
    color = PORTAL_COLORS[kind]

    def paint(cv):
        x = y = 7.0
        cv.ellipse(C.OUTLINE, x - 5, y - 5, w + 10, h + 10)
        cv.ellipse(color, x, y, w, h)
        cv.ellipse(CLEAR, x + 11, y + 11, w - 22, h - 22)
        ww, hh = w - 20 + pulse, h - 28 + pulse
        cv.ellipse(C.WHITE, x + (w - ww) / 2, y + (h - hh) / 2, ww, hh)
        cv.ellipse(CLEAR, x + (w - ww) / 2 + 3, y + (h - hh) / 2 + 3, ww - 6, hh - 6)
        mx, my = x + w / 2.0, y + h / 2.0
        if kind == "portal_ship":
            sym = [(mx - 8, my - 10), (mx + 11, my), (mx - 8, my + 10)]
        else:
            sym = gfx.rect_pts(mx - 8, my - 8, 16, 16)
        cv.shapes([(C.WHITE, sym)], 2.0)
    return skins.art(("portal", kind, w, h, pulse), w + 14, h + 14, paint)


class LevelArt:
    """Draws the objects of a level that are inside the camera view."""

    def __init__(self, level):
        self.level = level
        self.rebuild()

    def rebuild(self):
        self.columns = {}
        for i, o in enumerate(self.level.objects):
            self.columns.setdefault(o.x, []).append((i, o))
        self.end_x = self.level.length * T

    def draw(self, surf, cam, t, bg, hidden=(), used=(), ghost=(), show_end=True):
        w = surf.get_width()
        c0, c1 = int(cam.x // T) - 2, int((cam.x + w) // T) + 1
        later = []
        for col in range(c0, c1 + 1):
            for i, o in self.columns.get(col, ()):
                if i in hidden:
                    continue
                if o.type in ("block", "slab", "spike", "small_spike"):
                    draw_object(surf, cam, o, t, bg)
                else:
                    later.append((i, o))
        for i, o in later:
            state = "used" if i in used else ("ghost" if i in ghost else "")
            draw_object(surf, cam, o, t, bg, state)
        if show_end:
            ex = int(cam.sx(self.end_x))
            if -40 < ex < w + 40:
                top = int(cam.sy(C.CEILING_ROWS * T + 4 * T))
                bottom = int(cam.sy(0))
                for k in range(8):
                    color = C.lerp_color(C.WHITE, bg, k / 8.0)
                    pygame.draw.line(surf, color, (ex + k * 5, top), (ex + k * 5, bottom), 5)


def cube_sprite(style, size=T):
    """The player's cube; style = (design, primary, secondary) from skins.style()."""
    return skins.cube(style[0], style[1], style[2], size)


def ship_sprite(style, size=T):
    return skins.ship(style[0], style[1], style[2], size)


def blit_rotated(surf, img, center, angle):
    """Blit `img` rotated by `angle` degrees (counter-clockwise) with smooth edges."""
    a = angle % 360.0
    quarter = int(round(a / 90.0))
    if abs(a - quarter * 90.0) < 0.75:
        if quarter % 4:
            img = pygame.transform.rotate(img, (quarter % 4) * 90)
    else:
        img = pygame.transform.rotozoom(img, a, 1.0)
    surf.blit(img, img.get_rect(center=(int(round(center[0])), int(round(center[1])))))


def draw_player(surf, cam, p, style):
    spr = ship_sprite(style) if p.mode == "ship" else cube_sprite(style)
    blit_rotated(surf, spr, (cam.sx(p.x + SIZE / 2), cam.sy(p.y + SIZE / 2)), -p.rotation)


_flash_cache = {}


def _flash_layer(size, color):
    key = (size, tuple(color))
    layer = _flash_cache.get(key)
    if layer is None:
        layer = pygame.Surface(size)
        layer.fill(color)
        _flash_cache[key] = layer
    return layer


class Effects:
    """Particles, expanding rings and a full-screen flash (all in world coordinates)."""

    def __init__(self):
        self.parts = []
        self.rings = []
        self.flash = 0.0
        self.flash_color = C.WHITE

    def clear(self):
        self.parts = []
        self.rings = []
        self.flash = 0.0

    def emit(self, x, y, vx, vy, life, color, size, gravity=0.0):
        self.parts.append([x, y, vx, vy, 0.0, life, color, size, gravity])

    def burst(self, x, y, color, n=16, speed=(120, 520), life=(0.3, 0.8), size=(5, 12), gravity=900.0,
              angle=None, spread=TAU):
        for _ in range(n):
            a = random.uniform(0, TAU) if angle is None else angle + random.uniform(-spread / 2, spread / 2)
            v = random.uniform(*speed)
            self.emit(x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(*life), color,
                      random.uniform(*size), gravity)

    def ring(self, x, y, color, r0=10, r1=90, life=0.35, width=5):
        self.rings.append([x, y, r0, r1, 0.0, life, color, width])

    def explode(self, x, y, colors):
        for c in colors:
            self.burst(x, y, c, n=18, speed=(150, 760), life=(0.4, 1.0), size=(6, 16), gravity=700)
        self.ring(x, y, C.WHITE, 10, 160, 0.45, 8)
        self.flash, self.flash_color = 0.55, C.WHITE

    def update(self, dt):
        keep = []
        for p in self.parts:
            p[4] += dt
            if p[4] < p[5]:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                p[3] -= p[8] * dt
                keep.append(p)
        self.parts = keep
        for r in self.rings:
            r[4] += dt
        self.rings = [r for r in self.rings if r[4] < r[5]]
        self.flash = max(0.0, self.flash - dt * 2.5)

    def draw(self, surf, cam):
        for x, y, _vx, _vy, age, life, color, size, _g in self.parts:
            s = max(1, int(size * (1 - age / life)))
            sx, sy = cam.point(x, y)
            pygame.draw.rect(surf, color, (int(sx) - s // 2, int(sy) - s // 2, s, s))
        for x, y, r0, r1, age, life, color, width in self.rings:
            k = age / life
            r = max(2, int(r0 + (r1 - r0) * (1 - (1 - k) ** 2)))
            pygame.draw.circle(surf, color, (int(cam.sx(x)), int(cam.sy(y))), r,
                               min(r, max(1, int(width * (1 - k)) + 1)))
        if self.flash > 0:
            layer = _flash_layer(surf.get_size(), self.flash_color)
            layer.set_alpha(int(150 * self.flash))
            surf.blit(layer, (0, 0))
