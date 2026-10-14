"""Underware L / T / X junctions (pst-fsk8s.2): parity with the author's
renders, the planner rig's invariants, grip probes, named errors and the
endpoint print audit with an exposed-edge inventory.

References: assets/underware-opengrid/mesh/{l,t,x}.stl (mayor, BOSL2
b86a7584) and the worker variants listed in the NOTICE.
"""
from __future__ import annotations

import sys
from math import acos, degrees, hypot
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import Plane, mirror

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holders import underware_junctions as m
from tests import print_audit as pa
from scripts.export import export_stl
from tests.parity import load_reference, mesh_from_part, sample_surface
from underware import constants as c
from underware import junction as j
from underware.channel import cord_cutouts
from underware.grip import grip_flared_cut

from tests.test_underware import ASSETS, GRIP_PROBES

L, T, X = 'underware_l', 'underware_t', 'underware_x'


def flat(regions):
    return [r for family in regions.values() for r in family]


def build(name, values=None):
    return m.SPECS[name].build(values or {})


# --- parity ------------------------------------------------------------------

PARITY = {
    'l': (L, {}),
    't': (T, {}),
    'x': (X, {}),
    'l-mirror-r1-y2x3': (L, {'mirror_channel': True, 'added_radius': 1, 'length_y_units': 2,
                             'length_x_units': 3}),
    'l-y3-cutouts': (L, {'length_y_units': 3, 'number_of_cord_cutouts': 2}),
    't-b1l2r1': (T, {'width_left_units': 2}),
    't-b2l1r1': (T, {'width_bottom_units': 2}),
    't-b3l2r1': (T, {'width_bottom_units': 3, 'width_left_units': 2}),
    't-b4l2r1': (T, {'width_bottom_units': 4, 'width_left_units': 2}),
    't-s3-cutouts': (T, {'stem_length_units': 3, 'number_of_cord_cutouts': 2}),
    'x-w2-b2r1l1t3': (X, {'channel_width_units': 2, 'bottom_length_units': 2, 'top_length_units': 3}),
}
# Each corner is BOSL2 path_extrude2d of the section along a stub, a 90-point
# arc of centreline radius r and a stub; it sizes its mitre-cut and joint-fill
# cubes from the PATH bounds (miscellaneous.scad:121-123): s = sqrt(2)*(r +
# 0.81), so the section beyond s/2 from the centreline (or above z = s/2) is
# left as overlapping unmitred prisms. At added_radius 0 that leaves the L's
# outer wall hollow above z = 9.905 over two ~22 degree bands (winding number
# 0 inside the 2 mm wall, 333 mm3 of the 8.67 vs 9.00 cm3 pin spread; the
# 456fcd8 render and every added_radius >= 1 render carry the solid wall the
# port builds), and wide T corners' inside posts faceted by up to 0.03 mm.
HOLLOW_Z = 19.81/2
BAND_CAP = 0.15   # mm, surface distance allowed inside the unmitred band


def corner_axes(name, v):
    """(cx, cy, r, section width, quadrant x-sign, y-sign) of every corner, in
    the frame before the L mirror; the quadrant is where the arc sweeps."""
    if name == L:
        w = c.channel_width(v['channel_width_units'])
        return [(w/2, -w/2, v['added_radius']*c.GRID + w/2, w, -1, 1)]
    if name == T:
        return [(side*(wc/2) + dx, -wc/2 + dy, wc/2, wc, -side, 1)
                for side, wc, dx, dy in j.t_corner_placements(
                    v['width_bottom_units'], v['width_left_units'], v['width_right_units'])]
    w = c.channel_width(v['channel_width_units'])
    return [(sx*w/2, sy*w/2, w/2, w, -sx, -sy) for sx in (1, -1) for sy in (1, -1)]


