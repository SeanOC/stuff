# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""openGrid snap grips on the monokini wall tops.

[C] monokini_I_channel.scad:205-256 monokiniGrip, :372-425
monokiniGripFlared, :426-441 monokiniGripFlaredCut. Each grip is a
SNAP_WALL-thick rail GRIP_SIZE long on one wall; its nub undercut
(SNAP_CAPTURE) faces outward and is what the openGrid tile edge snaps into.
Profile coordinates (u, v): u inward from the outer wall face, v up from
the grip base. side=+1 is the +X wall (the author's 'Left', :311), -1 the -X
wall.
"""
from __future__ import annotations

from math import radians, tan

from build123d import Box, Face, Part, Pos, Vector, Wire, extrude

from . import constants as c


def _profile(height_mm: float, z0: float) -> list[tuple[float, float]]:
    """(u, z) outline: :215-224 (z0 = wall top) or :385-394 (z0 = topChamfer)."""
    h, cap, lc = height_mm, c.SNAP_CAPTURE, c.TOP_LITTLE_CHAMFER
    return [(cap, z0), (cap, h-c.SNAP_WALL), (0., h-c.SNAP_WALL/2), (0., h-lc),
            (cap, h), (c.SNAP_WALL, h), (c.SNAP_WALL, z0)]


def _rail(width_mm, height_mm, y0, side, z0, flare_deg) -> Part:
    t = tan(radians(flare_deg))
    pts = [Vector(side*(width_mm/2 - u + z*t), y0, z) for u, z in _profile(height_mm, z0)]
    return extrude(Face(Wire.make_polygon(pts, close=True)), c.GRIP_SIZE, dir=(0, 1, 0))


def _end_ramps(width_mm, height_mm, y0, side, flare_deg) -> Part:
    """[C] :233-252 / :404-422: 45 degree cut of the top GRIP_RAMP at both ends.

    Each triangle is swept across X far enough to cover a sheared rail. (The
    flared references keep a zero-thickness CGAL skin over each ramp at the
    grip top; tests/test_underware.py masks it as a reference artefact.)
    """
    h, r = height_mm, c.GRIP_RAMP
    inner = width_mm/2 - c.SNAP_WALL - 1
    outer = width_mm/2 + height_mm*tan(radians(flare_deg)) + 1
    cuts = None
    for y_end, inward in ((y0, 1), (y0 + c.GRIP_SIZE, -1)):
        pts = [Vector(side*inner, y_end, h-r), Vector(side*inner, y_end + inward*(r+1), h+1),
               Vector(side*inner, y_end - inward, h+1), Vector(side*inner, y_end - inward, h-r)]
        tri = extrude(Face(Wire.make_polygon(pts, close=True)), outer-inner, dir=(side, 0, 0))
        cuts = tri if cuts is None else cuts + tri
    return cuts


def grip(width_mm: float, height_mm: float, y_cell: float, side: int) -> Part:
    """monokiniGrip on one wall of the cell centred at y_cell (:205-256)."""
    y0 = y_cell - c.GRIP_SIZE/2
    rail = _rail(width_mm, height_mm, y0, side, height_mm - c.BASE_HEIGHT, 0.)
    return rail - _end_ramps(width_mm, height_mm, y0, side, 0.)


def grip_flared(width_mm: float, height_mm: float, y_cell: float, side: int,
                flare_deg: float) -> Part:
    """monokiniGripFlared (:372-425): the rail runs down to TOP_CHAMFER and
    is sheared outward by skew(axz=-flare) about z=0 (x += z*tan(flare))."""
    y0 = y_cell - c.GRIP_SIZE/2
    rail = _rail(width_mm, height_mm, y0, side, c.TOP_CHAMFER, flare_deg)
    return rail - _end_ramps(width_mm, height_mm, y0, side, flare_deg)


def grip_flared_cut(width_mm: float, height_mm: float, y_cell: float, side: int) -> Part:
    """monokiniGripFlaredCut (:426-441): FLARE_SLIT relief slits through the
    wall just beyond both grip ends, from TOP_CHAMFER up (reference: the
    Grip_Flare=10 render opens y 7.495..7.895 beside a cell-centred grip)."""
    x = side*(width_mm/2 - c.NUDGE)
    zh = height_mm - c.BASE_HEIGHT
    slits = [Pos(x, y, c.TOP_CHAMFER + zh/2)*Box(c.FLARE_SLIT_DEPTH, c.FLARE_SLIT, zh)
             for y in (y_cell + c.GRIP_SIZE/2 + c.FLARE_SLIT/2,
                       y_cell - c.GRIP_SIZE/2 - c.FLARE_SLIT/2)]
    return slits[0] + slits[1]


def end_ramp_regions(width_mm: float, height_mm: float, y_cell: float, side: int,
                     flare_deg: float = 0., grow: float = 0.02) -> list[Part]:
    """Exact audit-exclusion envelopes of the two grip-end ramp faces.

    Each is the ramp cutter with its 45 degree face moved `grow` into the
    grip, so it contains that face and nothing else of the rail. The ramp
    meets the nub undercut in the author's thin lead-in wedge (pinned by
    tests/test_underware.py::test_grip_end_wedge_matches_reference).
    """
    y0 = y_cell - c.GRIP_SIZE/2
    regions = []
    for y_end, inward in ((y0, 1), (y0 + c.GRIP_SIZE, -1)):
        h, r = height_mm, c.GRIP_RAMP
        inner = width_mm/2 - c.SNAP_WALL - 1
        outer = width_mm/2 + height_mm*tan(radians(flare_deg)) + 1
        d = grow*2**0.5  # move the 45 degree face `grow` along its normal
        pts = [Vector(side*inner, y_end, h-r-d), Vector(side*inner, y_end + inward*(r+1), h+1-d),
               Vector(side*inner, y_end + inward*(r+1), h+1), Vector(side*inner, y_end - inward, h+1),
               Vector(side*inner, y_end - inward, h-r-d)]
        regions.append(extrude(Face(Wire.make_polygon(pts, close=True)), outer-inner, dir=(side, 0, 0)))
    return regions


def slit_floor_regions(width_mm: float, height_mm: float, y_cell: float, side: int,
                       grow: float = 0.02) -> list[Part]:
    """Exact envelopes of each flare slit's floor and lower inner face.

    The slit (:436-437) starts at TOP_CHAMFER: its floor lies on the tip of
    the exterior chamfer, and its inner face runs under the inset corner at
    INNER_CHAMFER, leaving the author's thin fin and floor over the chamfer.
    """
    x = side*(width_mm/2 - c.NUDGE)
    zc = (c.TOP_CHAMFER + c.INNER_CHAMFER)/2
    return [Pos(x, y, zc)*Box(c.FLARE_SLIT_DEPTH + 2*grow, c.FLARE_SLIT + 2*grow,
                              c.INNER_CHAMFER - c.TOP_CHAMFER + 2*grow)
            for y in (y_cell + c.GRIP_SIZE/2 + c.FLARE_SLIT/2, y_cell - c.GRIP_SIZE/2 - c.FLARE_SLIT/2)]
