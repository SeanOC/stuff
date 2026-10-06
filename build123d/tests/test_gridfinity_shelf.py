"""Regression checks for the Gridfinity shelf's published mount geometry."""
import sys
from pathlib import Path

import pytest
from build123d import Axis, Face, Solid, Wire

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holders import gridfinity_shelf as m
from tests.mount_contracts import verify_openconnect_slot


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


def reference_bed_band(mesh, points):
    """Rev 9 E3 band, from the reference underside's welded triangle boundary.

    Reference meshes already use the author's bed-down print frame. The
    0.02 mm plane tolerance includes only the source's EPS-sized bed drift;
    downward normals reject short side faces near the same plane.
    """
    import numpy as np

    bed = mesh.triangles[(mesh.face_normals[:, 2] < -0.99999)
                         & np.all(np.abs(mesh.triangles[:, :, 2]) < 0.02, axis=1)]
    counts = {}
    for triangle in np.round(bed, 5):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((tuple(triangle[i]), tuple(triangle[j]))))
            counts[edge] = counts.get(edge, 0) + 1
    edges = [edge for edge, count in counts.items() if count == 1]
    assert edges, 'reference must have a bed perimeter'
    distance = np.full(len(points), np.inf)
    for start, end in edges:
        a, b = np.asarray(start), np.asarray(end)
        ab = b - a
        t = np.clip(np.sum((points-a)*ab, axis=1)/(ab@ab), 0, 1)
        distance = np.minimum(distance, np.linalg.norm(points-(a+t[:, None]*ab), axis=1))
    return distance <= 0.5


@pytest.mark.parametrize('preset', ['default', 'magnets', 'wide'])
def test_rev10_reference_bed_band_coverage(preset):
    """Rev 10 measures the full band separately from distance exemptions."""
    import trimesh

    root = Path(__file__).resolve().parents[2]
    mesh = trimesh.load_mesh(root/'assets'/'openConnect-gridfinity-shelf'/'mesh'/f'{preset}.stl')
    points, _ = trimesh.sample.sample_surface(mesh, 100000, seed=1)
    excluded = reference_bed_band(mesh, points)
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

    import numpy as np
    import trimesh
    from build123d import Pos, Rot

    from scripts.export import export_stl

    values = preset.values
    _, width, *_ = m.dimensions(values)
    frame = Pos(width/2, 0, 0)*Rot(0, 0, 180)*m.print_frame(values)
    before = m.before_bed_chamfer(values)
    part = frame*m.chamfer_bed(before, values)
    before_box = (frame*before).bounding_box()
    after_box = part.bounding_box()
    # In the print frame the back wall is y = z*tan(tilt_angle).
    # E1 runs from (y,z)=(leg,0) to that wall at slope tan(bevel_angle),
    # so its new depth extremum is leg*t/(1+t), t=tan(tilt)*tan(bevel).
    # The 45.01 degree OCCT angle includes the documented fitting margin.
    t = math.tan(math.radians(m.print_bottom_angle(values)))*math.tan(math.radians(45.01))
    reduction = .3*t/(1+t)
    assert after_box.size.Y == pytest.approx(before_box.size.Y-reduction, abs=.005)
    assert after_box.size.X == pytest.approx(before_box.size.X, abs=.005)
    assert after_box.size.Z == pytest.approx(before_box.size.Z, abs=.005)
    path = tmp_path/'port.stl'
    export_stl(part, path)
    port = trimesh.load_mesh(path)
    root = Path(__file__).resolve().parents[2]
    ref = trimesh.load_mesh(root/'assets'/'openConnect-gridfinity-shelf'/'mesh'/f'{preset.id}.stl')
    bbox_ok = np.allclose(sorted(before_box.size), sorted(ref.extents), atol=.05, rtol=0)
    print(f"BBOX_ROW | {preset.id} | ref {ref.extents} | pre-E1 {tuple(before_box.size)} | "
          f"finished {port.extents} | analytic reduction {reduction:.6f} | {bbox_ok}")
    assert port.volume == pytest.approx(ref.volume, rel=.01)
    assert port.is_watertight
    for direction, source, target in [('port->ref', port, ref), ('ref->port', ref, port)]:
        points, _ = trimesh.sample.sample_surface(source, 40000, seed=1)
        _, distances, _ = trimesh.proximity.closest_point(target, points)
        band = reference_bed_band(ref, points)
        excluded = band & (distances > .15)
        assert band.mean() <= .06
        assert excluded.mean() <= .02
        assert distances[~excluded].max() <= .15
        print(f'PARITY_ROW | {preset.id} | {direction} | {ref.volume:.3f} | {port.volume:.3f} | '
              f'{distances[~excluded].max():.5f} | {band.mean():.3%} | {excluded.mean():.3%}')
    assert bbox_ok, (before_box.size, ref.extents)


CASES = [(p.id, p.values) for p in m.SPEC.presets] + [
    (f'{p.name}={value:g}', {p.name: value})
    for p in m.SPEC.params if p.kind in ('number', 'integer')
    for value in (p.min, p.max)
]


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
          f'{worst:.3f} (E2 inventory) | PASS | volume {part.volume:.3f}')
