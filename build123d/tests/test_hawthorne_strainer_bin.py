"""Fit, scoop access, and production audit at every strainer-bin endpoint."""
import math

import pytest
from shapely.geometry import Point

from gridfinity import bin as gf
from holders import hawthorne_strainer_bin as m
from tests.audit_record import record
from tests.audit_tiers import audit_cases
from tests.print_audit import audit
from tests.test_gridfinity_capture_bin import bounded_exclusions


def exposed_edges(part):
    """Check every convex non-mating edge, including pocket/scoop crossings.

    The adjacent-face normals give the edge angle. A material probe between
    the normals identifies concave floor/wall junctions, not hand-contact lips.
    Only the unchanged library foot profile below Z=4.75 is functional.
    """
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    worst = 0
    for edge, faces in adjacency.items():
        assert len(faces) == 2
        if edge.bounding_box().max.Z <= gf.PROFILE_HEIGHT+1e-5:
            continue
        p = edge.position_at(.5)
        n1, n2 = [face.normal_at(p) for face in faces]
        angle = math.degrees(math.acos(max(-1, min(1, n1.dot(n2)))))
        if angle > 1 and part.is_inside(p+(n1-n2)*.01):
            continue  # concave junction
        worst = max(worst, angle)
        assert angle <= 45.01, (tuple(p), angle)
    return worst


def test_default_fit_and_tip_convention():
    v, floor, centre_y, envelope, offset, pocket, scoop = m.dimensions()
    assert envelope.bounds[1] == pytest.approx(centre_y-67)
    assert envelope.bounds[3] == pytest.approx(centre_y+93/2)
    assert pocket.area > envelope.area
    assert pocket.buffer(1e-6).covers(offset)
    cavity = 3*gf.PITCH-.5-2*v['wall_min']
    assert cavity-(pocket.bounds[3]-pocket.bounds[1]) >= 4
    assert pocket.bounds[1] == pytest.approx(-pocket.bounds[3])
    assert floor == 9 and scoop == 22


def test_stadium_reach_is_tip_not_arc_centre():
    for width in (10, 24, 40):
        shape = m.stadium(65, width, 0)
        assert shape.bounds[3] == pytest.approx(65)
        assert shape.bounds[0] == pytest.approx(-width/2)
        assert shape.covers(Point(0, 0))


