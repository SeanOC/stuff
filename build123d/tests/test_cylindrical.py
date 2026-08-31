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
from build123d import Align, Axis, Cylinder, Location, export_stl  # noqa: E402
from opengrid.base import Base  # noqa: E402
from opengrid.constants import OPEN_GRID_UNIT_SIZE  # noqa: E402

from holders.cylindrical import (  # noqa: E402
    D_MAX,
    D_MIN,
    H_MAX,
    H_MIN,
    LIP_RADIUS,
    OPENING_MAX,
    OPENING_MIN,
    WALL_MAX,
    WALL_MIN,
    _lip_radius,
    holder,
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


def test_unsupported_mount_raises_valueerror():
    with pytest.raises(ValueError) as exc:
        holder(66, 60, mount="multiconnect")
    assert "unsupported" in str(exc.value)


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
    # The back (0deg, -Y board side) must actually be solid (tile fused in).
    assert part.is_inside((r_mid, 0.0, z_mid)), "back of collar not solid"


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
    flat_faces = [
        f
        for f in part.faces()
        if str(f.geom_type) == "GeomType.PLANE"
        and near(math.degrees(math.atan2(f.center().Y, f.center().X)) % 360.0, a1)
        and f.bounding_box().size.Z > h - 1.0
    ]
    assert flat_faces, "expected the flat radial cut face at the opening lip"
    for face in flat_faces:
        unfilleted_width = wall  # full wall thickness, no fillet
        assert face.bounding_box().size.X < unfilleted_width / 2.0, (
            f"cut face not narrowed by fillet: width {face.bounding_box().size.X:.2f}"
        )


def test_mount_is_the_library_tile():
    """The back plate must be exactly the opengrid Base tile (minus the
    bore re-carve) - i.e. 100% library geometry, present in the part."""
    d, h = 66.0, 60.0
    r_in = d / 2.0
    r_out = r_in + 2.4
    part = holder(d, h)

    x_count = max(1, int(math.ceil(d / OPEN_GRID_UNIT_SIZE)))
    y_count = max(1, int(math.ceil(h / OPEN_GRID_UNIT_SIZE)))
    tile = Base(x_count=x_count, y_count=y_count)
    tile = tile.moved(Location((0, 0, 0), (1, 0, 0), 90))
    back_center_y = -(r_in + r_out) / 2.0
    tile = tile.moved(Location((0, back_center_y + 3.4, h / 2.0)))

    bore = Cylinder(
        radius=r_in, height=h + 8.0, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    expected = tile - bore
    present = part.intersect(tile)
    present_vol = sum(s.volume for s in present.solids()) if present is not None else 0.0
    assert present_vol == pytest.approx(expected.volume, abs=1.0), (
        f"library tile not fully present: {present_vol:.1f} vs {expected.volume:.1f}"
    )


def test_can_space_is_clear():
    """The cylinder must pass through the bore: zero interference."""
    d, h = 66.0, 60.0
    part = holder(d, h)
    can = Cylinder(radius=d / 2.0, height=h, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    overlap = part.intersect(can)
    overlap_vol = sum(s.volume for s in overlap.solids()) if overlap is not None else 0.0
    assert overlap_vol == pytest.approx(0.0, abs=1e-3)
