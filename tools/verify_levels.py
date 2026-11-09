"""Proves that every official level, and all of its coins, can be reached.

Usage:  python tools/verify_levels.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydash.level import load_official_levels  # noqa: E402
from pydash.solver import replay, solve  # noqa: E402


def main():
    ok = True
    for level in load_official_levels():
        for need_coins in (False, True):
            t0 = time.time()
            result = solve(level, need_coins=need_coins)
            final = replay(level, result.inputs) if result.success else None
            passed = result.success and final.finished and not final.dead
            ok &= passed
            print("%-14s %-10s %s  best %5.1f%%  coins %d  (%.1fs)" % (
                level.name, "all coins" if need_coins else "finish",
                "OK  " if passed else "FAIL", result.best_progress, result.coins,
                time.time() - t0))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
