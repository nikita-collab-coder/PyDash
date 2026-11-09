"""Deterministic player physics and collisions (pure Python, no pygame).

World coordinates are y-up: y = 0 is the ground surface and the player's
(x, y) is the bottom-left corner of its square hitbox. The game, the tests
and the level solver all use this module, so a level that the solver can
finish is guaranteed to be beatable in the game.
"""
import math
from dataclasses import dataclass, field, replace

from . import config as C

SIZE = C.TILE  # the player's hitbox is one tile

# Collision shape of every object type: (kind, (x, y, w, h) in tile units,
# y-up, for rotation 0). Spikes use small hitboxes, like the genre does.
SHAPES = {
    "block": ("solid", (0.0, 0.0, 1.0, 1.0)),
    "slab": ("solid", (0.0, 0.0, 1.0, 0.5)),
    "spike": ("hazard", (0.36, 0.08, 0.28, 0.56)),
    "small_spike": ("hazard", (0.36, 0.04, 0.28, 0.26)),
    "pad": ("pad", (0.1, 0.0, 0.8, 0.25)),
    "orb": ("orb", (0.05, 0.05, 0.9, 0.9)),
    "coin": ("coin", (0.1, 0.1, 0.8, 0.8)),
    "portal_ship": ("portal", (0.2, 0.0, 0.6, 3.0)),
    "portal_cube": ("portal", (0.2, 0.0, 0.6, 3.0)),
}


