# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""underware_outside_corner (pst-38hu7): the mitre's convex twin.

An original design derived from the ported mitre (no author source, no
parity mesh): the mitre's first arm, the bend turned the other way about an
axis above it (floor outside), a second arm rising +Z. Checked here: bed fit
and the arm cap, the grip cells against the mitre's (first arm identical,
second arm at the mitre's distances from its bend, mirrored to the other
side), mirror_channel = x-flip, cord cutouts on the first arm only, the bed
flat under the bend, the one published exception (BendUnderside) and the P4
endpoint audit + exposed-edge table in the -45 degree print frame.
"""
from __future__ import annotations

from math import acos, atan2, degrees, pi, sqrt

import numpy as np
import pytest
import trimesh
from build123d import Cylinder, Location, Plane, Pos, Rot, Vector, mirror

from holders import underware_path_channels as m
from holders.printer import BED_X, BED_Y, BED_Z
from scripts.export import export_stl
from tests import print_audit as pa
from tests.audit_record import record
from tests.test_underware_path_channels import _bed_faces, _inside_u_at, _print_frame_cut, _to, flat
from underware import constants as c
from underware import path as p
from underware.channel import cord_cutouts
from underware.grip import grip_flared, grip_flared_cut

SPEC = m.SPEC_OUTSIDE
MSPEC = m.SPEC_MITRE
MIN_BED_MM2 = 60.      # the mitre's floor (two tip strips there, one bend strip here)
PRESETS = {pr.id: pr.values for pr in SPEC.presets}


def _fits(span, width, height):
    return max(span, width) <= BED_X and min(span, width) <= BED_Y and height <= BED_Z


# --- registration, bed fit, arm cap ---------------------------------------------------

def test_registration_mirrors_the_mitre_params():
    """Same parameter names, kinds, ranges, labels and filename flags as the
    mitre (incl. its Advanced group); three presets, two mirroring the
    mitre's."""
    def shape(spec):
        return [(q.name, q.kind, q.default, q.min, q.max, q.step, q.label, q.group, q.filename)
                for q in spec.params]
    assert shape(SPEC) == shape(MSPEC)
    assert list(PRESETS) == ['outside-corner', 'outside-corner-r1', 'outside-corner-w2-h28-y2']
    assert [pr.values for pr in MSPEC.presets] == list(PRESETS.values())[:2]
    assert SPEC.category_id == 'multiboard' and SPEC.print_frame is m.outside_print_frame


@pytest.mark.parametrize('preset', PRESETS)
def test_presets_fit_the_bed_and_are_single_watertight_solids(preset, tmp_path):
    values = PRESETS[preset]
    v = m.outside_values(values)
    part = SPEC.build(values)
    assert part.is_valid and len(part.solids()) == 1
    box = (SPEC.print_frame(v)*part).bounding_box()
    assert m.outside_extent(v) == pytest.approx((box.size.Y, box.size.X, box.size.Z), abs=1e-3)
    assert _fits(box.size.Y, box.size.X, box.size.Z)
    export_stl(part, tmp_path/'p.stl')
    assert trimesh.load_mesh(tmp_path/'p.stl').is_watertight
    print(f'VOLUME | {SPEC.name} | {preset} | {m.unflattened_outside_corner(values).volume:.1f} -> '
          f'{part.volume:.1f} mm3 | {box.size.Y:.1f} x {box.size.X:.1f} x {box.size.Z:.1f} mm')


def test_arm_cap_is_the_bed():
    """MAX_ARM_OUTSIDE: 7 cells fit at the smallest corner, 8 do not (the
    span is set by both arms at 45 degrees, at any width)."""
    small = {'channel_total_height': 10, 'added_radius': 0}
    for units in (1, 4):
        v = m.outside_values({**small, 'channel_width_units': units, 'length_units': m.MAX_ARM_OUTSIDE})
        assert _fits(*m.outside_extent(v))
        v.update(length_y_units=m.MAX_ARM_OUTSIDE + 1, length_down_units=m.MAX_ARM_OUTSIDE + 1)
        assert not _fits(*m.outside_extent(v))
    assert m.MAX_ARM_OUTSIDE == max(q.max for q in SPEC.params if q.name == 'length_units')