def assert_shape(part, values):
    v, floor, _, _, offset, pocket, scoop = m.dimensions(values)
    assert part.is_valid and len(part.solids()) == 1
    bb = part.bounding_box()
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    assert bb.max.Z == pytest.approx(v['height_mm'], abs=1e-6)
    assert bb.size.X == pytest.approx(125.5)
    assert bb.size.Y == pytest.approx(v['depth_units']*42-.5)
    assert pocket.buffer(1e-6).covers(offset)
    # The planar coverage check above checks the entire clearance envelope.
    # Probe the actual solid at distributed boundary points and every axis
    # extreme. Checking hundreds of nearly identical arc vertices repeatedly
    # constructs OCCT solid classifiers without covering another feature.
    boundary = list(offset.exterior.coords)[:-1]
    probes = boundary[::max(1, len(boundary)//16)]
    for axis in (0, 1):
        probes.extend((min(boundary, key=lambda p: p[axis]),
                       max(boundary, key=lambda p: p[axis])))
    for x, y in probes:
        assert not part.is_inside((x, y, floor+.5))
        assert part.is_inside((x, y, floor-.5))
    front = -(v['depth_units']*42-.5)/2
    assert part.is_inside((0, front+.5, floor+.5))
    if scoop:
        assert part.is_inside((0, front+.5, floor+scoop-.5))
        assert not part.is_inside((0, front+.5, floor+scoop+.5))
    else:
        assert part.is_inside((0, front+.5, v['height_mm']-2))


CASES = [(p.id, p.values, None) for p in m.SPEC.presets]
for param in m.SPEC.params:
    for endpoint in (param.min, param.max):
        error = m.FIT_ERROR if (param.name, endpoint) in {
            ('coil_diameter', 110), ('handle_reach', 85),
        } else None
        if (param.name, endpoint) == ('handle_width', 40):
            # This endpoint previously depended on a sub-0.1 mm rim break.
            error = m.EDGE_ERROR
        CASES.append((f'{param.name}={endpoint}', {param.name: endpoint}, error))
CASES += [
    ('too-long-3x3', {'coil_diameter': 110, 'handle_reach': 85}, m.FIT_ERROR),
    ('long-3x4', {'coil_diameter': 110, 'handle_reach': 85, 'depth_units': 4}, None),
    ('clamped-scoop', {'height_mm': 35, 'floor_thickness': 1.2, 'scoop_height': 50}, None),
    ('wide-scoop-max-clearance', {'scoop_width': 70, 'clearance': 4, 'wall_min': 1.2}, None),
    ('narrow-scoop-wide-handle', {'scoop_width': 20, 'handle_width': 40}, None),
    ('long-max-clearance', {'coil_diameter': 110, 'handle_reach': 85, 'depth_units': 4,
                            'clearance': 4, 'floor_thickness': 1.2}, None),
    ('wide-ears', {'ear_reach': 65, 'ear_width': 24, 'ear_angle': 80}, m.FIT_ERROR),
]
# Cross-parameter regressions: the junction fallback may succeed, but these
# short pocket facets still cannot take the required 0.1 mm rim break.
CASES += [
    (f'narrow-scoop-coil-{coil}-depth-{depth}',
     {'coil_diameter': coil, 'depth_units': depth, 'scoop_width': 20}, m.EDGE_ERROR)
    for depth in (3, 4) for coil in (80, 100)
]
CASES += [
    (f'long-narrow-scoop-height-{height}',
     {'coil_diameter': 110, 'handle_reach': 85, 'depth_units': 4,
      'scoop_width': 20, 'scoop_height': height}, m.EDGE_ERROR)
    for height in (22, 50)
]
CASES += [
    (f'short-rim-facets-depth-{depth}',
     {'coil_diameter': 100, 'depth_units': depth, 'scoop_width': 30}, m.EDGE_ERROR)
    for depth in (3, 4)
]
CASES += [
    ('long-short-rim-facets', {'coil_diameter': 110, 'handle_reach': 85,
                             'depth_units': 4, 'scoop_width': 30}, m.EDGE_ERROR),
]
# All four min/max pairs, including the depth-4 fallback for large coils.
# The omitted pairs already have named cases above.
CASES += [
    (f'coil-scoop-pair-{coil}-{scoop}-depth-{depth}',
     {'coil_diameter': coil, 'scoop_width': scoop, 'depth_units': depth},
     m.FIT_ERROR if coil == 110 and depth == 3
     else m.EDGE_ERROR if coil == 80 and scoop == 70 else None)
    for depth in (3, 4) for coil in (80, 110) for scoop in (20, 70)
    if (coil, scoop) != (80, 20)
]
CASES += [
    (f'handle-scoop-pair-{handle}-{scoop}',
     {'handle_width': handle, 'scoop_width': scoop}, None)
    for handle in (20, 40) for scoop in (20, 70)
    if (handle, scoop) != (40, 20)
]


def test_unfinishable_edges_raise_named_error(monkeypatch):
    def failed_chamfer(*args, **kwargs):
        raise ValueError('OCC cannot chamfer this edge selection')

    monkeypatch.setattr(m, 'chamfer', failed_chamfer)
    with pytest.raises(m.EdgeTreatmentError, match=m.EDGE_ERROR):
        m.build()


@pytest.mark.audit
@pytest.mark.parametrize('name,values,error', CASES, ids=[c[0] for c in CASES])
@audit_cases(m.SPEC)
def test_endpoint_audit_edges_and_fit(name, values, error):
    if error:
        with pytest.raises(ValueError, match=f'^{error}$'):
            m.build(values)
        record(name, rejected=error)
        return
    part = m.build(values)
    assert_shape(part, values)
    worst = exposed_edges(part)
    raw = audit(part)
    report = audit(part, exclusions=bounded_exclusions(m.audit_exclusions(values)))
    assert report.ok, report.format()
    assert raw.longest_bridge_mm <= 10
    assert not raw.downward_fillets
    assert report.bed_chamfer == 'present'
    record(name, wall=report.min_wall_mm, overhang_raw=raw.max_overhang_deg,
           overhang=report.max_overhang_deg, bridge_raw=raw.longest_bridge_mm,
           bridge=report.longest_bridge_mm, worst_edge=worst, result='PASS', volume=part.volume)
