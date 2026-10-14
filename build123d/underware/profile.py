# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""The monokini U cross-section.

[C] monokini_I_channel.scad:487-507 monokini_offset_profile and :508-531
monokini_midline_*. Profile frame: X across the channel, Z up, Z=0 is the
closed (chamfered) face that lies on the bed; the open side faces +Z and
the walls end BASE_HEIGHT below the full height, where the grips start.
"""
from __future__ import annotations

from math import floor, sqrt

from build123d import Face, Vector, Wire

from . import constants as c


def monokini_profile_points(width_mm: float, height_mm: float,
                            top_chamfer: float = c.TOP_CHAMFER) -> list[tuple[float, float]]:
    """Outer U then the SNAP_WALL inset, as one closed (x, z) polygon.

    :489-495 builds the outer half; the Decorative=false points at
    -w/2+topChamfer+minWall(+Nudge) are collinear on z=0 and are dropped.
    :497-502 insets that path by snapWallThickness with sharp (delta) joins
    and resets both ends to the wall top. The inset chamfer corner sits
    INNER_CHAMFER = 2 + 2*sqrt(2) in from the outside (reference
    i-1x5-h22.stl section y=0: (-11.2, 4.828), (-8.372, 2.0)).

    top_chamfer 0 is monokini_text_label.scad:109: the outer corners are
    square and so is the inset. With height_mm = SNAP_WALL + BASE_HEIGHT the
    walls end at the floor top and the U is that file's :202-207 plate
    rectangle; repeated and collinear points are dropped.
    """
    w, h, t = width_mm/2, height_mm-c.BASE_HEIGHT, c.SNAP_WALL
    k, d = top_chamfer, t*sqrt(2)
    if k == 0:
        return _simplified([(-w, h), (-w, 0.), (w, 0.), (w, h),
                            (w-t, h), (w-t, t), (-w+t, t), (-w+t, h)])
    if k != c.TOP_CHAMFER:
        raise ValueError(f'top_chamfer {k:g}: the profile is defined for {c.TOP_CHAMFER:g} '
                         f'(the channels) or 0 (the text label plate)')
    outer = [(-w, h), (-w, k), (-w+k, 0.), (w-k, 0.), (w, k), (w, h)]
    inner = [(w-t, h), (w-t, t+d), (w-k-d+t, t), (-w+k+d-t, t), (-w+t, t+d), (-w+t, h)]
    return outer + inner


def _simplified(points):
    """Drop repeated points, then points collinear with their neighbours."""
    pts = [p for i, p in enumerate(points) if p != points[i-1]]
    def turn(a, b, q):
        return (b[0]-a[0])*(q[1]-b[1]) - (b[1]-a[1])*(q[0]-b[0])
    return [p for i, p in enumerate(pts) if abs(turn(pts[i-1], p, pts[(i+1) % len(pts)])) > 1e-12]


def _face(points) -> Face:
    return Face(Wire.make_polygon([Vector(x, 0, z) for x, z in points], close=True))


def monokini_profile(width_mm: float, height_mm: float, top_chamfer: float = c.TOP_CHAMFER) -> Face:
    """The U profile as a Face in the XZ plane (y=0)."""
    return _face(monokini_profile_points(width_mm, height_mm, top_chamfer))


def midline_positions(width_mm: float) -> list[float]:
    """Separator wall centres by Channel_Separators index [C] :519-531.

    left_half runs x = 0, 14, 28 ... <= w/2; right_half mirrors it in reverse.
    BOSL2 deduplicate() only drops CONSECUTIVE equal rects and the mirrored
    x=0 rect lists its points in another order, so x=0 appears at both ends
    (checked against author renders: width 2 'NS' -> x=14, width 3 'NNS' -> x=28).
    """
    half = [i*c.GRID/2 for i in range(floor(width_mm/2/(c.GRID/2))+1)]
    return half + [-x for x in reversed(half)]


def separator_rect(x: float, height_mm: float) -> Face:
    """[C] :521-526 one SNAP_WALL-wide wall from the floor to the wall top."""
    t, h = c.SNAP_WALL/2, height_mm-c.BASE_HEIGHT
    return _face([(x-t, 0.), (x-t, h), (x+t, h), (x+t, 0.)])