@pytest.mark.parametrize('values,message', [
    ({'length_units': 8}, 'length_units=8 > max 7'),
    ({'channel_width_units': 4, 'channel_total_height': 72, 'added_radius': 2, 'length_units': 4},
     'past the 325 x 320 x 325 mm build volume'),
    ({'length_units': 7, 'channel_total_height': 40}, 'past the 325 x 320 x 325 mm build volume'),
    ({'number_of_cord_cutouts': 1}, 'crosses the grip at y=0 mm'),
    ({'suppress_connectors': 'N,N,N'}, 'has 3 comma fields'),
])
def test_named_errors(values, message):
    with pytest.raises(ValueError) as exc:
        SPEC.build(values)
    assert message in str(exc.value)


# --- grips vs the mitre, mirror, cutouts ----------------------------------------------

GRIP_CASES = {
    'default': {}, 'r1': {'added_radius': 1}, 'r2-w2-h28-y2': {'added_radius': 2, 'channel_width_units': 2,
                                                                'channel_total_height': 28, 'length_units': 2},
    'w4-h10-y3-suppress': {'channel_width_units': 4, 'channel_total_height': 10, 'length_units': 3,
                           'suppress_connectors': 'NLR,RNB'},
}


def _grip_point(loc, y, side, w, h):
    """The grip's cell centre on its wall top, model frame."""
    return Vector(*(loc*Location((side*(w/2 - c.SNAP_WALL/2), y, h - c.BASE_HEIGHT))).position)


@pytest.mark.parametrize('case', GRIP_CASES)
def test_grip_cells_mirror_the_mitre(case):
    """First arm: the mitre's grips, location for location. Second arm: the
    mitre's cell distances from its bend plane (axis height), on the other
    side of the bend (mitre: below z = -r; here: above z = axis), same X and
    side codes, on the open-face plane through the edge line. From the edge
    line both arms sit on the 14 + 28 k lattice past the open-face radius
    added_radius*GRID (first arm +STUB, the mitre's lead-out)."""
    values = GRIP_CASES[case]
    v = m.outside_values(values)
    w, h, r = c.channel_width(v['channel_width_units']), v['channel_total_height'], v['added_radius']
    ours, mitre = m.grips(SPEC.name, values), m.grips(MSPEC.name, values)
    assert [g[1:] for g in ours] == [g[1:] for g in mitre]
    n1 = len(m._checked_outside(values)[1].grips(v['grip_flare']))
    for (lo, *_), (lm, *_) in zip(ours[:n1], mitre[:n1]):
        assert lo.position == lm.position and lo.orientation == lm.orientation
    ya, za = p.outside_axis(v['channel_width_units'], h, r)
    ey, ez = p.outside_edge(v['channel_width_units'], h, r)
    mr = p.mitre_radius(h, r)
    for (lo, y, side, _), (lm, *_) in zip(ours[n1:], mitre[n1:]):
        qo, qm = _grip_point(lo, y, side, w, h), _grip_point(lm, y, side, w, h)
        assert qo.X == pytest.approx(qm.X, abs=1e-9)
        assert qo.Z - za == pytest.approx(-mr - qm.Z, abs=1e-9)          # the mitre's distance, mirrored
        assert qo.Y == pytest.approx(ey, abs=1e-9)                       # on the second panel's face
        k = (qo.Z - ez - 14 - r*c.GRID)/c.GRID
        assert k == pytest.approx(round(k), abs=1e-9) and round(k) >= 0
    for lo, y, side, _ in ours[:n1]:
        q = _grip_point(lo, y, side, w, h)
        assert q.Z == pytest.approx(ez, abs=1e-9)
        k = (ey - q.Y - 14 - p.STUB - r*c.GRID)/c.GRID
        assert k == pytest.approx(round(k), abs=1e-9) and round(k) >= 0


MIRROR_CASES = {'default': {}, 'r1-w2-cut-left': {'added_radius': 1, 'channel_width_units': 2, 'length_units': 3,
                                                  'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Left Side'}}


@pytest.mark.parametrize('case', MIRROR_CASES)
def test_mirror_channel_is_an_x_flip(case):
    values = MIRROR_CASES[case]
    flipped = SPEC.build({**values, 'mirror_channel': True})
    expect = mirror(SPEC.build(values), Plane.YZ)
    assert flipped.is_valid and len(flipped.solids()) == 1
    assert (flipped - expect).volume < 1e-3 and (expect - flipped).volume < 1e-3
    a, b = flipped.bounding_box(), expect.bounding_box()
    assert np.allclose([*a.min, *a.max], [*b.min, *b.max], atol=1e-6)


