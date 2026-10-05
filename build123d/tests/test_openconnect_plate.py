"""OC2 author geometry, printable presets, exact border exception and edge audit."""
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import Axis, Compound, Pos, Rot

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from holders import openconnect_plate as m
from holders.registry import _validate_spec, resolve_mount_fixtures
from openconnect.constants import POCKET_DEPTH
from scripts.export import export_glb, export_stl
from tests.mount_contracts import CONTRACTS, _residual_vol
from tests.print_audit import audit
from tests.test_openconnect import ASSETS, TOL, _hausdorff, _stl


def author_frame(part, values):
    v, w, h, *_ = m.dimensions(values)
    thickness = (POCKET_DEPTH if v['slot_type'] == 'negslot' else
                 POCKET_DEPTH + v['extra_thickness'])
    return Pos(w/2, 0, thickness) * Rot(-90, 0, 0) * part


@pytest.mark.parametrize('name,values', [
    ('default', {}),
    ('asymmetric', {'lock': 'top-corners', 'position': 'edge-rows'}),
    ('one_slot', {'horizontal_size': 28, 'vertical_size': 28}),
])
def test_reference_equals_author(name, values, tmp_path):
    values = m.SPEC.resolve_values(dict(values, extra_thickness=0.5))
    mine = _stl(author_frame(m.build(values, reference=True), values), tmp_path/'ours.stl')
    path = ASSETS/'mesh'/f'openconnect_plate_{name}.stl'
    ref = trimesh.load_mesh(path)
    assert mine.is_watertight and ref.is_watertight
    assert mine.volume == pytest.approx(ref.volume, abs=0.15)
    np.testing.assert_allclose(mine.bounds, ref.bounds, atol=TOL)
    assert _hausdorff(mine, ref) < TOL
    assert _hausdorff(ref, mine) < TOL
    assert f'{hashlib.sha256(path.read_bytes()).hexdigest()}  mesh/{path.name}' in (ASSETS/'NOTICE').read_text()


def test_negative_is_exportable_author_grid_without_base(tmp_path):
    v = m.SPEC.resolve_values({'slot_type': 'negslot'})
    part = m.build(v)
    assert isinstance(part, Compound)
    assert len(part.solids()) == len(m.placements(v)) == 6
    assert _validate_spec(m.SPEC) is None
    assert resolve_mount_fixtures(m.SPEC, m.MOUNT, v) is None
    assert m.border_exclusions(v) == []
    for i, solid in enumerate(part.solids()):
        export_stl(solid, tmp_path/f'{i}.stl')
        assert trimesh.load_mesh(tmp_path/f'{i}.stl').is_watertight
    export_stl(part, tmp_path/'negative.stl')
    export_glb(part, tmp_path/'negative.glb')
    mesh = trimesh.load_mesh(tmp_path/'negative.stl')
    assert mesh.is_watertight and len(mesh.split()) == 6
    reference = ASSETS/'mesh'/'openconnect_plate_negative.stl'
    assert f'{hashlib.sha256(reference.read_bytes()).hexdigest()}  mesh/{reference.name}' in (ASSETS/'NOTICE').read_text()
    ref = trimesh.load_mesh(reference)
    mine = _stl(author_frame(part, v), tmp_path/'author-frame.stl')
    np.testing.assert_allclose(mine.bounds, ref.bounds, atol=TOL)
    assert mine.volume == pytest.approx(ref.volume, abs=0.15)
    assert _hausdorff(mine, ref) < TOL and _hausdorff(ref, mine) < TOL


@pytest.mark.parametrize('preset', m.SPEC.presets, ids=lambda p:p.id)
@pytest.mark.audit
def test_preset_print_audit(preset):
    v = m.SPEC.resolve_values(preset.values)
    if v['slot_type'] == 'negslot':
        pytest.skip('negative slot grid is a CAD subtraction tool, not a print (rev 3)')
    part = m.build(v)
    fx = m.mount_fixtures(m.MOUNT, v)
    report = audit(part, m.PRINT_ORIENTATION, cutters=fx.cutters, exclusions=m.border_exclusions(v))
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
    assert_finished_edges(part, v)
    CONTRACTS[m.MOUNT](part, fx)


