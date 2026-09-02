"""Targeted checks for the C-ring cylinder holder (bead pst-98p4).

The registry-driven suite (test_toolchain.py) already covers build +
watertight + volume>0 for both presets; here we pin the AC specifics:
preset registration, parameter validation, wrap floor, filleted lips,
library-only mount, and clear can space.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trimesh  # noqa: E402
from build123d import (  # noqa: E402
    Align,
    Cylinder,
    GeomType,
    Pos,
    Rotation as Rot,
    export_stl,
)
from opengrid.constants import (  # noqa: E402
    MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS,
    MULTICONNECT_SLOT_LENGTH,
    OPEN_GRID_UNIT_SIZE,
)
from opengrid.multiconnect import RoundHead, SnapInSlotCutter  # noqa: E402

from holders.cylindrical import (  # noqa: E402
    D_MAX,
    D_MIN,
    FLOOR_DEFAULT,
    FLOOR_MAX,
    FLOOR_MIN,
    H_MAX,
    H_MIN,
    LIP_RADIUS,
    OPENING_MAX,
    OPENING_MIN,
    PLATE_MARGIN_DEFAULT,
    PLATE_MARGIN_MAX,
    PLATE_MARGIN_MIN,
    SLOT_COUNT_MAX,
    SLOT_COUNT_MIN,
    SLOT_PITCH,
    SLOT_TRAVEL_DEFAULT,
    SLOT_TRAVEL_MAX,
    SLOT_TRAVEL_MIN,
    TWO_SLOT_WIDTH_THRESHOLD,
    WALL_MAX,
    WALL_MIN,
    _min_plate_width,
    _plate_geometry,
    _plate_height,
    _lip_radius,
    _slot_x_positions,
    holder,
    slot_count,
    slot_cutters,
)
from holders.registry import all_models  # noqa: E402

# Default mount params (what ``holder(d, h)`` and the shipped presets use).
_DEF_MOUNT = dict(
    slot_count=SLOT_COUNT_MIN,
    slot_travel=SLOT_TRAVEL_DEFAULT,
    plate_margin=PLATE_MARGIN_DEFAULT,
)


def _model_names():
    return {s.name for s in all_models()}


def test_both_presets_registered():
    names = _model_names()
    assert "holder_spray_can" in names
    assert "holder_bottle_500ml" in names


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(d=D_MIN - 1, h=60),
        dict(d=D_MAX + 1, h=60),
        dict(d=66, h=H_MIN - 1),
        dict(d=66, h=H_MAX + 1),
        dict(d=66, h=60, wall=WALL_MIN - 0.1),
        dict(d=66, h=60, wall=WALL_MAX + 0.1),
        dict(d=66, h=60, opening_deg=OPENING_MIN - 1),
        dict(d=66, h=60, opening_deg=OPENING_MAX + 1),
        dict(d=66, h=60, floor_thickness=FLOOR_MIN - 0.1),
        dict(d=66, h=60, floor_thickness=FLOOR_MAX + 0.1),
        dict(d=66, h=60, slot_count=SLOT_COUNT_MIN - 1),
        dict(d=66, h=60, slot_count=SLOT_COUNT_MAX + 1),
        dict(d=66, h=60, slot_travel=SLOT_TRAVEL_MIN - 0.1),
        dict(d=66, h=60, slot_travel=SLOT_TRAVEL_MAX + 0.1),
        dict(d=66, h=60, plate_margin=PLATE_MARGIN_MIN - 0.1),
        dict(d=66, h=60, plate_margin=PLATE_MARGIN_MAX + 0.1),
    ],
)
def test_out_of_range_params_raise_valueerror(kwargs):
    with pytest.raises(ValueError) as exc:
        holder(**kwargs)
    assert "out of range" in str(exc.value)


def test_lip_radius_respects_thin_walls():
    """The lip fillet must never demand more than the wall can hold
    (regression: wall=WALL_MIN was advertised but unbuildable because the
    1.0 mm fillet consumed the full 1.6 mm wall)."""
    for wall in (WALL_MIN, 2.4, WALL_MAX):
        assert _lip_radius(wall) < wall / 2.0
        assert _lip_radius(wall) >= 0.05
    assert _lip_radius(2.4) == LIP_RADIUS  # nominal 1.0 mm where it fits
    assert _lip_radius(WALL_MAX) == LIP_RADIUS  # 4.0 mm wall keeps 1.0 mm


@pytest.mark.parametrize("d", [D_MIN, 66.0, D_MAX])
def test_min_wall_builds_and_is_watertight(d, tmp_path):
    """Regression: every in-range d must build at wall=WALL_MIN, and the
    exported STL must be watertight and single-body."""
    for h in (20.0, 60.0, 120.0):
        for opening_deg in (60.0, 90.0, 120.0):
            part = holder(d=d, h=h, wall=WALL_MIN, opening_deg=opening_deg)
            assert part.volume > 0
            stl = tmp_path / f"w{WALL_MIN}_d{d}_h{h}_o{opening_deg}.stl"
            export_stl(part, str(stl))
            mesh = trimesh.load_mesh(stl)
            assert mesh.is_watertight, f"d={d}, h={h}, opening={opening_deg}: not watertight"
            assert mesh.body_count == 1, f"d={d}, h={h}, opening={opening_deg}: {mesh.body_count} bodies"


def test_collar_wrap_is_real():
    """The solid must actually cover >= 240deg around the axis (AC)."""
    d, h = 66.0, 60.0
    part = holder(d, h)
    r_in, r_out = d / 2.0, d / 2.0 + 2.4
    # Sample at a radius inside the annulus (between bore r_in and r_out),
    # but inside the opening's cut faces so the 90deg gap reads as empty.
    r_mid = r_in + (r_out - r_in) * 0.5  # 34.2
    z_mid = h / 2.0
    solid_angles = 0
    step = 1.0
    for i in range(int(360 / step)):
        a = math.radians(i * step)
        pt = (r_mid * math.cos(a), r_mid * math.sin(a), z_mid)
        if part.is_inside(pt):
            solid_angles += 1
    coverage = solid_angles / 360.0
    # opening 90deg -> expect ~270deg of wrap; floor is the AC (>=240deg).
    assert coverage >= 240 / 360.0 - 0.02, f"wrap coverage too low: {coverage:.3f}"
    assert coverage <= 300 / 360.0 + 0.02, f"wrap coverage too high: {coverage:.3f}"
    # A point in the collar wall away from the opening must be solid.
    assert part.is_inside((r_mid, 0.0, z_mid)), "collar wall not solid"


def test_opening_lips_are_filleted():
    """The 4 sharp entry-corner edges must be gone, replaced by fillet faces."""
    d, h, wall = 66.0, 60.0, 2.4
    opening = 90.0
    part = holder(d, h, wall, opening)
    r_in = d / 2.0
    r_out = d / 2.0 + wall
    a1, a2 = 90.0 - opening / 2.0, 90.0 + opening / 2.0

    def near(angle, ref):
        diff = abs(angle - ref) % 360.0
        return min(diff, 360.0 - diff) < 2.0

    # 1) A real BRep fillet leaves cylindrical band faces at each lip,
    #    centered between the inner and outer radii (the un-filleted faces
    #    sit exactly at r_in / r_out).
    fillet_faces = [
        f
        for f in part.faces()
        if str(f.geom_type) == "GeomType.CYLINDER"
        and near(math.degrees(math.atan2(f.center().Y, f.center().X)) % 360.0, a1)
        and (r_in + 0.1 < math.hypot(f.center().X, f.center().Y) < r_out - 0.1)
    ]
    assert len(fillet_faces) >= 2, "expected fillet band faces on the opening lips"

    # 2) The flat radial cut face at each lip must be narrowed by the
    #    fillet (a 1mm fillet eats ~1mm off each of the two corners, so a
    #    2.4mm wall shrinks to well under half its un-filleted width).
    # The floor closes the opening's bottom, so the exposed radial cut face
    # now spans z in [floor_thickness, h] — height h - FLOOR_DEFAULT, not the
    # full h. Match that reduced extent.
    exposed_h = h - FLOOR_DEFAULT
    flat_faces = [
        f
        for f in part.faces()
        if str(f.geom_type) == "GeomType.PLANE"
        and near(math.degrees(math.atan2(f.center().Y, f.center().X)) % 360.0, a1)
        and f.bounding_box().size.Z > exposed_h - 1.0
    ]
    assert flat_faces, "expected the flat radial cut face at the opening lip"
    for face in flat_faces:
        unfilleted_width = wall  # full wall thickness, no fillet
        assert face.bounding_box().size.X < unfilleted_width / 2.0, (
            f"cut face not narrowed by fillet: width {face.bounding_box().size.X:.2f}"
        )


def test_slot_pitch_is_the_library_unit():
    """Slots are spaced at the library's 28 mm openGrid/Multiconnect unit."""
    assert SLOT_PITCH == OPEN_GRID_UNIT_SIZE