@pytest.mark.parametrize('side', ['Both Sides', 'Left Side Top', 'Right Side'])
def test_cord_cutouts_cut_the_first_arm_only(side):
    """The cutters remove material only inside the first arm (y below the
    lead-out, under the first panel); the bend and the second arm are
    untouched."""
    base = {'length_units': 3}
    plain, cut = SPEC.build(base), SPEC.build({**base, 'number_of_cord_cutouts': 2, 'cord_side_cutouts': side})
    removed = plain - cut
    assert removed.volume > 1 and (cut - plain).volume < 1e-6
    box = removed.bounding_box()
    w = c.channel_width(1)
    assert box.max.Y <= -w/2 - p.STUB + 1e-6
    assert box.max.Z <= 22 + 1e-6 and box.min.Z >= -1e-6


# --- bed flat and the one exception ---------------------------------------------------

BED_CASES = {**PRESETS, **{f'w{w}-h{h}-r{r}': {'channel_width_units': w, 'channel_total_height': h,
                                                'added_radius': r}
                           for w in (1, 4) for h in (10, 72) for r in (0, 2)},
             'mirror-r1': {'mirror_channel': True, 'added_radius': 1}}


@pytest.mark.audit
@pytest.mark.parametrize('case', BED_CASES)
def test_bed_flat_under_the_bend(case):
    """The bed flat sits BEND_FLAT_MM above the floor cylinder's lowest line
    (outside_bed_plane, derived per parameter set); the finished solid is the
    unflattened one minus exactly that half-space (print-frame bbox: only
    min Z moves); one bed strip under the bend of >= 60 mm2; the floor keeps
    SNAP_WALL - BEND_FLAT_MM there."""
    values = BED_CASES[case]
    v = m.outside_values(values)
    frame = SPEC.print_frame(v)
    raw, part = m.unflattened_outside_corner(values), SPEC.build(values)
    assert part.is_valid and len(part.solids()) == 1
    plane = m.outside_bed_plane(v)
    pre, fin = (frame*raw).bounding_box(), (frame*part).bounding_box()
    assert pre.min.Z == pytest.approx(plane - m.BEND_FLAT_MM, abs=1e-3)
    assert fin.min.Z == pytest.approx(plane, abs=1e-6)
    assert np.allclose([*pre.min][:2] + [*pre.max], [*fin.min][:2] + [*fin.max], atol=1e-6)
    bed = _bed_faces(frame*part, plane)
    assert len(bed) == 1
    contact = bed[0].area
    assert contact >= MIN_BED_MM2
    removed = (raw & _print_frame_cut(frame, plane)).volume
    assert raw.volume - part.volume == pytest.approx(removed, abs=1e-3)
    assert 0 < removed < 2e-2*raw.volume      # ~0.4 % at the default, ~1.5 % at width 4 height 10
    assert c.SNAP_WALL - m.BEND_FLAT_MM >= pa.MIN_WALL_MM
    print(f'OUTSIDE BED | {case} | plane {plane:.3f} | contact {contact:.2f} mm2 | vol {raw.volume:.1f} -> '
          f'{part.volume:.1f} (-{removed:.1f})')


BEND_CASES = {'r0': {}, 'r1': {'added_radius': 1}, 'r2': {'added_radius': 2},
              'r1-mirror-w2-h28': {'channel_width_units': 2, 'channel_total_height': 28, 'added_radius': 1,
                                   'mirror_channel': True},
              'r0-w4-h10': {'channel_width_units': 4, 'channel_total_height': 10},
              'r2-w4-h72-y3': {'channel_width_units': 4, 'channel_total_height': 72, 'added_radius': 2,
                               'length_units': 3}}


