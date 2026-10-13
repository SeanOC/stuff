"""Sign / stake joint contract, QR helper and tombstone outline (epic pst-tl4ac).

The tombstone sign (S1, holders/tombstone_sign.py) carries POCKET_COUNT
tenon pockets in its bottom edge; the stake (S2) carries the matching
tenons. Both import the numbers below and nothing else, so the joint
cannot drift between the two parts. All lengths in mm.

Sign frame (the print frame of a face-down sign): X across the sign, Y up
the sign from its bottom edge (Y = 0), Z through the plate (Z = 0 is the
bed face). A pocket is an 8 mm wide slot entering the bottom edge, between
a SKIN on each face: X in centre +- POCKET_W / 2, Y in [0, POCKET_DEPTH],
Z in [SKIN, thickness - SKIN]. Printed flat, its roof is a POCKET_W bridge
(MAX_BRIDGE_MM is 10, so POCKET_W must stay <= 9).

Tenon (the stake's prong): POCKET_W, POCKET_DEPTH and the pocket height,
each less 2 x JOINT_CLEARANCE, so a centred tenon clears every pocket wall
by exactly JOINT_CLEARANCE. Its length leaves the same 0.4 at the pocket
end: the stake's shoulder bears on the sign's bottom edge, never the end.

retention='pin': one PIN_D cross-hole on PIN_AXIS (X, the pocket-width
axis) at Y = PIN_FROM_BOTTOM, Z = thickness / 2, through the plate's solid
walls and both pockets; S2 drills the same axis through each tenon, so the
plate hole and the tenon hole are one hole by construction. A tenon keeps
>= MIN_WALL_MM above and below the hole only if tenon_t - PIN_D >= 2 x
MIN_WALL_MM, i.e. thickness >= PIN_MIN_THICKNESS (7.8). The hole prints on
its side, so its section is a flat-topped teardrop (pin_profile): round
below, 45-degree flanks, a short flat roof, exactly PIN_D tall and wide.
"""
from __future__ import annotations

import math

import segno
from build123d import (Align, Circle, Part, Plane, Polygon, Pos, Rectangle, Sketch, extrude,
                       fillet)
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

# --- joint contract (S1 pockets, S2 tenons) -------------------------------
POCKET_COUNT = 2
POCKET_W = 8.0             # across X; the printed roof bridge (<= 9)
POCKET_DEPTH = 35.0        # along Y from the bottom edge
POCKET_OFFSET = 40.0       # pocket centres at X = +-POCKET_OFFSET
POCKET_XS = (-POCKET_OFFSET, POCKET_OFFSET)
SKIN = 1.2                 # plate skin on each face over a pocket
JOINT_CLEARANCE = 0.2      # tenon to pocket, per side, every axis

PIN_D = 3.2                # cross-pin hole (nail / 1.75 filament pin)
PIN_AXIS = (1.0, 0.0, 0.0)  # the pocket-width axis
PIN_FROM_BOTTOM = 20.0     # hole axis Y; inside POCKET_DEPTH
MIN_WALL_MM = 0.9          # tests/print_audit.py MIN_WALL_MM (kept in step by a test)
PIN_MIN_THICKNESS = round(PIN_D + 2 * MIN_WALL_MM + 2 * SKIN + 2 * JOINT_CLEARANCE, 6)  # 7.8

# Every colour inlay sits at least this far above the bottom edge: a 0.6
# inlay over a pocket would leave 1.2 - 0.6 = 0.6 < MIN_WALL_MM of skin.
INLAY_FLOOR = POCKET_DEPTH


def pocket_height(thickness: float) -> float:
    return thickness - 2 * SKIN


def tenon_w() -> float:
    return POCKET_W - 2 * JOINT_CLEARANCE                  # 7.6


def tenon_len() -> float:
    return POCKET_DEPTH - 2 * JOINT_CLEARANCE              # 34.6


def tenon_t(thickness: float) -> float:
    return thickness - 2 * SKIN - 2 * JOINT_CLEARANCE      # 3.2 at 6, 5.2 at 8


def pocket_rect(x: float, thickness: float):
    """One pocket's X-Z section (shapely), for the 2D joint test."""
    return box(x - POCKET_W / 2, SKIN, x + POCKET_W / 2, thickness - SKIN)


def tenon_rect(x: float, thickness: float):
    """The matching tenon's X-Z section, centred in the pocket."""
    zc = thickness / 2
    return box(x - tenon_w() / 2, zc - tenon_t(thickness) / 2,
               x + tenon_w() / 2, zc + tenon_t(thickness) / 2)


def check_pin_thickness(thickness: float) -> None:
    if thickness < PIN_MIN_THICKNESS - 1e-9:
        raise ValueError(
            f"retention 'pin' needs thickness >= {PIN_MIN_THICKNESS:g} mm (got {thickness:g}): "
            f'the {tenon_t(thickness):.1f} mm tenon must keep {MIN_WALL_MM:g} mm above and '
            f'below the {PIN_D:g} mm pin hole')


