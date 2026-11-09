"""Window, main loop and scene switching."""
import os
import sys

import pygame

from . import config as C
from . import ui
from .audio import MENU_MUSIC, Audio
from .level import load_official_levels
from .save import SaveData


class Scene:
    """Base class for screens. `music` (song settings or None) starts when the scene is entered."""

    music = None

    def __init__(self, game):
        self.game = game

    def enter(self):
        pass

    def exit(self):
        pass

    def handle(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


class Game:
    def __init__(self, headless=False, save_path=None):
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        pygame.display.set_caption("%s %s" % (C.TITLE, C.VERSION))
        flags = 0 if headless else getattr(pygame, "SCALED", 0) | getattr(pygame, "RESIZABLE", 0)
        try:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags, vsync=1)
        except (pygame.error, TypeError):
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags)
        self.clock = pygame.time.Clock()
        self.save = SaveData(save_path)
        self.audio = Audio(self.save.settings)
        ui.set_click_handler(lambda: self.audio.play("click", 0.45))
        self.levels = load_official_levels()
        self.audio.prepare([MENU_MUSIC] + [lv.music for lv in self.levels])
        self.scene = None
        self.running = True
        self.time = 0.0
        from .scenes.menu import MenuScene
        self.switch(MenuScene(self))

    def switch(self, scene):
        if self.scene is not None:
            self.scene.exit()
        self.scene = scene
        scene.enter()
        if scene.music is not None:
            self.audio.music(scene.music, restart=False)

    def quit(self):
        self.running = False

    def toggle_fullscreen(self):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    def frame(self, dt, events):
        """One frame: events, update and draw (the caller flips the display)."""
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
            else:
                self.scene.handle(event)
        self.time += dt
        self.scene.update(dt)
        self.audio.update()
        self.scene.draw(self.screen)

    def run(self):
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 0.05)
            self.frame(dt, pygame.event.get())
            pygame.display.flip()
        self.save.save()
        pygame.quit()


def main():
    if sys.version_info < (3, 8):
        sys.exit("PyDash needs Python 3.8 or newer.")
    Game().run()