def test_slot_count_scales_with_width():
    """One slot for spray-can-class holders; two once wide/heavy. (Only used to
    pick each model's DEFAULT slot_count — the count is now an explicit tunable.)"""
    assert slot_count(TWO_SLOT_WIDTH_THRESHOLD - 1) == 1
    assert slot_count(TWO_SLOT_WIDTH_THRESHOLD) == 2
    # The shipped presets (~70-78 mm plates) default to single-slot.
    assert slot_count(2 * (66.0 / 2 + 2.4)) == 1
    assert slot_count(2 * (73.0 / 2 + 2.4)) == 1


def test_mount_tunables_appear_in_param_list():
    """AC 1: the four mount tunables appear in every mount model's Param list
    with the specified ranges/defaults."""
    expected = {
        "slot_count": (SLOT_COUNT_MIN, SLOT_COUNT_MAX, "integer"),
        "slot_travel": (SLOT_TRAVEL_MIN, SLOT_TRAVEL_MAX, "number"),
        "snap_notches": (None, None, "boolean"),
        "plate_margin": (PLATE_MARGIN_MIN, PLATE_MARGIN_MAX, "number"),
    }
    for spec in all_models():
        if not spec.mounts:
            continue
        by_name = {p.name: p for p in spec.params}
        for name, (lo, hi, kind) in expected.items():
            assert name in by_name, f"{spec.name} missing mount param {name}"
            p = by_name[name]
            assert p.kind == kind, f"{spec.name}.{name} kind {p.kind} != {kind}"
            assert p.group == "mount"
            if lo is not None:
                assert p.min == lo and p.max == hi
        # snap_notches default true; count default = today's width heuristic.
        assert by_name["snap_notches"].default is True
        assert by_name["slot_count"].default == SLOT_COUNT_MIN  # both presets 1-slot


