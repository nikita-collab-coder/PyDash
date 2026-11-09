"""Procedural sound: effects and looping music are synthesised at start-up (no audio files).

Music for each level is generated from its `music` settings (bpm, root note, seed)
in a background thread, then looped on a dedicated mixer channel.
"""
import math
import operator
import random
import threading
from array import array

import pygame

MENU_MUSIC = {"bpm": 112, "root": 52, "seed": 5}
TAU = 2 * math.pi
# mixer format -> (array typecode, amplitude, offset)
_FORMATS = {-16: ("h", 30000.0, 0), 16: ("H", 30000.0, 32768), -8: ("b", 120.0, 0), 8: ("B", 120.0, 128),
            32: ("f", 0.92, 0), -32: ("i", 1.9e9, 0)}
SCALE = (0, 2, 3, 5, 7, 8, 10)  # natural minor
PROGRESSIONS = ((0, 5, 2, 6), (0, 3, 5, 4), (0, 6, 5, 4), (0, 5, 3, 4))
ARPS = ((0, 1, 2, 1, 0, 1, 2, 3), (0, 2, 1, 2, 0, 2, 3, 2), (2, 1, 0, 1, 2, 3, 2, 1), (0, 0, 2, 1, 3, 2, 1, 2))


def _osc(rate, dur, freq, shape="square", vol=1.0, attack=0.004, release=0.04, decay=0.0, slide=1.0):
    """One enveloped note. `slide` = final/initial frequency ratio, `decay` = exponential fade per second."""
    n = max(1, int(rate * dur))
    out = [0.0] * n
    a, r = max(1, int(rate * attack)), max(1, int(rate * release))
    fmul = slide ** (1.0 / n)
    dk = math.exp(-decay / rate) if decay else 1.0
    f, phase, fade = freq, 0.0, 1.0
    rnd, sin = random.random, math.sin
    for i in range(n):
        phase = (phase + f / rate) % 1.0
        f *= fmul
        if shape == "square":
            v = 1.0 if phase < 0.5 else -1.0
        elif shape == "saw":
            v = 2.0 * phase - 1.0
        elif shape == "tri":
            v = 4.0 * abs(phase - 0.5) - 1.0
        elif shape == "noise":
            v = rnd() * 2.0 - 1.0
        else:
            v = sin(TAU * phase)
        env = fade
        fade *= dk
        if i < a:
            env *= i / a
        elif i > n - r:
            env *= (n - i) / r
        out[i] = v * env * vol
    return out


def _mix(buf, snip, start, gain=1.0):
    if start >= len(buf):
        return
    end = min(len(buf), start + len(snip))
    part = snip[:end - start]
    if gain != 1.0:
        part = [s * gain for s in part]
    buf[start:end] = list(map(operator.add, buf[start:end], part))


