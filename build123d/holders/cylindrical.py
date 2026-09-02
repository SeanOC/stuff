"""Parametric open-front C-ring holder for cylinders (spray cans, bottles).

PoC model for the build123d "manufacturing as code" eval (bead pst-98p4).

Geometry
--------
- A C-ring collar: an annulus wrapping 360-opening_deg degrees around the
  cylinder, with the opening's entry corners rounded by real BRep fillets
  (no sharp entry edges at the lip). A solid FLOOR closes the collar
  bottom so an item rests on it instead of dropping through the bore; the
  front opening stays open above the floor.
- A solid back plate fused to the collar's back, carrying Multiconnect
  SLOT geometry cut straight from the library
  (``opengrid.multiconnect.SnapInSlotCutter``). The holder lowers straight
  DOWN onto wall-mounted Multiconnect round heads (the wall side is out of
  scope): each round head enters the aperture at the plate's BOTTOM edge
  and rides up to the narrow seat, the snap-in side notches locking it
  without tools; the holder's weight then keeps the head seated. The mount
  is 100% library geometry - the pockets are the library's own cutter,
  nothing bespoke, nothing ported from models/. The slot count scales with
  plate width at the library's 28 mm (``OPEN_GRID_UNIT_SIZE``) pitch.

Orientation convention (defined per plan review on pst-7lgg)
-------------------------------------------------------------
- Z: cylinder axis (vertical when installed; the can is pushed in from the
  front and rests on the FLOOR, grip from the 270deg wrap). The Multiconnect
  slot openings face -Z (the plate's bottom edge), so the holder drops DOWN
  onto the wall heads and its weight keeps them seated.
- -Y: board side. The back plate's mount face (where the slot pockets open)
  points at the wall. +Y: front, where the opening gap faces.
- X: lateral (slots are spaced along X at the 28 mm pitch).
Print orientation: **as modelled, +Z up — the floor disc (z=0) on the bed**
(``print_orientation = (0, 0, 1)``, the ModelSpec default). This stands the
cylinder axis vertical, so the collar prints as an upright ring (no side
overhang) and the large flat floor is the first layer (excellent adhesion);
the slot openings sit at the plate's bottom (z=0) edge and self-support. This
supersedes an earlier note that put the -Y mount face on the bed — that pose
lays the cylinder on its side and overhangs ~9300 mm^2 (57x this pose), so it
is NOT the print orientation. Trade-off: the wall load (the can's weight,
along -Z) then runs across the print layers at the cup-plate joint, which the
§4 web + junction fillet reinforce (worst-case load direction: -Z shear +
the +Y cantilever moment that peels the plate's top off the wall).

Edge treatment and the printability audit are measured in THIS pose: the bed
is the z=0 face; "downward" is -Z.
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
    Locations,
    Plane,
    Pos,
    Rotation as Rot,
    extrude,
)
from build123d import make_face
from build123d.topology import Part
from opengrid.constants import (
    MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS,
    OPEN_GRID_UNIT_SIZE,
)
from opengrid.multiconnect import RoundHeadCutter, Slot, SlotCutter, SnapInSlotCutter

from holders.registry import ModelSpec, MountFixtures, Param, Preset, register

# Parameter ranges (AC: out-of-range raises ValueError with a message).
D_MIN, D_MAX = 30.0, 120.0        # cylinder diameter, mm
H_MIN, H_MAX = 20.0, 120.0        # collar height (cylinder height held), mm
WALL_MIN, WALL_MAX = 1.6, 4.0     # collar wall thickness, mm
OPENING_MIN, OPENING_MAX = 60.0, 120.0  # opening arc, degrees (wrap >= 240)
FLOOR_MIN, FLOOR_MAX = 1.6, 10.0  # floor (base) thickness, mm
# Default floor is ~2x the default wall (2.4 mm) — a solid base that
# closes the collar bottom so a can rests on it instead of dropping
# through the bore. Always on by default (the range starts at a
# printable 1.6 mm); the front opening stays open ABOVE the floor.
FLOOR_DEFAULT = 4.8
# The floor disc is inset this far under the collar's outer radius. A disc
# at exactly r_out shares a coincident cylindrical face with the collar
# wall, which OCCT tessellates degenerately for thin walls (some footprints
# exported non-watertight). 0.1 mm inside the wall is visually nil but
# gives the fuse a clean, non-coincident boundary.
FLOOR_EDGE_INSET = 0.1

LIP_RADIUS = 1.0  # mm, nominal real BRep fillet on the opening's entry corners

# --- Edge treatment (design-guidelines §1, §2) ---------------------------
# User-exposed, non-functional edges get a fillet (top + vertical) or a 45°
# chamfer (bed-contact / downward). Functional edges stay sharp: the mount
# face, slot walls, snap notches, the bore. Applied to the fused body BEFORE
# the library slot pockets are carved, so the treatment never touches the
# cutter profile (its geometry is the spec) — §2's "never on library cutters".
EDGE_FILLET = 1.5   # mm, R on outer vertical + top/rim edges (§2: R 1-2 mm)
BED_CHAMFER = 0.4   # mm, 45° chamfer on bed-contact + downward edges (§1:
                    # 0.3-0.5 mm elephant-foot relief; NEVER a downward fillet)

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
_SLOT_BELOW_SEAT = 10.15   # mm, slot body on the closed (seat) side
_SLOT_ABOVE_SEAT = 28.0    # mm, DEFAULT slide travel on the OPEN (entry) side
                           # (== the library MULTICONNECT_SLOT_LENGTH). Now the
                           # default of the ``slot_travel`` mount tunable (§5).
# Pocket depth along the dovetail taper axis (narrow lip -> wide flange), i.e.
# the library slot's clearanced z0..z3: bottom_height 1 + bottom clearance
# 0.212132 + taper 2.5 + top_height 0.5 + top clearance -0.062132 = 4.15 mm.
# The pocket is anchored one POCKET_DEPTH inside the -Y mount face so its WIDE
# (retention) end lands at the pocket back and its NARROW lip at the mount
# face — the head's wide pad seats BEHIND the lip (bug pst-p07j: the pocket
# was carved inverted, wide at the open surface, so nothing retained the head).
POCKET_DEPTH = 4.15
_SLOT_EDGE_MARGIN = 3.0    # mm, DEFAULT solid plate margin around the slot
                           # envelope (the default of the ``plate_margin`` §5
                           # tunable).
# The channel entry (slide opening) must cut THROUGH the plate's bottom
# edge so a wall head can enter — a sealed pocket has no way in. Position
# the seat so the opening mouth pokes this far BELOW the plate bottom
# (z=0), guaranteeing a clean aperture rather than a tangent edge.
_SLOT_BOTTOM_OVERSHOOT = 2.0
# The two round-head cutters the library carves at the seat are spaced this
# far apart along the slide axis (opengrid.multiconnect.SnapInSlotCutter's
# ``head_spacing`` default). Mirrored here so the no-notch cutter reproduces
# the library seat exactly (see ``_slot_cutter``).
_HEAD_SPACING = 0.795

# --- Mount tunables (design-guidelines §5) -------------------------------
# Expose what changes the ROBUSTNESS of the mount; never the spec (pitch,
# head/slot profile, clearances, pocket depth stay library constants).
SLOT_COUNT_MIN, SLOT_COUNT_MAX = 1, 3      # slots at the fixed 28 mm pitch
PLATE_MARGIN_MIN, PLATE_MARGIN_MAX = 2.0, 6.0   # mm, solid material round slots
PLATE_MARGIN_DEFAULT = _SLOT_EDGE_MARGIN        # 3.0 mm — today's number
# ``slot_travel`` is the library SlotCutter LENGTH: the slide the wall head
# rides from the bottom aperture up to the seat. §5 lists slot travel/length
# as a robustness tunable (the cross-section PROFILE stays spec). The FLOOR is
# derived from library constants, not guessed: a seated RoundHead spans one
# bottom-radius either side of the seat, so the seat must sit at least one
# head-radius above the aperture for the head to enter fully and be captured
# WITHIN the plate (below this the seated head pokes back out the bottom
# aperture). seat_z = slot_travel - overshoot, so slot_travel_min = head bottom
# radius + overshoot. Proven by test_cylindrical (a head enters + seats at the
# minimum, and pokes out just below it).
SLOT_TRAVEL_MIN = MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS + _SLOT_BOTTOM_OVERSHOOT  # 12
SLOT_TRAVEL_MAX = 45.0
SLOT_TRAVEL_DEFAULT = _SLOT_ABOVE_SEAT     # 28.0 mm (== MULTICONNECT_SLOT_LENGTH)

# One slot for holders up to ~3 grid units wide; two for wider/heavier ones.
# Only used to pick each model's DEFAULT ``slot_count`` so presets don't change
# (the count is now an explicit tunable — see ``_params``).
TWO_SLOT_WIDTH_THRESHOLD = 84.0  # mm (3 * OPEN_GRID_UNIT_SIZE)

# Plate width hosting N slots at the pitch, with the notch reach + margin on
# every side (§3: the plate is the slot ENVELOPE + margin, nothing more).
def _min_plate_width(n_slots: int, plate_margin: float = PLATE_MARGIN_DEFAULT) -> float:
    span = (n_slots - 1) * SLOT_PITCH + 2 * _SLOT_HALF_WIDTH
    return span + 2 * plate_margin

# Plate height hosting the full slot envelope (seat cap + slide travel) with
# margins top and bottom.
def _plate_height(
    slot_travel: float = SLOT_TRAVEL_DEFAULT, plate_margin: float = PLATE_MARGIN_DEFAULT
) -> float:
    return _SLOT_BELOW_SEAT + slot_travel + 2 * plate_margin


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


def _validate(
    d: float,
    h: float,
    wall: float,
    opening_deg: float,
    floor_thickness: float,
    slot_count: int,
    slot_travel: float,
    plate_margin: float,
) -> None:
    for value, lo, hi, label in (
        (d, D_MIN, D_MAX, "d (cylinder diameter)"),
        (h, H_MIN, H_MAX, "h (collar height)"),
        (wall, WALL_MIN, WALL_MAX, "wall"),
        (opening_deg, OPENING_MIN, OPENING_MAX, "opening_deg"),
        (floor_thickness, FLOOR_MIN, FLOOR_MAX, "floor_thickness"),
        (slot_count, SLOT_COUNT_MIN, SLOT_COUNT_MAX, "slot_count"),
        (slot_travel, SLOT_TRAVEL_MIN, SLOT_TRAVEL_MAX, "slot_travel"),
        (plate_margin, PLATE_MARGIN_MIN, PLATE_MARGIN_MAX, "plate_margin"),
    ):
        if not (lo <= value <= hi):
            raise ValueError(f"{label}={value} out of range [{lo}, {hi}]")
    if int(slot_count) != slot_count:
        raise ValueError(f"slot_count={slot_count} must be a whole number")


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


def _slot_cutter(slot_travel: float, snap_notches: bool) -> Part:
    """One Multiconnect slot cutter, at rotation (90, 0, 0), sized to
    ``slot_travel`` — 100% library geometry, the cross-section PROFILE fixed.

    ``slot_travel`` is the library ``SlotCutter`` LENGTH (the slide the wall
    head rides from the bottom aperture to the seat). It is threaded in via a
    ``Slot`` subclass that only overrides ``length`` — every width, height,
    taper and clearance stays the library constant, so the retention dovetail
    profile is untouched (§5: travel/length is a tunable, the profile is spec).

    ``snap_notches`` selects the locking detent:
    - True  -> ``SnapInSlotCutter``: the library slot channel + the two seat
      round-head cutters + the side-triangle snap notches (a detent that clicks
      the head in place). The robust connection.
    - False -> the SAME library slot channel + the SAME two seat round-head
      cutters, with the detent triangles OMITTED — i.e. the snap cutter minus
      its notches (assembled here from the library ``SlotCutter`` +
      ``RoundHeadCutter`` exactly as ``SnapInSlotCutter`` does, using the
      library ``_HEAD_SPACING``). The lighter/looser connection: the head still
      seats and the dovetail lip still retains it, but nothing clicks it home.
    """
    class _Slot(Slot):
        def __init__(self, **kwargs):
            kwargs["length"] = slot_travel
            super().__init__(**kwargs)

    class _SlotCutter(SlotCutter):
        def __init__(self, **kwargs):
            kwargs["slot"] = _Slot
            super().__init__(**kwargs)

    if snap_notches:
        return SnapInSlotCutter(slot_cutter=_SlotCutter, rotation=(90, 0, 0))
    # No-notch: replicate SnapInSlotCutter's slot-channel + seat assembly with
    # the detent triangle step dropped. Same alignment (CENTER, MAX, MIN) and
    # the same two seat round heads at the library head spacing, so the seat,
    # aperture and retention profile are identical — only the notches are gone.
    with BuildPart() as cutter:
        _SlotCutter(align=(Align.CENTER, Align.MAX, Align.MIN))
        with Locations((0, 0, 0), (0, -_HEAD_SPACING, 0)):
            RoundHeadCutter()
    return Rot(90, 0, 0) * cutter.part


def _plate_geometry(
    r_in: float, slot_count: int, slot_travel: float, plate_margin: float
) -> tuple[float, float, float, float, int]:
    """Derived back-plate dimensions: (width, plate_h, mount_y, z_seat, n_slots).

    The plate front face touches the collar's inner radius (``-r_in``) so it
    fuses through the full collar wall; the mount face sits one panel
    thickness further out (-Y), standing proud of the collar. The head seat
    is placed near the BOTTOM so the slide opening reaches (and cuts through)
    the plate's bottom edge — the holder lowers straight down onto the wall
    head, which enters at the bottom aperture and rides up to the seat.

    §3 material efficiency: the plate is the SLOT ENVELOPE + margin, centred
    behind the cup — NOT stretched to the cup's width or height. Width, height
    and seat are functions of the MOUNT tunables (slot_count, slot_travel,
    plate_margin) ALONE, independent of d and h.
    """
    n_slots = slot_count
    width = _min_plate_width(n_slots, plate_margin)
    plate_h = _plate_height(slot_travel, plate_margin)
    mount_y = -r_in - PANEL_THICKNESS
    # Seat sits slot_travel above the opening mouth; place it so the mouth pokes
    # _SLOT_BOTTOM_OVERSHOOT below the plate bottom (z=0), cutting an aperture
    # through the bottom edge. The entry is always at the bottom, so the seat is
    # a fixed height (slot_travel - overshoot) up.
    z_seat = slot_travel - _SLOT_BOTTOM_OVERSHOOT
    return width, plate_h, mount_y, z_seat, n_slots


def _back_plate_solid(
    r_in: float, slot_count: int, slot_travel: float, plate_margin: float
) -> Part:
    """The plain (un-pocketed) back-plate box behind the collar."""
    width, plate_h, mount_y, _z_seat, _n = _plate_geometry(
        r_in, slot_count, slot_travel, plate_margin
    )
    return Pos(0, mount_y, 0) * Box(
        width, PANEL_THICKNESS, plate_h,
        align=(Align.CENTER, Align.MIN, Align.MIN),
    )


def _treat_edges(
    part: Part,
    wall: float,
    r_in: float,
    r_out: float,
    h: float,
    slot_count: int,
    slot_travel: float,
    plate_margin: float,
) -> Part:
    """Fillet/chamfer the user-exposed, non-functional edges (design-guidelines
    §1, §2). Runs on the fused body BEFORE the slot pockets are carved, so it
    never touches the library cutter profile (the spec). Functional edges stay
    sharp: the mount face, the bore, and the slots (carved after).

    - Bed-contact edges (the z=0 print face): 45° chamfer (BED_CHAMFER) —
      elephant-foot relief. NEVER a fillet on a downward edge (§1: a bottom
      fillet is a shallow overhang that prints as a curl).
    - Plate outer vertical + top edges and the collar's top rims: fillet
      (EDGE_FILLET, clamped so opposing fillets on a thin wall can't collide).

    Each category is best-effort with a chamfer fallback (§2: if a fillet fails
    in OCP, fall back rather than ship a hard edge); a per-category flag lets a
    test confirm what was applied.
    """
    _w, plate_h, mount_y, _zs, _n = _plate_geometry(
        r_in, slot_count, slot_travel, plate_margin
    )
    plate_half_w = _w / 2.0

    # 1) Bed-contact chamfer: every edge lying on the z=0 build-plate face.
    bed = part.edges().filter_by_position(Axis.Z, -0.05, 0.05)
    if bed:
        part = part.chamfer(BED_CHAMFER, None, bed)

    # 2) Plate outer VERTICAL edges (the four Z-parallel side edges at
    #    x = +/- plate_half_w). Thick 6.4 mm plate -> a full EDGE_FILLET fits.
    verticals = [
        e for e in part.edges().filter_by(Axis.Z)
        if abs(abs(e.center().X) - plate_half_w) < 0.5
        and e.center().Y < -r_in + 0.5           # behind the collar (plate sides)
    ]
    if verticals:
        try:
            part = part.fillet(EDGE_FILLET, verticals)
        except Exception:
            part = part.chamfer(BED_CHAMFER, None, verticals)

    # 3) Plate top edges (z=plate_h): fillet the exposed back + side top edges
    #    (thick plate takes a full fillet). EXCLUDE the front top edge, which
    #    is buried in the collar junction — filleting an edge embedded in
    #    another body aborts OCP for thick walls / tall collars; that joint is
    #    treated by the §4 web + junction fillet instead.
    ptops = [
        e for e in part.edges().filter_by_position(Axis.Z, plate_h - 0.05, plate_h + 0.05)
        if e.center().Y < -r_in - 0.1
    ]
    if ptops:
        try:
            part = part.fillet(EDGE_FILLET, ptops)
        except Exception:
            part = part.chamfer(BED_CHAMFER, None, ptops)

    # 4) Collar top rim (z=h): a 45° CHAMFER on the OUTER rim (radius ~ r_out)
    #    a hand meets. The collar is a thin annular wall, so a fillet that rolls
    #    both inner+outer overruns the wall and aborts OCP; a single-sided outer
    #    fillet still fails on tall collars. A chamfer on the outer rim is
    #    robust across the whole param range and is an upward edge (not a
    #    forbidden downward fillet). The inner bore lip stays sharp (functional
    #    — the can slides through it).
    ctops = [
        e for e in part.edges().filter_by_position(Axis.Z, h - 0.05, h + 0.05)
        if math.hypot(e.center().X, e.center().Y) > r_in + wall / 2.0
    ]
    if ctops:
        try:
            part = part.chamfer(BED_CHAMFER, None, ctops)
        except Exception:
            pass
    return part


def slot_cutters(
    r_in: float, slot_count: int, slot_travel: float, plate_margin: float,
    snap_notches: bool,
) -> list[Part]:
    """The library Multiconnect slot cutters, positioned on the back plate.

    Each is ``_slot_cutter(slot_travel, snap_notches)`` (100% library geometry
    — the library slot channel + seat, snap notches on/off) at rotation
    (90, 0, 0), anchored at the pocket BACK (``mount_y + POCKET_DEPTH``):
    the (90, 0, 0) spin lays the dovetail taper along -Y with its WIDE
    (retention) end toward -Y and points the slide opening at -Z (the plate
    BOTTOM); width -> X. Anchoring the wide end at the pocket back puts the
    NARROW lip at the -Y mount face and the wide flange deep inside, so a
    seated round head's wide pad sits BEHIND the narrow lip and cannot pull
    straight off the wall (bug pst-p07j, print-verified: the pocket was
    previously carved INVERTED — ``Rot(0, 180, 0) * SnapInSlotCutter(
    rotation=(-90, 0, 0))`` put the wide end at the open surface and the
    narrow end inside, so nothing retained the head). The holder lowers DOWN
    onto wall-mounted round heads: each head enters the aperture at the
    plate's bottom edge and rides up to the seat, where (with snap_notches)
    the side notches lock it. ``slot_count`` slots at the library 28 mm pitch.
    """
    _w, _ph, mount_y, z_seat, n_slots = _plate_geometry(
        r_in, slot_count, slot_travel, plate_margin
    )
    cutter = _slot_cutter(slot_travel, snap_notches)
    return [
        Pos(x, mount_y + POCKET_DEPTH, z_seat) * cutter
        for x in _slot_x_positions(n_slots)
    ]


def holder(
    d: float,
    h: float,
    wall: float = 2.4,
    opening_deg: float = 90.0,
    floor_thickness: float = FLOOR_DEFAULT,
    slot_count: int = SLOT_COUNT_MIN,
    slot_travel: float = SLOT_TRAVEL_DEFAULT,
    snap_notches: bool = True,
    plate_margin: float = PLATE_MARGIN_DEFAULT,
) -> Part:
    """Build the C-ring cylinder holder.

    Args:
        d: cylinder (can/bottle) diameter, mm. Range [30, 120].
        h: collar height (how much of the cylinder is held), mm.
        wall: collar wall thickness, mm. Range [1.6, 4].
        opening_deg: opening arc of the C-ring, degrees. Range [60, 120],
            i.e. the collar always wraps at least 240 degrees.
        floor_thickness: solid base closing the collar bottom so an item
            rests on it instead of dropping through the bore, mm. Range
            [1.6, 10]. The front opening stays open above the floor.
        slot_count: number of Multiconnect slots at the fixed 28 mm pitch,
            centred. Range [1, 3]. More slots = more bearing surface and
            anti-rotation; the plate width derives from it.
        slot_travel: slide length (library SlotCutter length) the wall head
            rides from the bottom aperture to the seat, mm. Range
            [SLOT_TRAVEL_MIN, 45]. The plate height derives from it.
        snap_notches: use the library snap-in detent notches (True, robust) or
            the plain slot channel + seat (False, lighter/looser connection).
        plate_margin: solid material around the slot envelope, mm. Range [2, 6].
    """
    _validate(
        d, h, wall, opening_deg, floor_thickness, slot_count, slot_travel, plate_margin
    )

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
        # The floor (fused below) re-closes the opening's bottom, but the
        # full-height cut keeps the opening EDGES running off the bottom so
        # their fillet stays buildable (a fillet that terminated on the
        # floor top exported non-watertight for tall, thin footprints).
        extrude(amount=h + 1.0, dir=(0, 0, 1))
    wedge_part = wedge.part.moved(Location((0, 0, -1.0)))
    collar = annulus - wedge_part

    # Real BRep fillets on the opening's entry corners (AC: no sharp lips).
    # Radius scales down for thin walls so the full [WALL_MIN, WALL_MAX]
    # range stays buildable (see _lip_radius).
    lip_edges = _opening_lip_edges(collar, a1, a2)
    collar = collar.fillet(radius=_lip_radius(wall), edge_list=lip_edges)

    # --- Multiconnect slot back plate (100% library geometry) ------------
    # Fuse a solid plate to the collar's back and re-carve the bore so no
    # plate material intrudes into the cylinder space (the plate front face
    # sits at the inner radius; this trims the coincident sliver and keeps
    # the boolean off-coplanar with the bore).
    part = collar.fuse(_back_plate_solid(r_in, slot_count, slot_travel, plate_margin))
    bore = Cylinder(
        radius=r_in + BORE_CLEARANCE,
        height=h + 8.0,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    part = (part - bore).clean()

    # --- Floor (solid base) ----------------------------------------------
    # Close the collar bottom so an item rests on a solid base instead of
    # dropping through the bore (live-review bug, pst-t9wi). A full disc
    # across the C-ring footprint, inset FLOOR_EDGE_INSET under r_out (see
    # that constant): the front opening therefore stays open only ABOVE the
    # floor. Fused AFTER the bore re-carve so the base stays solid.
    if floor_thickness > 0.0:
        floor = Cylinder(
            radius=r_out - FLOOR_EDGE_INSET,
            height=floor_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        part = part.fuse(floor).clean()

    # Edge treatment (design-guidelines §1/§2) on the fused body BEFORE the
    # pockets are carved: fillet the user-facing outer/top edges, chamfer the
    # bed-contact edges. Doing it here keeps the library cutter profile (carved
    # next) untouched and the mount face / slot walls sharp.
    part = _treat_edges(
        part, wall, r_in, r_out, h, slot_count, slot_travel, plate_margin
    )

    # Carve the library slot pockets LAST, out of the unified body, so each
    # pocket is exactly the library cutter (nothing bespoke) and the floor
    # can never refill a pocket. Their opening cuts THROUGH the plate's
    # bottom edge (aperture) — the wall head's way in.
    for cutter in slot_cutters(
        r_in, slot_count, slot_travel, plate_margin, snap_notches
    ):
        part = part - cutter
    return part.clean()


def mount_fixtures(mount_type: str, values: dict) -> MountFixtures:
    """Library-geometry fixtures for the deterministic mount contracts.

    The mount contract suite (tests/mount_contracts.py) is model-agnostic:
    it verifies the aperture, orientation, seat clearance and entry travel
    from these fixtures alone. This hook supplies them for the C-ring holder
    — the same placed library ``SnapInSlotCutter`` pockets the build carves,
    plus the world pose of a seated library ``RoundHead`` at each slot.

    A seated head is ``seat_loc * RoundHead()`` — the exact pose the cutter's
    own internal round-head cutter occupies: ``Pos(x, mount_y + POCKET_DEPTH,
    z_seat) * Rot(90, 0, 0)``, matching ``slot_cutters``. The (90, 0, 0) spin
    lays the head's dovetail along -Y with its WIDE pad toward -Y; anchoring
    at the pocket back (``mount_y + POCKET_DEPTH``) seats that wide pad at the
    pocket back, BEHIND the narrow lip at the mount face (bug pst-p07j — the
    seated pose was previously the inverted ``Rot(0, 180, 0) * Rot(-90, 0, 0)``
    pose, wide pad at the open surface, which the depth-blind contracts could
    not catch; the retention/profile contracts now can).
    """
    if mount_type != "multiconnect-slot":
        raise ValueError(
            f"cylindrical holder has no {mount_type!r} mount "
            "(only 'multiconnect-slot')"
        )
    d = values["d"]
    wall = values.get("wall", 2.4)
    slot_count = int(values.get("slot_count", SLOT_COUNT_MIN))
    slot_travel = float(values.get("slot_travel", SLOT_TRAVEL_DEFAULT))
    plate_margin = float(values.get("plate_margin", PLATE_MARGIN_DEFAULT))
    snap_notches = bool(values.get("snap_notches", True))
    r_in = d / 2.0
    _w, _ph, mount_y, z_seat, n_slots = _plate_geometry(
        r_in, slot_count, slot_travel, plate_margin
    )
    seat_locs = [
        Pos(x, mount_y + POCKET_DEPTH, z_seat) * Rot(90, 0, 0)
        for x in _slot_x_positions(n_slots)
    ]
    return MountFixtures(
        cutters=slot_cutters(
            r_in, slot_count, slot_travel, plate_margin, snap_notches
        ),
        seat_locs=seat_locs,
        entry_axis=(0.0, 0.0, 1.0),
        face_normal=(0.0, -1.0, 0.0),
    )


def _params(d: float, h: float) -> tuple[Param, ...]:
    """Param spec for one holder instance — defaults carry THAT model's
    shape (spray can vs bottle), so each registered model keeps its own
    identity in the default export and in the manifest.

    The mount tunables (§5) default to reproduce today's geometry: the default
    ``slot_count`` is the value the historical width heuristic gives for this
    model's own default footprint, so the shipped preset is byte-identical."""
    default_slot_count = slot_count(2.0 * (d / 2.0 + 2.4))
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
        Param(
            name="floor_thickness",
            kind="number",
            default=FLOOR_DEFAULT,
            min=FLOOR_MIN,
            max=FLOOR_MAX,
            step=0.2,
            unit="mm",
            label="Floor thickness",
            group="geometry",
        ),
        # --- Mount tunables (design-guidelines §5) -----------------------
        Param(
            name="slot_count",
            kind="integer",
            default=default_slot_count,
            min=SLOT_COUNT_MIN,
            max=SLOT_COUNT_MAX,
            step=1,
            label="Slot count",
            group="mount",
        ),
        Param(
            name="slot_travel",
            kind="number",
            default=SLOT_TRAVEL_DEFAULT,
            min=SLOT_TRAVEL_MIN,
            max=SLOT_TRAVEL_MAX,
            step=1.0,
            unit="mm",
            label="Slot travel",
            group="mount",
        ),
        Param(
            name="snap_notches",
            kind="boolean",
            default=True,
            label="Snap notches",
            group="mount",
        ),
        Param(
            name="plate_margin",
            kind="number",
            default=PLATE_MARGIN_DEFAULT,
            min=PLATE_MARGIN_MIN,
            max=PLATE_MARGIN_MAX,
            step=0.5,
            unit="mm",
            label="Plate margin",
            group="mount",
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
            Preset(
                id="spray_can_light",
                label="Spray can — light mount (1 slot, no notch)",
                values={
                    "d": 66.0, "h": 60.0,
                    "slot_count": 1,
                    "slot_travel": SLOT_TRAVEL_MIN,
                    "snap_notches": False,
                    "plate_margin": PLATE_MARGIN_MIN,
                },
            ),
            Preset(
                id="spray_can_robust",
                label="Spray can — robust mount (2 slots, full travel)",
                values={
                    "d": 66.0, "h": 60.0,
                    "slot_count": 2,
                    "slot_travel": SLOT_TRAVEL_MAX,
                    "snap_notches": True,
                    "plate_margin": PLATE_MARGIN_DEFAULT,
                },
            ),
        ),
        title="Spray can holder",
        category_id="multiboard",
        mounts=("multiconnect-slot",),
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
            Preset(
                id="bottle_500ml_light",
                label="500ml bottle — light mount (1 slot, no notch)",
                values={
                    "d": 73.0, "h": 50.0,
                    "slot_count": 1,
                    "slot_travel": SLOT_TRAVEL_MIN,
                    "snap_notches": False,
                    "plate_margin": PLATE_MARGIN_MIN,
                },
            ),
            Preset(
                id="bottle_500ml_robust",
                label="500ml bottle — robust mount (2 slots, full travel)",
                values={
                    "d": 73.0, "h": 50.0,
                    "slot_count": 2,
                    "slot_travel": SLOT_TRAVEL_MAX,
                    "snap_notches": True,
                    "plate_margin": PLATE_MARGIN_DEFAULT,
                },
            ),
        ),
        title="500ml bottle holder",
        category_id="multiboard",
        mounts=("multiconnect-slot",),
    )
)
