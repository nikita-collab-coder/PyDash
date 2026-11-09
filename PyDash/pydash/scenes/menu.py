"""Main menu: play, create, icon picker and sound toggles."""
import math

import pygame

from .. import config as C
from .. import skins
from .. import draw as D
from .. import ui
from ..audio import MENU_MUSIC
from ..game import Scene
from ..level import LevelObject

T = C.TILE
RUN_SPEED = 420.0  # 7 tiles per second; the demo cube jumps once per second


class MenuScene(Scene):
    music = MENU_MUSIC

    def __init__(self, game):
        super().__init__(game)
        self.cam = D.Camera()
        self.t = 0.0
        self.quit_armed = 0.0
        self.toast = ui.Toast()
        cx, w, h = C.SCREEN_W // 2, C.SCREEN_W, C.SCREEN_H
        self.play_btn = ui.Button((cx - 105, 270, 210, 150), "", self.play, C.GREEN, icon="play",
                                  hotkeys=(pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER))
        self.icon_btn = ui.Button((cx - 390, 305, 210, 84), "Icons", self.open_icons, C.CYAN, 28, icon="cube",
                                  hotkeys=(pygame.K_i,))
        self.create_btn = ui.Button((cx + 180, 305, 210, 84), "Create", self.create, C.ORANGE, 28, icon="edit",
                                    hotkeys=(pygame.K_e,))
        self.music_btn = ui.Button((24, h - 96, 76, 72), "", self.toggle_music, C.PINK, icon="music",
                                   hotkeys=(pygame.K_m,))
        self.sfx_btn = ui.Button((112, h - 96, 76, 72), "", self.toggle_sfx, C.PINK, icon="sound",
                                 hotkeys=(pygame.K_s,))
        self.quit_btn = ui.Button((w - 100, h - 96, 76, 72), "", self.game.quit, C.RED, icon="close")
        self.buttons = [self.play_btn, self.icon_btn, self.create_btn, self.music_btn, self.sfx_btn, self.quit_btn]
        self.spike = LevelObject("spike", 0, 0)

    # ------------------------------------------------------------ actions
    def play(self):
        from .select import SelectScene
        self.game.switch(SelectScene(self.game, "main"))

    def create(self):
        from .select import SelectScene
        self.game.switch(SelectScene(self.game, "custom"))

    def open_icons(self):
        from .icons import IconsScene
        self.game.switch(IconsScene(self.game))

    def toggle_music(self):
        on = not self.game.save.settings.get("music", True)
        self.game.audio.set_music_enabled(on)
        self.game.save.save()
        self.toast.show("Music on" if on else "Music off")

    def toggle_sfx(self):
        on = not self.game.save.settings.get("sfx", True)
        self.game.audio.set_sfx_enabled(on)
        self.game.save.save()
        self.toast.show("Sound effects on" if on else "Sound effects off")

    # ------------------------------------------------------------ loop
    def handle(self, event):
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.quit_armed > 0:
                self.game.quit()
            else:
                self.quit_armed = 2.0
                self.toast.show("Press Esc again to quit", seconds=2.0)

    def update(self, dt):
        self.t += dt
        self.quit_armed = max(0.0, self.quit_armed - dt)
        self.cam.x = self.t * RUN_SPEED
        settings = self.game.save.settings
        music, sfx = settings.get("music", True), settings.get("sfx", True)
        self.music_btn.color, self.music_btn.icon = (C.PINK, "music") if music else (C.GRAY, "music_off")
        self.sfx_btn.color, self.sfx_btn.icon = (C.PINK, "sound") if sfx else (C.GRAY, "sound_off")
        self.icon_btn.image = D.cube_sprite(skins.style(settings), 38)
        for b in self.buttons:
            b.update(dt)
        self.toast.update(dt)

    def theme(self):
        names = list(C.THEMES)
        k = self.t / 6.0
        i = int(k) % len(names)
        f = min(1.0, max(0.0, (k - int(k) - 0.8) / 0.2))
        a, b = C.THEMES[names[i]], C.THEMES[names[(i + 1) % len(names)]]
        return C.lerp_color(a[0], b[0], f), C.lerp_color(a[1], b[1], f)

    def draw(self, surf):
        bg, ground = self.theme()
        D.draw_background(surf, self.cam, bg, ground)
        # Spikes every 7 tiles; the cube clears each one in the middle of its jump.
        first = int(self.cam.x // (7 * T)) - 1
        for i in range(first, first + 5):
            self.spike.x = 7 * i + 9
            D.draw_object(surf, self.cam, self.spike, self.t, bg)
        phase = self.t % 1.0
        lift = 4 * 2.2 * T * phase * (1 - phase)
        D.blit_rotated(surf, D.cube_sprite(skins.style(self.game.save.settings)),
                       (C.PLAYER_SCREEN_X + T // 2, C.GROUND_Y - T / 2 - lift), -180.0 * phase)

        bob = math.sin(self.t * 2.2) * 6
        ui.draw_text(surf, C.TITLE, 120, (C.SCREEN_W // 2, int(150 + bob)), C.GOLD)
        for b in self.buttons:
            b.draw(surf)

        levels = self.game.levels
        stars = self.game.save.total_stars(levels)
        total = sum(lv.stars for lv in levels)
        coins = sum(len(self.game.save.stats(lv.level_id)["coins"]) for lv in levels)
        all_coins = sum(len(lv.coin_ids) for lv in levels)
        ui.panel(surf, pygame.Rect(C.SCREEN_W - 250, 20, 230, 104), alpha=200, radius=18)
        ui.draw_star(surf, (C.SCREEN_W - 212, 50), 17)
        ui.draw_text(surf, "%d / %d" % (stars, total), 28, (C.SCREEN_W - 184, 50), anchor="midleft")
        ui.draw_coin_slot(surf, (C.SCREEN_W - 212, 94), 15, True)
        ui.draw_text(surf, "%d / %d" % (coins, all_coins), 28, (C.SCREEN_W - 184, 94), anchor="midleft")
        ui.draw_text(surf, "Space: play    E: create    I: icons    M: music    F11: fullscreen", 20,
                     (C.SCREEN_W // 2, C.SCREEN_H - 50), C.WHITE)
        ui.draw_text(surf, "v" + C.VERSION, 18, (C.SCREEN_W - 120, C.SCREEN_H - 20), C.WHITE, anchor="midright")
        self.toast.draw(surf, (C.SCREEN_W // 2, 470), 30)