def test_spec_constants_are_unchanged_and_unexposed():
    """AC 2: the spec (28 mm pitch, head/slot profile, clearances, pocket depth)
    is the library constant and is NOT a tunable."""
    import holders.cylindrical as cyl
    assert cyl.SLOT_PITCH == OPEN_GRID_UNIT_SIZE == 28
    assert cyl.POCKET_DEPTH == 4.15
    # slot_travel maps exactly onto the library SlotCutter LENGTH default.
    assert SLOT_TRAVEL_DEFAULT == MULTICONNECT_SLOT_LENGTH == 28
    # The exposed params are ONLY the mount robustness tunables — never the
    # pitch, profile, clearances or pocket depth.
    exposed = {p.name for s in all_models() if s.mounts for p in s.params}
    for spec_name in ("pitch", "pocket_depth", "slot_width", "head_radius",
                      "clearance", "taper"):
        assert spec_name not in exposed, f"spec constant {spec_name} must not be exposed"


@pytest.mark.parametrize("n", [1, 2, 3])
def test_slot_centres_are_multiples_of_pitch(n):
    """AC 2: slot centres stay at multiples of the 28 mm pitch for every count,
    symmetric about the plate centre."""
    xs = _slot_x_positions(n)
    assert len(xs) == n
    step = SLOT_PITCH / 2.0  # symmetric layout lands on half-pitch multiples
    for x in xs:
        k = x / step
        assert k == pytest.approx(round(k)), f"slot centre {x} not on the pitch grid"
    # Adjacent centres are exactly one pitch apart.
    for a, b in zip(xs, xs[1:]):
        assert b - a == pytest.approx(SLOT_PITCH)
    assert sum(xs) == pytest.approx(0.0), "slot centres not symmetric about 0"