def _join(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def _add(a, b):
    n = max(len(a), len(b))
    a = a + [0.0] * (n - len(a))
    b = b + [0.0] * (n - len(b))
    return list(map(operator.add, a, b))


def _midi(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def _deg(d):
    return 12 * (d // 7) + SCALE[d % 7]


def render_music(rate, bpm=128, root=57, seed=1, bars=8):
    """An 8-bar loop: kick/snare/hats, a driving bass and an arpeggiated lead."""
    rnd = random.Random(seed)
    step = 60.0 / bpm / 4  # one sixteenth note
    n = int(rate * step * 16 * bars)
    buf = [0.0] * n
    prog = PROGRESSIONS[rnd.randrange(len(PROGRESSIONS))]
    arps = [ARPS[rnd.randrange(len(ARPS))] for _ in range(2)]
    lead = rnd.choice(("square", "saw", "tri"))
    kick = _osc(rate, 0.24, 150, "sine", 1.0, 0.001, 0.05, decay=9, slide=0.3)
    snare = _add(_osc(rate, 0.18, 1, "noise", 0.6, 0.001, 0.08, decay=14),
                 _osc(rate, 0.18, 190, "tri", 0.4, 0.001, 0.08, decay=18))
    hat = _osc(rate, 0.05, 1, "noise", 0.5, 0.001, 0.03, decay=60)
    notes = {}

    def note(shape, m, length, decay):
        key = (shape, m, length)
        if key not in notes:
            notes[key] = _osc(rate, length, _midi(m), shape, 0.5, 0.004, 0.03, decay)
        return notes[key]

    def at(s):
        return int(s * step * rate)

    for bar in range(bars):
        chord = prog[(bar // 2) % len(prog)]
        base = bar * 16
        for b in range(4):
            _mix(buf, kick, at(base + b * 4), 0.85)
            if b % 2:
                _mix(buf, snare, at(base + b * 4), 0.5)
            _mix(buf, hat, at(base + b * 4 + 2), 0.35)
        if bar % 2:
            _mix(buf, hat, at(base + 15), 0.2)
        for e in range(8):
            m = root - 24 + _deg(chord) + (12 if e % 2 else 0)
            _mix(buf, note("saw", m, step * 1.8, 4.0), at(base + e * 2), 0.32)
        arp = arps[(bar // 4) % 2]
        for s16 in range(16):
            if s16 % 8 == 7 and bar % 2:
                continue
            m = root + _deg(chord + arp[s16 % 8] * 2)
            _mix(buf, note(lead, m, step * 0.9, 7.0), at(base + s16), 0.17)
    return buf


def _pack(samples, fmt, channels):
    """Float samples -> raw bytes in the mixer's format, with soft clipping."""
    code, amp, offset = _FORMATS[fmt]
    tanh = math.tanh
    if code == "f":
        mono = array("f", [tanh(s) * amp for s in samples])
    else:
        mono = array(code, [int(tanh(s) * amp) + offset for s in samples])
    if channels <= 1:
        return mono.tobytes()
    out = array(code, [mono[0] if mono else 0]) * (len(mono) * channels)
    for c in range(channels):
        out[c::channels] = mono
    return out.tobytes()


class Audio:
    def __init__(self, settings):
        self.settings = settings
        self.enabled = False
        self.sfx = {}
        self.music_sounds = {}
        self._rendered = {}
        self._queue = []
        self._thread = None
        self._lock = threading.Lock()
        self.current = None   # music that should be playing
        self.playing = None   # music that is playing
        self.channel = None
        self._next = 1
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            info = pygame.mixer.get_init()
        except pygame.error as exc:
            print("PyDash: audio disabled ({})".format(exc))
            return
        if not info or info[1] not in _FORMATS:
            print("PyDash: audio disabled (mixer format {})".format(info))
            return
        self.rate, self.fmt, self.channels = info
        pygame.mixer.set_num_channels(12)
        self.channel = pygame.mixer.Channel(0)
        self.enabled = True
        self._make_sfx()

    def _sound(self, samples):
        return pygame.mixer.Sound(buffer=_pack(samples, self.fmt, self.channels))

    def _make_sfx(self):
        r = self.rate
        chime = _join(_osc(r, 0.07, 660, "tri", 0.6), _osc(r, 0.18, 990, "tri", 0.6, decay=8))
        self.sfx = {
            "click": self._sound(_osc(r, 0.06, 900, "square", 0.25, 0.001, 0.03, decay=30)),
            "death": self._sound(_add(_osc(r, 0.5, 1, "noise", 0.7, 0.001, 0.2, decay=7),
                                      _osc(r, 0.5, 320, "saw", 0.45, 0.001, 0.2, decay=5, slide=0.2))),
            "coin": self._sound(_join(_osc(r, 0.08, 988, "square", 0.28, 0.002, 0.02),
                                      _osc(r, 0.3, 1319, "square", 0.28, 0.002, 0.2, decay=6))),
            "pad": self._sound(_osc(r, 0.18, 300, "tri", 0.6, 0.002, 0.08, slide=4.0)),
            "orb": self._sound(_osc(r, 0.15, 500, "square", 0.22, 0.002, 0.08, slide=3.0)),
            "portal": self._sound(_osc(r, 0.35, 200, "saw", 0.3, 0.01, 0.15, slide=6.0)),
            "checkpoint": self._sound(chime),
            "best": self._sound(chime),
            "complete": self._sound(_join(*[_osc(r, 0.11, f, "square", 0.28, 0.002, 0.02) for f in (523, 659, 784)],
                                          _osc(r, 0.8, 1047, "square", 0.28, 0.002, 0.45, decay=3))),
        }

    def play(self, name, volume=0.8):
        if not self.enabled or not self.settings.get("sfx", True):
            return
        snd = self.sfx.get(name)
        if snd is not None:
            ch = pygame.mixer.Channel(self._next)
            self._next = self._next % 11 + 1
            ch.set_volume(volume)
            ch.play(snd)

    @staticmethod
    def key(params):
        return (int(params.get("bpm", 128)), int(params.get("root", 57)), int(params.get("seed", 1)))

    def prepare(self, params_list):
        """Queue songs for rendering in a background thread."""
        if not self.enabled:
            return
        with self._lock:
            for p in params_list:
                k = self.key(p)
                if k not in self._rendered and k not in self.music_sounds and k not in self._queue:
                    self._queue.append(k)
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def _worker(self):
        while True:
            with self._lock:
                if not self._queue:
                    return
                k = self._queue.pop(0)
            data = _pack(render_music(self.rate, *k), self.fmt, self.channels)
            with self._lock:
                self._rendered[k] = data

    def wait_ready(self, timeout=30.0):
        """Block until queued music is rendered (used by tests)."""
        if self._thread is not None:
            self._thread.join(timeout)
        self.update()
        return self._thread is None or not self._thread.is_alive()

    def music(self, params, restart=True):
        if params is None:
            return
        k = self.key(params)
        if k == self.current and not restart:
            return
        self.current, self.playing = k, None
        if not self.enabled:
            return
        self.channel.stop()
        if k not in self.music_sounds:
            with self._lock:
                if k in self._queue:
                    self._queue.remove(k)
                if k not in self._rendered:
                    self._queue.insert(0, k)
            self.prepare([])
        self.update()

    def stop_music(self, fade_ms=0):
        self.current = self.playing = None
        if self.enabled:
            if fade_ms:
                self.channel.fadeout(fade_ms)
            else:
                self.channel.stop()

    def pause_music(self):
        if self.enabled:
            self.channel.pause()

    def resume_music(self):
        if self.enabled:
            self.channel.unpause()

    def set_music_enabled(self, on):
        self.settings["music"] = bool(on)
        if self.enabled and not on:
            self.channel.stop()
            self.playing = None

    def set_sfx_enabled(self, on):
        self.settings["sfx"] = bool(on)

    def update(self):
        if not self.enabled:
            return
        with self._lock:
            ready = list(self._rendered.items())
            self._rendered.clear()
        for k, data in ready:
            self.music_sounds[k] = pygame.mixer.Sound(buffer=data)
        if self.current and self.playing != self.current and self.settings.get("music", True):
            snd = self.music_sounds.get(self.current)
            if snd is not None:
                self.channel.set_volume(0.55)
                self.channel.play(snd, loops=-1)
                self.playing = self.current
