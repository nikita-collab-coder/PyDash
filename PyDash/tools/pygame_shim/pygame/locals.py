"""pygame.locals emulation: re-exports every constant plus Rect and Color."""
import pygame as _pg

for _name, _value in list(vars(_pg).items()):
    if _name.isupper() or _name.startswith(("K_", "KMOD_")):
        globals()[_name] = _value
Rect = _pg.Rect
Color = _pg.Color
