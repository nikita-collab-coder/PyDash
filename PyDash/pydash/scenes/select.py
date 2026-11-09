"""Level select: official levels as cards, the player's own levels as a list."""
import os

import pygame

from .. import config as C
from .. import draw as D
from .. import skins, ui
from ..audio import MENU_MUSIC
from ..game import Scene
from ..level import list_custom_levels, new_custom_level, save_level


def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


class SelectScene(Scene):
    music = MENU_MUSIC
    PER_PAGE = 4

    def __init__(self, game, tab="main", index=0, page=0):
        super().__init__(game)
        self.tab = tab
        self.index = index % max(1, len(game.levels))
        self.page = page
        self.t = 0.0
        self.slide = 0.0
        self.toast = ui.Toast()
        self.confirm = None  # (path, seconds left) while a delete waits for confirmation
        self.cam = D.Camera()
        self.custom = []
        self.row_buttons = []
        self.bg, self.ground = self.target_theme()
        w, h = C.SCREEN_W, C.SCREEN_H
        self.back_btn = ui.Button((24, 20, 80, 70), "", self.back, C.RED, icon="home", hotkeys=(pygame.K_ESCAPE,))
        self.tab_main = ui.Button((w // 2 - 345, 22, 220, 64), "Levels", lambda: self.set_tab("main"), C.CYAN, 28,
                                  hotkeys=(pygame.K_1,))
        self.tab_custom = ui.Button((w // 2 - 110, 22, 220, 64), "My levels", lambda: self.set_tab("custom"),
                                    C.ORANGE, 28, hotkeys=(pygame.K_2,))
        self.tab_icons = ui.Button((w // 2 + 125, 22, 220, 64), "Icons", self.open_icons, C.PINK, 28, icon="cube",
                                   hotkeys=(pygame.K_3,))
        self.prev_btn = ui.Button((36, h // 2 - 70, 86, 120), "<", lambda: self.move(-1), C.GREEN, 54,
                                  hotkeys=(pygame.K_LEFT, pygame.K_a))
        self.next_btn = ui.Button((w - 122, h // 2 - 70, 86, 120), ">", lambda: self.move(1), C.GREEN, 54,
                                  hotkeys=(pygame.K_RIGHT, pygame.K_d))
        self.play_btn = ui.Button((w // 2 - 150, 566, 300, 92), "Play", self.play_selected, C.GREEN, 40,
                                  icon="play", hotkeys=(pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER))
        self.practice_btn = ui.Button((w // 2 + 180, 578, 210, 70), "Practice", lambda: self.play_selected(True),
                                      C.CYAN, 26, icon="flag", hotkeys=(pygame.K_p,))
        self.new_btn = ui.Button((w // 2 - 150, h - 98, 300, 76), "New level", self.new_level, C.GREEN, 30,
                                 icon="plus", hotkeys=(pygame.K_n,))
        self.refresh()

    # ------------------------------------------------------------ helpers
    def target_theme(self):
        if self.tab == "main" and self.game.levels:
            return self.game.levels[self.index].theme_at(0)
        return C.THEMES["night"]

    def pages(self):
        return max(1, (len(self.custom) + self.PER_PAGE - 1) // self.PER_PAGE)

    def page_levels(self):
        start = self.page * self.PER_PAGE
        return self.custom[start:start + self.PER_PAGE]

    def row_rect(self, i):
        return pygame.Rect(C.SCREEN_W // 2 - 460, 116 + i * 106, 920, 92)

    def refresh(self):
        self.custom = list_custom_levels() if self.tab == "custom" else []
        self.page = max(0, min(self.page, self.pages() - 1))
        self.row_buttons = []
        for i, level in enumerate(self.page_levels()):
            r = self.row_rect(i)
            y = r.y + 14
            self.row_buttons += [
                ui.Button((r.right - 262, y, 74, 62), "", lambda lv=level: self.play_custom(lv), C.GREEN, icon="play"),
                ui.Button((r.right - 176, y, 74, 62), "", lambda lv=level: self.edit(lv), C.ORANGE, icon="edit"),
                ui.Button((r.right - 90, y, 74, 62), "", lambda lv=level: self.delete(lv), C.RED, icon="trash"),
            ]

    def active_buttons(self):
        buttons = [self.back_btn, self.tab_main, self.tab_custom, self.tab_icons]
        if self.tab == "main":
            return buttons + [self.prev_btn, self.next_btn, self.play_btn, self.practice_btn]
        buttons += [self.new_btn] + self.row_buttons
        if self.pages() > 1:
            buttons += [self.prev_btn, self.next_btn]
        return buttons

    # ------------------------------------------------------------ actions
    def set_tab(self, tab):
        if tab != self.tab:
            self.tab = tab
            self.page = 0
            self.refresh()

    def move(self, d):
        if self.tab == "main":
            self.index = (self.index + d) % len(self.game.levels)
            self.slide = float(d)
        else:
            self.page = max(0, min(self.page + d, self.pages() - 1))
            self.refresh()

    def back(self):
        from .menu import MenuScene
        self.game.switch(MenuScene(self.game))

    def open_icons(self):
        from .icons import IconsScene
        tab, index, page = self.tab, self.index, self.page
        self.game.switch(IconsScene(self.game, back=lambda: SelectScene(self.game, tab, index, page)))

    def play_selected(self, practice=False):
        from .play import PlayScene
        game, index = self.game, self.index
        game.switch(PlayScene(game, game.levels[index], practice=practice,
                              back=lambda: SelectScene(game, "main", index)))

    def play_custom(self, level):
        from .play import PlayScene
        game, page = self.game, self.page
        game.switch(PlayScene(game, level, back=lambda: SelectScene(game, "custom", page=page)))

    def edit(self, level):
        from .editor import EditorScene
        self.game.switch(EditorScene(self.game, level))

    def new_level(self):
        level = new_custom_level()
        save_level(level)
        self.edit(level)

    def delete(self, level):
        if self.confirm and self.confirm[0] == level.path:
            try:
                os.remove(level.path)
                self.toast.show("Deleted " + level.name, C.RED)
            except OSError as exc:
                self.toast.show("Could not delete: %s" % exc, C.RED)
            self.confirm = None
            self.refresh()
        else:
            self.confirm = (level.path, 3.0)
            self.toast.show("Click delete again to remove " + level.name, C.ORANGE, 3.0)

    # ------------------------------------------------------------ loop
    def handle(self, event):
        for b in self.active_buttons():
            if b.handle(event):
                return
        if event.type == pygame.MOUSEWHEEL and self.tab == "custom":
            self.move(-1 if event.y > 0 else 1)

    def update(self, dt):
        self.t += dt
        self.cam.x += 60 * dt
        self.slide -= self.slide * min(1.0, dt * 12)
        bg, ground = self.target_theme()
        k = min(1.0, dt * 6)
        self.bg, self.ground = _mix(self.bg, bg, k), _mix(self.ground, ground, k)
        if self.confirm:
            left = self.confirm[1] - dt
            self.confirm = (self.confirm[0], left) if left > 0 else None
        self.tab_main.color = C.CYAN if self.tab == "main" else C.shade(C.CYAN, 0.55)
        self.tab_custom.color = C.ORANGE if self.tab == "custom" else C.shade(C.ORANGE, 0.55)
        self.tab_icons.image = D.cube_sprite(skins.style(self.game.save.settings), 34)
        for b in self.active_buttons():
            b.update(dt)
        self.toast.update(dt)

    def draw(self, surf):
        bg = tuple(int(c) for c in self.bg)
        D.draw_background(surf, self.cam, bg, tuple(int(c) for c in self.ground))
        if self.tab == "main":
            self.draw_card(surf, self.game.levels[self.index], int(C.SCREEN_W // 2 + self.slide * 240))
            n = len(self.game.levels)
            for i in range(n):
                pos = (int(C.SCREEN_W // 2 + (i - (n - 1) / 2) * 30), 540)
                pygame.draw.circle(surf, C.OUTLINE, pos, 10)
                pygame.draw.circle(surf, C.WHITE if i == self.index else (70, 78, 110), pos, 7)
        else:
            self.draw_custom(surf)
        for b in self.active_buttons():
            b.draw(surf)
        self.toast.draw(surf, (C.SCREEN_W // 2, C.SCREEN_H - 140), 26)

    def draw_card(self, surf, level, cx):
        stats = self.game.save.stats(level.level_id)
        rect = pygame.Rect(0, 0, 780, 410)
        rect.center = (cx, 318)
        ui.panel(surf, rect, alpha=215)
        ui.draw_face(surf, level.difficulty, (rect.x + 115, rect.y + 125), 64)
        ui.draw_text(surf, level.difficulty.capitalize(), 24, (rect.x + 115, rect.y + 218))
        ui.draw_star(surf, (rect.x + 95, rect.y + 266), 19, stats["completed"])
        ui.draw_text(surf, str(level.stars), 32, (rect.x + 123, rect.y + 266), anchor="midleft")
        ui.draw_text(surf, level.name, 54, (rect.x + 480, rect.y + 66))
        coins, got = level.coin_ids, set(stats["coins"])
        for k, cid in enumerate(coins):
            ui.draw_coin_slot(surf, (int(rect.x + 480 + (k - (len(coins) - 1) / 2) * 52), rect.y + 132), 17,
                              cid in got)
        ui.draw_text(surf, "Normal mode", 20, (rect.x + 240, rect.y + 182), anchor="midleft")
        ui.progress_bar(surf, (rect.x + 240, rect.y + 200, 490, 34), stats["best"] / 100.0, C.GREEN,
                        "%d%%" % stats["best"])
        ui.draw_text(surf, "Practice mode", 20, (rect.x + 240, rect.y + 262), anchor="midleft")
        ui.progress_bar(surf, (rect.x + 240, rect.y + 280, 490, 34), stats["practice"] / 100.0, C.CYAN,
                        "%d%%" % stats["practice"])
        ui.draw_text(surf, "Attempts: %d      Jumps: %d" % (stats["attempts"], stats["jumps"]), 22,
                     (rect.x + 480, rect.y + 360))
        if stats["completed"]:
            ui.draw_icon(surf, "check", (rect.right - 52, rect.y + 52), 46, C.GREEN)

    def draw_custom(self, surf):
        w = C.SCREEN_W
        if not self.custom:
            ui.draw_text(surf, "No levels yet!", 50, (w // 2, 270))
            ui.draw_text(surf, "Press New level to build your first one.", 26, (w // 2, 335))
            return
        for i, level in enumerate(self.page_levels()):
            rect = self.row_rect(i)
            ui.panel(surf, rect, alpha=215, radius=18)
            stats = self.game.save.stats(level.level_id)
            ui.draw_text(surf, level.name, 32, (rect.x + 28, rect.y + 32), anchor="midleft")
            info = "%d objects   |   %d tiles long   |   best %d%%" % (len(level.objects), level.length,
                                                                 stats["best"])
            ui.draw_text(surf, info, 20, (rect.x + 28, rect.y + 68), anchor="midleft")
            if stats["completed"]:
                ui.draw_icon(surf, "check", (rect.right - 300, rect.centery), 36, C.GREEN)
        if self.pages() > 1:
            ui.draw_text(surf, "Page %d / %d" % (self.page + 1, self.pages()), 22, (w // 2, 548))
