"""Level data model, object catalogue and JSON loading/saving.

A level file stores grid cells: x is the column, y the row (y = 0 sits on
the ground). The end of a level is placed automatically after the last
object, so editing never needs a separate "length" setting.
"""
import json
import os
from dataclasses import dataclass, field

from . import config as C

# Every placeable object. w/h are the footprint in tiles.
OBJECT_TYPES = {
    "block": {"label": "Block", "w": 1, "h": 1, "rotatable": False},
    "slab": {"label": "Slab", "w": 1, "h": 1, "rotatable": True},
    "spike": {"label": "Spike", "w": 1, "h": 1, "rotatable": True},
    "small_spike": {"label": "Small spike", "w": 1, "h": 1, "rotatable": True},
    "pad": {"label": "Jump pad", "w": 1, "h": 1, "rotatable": False},
    "orb": {"label": "Jump orb", "w": 1, "h": 1, "rotatable": False},
    "coin": {"label": "Coin", "w": 1, "h": 1, "rotatable": False},
    "portal_ship": {"label": "Ship portal", "w": 1, "h": 3, "rotatable": False},
    "portal_cube": {"label": "Cube portal", "w": 1, "h": 3, "rotatable": False},
}
DIFFICULTIES = ("easy", "normal", "hard", "harder", "insane")
FORMAT_VERSION = 1


@dataclass
class LevelObject:
    """One object on the grid."""
    type: str
    x: int
    y: int
    rot: int = 0  # clockwise degrees: 0, 90, 180 or 270

    def to_dict(self):
        d = {"type": self.type, "x": self.x, "y": self.y}
        if self.rot:
            d["rot"] = self.rot
        return d

    @classmethod
    def from_dict(cls, d):
        kind = d["type"]
        if kind not in OBJECT_TYPES:
            raise ValueError("unknown object type: %r" % kind)
        rot = int(d.get("rot", 0)) % 360
        if rot % 90:
            raise ValueError("rotation must be a multiple of 90 degrees")
        if not OBJECT_TYPES[kind]["rotatable"]:
            rot = 0
        return cls(kind, int(d["x"]), int(d["y"]), rot)


@dataclass
class Level:
    name: str = "Untitled"
    difficulty: str = "normal"
    stars: int = 0
    objects: list = field(default_factory=list)
    colors: list = field(default_factory=lambda: [{"x": 0, "theme": "blue"}])
    music: dict = field(default_factory=lambda: {"bpm": 128, "root": 57, "seed": 1})
    level_id: str = ""      # key used in the save file, e.g. "main:01_neon_steps"
    path: str = ""          # file the level was loaded from / is saved to
    official: bool = False  # official levels cannot be edited

    @property
    def length(self):
        """End of the level in tiles: 10 tiles after the last object."""
        last = max((o.x + OBJECT_TYPES[o.type]["w"] for o in self.objects), default=0)
        return max(last + 10, 30)

    @property
    def coin_ids(self):
        """Indices of the coin objects, in level order."""
        return [i for i, o in enumerate(self.objects) if o.type == "coin"]

    @staticmethod
    def _zone_colors(zone):
        if "theme" in zone:
            return C.THEMES.get(zone["theme"], C.THEMES["blue"])
        return tuple(zone["bg"]), tuple(zone["ground"])

    def theme_at(self, x_tiles, fade=6.0):
        """(background, ground) colours at a position, fading between zones."""
        zones = sorted(self.colors, key=lambda z: z.get("x", 0)) or [{"x": 0, "theme": "blue"}]
        bg, ground = self._zone_colors(zones[0])
        for zone in zones[1:]:
            start = zone.get("x", 0)
            if x_tiles < start:
                break
            t = min(1.0, (x_tiles - start) / fade)
            nbg, nground = self._zone_colors(zone)
            bg, ground = C.lerp_color(bg, nbg, t), C.lerp_color(ground, nground, t)
        return bg, ground

    # ---- serialisation
    def to_dict(self):
        return {
            "format": FORMAT_VERSION, "name": self.name, "difficulty": self.difficulty,
            "stars": self.stars, "music": dict(self.music),
            "colors": [dict(z) for z in self.colors],
            "objects": [o.to_dict() for o in self.objects],
        }

    @classmethod
    def from_dict(cls, data, level_id="", path="", official=False):
        difficulty = data.get("difficulty", "normal")
        if difficulty not in DIFFICULTIES:
            difficulty = "normal"
        return cls(
            name=str(data.get("name", "Untitled"))[:40],
            difficulty=difficulty,
            stars=int(data.get("stars", 0)),
            objects=[LevelObject.from_dict(o) for o in data.get("objects", [])],
            colors=list(data.get("colors") or [{"x": 0, "theme": "blue"}]),
            music=dict(data.get("music") or {"bpm": 128, "root": 57, "seed": 1}),
            level_id=level_id, path=path, official=official,
        )

    def copy(self):
        return Level.from_dict(self.to_dict(), self.level_id, self.path, self.official)


def dumps_level(level):
    """JSON text with one object per line (readable and diff-friendly)."""
    data = level.to_dict()
    objects = data.pop("objects")
    head = json.dumps(data, indent=2)[:-2]  # drop the closing "\n}"
    body = ",\n    ".join(json.dumps(o) for o in objects)
    return head + ',\n  "objects": [\n    ' + body + "\n  ]\n}\n"


def load_level(path, official=False):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    stem = os.path.splitext(os.path.basename(path))[0]
    level_id = ("main:" if official else "custom:") + stem
    return Level.from_dict(data, level_id, path, official)


def save_level(level, path=None):
    path = path or level.path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(dumps_level(level))
    os.replace(tmp, path)
    level.path = path


def load_official_levels():
    files = sorted(f for f in os.listdir(C.LEVELS_DIR) if f.endswith(".json"))
    return [load_level(os.path.join(C.LEVELS_DIR, f), official=True) for f in files]


def custom_levels_dir():
    return os.path.join(C.user_dir(), "levels")


def list_custom_levels():
    folder = custom_levels_dir()
    if not os.path.isdir(folder):
        return []
    levels = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            try:
                levels.append(load_level(os.path.join(folder, name)))
            except (OSError, ValueError, KeyError) as exc:
                print("Skipping broken level %s: %s" % (name, exc))
    return levels


def new_custom_level():
    """Create (but do not save) a new empty level with a free file name."""
    folder = custom_levels_dir()
    n = 1
    while os.path.exists(os.path.join(folder, "level_%d.json" % n)):
        n += 1
    level = Level(name="My Level %d" % n, music={"bpm": 130, "root": 55, "seed": n})
    level.path = os.path.join(folder, "level_%d.json" % n)
    level.level_id = "custom:level_%d" % n
    return level