@pytest.mark.parametrize('size,count', [(28, 1), (84, 3)])
@pytest.mark.parametrize('slide', ['up', 'down', 'left', 'right'])
@pytest.mark.parametrize('flip', [False, True])
def test_only_exact_edge_ramp_strips_are_excluded(size, count, slide, flip):
    v = m.SPEC.resolve_values({'horizontal_size': size, 'vertical_size': size,
                               'slide': slide, 'entryramp_flip': flip})
    exclusions = m.border_exclusions(v)
    assert len(exclusions) == count
    # Independently pinned integral of the author's ramp/channel end profile
    # at default clearances: area 54.703994949366 mm2 x 0.8 mm edge border.
    assert sum(s.volume for s in exclusions) == pytest.approx(count*43.763195959493, abs=1e-7)
    for strip in exclusions:
        bb = strip.bounding_box()
        assert bb.min.Y == pytest.approx(0, abs=1e-7)
        assert bb.max.Y == pytest.approx(2.7, abs=1e-7)
        if slide == 'up':
            assert (bb.min.Z, bb.max.Z) == pytest.approx((0, 0.8), abs=1e-7)
        elif slide == 'down':
            assert (bb.min.Z, bb.max.Z) == pytest.approx((size-.8, size), abs=1e-7)
        elif slide == 'left':
            assert (bb.min.X, bb.max.X) == pytest.approx((size/2-.8, size/2), abs=1e-7)
        else:
            assert (bb.min.X, bb.max.X) == pytest.approx((-size/2, -size/2+.8), abs=1e-7)
    v.update(horizontal_size=size+4, vertical_size=size+4)
    assert m.border_exclusions(v) == []


def test_grid_units_alignment_and_offset():
    assert m.placements({'size_unit':'grid', 'horizontal_size':3, 'vertical_size':2}) == m.placements({})
    v = {'horizontal_size':104, 'vertical_size':76, 'horizontal_alignment':'left',
         'vertical_alignment':'top', 'horizontal_offset':5, 'vertical_offset':-5}
    pts = m.placements(v)
    assert (pts[0].x, pts[0].z) == (-33, 57)
    assert (pts[-1].x, pts[-1].z) == (23, 29)


@pytest.mark.parametrize('values', [dict(horizontal_size=1), dict(vertical_size=281),
    dict(size_unit='grid', horizontal_size=1.5), dict(horizontal_offset=1),
    dict(horizontal_size=float('nan'))])
def test_invalid_envelopes_rejected(values):
    with pytest.raises(ValueError):
        m.build(values)


def assert_finished_edges(part, values):
    """Classify library mating edges; measure every other exterior dihedral.

    Returns the largest exposed-edge angle between adjacent face normals.
    Tangent joins are zero; a sharp right angle is 90 and fails.
    """
    fx = m.mount_fixtures(m.MOUNT, values)
    boxes = [c.bounding_box() for c in fx.cutters]
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    worst = 0.
    for edge, faces in adjacency.items():
        assert len(faces) == 2
        p = edge.center()
        if any(b.min.X-1e-6 <= p.X <= b.max.X+1e-6 and
               b.min.Y-1e-6 <= p.Y <= b.max.Y+1e-6 and
               b.min.Z-1e-6 <= p.Z <= b.max.Z+1e-6 for b in boxes):
            continue
        normals = [f.normal_at(p) for f in faces]
        angle = math.degrees(math.acos(max(-1., min(1., normals[0].dot(normals[1])))))
        worst = max(worst, angle)
        assert angle < 89.999, (tuple(p), angle)
    return worst


@pytest.mark.parametrize('style', ['chamfer', 'fillet'])
@pytest.mark.audit
def test_printable_corner_rounding(style):
    v = m.SPEC.resolve_values({'corner_rounding':style, 'corner_rounding_size':2})
    part = m.build(v)
    report = audit(part, m.PRINT_ORIENTATION, cutters=m._fixtures(v).cutters,
                   exclusions=m.border_exclusions(v))
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
    assert_finished_edges(part, v)
    CONTRACTS[m.MOUNT](part, m._fixtures(v))
    if style == 'fillet':
        assert all(f.center().Z > 28 for f in part.faces() if f.geom_type.name == 'CYLINDER'
                   and f.bounding_box().size.Y > 3)
        raw = m.plate_body(v, bed_chamfer=False)
        assert len([f for f in raw.faces() if f.geom_type.name == 'CYLINDER']) == 4