def test_slot_travel_floor_is_derived_from_library_constants():
    """AC 3: the slot_travel minimum is derived from library constants (a seated
    RoundHead must sit at least one bottom-radius above the aperture so it enters
    fully and is captured WITHIN the plate), not guessed."""
    assert SLOT_TRAVEL_MIN == MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS + 2.0  # + overshoot

    # At the minimum travel a seated RoundHead's bottom sits at (≈) the plate
    # bottom z=0 — fully seated within the plate. Just below the floor it would
    # poke back out the bottom aperture (which is why the floor is where it is).
    def seated_head_bottom_z(travel):
        _w, _ph, mount_y, z_seat, _n = _plate_geometry(33.0, 1, travel, PLATE_MARGIN_DEFAULT)
        head = Pos(0.0, mount_y + 4.15, z_seat) * Rot(90, 0, 0) * RoundHead()
        return head.bounding_box().min.Z

    at_min = seated_head_bottom_z(SLOT_TRAVEL_MIN)
    below = seated_head_bottom_z(SLOT_TRAVEL_MIN - 2.0)
    assert at_min == pytest.approx(0.0, abs=0.2), (
        f"at the floor the seated head bottom should reach z=0, got {at_min:.2f}"
    )
    assert below < -1.0, "below the floor the seated head should poke out the aperture"


def test_head_enters_and_seats_at_minimum_travel():
    """AC 3: a head can actually enter at the bottom aperture and reach the seat
    at the minimum travel — the full mount contract holds there."""
    from tests import mount_contracts as MC
    for spec in all_models():
        if "multiconnect-slot" not in spec.mounts:
            continue
        vals = spec.resolve_values({"slot_travel": SLOT_TRAVEL_MIN})
        MC.verify(spec, "multiconnect-slot", vals)


def test_light_and_robust_presets_registered():
    """AC 4: each mount model ships a 'light' and a 'robust' preset."""
    for spec in all_models():
        if "multiconnect-slot" not in spec.mounts:
            continue
        ids = {p.id for p in spec.presets}
        light = next(p for p in spec.presets if p.id.endswith("_light"))
        robust = next(p for p in spec.presets if p.id.endswith("_robust"))
        # light: one slot, minimum travel, no notches.
        assert light.values["slot_count"] == 1
        assert light.values["slot_travel"] == SLOT_TRAVEL_MIN
        assert light.values["snap_notches"] is False
        # robust: 2-3 slots, full travel, notches.
        assert 2 <= robust.values["slot_count"] <= 3
        assert robust.values["slot_travel"] == SLOT_TRAVEL_MAX
        assert robust.values["snap_notches"] is True


def test_plate_is_sized_to_the_slot_envelope_not_the_cup():
    """§3 material efficiency (design-guidelines): the back plate is the SLOT
    ENVELOPE + margin, a pure function of the MOUNT tunables (slot_count,
    slot_travel, plate_margin) — independent of the cup diameter d and height h.
    ``_min_plate_width(n, margin)`` and ``_plate_height(travel, margin)`` fold
    the margin in on every side, so they ARE "envelope + 2*margin". v4 oversized
    the plate to max(collar_width, ...) x max(h, ...); this pins the fix."""
    # For a single-slot default mount: width/height are the slot envelope.
    w, ph, _my, _zs, n = _plate_geometry(33.0, **_DEF_MOUNT)
    assert n == 1
    assert w == pytest.approx(_min_plate_width(1, PLATE_MARGIN_DEFAULT), abs=1e-6)
    assert ph == pytest.approx(_plate_height(SLOT_TRAVEL_DEFAULT, PLATE_MARGIN_DEFAULT), abs=1e-6)

    # Sweep d widely at FIXED mount params: the plate size never moves — width,
    # height and seat depend only on the mount tunables, not on the cup.
    ref = _plate_geometry(15.0, **_DEF_MOUNT)
    for d in (30.0, 40.0, 66.0, 73.0, 90.0, 120.0):
        width, plate_h, _m, z_seat, n_slots = _plate_geometry(d / 2.0, **_DEF_MOUNT)
        assert (width, plate_h, z_seat, n_slots) == pytest.approx(
            (ref[0], ref[1], ref[3], ref[4])
        ), f"plate envelope moved with d={d}"

    # The plate DOES grow with the mount tunables (that is their whole job):
    wide = _plate_geometry(33.0, slot_count=3, slot_travel=SLOT_TRAVEL_MAX,
                           plate_margin=PLATE_MARGIN_MAX)
    assert wide[0] > w and wide[1] > ph, "mount tunables must resize the plate"

    # Both shipped presets default to single-slot -> identical plate footprint.
    p66 = _plate_geometry(33.0, **_DEF_MOUNT)[:2]
    p73 = _plate_geometry(36.5, **_DEF_MOUNT)[:2]
    assert p66 == p73, "the two presets must share one plate footprint (both 1-slot)"


