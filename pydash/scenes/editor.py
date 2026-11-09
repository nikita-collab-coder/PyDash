"""Level editor: place, erase and rotate objects on the grid, set level options and test-play."""
import pygame

from .. import config as C
from .. import skins
from .. import draw as D
from .. import ui
from ..game import Scene
from ..level import DIFFICULTIES, OBJECT_TYPES, LevelObject, save_level

T = C.TILE
GY = C.EDITOR_GROUND_Y
TOP_BAR = 44
TOOLBAR_Y = GY + 26
MAX_ROW = C.CEILING_ROWS - 1
PALETTE = list(OBJECT_TYPES)
THEME_NAMES = list(C.THEMES)
STARS = {"easy": 1, "normal": 2, "hard": 3, "harder": 5, "insane": 8}
UNDO_LIMIT = 100
MAX_COINS = 3
SCROLL_SPEED = 900.0
HINT = ("LMB place  |  RMB erase  |  R rotate  |  1-9, Q/E pick  |  Wheel, A/D scroll  |  W/S up/down  |  "
        "Ctrl+Z undo  |  P test  |  Ctrl+S save")

_images = {}


def object_image(kind, rot, bg, alpha=255):
    """An object drawn on its own transparent surface (10 px margin), cached."""
    key = (kind, rot, tuple(bg), alpha)
    img = _images.get(key)
    if img is None:
        h = OBJECT_TYPES[kind]["h"]
        img = pygame.Surface((T + 20, h * T + 20), pygame.SRCALPHA)
        cam = D.Camera(ground_y=h * T + 10)
        cam.x = -10
        D.draw_object(img, cam, LevelObject(kind, 0, 0, rot), 0.0, bg)
        if alpha < 255:
            img.set_alpha(alpha)
        if len(_images) > 300:
            _images.clear()
        _images[key] = img
    return img


