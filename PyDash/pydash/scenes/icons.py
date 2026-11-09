"""Icons: pick the cube design and its two colours. Every change is saved at once."""
import pygame

from .. import config as C
from .. import draw as D
from .. import gfx, skins, ui
from ..audio import MENU_MUSIC
from ..game import Scene

PREVIEW = pygame.Rect(40, 110, 380, 262)
DESIGNS = pygame.Rect(440, 110, 800, 262)
COLORS = pygame.Rect(40, 392, 1200, 252)
CELL, GAP = 88, 8
SWATCH, SW_GAP = 50, 6
KEYS = ("color1", "color2")


class IconsScene(Scene):
    music = MENU_MUSIC

    def __init__(self, game, back=None):
        super().__init__(game)
        self.back_to = back
        self.t = 0.0
        self.cam = D.Camera()
        self.hover = None
        self.back_btn = ui.Button((24, 20, 80, 70), "", self.back, C.RED, icon="back", hotkeys=(pygame.K_ESCAPE,))
        self.swap_btn = ui.Button((COLORS.centerx - 110, COLORS.bottom - 80, 220, 60), "Swap", self.swap, C.PINK, 26,
                                  icon="retry", hotkeys=(pygame.K_x,))
        self.buttons = [self.back_btn, self.swap_btn]

    # ------------------------------------------------------------ layout
    def design_rect(self, i):
        x0 = DESIGNS.x + (DESIGNS.w - (8 * CELL + 7 * GAP)) // 2
        return pygame.Rect(x0 + (i % 8) * (CELL + GAP), DESIGNS.y + 62 + (i // 8) * (CELL + GAP), CELL, CELL)

    def swatch_rect(self, row, i):
        return pygame.Rect(COLORS.x + 168 + i * (SWATCH + SW_GAP), COLORS.y + 26 + row * 78, SWATCH, SWATCH)

    def hit(self, pos):
        for i in range(len(C.ICON_DESIGNS)):
            if self.design_rect(i).collidepoint(pos):
                return "icon", i
        for row, key in enumerate(KEYS):
            for i in range(len(C.ICON_COLORS)):
                if self.swatch_rect(row, i).inflate(SW_GAP, SW_GAP).collidepoint(pos):
                    return key, i
        return None

    # ------------------------------------------------------------ actions
    def value(self, key):
        n = len(C.ICON_DESIGNS) if key == "icon" else len(C.ICON_COLORS)
        try:
            return int(self.game.save.settings.get(key, skins.DEFAULTS[key])) % n
        except (TypeError, ValueError):
            return skins.DEFAULTS[key]

    def set(self, key, value, sound=True):
        self.game.save.settings[key] = value
        self.game.save.save()
        if sound:
            self.game.audio.play("click", 0.45)

    def step(self, key, d):
        n = len(C.ICON_DESIGNS) if key == "icon" else len(C.ICON_COLORS)
        self.set(key, (self.value(key) + d) % n)

    def swap(self):
        c1, c2 = self.value("color1"), self.value("color2")
        self.game.save.settings["color1"] = c2
        self.set("color2", c1, sound=False)

    def back(self):
        if self.back_to is not None:
            self.game.switch(self.back_to())
        else:
            from .menu import MenuScene
            self.game.switch(MenuScene(self.game))

    # ------------------------------------------------------------ loop
    def handle(self, event):
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            target = self.hit(event.pos)
            if target:
                self.set(*target)
        elif event.type == pygame.KEYDOWN:
            steps = {pygame.K_RIGHT: ("icon", 1), pygame.K_d: ("icon", 1), pygame.K_LEFT: ("icon", -1),
                     pygame.K_a: ("icon", -1), pygame.K_DOWN: ("color1", 1), pygame.K_s: ("color1", 1),
                     pygame.K_UP: ("color1", -1), pygame.K_w: ("color1", -1), pygame.K_e: ("color2", 1),
                     pygame.K_q: ("color2", -1)}
            if event.key in steps:
                self.step(*steps[event.key])

    def update(self, dt):
        self.t += dt
        self.cam.x += 60 * dt
        self.hover = self.hit(pygame.mouse.get_pos())
        for b in self.buttons:
            b.update(dt)

    def draw(self, surf):
        bg, ground = C.THEMES["purple"]
        D.draw_background(surf, self.cam, bg, ground)
        ui.draw_text(surf, "Icons", 60, (C.SCREEN_W // 2, 56), C.GOLD)
        style = skins.style(self.game.save.settings)
        design, c1, c2 = style
        idx = self.value("icon")

        ui.panel(surf, PREVIEW, alpha=215, radius=18)
        cube = D.cube_sprite(style, 112)
        surf.blit(cube, cube.get_rect(center=(PREVIEW.x + 108, PREVIEW.y + 104)))
        ship = D.ship_sprite(style, 74)
        surf.blit(ship, ship.get_rect(center=(PREVIEW.x + 282, PREVIEW.y + 110)))
        ui.draw_text(surf, design.capitalize(), 36, (PREVIEW.centerx, PREVIEW.y + 202))
        ui.draw_text(surf, "Design %d / %d" % (idx + 1, len(C.ICON_DESIGNS)), 20,
                     (PREVIEW.centerx, PREVIEW.y + 236), (200, 212, 245))

        ui.panel(surf, DESIGNS, alpha=215, radius=18)
        ui.draw_text(surf, "Design", 28, (DESIGNS.x + 28, DESIGNS.y + 32), anchor="midleft")
        for i, name in enumerate(C.ICON_DESIGNS):
            r = self.design_rect(i)
            ui.panel(surf, r, color=(26, 34, 78), edge=(76, 98, 166), alpha=255, radius=12)
            img = skins.cube(name, c1, c2, 60)
            surf.blit(img, img.get_rect(center=r.center))
            if i == idx:
                surf.blit(gfx.frame(r.w + 14, r.h + 14, C.GOLD, 4.5, 17.0), (r.x - 7, r.y - 7))
            elif self.hover == ("icon", i):
                surf.blit(gfx.frame(r.w + 10, r.h + 10, C.WHITE, 3.0, 15.0), (r.x - 5, r.y - 5))

        ui.panel(surf, COLORS, alpha=215, radius=18)
        for row, key in enumerate(KEYS):
            sel = self.value(key)
            r0 = self.swatch_rect(row, 0)
            ui.draw_text(surf, "Color %d" % (row + 1), 28, (COLORS.x + 28, r0.centery), anchor="midleft")
            for i, col in enumerate(C.ICON_COLORS):
                r = self.swatch_rect(row, i)
                pygame.draw.rect(surf, C.OUTLINE, r)
                pygame.draw.rect(surf, col, r.inflate(-8, -8))
                if i == sel:
                    surf.blit(gfx.frame(r.w + 14, r.h + 14, C.WHITE, 4.0, 9.0), (r.x - 7, r.y - 7))
                elif self.hover == (key, i):
                    surf.blit(gfx.frame(r.w + 10, r.h + 10, (200, 210, 240), 2.5, 7.0), (r.x - 5, r.y - 5))
        for b in self.buttons:
            b.draw(surf)
        ui.draw_text(surf, "Left/Right: design    Up/Down: color 1    Q/E: color 2    X: swap    Esc: back", 20,
                     (C.SCREEN_W // 2, C.SCREEN_H - 40))
