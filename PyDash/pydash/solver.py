"""Breadth-first search over jump inputs that proves a level is beatable.

Inputs change at most once per rendered frame (60 Hz), like a real player.
Almost identical states are merged to keep the search small. Every solution
is a real simulation, so its input list can be replayed in the game.
"""
from dataclasses import dataclass, field

from . import config as C
from .physics import PlayerState, World, step

STEPS_PER_FRAME = C.PHYSICS_HZ // C.FPS


@dataclass
class SolveResult:
    success: bool
    best_progress: float                        # percent reached by the best run
    inputs: list = field(default_factory=list)  # one hold flag per frame
    coins: int = 0


def _choices(state, world, frame, last_hold):
    """Which hold values are worth trying from this state."""
    if state.mode == "ship":
        # Ship inputs only change every second frame: plenty of control.
        return (last_hold,) if frame % 2 else (False, True)
    if state.on_ground or state.vy <= 0:
        return (False, True)
    # Rising cube: holding only matters near an unused orb.
    if any(b.kind == "orb" and b.index not in state.used for b in world.near(state.x)):
        return (False, True)
    return (False,)


def _unroll(node):
    out = []
    while node is not None:
        out.append(node[0])
        node = node[1]
    out.reverse()
    return out


def solve(level, need_coins=False, max_states=600):
    """Search for an input sequence that finishes `level` (optionally with all coins)."""
    world = World(level)
    frontier = [(PlayerState(), None)]  # (state, input history as a linked list)
    best_x = 0.0
    frame = 0
    while frontier:
        layer = {}
        for state, history in frontier:
            last = history[0] if history else False
            for hold in _choices(state, world, frame, last):
                s = state.copy()
                for _ in range(STEPS_PER_FRAME):
                    step(s, hold, world)
                    if s.dead or s.finished:
                        break
                if s.dead:
                    continue
                node = (hold, history)
                best_x = max(best_x, s.x)
                if s.finished:
                    if not need_coins or s.coins >= world.coin_ids:
                        return SolveResult(True, 100.0, _unroll(node), len(s.coins))
                    continue
                key = (s.mode, s.on_ground, int(s.y // 2), int(s.vy // 30), s.used,
                       s.coins if need_coins else None)
                if key not in layer:
                    layer[key] = (s, node)
        frontier = list(layer.values())
        if len(frontier) > max_states:
            frontier.sort(key=lambda item: (item[0].mode, item[0].y, item[0].vy))
            stride = len(frontier) / max_states
            frontier = [frontier[int(i * stride)] for i in range(max_states)]
        frame += 1
    return SolveResult(False, 100.0 * best_x / world.end_x)


def replay(level, inputs):
    """Run an input list through the physics and return the final state."""
    world = World(level)
    p = PlayerState()
    for hold in inputs:
        for _ in range(STEPS_PER_FRAME):
            step(p, hold, world)
        if p.dead or p.finished:
            break
    return p