class EditorScene(Scene):
    music = None

    def __init__(self, game, level):
        super().__init__(game)
        self.level = level
        self.art = D.LevelArt(level)
        self.cam = D.Camera(ground_y=GY)
        self.cam.x = -2 * T
        self.t = 0.0
        self.toast = ui.Toast()
        self.selected = 0
        self.rot = 0
        self.mode = "build"
        self.undo, self.redo = [], []
        self.dirty = False
        self.hover = None
        self.painting = None  # "build" / "erase" while a mouse button is held
        self.stroke = None
        self.last_cell = None
        self.panning = False
        self.typing = False
        self.name_before = level.name
        self._palette = {}
        self.start_img = D.cube_sprite(skins.style(game.save.settings)).copy()
        self.start_img.set_alpha(110)
        y1, y2 = TOOLBAR_Y + 12, TOOLBAR_Y + 100
        self.palette_buttons = [ui.Button((24 + i * 84, y1, 76, 76), "", lambda i=i: self.select(i), (44, 56, 104))
                                for i in range(len(PALETTE))]
        self.build_btn = ui.Button((790, y1, 130, 76), "Build", lambda: self.set_mode("build"), C.GREEN, 26)
        self.erase_btn = ui.Button((928, y1, 130, 76), "Erase", lambda: self.set_mode("erase"), C.RED, 26)
        self.rotate_btn = ui.Button((1066, y1, 190, 76), "Rotate", self.rotate, C.CYAN, 24)
        self.theme_btn = ui.Button((24, y2, 200, 68), "", self.cycle_theme, C.PINK, 22)
        self.zone_btn = ui.Button((232, y2, 120, 68), "Zone", self.cycle_zone, C.PINK, 22)
        self.diff_btn = ui.Button((360, y2, 220, 68), "", self.cycle_difficulty, C.ORANGE, 22)
        self.song_btn = ui.Button((588, y2, 130, 68), "", self.next_song, C.PINK, 22)
        self.name_btn = ui.Button((726, y2, 130, 68), "Rename", self.start_rename, C.CYAN, 22)
        self.undo_btn = ui.Button((864, y2, 100, 68), "Undo", self.do_undo, C.GRAY, 22)
        self.test_btn = ui.Button((1000, y2, 76, 68), "", self.test, C.GREEN, icon="play")
        self.save_btn = ui.Button((1088, y2, 76, 68), "", self.save, C.CYAN, icon="check")
        self.exit_btn = ui.Button((1176, y2, 80, 68), "", self.leave, C.RED, icon="home")
        self.buttons = self.palette_buttons + [
            self.build_btn, self.erase_btn, self.rotate_btn, self.theme_btn, self.zone_btn, self.diff_btn,
            self.song_btn, self.name_btn, self.undo_btn, self.test_btn, self.save_btn, self.exit_btn]

    # ------------------------------------------------------------ grid helpers
    def cell_at(self, pos):
        mx, my = pos
        if my < TOP_BAR or my >= TOOLBAR_Y:
            return None
        wx = mx + self.cam.x
        wy = self.cam.ground_y - my + self.cam.y
        cx, cy = int(wx // T), int(wy // T)
        if cx < 0 or cy < 0 or cy > MAX_ROW:
            return None
        return cx, cy

    def place_rot(self, kind):
        return self.rot if OBJECT_TYPES[kind]["rotatable"] else 0

    def objects_in(self, cx, y0, h):
        """Indices of objects in column cx whose footprint overlaps rows y0 .. y0 + h - 1."""
        found = []
        for i, o in enumerate(self.level.objects):
            if o.x == cx:
                oh = OBJECT_TYPES[o.type]["h"]
                if o.y < y0 + h and y0 < o.y + oh:
                    found.append(i)
        return found

    def snapshot(self):
        return [(o.type, o.x, o.y, o.rot) for o in self.level.objects]

    def restore(self, snap):
        self.level.objects = [LevelObject(*s) for s in snap]
        self.art.rebuild()
        self.dirty = True

    def changed(self):
        self.art.rebuild()
        self.dirty = True

    def place(self, cx, cy):
        kind = PALETTE[self.selected]
        h = OBJECT_TYPES[kind]["h"]
        cy = min(cy, MAX_ROW - h + 1)
        rot = self.place_rot(kind)
        hits = self.objects_in(cx, cy, h)
        objs = self.level.objects
        if len(hits) == 1:
            o = objs[hits[0]]
            if (o.type, o.x, o.y, o.rot) == (kind, cx, cy, rot):
                return
        if kind == "coin" and sum(o.type == "coin" for o in objs) - sum(objs[i].type == "coin" for i in hits) >= MAX_COINS:
            self.toast.show("A level can have at most %d coins" % MAX_COINS, C.ORANGE)
            return
        for i in reversed(hits):
            del objs[i]
        objs.append(LevelObject(kind, cx, cy, rot))
        self.changed()

    def erase(self, cx, cy):
        hits = self.objects_in(cx, cy, 1)
        if hits:
            del self.level.objects[hits[-1]]
            self.changed()

    def paint(self, cell):
        if cell is None or cell == self.last_cell or self.painting is None:
            return
        self.last_cell = cell
        if self.painting == "build":
            self.place(*cell)
        else:
            self.erase(*cell)

    def begin_stroke(self, kind, cell):
        self.painting = kind
        self.stroke = self.snapshot()
        self.last_cell = None
        self.paint(cell)

    def end_stroke(self):
        if self.stroke is not None and self.stroke != self.snapshot():
            self.undo.append(self.stroke)
            del self.undo[:-UNDO_LIMIT]
            self.redo.clear()
        self.painting = None
        self.stroke = None
        self.last_cell = None

    def clamp_camera(self):
        self.cam.x = max(-4 * T, min(self.cam.x, (self.level.length + 10) * T))
        self.cam.y = max(0.0, min(self.cam.y, 2.0 * T))

    # ------------------------------------------------------------ actions
    def select(self, i):
        self.selected = i % len(PALETTE)
        self.mode = "build"

    def set_mode(self, mode):
        self.mode = mode

    def rotate(self):
        self.rot = (self.rot + 90) % 360
        if not OBJECT_TYPES[PALETTE[self.selected]]["rotatable"]:
            self.toast.show("%s cannot be rotated" % OBJECT_TYPES[PALETTE[self.selected]]["label"], C.ORANGE, 1.4)

    def do_undo(self):
        if self.undo:
            self.redo.append(self.snapshot())
            self.restore(self.undo.pop())
        else:
            self.toast.show("Nothing to undo", C.GRAY, 1.2)

    def do_redo(self):
        if self.redo:
            self.undo.append(self.snapshot())
            self.restore(self.redo.pop())

    def base_zone(self):
        if not self.level.colors:
            self.level.colors.append({"x": 0, "theme": "blue"})
        return min(self.level.colors, key=lambda z: z.get("x", 0))

    def cycle_theme(self):
        zone = self.base_zone()
        cur = zone.get("theme")
        k = (THEME_NAMES.index(cur) + 1) % len(THEME_NAMES) if cur in THEME_NAMES else 0
        zone.clear()
        zone.update({"x": 0, "theme": THEME_NAMES[k]})
        self.dirty = True

    def cycle_zone(self):
        col = int((self.cam.x + C.SCREEN_W / 2) // T)
        if col <= 0:
            self.toast.show("Scroll right to add a color zone", C.ORANGE)
            return
        zones = self.level.colors
        zone = next((z for z in zones if z.get("x", 0) == col), None)
        name = THEME_NAMES[0]
        if zone is None:
            zones.append({"x": col, "theme": name})
        else:
            cur = zone.get("theme")
            k = THEME_NAMES.index(cur) + 1 if cur in THEME_NAMES else 0
            if k >= len(THEME_NAMES):
                zones.remove(zone)
                name = None
            else:
                name = THEME_NAMES[k]
                zone.clear()
                zone.update({"x": col, "theme": name})
        self.dirty = True
        self.toast.show("Color zone at column %d: %s" % (col, name.capitalize()) if name else "Color zone removed")

    def cycle_difficulty(self):
        cur = self.level.difficulty
        k = (DIFFICULTIES.index(cur) + 1) % len(DIFFICULTIES) if cur in DIFFICULTIES else 0
        self.level.difficulty = DIFFICULTIES[k]
        self.level.stars = STARS[DIFFICULTIES[k]]
        self.dirty = True

    def next_song(self):
        m = dict(self.level.music)
        seed = int(m.get("seed", 1)) + 1
        m.update(seed=seed, bpm=118 + (seed * 7) % 36, root=52 + (seed * 5) % 9)
        self.level.music = m
        self.dirty = True
        self.game.audio.prepare([m])
        self.toast.show("Song %d  (%d BPM)" % (seed, m["bpm"]))

    def start_rename(self):
        self.typing = True
        self.name_before = self.level.name
        self.toast.show("Type a name, then press Enter", seconds=2.5)

    def stop_rename(self, cancel=False):
        self.typing = False
        self.level.name = self.level.name.strip()
        if cancel or not self.level.name:
            self.level.name = self.name_before
        if self.level.name != self.name_before:
            self.dirty = True

    def save(self, quiet=False):
        try:
            save_level(self.level)
        except OSError as exc:
            self.toast.show("Could not save: %s" % exc, C.RED, 3.0)
            return False
        self.dirty = False
        if not quiet:
            self.toast.show("Saved", C.GREEN, 1.2)
        return True

    def test(self):
        from .play import PlayScene
        self.end_stroke()
        self.save(quiet=True)
        self.game.switch(PlayScene(self.game, self.level.copy(), back=lambda: self, record=False))

    def leave(self):
        """Save if needed and return to My levels (Scene.exit is the scene-switch hook)."""
        from .select import SelectScene
        if self.dirty and not self.save(quiet=True):
            return
        self.game.switch(SelectScene(self.game, "custom"))

    # ------------------------------------------------------------ input
    def handle_typing(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.stop_rename()
            elif event.key == pygame.K_ESCAPE:
                self.stop_rename(cancel=True)
            elif event.key == pygame.K_BACKSPACE:
                self.level.name = self.level.name[:-1]
            else:
                ch = getattr(event, "unicode", "")
                if ch and ch.isprintable() and len(self.level.name) < 24:
                    self.level.name += ch
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.stop_rename()
        return False

    def handle_key(self, event):
        key, mods = event.key, pygame.key.get_mods()
        ctrl, shift = mods & pygame.KMOD_CTRL, mods & pygame.KMOD_SHIFT
        if ctrl and key == pygame.K_z:
            self.do_redo() if shift else self.do_undo()
        elif ctrl and key == pygame.K_y:
            self.do_redo()
        elif ctrl and key == pygame.K_s:
            self.save()
        elif ctrl:
            return
        elif pygame.K_1 <= key <= pygame.K_9:
            self.select(key - pygame.K_1)
        elif key == pygame.K_q:
            self.select(self.selected - 1)
        elif key == pygame.K_e:
            self.select(self.selected + 1)
        elif key == pygame.K_r:
            self.rotate()
        elif key == pygame.K_b:
            self.set_mode("build")
        elif key in (pygame.K_x, pygame.K_DELETE):
            self.set_mode("erase")
        elif key in (pygame.K_p, pygame.K_RETURN):
            self.test()
        elif key == pygame.K_ESCAPE:
            self.leave()
        elif key == pygame.K_HOME:
            self.cam.x = -2 * T
        elif key == pygame.K_END:
            self.cam.x = (self.level.length - 12) * T

    def handle(self, event):
        if self.typing and self.handle_typing(event):
            return
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            self.handle_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            cell = self.cell_at(event.pos)
            if event.button == 2:
                self.panning = True
            elif event.button in (1, 3) and cell is not None and self.painting is None:
                kind = "erase" if event.button == 3 or self.mode == "erase" else "build"
                self.begin_stroke(kind, cell)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                self.panning = False
            elif event.button in (1, 3):
                self.end_stroke()
        elif event.type == pygame.MOUSEMOTION:
            if self.panning:
                self.cam.x -= event.rel[0]
                self.cam.y += event.rel[1]
                self.clamp_camera()
            self.paint(self.cell_at(event.pos))
        elif event.type == pygame.MOUSEWHEEL:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                self.cam.y += event.y * T
            else:
                self.cam.x += (event.x - event.y) * 2 * T
            self.clamp_camera()

    def update(self, dt):
        self.t += dt
        if not self.typing and not pygame.key.get_mods() & pygame.KMOD_CTRL:
            keys = pygame.key.get_pressed()
            dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = int(keys[pygame.K_UP] or keys[pygame.K_w]) - int(keys[pygame.K_DOWN] or keys[pygame.K_s])
            fast = 2.0 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1.0
            self.cam.x += dx * SCROLL_SPEED * fast * dt
            self.cam.y += dy * SCROLL_SPEED * 0.5 * dt
        self.clamp_camera()
        self.hover = self.cell_at(pygame.mouse.get_pos())
        self.paint(self.hover)
        base = self.base_zone().get("theme", "custom")
        self.theme_btn.label = "Theme: %s" % base.capitalize()
        self.diff_btn.label = self.level.difficulty.capitalize()
        self.diff_btn.color = C.DIFFICULTY_COLORS.get(self.level.difficulty, C.ORANGE)
        self.song_btn.label = "Song %d" % int(self.level.music.get("seed", 1))
        self.rotate_btn.label = "Rotate: %d" % self.rot
        self.build_btn.color = C.GREEN if self.mode == "build" else C.shade(C.GREEN, 0.5)
        self.erase_btn.color = C.RED if self.mode == "erase" else C.shade(C.RED, 0.5)
        self.undo_btn.color = C.GRAY if self.undo else C.shade(C.GRAY, 0.6)
        for b in self.buttons:
            b.update(dt)
        self.toast.update(dt)

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        cam = self.cam
        bg, ground = self.level.theme_at((cam.x + C.SCREEN_W / 2) / T)
        D.draw_background(surf, cam, bg, ground)
        self.draw_grid(surf, bg)
        self.art.draw(surf, cam, self.t, bg)
        self.draw_markers(surf)
        self.draw_hover(surf, bg)
        self.draw_toolbar(surf)
        self.draw_topbar(surf)
        self.toast.draw(surf, (C.SCREEN_W // 2, 92), 30)

    def draw_grid(self, surf, bg):
        cam, w = self.cam, C.SCREEN_W
        top, bottom = int(cam.sy(C.CEILING_ROWS * T)), int(cam.sy(0))
        left = int(cam.sx(0))
        if left > 0:
            pygame.draw.rect(surf, C.shade(bg, 0.6), (0, max(0, top), left, bottom - max(0, top)))
        color = C.lerp_color(bg, C.WHITE, 0.13)
        first = max(0, int(cam.x // T))
        for col in range(first, int((cam.x + w) // T) + 2):
            x = int(cam.sx(col * T))
            pygame.draw.line(surf, color, (x, max(0, top)), (x, bottom))
        for row in range(1, C.CEILING_ROWS + 1):
            y = int(cam.sy(row * T))
            pygame.draw.line(surf, color, (max(0, left), y), (w, y))
        pygame.draw.line(surf, C.lerp_color(bg, C.RED, 0.6), (max(0, left), top), (w, top), 2)

    def draw_markers(self, surf):
        cam = self.cam
        sx = int(cam.sx(0))
        if -T < sx < C.SCREEN_W:
            surf.blit(self.start_img, cam.box(0, 0, T, T))
            ui.draw_text(surf, "Start", 20, (sx + T // 2, int(cam.sy(T)) - 16))
        for zone in self.level.colors:
            x = zone.get("x", 0)
            px = int(cam.sx(x * T))
            if x > 0 and -60 < px < C.SCREEN_W + 60:
                col = C.lerp_color(self.level._zone_colors(zone)[0], C.WHITE, 0.45)
                pygame.draw.line(surf, col, (px, TOP_BAR + 6), (px, int(cam.sy(0))), 3)
                ui.draw_text(surf, zone.get("theme", "custom").capitalize(), 18, (px + 8, TOP_BAR + 20),
                             col, anchor="midleft")

    def draw_hover(self, surf, bg):
        if self.hover is None or self.typing:
            return
        cx, cy = self.hover
        cam = self.cam
        if self.painting == "erase" or (self.painting is None and self.mode == "erase"):
            pygame.draw.rect(surf, C.RED, cam.box(cx * T, cy * T, T, T), 3)
            return
        kind = PALETTE[self.selected]
        h = OBJECT_TYPES[kind]["h"]
        cy = min(cy, MAX_ROW - h + 1)
        ghost = object_image(kind, self.place_rot(kind), bg, 150)
        surf.blit(ghost, cam.box(cx * T - 10, cy * T - 10, T + 20, h * T + 20).topleft)
        pygame.draw.rect(surf, C.WHITE, cam.box(cx * T, cy * T, T, h * T), 2)

    def palette_image(self, i, bg):
        kind = PALETTE[i]
        key = (i, tuple(bg), self.place_rot(kind))
        img = self._palette.get(key)
        if img is None:
            src = object_image(kind, self.place_rot(kind), bg)
            w, h = src.get_size()
            k = min(64.0 / w, 64.0 / h)
            img = pygame.transform.smoothscale(src, (max(1, int(w * k)), max(1, int(h * k))))
            if len(self._palette) > 120:
                self._palette.clear()
            self._palette[key] = img
        return img

    def draw_toolbar(self, surf):
        ui.panel(surf, pygame.Rect(10, TOOLBAR_Y, C.SCREEN_W - 20, C.SCREEN_H - TOOLBAR_Y - 8), alpha=228, radius=18)
        for b in self.buttons:
            b.draw(surf)
        bg = self.level.theme_at(0)[0]
        for i, b in enumerate(self.palette_buttons):
            img = self.palette_image(i, bg)
            surf.blit(img, img.get_rect(center=b.rect.center))
            if i == self.selected and self.mode == "build":
                pygame.draw.rect(surf, C.GOLD, b.rect.inflate(8, 8), 4, border_radius=14)
            ui.draw_text(surf, str(i + 1), 16, (b.rect.x + 11, b.rect.y + 11))
        ui.draw_text(surf, HINT, 16, (C.SCREEN_W // 2, C.SCREEN_H - 30))

    def draw_topbar(self, surf):
        layer = pygame.Surface((C.SCREEN_W, TOP_BAR), pygame.SRCALPHA)
        layer.fill((8, 12, 30, 170))
        surf.blit(layer, (0, 0))
        if self.typing:
            cursor = "_" if int(self.t * 2.5) % 2 == 0 else " "
            ui.draw_text(surf, "Name: " + self.level.name + cursor, 24, (16, TOP_BAR // 2), C.GOLD, anchor="midleft")
        else:
            ui.draw_text(surf, self.level.name, 24, (16, TOP_BAR // 2), anchor="midleft")
        col = int((self.cam.x + C.SCREEN_W / 2) // T)
        kind = OBJECT_TYPES[PALETTE[self.selected]]["label"]
        info = "%s   |   Column %d   |   Objects %d   |   Length %d" % (kind, col, len(self.level.objects),
                                                                    self.level.length)
        ui.draw_text(surf, info, 20, (C.SCREEN_W // 2 + 40, TOP_BAR // 2))
        state, color = ("Unsaved", C.ORANGE) if self.dirty else ("Saved", C.GREEN)
        ui.draw_text(surf, state, 20, (C.SCREEN_W - 16, TOP_BAR // 2), color, anchor="midright")
