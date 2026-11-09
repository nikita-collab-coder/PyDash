"""Headless end-to-end test: drives every screen with synthetic input and saves screenshots.

Run from the project folder:   python tools/smoke_test.py [screenshot-folder]
It uses a temporary save folder, so your own progress and levels are not touched.
"""
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
TMP = tempfile.mkdtemp(prefix="pydash_test_")
os.environ["PYDASH_USER_DIR"] = TMP
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from pydash import config as C  # noqa: E402
from pydash import solver, ui  # noqa: E402
from pydash.game import Game  # noqa: E402
from pydash.level import list_custom_levels  # noqa: E402
from pydash.scenes.editor import GY, TOOLBAR_Y, EditorScene  # noqa: E402
from pydash.scenes.icons import IconsScene  # noqa: E402
from pydash.scenes.menu import MenuScene  # noqa: E402
from pydash.scenes.play import PlayScene  # noqa: E402
from pydash.scenes.select import SelectScene  # noqa: E402

SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)
T = C.TILE
DT = 1.0 / C.FPS
started = time.time()
game = Game(headless=True)


def run(frames=1, events=()):
    events = list(events)
    for i in range(frames):
        game.frame(DT, events if i == 0 else [])


def key(k, char=""):
    return [pygame.event.Event(pygame.KEYDOWN, key=k, mod=pygame.key.get_mods(), unicode=char, scancode=0)]


def click(pos, button=1):
    pygame.mouse.set_pos(pos)
    return [pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=button)]


def shot(name):
    pygame.image.save(game.screen, os.path.join(SHOTS, name + ".png"))


def check(cond, msg):
    if not cond:
        raise AssertionError("FAILED: " + msg)
    print("ok   " + msg)


def ctrl(k):
    pygame.key.set_mods(pygame.KMOD_LCTRL)
    run(1, key(k))
    pygame.key.set_mods(0)


# ---------------------------------------------------------------- main menu
check(isinstance(game.scene, MenuScene), "the game starts in the main menu")
run(45)
shot("01_menu")
run(1, key(pygame.K_i))
check(isinstance(game.scene, IconsScene), "I opens the Icons screen")
run(20)
shot("01b_icons")
icon = game.save.settings["icon"]
run(1, key(pygame.K_RIGHT))
check(game.save.settings["icon"] == (icon + 1) % len(C.ICON_DESIGNS), "the right arrow picks the next cube design")
run(1, click(game.scene.design_rect(11).center))
check(game.save.settings["icon"] == 11, "clicking a design selects it")
run(1, click(game.scene.swatch_rect(0, 7).center))
run(1, click(game.scene.swatch_rect(1, 0).center))
check((game.save.settings["color1"], game.save.settings["color2"]) == (7, 0), "clicking swatches sets both colours")
run(1, key(pygame.K_x))
check((game.save.settings["color1"], game.save.settings["color2"]) == (0, 7), "X swaps the two colours")
run(10)
shot("01c_icons_robot")
run(1, key(pygame.K_ESCAPE))
check(isinstance(game.scene, MenuScene), "Esc returns from Icons to the main menu")
run(20)
run(1, key(pygame.K_m))
check(game.save.settings["music"] is False, "M turns the music off")
run(1, key(pygame.K_m))
check(game.save.settings["music"] is True, "M turns the music back on")

# ---------------------------------------------------------------- level select
run(1, key(pygame.K_RETURN))
check(isinstance(game.scene, SelectScene) and game.scene.tab == "main", "Enter opens the level select")
run(30)
shot("02_select")
run(1, key(pygame.K_3))
check(isinstance(game.scene, IconsScene), "3 opens the Icons tab from the level select")
run(5)
run(1, key(pygame.K_ESCAPE))
check(isinstance(game.scene, SelectScene) and game.scene.tab == "main", "Esc returns from Icons to the level select")
run(30)
run(1, key(pygame.K_RIGHT))
run(30)
check(game.scene.index == 1, "the right arrow selects the next level")
shot("03_select_level2")
run(1, key(pygame.K_LEFT))
run(10)
run(1, key(pygame.K_RETURN))
check(isinstance(game.scene, PlayScene), "Enter starts the selected level")

