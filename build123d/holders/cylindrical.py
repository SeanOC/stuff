"""Parametric open-front C-ring holder for cylinders (spray cans, bottles).

PoC model for the build123d "manufacturing as code" eval (bead pst-98p4).

Geometry
--------
- A C-ring collar: an annulus wrapping 360-opening_deg degrees around the
  cylinder, with the opening's entry corners rounded by real BRep fillets
  (no sharp entry edges at the lip).
- A back plate fused to the collar's back: an openGrid tile
  (``opengrid.base.Base``) whose perimeter snap lattice is the library's
  board-mount interface. The mount is 100% library geometry - no bespoke
  snap/slot shapes, nothing ported from models/. The collar fuses into the
  tile, and the bore is re-carved afterwards so the cylinder space stays
  clear of the tile lattice.

Orientation convention (defined per plan review on pst-7lgg)
-------------------------------------------------------------
- Z: cylinder axis (vertical when installed; the can is pushed in from the
  front and rests on the collar's bottom arc, grip from the 270deg wrap).
- -Y: board side. The back plate's snap face points at the openGrid board
  (the wall). +Y: front, where the opening gap faces.
- X: lateral.
Print orientation: rotate so the back plate face (the -Y face) is on the
bed; the openGrid snap face then mounts against the board.

The Multiconnect (male SnapInSlot) mount variant is a separate fast-follow
bead; ``mount="opengrid"`` is the only supported value today.
"""
from __future__ import annotations

import math

from build123d import (
    Align,
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    CenterArc,
    Cylinder,
    Line,
    Location,
    Plane,
    extrude,
)
from build123d import make_face
from build123d.topology import Part
from opengrid.base import Base
from opengrid.constants import OPEN_GRID_UNIT_SIZE

from holders.registry import ModelSpec, Param, Preset, register

# Parameter ranges (AC: out-of-range raises ValueError with a message).
D_MIN, D_MAX = 30.0, 120.0        # cylinder diameter, mm
H_MIN, H_MAX = 20.0, 120.0        # collar height (cylinder height held), mm
WALL_MIN, WALL_MAX = 1.6, 4.0     # collar wall thickness, mm
OPENING_MIN, OPENING_MAX = 60.0, 120.0  # opening arc, degrees (wrap >= 240)

LIP_RADIUS = 1.0  # mm, nominal real BRep fillet on the opening's entry corners

# Radial clearance between the cylinder and the re-carved bore, mm. Keeps the
# carve off-coplanar with the collar's inner face (a coplanar boolean left the
# exported STL non-watertight for some tile footprints) and gives the
# slip-fit holder a real insertion gap.
BORE_CLEARANCE = 0.1


def _lip_radius(wall: float) -> float:
    """Fillet radius for the opening's entry corners.

    The nominal 1.0 mm lip does not fit a thin wall: a 1.0 mm BRep fillet
    on both edges of a radial cut face consumes the full wall thickness
    (verified: it fails on the 1.6 mm minimum wall for every in-range d,
    h, and opening_deg), so the advertised wall range could not be built.
    Below the crossover the radius scales with the wall and keeps a small
    safety margin (OCCT rejects radius >= wall/2, and wall/2 itself
    leaves the fillet tangent to the bore, so we stay just under).
    """
    return min(LIP_RADIUS, 0.5 * wall - 0.02)


def _validate(d: float, h: float, wall: float, opening_deg: float, mount: str) -> None:
    for value, lo, hi, label in (
        (d, D_MIN, D_MAX, "d (cylinder diameter)"),
        (h, H_MIN, H_MAX, "h (collar height)"),
        (wall, WALL_MIN, WALL_MAX, "wall"),
        (opening_deg, OPENING_MIN, OPENING_MAX, "opening_deg"),
    ):
        if not (lo <= value <= hi):
            raise ValueError(f"{label}={value} out of range [{lo}, {hi}]")
    if mount != "opengrid":
        raise ValueError(
            f"mount={mount!r} unsupported; only 'opengrid' (Multiconnect is a "
            "separate fast-follow bead)"
        )


def _polar(r: float, angle_deg: float) -> tuple[float, float]:
    rad = math.radians(angle_deg)
    return (r * math.cos(rad), r * math.sin(rad))


def _opening_lip_edges(part: Part, a1: float, a2: float) -> list:
    """The vertical (Z-parallel) edges bounding the opening at angles a1/a2.

    These are the sharp entry corners that get the real BRep fillet. Only
    Z-parallel edges are candidates, which also skips the cylindrical
    seam edges that happen to sit at those angles.
    """

    def angle_of(edge) -> float:
        center = edge.center()
        return math.degrees(math.atan2(center.Y, center.X)) % 360.0

    def near(angle: float, ref: float) -> bool:
        diff = abs(angle - ref) % 360.0
        return min(diff, 360.0 - diff) < 2.0

    return [
        edge
        for edge in part.edges().filter_by(Axis.Z)
        if near(angle_of(edge), a1) or near(angle_of(edge), a2)
    ]