def unmitred_band(points, name, values):
    """Points in some corner's sweep quadrant whose section coordinate lies
    beyond s/2 of the centreline, or above z = s/2."""
    v = m.SPECS[name].resolve_values(values)
    pts = points.copy()
    if name == L and v['mirror_channel']:
        pts[:, 0] = -pts[:, 0]
    band = np.zeros(len(pts), bool)
    for cx, cy, r, ws, qx, qy in corner_axes(name, v):
        half = (2**.5)*(r + j.STUB)/2
        dx, dy = pts[:, 0] - cx, pts[:, 1] - cy
        rho = np.hypot(dx, dy)
        lead = j.STUB + .01   # the stubs run into the arc unmitred too
        swept = (qx*dx >= -lead) & (qy*dy >= -lead) & (rho <= r + ws/2 + .05)
        band |= swept & ((np.abs(rho - r) > half - .05) | (pts[:, 2] > half - .05))
    return band


def _v(p):
    from build123d import Location
    return Location(tuple(p))


def t_cutout_deviation(values):
    """The T source clips its stem cutouts with the stem's x > 0 half
    (T:143-145 right_half wraps the channel AND its cutout children), so the
    -X wall openings never cut; the port cuts what Cord_Side_Cutouts names
    (NOTICE deviations). Returns the clipped-away cutter parts, world frame."""
    from build123d import Box, Pos
    v = m.SPECS[T].resolve_values(values)
    first = m.layout(T, v)[0]
    half = Pos(-j.FAR/2, 0, 0)*Box(j.FAR, j.FAR, j.FAR)
    kept = [cut & half for cut in j.first_arm_cutters(first.width, v['channel_total_height'],
                                                      **m._cut_args(v))]
    return [first.location*cut for cut in kept if cut._wrapped is not None and cut.volume > 0]


def _in_any(part_list, points, grow=.05):
    hit = np.zeros(len(points), bool)
    for part in part_list:
        bb = part.bounding_box()
        hit |= np.all((points >= np.array(tuple(bb.min)) - grow) & (points <= np.array(tuple(bb.max)) + grow), axis=1)
    return hit


@pytest.mark.parametrize('ref_name', PARITY)
def test_reference_parity(ref_name, tmp_path):
    """Both-way surface distance <= 0.02 mm, bounds within the 0.01 mm Nudge,
    volume within 0.1 %.

    Reference faces with port solid on both sides are skipped (reported):
    CGAL keeps touching volumes, so grip bases, each arm's junction-end cap,
    the T stem halves' and the curve quadrants' clip faces and the curves'
    path_extrude2d mitre joints are internal faces in the meshes (Volumes: 6
    to 14 in the logs), and the added_radius 0 L wall is hollow above
    HOLLOW_Z. A ref point >= 0.02 mm off the port surface counts only when it
    is inside the port solid, so missing port material still fails ref->port
    and extra port material fails port->ref and the volume check.
    """
    name, values = PARITY[ref_name]
    part = build(name, values)
    ref = load_reference(ASSETS / 'mesh' / f'{ref_name}.stl')
    port = mesh_from_part(part, tmp_path / 'port.stl', tolerance=0.002, angular_tolerance=0.05)
    box = part.bounding_box()
    assert (box.min.Z, box.max.Z) == pytest.approx((ref.bounds[0][2], ref.bounds[1][2]), abs=1e-3)
    assert np.abs(np.array([box.min.X, box.min.Y, box.max.X, box.max.Y])
                  - np.array([*ref.bounds[0][:2], *ref.bounds[1][:2]])).max() <= 0.015
    hollow = name == L and not values.get('added_radius')
    deviation = t_cutout_deviation(values) if name == T and values.get('number_of_cord_cutouts') else []
    expected = 0.
    if hollow:
        expected = -333.   # the hollow band (see HOLLOW_Z)
    if deviation:
        stem = m.layout(T, m.SPECS[T].resolve_values(values))[0].solid(values.get('channel_total_height', 22), 0.)
        expected = sum((stem & cut).volume for cut in deviation)
    assert ref.volume - part.volume == pytest.approx(expected, abs=max(3, 1e-3*part.volume))
    out = {}
    for label, a, b in (('port->ref', port, ref), ('ref->port', ref, port)):
        points, _ = sample_surface(a, n=20000, seed=7, sampler='even')
        points = np.vstack([points, a.vertices])
        d = trimesh.proximity.closest_point(b, points)[1]
        skip = _in_any(deviation, points)
        if a is ref:
            far = np.flatnonzero((d > 0.02) & ~skip)
            skip[far[[part.is_inside(tuple(p)) for p in points[far]]]] = True
        band = unmitred_band(points, name, values) & ~skip
        keep = ~skip & ~band
        out[label] = (d[keep].max(), d[band].max() if band.any() else 0., skip.mean())
        assert d[keep].max() <= 0.02, (label, d[keep].max(), points[keep][np.argmax(d[keep])])
        assert out[label][1] <= BAND_CAP, (label, 'unmitred band', out[label][1])
    print(f'PARITY | {ref_name} | ref vol {ref.volume:.1f} port {part.volume:.1f} expected gap {expected:.1f} | '
          + ' | '.join(f'{k} max {v[0]:.4f} band max {v[1]:.3f} skipped {100*v[2]:.2f}%' for k, v in out.items()))