def pin_profile(cy: float, cz: float) -> Sketch:
    """The pin hole's section on Plane.YZ (local u = Y, v = Z), centred (cy, cz).

    A Ø PIN_D circle whose top is replaced by its 45-degree tangent flanks,
    cut flat at the circle's top: no downward face steeper than 45 degrees
    except a 2r(sqrt 2 - 1) = 1.33 mm flat roof (a bridge), and the section
    stays exactly PIN_D wide and tall.
    """
    r = PIN_D / 2
    t = r / math.sqrt(2)  # the 45-degree tangent points sit at (+-t, t)
    flanks = Polygon((-t, t), (0, r * math.sqrt(2)), (t, t), align=None)
    drop = (Circle(r) + flanks) & Rectangle(2 * r, 2 * r)
    return Plane.YZ * Pos(cy, cz) * drop


def pin_hole(width: float, thickness: float) -> Part:
    """The cross-hole as a solid, through the whole plate width along X."""
    section = pin_profile(PIN_FROM_BOTTOM, thickness / 2)
    return extrude(section, width / 2 + 1, both=True)


# --- QR -------------------------------------------------------------------
QR_ERROR = 'm'
QR_QUIET = 4               # modules of quiet zone on every side (ISO minimum)
MIN_QR_PITCH = 2.0         # mm per module: >= 5 extrusion lines at 0.4


def qr_matrix(url: str) -> tuple[tuple[bool, ...], ...]:
    """The QR module matrix (row 0 at the top, True = dark), no quiet zone.

    Error level M exactly (no boost), version chosen by segno from the data.
    """
    qr = segno.make(url, error=QR_ERROR, micro=False, boost_error=False)
    return tuple(tuple(bool(v) for v in row) for row in qr.matrix)


def qr_symbol_size(url: str) -> int:
    """Modules across the whole symbol, quiet zone included."""
    return len(qr_matrix(url)) + 2 * QR_QUIET


def qr_pitch(url: str, qr_size: float) -> float:
    return qr_size / qr_symbol_size(url)


def min_qr_size(url: str) -> float:
    return MIN_QR_PITCH * qr_symbol_size(url)


def qr_regions(url: str, qr_size: float, eps: float = 0.01):
    """(dark, light) shapely regions of the QR block centred on the origin.

    The block is qr_size square, quiet zone included. Dark modules are
    merged and shrunk by eps so diagonal neighbours never share an edge
    (that edge would make the ink body non-manifold); light is the block
    minus dark. Raises ValueError when the pitch is below MIN_QR_PITCH.
    """
    matrix = qr_matrix(url)
    pitch = qr_size / (len(matrix) + 2 * QR_QUIET)
    if pitch < MIN_QR_PITCH:
        raise ValueError(
            f'qr_size {qr_size:g} mm gives a {pitch:.2f} mm module pitch for {url!r}, '
            f'below the {MIN_QR_PITCH:g} mm minimum; qr_size must be >= '
            f'{min_qr_size(url):g} mm')
    half = qr_size / 2
    cells = [box(-half + (QR_QUIET + c) * pitch, half - (QR_QUIET + r + 1) * pitch,
                 -half + (QR_QUIET + c + 1) * pitch, half - (QR_QUIET + r) * pitch)
             for r, row in enumerate(matrix) for c, dark in enumerate(row) if dark]
    dark = unary_union(cells).buffer(-eps, join_style=2).simplify(0)
    light = box(-half, -half, half, half).difference(dark).simplify(0)
    return dark, light


# --- outline ---------------------------------------------------------------
CORNER_R = 3.0             # plan-view rounding of the outline's convex corners


def arch_radius(width: float, arch: str) -> float:
    """'round': a full semicircle over the width; 'shoulder': a third of it."""
    return width / 2 if arch == 'round' else width / 3


def min_outline_height(width: float, arch: str) -> float:
    """outline()'s precondition: a straight side of at least 2 x CORNER_R under
    the arch (the bottom fillet, and the shoulder fillet for 'shoulder')."""
    return arch_radius(width, arch) + 2 * CORNER_R


def outline(width: float, height: float, arch: str) -> Sketch:
    """The tombstone in plan: bottom edge on Y = 0, centred on X = 0.

    Straight sides, a flat bottom and an arched top whose crown is at
    Y = height. 'shoulder' adds flat shoulders either side of a smaller
    arch. Corners that are not tangent are rounded CORNER_R in plan.
    """
    r = arch_radius(width, arch)
    yc = height - r
    body = Rectangle(width, yc, align=(Align.CENTER, Align.MIN))
    crown = Pos(0, yc) * (Circle(r) & Rectangle(2 * r, r, align=(Align.CENTER, Align.MIN)))
    shape = body + crown
    corners = [v for v in shape.vertices()
               if v.Y < 1e-6 or (arch == 'shoulder' and abs(v.Y - yc) < 1e-6)]
    return fillet(corners, CORNER_R)


def outline_region(width: float, height: float, arch: str):
    """outline() for layout (shapely, corners left square: conservative)."""
    r = arch_radius(width, arch)
    yc = height - r
    crown = Point(0, yc).buffer(r, quad_segs=256).intersection(box(-r, yc, r, height + 1))
    return unary_union([box(-width / 2, 0, width / 2, yc), crown])


def inner_width(region, y: float) -> float:
    """Width of region along the horizontal line at y, through X = 0 (0 if none)."""
    x0, _, x1, _ = region.bounds
    cut = region.intersection(LineString([(x0 - 1, y), (x1 + 1, y)]))
    pieces = [g for g in getattr(cut, 'geoms', [cut]) if not g.is_empty]
    through = [g for g in pieces if g.bounds[0] <= 0 <= g.bounds[2]]
    return through[0].length if through else 0.0
