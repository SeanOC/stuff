# SPDX-License-Identifier: CC-BY-SA-4.0 AND BSD-2-Clause
"""Drawer hex panels, centred in XY with thickness centred on Z.

[C] drawer source :435-451 and BOSL2 walls.scad hex_panel/_honeycomb,
distributors.scad grid_copies at the NOTICE pin b86a7584.
BOSL2 algorithms: Copyright (c) 2017-2019 Revar Desmera, BSD-2-Clause;
see BOSL2-LICENSE. Drawer adaptation is CC-BY-SA-4.0. The frame clips
edge cells; it does not change the centred staggered lattice.
"""
from math import cos, sin, pi, floor, isfinite, sqrt

from dataclasses import dataclass

from build123d import Box, Face, Part, Sketch, Wire, extrude
from shapely import maximum_inscribed_circle, set_precision
from shapely.affinity import affine_transform
from shapely.geometry import Point, Polygon, box

from .constants import HONEYCOMB_UNIT, HONEYCOMB_STRUT_HYP, MAX_BRIDGE_MM, MIN_LATTICE_OPENING_MM


class HoneycombPanelTooSmall(ValueError):
    """BOSL2's strict frame*2 + spacing < size guard failed."""


class HoneycombStrutOutOfRange(ValueError):
    """Unit/strut values cannot form a finite, positive hex opening."""


def strut_dimensions(strut_hyp=HONEYCOMB_STRUT_HYP, unit=HONEYCOMB_UNIT):
    """Return spacing, perpendicular strut width, hex inradius/circumradius."""
    if not all(isfinite(x) and x > 0 for x in (strut_hyp, unit)):
        raise HoneycombStrutOutOfRange('honeycomb unit and strut_hyp must be finite and positive')
    if strut_hyp < 1.1:
        raise HoneycombStrutOutOfRange('honeycomb strut_hyp must be at least 1.1 mm')
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


def roof_opening(opening, frame_up=(0, 1), *, ceiling='roofed'):
    """Return the opening minus its over-limit ceiling triangle, and chord.

    Work in (horizontal, print-up) coordinates. Intersecting the inward V
    with the source opening naturally permits two voids in a shallow cell.
    The source polygon must already include frame and fitting clipping.
    """
    if ceiling not in ('source', 'roofed'):
        raise ValueError('honeycomb ceiling must be source or roofed')
    ux, uy = frame_up
    length = (ux*ux+uy*uy)**.5
    if not isfinite(length) or length == 0:
        raise ValueError('honeycomb print up must be a finite nonzero direction')
    ux, uy = ux/length, uy/length
    upright = affine_transform(opening, [uy, -ux, ux, uy, 0, 0])
    vertices = list(upright.exterior.coords)[:-1]
    top = max(y for _, y in vertices)
    ends = sorted((x, y) for x, y in vertices if abs(y-top) < 1e-7)
    spans = [(ends[0][0], ends[-1][0], top)] + _lower_ceilings(upright, vertices, top)
    chord = max(x1-x0 for x0, x1, _ in spans)
    roofed = ceiling == 'roofed' and chord > MAX_BRIDGE_MM
    if roofed:
        x0, x1, y = spans[0]
        # The top V reaches the cell's bottom (a shallow frame-clipped cell).
        through = x1-x0 > MAX_BRIDGE_MM and y-(x1-x0)/2 < min(y for _, y in vertices)+1e-7
        for x0, x1, y in spans:
            if x1-x0 > MAX_BRIDGE_MM:
                triangle = Polygon([(x0, y), (x1, y), ((x0+x1)/2, y-(x1-x0)/2)])
                upright = upright.difference(triangle.intersection(upright))
        if ((through and upright.geom_type == 'Polygon')
                or any(x1-x0 > MAX_BRIDGE_MM for x0, x1, _ in spans[1:])):
            # A V through the cell's bottom edge can leave a ~1e-15 mm
            # bridge between the two halves (one Polygon instead of two),
            # which OCCT extrudes into an invalid cutter. A 1e-9 grid
            # collapses it into two pieces.
            upright = set_precision(upright, 1e-9)
    return affine_transform(upright, [uy, ux, -ux, uy, 0, 0]), chord, roofed


def opening_diameter(opening):
    """Inscribed circle diameter of the SMALLEST piece of a through-wall
    opening: a 45 deg roof can split a cell in two (docs/openconnect-drawer.md),
    and the small lobe is a real hole, so the cell is judged by it
    (review round 5 B1, PR #190)."""
    return min((2*maximum_inscribed_circle(p, .001).length
                for p in getattr(opening, 'geoms', [opening]) if not p.is_empty), default=0.)