def _winding(mesh, p):
    a, b, cc = (mesh.triangles[:, i] - p for i in range(3))
    la, lb, lc = (np.linalg.norm(q, axis=1) for q in (a, b, cc))
    det = np.einsum('ij,ij->i', a, np.cross(b, cc))
    den = la*lb*lc + np.einsum('ij,ij->i', a, b)*lc + np.einsum('ij,ij->i', b, cc)*la \
        + np.einsum('ij,ij->i', cc, a)*lb
    return 2*np.arctan2(det, den).sum()/(4*np.pi)


def test_l_reference_wall_is_hollow_only_where_masked():
    """Pin the reference artefact: the b86a7584 L wall mid-plane is empty
    (winding 0) above HOLLOW_Z at 100 and 170 degrees, solid below it and at
    135 degrees; the port wall is solid at every one of those points."""
    ref = load_reference(ASSETS / 'mesh' / 'l.stl')
    part = build(L)
    w = c.channel_width(1)
    for ang, z, solid in ((100, 12, False), (100, 17, False), (170, 12, False), (170, 17, False),
                          (100, 6, True), (135, 12, True), (135, 17, True), (170, 9, True)):
        a = np.radians(ang)
        p = np.array([w/2 + (w - 1)*np.cos(a), -w/2 + (w - 1)*np.sin(a), z])
        assert round(_winding(ref, p)) == int(solid), (ang, z)
        assert part.is_inside(tuple(p))


# --- planner rig invariants (parts/monokini_{l,t,x}.invariants.py) ------------

@pytest.mark.parametrize('arm', [1, 2])   # author default 1, planner default 2
def test_planner_footprint_formula(arm):
    """28*(w + arm) - 0.79 at both defaults (the planner's EXPECTED numbers are
    at arm 2; the author's at arm 1). The port is 0.01 mm short of the
    source's Nudge at each free end."""
    lb = build(L, {'length_y_units': arm, 'length_x_units': arm}).bounding_box()
    assert (lb.size.X, lb.size.Y, lb.size.Z) == pytest.approx((28*(1 + arm) - .79,)*2 + (22,), abs=.015)
    tb = build(T, {'stem_length_units': arm}).bounding_box()
    assert (tb.size.X, tb.size.Y) == pytest.approx((84.03, 28*(1 + arm) - .79), abs=.035)
    xb = build(X, {k: arm for k in ('bottom_length_units', 'right_length_units', 'left_length_units',
                                    'top_length_units')}).bounding_box()
    assert (xb.size.X, xb.size.Y) == pytest.approx((28*(1 + 2*arm),)*2, abs=.035)