@pytest.mark.audit
@pytest.mark.parametrize('case', BEND_CASES)
def test_bend_exception_is_narrow_and_exact(case):
    """The one published exception (approver: mayor) is the bend's floor
    underside and nothing else: the envelope holds exactly the two cylinder
    faces the bed flat leaves of the floor-radius cylinder (area = floor
    width * R * (pi/2 - 2 alpha), alpha the flat's half angle); without it
    the audit fails on exactly those (downward curved faces, overhang < 90
    because the flat removed the crown), with it the audit passes; the
    print-frame placement keeps the same faces; a new curved overhang under
    the first arm, off the bend, is not waived."""
    values = BEND_CASES[case]
    v = m.outside_values(values)
    frame, part = SPEC.print_frame(v), SPEC.build(values)
    regions = m.audit_exclusions(SPEC.name, values)
    assert 'arch-underside' not in regions
    (bend,) = regions['bend-underside']
    h, r = v['channel_total_height'], v['added_radius']
    rf = p.outside_floor_radius(h, r)

    def held(envelope, face):
        return all(envelope.is_inside(tuple(q)) for q in (face.center(), *face.vertices(),
                                                          *(face.position_at(*uv) for uv in ((.2, .3), (.8, .7)))))

    inside = [f for f in part.faces() if held(bend, f)]
    assert len(inside) == 2 and all(str(f.geom_type).endswith('CYLINDER') for f in inside)
    width = inside[0].bounding_box().size.X
    alpha = acos((rf - m.BEND_FLAT_MM)/rf)
    assert sum(f.area for f in inside) == pytest.approx(width*rf*(pi/2 - 2*alpha), rel=1e-3)
    placed = frame*bend
    assert [i for i, f in enumerate((frame*part).faces()) if held(placed, f)] == \
        [i for i, f in enumerate(part.faces()) if held(bend, f)]
    others = [e for k, family in regions.items() if k != 'bend-underside' for e in family]
    raw = pa.audit(part, SPEC.print_orientation, print_frame=frame, exclusions=others)
    assert not raw.ok and 45 < raw.max_overhang_deg < 90
    assert [d.geom_type for d in raw.downward_fillets] == ['CYLINDER', 'CYLINDER']
    assert raw.longest_bridge_mm <= pa.MAX_BRIDGE_MM
    clean = pa.audit(part, SPEC.print_orientation, print_frame=frame, exclusions=flat(regions))
    assert clean.ok, clean.format()
    w = c.channel_width(v['channel_width_units'])
    xc = -bend.x0 - w/2 if v['mirror_channel'] else bend.x0 + w/2
    bump = Pos(xc, -w/2 - p.STUB - 4, -1)*Rot(0, 90, 0)*Cylinder(2, 6)   # under the first arm, off the bend
    damaged = pa.audit(part + bump, SPEC.print_orientation, print_frame=frame, exclusions=flat(regions))
    assert not damaged.ok and len(damaged.downward_fillets) > 0
    print(f'OUTSIDE BEND | {case} | floor r {rf:.1f} mm | chord {rf*sqrt(2):.1f} mm | floor width {width:.2f} mm | '
          f'faces {sum(f.area for f in inside):.1f} mm2 | raw ovh {raw.max_overhang_deg:.1f} bridge '
          f'{raw.longest_bridge_mm:.2f} | filtered ovh {clean.max_overhang_deg:.1f} wall {clean.min_wall_mm:.3f} '
          f'| signed: pending mayor')


def test_bend_envelope_is_the_quadrant_only():
    """The predicate's own bounds: on the floor radius inside the bend's
    quadrant and the width; off it by radius, quadrant or x; frame placement
    round-trips; mirrored x range."""
    v = m.outside_values({})
    bend, w = m.bend_underside({}), c.channel_width(1)
    ya, za = p.outside_axis(1, 22, 0)
    rf = p.outside_floor_radius(22, 0)
    on = (0., ya + rf*.5, za - rf*sqrt(.75))
    assert bend.is_inside(on)
    assert not bend.is_inside((on[0], on[1] + .01, on[2] - .01))         # off the radius
    assert not bend.is_inside((0., ya - .5, za - (rf**2 - .25)**.5))      # before the bend (first arm)
    assert not bend.is_inside((0., ya + (rf**2 - .25)**.5, za + .5))      # past it (second arm)
    assert not bend.is_inside((w/2 + .01, *on[1:]))                       # outside the width
    frame = SPEC.print_frame(v)
    assert (frame*bend).is_inside(tuple(_to(frame, on)))
    assert not (frame*bend).is_inside(on)
    assert type(frame*bend) is m.BendUnderside
    mirrored = m.bend_underside({'added_radius': 1, 'mirror_channel': True})
    assert (mirrored.x0, mirrored.x1) == pytest.approx((c.GRID - w/2, c.GRID + w/2))


# --- P4: endpoint audit + exposed edges ----------------------------------------------

