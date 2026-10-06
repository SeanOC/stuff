"""Regression checks for the Gridfinity shelf's published mount geometry."""
import sys
from pathlib import Path

import pytest
from build123d import Axis, Face, Solid, Wire

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holders import gridfinity_shelf as m
from tests.mount_contracts import verify_openconnect_slot
from tests.parity import (band_mask, bbox_parity, boundary_edges, load_reference,
                          over_cap_exclusion, rotate_to_print_frame, sample_surface,
                          surface_distance, volume_parity)


@pytest.mark.parametrize('values,thickness', [({}, 0.8), ({'shelf_back_offset': 1.55}, 2.4)],
                         ids=['default', 'sturdy-back'])
def test_rev11_backing_envelope(values, thickness):
    """Rev 11: exclude only the below-wedge slab plus the actual final bevel."""
    part = m.build(values)
    fx = m.mount_fixtures(m.MOUNT, values)
    _, width, depth, _, _, tilt, *_ = m.dimensions(values)
    envelope = m.backing_envelope(values)
    below = Solid.extrude(Face(Wire.make_polygon([
        (-width/2, 0, -10), (-width/2, depth, -10),
        (-width/2, depth, tilt), (-width/2, 0, 0)], close=True)), (width, 0, 0))
    bevel = m.before_bed_chamfer(values) - part
    for cutter in fx.cutters:
        back = cutter.bounding_box().max.Y
        for face in cutter.faces().filter_by(Axis.Y):
            if abs(face.center().Y-back) > 1e-7:
                continue
            probe = Solid.extrude(face, (0, thickness, 0))
            clipped = probe & envelope
            removed = probe-clipped
            lower = (probe & below) + (probe & bevel)
            assert removed.volume == pytest.approx(lower.volume, abs=0.01)
            inside_wedge = probe & m.uncut_wedge(values)
            assert (inside_wedge-part).volume == pytest.approx((probe & bevel).volume, abs=0.01)
            assert (removed-lower).volume < 1e-7
            assert (lower-removed).volume < 1e-7
    verify_openconnect_slot(part, fx, min_backing=thickness, backing_envelope=envelope)


@pytest.mark.parametrize('preset', ['default', 'magnets', 'wide'])
def test_rev10_reference_bed_band_coverage(preset):
    """Rev 10 measures the full band separately from distance exemptions."""
    root = Path(__file__).resolve().parents[2]
    mesh = load_reference(root/'assets'/'openConnect-gridfinity-shelf'/'mesh'/f'{preset}.stl')
    points, _ = sample_surface(mesh, n=100000, seed=1, sampler='uniform')
    excluded = band_mask(points, boundary_edges(
        mesh, normal_z=-0.99999, plane_tol=0.02, decimals=5), radius=0.5)
    print(f'BED_BAND | {preset} | {excluded.mean():.5%}')
    assert excluded.mean() <= 0.06, f'{preset}: band coverage {excluded.mean():.3%}, cap 6%'