def test_grip_counts_t_node_and_x_centre():
    """Per arm, cells x 2 walls; the T crossbar keeps only its top-wall grip at
    the node (x=0); the X centre cell carries none (planner F7)."""
    per_arm = lambda name, v=None: [sum(1 for g in m.grips(name, v) if g[0] == arm)
                                    for arm in m.layout(name, m.SPECS[name].resolve_values(v or {}))]
    assert per_arm(L) == [2, 2]
    assert per_arm(L, {'length_y_units': 3, 'length_x_units': 2}) == [6, 4]
    assert per_arm(T) == [2, 2, 2, 1]
    node = [g for g in m.grips(T) if g[0].keep is not None and g[0].spin == 90]
    assert len(node) == 1 and node[0][1] == 0 and node[0][2] == 1   # +X local = +Y world wall
    assert per_arm(X) == [2, 2, 2, 2]
    part, w, h = build(X), c.channel_width(1), 22
    for x, y in ((0, w/2 - .1), (0, -(w/2 - .1)), (w/2 - .1, 0), (-(w/2 - .1), 0)):
        assert not part.is_inside((x, y, h - .7))     # no nub anywhere round the centre
    tp = build(T)
    assert tp.is_inside((0, w/2 - .1, h - .7)) and not tp.is_inside((0, w/2 - .35, h - 2.7))


@pytest.mark.parametrize('name,values', [
    (L, {}), (L, {'mirror_channel': True, 'added_radius': 2, 'suppress_connectors': 'L,R'}),
    (T, {'width_left_units': 2, 'suppress_connectors': 'L,B,R,N'}), (X, {'suppress_connectors': 'B,L,R,S'}),
])
def test_grip_probe(name, values):
    """The unit grip probe of underware_i_channel at every kept grip, mapped
    through its arm's placement (and the L mirror); suppressed grips are air."""
    part = build(name, values)
    v = m.SPECS[name].resolve_values(values)
    h = v['channel_total_height']
    flip = -1 if v.get('mirror_channel') else 1
    for arm in m.layout(name, v):
        kept = {(y, s) for y, s, _ in arm.grips(v['grip_flare'])}
        everything = j.Arm(arm.length, arm.width, arm.x, arm.y, arm.spin, '', keep=arm.keep)
        for y, side, _ in everything.grips():
            for probe, (u, dz, solid) in GRIP_PROBES.items():
                p = arm.location*_v((side*(arm.width/2 - u), y, h - dz))
                pt = (flip*p.position.X, p.position.Y, p.position.Z)
                expect = solid and ((y, side) in kept or probe == 'wall under rail')
                assert part.is_inside(pt) == expect, (name, values, arm.spin, y, side, probe)


def test_mirror_is_exact_and_commutes_with_added_radius():
    """Mirror_Channel xflips the whole actually_channel (L:127-131), Added_Radius
    shifts inside it (:134/:140): mirrored(r) == mirror(unmirrored(r))."""
    for r in (0, 1):
        plain = build(L, {'added_radius': r, 'length_x_units': 2})
        flipped = build(L, {'added_radius': r, 'length_x_units': 2, 'mirror_channel': True})
        ref = mirror(plain, Plane.YZ)
        assert (flipped - ref).volume < 1e-3 and (ref - flipped).volume < 1e-3
        assert flipped.bounding_box().min.X == pytest.approx(-plain.bounding_box().max.X, abs=1e-6)


def test_added_radius_shifts_whole_cells():
    """Each Added_Radius unit moves the Y arm 28 mm to -X and the X arm 28 mm to
    +Y (L:134, :140), so both footprint sides grow by exactly 28 mm."""
    boxes = [build(L, {'added_radius': r}).bounding_box() for r in (0, 1, 2)]
    for r, b in enumerate(boxes):
        assert (b.min.X, b.max.X, b.min.Y, b.max.Y) == pytest.approx(
            (-13.2 - 28*r, 42, -42, 13.2 + 28*r), abs=1e-6)
    arms = [m.layout(L, m.SPECS[L].resolve_values({'added_radius': r})) for r in (0, 1, 2)]
    assert [a[0].x for a in arms] == [0, -28, -56] and [a[1].y for a in arms] == [0, 28, 56]


