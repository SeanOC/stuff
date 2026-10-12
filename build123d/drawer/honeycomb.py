# SPDX-License-Identifier: CC-BY-SA-4.0 AND BSD-2-Clause
"""Drawer hex panels, centred in XY with thickness centred on Z.

[C] drawer source :435-451 and BOSL2 walls.scad hex_panel/_honeycomb,
distributors.scad grid_copies at the NOTICE pin b86a7584.
BOSL2 algorithms: Copyright (c) 2017-2019 Revar Desmera, BSD-2-Clause;
see BOSL2-LICENSE. Drawer adaptation is CC-BY-SA-4.0. The frame clips
edge cells; it does not change the centred staggered lattice.
"""
from math import cos, sin, pi, floor, isfinite, sqrt

from build123d import Box, Face, Part, Pos, Solid, Wire
from shapely.geometry import Polygon, box

from .constants import HONEYCOMB_UNIT, HONEYCOMB_STRUT_HYP


class HoneycombPanelTooSmall(ValueError):
    """BOSL2's strict frame*2 + spacing < size guard failed."""


class HoneycombStrutOutOfRange(ValueError):
    """Unit/strut values cannot form a finite, positive hex opening."""


def strut_dimensions(strut_hyp=HONEYCOMB_STRUT_HYP, unit=HONEYCOMB_UNIT):
    """Return spacing, perpendicular strut width, hex inradius/circumradius."""
    if not all(isfinite(x) and x > 0 for x in (strut_hyp, unit)):
        raise HoneycombStrutOutOfRange('honeycomb unit and strut_hyp must be finite and positive')
    spacing, strut = unit/cos(pi/6), strut_hyp*cos(pi/6)
    ir = (spacing-strut)/2
    if ir <= 0:
        raise HoneycombStrutOutOfRange('honeycomb strut must be smaller than spacing')
    return spacing, strut, ir, ir*2/sqrt(3)


def front_alignment(width, height, unit=HONEYCOMB_UNIT):
    """Source fronthex width/height strut counts and centred height offset.

    D3's handle uses these front-panel formulas, not the BOSL2 grid counts.
    """
    spacing = unit/cos(pi/6)
    nx, ny = floor(width/unit), floor(height/spacing*2)/2
    return nx, ny, (height-ny*spacing)/2


def hex_centres(width, height, unit=HONEYCOMB_UNIT):
    """BOSL2 grid_copies(spacing=unit/cos(30), stagger=true)."""
    dx, dy = unit/sqrt(3), unit
    spacing = unit/cos(pi/6)
    # NOTICE pin pads the lattice before centring (walls.scad:415-420).
    nx = floor((width+2*spacing)/dx)+5
    ny = floor((height+2*spacing)/dy)+5
    return [((col-(nx-1)/2)*dx, (row-(ny-1)/2)*dy)
            for row in range(ny) for col in range(row % 2, nx, 2)]


def hole_polygons(width, height, *, strut_hyp=HONEYCOMB_STRUT_HYP,
                  unit=HONEYCOMB_UNIT, frame=None):
    """Clipped hex openings as XY vertex lists, including partial edge cells."""
    spacing, strut, _, radius = strut_dimensions(strut_hyp, unit)
    frame = strut if frame is None else frame
    if not isfinite(frame) or frame < 0:
        raise ValueError('honeycomb frame must be finite and nonnegative')
    if not all(isfinite(x) and x > 2*frame+spacing for x in (width, height)):
        raise HoneycombPanelTooSmall(
            f'honeycomb panel axes must exceed 2*frame + spacing ({2*frame+spacing:.6f} mm)')
    interior = box(-width/2+frame, -height/2+frame, width/2-frame, height/2-frame)
    hexagon = [(radius*cos(pi/6+i*pi/3), radius*sin(pi/6+i*pi/3)) for i in range(6)]
    result = []
    for x, y in hex_centres(width, height, unit):
        clipped = Polygon([(x+u, y+v) for u, v in hexagon]).intersection(interior)
        if not clipped.is_empty and clipped.area > 1e-10:
            result.append(list(clipped.exterior.coords)[:-1])
    return result


def hole_solids(width, height, thickness, **kwargs):
    if not isfinite(thickness) or thickness <= 0:
        raise ValueError('honeycomb thickness must be finite and positive')
    return [Pos(0, 0, -thickness/2)*Solid.extrude(
        Face(Wire.make_polygon([(x, y, 0) for x, y in polygon], close=True)),
        (0, 0, thickness)) for polygon in hole_polygons(width, height, **kwargs)]


def honeycomb_panel(width, height, thickness, *, strut_hyp=HONEYCOMB_STRUT_HYP,
                    unit=HONEYCOMB_UNIT, frame=None) -> Part:
    holes = hole_solids(width, height, thickness, strut_hyp=strut_hyp, unit=unit, frame=frame)
    return Part(children=[Box(width, height, thickness).cut(*holes)])
