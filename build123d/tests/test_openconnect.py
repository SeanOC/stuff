"""openConnect adapter: [C] provenance, author-render equality, mount contract.

The port is verified against meshes rendered from the author's own SCAD at
the pinned commit (assets/openConnect/NOTICE records how). openConnect
constants are [C] by design: they must NOT join test_reference_provenance's
_all_tags() or test_multibuild's _check_tag, which require [V].
"""
import hashlib
import re
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build123d import Align, Box, Plane, Pos, Mode, export_stl as fine_stl, section
from openconnect import POCKET_DEPTH, head, onramp_location, seat_location, slot_cutter
from openconnect import constants as c
from openconnect import demo_plate as demo
from openconnect.slot import slot_body
from scripts.export import export_stl
from tests.mount_contracts import CONTRACTS, _residual_vol
from tests.print_audit import audit

ASSETS = ROOT.parent / 'assets' / 'openConnect'
LOCATOR = re.compile(
    r'^https://github\.com/mitufy/opengrid-projects/blob/04e2277a71c5/'
    r'(?P<file>[\w/.-]+\.scad)#L(?P<line>\d+)$')
# Values computed from other constants; the cited line holds the arithmetic.
DERIVED = {'HEAD_DEPTH', 'MOUTH_WIDTH', 'POCKET_DEPTH', 'NUB_TAPER_SHIFT', 'ONRAMP_SHIFT'}
# Render-comparison bound. The spec allows side clearance + EPS (0.105 mm);
# the port is exact, so hold it to tessellation noise, 10x tighter.
TOL = 0.01
PLATE_THICKNESS = 3.2  # the render: 2.7 pocket + plate_extra_thickness 0.5


def test_constants_are_cited_to_the_pinned_upstream():
    assert set(c.PROVENANCE) >= {'HEAD_WIDTH', 'HEAD_HEIGHT', 'HEAD_DEPTH', 'MOUTH_WIDTH',
                                 'MOVE_DISTANCE', 'SIDE_CLEARANCE', 'DEPTH_CLEARANCE'}
    for name, p in c.PROVENANCE.items():
        assert p.status == 'C' and p.source, name
        assert getattr(c, name) == p.value, name
        m = LOCATOR.match(p.locator)
        assert m, f'{name}: {p.locator}'
        assert p.source == f"mitufy/opengrid-projects {m['file']}", name
        # The vendored copy is the pinned file, so the locator's line is checkable.
        line = (ASSETS / m['file']).read_text(encoding='utf-8').splitlines()[int(m['line']) - 1]
        if name not in DERIVED:
            assert f'{p.value:g}' in line, f'{name}={p.value:g} not on {m["file"]}:{m["line"]}: {line}'
    assert c.MOUTH_WIDTH == pytest.approx(14.2)
    assert c.HEAD_DEPTH == pytest.approx(2.6) and POCKET_DEPTH == pytest.approx(2.7)


def test_vendored_files_and_renders_match_notice():
    notice = (ASSETS / 'NOTICE').read_text(encoding='utf-8')
    assert '04e2277a71c54a832e38062953845a590fbd80ca' in notice and 'CC BY 4.0' in notice
    for rel in ('lib/opengrid_base.scad', 'lib/openconnect_lib.scad', 'lib/opengrid_threads_lib.scad',
                'openconnect_plate.scad', 'mesh/openconnect_plate_one_slot.stl',
                'mesh/openconnect_head.stl'):
        digest = hashlib.sha256((ASSETS / rel).read_bytes()).hexdigest()
        assert f'{digest}  {rel}' in notice, rel