# ---------------------------------------------------------------- beat level 1 with the solver's inputs
level = game.levels[0]
res = solver.solve(level)
inputs = getattr(res, "inputs", None)
if inputs is None and isinstance(res, tuple):
    inputs = next((v for v in res if isinstance(v, (list, tuple))), None)
check(bool(inputs), "the solver finds a route through %s (%d frames)" % (level.name, len(inputs or [])))
frame = {"i": 0}


def replay_hold():
    i = frame["i"]
    frame["i"] += 1
    return bool(inputs[i]) if i < len(inputs) else False


scene = PlayScene(game, level, back=lambda: SelectScene(game, "main", 0))
scene.input_override = replay_hold
game.switch(scene)
for f in range(len(inputs) + 30):
    run(1)
    if f in (150, 420):
        shot("04_play_%d" % f)
    if scene.p.mode == "ship" and not os.path.exists(os.path.join(SHOTS, "05_ship.png")):
        run(20)
        shot("05_ship")
    if not scene.running():
        break
check(scene.finished_time is not None and not scene.p.dead, "replaying the route completes %s" % level.name)
run(70)
shot("06_complete")
stats = game.save.stats(level.level_id)
check(stats["completed"] and stats["best"] == 100, "the completion is saved (100%, completed)")
check(game.save.total_stars(game.levels) == level.stars, "the level's stars are awarded")
run(1, key(pygame.K_ESCAPE))
check(isinstance(game.scene, SelectScene), "Esc on the results screen returns to the level select")

# ---------------------------------------------------------------- practice mode, death, checkpoints, pause
scene = PlayScene(game, game.levels[1], practice=True, back=lambda: SelectScene(game, "main", 1))
scene.input_override = lambda: False
game.switch(scene)
run(20)
run(1, key(pygame.K_z))
check(len(scene.checkpoints) == 1, "Z places a practice checkpoint")
for _ in range(900):
    run(1)
    if scene.dead_time is not None:
        break
check(scene.dead_time is not None, "running without jumping crashes into an obstacle")
run(8)
shot("07_death")
for _ in range(120):
    run(1)
    if scene.running():
        break
check(scene.running() and abs(scene.p.x - scene.checkpoints[0].x) < 40, "practice mode respawns at the checkpoint")
check(scene.attempt == 2, "the attempt counter goes up")
run(1, key(pygame.K_ESCAPE))
check(scene.paused, "Esc pauses the game")
x = scene.p.x
run(20)
check(scene.p.x == x, "nothing moves while paused")
shot("08_pause")
run(1, key(pygame.K_ESCAPE))
check(not scene.paused, "Esc resumes")
run(1, key(pygame.K_ESCAPE))
run(1, key(pygame.K_q))
check(isinstance(game.scene, SelectScene), "Quit in the pause menu returns to the level select")
check(game.save.stats(game.levels[1].level_id)["practice"] > 0, "practice progress is saved")

# ---------------------------------------------------------------- level editor
run(1, key(pygame.K_2))
check(game.scene.tab == "custom", "2 opens the My levels tab")
run(10)
shot("09_my_levels_empty")
run(1, key(pygame.K_n))
ed = game.scene
check(isinstance(ed, EditorScene), "New level opens the editor")


def cell(cx, cy):
    return (int(cx * T - ed.cam.x + T / 2), int(GY - (cy + 0.5) * T + ed.cam.y))


def place(slot, cx, cy):
    ed.cam.x = max(-2 * T, cx * T - 600)
    run(1, key(pygame.K_1 + slot))
    run(1, click(cell(cx, cy)))


def find_buttons(scene, icon):
    found = []

    def visit(obj):
        if isinstance(obj, ui.Button):
            found.append(obj)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                visit(item)
        elif isinstance(obj, dict):
            for item in obj.values():
                visit(item)

    for value in vars(scene).values():
        visit(value)
    return sorted((b for b in found if b.icon == icon and not b.label), key=lambda b: (b.rect.y, b.rect.x))


for slot, cx, cy in [(0, 8, 0), (2, 14, 0), (4, 20, 0), (5, 24, 2), (7, 30, 1), (8, 40, 1), (0, 44, 0)]:
    place(slot, cx, cy)
