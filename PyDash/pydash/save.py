"""Saving progress and settings to a small JSON file in the user folder."""
import json
import os

from . import config as C

DEFAULT_SETTINGS = {"music": True, "sfx": True, "icon": 0, "color1": 0, "color2": 7}


def _blank_stats():
    return {"best": 0, "practice": 0, "attempts": 0, "jumps": 0,
            "completed": False, "coins": []}


class SaveData:
    def __init__(self, path=None):
        self.path = path or os.path.join(C.user_dir(), "save.json")
        self.levels = {}
        self.settings = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return  # first start or a broken file: keep the defaults
        self.settings.update(data.get("settings", {}))
        for level_id, values in data.get("levels", {}).items():
            stats = _blank_stats()
            stats.update(values)
            self.levels[level_id] = stats

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"settings": self.settings, "levels": self.levels}, fh, indent=2)
        os.replace(tmp, self.path)

    def stats(self, level_id):
        return self.levels.setdefault(level_id, _blank_stats())

    def record_run(self, level_id, percent, practice, jumps, completed=False, coins=()):
        """Store the result of one attempt. Returns True for a new best percentage."""
        s = self.stats(level_id)
        s["attempts"] += 1
        s["jumps"] += int(jumps)
        key = "practice" if practice else "best"
        pct = int(percent)
        new_best = pct > s[key]
        if new_best:
            s[key] = pct
        if completed and not practice:
            s["completed"] = True
            s["coins"] = sorted(set(s["coins"]) | set(coins))
        self.save()
        return new_best

    def total_stars(self, levels):
        return sum(l.stars for l in levels if self.stats(l.level_id)["completed"])