@pytest.mark.parametrize('preset', m.SPEC.presets, ids=lambda p: p.id)
def test_envelope_and_print_orientation(preset):
    import math

    from build123d import Pos

    v, w, d, extra, deck, tilt, magnets, count, _, _ = m.dimensions(preset.values)
    assert w == 42*v['gridfinity_width_grids']+2*v['shelf_side_rim']
    assert d == v['shelf_back_offset']+.7+42*v['gridfinity_depth_grids']+v['shelf_front_rim']
    assert extra == (max(2.4, v['magnet_thickness']) if magnets else 2.4)
    assert deck == pytest.approx(extra+4.65+(.35 if magnets else 0))
    assert deck+tilt == 28
    assert count == int(w//28)
    frame = m.print_frame(v)
    for y in (0, d/2, d):
        assert (frame*Pos(0, y, tilt*y/d)).position.Z == pytest.approx(0, abs=1e-8)
    assert m.print_bottom_angle(v) == pytest.approx(math.degrees(math.atan(tilt/d)))


def test_published_backing_is_point_85_and_sturdy_is_2_point_4():
    from build123d import Align, Box, Pos
    for offset, expected in ((0, .85), (1.55, 2.4)):
        part = m.build({'shelf_back_offset': offset})
        probe = Pos(-28, 2.7, 10)*Box(.1, 3, .1,
                                   align=(Align.CENTER, Align.MIN, Align.CENTER))
        assert (part & probe).volume/.01 == pytest.approx(expected, abs=.05)


def test_socket_stack_and_clearance_saturation():
    from gridfinity import baseplate as gf
    for magnets in (False, True):
        cut = gf.socket_cutout(.2, magnets)
        bb = cut.bounding_box()
        assert bb.size.X == pytest.approx(42.2)
        assert bb.size.Z == pytest.approx(4.65+(.35 if magnets else 0)+gf.EPS)
        assert gf.socket_cutout(3, magnets).volume == pytest.approx(cut.volume)
    assert gf.magnet_offset(6.4) == 13
    assert len(gf.magnet_positions(2, 2, 'All')) == 16
    assert len(gf.magnet_positions(2, 2, 'Corners Only')) == 4
    assert gf.magnet_positions(2, 2, 'None') == []


def test_screws_obey_author_wall_guard():
    import math
    for diameter in (2, 3.3, 5):
        v = {'enable_screw_connections': True, 'connection_screw_diameter': diameter}
        _, w, d, extra, _, tilt, *_ = m.dimensions(v)
        expected = []
        for j in range(2):
            y = .7+(j+.5)*42
            z = tilt+extra-diameter/2-.8
            wall = (z-tilt*y/d)*math.cos(math.radians(m.print_bottom_angle(v)))-diameter/2
            if wall >= .8:
                expected.extend([(x, y, z) for x in (-w/2, w/2)])
        assert m.screw_positions(v) == expected
    assert m.screw_positions({}) == []


@pytest.mark.parametrize('rims', [
    {'shelf_side_rim': 4}, {'shelf_front_rim': 4},
    {'shelf_side_rim': 4, 'shelf_front_rim': 4},
])
def test_lips_require_matching_rims_and_leave_the_bin_pocket_open(rims):
    from build123d import Align, Box, Pos

    values = {**rims, 'shelf_rim_lip_height': 5}
    part = m.before_bed_chamfer(values)
    _, width, depth, *_ = m.dimensions(values)
    assert part.bounding_box().max.Z == pytest.approx(33)
    for point, occupied in [
        ((width/2-1, depth/2, 30), bool(rims.get('shelf_side_rim'))),
        ((0, depth-1, 30), bool(rims.get('shelf_front_rim'))),
    ]:
        assert part.is_inside(point) == occupied
    # A bin's central clearance stays open through the full lip height.
    probe = Pos(0, depth/2, 28)*Box(20, 20, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    intersection = part & probe
    assert intersection is None or intersection.volume < 1e-7


def test_lip_height_alone_adds_no_geometry():
    part = m.before_bed_chamfer({'shelf_rim_lip_height': 5})
    assert part.bounding_box().max.Z == pytest.approx(28)


@pytest.mark.parametrize('disabled', [{'magnet_diameter': 0}, {'magnet_thickness': 0}])
def test_zero_magnet_dimension_restores_plain_socket_and_windows(disabled):
    reference = m.before_bed_chamfer({})
    part = m.before_bed_chamfer({'baseplate_style': 'Magnet - All', **disabled})
    assert (reference-part).volume + (part-reference).volume < 1e-7


def test_corner_magnets_cut_only_the_four_outer_bosses():
    values = {'baseplate_style': 'Magnet - Corners Only'}
    part = m.before_bed_chamfer(values)
    # The four outer holes are empty; the material immediately beyond each
    # hole remains as its boss. Inner cell-corner positions are open windows.
    for x in (-34, 34):
        for y in (8.7, 76.7):
            assert not part.is_inside((x, y, 22))
            assert part.is_inside((x+3.7, y, 22))
    assert not part.is_inside((8, 34.7, 22))


@pytest.mark.parametrize('preset', [p for p in m.SPEC.presets if p.id != 'sturdy-back'], ids=lambda p: p.id)
def test_reference_parity(preset, tmp_path):
    """Finished surface/volume parity and pre-E1 bbox parity (E3/E4)."""
    import math

    from build123d import Pos, Rot

    from scripts.export import export_stl

    values = preset.values
    _, width, *_ = m.dimensions(values)
    frame = Pos(width/2, 0, 0)*Rot(0, 0, 180)
    before = m.before_bed_chamfer(values)
    part = frame*rotate_to_print_frame(m.chamfer_bed(before, values), m.SPEC, values)
    before = frame*rotate_to_print_frame(before, m.SPEC, values)
    before_box = before.bounding_box()
    # In the print frame the back wall is y = z*tan(tilt_angle).
    # E1 runs from (y,z)=(leg,0) to that wall at slope tan(bevel_angle),
    # so its new depth extremum is leg*t/(1+t), t=tan(tilt)*tan(bevel).
    # The 45.01 degree OCCT angle includes the documented fitting margin.
    t = math.tan(math.radians(m.print_bottom_angle(values)))*math.tan(math.radians(45.01))
    reduction = .3*t/(1+t)
    path = tmp_path/'port.stl'
    export_stl(part, path)
    port = load_reference(path)
    root = Path(__file__).resolve().parents[2]
    ref = load_reference(root/'assets'/'openConnect-gridfinity-shelf'/'mesh'/f'{preset.id}.stl')
    bbox_ok = bbox_parity(part, ref, tol=.05, mode='sorted', rtol=0,
                          pre_treatment=before, expected_reduction=(0, reduction, 0),
                          reduction_tol=.005)
    print(f"BBOX_ROW | {preset.id} | ref {ref.extents} | pre-E1 {tuple(before_box.size)} | "
          f"finished {port.extents} | analytic reduction {reduction:.6f} | {bbox_ok}")
    assert volume_parity(port, ref, rel=.01)
    assert port.is_watertight
    edges = boundary_edges(ref, normal_z=-0.99999, plane_tol=0.02, decimals=5)
    for direction, source, target in [('port->ref', port, ref), ('ref->port', ref, port)]:
        points, distances = surface_distance(source, target, n=40000, seed=1,
                                             sampler='uniform', vertices=False, signed=False)
        band = band_mask(points, edges, radius=0.5)
        coverage, fraction = over_cap_exclusion(distances, band, cap=.15)
        excluded = band & (distances > .15)
        assert coverage <= .06
        assert fraction <= .02
        assert distances[~excluded].max() <= .15
        print(f'PARITY_ROW | {preset.id} | {direction} | {ref.volume:.3f} | {port.volume:.3f} | '
              f'{distances[~excluded].max():.5f} | {coverage:.3%} | {fraction:.3%}')
    assert bbox_ok, (before_box.size, ref.extents)


CASES = [(p.id, p.values) for p in m.SPEC.presets] + [
    (f'{p.name}={value:g}', {p.name: value})
    for p in m.SPEC.params if p.kind in ('number', 'integer')
    for value in (p.min, p.max)
]


def published_back_wall_faces(part, values):
    """The two lower-taper probe faces adjoining the first socket row/back wall.

    Select the analytic socket plane, never faces by their measured thickness.
    Rev 14 retains these probes and adds the outer upper tapers below.
    """
    from gridfinity import baseplate as gf

    v, _, _, extra, _, tilt, magnets, *_ = m.dimensions(values)
    bottom_z = tilt + extra + (gf.CLEARANCE if magnets else 0)
    back_y = v['shelf_back_offset'] + .7 + gf.BOTTOM_INSET - v['gridfinity_socket_clearance']/2
    selected = []
    for face in part.faces():
        p = face.center()
        n = face.normal_at(p)
        bb = face.bounding_box()
        if (face.geom_type.name == 'PLANE' and abs(n.X) < 1e-6
                and abs(n.Y - 2**-.5) < 1e-6 and abs(n.Z - 2**-.5) < 1e-6
                and abs(p.Y+p.Z-back_y-bottom_z) < 1e-5
                and abs(bb.min.Z-bottom_z) < 1e-5
                and abs(bb.max.Z-bottom_z-gf.LOWER_TAPER) < 1e-5):
            selected.append(face)
    assert len(selected) == v['gridfinity_width_grids']
    return selected


def published_socket_wall_faces(part, values):
    """Rev 14 inventory by socket/exterior adjacency, never by wall thickness.

    The back-wall probes lie on the lower taper; the side/front probes lie
    on the upper taper. Identify the latter by their shared edge with the
    vertical socket riser and that edge's position on the outer socket row.
    OCCT represents some straight loft faces as BSplines, so surface type
    alone cannot identify the straight versus corner groups.
    """
    from gridfinity import baseplate as gf

    v, width, depth, extra, _, tilt, magnets, *_ = m.dimensions(values)
    upper_z = tilt + extra + (gf.CLEARANCE if magnets else 0) + gf.LOWER_TAPER + gf.RISER
    side = width/2 - v['shelf_side_rim'] - gf.MID_INSET + v['gridfinity_socket_clearance']/2
    front = depth - v['shelf_front_rim'] - gf.MID_INSET + v['gridfinity_socket_clearance']/2
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    groups = {'back': published_back_wall_faces(part, values), 'straight': [], 'corner': []}
    for face in part.faces():
        if abs(face.bounding_box().min.Z - upper_z) > 1e-5:
            continue
        for edge in face.edges():
            bb = edge.bounding_box()
            if abs(bb.min.Z-upper_z) > 1e-5 or abs(bb.max.Z-upper_z) > 1e-5:
                continue
            neighbours = [f for f in adjacency[edge] if f != face]
            if not any(abs(f.normal_at(edge.center()).Z) < 1e-5 for f in neighbours):
                continue  # upper taper must meet the vertical socket riser
            left = abs(bb.min.X + side) < 1e-5
            right = abs(bb.max.X - side) < 1e-5
            outer_front = abs(bb.max.Y - front) < 1e-5
            if edge.geom_type.name == 'LINE' and (left or right or outer_front):
                groups['straight'].append(face)
            elif edge.geom_type.name == 'CIRCLE' and (left or right) and outer_front:
                groups['corner'].append(face)
    assert len(groups['straight']) == 2*v['gridfinity_depth_grids'] + v['gridfinity_width_grids']
    assert len(groups['corner']) == 2
    return groups


def face_wall_measurements(part, values, faces):
    """Use the production wall sampler and solid classifier on each given face."""
    from tests import print_audit as a

    frame = m.print_frame(values)
    classified = a._ClassifiedPart(frame*part)
    boxes = a._cutter_boxes([frame*c for c in m.slot_fixtures(values).cutters])

    class FaceSubset:
        def __init__(self, face):
            self.face = frame*face

        def faces(self):
            return [self.face]

        def __getattr__(self, name):
            return getattr(classified, name)

    return [(tuple(face.center()), a._min_wall(FaceSubset(face), (0, 0, 1), boxes))
            for face in faces]


@pytest.mark.parametrize('clearance,expected', [
    (0, {'back': .905097, 'straight': .916043, 'corner': .916043}),
    (.1, {'back': .834378, 'straight': .889918, 'corner': .860975}),
    (.2, {'back': .791961, 'straight': .868733, 'corner': .811455}),
])
def test_rev14_published_socket_wall_thickness(clearance, expected):
    values = {'gridfinity_socket_clearance': clearance}
    part = m.build(values)
    groups = published_socket_wall_faces(part, values)
    assert {name: len(faces) for name, faces in groups.items()} == {
        'back': 2, 'straight': 6, 'corner': 2}
    for name, faces in groups.items():
        measurements = face_wall_measurements(part, values, faces)
        for _, thickness in measurements:
            assert thickness == pytest.approx(expected[name], abs=.01)
            if clearance == 0:
                assert thickness >= .9
        # Max-clearance pins match rays on the unmodified author SCAD.
        print(f'PUBLISHED_WALL_2 | clearance {clearance} | {name} | {measurements}')


def assert_no_other_thin_faces(part, values):
    groups = published_socket_wall_faces(part, values)
    approved = {face for faces in groups.values() for face in faces}
    assert len(approved) == 10
    other = [f for f in part.faces() if f not in approved]
    measurements = face_wall_measurements(part, values, other)
    thin = [(p, thickness) for p, thickness in measurements if thickness < .9-1e-6]
    assert not thin, f'faces outside published exception #2 below 0.9 mm: {thin}'
    return min(thickness for _, thickness in measurements)


def test_rev14_no_other_thin_faces_at_max_clearance():
    values = {'gridfinity_socket_clearance': .2}
    assert_no_other_thin_faces(m.build(values), values)


def edge_inventory(part, values):
    """Classify sharp seams by E2 reason; pin their positions in a golden.

    Bed bevels must be treated; any other unclassified sharp seam fails here.
    The recorded inventory catches new seams even in a permitted region.
    """
    import math

    from build123d import Pos

    from gridfinity import baseplate as gf
    v, width, depth, extra, _deck, tilt, magnets, *_ = m.dimensions(values)
    boxes = [c.bounding_box() for c in m.slot_fixtures(v).cutters]
    mode = 'Corners Only' if v['baseplate_style'] == 'Magnet - Corners Only' else 'All'
    origin_y = v['shelf_back_offset']+.7+v['gridfinity_depth_grids']*gf.PITCH/2
    bosses = [(x, y+origin_y) for x, y in gf.magnet_positions(
        v['gridfinity_width_grids'], v['gridfinity_depth_grids'], mode, v['magnet_diameter'])]
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    result = []
    for edge, faces in adjacency.items():
        if len(faces) == 1:  # periodic cylinder seams have one face twice
            assert edge.is_closed or faces[0].geom_type.name in ('CYLINDER', 'CONE')
            continue
        assert len(faces) == 2
        p = edge.center()
        normals = [f.normal_at(p) for f in faces]
        angle = math.degrees(math.acos(max(-1, min(1, normals[0].dot(normals[1])))))
        if angle < 89.99:
            continue
        # New concave junctions between E1 bevel faces are already treated,
        # not untreated author edges. Check their actual downward slope.
        frame = m.print_frame(v)
        bevel_faces = [f for f in faces if (frame*f).bounding_box().max.Z < 1]
        if any(abs(math.degrees(math.asin(max(-1, min(1,
               -(frame*Pos(*f.normal_at(p))).position.Z))))-44.99) < .02
               for f in bevel_faces):
            continue
        assert (m.print_frame(v)*Pos(*p)).position.Z > .05, ('untreated bed edge', tuple(p), angle)
        if any(b.min.X-1e-5 <= p.X <= b.max.X+1e-5 and
               b.min.Y-1e-5 <= p.Y <= b.max.Y+1e-5 and
               b.min.Z-1e-5 <= p.Z <= b.max.Z+1e-5 for b in boxes) or abs(p.Y) < 1e-5:
            reason = 'mount face'
        elif p.Z >= tilt+extra-1e-5:
            reason = 'gridfinity profile'
        elif abs(abs(p.X)-width/2) < 1e-5 or p.Y >= depth-4-1e-5:
            reason = 'author exterior'
        elif magnets and abs(p.Z-(tilt+extra-v['magnet_thickness'])) < 1e-5:
            reason = 'gridfinity profile'
        elif magnets and any(abs(math.hypot(p.X-x, p.Y-y)
                                 -(v['magnet_diameter']+gf.BOSS_EXTRA)/2) < 1e-5
                             for x, y in bosses):
            # Author's attachment-boss / through-window intersections.
            reason = 'gridfinity profile'
        else:
            raise AssertionError(('unclassified sharp edge', tuple(p), angle))
        result.append([reason, *(round(x, 3) for x in p), round(edge.length, 3), round(angle, 3)])
    return sorted(result)


@pytest.mark.audit
@pytest.mark.parametrize('name,values', CASES, ids=[name for name, _ in CASES])
def test_endpoint_audit_mount_and_edges(name, values):
    import json

    from tests.print_audit import audit

    try:
        part = m.build(values)
    except ValueError as exc:
        assert str(exc) in ('slot_horizontal offset leaves the back face',
                            'slot_vertical offset leaves the back face')
        assert set(values) <= {'slot_horizontal_offset', 'slot_vertical_offset'}
        print(f'AUDIT_ROW | {name} | — | — | — | rejected: {exc}')
        return
    fx = m.mount_fixtures(m.MOUNT, values)
    report = audit(part, cutters=fx.cutters, print_frame=m.print_frame(values))
    result = 'PASS'
    if name == 'gridfinity_socket_clearance=0.2':
        from dataclasses import replace

        assert report.min_wall_mm == pytest.approx(.792, abs=.01)
        other_min = assert_no_other_thin_faces(part, values)
        assert replace(report, min_wall_mm=other_min).ok, report.format()
        result = ('PASS (published exception #2 — socket upper-taper family (10 faces); '
                  'reference back/straight/corner 0.791961/0.868733/0.811455 mm)')
    else:
        assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
    assert len(part.solids()) == 1
    verify_openconnect_slot(part, fx, min_backing=2.4 if name == 'sturdy-back' else .8,
                            backing_envelope=fx.backing_envelope)
    inventory = edge_inventory(part, values)
    recorded = json.loads((Path(__file__).parent/'gridfinity_shelf_edges.json').read_text())
    assert inventory == recorded[name]
    worst = max((e[-1] for e in inventory), default=0)
    print(f'AUDIT_ROW | {name} | {report.min_wall_mm:.3f} | {report.max_overhang_deg:.3f} | '
          f'{worst:.3f} (E2 inventory) | {result} | volume {part.volume:.3f}')