# Every numeric endpoint, plus both unit modes and documented geometry corners.
AUDIT_CASES = {
    'default': {},
    'one-tile': {'horizontal_size':28, 'vertical_size':28},
    'width-min-grid': {'size_unit':'grid', 'horizontal_size':1, 'vertical_size':2},
    'width-max-mm': {'horizontal_size':280},
    'height-min-grid': {'size_unit':'grid', 'horizontal_size':3, 'vertical_size':1},
    'height-max-mm': {'vertical_size':280},
    'backing-max': {'extra_thickness':6},
    'rounding-zero': {'corner_rounding':'fillet', 'corner_rounding_size':0},
    'rounding-max-fillet': {'corner_rounding':'fillet', 'corner_rounding_size':2},
    'rounding-max-chamfer': {'corner_rounding':'chamfer', 'corner_rounding_size':2},
    'offset-x-min': {'horizontal_size':104, 'horizontal_offset':-10},
    'offset-x-max': {'horizontal_size':104, 'horizontal_offset':10},
    'offset-z-min': {'vertical_size':76, 'vertical_offset':-10},
    'offset-z-max': {'vertical_size':76, 'vertical_offset':10},
    'clearance-side-min': {'side_clearance':0},
    'clearance-side-max': {'side_clearance':0.5},
    'clearance-depth-min': {'depth_clearance':0},
    'clearance-depth-max': {'depth_clearance':0.5},
    'clearance-max': {'side_clearance':0.5, 'depth_clearance':0.5},
    'slide-down': {'slide':'down'},
    'slide-left': {'slide':'left'},
    'slide-right': {'slide':'right'},
    'flip': {'entryramp_flip':True},
    'tile-rounded-max-clearance': {'horizontal_size':28, 'vertical_size':28,
        'corner_rounding':'fillet', 'corner_rounding_size':2,
        'side_clearance':0.5, 'depth_clearance':0.5},
}


@pytest.mark.audit
@pytest.mark.parametrize('name,overrides', AUDIT_CASES.items(), ids=AUDIT_CASES)
def test_printable_endpoints(name, overrides):
    v = m.SPEC.resolve_values(overrides)
    part = m.build(v)
    report = audit(part, m.PRINT_ORIENTATION, cutters=m._fixtures(v).cutters,
                   exclusions=m.border_exclusions(v))
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
    angle = assert_finished_edges(part, v)
    print(f'AUDIT_ROW | {name} | {report.min_wall_mm:.3f} | {report.max_overhang_deg:.3f} | {angle:.3f} | PASS |')


def test_maximum_clearance_retains_after_initial_free_play():
    from openconnect import head
    values = m.SPEC.resolve_values(AUDIT_CASES['tile-rounded-max-clearance'])
    part = m.build(values)
    seated = m._fixtures(values).seat_locs[0] * head()
    # Author tolerances permit play beyond the default contract's 0.5 mm probe.
    assert _residual_vol(part, Pos(0, -.5, 0) * seated) < 1e-6
    for pull in (1, 2):
        assert _residual_vol(part, Pos(0, -pull, 0) * seated) > 1


@pytest.mark.parametrize('slide,dimension', [('up','vertical_size'), ('down','vertical_size'),
                                          ('left','horizontal_size'), ('right','horizontal_size')])
def test_near_edge_offsets_cannot_hide_a_thin_border(slide, dimension):
    values = {'slide':slide, dimension:56.1}
    for size in (56.1, 56.2, 56.8):
        with pytest.raises(ValueError, match='on-ramp border'):
            m.build(dict(values, **{dimension:size}))
    with pytest.raises(ValueError, match='on-ramp border'):
        m.build(dict(values, **{dimension:57}, side_clearance=.5))
    # Exact author edge is the approved exception; a 1 mm size remainder
    # gives 1.3 mm border: 0.9 mm wall plus the 0.4 mm exterior edge relief.
    for size in (56,57):
        assert m.build(dict(values, **{dimension:size})).is_valid