@pytest.mark.parametrize('name', m.SPECS)
def test_presets_are_single_valid_watertight_solids(name, tmp_path):
    for preset in m.SPECS[name].presets:
        part = build(name, preset.values)
        assert part.is_valid and len(part.solids()) == 1
        # The production exporter drops the native cone-apex collapsed triangle
        # at each added_radius-0 inside corner (tests/test_toolchain.py).
        export_stl(part, tmp_path / 'p.stl')
        assert trimesh.load_mesh(tmp_path / 'p.stl').is_watertight
        print(f'VOLUME | {name} | {preset.id} | {part.volume:.1f} mm3')


# --- named errors (three-outcome domains) --------------------------------------

@pytest.mark.parametrize('name,values,message', [
    (L, {'suppress_connectors': 'N,N,N'}, 'has 3 comma fields but the junction has only 2'),
    (T, {'suppress_connectors': 'N,N,N,N,N'}, 'has 5 comma fields but the junction has only 4'),
    (L, {'suppress_connectors': 'NN'}, 'has 2 codes but the channel has only 1'),
    (X, {'suppress_connectors': 'N,N,N,Q'}, 'unknown code(s) Q'),
    (T, {'suppress_connectors': ',,,NN'}, 'has 2 codes but the channel has only 1'),
    (L, {'channel_separators': 'SSS'}, 'has 3 codes but the channel has only 2'),
    (T, {'channel_separators': 'S'}, "unknown param 'channel_separators'"),
    (X, {'channel_separators': 'S'}, "unknown param 'channel_separators'"),
    (X, {'cord_side_cutouts': 'Left Side Top'}, 'cord_side_cutouts'),
    (L, {'grip_flare': 10}, 'grip_flare above 9.9 degrees'),
    (L, {'number_of_cord_cutouts': 1}, 'crosses the grip at y=0 mm'),
    (L, {'number_of_cord_cutouts': 1, 'suppress_connectors': 'B', 'shift_cutouts': 14}, 'runs past the first channel'),
    (T, {'number_of_cord_cutouts': 2, 'stem_length_units': 3, 'shift_cutouts': 28},
     'runs past the first channel'),
    (L, {'channel_width_units': 4, 'length_x_units': 10}, 'past the 325 x 320 mm bed'),
    (L, {'added_radius': 2, 'length_x_units': 10}, 'past the 325 x 320 mm bed'),
    (T, {'left_length_units': 9, 'right_length_units': 9}, 'past the 325 x 320 mm bed'),
    (X, {'channel_width_units': 4, 'top_length_units': 9}, 'past the 325 x 320 mm bed'),
])
def test_named_errors(name, values, message):
    with pytest.raises(ValueError) as exc:
        build(name, values)
    assert message in str(exc.value)


# --- print audit and edge inventory ---------------------------------------------