def rotate_box(box, rot):
    """Rotate a tile-local box clockwise around the tile centre (90 degree steps)."""
    x, y, w, h = box
    for _ in range((rot // 90) % 4):
        # A point (px, py) moves to (py, 1 - px) for a clockwise quarter turn.
        x, y, w, h = y, 1.0 - x - w, h, w
    return x, y, w, h


@dataclass(eq=False)
class Body:
    """A collision shape in world pixels."""
    index: int      # index of the object in level.objects
    kind: str       # solid, hazard, pad, orb, coin or portal
    x: float
    y: float
    w: float
    h: float
    data: str = ""  # portal target mode ("ship" or "cube")


def overlap(ax, ay, aw, ah, b):
    """True if the box (ax, ay, aw, ah) overlaps body b (touching edges do not count)."""
    return ax < b.x + b.w and b.x < ax + aw and ay < b.y + b.h and b.y < ay + ah


class World:
    """Static collision data for one level, bucketed by grid column."""

    def __init__(self, level):
        self.bodies = []
        self._columns = {}
        self._near = {}
        for i, obj in enumerate(level.objects):
            kind, box = SHAPES[obj.type]
            bx, by, bw, bh = rotate_box(box, obj.rot)
            target = obj.type.split("_")[1] if kind == "portal" else ""
            body = Body(i, kind, (obj.x + bx) * C.TILE, (obj.y + by) * C.TILE,
                        bw * C.TILE, bh * C.TILE, target)
            self.bodies.append(body)
            self._columns.setdefault(obj.x, []).append(body)
        self.end_x = level.length * C.TILE
        self.ceiling = C.CEILING_ROWS * C.TILE
        self.coin_ids = frozenset(b.index for b in self.bodies if b.kind == "coin")

    def near(self, x):
        """Bodies that a player standing at world x could touch."""
        col = int(x // C.TILE)
        found = self._near.get(col)
        if found is None:
            found = tuple(b for c in range(col - 1, col + 3) for b in self._columns.get(c, ()))
            self._near[col] = found
        return found


@dataclass
class PlayerState:
    x: float = 0.0
    y: float = 0.0
    vy: float = 0.0
    mode: str = "cube"              # "cube" or "ship"
    on_ground: bool = True
    rotation: float = 0.0           # visual rotation, clockwise degrees
    dead: bool = False
    finished: bool = False
    used: frozenset = frozenset()   # pads and orbs that already fired
    coins: frozenset = frozenset()  # collected coin object indices
    jumps: int = 0
    events: list = field(default_factory=list)  # "jump", "death", ... for effects

    def copy(self):
        return replace(self, events=[])


def _die(p):
    p.dead = True
    p.events.append("death")


def step(p, hold, world, dt=1.0 / C.PHYSICS_HZ):
    """Advance the player by one fixed step. `hold` is True while jump is held."""
    if p.dead or p.finished:
        return
    prev_y = p.y
    was_grounded = p.on_ground
    p.x += C.SPEED * dt

    # 1) Vertical motion.
    if p.mode == "cube":
        if hold and p.on_ground:
            p.vy = C.JUMP_VELOCITY
            p.jumps += 1
            p.events.append("jump")
        p.vy = max(p.vy - C.GRAVITY * dt, -C.MAX_FALL_SPEED)
    else:
        p.vy += (C.SHIP_LIFT if hold else -C.SHIP_GRAVITY) * dt
        p.vy = max(-C.SHIP_MAX_SPEED, min(C.SHIP_MAX_SPEED, p.vy))
    p.y += p.vy * dt
    p.on_ground = False

    # 2) The floor, and the ceiling of the ship corridor.
    if p.y <= 0.0:
        p.y = 0.0
        p.vy = max(p.vy, 0.0)
        p.on_ground = True
    if p.mode == "ship" and p.y + SIZE > world.ceiling:
        p.y = world.ceiling - SIZE
        p.vy = min(p.vy, 0.0)

    bodies = world.near(p.x)

    # 3) Solid blocks: land on top, slide under them (ship) or crash.
    inset = C.INNER_HITBOX
    for b in bodies:
        if b.kind != "solid" or not overlap(p.x, p.y, SIZE, SIZE, b):
            continue
        top = b.y + b.h
        if p.vy <= 0.0 and prev_y >= top - C.LANDING_SNAP:
            p.y, p.vy, p.on_ground = top, 0.0, True
        elif p.mode == "ship" and p.vy >= 0.0 and prev_y + SIZE <= b.y + C.LANDING_SNAP:
            p.y, p.vy = b.y - SIZE, 0.0
        elif overlap(p.x + inset, p.y + inset, SIZE - 2 * inset, SIZE - 2 * inset, b):
            _die(p)
            return

    # 4) Hazards and triggers.
    for b in bodies:
        if b.kind == "solid" or not overlap(p.x, p.y, SIZE, SIZE, b):
            continue
        if b.kind == "hazard":
            _die(p)
            return
        if b.kind == "pad" and b.index not in p.used:
            p.used = p.used | {b.index}
            p.vy = C.PAD_VELOCITY if p.mode == "cube" else C.SHIP_MAX_SPEED
            p.on_ground = False
            p.events.append("pad")
        elif b.kind == "orb" and hold and b.index not in p.used:
            p.used = p.used | {b.index}
            p.vy = C.ORB_VELOCITY if p.mode == "cube" else C.SHIP_MAX_SPEED
            p.on_ground = False
            p.events.append("orb")
        elif b.kind == "coin" and b.index not in p.coins:
            p.coins = p.coins | {b.index}
            p.events.append("coin")
        elif b.kind == "portal" and p.mode != b.data:
            p.mode = b.data
            p.vy *= 0.5
            p.events.append("portal")

    # 5) Visual rotation: spin in the air, settle on a flat side when landing.
    if p.mode == "cube":
        if p.on_ground:
            target = round(p.rotation / 90.0) * 90.0
            p.rotation += (target - p.rotation) * min(1.0, 28.0 * dt)
            if not was_grounded:
                p.events.append("land")
        else:
            p.rotation += C.CUBE_SPIN * dt
        p.rotation %= 360.0
    else:
        p.rotation = -math.degrees(math.atan2(p.vy, C.SPEED))

    if p.x >= world.end_x:
        p.finished = True
        p.events.append("finish")


def progress(p, world):
    """Level progress in percent (0..100)."""
    return max(0.0, min(100.0, 100.0 * p.x / world.end_x))