def holder(
    d: float,
    h: float,
    wall: float = 2.4,
    opening_deg: float = 90.0,
    mount: str = "opengrid",
) -> Part:
    """Build the C-ring cylinder holder.

    Args:
        d: cylinder (can/bottle) diameter, mm. Range [30, 120].
        h: collar height (how much of the cylinder is held), mm.
        wall: collar wall thickness, mm. Range [1.6, 4].
        opening_deg: opening arc of the C-ring, degrees. Range [60, 120],
            i.e. the collar always wraps at least 240 degrees.
        mount: back-plate mount system. Only ``"opengrid"`` today.
    """
    _validate(d, h, wall, opening_deg, mount)

    r_in = d / 2.0
    r_out = r_in + wall
    a1 = 90.0 - opening_deg / 2.0  # opening centered on +Y (front, away from board)
    a2 = 90.0 + opening_deg / 2.0

    # --- C-ring collar ---------------------------------------------------
    annulus = (
        Cylinder(radius=r_out, height=h, align=(Align.CENTER, Align.CENTER, Align.MIN))
        - Cylinder(radius=r_in, height=h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    )
    wedge_r = r_out + 6.0
    with BuildPart() as wedge:
        with BuildSketch(Plane.XY):
            with BuildLine():
                Line((0, 0), _polar(wedge_r, a1))
                CenterArc((0, 0), wedge_r, start_angle=a1, arc_size=opening_deg)
                Line(_polar(wedge_r, a2), (0, 0))
            make_face()
        # Collar spans z 0..h (Align.MIN); overshoot 1mm at the bottom so
        # the cut is through-all and not coplanar with the collar's faces.
        extrude(amount=h + 1.0, dir=(0, 0, 1))
    wedge_part = wedge.part.moved(Location((0, 0, -1.0)))
    collar = annulus - wedge_part

    # Real BRep fillets on the opening's entry corners (AC: no sharp lips).
    # Radius scales down for thin walls so the full [WALL_MIN, WALL_MAX]
    # range stays buildable (see _lip_radius).
    lip_edges = _opening_lip_edges(collar, a1, a2)
    collar = collar.fillet(radius=_lip_radius(wall), edge_list=lip_edges)

    # --- openGrid back-plate mount (100% library geometry) ---------------
    # Tile footprint in whole 28mm grid cells: wide enough to clear the
    # collar diameter, tall enough to clear the collar height.
    x_count = max(1, int(math.ceil(d / OPEN_GRID_UNIT_SIZE)))
    y_count = max(1, int(math.ceil(h / OPEN_GRID_UNIT_SIZE)))
    tile = Base(x_count=x_count, y_count=y_count)
    # Stand the tile vertical: local Z (thickness, 0..6.8) -> global Y.
    # Snap face (local +Z) ends up on -Y: the board side.
    tile = tile.moved(Location((0, 0, 0), (1, 0, 0), 90))
    # Straddle the collar's back wall (y in [-r_out, -r_in]) so the fuse
    # gets solid overlap, not a tangent touch. The +4.0 centering (vs the
    # exact wall midplane at 3.4) moves the bore's re-carve cut face off
    # the tile lattice faces; at the exact midplane the carve was
    # degenerate for several footprints and left open STL edges at h=20.
    back_center_y = -(r_in + r_out) / 2.0
    tile = tile.moved(Location((0, back_center_y + 4.0, h / 2.0)))

    part = collar.fuse(tile)

    # Re-carve the bore so the tile lattice never intrudes into the
    # cylinder space (the tile's front 5+mm of overlap is removed).
    bore = Cylinder(
        radius=r_in + BORE_CLEARANCE,
        height=h + 8.0,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    part = (part - bore).clean()
    return part


def _params(d: float, h: float) -> tuple[Param, ...]:
    """Param spec for one holder instance — defaults carry THAT model's
    shape (spray can vs bottle), so each registered model keeps its own
    identity in the default export and in the manifest."""
    return (
        Param(
            name="d",
            kind="number",
            default=d,
            min=D_MIN,
            max=D_MAX,
            step=1.0,
            unit="mm",
            label="Cylinder diameter",
            group="geometry",
        ),
        Param(
            name="h",
            kind="number",
            default=h,
            min=H_MIN,
            max=H_MAX,
            step=1.0,
            unit="mm",
            label="Collar height",
            group="geometry",
        ),
        Param(
            name="wall",
            kind="number",
            default=2.4,
            min=WALL_MIN,
            max=WALL_MAX,
            step=0.1,
            unit="mm",
            label="Wall thickness",
            group="geometry",
        ),
        Param(
            name="opening_deg",
            kind="number",
            default=90.0,
            min=OPENING_MIN,
            max=OPENING_MAX,
            step=5.0,
            unit="deg",
            label="Opening arc",
            group="geometry",
        ),
    )


def _build(values: dict) -> Part:
    return holder(**values)


register(
    ModelSpec(
        name="holder_spray_can",
        build=_build,
        description="open-front C-ring holder, spray can (d=66, collar h=60), openGrid tile back plate",
        tags=("holder", "opengrid", "cylindrical"),
        params=_params(66.0, 60.0),
        presets=(
            Preset(
                id="spray_can",
                label="Spray can (d=66, h=60)",
                values={"d": 66.0, "h": 60.0},
            ),
        ),
        title="Spray can holder",
        category_id="multiboard",
    )
)
register(
    ModelSpec(
        name="holder_bottle_500ml",
        build=_build,
        description="open-front C-ring holder, 500ml bottle (d=73, collar h=50), openGrid tile back plate",
        tags=("holder", "opengrid", "cylindrical"),
        params=_params(73.0, 50.0),
        presets=(
            Preset(
                id="bottle_500ml",
                label="500ml bottle (d=73, h=50)",
                values={"d": 73.0, "h": 50.0},
            ),
        ),
        title="500ml bottle holder",
        category_id="multiboard",
    )
)
