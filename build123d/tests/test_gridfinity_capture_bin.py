"""CB2 parity, socket, endpoint and narrowly inventoried print contracts."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build123d import Align, Box, Plane, Pos, section
from shapely.geometry import Point, box

from capture.encoding import encode, parse, validate
from gridfinity import baseplate
from gridfinity import bin as gf
from holders import gridfinity_capture_bin as m
from tests.parity import (
    bbox_parity,
    load_reference,
    mesh_from_part,
    surface_distance,
    volume_parity,
)
from tests.print_audit import audit

REFERENCE = Path(__file__).resolve().parents[2]/'assets/gridfinity-rebuilt/mesh/gr-bin-2x2x3-nolip.stl'


def test_pre_treatment_reference_parity(tmp_path):
    ref = load_reference(REFERENCE)
    part = gf.body(2, 2, 3, gf.REFERENCE_WALL)
    port = mesh_from_part(part, tmp_path/'port.stl', tolerance=.01, angular_tolerance=.1)
    assert ref.is_watertight and port.is_watertight
    assert bbox_parity(port, ref, tol=.05, mode='ordered', rtol=0)
    assert volume_parity(port, ref, rel=.01)
    for left, right in ((port, ref), (ref, port)):
        _, distances = surface_distance(left, right, n=10000, seed=17,
                                        sampler='uniform', vertices=True, signed=False)
        assert max(distances) <= .15


def test_reference_has_horizontal_underside_between_feet():
    """Exact reference evidence: 374 downward triangles, Z=4.75 mm."""
    ref = load_reference(REFERENCE)
    face_mask = ((ref.face_normals[:, 2] < -.999999)
                 & (np.abs(ref.triangles_center[:, 2]-gf.PROFILE_HEIGHT) < 1e-6))
    assert np.count_nonzero(face_mask) == 374
    assert ref.area_faces[face_mask].sum() == pytest.approx(119.5754275, abs=.001)
    # A probe in the 0.5 mm inter-foot gap meets the horizontal underside.
    hits, _, _ = ref.ray.intersects_location([[0, 10, 0]], [[0, 0, 1]])
    assert min(hits[:, 2]) == pytest.approx(4.75, abs=1e-6)


@pytest.mark.audit
def test_published_exception_1_is_the_only_raw_miss():
    """Keep the raw published 90° overhang and its short bridge visible."""
    report = audit(gf.body(2, 2, 3, gf.REFERENCE_WALL))
    assert report.max_overhang_deg == 90
    assert report.longest_bridge_mm <= 10
    assert report.min_wall_mm >= .9
    assert report.bed_chamfer == 'present'
    assert not report.downward_fillets
    assert report.failures() == ['overhang 90.0° > 45° (steeper than 45° from vertical)']


SMALL = encode(box(-7, -7, 7, 7).buffer(2, quad_segs=8).exterior.coords)
CASES = [(p.id, p.values, None) for p in m.SPEC.presets]
for param in m.SPEC.params:
    if param.kind not in ('integer', 'number'):
        continue
    for endpoint in (param.min, param.max):
        values = {param.name: endpoint}
        error = None
        if param.name in ('width_units', 'depth_units'):
            values['size_mode'] = 'manual'
        if param.name == 'width_units' and endpoint == 1:
            error = 'footprint + wall exceeds 6×6 cells'
        CASES.append((f'{param.name}={endpoint}', values, error))
CASES += [
    ('1x1', {'footprint': SMALL, 'size_mode': 'manual', 'width_units': 1, 'depth_units': 1}, None),
    ('6x6', {'size_mode': 'manual', 'width_units': 6, 'depth_units': 6}, None),
    ('tight-wall', {'footprint': encode(box(-16, -16, 16, 16).buffer(2, quad_segs=8).exterior.coords),
                    'clearance': 1.0, 'wall_min': 1.2}, None),
    ('combined', {'footprint': SMALL, 'clearance': 3, 'floor_thickness': 1.2,
                  'wall_min': 1.2, 'pocket_depth': 90}, None),
]


class BoundedExactSolid:
    """Reject points outside a solid's bounds before its costly native query.

    This is NOT a bbox exclusion: only the original BRep's is_inside can
    accept a point. The thin, many-holed underside otherwise spends minutes
    classifying unrelated wall/fillet samples far above or below its slab.
    """

    def __init__(self, solid):
        self.solid = solid
        self.bounds = solid.bounding_box()

    def is_inside(self, point, tolerance=1e-6):
        if any(p < lo-tolerance or p > hi+tolerance
               for p, lo, hi in zip(point, self.bounds.min, self.bounds.max)):
            return False
        return self.solid.is_inside(point, tolerance=tolerance)


def bounded_exclusions(regions):
    return [BoundedExactSolid(region) for region in regions]


def test_exact_exclusion_prefilter_preserves_native_membership():
    region, = gf.underside_exclusions(2, 2)
    bounded = BoundedExactSolid(region)
    for x, y in ((0, 10), (10, 10), (41.7, 41.7), (41.5, 0), (50, 0)):
        for z in (0, 4.7498, 4.7499, 4.75, 4.7501, 4.7502, 8):
            assert bounded.is_inside((x, y, z)) == region.is_inside((x, y, z))
    assert bounded.is_inside((0, 10, 4.75))
    assert not bounded.is_inside((10, 10, 4.75))  # inside bbox, in a foot hole


def edge_inventory(part, values):
    """Every edge is located by geometry; new/changed seams fail the golden.

    Foot profiles and base underside are functional. The rim must be tangent;
    pocket mouth chamfers are at most 45°, and the polygon's vertical seams
    are bounded by the round clearance offset. Floor seams are concave.
    """
    _, _, _, units, floor, pocket, _ = m.dimensions(values)
    top = units*gf.BASE_HEIGHT
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    rows = []
    for edge, faces in adjacency.items():
        assert len(faces) == 2
        p = edge.center()
        normals = [face.normal_at(p) for face in faces]
        angle = math.degrees(math.acos(max(-1, min(1, normals[0].dot(normals[1])))))
        bb = edge.bounding_box()
        if bb.max.Z <= gf.PROFILE_HEIGHT+1e-5:
            reason = 'functional-mating'
        elif pocket.boundary.distance(Point(p.X, p.Y)) <= m.POCKET_BREAK+.001:
            reason = 'pocket'
            if bb.min.Z > floor+1e-5:
                assert angle <= 45.01, ('sharp pocket mouth', tuple(p), angle)
            elif bb.max.Z > floor+1e-5:
                assert angle < 45.01, ('sharp vertical pocket seam', tuple(p), angle)
        else:
            reason = 'treated-rim'
            assert angle < .01, ('untreated exterior seam', tuple(p), angle)
            assert bb.max.Z <= top+1e-5
        rows.append([reason, *(round(x, 3) for x in p), round(edge.length, 3), round(angle, 3)])
    return sorted(rows)


def assert_containment(part, values):
    v, w, d, units, floor, pocket, offset = m.dimensions(values)
    assert len(pocket.exterior.coords) <= 257
    assert pocket.buffer(1e-7).covers(offset)
    outer = m.outer_polygon(w, d)
    assert outer.covers(pocket)
    assert outer.boundary.distance(pocket) >= v['wall_min']-1e-6
    assert floor >= gf.BASE_HEIGHT+v['floor_thickness']-1e-6
    assert units*7-floor == pytest.approx(v['pocket_depth'])
    # Check the actual BRep cavity at the floor, including every offset vertex.
    for x, y in offset.exterior.coords:
        toward = pocket.representative_point()
        dx, dy = toward.x-x, toward.y-y
        scale = .0001/math.hypot(dx, dy)
        assert not part.is_inside((x+dx*scale, y+dy*scale, floor+.001))
        assert part.is_inside((x+dx*scale, y+dy*scale, floor-.001))


# Dual-marked like test_cartridge_holder.test_endpoints: this sweep pushed the
# bd123 'audit' job (25 min budget) past its timeout on main at #167, so it
# runs in the sharded audit_full job instead (cradle-touching PRs, push to
# main, nightly) — pst-8vwop.
@pytest.mark.audit
@pytest.mark.audit_full
@pytest.mark.parametrize('name,values,error', CASES, ids=[c[0] for c in CASES])
def test_endpoint_audit_edges_and_containment(name, values, error):
    if error:
        with pytest.raises(ValueError, match=f'^{error.replace("+", r"\+")}$'):
            m.build(values)
        print(f'AUDIT_ROW | {name} | — | — | — | — | rejected: {error}')
        return
    part = m.build(values)
    assert part.is_valid and len(part.solids()) == 1
    assert_containment(part, values)
    edges = edge_inventory(part, values)
    recorded = json.loads((Path(__file__).parent/'gridfinity_capture_bin_edges.json').read_text())
    assert edges == recorded[name]
    raw = audit(part)
    report = audit(part, exclusions=bounded_exclusions(m.audit_exclusions(values)))
    assert report.ok, report.format()
    assert raw.longest_bridge_mm <= 10
    assert not raw.downward_fillets
    assert report.bed_chamfer == 'present'
    floor = m.dimensions(values)[4]
    worst = max(row[-1] for row in edges
                if row[0] == 'treated-rim' or (row[0] == 'pocket' and row[3] > floor+1e-5))
    print(f'AUDIT_ROW | {name} | {report.min_wall_mm:.3f} | '
          f'{raw.max_overhang_deg:.1f}/{report.max_overhang_deg:.1f} | '
          f'{raw.longest_bridge_mm:.2f}/{report.longest_bridge_mm:.2f} | '
          f'{worst:.3f} | PASS | volume {part.volume:.3f}')


@pytest.mark.parametrize('w,d', [(1, 1), (2, 2), (6, 6)])
def test_published_underside_family_area(w, d):
    part = gf.blank(w, d, 3)
    expected = ((w*42-.5)*(d*42-.5)-(4-math.pi)*gf.TOP_RADIUS**2
                -w*d*(gf.TOP_SIZE**2-(4-math.pi)*gf.TOP_RADIUS**2))
    family = [face for face in part.faces()
              if abs(face.bounding_box().min.Z-gf.PROFILE_HEIGHT) < 1e-6
              and abs(face.bounding_box().max.Z-gf.PROFILE_HEIGHT) < 1e-6
              and face.normal_at().Z < -.9999]
    assert sum(face.area for face in family) == pytest.approx(expected, rel=.005, abs=1e-6)
    envelopes = gf.underside_exclusions(w, d)
    assert sum(region.volume for region in envelopes)/.0002 == pytest.approx(expected, rel=.005, abs=1e-6)
    for face in family:
        assert sum((face & region).area for region in envelopes) == pytest.approx(face.area, rel=.005)


@pytest.mark.audit
def test_exception_rejects_new_ledge():
    part = gf.body(2, 2, 3, gf.REFERENCE_WALL)
    # A new flat ledge extends 2 mm outside the wall, 8 mm above the bed.
    ledge = Pos(40.75, -5, 8)*Box(3, 10, 2, align=(Align.MIN, Align.MIN, Align.MIN))
    report = audit(part+ledge, exclusions=bounded_exclusions(gf.underside_exclusions(2, 2)))
    assert any('overhang 90.0' in failure for failure in report.failures())


def test_socket_fit_below_plate_top():
    foot = gf.base(1, 1)
    below = Box(100, 100, baseplate.PROFILE_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    socket = baseplate.socket_cutout(0)
    assert ((foot & below)-socket).volume < 1e-6
    for z, gap in ((.05, .35), (1.5, .25), (4.6, .35)):
        foot_width = section(foot, Plane.XY.offset(z)).bounding_box().size.X
        socket_width = section(socket, Plane.XY.offset(z)).bounding_box().size.X
        assert (socket_width-foot_width)/2 == pytest.approx(gap, abs=.05)


def test_finished_rim_preserves_bbox_and_reduces_top_extent():
    before, finished = m.before_treatment(), m.build()
    for endpoint in ('min', 'max'):
        assert tuple(getattr(finished.bounding_box(), endpoint)) == pytest.approx(
            tuple(getattr(before.bounding_box(), endpoint)), abs=.005)
    top = finished.bounding_box().max.Z
    faces = [f for f in finished.faces() if f.bounding_box().min.Z >= top-1e-6]
    assert len(faces) == 1
    for axis in ('X', 'Y'):
        assert getattr(faces[0].bounding_box().size, axis) == pytest.approx(
            getattr(before.bounding_box().size, axis)-2*m.RIM_RADIUS, abs=.005)


@pytest.mark.parametrize('raw', ['garbage', 'v1;0,0;1,0;0,0', 'v1;0,0;10,10;0,10;10,0;0,0',
                                  'v1;0,0;'+'x'*16384])
def test_encoding_errors_are_reused_verbatim(raw):
    with pytest.raises(ValueError) as expected:
        validate(parse(raw))
    with pytest.raises(ValueError) as actual:
        m.build({'footprint': raw})
    assert str(actual.value) == str(expected.value)


def test_footprint_limit_and_overflow():
    param = next(p for p in m.SPEC.params if p.name == 'footprint')
    assert param.max_length == 16384
    assert m.SPEC.mounts == ()
    with pytest.raises(ValueError, match='footprint \\+ wall exceeds 6×6 cells'):
        m.build({'footprint': encode(box(-126, -126, 126, 126).exterior.coords)})


def test_dense_footprint_offset_is_contained_after_simplification():
    raw = encode(Point(0, 0).buffer(30, quad_segs=64).exterior.coords)
    values = {'footprint': raw}
    _, w, d, _, _, pocket, offset = m.dimensions(values)
    assert len(offset.exterior.coords) > 257
    assert len(pocket.exterior.coords) <= 257
    assert pocket.buffer(1e-7).covers(offset)
    for cw in range(1, 7):
        for cd in range(1, 7):
            if cw*cd >= w*d:
                continue
            outer = m.outer_polygon(cw, cd)
            assert not (outer.covers(pocket) and outer.boundary.distance(pocket) >= 1.6)
