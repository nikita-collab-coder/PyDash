"""pygame.time emulation with a virtual clock (never sleeps, fully deterministic)."""
_ticks = 0  # virtual milliseconds since init


def get_ticks():
    return int(_ticks)


def wait(milliseconds):
    global _ticks
    _ticks += max(0, int(milliseconds))
    return int(milliseconds)


delay = wait


def set_timer(event, millis, loops=0):
    pass


class Clock:
    def __init__(self):
        self._time = 0
        self._fps = 0.0

    def tick(self, framerate=0):
        """Advance virtual time by one frame and return its length in ms."""
        global _ticks
        dt = int(1000 / framerate) if framerate and framerate > 0 else 16
        _ticks += dt
        self._time = dt
        self._fps = 1000.0 / dt
        return dt

    tick_busy_loop = tick

    def get_time(self):
        return self._time

    def get_rawtime(self):
        return self._time

    def get_fps(self):
        return self._fps