LEN_L = ('length_y_units', 'length_x_units')
LEN_T = ('stem_length_units', 'left_length_units', 'right_length_units')
LEN_X = ('bottom_length_units', 'right_length_units', 'left_length_units', 'top_length_units')
CUT3 = {'number_of_cord_cutouts': 2}
CASES = {
    # L: every numeric endpoint, both booleans, the corners the bed allows.
    'l-default': (L, {}), 'l-mirrored': (L, {'mirror_channel': True}),
    'l-width-4': (L, {'channel_width_units': 4}),
    'l-height-10': (L, {'channel_total_height': 10}), 'l-height-72': (L, {'channel_total_height': 72}),
    'l-y-10': (L, {'length_y_units': 10}), 'l-x-10': (L, {'length_x_units': 10}),
    'l-radius-1': (L, {'added_radius': 1}), 'l-radius-2-mirrored': (L, {'added_radius': 2, 'mirror_channel': True}),
    'l-max-corner': (L, {'channel_width_units': 4, 'channel_total_height': 72, 'added_radius': 2,
                         'length_y_units': 4, 'length_x_units': 4}),
    'l-min-corner': (L, {'channel_total_height': 10, 'added_radius': 2}),
    'l-separators-w4': (L, {'channel_width_units': 4, 'channel_separators': 'SSSSSSSS', 'added_radius': 1}),
    'l-separators-w2-r0': (L, {'channel_width_units': 2, 'channel_separators': 'SNS'}),
    'l-flare-9.9': (L, {'grip_flare': 9.9}), 'l-flare-5-suppress': (L, {'grip_flare': 5, 'suppress_connectors': 'S,L'}),
    'l-suppress-all': (L, {'suppress_connectors': 'B,B'}),
    'l-cut-both': (L, {'length_y_units': 3, **CUT3}),
    'l-cut-n9-w6': (L, {'length_y_units': 10, 'number_of_cord_cutouts': 9, 'cord_cutout_width': 6}),
    'l-cut-w20': (L, {'length_y_units': 3, 'number_of_cord_cutouts': 1, 'cord_cutout_width': 20,
                      'suppress_connectors': 'NBN'}),
    'l-cut-d56': (L, {'length_y_units': 4, 'number_of_cord_cutouts': 2, 'distance_between_cutouts': 56}),
    'l-cut-d14': (L, {'length_y_units': 3, 'number_of_cord_cutouts': 2, 'distance_between_cutouts': 14,
                      'suppress_connectors': 'NBN'}),
    'l-cut-left-top': (L, {'length_y_units': 3, 'cord_side_cutouts': 'Left Side Top', **CUT3}),
    'l-cut-right-top-h10': (L, {'length_y_units': 3, 'cord_side_cutouts': 'Right Side Top',
                                'channel_total_height': 10, **CUT3}),
    # T: three widths, three lengths.
    't-default': (T, {}), 't-height-10': (T, {'channel_total_height': 10}),
    't-height-72': (T, {'channel_total_height': 72}),
    't-bottom-4': (T, {'width_bottom_units': 4}), 't-left-4': (T, {'width_left_units': 4}),
    't-right-4': (T, {'width_right_units': 4}),
    't-stem-10': (T, {'stem_length_units': 10}), 't-left-9': (T, {'left_length_units': 9}),
    't-right-9': (T, {'right_length_units': 9}),
    't-widths-421': (T, {'width_bottom_units': 4, 'width_left_units': 2, 'width_right_units': 1}),
    't-widths-321': (T, {'width_bottom_units': 3, 'width_left_units': 2}),
    't-widths-142': (T, {'width_bottom_units': 1, 'width_left_units': 4, 'width_right_units': 2}),
    't-max-corner': (T, {'width_bottom_units': 4, 'width_left_units': 4, 'width_right_units': 4,
                         'channel_total_height': 72, 'stem_length_units': 4, 'left_length_units': 2,
                         'right_length_units': 2}),
    't-flare-9.9': (T, {'grip_flare': 9.9}), 't-suppress-all': (T, {'suppress_connectors': 'B,B,B,B'}),
    't-cut-both': (T, {'stem_length_units': 3, **CUT3}),
    't-cut-right-top-widths': (T, {'stem_length_units': 3, 'width_left_units': 2,
                                   'cord_side_cutouts': 'Right Side Top', 'number_of_cord_cutouts': 1}),
    # X: one width, four lengths.
    'x-default': (X, {}), 'x-width-4': (X, {'channel_width_units': 4}),
    'x-height-10': (X, {'channel_total_height': 10}), 'x-height-72': (X, {'channel_total_height': 72}),
    **{f'x-{k.split("_")[0]}-9': (X, {k: 9}) for k in LEN_X},
    'x-max-corner': (X, {'channel_width_units': 4, 'channel_total_height': 72,
                         **{k: 3 for k in LEN_X}}),
    'x-flare-9.9': (X, {'grip_flare': 9.9}), 'x-suppress-all': (X, {'suppress_connectors': 'B,B,B,B'}),
    'x-cut-left': (X, {'bottom_length_units': 3, 'cord_side_cutouts': 'Left Side', **CUT3}),
}


