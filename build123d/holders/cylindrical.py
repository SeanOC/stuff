"""Parametric open-front C-ring holder for cylinders (spray cans, bottles).

PoC model for the build123d "manufacturing as code" eval (bead pst-98p4).

Geometry
--------
- A C-ring collar: an annulus wrapping 360-opening_deg degrees around the
  cylinder, with the opening's entry corners rounded by real BRep fillets
  (no sharp entry edges at the lip).
- A solid back plate fused to the collar's back, carrying Multiconnect
  SLOT geometry cut straight from the library
  (``opengrid.multiconnect.SnapInSlotCutter``). The holder slides down onto
  wall-mounted Multiconnect round heads (the wall side is out of scope):
  each round head enters the wide top opening and seats in the narrow slot,
  the snap-in side notches locking it without tools. The mount is 100%
  library geometry - the pockets are the library's own cutter, nothing
  bespoke, nothing ported from models/. The slot count scales with plate
  width at the library's 28 mm (``OPEN_GRID_UNIT_SIZE``) pitch.

Orientation convention (defined per plan review on pst-7lgg)
-------------------------------------------------------------
- Z: cylinder axis (vertical when installed; the can is pushed in from the
  front and rests on the collar's bottom arc, grip from the 270deg wrap).
  The Multiconnect slots slide along +Z, so the holder drops DOWN onto the
  wall heads and gravity keeps it seated.
- -Y: board side. The back plate's mount face (where the slot pockets open)
  points at the wall. +Y: front, where the opening gap faces.
- X: lateral (slots are spaced along X at the 28 mm pitch).
Print orientation: rotate so the back plate face (the -Y face) is on the
bed; the slot pockets then face up and print cleanly (the openings that the
round heads slide into are self-supporting in this orientation).
"""
from __future__ import annotations

import math

from build123d import (
    Align,
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Box,
    CenterArc,
    Cylinder,
    Line,
    Location,
    Plane,
    Pos,
    extrude,
)
from build123d import make_face
from build123d.topology import Part
from opengrid.constants import OPEN_GRID_UNIT_SIZE
from opengrid.multiconnect import SnapInSlotCutter

from holders.registry import ModelSpec, Param, Preset, register

# Parameter ranges (AC: out-of-range raises ValueError with a message).
D_MIN, D_MAX = 30.0, 120.0        # cylinder diameter, mm
H_MIN, H_MAX = 20.0, 120.0        # collar height (cylinder height held), mm
WALL_MIN, WALL_MAX = 1.6, 4.0     # collar wall thickness, mm
OPENING_MIN, OPENING_MAX = 60.0, 120.0  # opening arc, degrees (wrap >= 240)

LIP_RADIUS = 1.0  # mm, nominal real BRep fillet on the opening's entry corners

# Radial clearance between the cylinder and the re-carved bore, mm. Keeps the
# carve off-coplanar with the collar's inner face (a coplanar boolean left the
# exported STL non-watertight for some footprints) and gives the slip-fit
# holder a real insertion gap.
BORE_CLEARANCE = 0.1

# --- Multiconnect slot back plate (100% library geometry) ----------------
# The mount is a solid rectangular plate that stands proud of the collar's
# back and carries opengrid.multiconnect.SnapInSlotCutter pockets. The
# holder slides DOWN (+Z) onto wall-mounted round heads.
#
# PANEL_THICKNESS must exceed the ~4.15 mm library pocket depth so solid
# material backs every pocket. It also exceeds the collar wall (<=4 mm), so
# the plate stands proud of the collar - the plate front face touches the
# collar's INNER radius (a full-wall fuse), the mount face sits one panel
# thickness further out, and the pocket back lands well clear of the bore.
PANEL_THICKNESS = 6.4   # mm, plate thickness along Y (pocket ~4.15 + backing)
SLOT_PITCH = OPEN_GRID_UNIT_SIZE  # 28 mm, the library's Multiconnect spacing

# The library SnapInSlotCutter, at rotation (-90, 0, 0), spans ~+/-16.7 mm in
# X (slot body + snap-in side notches) and z in [seat-10.15, seat+28].
_SLOT_HALF_WIDTH = 16.75   # mm, notch reach either side of a slot centre
_SLOT_BELOW_SEAT = 10.15   # mm, slot body below the head seat
_SLOT_ABOVE_SEAT = 28.0    # mm, slide travel above the head seat (opening)
_SLOT_EDGE_MARGIN = 3.0    # mm, solid plate margin around the slot envelope

# One slot for holders up to ~3 grid units wide; two for wider/heavier ones.
TWO_SLOT_WIDTH_THRESHOLD = 84.0  # mm (3 * OPEN_GRID_UNIT_SIZE)

# Minimum plate width to host N slots without the notches breaking the edge.
def _min_plate_width(n_slots: int) -> float:
    span = (n_slots - 1) * SLOT_PITCH + 2 * _SLOT_HALF_WIDTH
    return span + 2 * _SLOT_EDGE_MARGIN

# Minimum plate height to host the full slot envelope with margins.
MIN_PLATE_HEIGHT = _SLOT_BELOW_SEAT + _SLOT_ABOVE_SEAT + 2 * _SLOT_EDGE_MARGIN


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