check(len(ed.level.objects) == 7, "clicking places the selected objects")
ed.cam.x = 0
run(1, key(pygame.K_3))
run(1, key(pygame.K_r))
run(1, key(pygame.K_r))
run(1, click(cell(16, 3)))
check(ed.level.objects[-1].type == "spike" and ed.level.objects[-1].rot == 180, "R rotates spikes")
run(1, key(pygame.K_1))
pygame.mouse.set_pos(cell(10, 0))
events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=cell(10, 0), button=1)]
for cx in (11, 12):
    events.append(pygame.event.Event(pygame.MOUSEMOTION, pos=cell(cx, 0), rel=(T, 0), buttons=(1, 0, 0)))
events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=cell(12, 0), button=1))
run(1, events)
count = len(ed.level.objects)
check(count == 11, "dragging paints a row of blocks")
run(1, click(cell(12, 0), button=3))
check(len(ed.level.objects) == count - 1, "right click erases")
ctrl(pygame.K_z)
check(len(ed.level.objects) == count, "Ctrl+Z undoes the erase")
for cx in (26, 27, 28, 29):
    place(6, cx, 3)
check(sum(o.type == "coin" for o in ed.level.objects) == 3, "a level is limited to 3 coins")
run(1, click(ed.name_btn.rect.center))
check(ed.typing, "Rename starts typing")
for _ in range(20):
    run(1, key(pygame.K_BACKSPACE))
for ch in "Test Run!":
    run(1, key(pygame.K_a, ch))
run(1, key(pygame.K_RETURN))
check(ed.level.name == "Test Run!" and not ed.typing, "typing renames the level")
theme = ed.base_zone()["theme"]
run(1, click(ed.theme_btn.rect.center))
check(ed.base_zone()["theme"] != theme, "the Theme button changes the colors")
ed.cam.x = 20 * T
run(1, click(ed.zone_btn.rect.center))
check(len(ed.level.colors) == 2, "the Zone button adds a color zone")
seed = ed.level.music["seed"]
run(1, click(ed.song_btn.rect.center))
check(ed.level.music["seed"] == seed + 1, "the Song button picks another song")
run(1, [pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False)])
run(1, click(ed.diff_btn.rect.center))
ed.cam.x = 4 * T
pygame.mouse.set_pos(cell(18, 1))
run(5)
shot("10_editor")
ctrl(pygame.K_s)
saved = list_custom_levels()
check(len(saved) == 1 and len(saved[0].objects) == len(ed.level.objects) and saved[0].name == "Test Run!",
      "Ctrl+S saves the level file")
run(1, key(pygame.K_p))
check(isinstance(game.scene, PlayScene) and not game.scene.record, "P test-plays the level")
run(40)
shot("11_editor_test")
run(1, key(pygame.K_ESCAPE))
run(1, key(pygame.K_q))
check(game.scene is ed, "leaving the test returns to the same editor")
run(1, key(pygame.K_ESCAPE))
check(isinstance(game.scene, SelectScene) and game.scene.tab == "custom", "Esc leaves the editor")
run(10)
shot("12_my_levels")
plays = find_buttons(game.scene, "play")
check(bool(plays), "each custom level row has a play button")
run(1, click(plays[0].rect.center))
check(isinstance(game.scene, PlayScene) and game.scene.record, "the row's play button starts the custom level")
run(30)
run(1, key(pygame.K_ESCAPE))
run(1, key(pygame.K_q))
run(2)
trash = find_buttons(game.scene, "trash")
check(bool(trash), "each custom level row has a delete button")
run(1, click(trash[0].rect.center))
run(1, click(trash[0].rect.center))
check(not list_custom_levels(), "clicking delete twice removes the level")
run(1, key(pygame.K_ESCAPE))
check(isinstance(game.scene, MenuScene), "Esc returns to the main menu")
run(1, [pygame.event.Event(pygame.QUIT)])
check(not game.running, "closing the window stops the game")
game.save.save()
check(os.path.exists(game.save.path), "progress file written: %s" % os.path.basename(game.save.path))
ready = game.audio.wait_ready(timeout=240)
print("music ready: %s   (audio enabled: %s)" % (ready, game.audio.enabled))
print("ALL CHECKS PASSED in %.1f s, screenshots in %s" % (time.time() - started, SHOTS))
if not SHOTS.startswith(TMP):
    shutil.rmtree(TMP, ignore_errors=True)
