"""Global constants: window, grid, physics, colours and file paths.

Physics uses pixels and seconds. World coordinates are y-up: y = 0 is the
top of the ground and one grid cell is TILE pixels wide.
"""
import os

# ----------------------------------------------------------------- window
TITLE = "PyDash"
VERSION = "1.0.0"
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

# ----------------------------------------------------------------- world
TILE = 60                 # one grid cell in pixels
GROUND_Y = 560            # screen y of the ground line (camera at y = 0)
EDITOR_GROUND_Y = 470     # the editor shows the ground higher (toolbar below)
PLAYER_SCREEN_X = 330     # horizontal screen position of the player
CEILING_ROWS = 9          # height of the ship corridor in tiles

# ----------------------------------------------------------------- physics
PHYSICS_HZ = 240          # fixed physics steps per second (deterministic)
SPEED = 623.0             # horizontal speed, about 10.4 tiles per second
GRAVITY = 5330.0          # cube gravity
JUMP_VELOCITY = 1170.0    # cube jump: about 2.1 tiles high, 4.5 tiles long
PAD_VELOCITY = 1500.0     # yellow pad: about 3.5 tiles high
ORB_VELOCITY = 1250.0     # yellow orb: about 2.4 tiles high
MAX_FALL_SPEED = 1900.0
SHIP_LIFT = 2300.0        # ship acceleration while holding
SHIP_GRAVITY = 2100.0     # ship acceleration while released
SHIP_MAX_SPEED = 640.0    # ship vertical speed limit
CUBE_SPIN = 415.0         # degrees per second while the cube is airborne
LANDING_SNAP = 12.0       # landing tolerance in pixels
INNER_HITBOX = 20.0       # inset of the "core" hitbox used for wall crashes

# ----------------------------------------------------------------- paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(ROOT, "assets", "fonts", "PyDashSans-Bold.ttf")
LEVELS_DIR = os.path.join(ROOT, "levels")


def user_dir():
    """Folder for progress and created levels (override with PYDASH_USER_DIR)."""
    return os.environ.get("PYDASH_USER_DIR") or os.path.join(ROOT, "userdata")


# ----------------------------------------------------------------- colours
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
OUTLINE = (10, 12, 28)
GOLD = (255, 212, 60)
GREEN = (84, 214, 74)
CYAN = (56, 200, 255)
PINK = (250, 86, 186)
RED = (235, 64, 64)
ORANGE = (255, 150, 40)
GRAY = (120, 128, 150)
PANEL = (14, 22, 54)
PANEL_EDGE = (110, 180, 255)

# Player icon kit: cube designs (drawn in skins.py) and the colour palette of the Icons screen.
ICON_DESIGNS = ["classic", "visor", "dots", "smile", "cross", "diamond", "corners", "plus",
                "split", "stripes", "target", "robot", "checker", "arrows", "grin", "window"]
ICON_COLORS = [
    (255, 214, 60), (255, 150, 40), (235, 64, 64), (255, 105, 180), (220, 80, 235), (150, 96, 255),
    (70, 120, 255), (56, 200, 255), (60, 232, 220), (40, 190, 140), (90, 230, 120), (184, 240, 60),
    (255, 255, 255), (190, 198, 215), (112, 120, 142), (52, 56, 84), (166, 104, 52), (22, 24, 38),
]

# Level colour themes: name -> (background, ground)
THEMES = {
    "blue": ((38, 108, 255), (22, 58, 196)),
    "purple": ((128, 58, 228), (78, 30, 168)),
    "magenta": ((218, 48, 168), (148, 24, 118)),
    "orange": ((255, 118, 38), (188, 68, 18)),
    "red": ((216, 38, 58), (146, 18, 38)),
    "teal": ((18, 176, 168), (8, 108, 118)),
    "green": ((58, 186, 78), (28, 118, 48)),
    "night": ((30, 34, 82), (16, 18, 52)),
}

DIFFICULTY_COLORS = {
    "easy": (80, 200, 255), "normal": (90, 220, 90), "hard": (255, 200, 40),
    "harder": (255, 110, 40), "insane": (230, 60, 200),
}


def lerp_color(a, b, t):
    """Blend two RGB(A) colours; t = 0 gives a, t = 1 gives b. Returns ints."""
    t = max(0.0, min(1.0, t))
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def shade(color, factor):
    """Darken (factor < 1) or lighten (factor > 1) an RGB colour."""
    if factor <= 1:
        return tuple(int(c * factor) for c in color[:3])
    return tuple(int(c + (255 - c) * (factor - 1)) for c in color[:3])