def _section_frame(q, ya, za, second):
    """The piece frame an edge at model point q is read in: the first arm
    (and the lead-out) as built, the second arm's Location, or the bend
    unrolled about its axis onto the first arm's end (outside_bend revolves
    the section by theta about +X). Grips stand >= 6.5 mm off the bend
    planes, so a grip above z = axis (first arm, added_radius 0) is still
    first-arm."""
    if q.Y <= ya + 1e-6 and (q.Z <= za + 1e-6 or q.Y < ya - 6):
        return Location()
    if q.Z >= za - 1e-6:
        return second
    theta = degrees(atan2(q.Y - ya, za - q.Z))
    return Pos(0, ya, za)*Rot(theta, 0, 0)*Pos(0, -ya, -za)


def edge_inventory(part, values):
    """The mitre's edge families (tests/test_underware_path_channels.py
    mitre_edge_inventory) read in this part's piece frames: grip, end face,
    bed chamfer, interior, cutout / flare (+ a flared rail's own sheared end
    edges, as grip) and 'bed flat' (the cut's boundary
    on the print bed, the only exposed edge it adds). A mirrored part is read
    unmirrored (the cut is mirror-invariant)."""
    v = m.outside_values(values)
    if v['mirror_channel']:
        part, values = mirror(part, Plane.YZ), {**values, 'mirror_channel': False}
        v = m.outside_values(values)
    h, w, r = v['channel_total_height'], c.channel_width(v['channel_width_units']), v['added_radius']
    ya, za = p.outside_axis(v['channel_width_units'], h, r)
    frame = SPEC.print_frame(v)
    plane = m.outside_bed_plane(v)
    _, first = m._checked_outside(values)
    second = p.outside_second_location(v['channel_width_units'], h, v['length_down_units'], r)
    tips = (-(first.length + v['channel_width_units']*c.GRID/2), -v['length_down_units']*c.GRID/2)
    boxes = [(first.location*cut).bounding_box() for cut in cord_cutouts(w, h, **m._cut_args(v))]
    boxes += [(loc*grip_flared_cut(w, h, y, side)).bounding_box()
              for loc, y, side, flared in m.grips(SPEC.name, values) if flared]
    # A flared rail is sheared z*tan(flare) outward: at height 72 its end
    # edges lean up to 12.6 mm out of its slit box (the mitre's table stops
    # at height 22, 3.8 mm). Those are still grip (library) edges.
    rails = [(loc*grip_flared(w, h, y, side, v['grip_flare'])).bounding_box()
             for loc, y, side, flared in m.grips(SPEC.name, values) if flared]
    adjacent = {}
    for face in part.faces():
        for edge in face.edges():
            adjacent.setdefault(edge, []).append(face)
    families, worst = {}, 0.
    for edge, faces in adjacent.items():
        if len(faces) != 2:
            continue
        mid = edge.position_at(.5)
        normals = [f.normal_at(mid) for f in faces]
        angle = degrees(acos(max(-1., min(1., normals[0].dot(normals[1])))))
        if angle < 1:
            continue
        samples = [edge.position_at(t) for t in (0, .5, 1)]
        loc = _section_frame(mid, ya, za, second)
        back = loc.inverse()
        ql = _to(back, mid)
        local_y = [_to(back, q).Y for q in samples]
        z = ql.Z
        if all(abs(_to(frame, q).Z - plane) < 1e-4 for q in samples):
            family = 'bed flat'
            worst = max(worst, angle)
        elif any(b.min.X - .05 <= mid.X <= b.max.X + .05 and b.min.Y - .05 <= mid.Y <= b.max.Y + .05
                 and b.min.Z - .05 <= mid.Z <= b.max.Z + .05 for b in boxes):
            family = 'cutout/flare'
        elif z >= h - c.BASE_HEIGHT - 1e-4:
            family = 'grip'
        elif any(all(abs(y - tip) < 1e-4 for y in local_y)
                 for tip in (tips[0] if loc == Location() else tips[1],)):
            family = 'end face'
        elif (abs(z) < 1e-4 or abs(z - c.TOP_CHAMFER) < 1e-4) and abs(angle - 45) < 1:
            family = 'bed chamfer'
            worst = max(worst, angle)
        elif z >= c.SNAP_WALL - 1e-4 and _inside_u_at(part, loc, ql, [_to(back, mid + n) - ql for n in normals]):
            family = 'interior'
        elif any(b.min.X - .05 <= mid.X <= b.max.X + .05 and b.min.Y - .05 <= mid.Y <= b.max.Y + .05
                 and b.min.Z - .05 <= mid.Z <= b.max.Z + .05 for b in rails):
            family = 'grip'
        else:
            family = f'UNCLASSIFIED {tuple(round(q, 2) for q in mid)} {angle:.0f}'
        families[family] = families.get(family, 0) + 1
    return families, worst