def _slot_boxes(d, h):
    r_in = d / 2.0
    return [
        c.bounding_box()
        for c in slot_cutters(r_in, **_DEF_MOUNT, snap_notches=True)
    ]


def _in_slot(c, boxes, pad=0.7):
    return any(
        b.min.X - pad <= c.X <= b.max.X + pad
        and b.min.Y - pad <= c.Y <= b.max.Y + pad
        and b.min.Z - pad <= c.Z <= b.max.Z + pad
        for b in boxes
    )


@pytest.mark.parametrize("d,h", [(66.0, 60.0), (73.0, 50.0), (66.0, 40.0)])
def test_no_downward_facing_fillets(d, h):
    """§1/§6.2: NO downward-facing fillet. In the declared print pose (floor,
    z=0, on the bed; +Z up) a fillet on a bottom edge is a shallow overhang
    that prints as a curl. Every face steeper than 45° below horizontal must
    be either the flat bed itself (touching z=0), a 45° chamfer (PLANE/CONE),
    or the library slot profile (the spec, exempt) — never a rolled fillet
    surface. (The lone pre-existing 0.1 mm bore-top ledge at z=(h+8)/2 is a
    PLANE, not a fillet, and is flagged as an out-of-scope follow-up.)"""
    part = holder(d=d, h=h)
    boxes = _slot_boxes(d, h)
    cos45 = math.cos(math.radians(45))
    offenders = []
    for f in part.faces():
        n = f.normal_at(f.center())
        if n.Z < -cos45 - 1e-3:                      # steeper than 45° downward
            bb = f.bounding_box()
            c = f.center()
            if bb.min.Z < 0.1 or _in_slot(c, boxes):  # bed / chamfer / library
                continue
            # A fillet rolls a torus (curved edge) or a tangent cylinder; a
            # chamfer is a PLANE or a 45° CONE. Only planar faces (the bore
            # ledge) are tolerated here.
            if f.geom_type != GeomType.PLANE:
                offenders.append((str(f.geom_type), round(f.area, 1),
                                  (round(c.X, 1), round(c.Y, 1), round(c.Z, 1))))
    assert not offenders, f"downward-facing fillet surfaces present: {offenders}"


def test_bed_contact_edges_are_chamfered():
    """§1/§6.2: the z=0 build-plate face carries a 0.3-0.5 mm 45° chamfer
    (elephant-foot relief), not a fillet. Detect the chamfer faces that touch
    the bed and slope at ~45° (normal Z ≈ -sin45), and confirm the relief is
    within the 0.3-0.5 mm band."""
    from holders.cylindrical import BED_CHAMFER
    assert 0.3 <= BED_CHAMFER <= 0.5, "bed chamfer must be a 0.3-0.5 mm relief"
    part = holder(d=66.0, h=60.0)
    sin45 = math.sin(math.radians(45))
    bed_chamfers = [
        f for f in part.faces()
        if f.bounding_box().min.Z < 0.1
        and -sin45 - 0.15 < f.normal_at(f.center()).Z < -sin45 + 0.15
        and f.geom_type in (GeomType.PLANE, GeomType.CONE)
    ]
    assert len(bed_chamfers) >= 4, (
        f"expected the bottom outline chamfered; found {len(bed_chamfers)} "
        "bed-contact 45° faces"
    )


def test_outer_edges_are_softened():
    """§2/§6.4: user-exposed outer/top edges are treated (filleted/chamfered),
    not left sharp. Edge treatment only ever REMOVES material, so a treated
    build is strictly lighter than the same body with the treatment bypassed;
    a meaningful drop proves the outer verticals + top + rim were rounded (the
    plate side fillets alone remove tens of mm^3)."""
    import holders.cylindrical as cyl
    treated = holder(d=66.0, h=60.0).volume
    orig = cyl._treat_edges
    cyl._treat_edges = lambda part, *a, **k: part
    try:
        untreated = holder(d=66.0, h=60.0).volume
    finally:
        cyl._treat_edges = orig
    assert untreated - treated > 30.0, (
        f"edge treatment barely changed the body (untreated {untreated:.0f} - "
        f"treated {treated:.0f} = {untreated - treated:.1f} mm^3) — outer/top "
        "edges may not be getting rounded"
    )


