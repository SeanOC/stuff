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
from build123d import Align, Cylinder, GeomType, Pos, export_stl  # noqa: E402
from opengrid.constants import OPEN_GRID_UNIT_SIZE  # noqa: E402
from opengrid.multiconnect import SnapInSlotCutter  # noqa: E402

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
    SLOT_PITCH,
    TWO_SLOT_WIDTH_THRESHOLD,
    WALL_MAX,
    WALL_MIN,
    MIN_PLATE_HEIGHT,
    _min_plate_width,
    _plate_geometry,
    _lip_radius,
    holder,
    slot_count,
    slot_cutters,
)
from holders.registry import all_models  # noqa: E402


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
    """One slot for spray-can-class holders; two once wide/heavy."""
    assert slot_count(TWO_SLOT_WIDTH_THRESHOLD - 1) == 1
    assert slot_count(TWO_SLOT_WIDTH_THRESHOLD) == 2
    # The shipped presets (~70-78 mm plates) are single-slot.
    assert slot_count(2 * (66.0 / 2 + 2.4)) == 1
    assert slot_count(2 * (73.0 / 2 + 2.4)) == 1


def test_plate_is_sized_to_the_slot_envelope_not_the_cup():
    """§3 material efficiency (design-guidelines): the back plate is the SLOT
    ENVELOPE + margin, a function of the slot COUNT alone — independent of the
    cup diameter d and height h. ``_min_plate_width(n)`` and
    ``MIN_PLATE_HEIGHT`` already fold _SLOT_EDGE_MARGIN in on every side, so
    they ARE "envelope + 2*margin". v4 oversized the plate to
    max(collar_width, ...) x max(h, ...); this pins the fix."""
    # For holder(d=66, h=40): a single-slot plate.
    w, ph, _my, _zs, n = _plate_geometry(33.0, 35.4, 40.0)
    assert n == 1
    assert w == pytest.approx(_min_plate_width(1), abs=0.5)
    assert ph == pytest.approx(MIN_PLATE_HEIGHT, abs=0.5)

    # Sweep d and h widely: for a FIXED slot count the plate size never moves,
    # and the height never moves at all. (Slot count itself still scales with
    # the cup — a deliberate load choice, promoted to a tunable in pst-c1qo.)
    seen: dict[int, tuple[float, float]] = {}
    for d in (30.0, 40.0, 66.0, 73.0, 90.0, 120.0):
        for h in (20.0, 40.0, 60.0, 90.0, 120.0):
            r_in = d / 2.0
            r_out = r_in + 2.4
            width, plate_h, _m, _z, n_slots = _plate_geometry(r_in, r_out, h)
            # height is independent of EVERYTHING
            assert plate_h == pytest.approx(MIN_PLATE_HEIGHT, abs=1e-6), (
                f"plate height moved with d={d}, h={h}"
            )
            # width is a pure function of the slot count
            assert width == pytest.approx(_min_plate_width(n_slots), abs=1e-6), (
                f"plate width not the slot envelope at d={d}, h={h}"
            )
            if n_slots in seen:
                assert seen[n_slots] == (width, plate_h)
            seen[n_slots] = (width, plate_h)

    # Both shipped presets are single-slot -> identical plate footprint.
    p66 = _plate_geometry(33.0, 35.4, 60.0)[:2]
    p73 = _plate_geometry(36.5, 38.9, 50.0)[:2]
    assert p66 == p73, "the two presets must share one plate footprint (both 1-slot)"


def _slot_boxes(d, h):
    r_in = d / 2.0
    r_out = r_in + 2.4
    return [c.bounding_box() for c in slot_cutters(r_in, r_out, h)]


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
    r_out = r_in + 2.4
    part = holder(d, h)

    # Sanity: the module builds its cutters from the library type.
    assert isinstance(SnapInSlotCutter(), SnapInSlotCutter)

    cutters = slot_cutters(r_in, r_out, h)
    assert len(cutters) == slot_count(2 * r_out) >= 1
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