MCUT = {'length_units': 3, 'number_of_cord_cutouts': 2}
ENDPOINT_CASES = {
    # every numeric Param endpoint the bed allows (longer / wider-taller
    # corners are named errors above), all presets, the documented corners.
    **PRESETS,
    'width-4': {'channel_width_units': 4}, 'height-10': {'channel_total_height': 10},
    'height-72': {'channel_total_height': 72}, 'length-7': {'length_units': 7},
    'radius-2': {'added_radius': 2}, 'mirror': {'mirror_channel': True},
    'max-corner': {'channel_width_units': 4, 'channel_total_height': 72, 'added_radius': 2,
                   'length_units': 3, 'mirror_channel': True},
    'min-corner': {'channel_total_height': 10, 'mirror_channel': True},
    'length-7-w4-h10': {'channel_width_units': 4, 'channel_total_height': 10, 'length_units': 7},
    'separators-w4': {'channel_width_units': 4, 'channel_separators': 'SSSSSSSS'},
    'separators-w3-r1': {'channel_width_units': 3, 'channel_separators': 'SNNNNN', 'added_radius': 1},
    'flare-9.9': {'grip_flare': 9.9},
    'flare-9.9-h72-r2': {'grip_flare': 9.9, 'channel_total_height': 72, 'added_radius': 2},
    'flare-5-suppress': {'grip_flare': 5, 'suppress_connectors': 'S,L'},
    'suppress-all': {'suppress_connectors': 'B,B'},
    'cut-both': MCUT,
    'cut-n4-w6': {**MCUT, 'length_units': 5, 'number_of_cord_cutouts': 4, 'cord_cutout_width': 6},
    'cut-w20': {**MCUT, 'number_of_cord_cutouts': 1, 'cord_cutout_width': 20, 'suppress_connectors': 'NBN'},
    'cut-d56': {**MCUT, 'length_units': 4, 'distance_between_cutouts': 56},
    'cut-d14': {**MCUT, 'distance_between_cutouts': 14, 'suppress_connectors': 'NBN'},
    'cut-shift-14': {**MCUT, 'number_of_cord_cutouts': 1, 'shift_cutouts': 14, 'suppress_connectors': 'NBN'},
    'cut-left-mirror': {**MCUT, 'cord_side_cutouts': 'Left Side', 'mirror_channel': True},
    'cut-right-top-h10': {**MCUT, 'cord_side_cutouts': 'Right Side Top', 'channel_total_height': 10},
}


@pytest.mark.audit
@pytest.mark.parametrize('case', ENDPOINT_CASES)
def test_endpoint_audit_and_edges(case):
    """P4 table for underware_outside_corner in its -45 degree print frame:
    raw (only the bend underside fails), filtered (every exception family)
    and the exposed-edge inventory."""
    values = ENDPOINT_CASES[case]
    v = m.outside_values(values)
    frame, part = SPEC.print_frame(v), SPEC.build(values)
    assert part.is_valid and len(part.solids()) == 1
    raw = pa.audit(part, SPEC.print_orientation, print_frame=frame, model=case)
    assert raw.longest_bridge_mm <= pa.MAX_BRIDGE_MM
    regions = m.audit_exclusions(SPEC.name, values)
    report = pa.audit(part, SPEC.print_orientation, print_frame=frame, model=case, exclusions=flat(regions))
    assert report.ok, report.format()
    families, worst = edge_inventory(part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    print(f'AUDIT | outside-corner {case} | vol {part.volume:.1f} | raw wall {raw.min_wall_mm:.3f} ovh '
          f'{raw.max_overhang_deg:.1f} bridge {raw.longest_bridge_mm:.2f} | filtered wall {report.min_wall_mm:.3f} '
          f'ovh {report.max_overhang_deg:.1f} | edges worst exposed {worst:.1f} {dict(sorted(families.items()))} '
          f'| exceptions {", ".join(k for k, r in regions.items() if r) or "none"} | PASS')
    record(f'outside-corner-{case}', vol=part.volume, raw_wall=raw.min_wall_mm, raw_ovh=raw.max_overhang_deg,
           raw_bridge=raw.longest_bridge_mm, filtered_wall=report.min_wall_mm,
           filtered_ovh=report.max_overhang_deg, edges_worst_exposed=worst,
           edges=dict(sorted(families.items())), exceptions=[k for k, r in regions.items() if r],
           result='PASS')