def _world(name, v, shape):
    if name == L and v['mirror_channel']:
        return mirror(shape, Plane.YZ)
    return shape


def edge_inventory(name, part, values):
    """Every edge with a >= 1 degree turn, by family; anything else fails.

    Families as underware_i_channel's: grip (wall tops, rails, nubs and ramps
    face the board), end face (each arm's free end butts the next part),
    bed chamfer (the author's 4 mm 45 degree exterior chamfer, also swept
    round the corner and revolved into the inside-corner cone), interior
    (inside the U), cutout / flare (author edges), inside corner: at
    added_radius 0 (always on T and X) the corner arc's axis lies on the two
    arms' outer walls, which meet in a sharp vertical 90 degree edge from the
    chamfer apex (z = topChamfer) to the wall top; kept as the author's (the
    Underware lids interlock round these walls), width step: a T corner
    sized for a stem wider than the arm it leads into leaves its stub end
    and the walls beside it exposed (author geometry, t-b4l2r1.stl). Stubs
    and arcs otherwise meet the arms tangentially.
    """
    v = m.SPECS[name].resolve_values(values)
    h, arms = v['channel_total_height'], m.layout(name, v)
    boxes = [_world(name, v, arms[0].location*cut).bounding_box() for cut in cord_cutouts(
        arms[0].width, h, **m._cut_args(v))]
    if v['grip_flare'] > 0:
        boxes += [_world(name, v, arm.location*grip_flared_cut(arm.width, h, y, side)).bounding_box()
                  for arm in arms for y, side, flared in arm.grips(v['grip_flare']) if flared]
    steps = []
    if name == T:
        # A corner sized for the stem leads out into a narrower arm: its stub's
        # end and the walls round it stay exposed (t-b4l2r1.stl, T:239-281).
        for (side, wc, dx, dy), arm in zip(j.t_corner_placements(
                v['width_bottom_units'], v['width_left_units'], v['width_right_units']), arms[1:3]):
            cx, cy = side*wc/2 + dx, -wc/2 + dy
            wall = arm.y - arm.width/2
            if abs(wall - cy) > 1e-6:
                steps.append((min(abs(cx) - c.SNAP_WALL, abs(cx) + j.STUB), abs(cx) + j.STUB, side,
                              min(cy, wall), max(cy, wall) + c.INNER_CHAMFER))
    ends = []
    for arm in arms:
        if arm.keep is not None and arm is not arms[0]:
            continue   # the T crossbar: both ends meet the arms
        far = max((-1, 1), key=lambda s: hypot(*_end(arm, s)))
        ends.append(_world_end(name, v, arm, far))
    adjacent = {}
    for face in part.faces():
        for edge in face.edges():
            adjacent.setdefault(edge, []).append(face)
    families, worst = {}, 0.
    for edge, faces in adjacent.items():
        if len(faces) != 2:
            continue
        mid = edge.position_at(.5)
        angle = degrees(acos(max(-1., min(1., faces[0].normal_at(mid).dot(faces[1].normal_at(mid))))))
        if angle < 1:
            continue
        z, bb = mid.Z, edge.bounding_box()
        if any(b.min.X - .05 <= mid.X <= b.max.X + .05 and b.min.Y - .05 <= mid.Y <= b.max.Y + .05
               and b.min.Z - .05 <= z <= b.max.Z + .05 for b in boxes):
            family = 'cutout/flare'
        elif z >= h - c.BASE_HEIGHT - 1e-4:
            family = 'grip'
        elif any(a - .05 <= side*mid.X <= b + .05 and lo - .05 <= mid.Y <= hi + .05
                 for a, b, side, lo, hi in steps):
            family = 'width step'
        elif any((axis == 'x' and abs(mid.X - at) < 1e-4 and bb.size.X < 1e-4)
                 or (axis == 'y' and abs(mid.Y - at) < 1e-4 and bb.size.Y < 1e-4) for axis, at in ends):
            family = 'end face'
        elif (abs(z) < 1e-4 or abs(z - c.TOP_CHAMFER) < 1e-4) and abs(angle - 45) < 1:
            family = 'bed chamfer'
            worst = max(worst, angle)
        elif z >= c.SNAP_WALL - 1e-4 and _inside_u(part, mid, faces):
            family = 'interior'
        elif bb.size.X < 1e-4 and bb.size.Y < 1e-4 and abs(bb.min.Z - c.TOP_CHAMFER) < 1e-4 \
                and abs(bb.max.Z - (h - c.BASE_HEIGHT)) < 1e-4 and abs(angle - 90) < 1:
            family = 'inside corner'
        else:
            family = f'UNCLASSIFIED {tuple(round(q, 2) for q in mid)} {angle:.0f}'
        families[family] = families.get(family, 0) + 1
    return families, worst