def test_mount_is_the_library_slot():
    """The back-plate pockets must be exactly the opengrid library's
    SnapInSlotCutter - i.e. 100% library geometry, carved out of the plate
    (nothing bespoke). Rebuild the library cutter at the plate's slot
    positions and assert each region is fully absent from the part."""
    d, h = 66.0, 60.0
    r_in = d / 2.0
    part = holder(d, h)

    # Sanity: the module builds its cutters from the library type.
    assert isinstance(SnapInSlotCutter(), SnapInSlotCutter)

    cutters = slot_cutters(r_in, **_DEF_MOUNT, snap_notches=True)
    assert len(cutters) == SLOT_COUNT_MIN >= 1
    for cutter in cutters:
        assert cutter.volume > 100.0, "sanity: library cutter is a real pocket"
        present = part.intersect(cutter)
        present_vol = (
            sum(s.volume for s in present.solids()) if present is not None else 0.0
        )
        assert present_vol == pytest.approx(0.0, abs=1.0), (
            f"library slot pocket not carved: residual {present_vol:.2f}"
        )


# The slot APERTURE / ORIENTATION assertions that used to live here (the
# channel opens at the plate's bottom edge, not the top) migrated into the
# systematic mount-contract library — tests/mount_contracts.py, exercised by
# tests/test_mount_contracts.py over every mount-tagged model (bead pst-3eun).


def test_floor_closes_collar_bottom():
    """A solid floor closes the collar bottom so an item rests on it instead
    of dropping through the bore; the front opening stays open above it."""
    d, h = 66.0, 60.0
    r_in = d / 2.0
    part = holder(d, h)
    r_mid = r_in + 1.2  # inside the front wall/opening region

    # Bore centre: SOLID within the floor, EMPTY above it (item space).
    assert part.is_inside((0.0, 0.0, FLOOR_DEFAULT / 2.0)), "floor does not close the bore"
    assert not part.is_inside((0.0, 0.0, FLOOR_DEFAULT + 10.0)), "bore not open above floor"
    # The floor spans the full C-ring footprint: the FRONT (where the
    # opening is) is solid at floor level but open above it.
    assert part.is_inside((0.0, r_mid, FLOOR_DEFAULT / 2.0)), "floor gap at the front opening"
    assert not part.is_inside((0.0, r_mid, h / 2.0)), "front opening closed above the floor"


@pytest.mark.parametrize(
    ("d", "h"),
    [
        # Review round 2's failing set at h=20 (tile z-extent degeneracy),
        # plus the round-1 failing set at h=60, plus two known-good points.
        (30.0, 20.0), (40.0, 20.0), (50.0, 20.0), (56.0, 20.0),
        (85.0, 20.0), (90.0, 20.0), (112.0, 20.0), (66.0, 20.0),
        (30.0, 60.0), (50.0, 60.0), (85.0, 60.0), (90.0, 60.0),
        (112.0, 60.0), (66.0, 60.0),
    ],
)
def test_export_is_watertight_across_corner_cases(d, h, tmp_path):
    """Regression: the bore re-carve and the tile fuse must stay
    off-degenerate across the parameter space. Two coplanar-boolean
    defects left exported STLs non-watertight: the bore at exactly r_in
    (round 1, h=60 footprints) and the tile centered on the ring wall
    midplane (round 2, h=20 footprints)."""
    for wall in (WALL_MIN, 2.4):
        part = holder(d, h, wall=wall)
        stl = tmp_path / f"wt_d{d}_h{h}_w{wall}.stl"
        export_stl(part, str(stl))
        mesh = trimesh.load_mesh(stl)
        assert mesh.is_watertight, f"d={d}, h={h}, wall={wall}: not watertight"
        assert mesh.body_count == 1


def test_can_space_is_clear_above_floor():
    """The cylinder drops into the bore and rests ON the floor: zero
    interference with the collar walls above the floor. (Below the floor
    the base is intentionally solid — see test_floor_closes_collar_bottom.)"""
    d, h = 66.0, 60.0
    part = holder(d, h)
    # Can sits on the floor: from z=FLOOR_DEFAULT up to the collar top.
    can = Pos(0, 0, FLOOR_DEFAULT) * Cylinder(
        radius=d / 2.0,
        height=h - FLOOR_DEFAULT,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    overlap = part.intersect(can)
    overlap_vol = sum(s.volume for s in overlap.solids()) if overlap is not None else 0.0
    assert overlap_vol == pytest.approx(0.0, abs=1e-3)