def _hausdorff(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    """Largest distance from a surface sample of ``a`` (plus its vertices) to ``b``."""
    pts, _ = trimesh.sample.sample_surface_even(a, 40000, seed=1)
    _, dist, _ = trimesh.proximity.closest_point(b, np.vstack([pts, a.vertices]))
    return float(dist.max())


def _stl(part, path) -> trimesh.Trimesh:
    # Fine tessellation so chord error stays far below TOL.
    fine_stl(part, str(path), tolerance=0.001, angular_tolerance=0.05)
    return trimesh.load(path)


@pytest.fixture(scope='module')
def rendered_plate():
    return trimesh.load(ASSETS / 'mesh' / 'openconnect_plate_one_slot.stl')


def test_slot_equals_the_author_render(rendered_plate, tmp_path):
    ref = rendered_plate
    assert ref.is_watertight
    assert ref.bounds.ravel().tolist() == pytest.approx([0, 0, 0, 28, 28, PLATE_THICKNESS])
    # Rebuild the author's plate: the slot frame's mouth on the top face, the
    # SCAD's EPS excess past it, the tile centred on (14, 14).
    body = slot_body(excess=c.EPS)
    plate = (Box(28, 28, PLATE_THICKNESS, align=(Align.MIN,) * 3)
             - Pos(14, 14, PLATE_THICKNESS - POCKET_DEPTH) * body)
    mine = _stl(plate, tmp_path / 'plate.stl')
    assert mine.volume == pytest.approx(ref.volume, abs=0.05)
    assert _hausdorff(mine, ref) < TOL and _hausdorff(ref, mine) < TOL
    # The consumer cutter is the same body, rotated into the back-face frame.
    cutter = slot_cutter()
    assert cutter.volume == pytest.approx(slot_body().volume, rel=1e-9)


def test_head_equals_the_author_render(tmp_path):
    ref = trimesh.load(ASSETS / 'mesh' / 'openconnect_head.stl')
    part = head()
    assert part.is_valid and len(part.solids()) == 1
    mine = _stl(part, tmp_path / 'head.stl')
    assert mine.volume == pytest.approx(ref.volume, abs=0.05)
    assert _hausdorff(mine, ref) < TOL and _hausdorff(ref, mine) < TOL
    # Envelope 17 x 10.6 x 2.6, and the dovetail: flange 17 wide, neck = mouth.
    assert tuple(part.bounding_box().size) == pytest.approx((17, 10.6, 2.6), abs=1e-6)
    for z, width in ((0.3, c.HEAD_WIDTH), (2.3, c.MOUTH_WIDTH)):
        cut = section(part, section_by=Plane.XY.offset(z), mode=Mode.PRIVATE)
        assert cut.bounding_box().size.X == pytest.approx(width, abs=1e-6)
    widths = [section(part, section_by=Plane.XY.offset(z), mode=Mode.PRIVATE).bounding_box().size.X
              for z in np.linspace(0.05, 2.55, 26)]
    assert min(widths) == pytest.approx(c.MOUTH_WIDTH, abs=1e-6)


def test_head_fits_the_rendered_slot(rendered_plate, tmp_path):
    # Seated: flange c.DEPTH_CLEARANCE above the pocket floor, top flush.
    seated = _stl(Pos(14, 14, PLATE_THICKNESS - POCKET_DEPTH + c.DEPTH_CLEARANCE) * head(),
                  tmp_path / 'seated.stl')
    pts, _ = trimesh.sample.sample_surface_even(seated, 40000, seed=2)
    depth_into_plate = trimesh.proximity.signed_distance(rendered_plate, np.vstack([pts, seated.vertices]))
    assert depth_into_plate.max() < -0.05  # never inside material; tightest gap 0.1/sqrt(2)


def test_cutter_frame_and_options():
    cutter = slot_cutter()
    assert cutter.is_valid and len(cutter.solids()) == 1
    bb = cutter.bounding_box()
    assert bb.min.Y == pytest.approx(0, abs=1e-6) and bb.max.Y == pytest.approx(POCKET_DEPTH)
    assert -c.TILE_SIZE / 2 <= bb.min.X and bb.max.X <= c.TILE_SIZE / 2
    assert -c.TILE_SIZE / 2 <= bb.min.Z and bb.max.Z <= c.TILE_SIZE / 2
    # Seat end above the origin, on-ramp 10.6 below: the slot runs -13.2 .. +9.0.
    assert bb.max.Z == pytest.approx(9.0, abs=1e-6) and bb.min.Z == pytest.approx(-13.2, abs=1e-6)
    # snap=False drops the lock nub: the negative grows by exactly the nub.
    assert slot_cutter(snap=False).volume - cutter.volume == pytest.approx(1.417, abs=0.001)
    loose = slot_cutter(clearance=(0.2, 0.2))
    assert loose.bounding_box().max.Y == pytest.approx(2.8) and loose.volume > cutter.volume
    for bad in ((-0.1, 0.1), (0.1, 0.6)):
        with pytest.raises(ValueError):
            slot_cutter(clearance=bad)
    assert onramp_location(0, 0).position.Z == pytest.approx(-c.MOVE_DISTANCE)
    assert onramp_location(0, 0).position.X == pytest.approx(-2.2)


@pytest.fixture(scope='module')
def plate():
    return demo.build()


def test_demo_plate_contract_audit_and_volume(plate, tmp_path):
    assert plate.is_valid and len(plate.solids()) == 1
    assert tuple(plate.bounding_box().size) == pytest.approx((84, 5.5, 84))
    assert demo.THICKNESS - POCKET_DEPTH >= 2.4
    fx = demo.mount_fixtures(demo.MOUNT, {})
    assert tuple((loc.position.X, loc.position.Z) for loc in fx.seat_locs) == demo.SLOTS == (
        (-14, 28), (14, 28), (-14, 56), (14, 56))
    CONTRACTS[demo.MOUNT](plate, fx)
    export_stl(plate, tmp_path / 'demo.stl')
    assert trimesh.load(tmp_path / 'demo.stl').is_watertight
    report = audit(plate, demo.PRINT_ORIENTATION, cutters=fx.cutters)
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
    assert not audit(plate, demo.PRINT_ORIENTATION).ok
    # Webs between neighbouring slots and margins to the plate edge.
    boxes = [cut.bounding_box() for cut in fx.cutters]
    assert boxes[1].min.X - boxes[0].max.X == pytest.approx(6.4, abs=1e-6)
    assert boxes[2].min.Z - boxes[0].max.Z == pytest.approx(5.8, abs=1e-6)
    assert plate.volume == pytest.approx(34750.930, abs=0.001)


def test_demo_is_not_registered():
    from holders.registry import all_models
    assert all(spec.build.__module__ != demo.__name__ for spec in all_models())


@pytest.fixture(scope='module')
def single():
    """One slot at (0, 20) in a 28 x 5.5 x 40 plate: the defect baseline."""
    part = Box(28, 5.5, 40, align=(Align.CENTER, Align.MIN, Align.MIN)) - Pos(0, 0, 20) * slot_cutter()
    from holders.registry import MountFixtures
    fx = MountFixtures([Pos(0, 0, 20) * slot_cutter()], [seat_location(0, 20)],
                       onramp_locs=[onramp_location(0, 20)])
    return part, fx


@pytest.mark.parametrize('defect', ['none', 'sealed_onramp', 'blocked_channel', 'open_seat',
                                    'thin_backing', 'straight_entry'])
def test_contract_detects_broken_slots(single, defect):
    part, fx = single
    if defect == 'sealed_onramp':
        part = part + Pos(-2.2, 0.25, 9.4) * Box(20, 0.5, 13)
    elif defect == 'blocked_channel':
        part = part + Pos(0, 1.35, 14) * Box(20, 2.7, 0.5)
    elif defect == 'open_seat':
        # Remove the seat end (roof and its 45° chamfers) above Z=26.
        part = part - Pos(0, 1.35, 31) * Box(20, 2.7, 10)
    elif defect == 'thin_backing':
        # 1.3 mm left behind the pocket instead of 2.8.
        part = part - Pos(0, 4.75, 20) * Box(20, 1.5, 20)
    elif defect == 'straight_entry':
        # A head pushed in on the slot axis instead of at the -X on-ramp fouls.
        from holders.registry import MountFixtures
        fx = MountFixtures(fx.cutters, fx.seat_locs, onramp_locs=[Pos(0, 0, 9.4) * seat_location(0, 0)])
    if defect == 'none':
        CONTRACTS[demo.MOUNT](part, fx)
        return
    match = {'sealed_onramp': 'entry path blocked', 'blocked_channel': 'entry path blocked',
             'open_seat': 'open past the seat', 'thin_backing': 'backing',
             'straight_entry': 'entry path blocked'}[defect]
    with pytest.raises(AssertionError, match=match):
        CONTRACTS[demo.MOUNT](part, fx)
