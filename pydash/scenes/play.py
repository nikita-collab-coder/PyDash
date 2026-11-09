"""Gameplay: fixed-step physics, camera, effects, practice checkpoints, pause menu and results."""
import math
import random

import pygame

from .. import config as C
from .. import skins
from .. import draw as D
from .. import ui
from ..game import Scene
from ..physics import SIZE, PlayerState, World, progress, step

T = C.TILE
STEP = 1.0 / C.PHYSICS_HZ
JUMP_KEYS = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)
RESPAWN_DELAY = 1.0
END_PANEL_DELAY = 1.0
FOCUS_LOST = getattr(pygame, "WINDOWFOCUSLOST", -1)


class PlayScene(Scene):
    def __init__(self, game, level, practice=False, back=None, record=True):
        super().__init__(game)
        self.level = level
        self.practice = practice
        self.back = back
        self.record = record and bool(level.level_id)
        self.world = World(level)
        self.art = D.LevelArt(level)
        self.cam = D.Camera()
        self.fx = D.Effects()
        self.toast = ui.Toast()
        self.icon = skins.style(game.save.settings)
        self.colors = self.icon[1:]
        self.stats = game.save.stats(level.level_id) if self.record else None
        self.owned_coins = set(self.stats["coins"]) if self.stats else set()
        self.attempt = 0
        self.t = 0.0
        self.paused = False
        self.checkpoints = []
        self.mouse_hold = False
        self.input_override = None  # tests: a callable that returns the jump state
        self.result = {}
        w, h = C.SCREEN_W, C.SCREEN_H
        cx, cy = w // 2, h // 2
        self.pause_btn = ui.Button((w - 80, 12, 64, 58), "", self.toggle_pause, C.GRAY, icon="pause",
                                   hotkeys=(pygame.K_ESCAPE, pygame.K_p))
        self.cp_add = ui.Button((cx - 140, h - 90, 120, 72), "", self.add_checkpoint, C.GREEN, icon="flag",
                                hotkeys=(pygame.K_z,))
        self.cp_del = ui.Button((cx + 20, h - 90, 120, 72), "", self.remove_checkpoint, C.RED, icon="close",
                                hotkeys=(pygame.K_x,))
        self.pause_buttons = [
            ui.Button((cx - 230, cy - 10, 140, 110), "", self.toggle_pause, C.GREEN, icon="play",
                      hotkeys=(pygame.K_SPACE, pygame.K_RETURN)),
            ui.Button((cx - 70, cy - 10, 140, 110), "", self.restart, C.CYAN, icon="retry", hotkeys=(pygame.K_r,)),
            ui.Button((cx + 90, cy - 10, 140, 110), "", self.exit_level, C.RED,
                      icon="home" if self.record else "edit", hotkeys=(pygame.K_q,)),
            ui.Button((cx - 230, cy + 125, 220, 62), "Practice", self.toggle_practice, C.CYAN, 24, icon="flag",
                      hotkeys=(pygame.K_t,)),
            ui.Button((cx + 10, cy + 125, 220, 62), "Music", self.toggle_music, C.PINK, 24, icon="music",
                      hotkeys=(pygame.K_m,)),
        ]
        self.end_buttons = [
            ui.Button((cx - 170, cy + 118, 150, 100), "", self.restart, C.GREEN, icon="retry",
                      hotkeys=(pygame.K_SPACE, pygame.K_RETURN, pygame.K_r)),
            ui.Button((cx + 20, cy + 118, 150, 100), "", self.exit_level, C.ORANGE,
                      icon="home" if self.record else "edit", hotkeys=(pygame.K_ESCAPE, pygame.K_q)),
        ]
        self.respawn(fresh=True)

    # ------------------------------------------------------------ attempts
    def respawn(self, fresh=False):
        """Start a new attempt, or go back to the last checkpoint in practice mode."""
        cp = self.checkpoints[-1] if self.practice and self.checkpoints and not fresh else None
        self.p = cp.copy() if cp else PlayerState()
        self.attempt += 1
        self.attempt_jumps = 0
        self.attempt_time = 0.0
        self.acc = 0.0
        self.trail_t = 0.0
        self.dead_time = None
        self.finished_time = None
        self.fx.clear()
        self.cam.x = self.p.x - C.PLAYER_SCREEN_X
        self.cam.y = self.cam_target()
        self.game.audio.music(self.level.music, restart=not (self.practice and not fresh))

    def cam_target(self):
        if self.p.mode == "ship":
            return 0.0
        return max(0.0, self.p.y + SIZE - (C.GROUND_Y - 150))

    def running(self):
        return self.dead_time is None and self.finished_time is None

    def save_attempt(self, pct, completed=False):
        if not self.record:
            return
        new_best = self.game.save.record_run(self.level.level_id, pct, self.practice, self.attempt_jumps,
                                             completed, self.p.coins)
        if new_best and not completed and int(pct) > 0:
            self.toast.show("New best!  %d%%" % int(pct), C.CYAN if self.practice else C.GOLD, 1.6)
            self.game.audio.play("best", 0.7)

    def save_partial(self):
        """Count an attempt that was abandoned (restart or exit while alive)."""
        if self.running() and self.attempt_time > 0.2:
            self.save_attempt(progress(self.p, self.world))

    def die(self):
        p = self.p
        self.dead_time = 0.0
        self.fx.explode(p.x + SIZE / 2, p.y + SIZE / 2, self.colors)
        self.game.audio.play("death", 0.9)
        if not self.practice:
            self.game.audio.stop_music()
        self.save_attempt(progress(p, self.world))

    def finish(self):
        p = self.p
        self.finished_time = 0.0
        first = bool(self.stats) and not self.stats["completed"] and not self.practice
        self.save_attempt(100, completed=True)
        self.result = {"stars": self.level.stars if first else 0, "jumps": self.attempt_jumps,
                       "time": self.attempt_time}
        for color in (C.GOLD, C.CYAN, C.PINK, C.GREEN, C.WHITE):
            self.fx.burst(p.x, p.y + 2 * T, color, n=14, speed=(200, 800), life=(0.6, 1.4), size=(6, 14),
                          gravity=500)
        self.fx.ring(p.x, p.y + SIZE / 2, C.WHITE, 20, 260, 0.6, 10)
        self.fx.flash, self.fx.flash_color = 0.7, C.WHITE
        self.game.audio.play("complete")
        self.game.audio.stop_music(fade_ms=1200)

    # ------------------------------------------------------------ actions
    def toggle_pause(self):
        if not self.running():
            return
        self.paused = not self.paused
        self.mouse_hold = False
        if self.paused:
            self.game.audio.pause_music()
        else:
            self.game.audio.resume_music()

    def restart(self):
        self.save_partial()
        self.paused = False
        self.checkpoints = []
        self.game.audio.resume_music()
        self.respawn(fresh=True)

    def toggle_practice(self):
        self.save_partial()
        self.practice = not self.practice
        self.paused = False
        self.checkpoints = []
        self.game.audio.resume_music()
        self.respawn(fresh=True)

    def toggle_music(self):
        on = not self.game.save.settings.get("music", True)
        self.game.audio.set_music_enabled(on)
        self.game.save.save()

    def exit_level(self):
        self.save_partial()
        self.game.audio.resume_music()
        self.game.audio.stop_music()
        if self.back:
            self.game.switch(self.back())
        else:
            from .menu import MenuScene
            self.game.switch(MenuScene(self.game))

    def add_checkpoint(self):
        p = self.p
        if self.practice and self.running():
            self.checkpoints.append(p.copy())
            self.fx.ring(p.x + SIZE / 2, p.y + SIZE / 2, C.GREEN, 10, 70, 0.3, 5)
            self.game.audio.play("checkpoint", 0.6)

    def remove_checkpoint(self):
        if self.practice and self.checkpoints:
            self.checkpoints.pop()

    # ------------------------------------------------------------ input
    def hud_buttons(self):
        return [self.pause_btn] + ([self.cp_add, self.cp_del] if self.practice else [])

    def current_buttons(self):
        if self.finished_time is not None:
            return self.end_buttons if self.finished_time >= END_PANEL_DELAY else []
        if self.paused:
            return self.pause_buttons + [self.pause_btn]
        return self.hud_buttons()

    def hold(self):
        if self.input_override is not None:
            return bool(self.input_override())
        keys = pygame.key.get_pressed()
        return self.mouse_hold or any(keys[k] for k in JUMP_KEYS)

    def handle(self, event):
        buttons = self.current_buttons()
        for b in buttons:
            if b.handle(event):
                return
        if event.type == FOCUS_LOST and self.running() and not self.paused:
            self.toggle_pause()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not any(b.rect.collidepoint(event.pos) for b in buttons):
                self.mouse_hold = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.mouse_hold = False

    # ------------------------------------------------------------ simulation
    def on_events(self, events):
        p, fx, audio = self.p, self.fx, self.game.audio
        cx, cy = p.x + SIZE / 2, p.y + SIZE / 2
        for e in events:
            if e == "jump":
                self.attempt_jumps += 1
                fx.burst(cx, p.y, C.WHITE, n=6, speed=(60, 200), life=(0.15, 0.35), size=(4, 8), gravity=300,
                         angle=math.pi, spread=1.6)
            elif e == "land":
                fx.burst(cx, p.y, C.WHITE, n=5, speed=(40, 160), life=(0.1, 0.3), size=(3, 7), gravity=200,
                         angle=math.pi / 2, spread=2.6)
            elif e in ("pad", "orb"):
                if e == "orb":
                    self.attempt_jumps += 1
                fx.ring(cx, cy if e == "orb" else p.y, C.GOLD, 10, 80, 0.3, 5)
                audio.play(e, 0.6)
            elif e == "coin":
                fx.burst(cx, cy, C.GOLD, n=20, speed=(100, 400), life=(0.3, 0.7), size=(5, 10), gravity=500)
                fx.ring(cx, cy, C.GOLD, 10, 110, 0.4, 6)
                audio.play("coin")
            elif e == "portal":
                color = C.PINK if p.mode == "ship" else C.GREEN
                fx.ring(cx, cy, color, 20, 160, 0.45, 8)
                fx.flash, fx.flash_color = 0.35, color
                audio.play("portal", 0.6)
            elif e == "death":
                self.die()
            elif e == "finish":
                self.finish()

    def emit_trail(self, dt):
        p = self.p
        self.trail_t += dt
        while self.trail_t > 0.02:
            self.trail_t -= 0.02
            if p.mode == "ship":
                self.fx.emit(p.x + 4, p.y + SIZE * 0.35, -160, random.uniform(-40, 40), 0.35, self.colors[1], 9)
            elif p.on_ground:
                self.fx.emit(p.x + 2, p.y + 3, -120, random.uniform(20, 90), 0.25, C.WHITE, 6, 300)

    def update(self, dt):
        self.t += dt
        settings = self.game.save.settings
        self.pause_buttons[3].label = "Normal" if self.practice else "Practice"
        self.pause_buttons[4].color = C.PINK if settings.get("music", True) else C.GRAY
        for b in self.current_buttons():
            b.update(dt)
        self.toast.update(dt)
        if self.paused:
            return
        self.fx.update(dt)
        if self.finished_time is not None:
            self.finished_time += dt
            return
        if self.dead_time is not None:
            self.dead_time += dt
            if self.dead_time >= RESPAWN_DELAY:
                self.respawn()
            return
        hold = self.hold()
        self.acc += dt
        n = int(self.acc * C.PHYSICS_HZ + 1e-6)
        self.acc -= n * STEP
        p = self.p
        for _ in range(n):
            step(p, hold, self.world)
            if p.events:
                events = list(p.events)
                p.events.clear()
                self.on_events(events)
            if p.dead or p.finished:
                break
        self.attempt_time += dt
        self.cam.x = p.x - C.PLAYER_SCREEN_X
        self.cam.y += (self.cam_target() - self.cam.y) * min(1.0, dt * 6)
        if self.running():
            self.emit_trail(dt)

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        p, cam = self.p, self.cam
        bg, ground = self.level.theme_at(p.x / T)
        D.draw_background(surf, cam, bg, ground, ceiling=(p.mode == "ship"))
        self.art.draw(surf, cam, self.t, bg, hidden=p.coins, used=p.used, ghost=self.owned_coins)
        if not (self.practice and self.checkpoints):
            ui.draw_text(surf, "Attempt %d" % self.attempt, 52, (int(cam.sx(6 * T)), int(cam.sy(5 * T))))
        for cp in self.checkpoints:
            x, y = cam.point(cp.x + SIZE / 2, cp.y + SIZE / 2)
            pts = [(x, y - 17), (x + 12, y), (x, y + 17), (x - 12, y)]
            pygame.draw.polygon(surf, C.GREEN, pts)
            pygame.draw.polygon(surf, C.OUTLINE, pts, 3)
        if self.running():
            D.draw_player(surf, cam, p, self.icon)
        self.fx.draw(surf, cam)

        pct = progress(p, self.world)
        ui.progress_bar(surf, (C.SCREEN_W // 2 - 250, 24, 500, 22), pct / 100.0, C.CYAN if self.practice else C.GREEN)
        ui.draw_text(surf, "%d%%" % int(pct), 26, (C.SCREEN_W // 2 + 272, 35), anchor="midleft")
        if self.practice:
            ui.draw_text(surf, "PRACTICE MODE", 22, (C.SCREEN_W // 2, 70), C.CYAN)
            ui.draw_text(surf, "Z: checkpoint   X: remove", 18, (C.SCREEN_W // 2, C.SCREEN_H - 104))
        if not self.paused and self.finished_time is None:
            for b in self.hud_buttons():
                b.draw(surf)
        self.toast.draw(surf, (C.SCREEN_W // 2, 140), 40)
        if self.paused:
            self.draw_pause(surf)
        if self.finished_time is not None and self.finished_time >= END_PANEL_DELAY:
            self.draw_end(surf)

    def draw_pause(self, surf):
        ui.dim(surf, 150)
        rect = pygame.Rect(0, 0, 560, 430)
        rect.center = (C.SCREEN_W // 2, C.SCREEN_H // 2 + 20)
        ui.panel(surf, rect)
        ui.draw_text(surf, self.level.name, 44, (rect.centerx, rect.y + 52))
        if self.stats:
            ui.progress_bar(surf, (rect.x + 60, rect.y + 100, rect.w - 120, 26), self.stats["best"] / 100.0, C.GREEN,
                            "Normal  %d%%" % self.stats["best"], 18)
            ui.progress_bar(surf, (rect.x + 60, rect.y + 142, rect.w - 120, 26), self.stats["practice"] / 100.0,
                            C.CYAN, "Practice  %d%%" % self.stats["practice"], 18)
        else:
            ui.draw_text(surf, "Test play from the editor", 24, (rect.centerx, rect.y + 120))
        for b in self.pause_buttons:
            b.draw(surf)

    def draw_end(self, surf):
        ui.dim(surf, 140)
        rect = pygame.Rect(0, 0, 660, 440)
        rect.center = (C.SCREEN_W // 2, C.SCREEN_H // 2 + 10)
        ui.panel(surf, rect)
        r = self.result
        title = "PRACTICE COMPLETE!" if self.practice else "LEVEL COMPLETE!"
        ui.draw_text(surf, title, 54, (rect.centerx, rect.y + 62), C.GOLD)
        minutes, seconds = divmod(r.get("time", 0.0), 60)
        ui.draw_text(surf, "Attempt %d      Jumps %d      Time %d:%04.1f" % (self.attempt, r.get("jumps", 0),
                                                                         minutes, seconds), 26,
                     (rect.centerx, rect.y + 132))
        coins = self.level.coin_ids
        for k, cid in enumerate(coins):
            ui.draw_coin_slot(surf, (int(rect.centerx + (k - (len(coins) - 1) / 2) * 58), rect.y + 192), 20,
                              cid in self.p.coins)
        if r.get("stars"):
            ui.draw_star(surf, (rect.centerx - 34, rect.y + 252), 24)
            ui.draw_text(surf, "+%d" % r["stars"], 38, (rect.centerx - 2, rect.y + 252), C.GOLD, anchor="midleft")
        for b in self.end_buttons:
            b.draw(surf)
