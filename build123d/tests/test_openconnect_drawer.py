# SPDX-License-Identifier: CC-BY-SA-4.0
"""Drawer source parity, fixture contracts and published print inventory."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
import trimesh

from drawer import shell


REFERENCES = Path(__file__).resolve().parents[2] / 'assets/openConnect-drawer/mesh'


@pytest.mark.parametrize('name,values', [
    ('shell-all-solid', dict(shell_bottom_wall_type='Solid')),
    ('shell-1x1x1-solid', dict(horizontal_grids=1, vertical_grids=1, depth_grids=1, shell_bottom_wall_type='Solid')),
    ('shell-top-slot-solid', dict(shell_slot_position='Top', shell_bottom_wall_type='Solid')),
])
def test_reference_body_envelope_and_cavity(name, values):
    """Check the box/cavity against actual source meshes away from cut features.

This is deliberately not finished-model parity: slots, magnets, stoppers
and bed treatment are still absent from the body primitive.
"""
    ref = trimesh.load_mesh(REFERENCES / f'{name}.stl')
    body = shell.source_body(values)
    assert body.is_valid
    assert len(body.solids()) == 1
    bb = body.bounding_box()
    assert np.array([tuple(bb.min), tuple(bb.max)]) == pytest.approx(ref.bounds, abs=1e-5)
    # Mid-depth sections avoid front magnet/stopper cuts and back pockets.
    # Probe both sides of the side walls and the non-slot bottom wall.
    w = values.get('horizontal_grids', 5)*28-4.8
    h = values.get('vertical_grids', 2)*28-4.8
    y = values.get('depth_grids', 5)*14
    points = [(0, 0, y), (w/2-.1, 0, y), (w/2+.1, 0, y),
              (-w/2+.1, 0, y), (-w/2-.1, 0, y),
              (0, -h/2+.1, y), (0, -h/2-.1, y)]
    expected = [False, False, True, False, True, False, True]
    assert ref.contains(points).tolist() == expected
    assert [body.is_inside(p) for p in points] == expected


@pytest.mark.parametrize('face', shell.SLOT_FACES)
def test_back_wall_lies_on_bed_for_every_mount_face(face):
    values = {'shell_slot_position': face}
    printed = shell.print_frame(values) * shell.body(values)
    assert printed.bounding_box().min.Z == pytest.approx(0, abs=1e-7)
    assert shell.print_frame(values) == shell.print_frame({'shell_slot_position': 'Back'})


@pytest.mark.parametrize('backing', [.6, .7])
def test_reject_backing_below_decided_shallow_contract(backing):
    with pytest.raises(ValueError, match='shell_to_slot_wall_thickness below 0.8 mm'):
        shell.body({'shell_to_slot_wall_thickness': backing})


def test_reject_empty_cavity_with_author_error():
    with pytest.raises(ValueError, match='shell inner dimensions must be greater than 0'):
        shell.body({'horizontal_grids': 1, 'shell_thickness': 14})


from holders import openconnect_drawer as m
from tests import print_audit as audit
from tests.openconnect_drawer_inventory import edge_inventory, source_contact_mask, wall_regions
from tests.parity import (band_mask, bbox_parity, boundary_edges, load_reference,
                          over_cap_exclusion, surface_distance, volume_parity)


@pytest.mark.parametrize('builder', [shell.build, m.build])
def test_reject_clearance_above_retention_cap(builder):
    parameter, cap = 'slot_side_clearance', m.SLOT_SIDE_CLEARANCE_MAX
    for value in (cap+.01, cap+.05):
        with pytest.raises(ValueError) as exc:
            builder({parameter: value})
        assert str(exc.value) == (
            f'{parameter} above {cap:g} mm leaves no openConnect head '
            'retention (openconnect-slot-shallow contract)')


@pytest.fixture(scope='module', params=[
    ('shell-default', {}),
    ('shell-top-slot', dict(shell_slot_position='Top')),
    ('shell-1x1x1', dict(horizontal_grids=1, vertical_grids=1, depth_grids=1)),
    ('shell-all-solid', dict(shell_bottom_wall_type='Solid')),
    ('shell-1x1x1-solid', dict(horizontal_grids=1, vertical_grids=1, depth_grids=1, shell_bottom_wall_type='Solid')),
    ('shell-top-slot-solid', dict(shell_slot_position='Top', shell_bottom_wall_type='Solid')),
    ('shell-top-honeycomb', dict(shell_top_wall_type='Honeycomb')),
    ('shell-side-honeycomb', dict(shell_side_wall_type='Honeycomb')),
    ('shell-all-honeycomb', dict(shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb')),
    ('shell-1x1x1-all-honeycomb', dict(horizontal_grids=1, vertical_grids=1, depth_grids=1,
                                       shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb')),
], ids=lambda case: case[0])
def reference_case(request, tmp_path_factory):
    from build123d import export_stl
    name, values = request.param
    values = {**values, "honeycomb_ceiling": "source"}
    before = shell.before_bed_chamfer(values)
    finished = shell.chamfer_bed(before, values)
    source = shell.AUTHOR_TO_MODEL.inverse()*finished
    path = tmp_path_factory.mktemp(name)/'port.stl'
    export_stl(source, str(path), tolerance=.01, angular_tolerance=.05)
    return name, values, before, finished, source, load_reference(path), load_reference(REFERENCES/f'{name}.stl')


@pytest.mark.audit
def test_reference_parity(reference_case):
    name, values, before, finished, source, port, ref = reference_case
    assert finished.is_valid and len(finished.solids()) == 1
    assert port.is_watertight and port.body_count == 1
    assert bbox_parity(source, ref, tol=.05, mode='ordered', rtol=0,
                       pre_treatment=shell.AUTHOR_TO_MODEL.inverse()*before,
                       expected_reduction=(0, 0, 0), reduction_tol=1e-5)
    assert volume_parity(port, ref, rel=.01)
    edges = boundary_edges(ref, normal_z=-.99999, plane_tol=.02, decimals=6)
    # Preserve the source STL's 1.9e-6 mm bed slivers when welding.
    # Rounding to five decimals collapses triangles and loses real boundaries.
    # Zero-length segments have no boundary length.
    edges = [(a, b) for a, b in edges if np.linalg.norm(np.asarray(a)-b) > 1e-8]
    classifier = audit._ClassifiedPart(source)
    for direction, a, b in [('port->ref', port, ref), ('ref->port', ref, port)]:
        points, distances = surface_distance(a, b, n=40000, seed=1, sampler='uniform',
                                             vertices=True, signed=False)
        contact = (source_contact_mask(points, values, classifier) if direction == 'ref->port'
                   else np.zeros(len(points), dtype=bool))
        # Same scoped contact-surface treatment as the snap precedent; no
        # physical exterior errors are removed. The three planes/families
        # are independently pinned below, separately from the bed band.
        contact_cap = {'shell-all-solid': .005, 'shell-1x1x1-solid': .01,
                       'shell-top-slot-solid': .12, 'shell-default': .005,
                       'shell-top-slot': .12, 'shell-1x1x1': .01,
                       'shell-top-honeycomb': .005, 'shell-side-honeycomb': .005,
                       'shell-all-honeycomb': .005, 'shell-1x1x1-all-honeycomb': .01}[name]
        assert contact.mean() < contact_cap
        points, distances = points[~contact], distances[~contact]
        band = band_mask(points, edges, radius=.5)
        coverage, excluded = over_cap_exclusion(distances, band, cap=.15)
        kept = ~(band & (distances > .15))
        assert coverage <= .06
        assert excluded <= .02
        assert distances[kept].max() <= .15
        print(f'PARITY | {name} | {direction} | {ref.volume:.6f} | {port.volume:.6f} | '
              f'{distances[kept].max():.6f} | band {coverage:.4%} | bevel {excluded:.4%} | contact {contact.mean():.4%}')


def test_source_contact_planes_are_opposite_csg_skins():
    """Source skins have opposite normals at the SAME physical points."""
    from trimesh.proximity import closest_point_naive
    cases = [
        ('shell-all-solid', (56, 28, 135.8), (0, 1, 0)),
        ('shell-all-solid', (56, 27.2, 135.8), (0, 1, 0)),
        ('shell-top-slot-solid', (0, 0, 140), (0, 0, 1)),
    ]
    for name, point, normal in cases:
        ref = load_reference(REFERENCES/f'{name}.stl')
        for sign in (-1, 1):
            faces = np.flatnonzero(ref.face_normals@np.asarray(normal)*sign > .999)
            subset = ref.submesh([faces], append=True)
            _, distances, _ = closest_point_naive(subset, [point])
            assert distances[0] < 1e-5, (name, point, sign, distances)


@pytest.mark.parametrize('values,slots,back_y,side_y,stop_y', [
    ({}, 10, -9.4, (-14, 14), 28),
    ({'slot_lock_distribution': 'Corners'}, 10, -9.4, (-14, 14), 28),
    ({'shell_slot_position': 'Top'}, 23, -8.8, (-13.4, 14.6), 29.2),
])
def test_feature_positions_and_seated_heads(values, slots, back_y, side_y, stop_y):
    from openconnect.slot import head
    part = m.build(values)
    fx = shell.slot_fixtures(values)
    assert len(fx.cutters) == slots
    assert np.asarray(shell.source_back_magnet_positions(values)) == pytest.approx(np.array([(-42, back_y, 0), (42, back_y, 0)]))
    side = shell.source_side_magnet_positions(values)
    assert len(side) == 4
    assert sorted({round(p[1], 6) for _, p in side}) == pytest.approx(side_y)
    assert {round(p[2], 5) for _, p in side} == {130.8}
    assert np.asarray(shell.source_stopper_positions(values)) == pytest.approx(np.array([(-56, stop_y, 134.6), (56, stop_y, 134.6)]))
    fixture = head()
    for pose in fx.seat_locs:
        assert (part & (pose*fixture)).volume < 1e-3


@pytest.mark.parametrize('wall,name,expected', [(1.6, 'shell-wall-1p6', .46),
                                               (2.8, 'shell-wall-2p8', 1.66),
                                               (4., 'shell-wall-4', 2.86)])
def test_published_wall_inventory(wall, name, expected):
    """Pin minimum, midpoint and maximum against independent source renders."""
    ref = load_reference(REFERENCES/f'{name}.stl')
    points, _, _ = ref.ray.intersects_location([[0, -14, 130.8]], [[-1, 0, 0]])
    hits = sorted(-p[0] for p in points)
    assert hits == pytest.approx([70-expected, 70], abs=1e-5)
    # The flange floor beside the shaft thins to .8 mm at the low endpoint.
    points, _, _ = ref.ray.intersects_location([[59.1, 30, 135.8]], [[0, -1, 0]])
    positive_y = sorted(p[1] for p in points if p[1] > 0)
    # The y=28 hit is the independently pinned coincident mouth skin.
    assert positive_y == pytest.approx([28-wall, 27.2, 28], abs=1e-5)
    # Normal-direction ray through the adjacent .4 mm flange/shaft round.
    normal = np.array([1., 1., 0.])/np.sqrt(2)
    point = np.array([53.2, 26.8, 135.8])+.4*normal
    hits, _, _ = ref.ray.intersects_location([point+.01*normal], [-normal])
    distances = sorted((point+.01*normal-hit)@normal for hit in hits)
    assert distances[1]-distances[0] == pytest.approx(
        (point[1]-(28-wall))*np.sqrt(2), abs=.002)
    v = {'shell_thickness': wall}
    part = shell.AUTHOR_TO_MODEL.inverse()*m.build(v)
    classified = audit._ClassifiedPart(part)
    floors = [f for f in part.faces() if f.bounding_box().size.X < 1e-5
              and abs(abs(f.center().X)-(70-expected)) < 1e-5]
    assert len(floors) == 4
    class Subset:
        def __init__(self, face): self.face = face
        def faces(self): return [self.face]
        def __getattr__(self, attr): return getattr(classified, attr)
    for face in floors:
        assert audit._min_wall(Subset(face), (0, 0, 1), []) == pytest.approx(expected, abs=.002)


def test_published_shallow_backing_reference():
    ref = load_reference(REFERENCES/'shell-backing-0p8.stl')
    hits, _, _ = ref.ray.intersects_location([[0, 18, 10]], [[0, 0, -1]])
    z = sorted(p[2] for p in hits)
    assert z == pytest.approx([2.7, 3.5], abs=1e-5)


def test_reference_ceiling_heights_and_short_spans():
    ref = load_reference(REFERENCES/'shell-all-solid.stl')
    # Independently measure each connected horizontal ceiling from the STL.
    for point, height, span in [((-42, -9.4, 1), 2.15, 6.4),
                                ((-68, -14, 132), 134.2, 2.251),
                                ((56, 27.6, 136), 137., 6.8)]:
        hits, _, _ = ref.ray.intersects_location([point], [[0, 0, 1]])
        assert min(p[2] for p in hits) == pytest.approx(height, abs=1e-5)
        mask = ((ref.face_normals[:, 2] < -.999)
                & (np.abs(ref.triangles_center[:, 2]-height) < 1e-5)
                & (np.linalg.norm(ref.triangles_center[:, :2]-point[:2], axis=1) < 7))
        vertices = ref.triangles[mask].reshape(-1, 3)
        measured = np.ptp(vertices, axis=0)[:2].max()
        assert measured == pytest.approx(span, abs=.002)
        assert measured < audit.MAX_BRIDGE_MM


def test_reference_exposed_edge_angles():
    from trimesh.triangles import closest_point
    ref = load_reference(REFERENCES/'shell-all-solid.stl')
    for point, angle in [((-70, -26, 70), 45), ((0, -28, 140), 90),
                         ((0, -25.6, 3.6), 90), ((0, -25.6, 140), 90)]:
        points = np.tile(point, (len(ref.faces), 1))
        near = np.linalg.norm(closest_point(ref.triangles, points)-points, axis=1) < 1e-5
        normals = ref.face_normals[near]
        measured = np.degrees(np.arccos(np.clip(normals@normals.T, -1, 1))).max()
        assert measured == pytest.approx(angle, abs=.001)


CASES = [(p.id, p.values) for p in m.SPEC.presets] + [
    (f'{p.name}={x:g}', {p.name: x}) for p in m.SPEC.params
    if p.kind in ('number', 'integer') for x in (p.min, p.max) if x is not None
] + [
    ('1x1x1', dict(horizontal_grids=1, vertical_grids=1, depth_grids=1)),
    ('honeycomb-strut-2', dict(honeycomb_strut_hyp=2)),
    ('all-honeycomb-strut-2', dict(honeycomb_strut_hyp=2, shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb')),
    ('honeycomb-strut-default', dict(honeycomb_strut_hyp=5)),
    ('all-honeycomb', dict(shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb')),
    *((f'honeycomb-{face}', dict(shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb', shell_slot_position=face)) for face in shell.SLOT_FACES[1:]),
    ('8x8x8', dict(horizontal_grids=8, vertical_grids=8, depth_grids=8)),
    ('thin-chamfer', dict(shell_thickness=1.6, shell_outer_chamfer=4)),
    ('max-clearance', dict(slot_side_clearance=m.SLOT_SIDE_CLEARANCE_MAX,
                           slot_depth_clearance=m.SLOT_DEPTH_CLEARANCE_MAX)),
    ('minimum-valid-backing', dict(shell_to_slot_wall_thickness=.8)),
    *((face, {'shell_slot_position': face}) for face in ('Bottom', 'Left', 'Right')),
]


@pytest.mark.audit
@pytest.mark.parametrize('name,values', [
    # Keep presets in the regular audit job and the parameter/corner sweep
    # in its sharded counterpart. With the honeycomb default, moving only
    # the six extra wall-type cases still exceeds the 35-minute CI budget.
    pytest.param(name, values, id=name,
                 marks=pytest.mark.audit_full
                 if name not in {p.id for p in m.SPEC.presets} else ())
    for name, values in CASES
])
def test_endpoint_audit_and_edges(name, values):
    if name == 'max-clearance':
        cap = values['slot_side_clearance']
        with pytest.raises(ValueError) as exc:
            m.build({**values, 'slot_side_clearance': cap+.05})
        assert str(exc.value) == (
            f'slot_side_clearance above {cap:g} mm leaves no openConnect head '
            'retention (openconnect-slot-shallow contract)')
    try:
        part = m.build(values)
    except ValueError as exc:
        assert str(exc) in (
            'slot_horizontal offset leaves the slot face',
            'slot_vertical offset leaves the slot face',
            'shell_to_slot_wall_thickness below 0.8 mm leaves less slot backing than the openconnect-slot-shallow contract',
        )
        print(f'AUDIT | {name} | named error: {exc}')
        return
    assert part.is_valid and len(part.solids()) == 1
    chords = shell.honeycomb_ceiling_chords(values)
    max_unroofed = max((chord for _, chord, roofed in chords if not roofed), default=0)
    assert max_unroofed <= audit.MAX_BRIDGE_MM
    fx = shell.slot_fixtures(values)
    raw = audit.audit(part, cutters=fx.cutters, print_frame=m.print_frame(values))
    assert raw.longest_bridge_mm <= audit.MAX_BRIDGE_MM
    report = audit.audit(part, cutters=fx.cutters, print_frame=m.print_frame(values),
                         exclusions=shell.published_ceiling_regions(values)+wall_regions(values))
    assert report.ok, report.format()
    # OCCT's fallback loft stores planar bevels as BSplines; the production
    # advisory only recognizes PLANEs. Independently measure its .3 mm slope.
    from build123d import Plane, section
    source = shell.AUTHOR_TO_MODEL.inverse()*part
    d = shell.dimensions(values)
    for z in (.001, .15, .301):
        box = section(source, section_by=Plane.XY.offset(z)).bounding_box()
        reduction = 2*max(0, .3-z)
        assert (box.size.X, box.size.Y) == pytest.approx((d.width-reduction, d.height-reduction), abs=.001)
    from tests.mount_contracts import verify_openconnect_slot
    before = shell.before_bed_chamfer(values)
    envelope = shell.body(values)-(before-part)
    verify_openconnect_slot(part, fx, min_backing=.8, backing_envelope=envelope)
    inventory, angle = edge_inventory(part, values)
    print(f'AUDIT | {name} | raw wall {raw.min_wall_mm:.3f} | raw overhang {raw.max_overhang_deg:.1f} | '
          f'bridge {raw.longest_bridge_mm:.2f} | analytic unroofed chord {max_unroofed:.6f} | exposed edge {angle:.3f} | '
          f'filtered wall {report.min_wall_mm:.3f} / overhang {report.max_overhang_deg:.1f} | mount PASS | PASS {inventory}')


def test_edge_inventory_rejects_unpublished_protrusion():
    from build123d import Box, Pos
    part = m.build({'horizontal_grids': 1, 'vertical_grids': 1, 'depth_grids': 1})
    # An added boss on the side has no source/interface reason for sharp edges.
    bad = part + shell.AUTHOR_TO_MODEL*(Pos(14, 0, 12)*Box(4, 4, 4))
    with pytest.raises(AssertionError, match='uninventoried edge'):
        edge_inventory(bad, {'horizontal_grids': 1, 'vertical_grids': 1, 'depth_grids': 1})


def test_published_exclusions_reject_new_thin_overhang():
    from build123d import Box, Pos
    v = dict(horizontal_grids=1, vertical_grids=1, depth_grids=1)
    part = m.build(v)+shell.AUTHOR_TO_MODEL*(Pos(16, 0, 12)*Box(6, 8, .6))
    report = audit.audit(part, cutters=shell.slot_fixtures(v).cutters,
                         print_frame=m.print_frame(v),
                         exclusions=shell.published_ceiling_regions(v)+wall_regions(v))
    assert not report.ok
    assert report.max_overhang_deg > 45
    assert report.min_wall_mm < .9


@pytest.mark.parametrize('face,entry_axis,face_normal,slots', [
    ('Back', (0, 0, 1), (0, -1, 0), 10),
    ('Left', (0, 0, 1), (1, 0, 0), 8),
    ('Right', (0, 0, 1), (-1, 0, 0), 8),
    ('Top', (-1, 0, 0), (0, 0, 1), 23),
    ('Bottom', (1, 0, 0), (0, 0, -1), 25),
])
def test_mount_entry_axis_in_model_frame(face, entry_axis, face_normal, slots):
    """Wall mounts lock by gravity with the drawer opening facing forward."""
    fx = shell.slot_fixtures({'shell_slot_position': face})
    assert fx.entry_axis == pytest.approx(entry_axis, abs=1e-6)
    assert fx.face_normal == pytest.approx(face_normal, abs=1e-6)
    assert len(fx.cutters) == len(fx.seat_locs) == len(fx.onramp_locs) == slots
    if face in ('Back', 'Left', 'Right'):
        for seat, onramp in zip(fx.seat_locs, fx.onramp_locs, strict=True):
            assert seat.position.Z - onramp.position.Z > 0