def _end(arm, s):
    """World (x, y) of an arm's end s (-1: local -Y)."""
    a = np.radians(arm.spin)
    return arm.x - s*arm.length/2*np.sin(a), arm.y + s*arm.length/2*np.cos(a)


def _world_end(name, v, arm, s):
    x, y = _end(arm, s)
    flip = -1 if name == L and v['mirror_channel'] else 1
    return ('y', y) if arm.spin % 180 == 0 else ('x', flip*x)


def _inside_u(part, mid, faces):
    """An interior edge faces into the channel: neither face points at the
    bed, the point 0.05 mm off both faces and 0.5 mm up is air, and there is
    floor or wall straight below that point (an exterior edge has open air
    under it, outside the U)."""
    n = faces[0].normal_at(mid) + faces[1].normal_at(mid)
    if min(f.normal_at(mid).Z for f in faces) < -1e-6:
        return False
    px, py = mid.X + .05*n.X, mid.Y + .05*n.Y
    if part.is_inside((px, py, mid.Z + .05*n.Z + .5)):
        return False
    return any(part.is_inside((px, py, z)) for z in (mid.Z - .1, mid.Z - .5, mid.Z - 1, 1., .5))


@pytest.mark.audit
@pytest.mark.parametrize('case', CASES)
def test_endpoint_audit_and_edges(case):
    name, values = CASES[case]
    part = build(name, values)
    assert part.is_valid and len(part.solids()) == 1
    spec = m.SPECS[name]
    raw = pa.audit(part, spec.print_orientation, model=case)
    assert raw.longest_bridge_mm <= pa.MAX_BRIDGE_MM
    regions = m.audit_exclusions(name, values)
    report = pa.audit(part, spec.print_orientation, model=case, exclusions=flat(regions))
    assert report.ok, report.format()
    families, worst = edge_inventory(name, part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    print(f'AUDIT | {case} | vol {part.volume:.1f} | raw wall {raw.min_wall_mm:.3f} ovh {raw.max_overhang_deg:.1f} '
          f'bridge {raw.longest_bridge_mm:.2f} | filtered wall {report.min_wall_mm:.3f} ovh '
          f'{report.max_overhang_deg:.1f} | edges worst exposed {worst:.1f} {dict(sorted(families.items()))} '
          f'| exceptions {", ".join(k for k, r in regions.items() if r) or "none"} | PASS')


@pytest.mark.parametrize('name', m.SPECS)
def test_exclusions_still_reject_a_new_thin_fin(name):
    from build123d import Box, Pos
    part = build(name) + Pos(0, -30, 4)*Box(.4, 6, 4)   # a 0.4 mm fin on the first arm's floor
    report = pa.audit(part, m.SPECS[name].print_orientation, exclusions=flat(m.audit_exclusions(name)))
    assert report.min_wall_mm < pa.MIN_WALL_MM