def close_small_openings(openings, frame_up=(0, 1), *, ceiling='roofed'):
    """The openings whose roofed profile admits a MIN_LATTICE_OPENING_MM
    circle; the rest are closed, by size, whatever clipped them
    (docs/design-guidelines.md:46, pst-t0ob3.3 DECISION C rev (b))."""
    return [p for p in openings
            if opening_diameter(roof_opening(p, frame_up, ceiling=ceiling)[0])
            >= MIN_LATTICE_OPENING_MM]


def _lower_ceilings(upright, vertices, top):
    """Flat ceilings below the topmost one (x0, x1, y), merged along y.

    A fill can clip a cell into a flat ceiling under a short horn (the
    container's label plates); that ceiling bridges like any other.
    """
    spans = []
    for (xa, ya), (xb, yb) in zip(vertices, vertices[1:]+vertices[:1]):
        if abs(ya-yb) > 1e-7 or abs(xa-xb) < 1e-7 or ya > top-1e-7:
            continue
        mid = (xa+xb)/2
        if upright.contains(Point(mid, ya-1e-4)) and not upright.contains(Point(mid, ya+1e-4)):
            spans.append([min(xa, xb), max(xa, xb), ya])
    spans.sort(key=lambda s: (s[2], s[0]))
    merged = []
    for span in spans:
        if merged and abs(merged[-1][2]-span[2]) < 1e-7 and span[0] <= merged[-1][1]+1e-7:
            merged[-1][1] = max(merged[-1][1], span[1])
        else:
            merged.append(span)
    return [tuple(s) for s in merged]


def _without_spikes(coords):
    """Drop zero-area spike tips (the outline reverses along one line).

    Roofing a fill-clipped cell can leave one; OCCT extrudes it into an
    invalid cutter. Every other vertex, collinear or not, is kept.
    """
    points = list(coords)
    changed = True
    while changed and len(points) > 3:
        changed = False
        for i, (x, y) in enumerate(points):
            px, py = points[i-1]
            nx, ny = points[(i+1) % len(points)]
            ax, ay, bx, by = x-px, y-py, nx-x, ny-y
            if abs(ax*by-ay*bx) < 1e-9 and ax*bx+ay*by < 0:
                del points[i]
                changed = True
                break
    return points


@dataclass
class HoneycombLayout:
    """2D source cells shared by panel extrusion and the analytic span audit."""

    openings: list
    ceiling: str = 'source'
    wall: str = 'panel'

    def profiles(self, frame_up=(0, 1)):
        return [roof_opening(p, frame_up, ceiling=self.ceiling) for p in self.openings]

    def ceiling_chords(self, frame_up=(0, 1)):
        return [(self.wall, chord, roofed) for _, chord, roofed in self.profiles(frame_up)
                if chord > 1e-7]

    def cutter(self, thickness, frame_up=(0, 1)):
        """One sketch, extrusion and cutter for the entire wall."""
        if not isfinite(thickness) or thickness <= 0:
            raise ValueError('honeycomb thickness must be finite and positive')
        faces = []
        for profile, _, _ in self.profiles(frame_up):
            polygons = [profile] if profile.geom_type == 'Polygon' else profile.geoms
            for polygon in polygons:
                faces.append(Face(Wire.make_polygon(
                    [(x, y, -thickness/2) for x, y in
                     _without_spikes(list(polygon.exterior.coords)[:-1])],
                    close=True)))
        return extrude(Sketch(children=faces), amount=thickness, dir=(0, 0, 1))


def hole_solids(width, height, thickness, *, ceiling='source', frame_up=(0, 1), **kwargs):
    if not isfinite(thickness) or thickness <= 0:
        raise ValueError('honeycomb thickness must be finite and positive')
    layout = HoneycombLayout([Polygon(p) for p in hole_polygons(width, height, **kwargs)], ceiling)
    return list(layout.cutter(thickness, frame_up).solids())


class HoneycombPanel(Part):
    def ceiling_chords(self, frame_up=(0, 1)):
        return self.layout.ceiling_chords(frame_up)


def honeycomb_panel(width, height, thickness, *, strut_hyp=HONEYCOMB_STRUT_HYP,
                    unit=HONEYCOMB_UNIT, frame=None, ceiling='source',
                    frame_up=(0, 1)) -> Part:
    layout = HoneycombLayout([Polygon(p) for p in hole_polygons(
        width, height, strut_hyp=strut_hyp, unit=unit, frame=frame)], ceiling)
    result = HoneycombPanel(children=[Box(width, height, thickness).cut(
        layout.cutter(thickness, frame_up))])
    result.layout = layout
    return result