def _validate(d: float, h: float, wall: float, opening_deg: float) -> None:
    for value, lo, hi, label in (
        (d, D_MIN, D_MAX, "d (cylinder diameter)"),
        (h, H_MIN, H_MAX, "h (collar height)"),
        (wall, WALL_MIN, WALL_MAX, "wall"),
        (opening_deg, OPENING_MIN, OPENING_MAX, "opening_deg"),
    ):
        if not (lo <= value <= hi):
            raise ValueError(f"{label}={value} out of range [{lo}, {hi}]")


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


def slot_count(plate_width: float) -> int:
    """Number of Multiconnect slots for a plate of this width.

    One slot carries a spray-can-class holder; wider/heavier holders
    (>= 84 mm, three grid units) get two slots at the library's 28 mm
    pitch for extra bearing surface and anti-rotation.
    """
    return 2 if plate_width >= TWO_SLOT_WIDTH_THRESHOLD else 1


def _slot_x_positions(n_slots: int) -> list[float]:
    """Slot centre X positions, symmetric about 0 at the library pitch."""
    return [(-(n_slots - 1) / 2.0 + i) * SLOT_PITCH for i in range(n_slots)]


def _plate_geometry(r_in: float, r_out: float, h: float) -> tuple[float, float, float, float, int]:
    """Derived back-plate dimensions: (width, plate_h, mount_y, z_seat, n_slots).

    The plate front face touches the collar's inner radius (``-r_in``) so it
    fuses through the full collar wall; the mount face sits one panel
    thickness further out (-Y), standing proud of the collar. The head seat
    is placed so the wide slot opening sits just below the plate top and the
    whole slot envelope stays inside the plate height.
    """
    collar_width = 2.0 * r_out
    n_slots = slot_count(collar_width)
    width = max(collar_width, _min_plate_width(n_slots))
    plate_h = max(h, MIN_PLATE_HEIGHT)
    mount_y = -r_in - PANEL_THICKNESS
    z_seat = plate_h - _SLOT_ABOVE_SEAT - _SLOT_EDGE_MARGIN
    return width, plate_h, mount_y, z_seat, n_slots


def _back_plate_solid(r_in: float, r_out: float, h: float) -> Part:
    """The plain (un-pocketed) back-plate box behind the collar."""
    width, plate_h, mount_y, _z_seat, _n = _plate_geometry(r_in, r_out, h)
    return Pos(0, mount_y, 0) * Box(
        width, PANEL_THICKNESS, plate_h,
        align=(Align.CENTER, Align.MIN, Align.MIN),
    )


def slot_cutters(r_in: float, r_out: float, h: float) -> list[Part]:
    """The library Multiconnect slot cutters, positioned on the back plate.

    Each is ``opengrid.multiconnect.SnapInSlotCutter`` at rotation
    (-90, 0, 0): pocket depth -> +Y (into the plate from the -Y mount face),
    slide -> +Z (opening at the plate top), width -> X. Verified against the
    library's own ``snap_in_slot_cutter_fitting_test`` recipe. The holder
    slides DOWN onto wall-mounted round heads; the snap-in side notches lock
    each head in place. 100% library geometry - no bespoke slot solids.
    """
    _w, _ph, mount_y, z_seat, n_slots = _plate_geometry(r_in, r_out, h)
    return [
        Pos(x, mount_y, z_seat) * SnapInSlotCutter(rotation=(-90, 0, 0))
        for x in _slot_x_positions(n_slots)
    ]


def holder(
    d: float,
    h: float,
    wall: float = 2.4,
    opening_deg: float = 90.0,
) -> Part:
    """Build the C-ring cylinder holder.

    Args:
        d: cylinder (can/bottle) diameter, mm. Range [30, 120].
        h: collar height (how much of the cylinder is held), mm.
        wall: collar wall thickness, mm. Range [1.6, 4].
        opening_deg: opening arc of the C-ring, degrees. Range [60, 120],
            i.e. the collar always wraps at least 240 degrees.
    """
    _validate(d, h, wall, opening_deg)

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

    # --- Multiconnect slot back plate (100% library geometry) ------------
    # Fuse a solid plate to the collar's back, then carve the library's own
    # SnapInSlotCutter pockets out of the unified body so each pocket is
    # exactly the library cutter (nothing bespoke, no refilled sliver).
    part = collar.fuse(_back_plate_solid(r_in, r_out, h))
    for cutter in slot_cutters(r_in, r_out, h):
        part = part - cutter

    # Re-carve the bore so no plate material intrudes into the cylinder
    # space (the plate front face sits at the inner radius; this trims the
    # coincident sliver and keeps the boolean off-coplanar with the bore).
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
        description="open-front C-ring holder, spray can (d=66, collar h=60), Multiconnect slot back plate",
        tags=("holder", "multiconnect", "cylindrical"),
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
        description="open-front C-ring holder, 500ml bottle (d=73, collar h=50), Multiconnect slot back plate",
        tags=("holder", "multiconnect", "cylindrical"),
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
