"""pygame.draw emulation. Like pygame, draw calls overwrite pixels (no blending)."""
import math

from PIL import ImageDraw

from . import Rect, _rgba


def _ink(surface, color):
    c = _rgba(color)
    return c if surface._has_alpha else c[:3] + (255,)


def _bounds(surface, xs, ys, pad=0.0):
    x0, y0 = int(math.floor(min(xs) - pad)), int(math.floor(min(ys) - pad))
    x1, y1 = int(math.ceil(max(xs) + pad)) + 1, int(math.ceil(max(ys) + pad)) + 1
    return Rect(x0, y0, x1 - x0, y1 - y0).clip(surface.get_rect())


def _pts(points, minimum):
    pts = [(float(p[0]), float(p[1])) for p in points]
    if len(pts) < minimum:
        raise ValueError("points argument must contain %d or more points" % minimum)
    return pts


def rect(surface, color, rect, width=0, border_radius=0, border_top_left_radius=-1,
         border_top_right_radius=-1, border_bottom_left_radius=-1, border_bottom_right_radius=-1):
    r = Rect(rect)
    r.normalize()
    if r.w <= 0 or r.h <= 0 or width < 0:
        return Rect(r.x, r.y, 0, 0)
    ink = _ink(surface, color)
    d = ImageDraw.Draw(surface._img)
    box = [r.x, r.y, r.right - 1, r.bottom - 1]
    corners = (border_top_left_radius, border_top_right_radius,
               border_bottom_right_radius, border_bottom_left_radius)
    radius = min(max([border_radius] + list(corners)), r.w // 2, r.h // 2)
    kw = {"fill": ink} if width == 0 else {"outline": ink, "width": int(width)}
    if radius > 0:
        if any(c >= 0 for c in corners):
            flags = tuple((c if c >= 0 else border_radius) > 0 for c in corners)
            d.rounded_rectangle(box, radius, corners=flags, **kw)
        else:
            d.rounded_rectangle(box, radius, **kw)
    else:
        d.rectangle(box, **kw)
    return r.clip(surface.get_rect())


def polygon(surface, color, points, width=0):
    pts = _pts(points, 3)
    ink = _ink(surface, color)
    d = ImageDraw.Draw(surface._img)
    if width == 0:
        d.polygon(pts, fill=ink)
    elif width > 0:
        d.line(pts + [pts[0]], fill=ink, width=int(width), joint="curve" if width > 2 else None)
    return _bounds(surface, [p[0] for p in pts], [p[1] for p in pts], width / 2)


def circle(surface, color, center, radius, width=0, draw_top_right=None, draw_top_left=None,
           draw_bottom_left=None, draw_bottom_right=None):
    cx, cy, r = float(center[0]), float(center[1]), float(radius)
    if r < 1 or width < 0:
        return Rect(int(cx), int(cy), 0, 0)
    ink = _ink(surface, color)
    box = [cx - r, cy - r, cx + r - 1, cy + r - 1]
    d = ImageDraw.Draw(surface._img)
    if width == 0 or width >= r:
        d.ellipse(box, fill=ink)
    else:
        d.ellipse(box, outline=ink, width=int(width))
    return _bounds(surface, [box[0], box[2]], [box[1], box[3]])


def ellipse(surface, color, rect, width=0):
    r = Rect(rect)
    r.normalize()
    if r.w <= 0 or r.h <= 0 or width < 0:
        return Rect(r.x, r.y, 0, 0)
    ink = _ink(surface, color)
    box = [r.x, r.y, r.right - 1, r.bottom - 1]
    d = ImageDraw.Draw(surface._img)
    if width == 0:
        d.ellipse(box, fill=ink)
    else:
        d.ellipse(box, outline=ink, width=int(width))
    return r.clip(surface.get_rect())


def line(surface, color, start_pos, end_pos, width=1):
    pts = [(float(start_pos[0]), float(start_pos[1])), (float(end_pos[0]), float(end_pos[1]))]
    if width < 1:
        return Rect(int(pts[0][0]), int(pts[0][1]), 0, 0)
    ImageDraw.Draw(surface._img).line(pts, fill=_ink(surface, color), width=int(width))
    return _bounds(surface, [p[0] for p in pts], [p[1] for p in pts], width / 2)


def lines(surface, color, closed, points, width=1):
    pts = _pts(points, 2)
    if closed:
        pts.append(pts[0])
    if width < 1:
        return Rect(int(pts[0][0]), int(pts[0][1]), 0, 0)
    ImageDraw.Draw(surface._img).line(pts, fill=_ink(surface, color), width=int(width),
                                      joint="curve" if width > 2 else None)
    return _bounds(surface, [p[0] for p in pts], [p[1] for p in pts], width / 2)


def aaline(surface, color, start_pos, end_pos, blend=1):
    return line(surface, color, start_pos, end_pos, 1)


def aalines(surface, color, closed, points, blend=1):
    return lines(surface, color, closed, points, 1)


def arc(surface, color, rect, start_angle, stop_angle, width=1):
    r = Rect(rect)
    r.normalize()
    if r.w <= 0 or r.h <= 0 or width < 1:
        return Rect(r.x, r.y, 0, 0)
    start, end = -math.degrees(stop_angle), -math.degrees(start_angle)
    ImageDraw.Draw(surface._img).arc([r.x, r.y, r.right - 1, r.bottom - 1], start, end,
                                     fill=_ink(surface, color), width=int(width))
    return r.clip(surface.get_rect())
