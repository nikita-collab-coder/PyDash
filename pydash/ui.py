"""Fonts, outlined text, buttons, panels and small vector icons."""
import math

import pygame

from . import config as C
from . import gfx, glyphs

_fonts = {}
_text_cache = {}
_dim_cache = {}
_click_handler = None


def set_click_handler(fn):
    """Function called whenever any button fires (used for the click sound)."""
    global _click_handler
    _click_handler = fn


def font(size):
    f = _fonts.get(size)
    if f is None:
        try:
            f = pygame.font.Font(C.FONT_PATH, size)
        except (OSError, pygame.error):
            f = pygame.font.Font(None, int(size * 1.35))
        _fonts[size] = f
    return f


def render_text(text, size, color=C.WHITE, outline=C.OUTLINE):
    """Text with a chunky outline, like arcade games use (cached)."""
    key = (text, size, tuple(color), tuple(outline) if outline else None)
    img = _text_cache.get(key)
    if img is not None:
        return img
    f = font(size)
    inner = f.render(text, True, color)
    if outline:
        t = max(2, size // 14)
        w, h = inner.get_size()
        img = pygame.Surface((w + 2 * t, h + 2 * t), pygame.SRCALPHA)
        edge = f.render(text, True, outline)
        steps = 16
        for i in range(steps):
            a = i * 2 * math.pi / steps
            img.blit(edge, (t + round(math.cos(a) * t), t + round(math.sin(a) * t)))
        img.blit(edge, (t, t + 1))
        img.blit(inner, (t, t))
    else:
        img = inner
    if len(_text_cache) > 800:
        _text_cache.clear()
    _text_cache[key] = img
    return img


def draw_text(surf, text, size, pos, color=C.WHITE, anchor="center", outline=C.OUTLINE, alpha=255):
    img = render_text(str(text), size, color, outline)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(max(0, int(alpha)))
    rect = img.get_rect()
    setattr(rect, anchor, (int(pos[0]), int(pos[1])))
    surf.blit(img, rect)
    return rect


def dim(surf, alpha=150):
    key = (surf.get_size(), alpha)
    layer = _dim_cache.get(key)
    if layer is None:
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        layer.fill((0, 0, 0, alpha))
        _dim_cache[key] = layer
    surf.blit(layer, (0, 0))


def panel(surf, rect, color=C.PANEL, edge=C.PANEL_EDGE, alpha=235, radius=22):
    rect = pygame.Rect(rect)
    surf.blit(gfx.panel(rect.w, rect.h, color, edge, alpha, radius), rect.topleft)
    return rect


def progress_bar(surf, rect, frac, color, label=None, size=22):
    rect = pygame.Rect(rect)
    surf.blit(gfx.bar_frame(rect.w, rect.h), (rect.x - 4, rect.y - 4))
    frac = max(0.0, min(1.0, float(frac)))
    if frac > 0:
        w = max(rect.h, min(rect.w, int(rect.w * frac) // 2 * 2))
        surf.blit(gfx.bar_fill(w, rect.h, color), rect.topleft)
    if label is not None:
        draw_text(surf, label, size, rect.center, C.WHITE)


def star_points(cx, cy, r_out, r_in, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _blit_center(surf, img, center):
    surf.blit(img, img.get_rect(center=(int(round(center[0])), int(round(center[1])))))


def draw_star(surf, center, r, filled=True, color=C.GOLD):
    _blit_center(surf, glyphs.star(r, filled, color), center)


def draw_coin_slot(surf, center, r, got):
    _blit_center(surf, glyphs.coin(r, got), center)


def draw_face(surf, difficulty, center, r):
    """Round difficulty face: happy for easy levels, angrier (and horned) for hard ones."""
    _blit_center(surf, glyphs.face(difficulty, r), center)


def draw_icon(surf, name, center, size, color=C.WHITE):
    """Vector icon (see glyphs.py). `size` is the glyph height; names ending in _off are crossed out."""
    _blit_center(surf, glyphs.icon(name, size, color), center)


class Button:
    """Rounded arcade button. `handle` returns True when the button fires."""

    def __init__(self, rect, label="", action=None, color=C.GREEN, size=30, hotkeys=(), icon=None,
                 enabled=True, text_color=C.WHITE):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.color = color
        self.size = size
        self.hotkeys = tuple(hotkeys)
        self.icon = icon
        self.enabled = enabled
        self.text_color = text_color
        self.hover = False
        self.pressed = False
        self.pop = 0.0
        self.image = None  # optional Surface drawn instead of the icon glyph

    def handle(self, event):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            hit = self.pressed and self.rect.collidepoint(event.pos)
            self.pressed = False
            if hit:
                return self.fire()
        elif event.type == pygame.KEYDOWN and event.key in self.hotkeys:
            return self.fire()
        return False

    def fire(self):
        self.pop = 1.0
        if _click_handler:
            _click_handler()
        if self.action:
            self.action()
        return True

    def update(self, dt):
        self.hover = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
        self.pop = max(0.0, self.pop - dt * 6)

    def draw(self, surf):
        state = "pressed" if self.pressed and self.hover else ("hover" if self.hover else "normal")
        grow = int(round(5 * self.pop))
        r = self.rect.inflate(grow * 2, grow * 2)
        img, face = gfx.button(r.w, r.h, self.color if self.enabled else C.GRAY, state)
        surf.blit(img, (r.x - 2, r.y - 2))
        cx, cy = r.x - 2 + face.centerx, r.y - 2 + face.centery
        has_icon = bool(self.icon) or self.image is not None
        if has_icon and self.label:
            isz = int(min(face.h * 0.56, 40))
            iw = self.image.get_width() if self.image is not None else isz
            text = render_text(self.label, self.size, self.text_color)
            x0 = cx - (iw + 12 + text.get_width()) // 2
            self._draw_icon(surf, (x0 + iw // 2, cy), isz)
            surf.blit(text, text.get_rect(midleft=(x0 + iw + 12, cy)))
        elif has_icon:
            self._draw_icon(surf, (cx, cy), int(min(face.w, face.h) * 0.56))
        else:
            draw_text(surf, self.label, self.size, (cx, cy), self.text_color)

    def _draw_icon(self, surf, center, size):
        if self.image is not None:
            _blit_center(surf, self.image, center)
        else:
            draw_icon(surf, self.icon, center, size)


class Toast:
    """A short message that fades out."""

    def __init__(self):
        self.text = ""
        self.color = C.WHITE
        self.time = 0.0

    def show(self, text, color=C.WHITE, seconds=2.2):
        self.text, self.color, self.time = text, color, seconds

    def update(self, dt):
        self.time = max(0.0, self.time - dt)

    def draw(self, surf, pos=(C.SCREEN_W // 2, 120), size=38):
        if self.time > 0 and self.text:
            draw_text(surf, self.text, size, pos, self.color, alpha=min(1.0, self.time * 3) * 255)
