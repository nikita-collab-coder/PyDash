"""Generates the official levels in levels/*.json.

Levels are written with a tiny cursor-based builder so that the layout is
easy to read and tweak. Run tools/verify_levels.py afterwards: it proves
with the solver that every level (and every coin) can be reached.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydash import config as C  # noqa: E402
from pydash.level import Level, LevelObject, save_level  # noqa: E402


class Builder:
    def __init__(self):
        self.objects = []
        self.x = 0  # cursor column

    def put(self, kind, x, y, rot=0):
        self.objects.append(LevelObject(kind, x, y, rot))

    def run(self, n):
        """Empty ground."""
        self.x += n

    def spikes(self, n=1, row=0, kind="spike", advance=True):
        for i in range(n):
            self.put(kind, self.x + i, row)
        if advance:
            self.x += n

    def platform(self, w, h):
        """A solid platform w tiles long and h tiles high, standing on the ground."""
        for i in range(w):
            for row in range(h):
                self.put("block", self.x + i, row)
        self.x += w

    def floating(self, w, row, advance=True):
        for i in range(w):
            self.put("block", self.x + i, row)
        if advance:
            self.x += w

    def at(self, dx, kind, row, rot=0):
        """Place an object relative to the cursor without moving it."""
        self.put(kind, self.x + dx, row, rot)

    def wall(self, w, gap_row, gap):
        """Ship-section wall with an opening of `gap` rows starting at `gap_row`."""
        for i in range(w):
            for row in range(C.CEILING_ROWS):
                if not gap_row <= row < gap_row + gap:
                    self.put("block", self.x + i, row)
        self.x += w

    def ship_portal(self):
        self.put("portal_ship", self.x, 0)
        self.x += 1

    def cube_portal(self, row=3):
        """Cube portal inside a ship corridor, framed so it cannot be missed."""
        for row_ in range(C.CEILING_ROWS):
            if not row <= row_ < row + 3:
                self.put("block", self.x, row_)
        self.put("portal_cube", self.x + 1, row)
        for row_ in range(C.CEILING_ROWS):
            if not row <= row_ < row + 3:
                self.put("block", self.x + 2, row_)
        self.x += 3


# --------------------------------------------------------------------------- 1
def neon_steps():
    b = Builder()
    b.run(16)
    b.spikes(1); b.run(8)
    b.spikes(1); b.run(7)
    b.spikes(2); b.run(8)
    b.platform(6, 1); b.run(5)
    b.spikes(2); b.run(7)
    b.platform(4, 1); b.platform(4, 2); b.run(6)
    b.spikes(1); b.run(6)
    b.at(0, "coin", 2); b.spikes(2); b.run(8)          # coin 1 above a double spike
    b.at(0, "pad", 0); b.run(4)
    b.floating(8, 2); b.run(7)
    b.spikes(1); b.run(7)
    b.spikes(6); b.at(-4, "orb", 2); b.run(8)          # orb over a spike pit
    b.platform(3, 1); b.platform(3, 2); b.at(1, "coin", 4); b.platform(3, 3)  # coin 2
    b.run(7)
    b.spikes(1); b.run(6)
    b.spikes(2); b.run(7)
    b.platform(3, 1); b.spikes(3); b.platform(4, 1); b.spikes(3); b.platform(4, 1)
    b.run(7)
    b.spikes(1, kind="small_spike"); b.run(5)
    b.platform(1, 1); b.at(0, "coin", 3); b.run(6)       # coin 3 above a lone block
    b.spikes(2); b.run(7)
    b.spikes(1); b.run(5)
    b.spikes(1); b.run(8)
    b.at(0, "pad", 0); b.run(4); b.floating(6, 2); b.spikes(2, advance=False); b.run(8)
    b.spikes(2); b.run(6)
    return Level(
        name="Neon Steps", difficulty="easy", stars=2, objects=b.objects,
        colors=[{"x": 0, "theme": "blue"}, {"x": 70, "theme": "purple"},
                {"x": 140, "theme": "magenta"}, {"x": 200, "theme": "blue"}],
        music={"bpm": 128, "root": 57, "seed": 3},
    )


# --------------------------------------------------------------------------- 2
def ember_drift():
    b = Builder()
    b.run(14)
    b.spikes(1); b.run(6)
    b.spikes(2); b.run(6)
    b.platform(5, 1); b.at(-2, "small_spike", 1); b.run(5)
    b.at(0, "pad", 0); b.run(3); b.floating(5, 2); b.floating(5, 3); b.run(7)
    b.spikes(10); b.at(-8, "orb", 2); b.at(-4, "orb", 2); b.at(-6, "coin", 5)  # coin 1
    b.run(7)
    b.spikes(2); b.run(5)
    b.platform(3, 1); b.spikes(3); b.platform(3, 2); b.spikes(3); b.platform(4, 1)
    b.run(6)
    b.spikes(1); b.run(4); b.spikes(2); b.run(8)
    b.ship_portal(); b.run(10)
    b.wall(2, 3, 4); b.run(6)
    b.wall(2, 5, 4); b.run(6)
    b.wall(2, 2, 4); b.run(6)
    b.at(0, "coin", 7); b.wall(2, 4, 4); b.run(6)          # coin 2 above a wall
    b.wall(2, 1, 4); b.run(5)
    b.wall(2, 4, 4); b.run(6)
    b.wall(2, 2, 4); b.run(6)
    b.cube_portal(3); b.run(10)
    b.spikes(1); b.run(6)
    b.spikes(2); b.run(6)
    b.at(0, "pad", 0); b.run(3); b.floating(4, 2); b.spikes(4, advance=False); b.run(4)
    b.floating(4, 2); b.spikes(4, advance=False); b.at(2, "coin", 4); b.run(7)  # coin 3
    b.spikes(2); b.run(5)
    b.spikes(1); b.run(4); b.spikes(1); b.run(8)
    return Level(
        name="Ember Drift", difficulty="normal", stars=4, objects=b.objects,
        colors=[{"x": 0, "theme": "orange"}, {"x": 90, "theme": "red"},
                {"x": 135, "theme": "night"}, {"x": 212, "theme": "orange"}],
        music={"bpm": 140, "root": 52, "seed": 7},
    )


# --------------------------------------------------------------------------- 3
def frost_circuit():
    b = Builder()
    b.run(14)
    b.spikes(2); b.run(6)
    b.spikes(3); b.run(7)
    b.platform(4, 1); b.at(-2, "small_spike", 1)
    b.run(5)
    b.spikes(1, kind="small_spike"); b.run(1); b.spikes(1, kind="small_spike"); b.run(6)
    b.spikes(11); b.at(-9, "orb", 2); b.at(-4, "orb", 2); b.at(-7, "coin", 5)  # coin 1
    b.run(6)
    b.platform(2, 1); b.spikes(2); b.platform(2, 2); b.spikes(2); b.platform(2, 3)
    b.spikes(3); b.at(-2, "coin", 5); b.run(7)                                  # coin 2
    b.spikes(3); b.run(6)
    b.at(0, "pad", 0); b.run(3); b.floating(3, 2); b.spikes(5, advance=False); b.run(2)
    b.floating(5, 3); b.at(-2, "small_spike", 4); b.spikes(3, advance=False); b.run(6)
    b.ship_portal(); b.run(8)
    b.wall(2, 3, 3); b.run(5)
    b.wall(2, 6, 3); b.run(5)
    b.wall(2, 1, 3); b.run(4)
    b.wall(2, 4, 3); b.at(-1, "coin", 5); b.run(5)
    b.wall(2, 0, 3); b.run(5)
    b.wall(2, 5, 3); b.run(4)
    b.wall(2, 2, 3); b.run(5)
    b.wall(2, 6, 3); b.run(5)
    b.cube_portal(3); b.run(9)
    b.spikes(3); b.run(6)
    b.platform(3, 1); b.spikes(2, row=0); b.platform(3, 2); b.spikes(2); b.platform(3, 1)
    b.run(6)
    b.spikes(2); b.run(4); b.spikes(3); b.run(7)
    b.at(0, "pad", 0); b.run(3); b.floating(4, 2); b.spikes(6, advance=False); b.run(2)
    b.floating(4, 3); b.run(7)
    b.spikes(3); b.run(8)
    return Level(
        name="Frost Circuit", difficulty="hard", stars=6, objects=b.objects,
        colors=[{"x": 0, "theme": "teal"}, {"x": 80, "theme": "blue"},
                {"x": 160, "theme": "night"}, {"x": 240, "theme": "purple"}],
        music={"bpm": 150, "root": 50, "seed": 11},
    )


LEVELS = [("01_neon_steps", neon_steps), ("02_ember_drift", ember_drift),
          ("03_frost_circuit", frost_circuit)]


def main():
    os.makedirs(C.LEVELS_DIR, exist_ok=True)
    for stem, make in LEVELS:
        level = make()
        save_level(level, os.path.join(C.LEVELS_DIR, stem + ".json"))
        print("%-18s %4d objects, %3d tiles, %d coins"
              % (stem, len(level.objects), level.length, len(level.coin_ids)))


if __name__ == "__main__":
    main()
