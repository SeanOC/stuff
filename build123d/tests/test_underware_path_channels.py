"""Underware S / diagonal path channels (pst-fsk8s.3): parity with the
author's renders, the swept connector's constant section, grip probes on
the two straight runs (and none on the connector), named errors and the
endpoint print audit with an exposed-edge inventory.

References: assets/underware-opengrid/mesh/{s,diagonal}.stl (mayor, BOSL2
b86a7584) and the worker variants listed in the NOTICE.

The epic's two "exception families" are reference artefacts, not geometry:
the z = h - BASE_HEIGHT "lips" (1.30 mm wide, 78 mm2) are the grip bases
CGAL keeps as internal faces (winding 1 above and below), and the S z = 2.0
patch (21 mm2) is the channel floor's top with inverted normals where
path_extrude2d segments overlap (winding >= 1 below, 0 above). The port has
neither face (test_reference_exception_faces_are_internal), so it registers
no exclusion beyond underware_i_channel's grip families.
"""
from __future__ import annotations

import sys
from math import acos, atan2, cos, degrees, hypot, radians
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import Box, Plane, Pos, Rectangle, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holders import underware_path_channels as m
from tests import print_audit as pa
from scripts.export import export_stl
from tests.audit_record import record
from tests.parity import load_reference, mesh_from_part, sample_surface
from underware import constants as c
from underware import path as p
from underware.channel import cell_centres, channel_section, cord_cutouts, present_grips
from underware.grip import grip_flared_cut

from tests.test_underware import ASSETS, GRIP_PROBES
from tests.test_underware_junctions import _inside_u, _winding

SPEC = m.SPEC_PATH


def flat(regions):
    return [r for family in regions.values() for r in family]


def build(values=None):
    return SPEC.build(values or {})


def layout(values=None):
    v = SPEC.resolve_values(values or {})
    first, second = m.path_runs(v)
    return v, first, second


def connector(values=None):
    """The swept connector's middle edge: the S Bezier or the diagonal leg."""
    v, first, second = layout(values)
    return p.centre_path(v['part'], first, second).edges()[1]


# --- parity ------------------------------------------------------------------

PARITY = {
    's': {},
    'diagonal': {'part': 'diagonal'},
    's-w2-om1-u3-b2-flare5': {'channel_width_units': 2, 'units_over': -1, 'units_up': 3,
                              'length_bottom_units': 2, 'grip_flare': 5,
                              'suppress_connectors': 'NB,L', 'channel_separators': 'NS'},
    'diagonal-o1-u3-b2t3-h34-sep': {'part': 'diagonal', 'units_over': 1, 'units_up': 3,
                                    'length_bottom_units': 2, 'length_top_units': 3,
                                    'channel_total_height': 34, 'channel_separators': 'S'},
}
BEZIER_CHORDS = 16       # BOSL2 bezpath_curve's default splinesteps
DIAGONAL_FA = 12         # rotate_extrude $fa of each diagonal joint's outside fill


def _bez(q, t):
    t = t[:, None]
    return (1-t)**3*q[0] + 3*(1-t)**2*t*q[1] + 3*(1-t)*t**2*q[2] + t**3*q[3]


def _dbez(q, t):
    t = t[:, None]
    return 3*(1-t)**2*(q[1]-q[0]) + 6*(1-t)*t*(q[2]-q[1]) + 3*t**2*(q[3]-q[2])


def _segment_distance(points, a, b):
    ab = b - a
    s = np.clip(((points - a) @ ab)/(ab @ ab), 0, 1)
    return np.linalg.norm(points - (a + s[:, None]*ab), axis=1)


def bezier_chord_sagitta(width, over, up):
    """How far the source's chorded S walls (path_extrude2d of the Bezier
    sampled at BEZIER_CHORDS) sit off the true offset curves the port sweeps:
    worst over the outer and inner faces of both walls."""
    q = np.array(p.bezier_controls(*p.offsets(over, up)))
    fine, knots = np.linspace(0, 1, 4001), np.linspace(0, 1, BEZIER_CHORDS + 1)
    worst = 0.
    for o in (width/2, -width/2, width/2 - c.SNAP_WALL, -(width/2 - c.SNAP_WALL)):
        def offset(t):
            d = _dbez(q, t)
            return _bez(q, t) + o*np.stack([d[:, 1], -d[:, 0]], 1)/np.linalg.norm(d, axis=1)[:, None]
        curve, chords = offset(fine), offset(knots)
        worst = max(worst, np.min([_segment_distance(curve, chords[i], chords[i + 1])
                                   for i in range(BEZIER_CHORDS)], axis=0).max())
    return worst


def connector_band(points, values):
    """(mask, cap): reference points on the source's faceted connector and
    the facet sagitta they may sit off the port. S: the Bezier stretch
    between the runs (+1 mm); diagonal: within the half-width of either vertex."""
    v, first, second = layout(values)
    w = first.width
    if v['part'] == 'S':
        # The first and last chords' joints into the runs spill under 1 mm
        # along Y (0.10 mm off at the seam, 0 by 1 mm in).
        mask = (points[:, 1] > first.end - 1) & (points[:, 1] < second.start + 1)
        return mask, bezier_chord_sagitta(w, v['units_over'], v['units_up']) + 0.02
    mask = np.zeros(len(points), bool)
    for x, y in ((0., first.end), (second.x, second.start)):
        mask |= np.hypot(points[:, 0] - x, points[:, 1] - y) <= w/2 + 0.1
    return mask, w/2*(1 - cos(radians(DIAGONAL_FA/2))) + 0.02


@pytest.mark.parametrize('ref_name', PARITY)
def test_reference_parity(ref_name, tmp_path):
    """Both-way surface distance <= 0.02 mm off the connector band, the facet
    sagitta inside it; bounds within 0.015 mm; volume within 0.1 % (S: 0.15 %,
    the chords cut the outside of every bend).

    Skipped (reported) reference points: faces with port solid on both sides
    (CGAL keeps touching volumes: the grips stand on the connector's wall
    tops, the path_extrude2d segments overlap) and zero-thickness sheets
    (winding 0 on both sides: each flared grip's end-ramp skin at z = h).
    A ref point >= 0.02 mm off the port surface counts unless it is one of
    those, so missing port material still fails ref->port and extra port
    material fails port->ref and the volume check.
    """
    values = PARITY[ref_name]
    part = build(values)
    ref = load_reference(ASSETS / 'mesh' / f'{ref_name}.stl')
    port = mesh_from_part(part, tmp_path / 'port.stl', tolerance=0.002, angular_tolerance=0.05)
    box = part.bounding_box()
    assert np.abs(np.array([*box.min, *box.max]) - ref.bounds.ravel()).max() <= 0.015
    share = 1.5e-3 if SPEC.resolve_values(values)['part'] == 'S' else 1e-3
    assert abs(ref.volume - part.volume) <= max(3, share*part.volume)
    out = {}
    for label, a, b in (('port->ref', port, ref), ('ref->port', ref, port)):
        points, _ = sample_surface(a, n=20000, seed=7, sampler='even')
        points = np.vstack([points, a.vertices])
        d = trimesh.proximity.closest_point(b, points)[1]
        skip = np.zeros(len(points), bool)
        if a is ref:
            for i in np.flatnonzero(d > 0.02):
                q = points[i]
                sheet = all(round(_winding(ref, q + dz)) == 0 for dz in ((0, 0, .05), (0, 0, -.05)))
                skip[i] = sheet or part.is_inside(tuple(q))
        band, cap = connector_band(points, values)
        band &= ~skip
        keep = ~skip & ~band
        out[label] = (d[keep].max(), d[band].max() if band.any() else 0., cap, skip.mean())
        assert d[keep].max() <= 0.02, (label, d[keep].max(), points[keep][np.argmax(d[keep])])
        assert out[label][1] <= cap, (label, 'connector band', out[label][1], cap)
    print(f'PARITY | {ref_name} | ref vol {ref.volume:.1f} port {part.volume:.1f} | '
          + ' | '.join(f'{k} max {v[0]:.4f} band max {v[1]:.3f} (cap {v[2]:.3f}) skipped {100*v[3]:.2f}%'
                       for k, v in out.items()))


def test_reference_exception_faces_are_internal():
    """The epic's lip (z = h - BASE_HEIGHT) and S z = 2.0 down-facing families
    have reference solid on the far side, so they print as nothing; the port
    has no down-facing face steeper than 45 degrees anywhere."""
    for name in ('s', 'diagonal'):
        ref = load_reference(ASSETS / 'mesh' / f'{name}.stl')
        n, centres = ref.face_normals, ref.triangles_center
        down = (n[:, 2] < -0.99) & (centres[:, 2] > 0.5)
        heights = sorted(set(np.round(centres[down, 2], 2)))
        assert heights == ([2.0, 18.6] if name == 's' else [18.6]), (name, heights)
        for q in centres[down][::7]:
            above = round(_winding(ref, q + (0, 0, .05)))
            below = round(_winding(ref, q - (0, 0, .05)))
            assert below >= 1, (name, q)   # solid under a "down" face: not an overhang
            assert above == (1 if q[2] > 10 else 0), (name, q)
    for values in ({}, {'part': 'diagonal'}):
        report = pa.audit(build(values), SPEC.print_orientation)
        assert report.max_overhang_deg <= pa.MAX_OVERHANG_DEG + 1e-6


# --- invariants -----------------------------------------------------------------

SECTION_CASES = {
    'S': {},
    'S-w2-om1-u3-sep': {'channel_width_units': 2, 'units_over': -1, 'units_up': 3,
                        'channel_separators': 'NS'},
    'diagonal': {'part': 'diagonal'},
    'diagonal-w4-o1-u5-h72-sep': {'part': 'diagonal', 'channel_width_units': 4, 'units_over': 1,
                                  'units_up': 5, 'channel_total_height': 72,
                                  'channel_separators': 'SNSNSNS'},
}


@pytest.mark.parametrize('case', SECTION_CASES)
def test_connector_section_is_constant(case):
    """At 7 stations along the connector (the S Bezier, the diagonal leg) the
    part cut normal to the path is the channel section, separators included:
    symmetric difference under 0.002 mm2."""
    values = SECTION_CASES[case]
    v, first, _ = layout(values)
    part, edge, h, w = build(values), connector(values), v['channel_total_height'], first.width
    profile = channel_section(w, h, v['channel_separators'])
    for u in np.linspace(.1, .9, 7):
        at, t = edge.position_at(u), edge.tangent_at(u)
        expected = Pos(at.X, at.Y, 0)*Rot(0, 0, degrees(atan2(-t.X, t.Y)))*profile
        window = Plane(origin=(at.X, at.Y, h/2), x_dir=(t.Y, -t.X, 0), z_dir=t)*Rectangle(w + .4, h + .4)
        actual = part & window
        assert sum(f.area for f in actual.faces()) == pytest.approx(profile.area, abs=1e-3), (case, u)
        assert (actual - expected).area + (expected - actual).area < 2e-3, (case, u)


GRIP_CASES = {
    'S': {},
    'S-w2-om1-u3-suppress': {**PARITY['s-w2-om1-u3-b2-flare5'], 'grip_flare': 0},
    'diagonal-b3t2-suppress': {'part': 'diagonal', 'length_bottom_units': 3, 'length_top_units': 2,
                               'suppress_connectors': 'LNB,R'},
    'diagonal-o-3-u3': {'part': 'diagonal', 'units_over': -3, 'units_up': 3},
}


def _v(q):
    from build123d import Location
    return Location(q)


@pytest.mark.parametrize('case', GRIP_CASES)
def test_grips_sit_on_straight_run_cells_only(case):
    """underware_i_channel's grip probe at every cell centre of both straight
    runs (kept grips solid, suppressed ones air, the connector's wall under
    the rail always solid), and no solid above the wall top over the
    connector's Y span: the connector is gripless."""
    values = GRIP_CASES[case]
    v, first, second = layout(values)
    part, h, w = build(values), v['channel_total_height'], first.width
    grips = m.grips(SPEC.name, values)
    assert len(grips) == sum(len(present_grips(r.length, r.suppress, v['grip_flare'])) for r in (first, second))
    for run in (first, second):
        kept = {(y, s) for y, s, _ in present_grips(run.length, run.suppress, v['grip_flare'])}
        assert {(g[1], g[2]) for g in grips
                if (g[0].position.X, g[0].position.Y) == (run.x, run.y)} == kept
        for y in cell_centres(run.length):
            for side in (1, -1):
                for probe, (u, dz, solid) in GRIP_PROBES.items():
                    q = run.location*_v((side*(w/2 - u), y, h - dz))
                    expect = solid and ((y, side) in kept or probe == 'wall under rail')
                    assert part.is_inside(tuple(q.position)) == expect, (case, run.y, y, side, probe)
    lo, hi = first.end, second.start
    x0, x1 = min(0, second.x) - w, max(0, second.x) + w
    roof = Pos((x0 + x1)/2, (lo + hi)/2, h)*Box(x1 - x0, hi - lo, 2*c.BASE_HEIGHT - .02)
    assert (part & roof).volume < 1e-6, case


@pytest.mark.parametrize('preset', [pr.id for pr in SPEC.presets])
def test_presets_are_single_valid_watertight_solids(preset, tmp_path):
    values = next(pr.values for pr in SPEC.presets if pr.id == preset)
    part = build(values)
    assert part.is_valid and len(part.solids()) == 1
    export_stl(part, tmp_path / 'p.stl')
    assert trimesh.load_mesh(tmp_path / 'p.stl').is_watertight
    print(f'VOLUME | {SPEC.name} | {preset} | {part.volume:.1f} mm3')


# --- named errors (three-outcome domains) --------------------------------------

@pytest.mark.parametrize('values,message', [
    ({'units_over': 0}, 'units_over 0 is a straight channel'),
    ({'part': 'diagonal', 'units_over': 0}, 'units_over 0 is a straight channel'),
    ({'units_over': 2, 'units_up': 1}, 'the S bend over 2 / up 1 cells'),
    ({'units_over': 3, 'units_up': 2}, 'the S bend over 3 / up 2 cells'),
    ({'channel_width_units': 2, 'units_over': 2, 'units_up': 9}, 'the inner wall would fold'),
    ({'channel_width_units': 4, 'units_over': 1, 'units_up': 9}, 'the inner wall would fold'),
    ({'units_over': -10, 'units_up': 9}, 'the inner wall would fold'),
    ({'part': 'diagonal', 'units_over': 2, 'units_up': 1}, 'past the 6.5 mm the end grip'),
    ({'part': 'diagonal', 'channel_width_units': 2, 'units_over': 1, 'units_up': 1},
     'past the 6.5 mm the end grip'),
    ({'part': 'diagonal', 'channel_width_units': 4, 'units_over': 1, 'units_up': 4},
     'past the 6.5 mm the end grip'),
    ({'part': 'diagonal', 'units_over': 10, 'units_up': 5}, 'past the 6.5 mm the end grip'),
    ({'length_bottom_units': 9}, 'past the 325 x 320 mm bed'),
    ({'units_over': 1, 'units_up': 9, 'length_top_units': 2}, 'past the 325 x 320 mm bed'),
    ({'part': 'diagonal', 'units_over': 1, 'units_up': 1, 'length_bottom_units': 9,
      'length_top_units': 2}, 'past the 325 x 320 mm bed'),
    ({'part': 'diagonal', 'units_over': 10, 'units_up': 6, 'channel_width_units': 2},
     'past the 6.5 mm the end grip'),
    ({'suppress_connectors': 'N,N,N'}, 'has 3 comma fields'),
    ({'suppress_connectors': 'NN'}, 'has 2 codes but the channel has only 1'),
    ({'suppress_connectors': 'Q'}, 'unknown code(s) Q'),
    ({'channel_separators': 'SSS'}, 'has 3 codes but the channel has only 2'),
    ({'grip_flare': 10}, 'grip_flare above 9.9 degrees'),
    ({'grip_flare': 15}, 'grip_flare above 9.9 degrees'),
    ({'number_of_cord_cutouts': 1}, 'crosses the grip at y=0 mm'),
    ({'length_bottom_units': 3, 'number_of_cord_cutouts': 12, 'units_over': 1},
     'runs past the first channel'),
    ({'length_bottom_units': 3, 'number_of_cord_cutouts': 2, 'shift_cutouts': 28, 'units_over': 1},
     'runs past the first channel'),
])
def test_named_errors(values, message):
    with pytest.raises(ValueError) as exc:
        build(values)
    assert message in str(exc.value)


@pytest.mark.parametrize('values', [
    {'part': 'diagonal', 'units_over': 1, 'units_up': 1},                            # setback 4.64
    {'part': 'diagonal', 'channel_width_units': 2, 'units_over': 1, 'units_up': 2},  # 5.95
    {'part': 'diagonal', 'channel_width_units': 4, 'units_over': 1, 'units_up': 5},  # 5.27 (u4: 6.55)
    {'part': 'diagonal', 'units_over': 10, 'units_up': 6},                           # 6.34 (u5: 6.92)
    {'channel_width_units': 3, 'units_over': 1, 'units_up': 3},                      # S r >= w/2
])
def test_domain_edges_build(values):
    """The valid side of each connector limit builds one valid solid."""
    part = build(values)
    assert part.is_valid and len(part.solids()) == 1


def test_setback_rule_is_the_grip_spacing():
    """The diagonal limit is SPACING_FROM_CHANNEL: (w/2 - SNAP_WALL) tan(turn/2)."""
    assert p.MAX_SETBACK == c.SPACING_FROM_CHANNEL == 6.5
    w = c.channel_width(2)
    assert p.mitre_setback(w, p.corner_turn(*p.offsets(1, 2))) == pytest.approx(5.949, abs=1e-3)
    assert p.mitre_setback(w, p.corner_turn(*p.offsets(1, 1))) == pytest.approx(10.438, abs=1e-3)
    narrow = c.channel_width(1)
    assert p.mitre_setback(narrow, p.corner_turn(*p.offsets(10, 6))) == pytest.approx(6.341, abs=1e-3)
    assert p.mitre_setback(narrow, p.corner_turn(*p.offsets(10, 5))) == pytest.approx(6.922, abs=1e-3)


# --- print audit and edge inventory ---------------------------------------------

D = {'part': 'diagonal'}
CUT = {'length_bottom_units': 3, 'units_over': 1, 'number_of_cord_cutouts': 2}
CASES = {
    # S: every numeric endpoint the connector and the bed allow (the rest are
    # named errors above: width 4, |units_over| >= 4, a 9-cell run).
    's-default': {}, 's-width-2': {'channel_width_units': 2, 'units_over': 1},
    's-width-3': {'channel_width_units': 3, 'units_over': 1, 'units_up': 3},
    's-height-10': {'channel_total_height': 10}, 's-height-72': {'channel_total_height': 72},
    's-over-minus-3': {'units_over': -3, 'units_up': 3}, 's-over-1-up-9': {'units_over': 1, 'units_up': 9},
    's-bottom-8': {'units_over': 1, 'length_bottom_units': 8},
    's-top-8': {'units_over': 1, 'length_top_units': 8},
    's-max-corner': {'channel_width_units': 3, 'channel_total_height': 72, 'units_over': -1,
                     'units_up': 3, 'length_bottom_units': 3, 'length_top_units': 3},
    's-min-corner': {'channel_total_height': 10, 'units_over': 1, 'units_up': 2},
    's-separators-w3': {'channel_width_units': 3, 'units_over': 1, 'units_up': 3,
                        'channel_separators': 'SNSN'},
    's-flare-9.9': {'grip_flare': 9.9}, 's-flare-5-suppress': {'grip_flare': 5, 'suppress_connectors': 'S,L'},
    's-suppress-all': {'suppress_connectors': 'B,B'},
    's-cut-both': CUT,
    's-cut-n4-w6': {**CUT, 'length_bottom_units': 5, 'number_of_cord_cutouts': 4, 'cord_cutout_width': 6},
    's-cut-w20': {**CUT, 'number_of_cord_cutouts': 1, 'cord_cutout_width': 20, 'suppress_connectors': 'NBN'},
    's-cut-d56': {**CUT, 'length_bottom_units': 4, 'distance_between_cutouts': 56},
    's-cut-d14': {**CUT, 'distance_between_cutouts': 14, 'suppress_connectors': 'NBN'},
    's-cut-left-top': {**CUT, 'cord_side_cutouts': 'Left Side Top'},
    's-cut-right-top-h10': {**CUT, 'cord_side_cutouts': 'Right Side Top', 'channel_total_height': 10},
    # diagonal: wider domain (width 4, |units_over| 10, 9-cell runs, up 1).
    'diag-default': D, 'diag-width-4': {**D, 'channel_width_units': 4, 'units_over': 1, 'units_up': 5},
    'diag-height-10': {**D, 'channel_total_height': 10}, 'diag-height-72': {**D, 'channel_total_height': 72},
    'diag-over-10': {**D, 'units_over': 10, 'units_up': 6},
    'diag-over-minus-10': {**D, 'units_over': -10, 'units_up': 6},
    'diag-up-1': {**D, 'units_over': 1, 'units_up': 1}, 'diag-up-9': {**D, 'units_over': 1, 'units_up': 9},
    'diag-bottom-9': {**D, 'units_over': 1, 'units_up': 1, 'length_bottom_units': 9},
    'diag-top-9': {**D, 'units_over': -1, 'units_up': 1, 'length_top_units': 9},
    'diag-max-corner': {**D, 'channel_width_units': 4, 'channel_total_height': 72, 'units_over': -1,
                        'units_up': 5, 'length_bottom_units': 2, 'length_top_units': 2},
    'diag-setback-5.9-w2': {**D, 'channel_width_units': 2, 'units_over': 1, 'units_up': 2},
    'diag-separators-w4': {**D, 'channel_width_units': 4, 'units_over': 1, 'units_up': 5,
                           'channel_separators': 'SSSSSSSS'},
    'diag-flare-9.9': {**D, 'grip_flare': 9.9}, 'diag-suppress-all': {**D, 'suppress_connectors': 'B,B'},
    'diag-cut-both': {**D, **CUT}, 'diag-cut-left': {**D, **CUT, 'cord_side_cutouts': 'Left Side'},
    'diag-cut-shift-14': {**D, **CUT, 'number_of_cord_cutouts': 1, 'shift_cutouts': 14,
                          'suppress_connectors': 'NBN'},
}


def _mitre_planes(v, first, second):
    """(point, unit normal, turn) of the diagonal's two mitre planes: each
    joint's inside is mitred on the bisector of its legs (the outside is the
    swept round fill, tangent to both legs)."""
    a, b = np.array([0., first.end]), np.array([second.x, second.start])
    up, leg = np.array([0., 1.]), (b - a)/np.linalg.norm(b - a)
    turn = degrees(acos(float(up @ leg)))
    return [(q, (d1 + d2)/np.linalg.norm(d1 + d2), turn) for q, d1, d2 in ((a, up, leg), (b, leg, up))]


def edge_inventory(part, values):
    """Every edge with a >= 1 degree turn, by family; anything else fails.

    Families as underware_junctions': grip (wall tops, rails, nubs and ramps
    face the board), end face (each run's free end butts the next part),
    bed chamfer (the author's 45 degree exterior chamfer, swept round the S
    and the diagonal joints), interior (inside the U), cutout / flare
    (author edges), mitre joint (diagonal only: path_extrude2d mitres each
    joint's inside on the bisector of the legs, a crease of the turn angle
    down the wall, chamfer and floor; kept as the author's — the lids
    interlock round these walls). The S Bezier meets both runs tangentially.
    """
    v, first, second = layout(values)
    h, w = v['channel_total_height'], first.width
    boxes = [(first.location*cut).bounding_box() for cut in cord_cutouts(w, h, **m._cut_args(v))]
    if v['grip_flare'] > 0:
        boxes += [(run.location*grip_flared_cut(w, h, y, side)).bounding_box()
                  for run in (first, second)
                  for y, side, flared in present_grips(run.length, run.suppress, v['grip_flare']) if flared]
    mitres = _mitre_planes(v, first, second) if v['part'] == 'diagonal' else []
    ends = (first.start, second.end)
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
        samples = [np.array(tuple(edge.position_at(s))[:2]) for s in (0, .5, 1)]
        if any(b.min.X - .05 <= mid.X <= b.max.X + .05 and b.min.Y - .05 <= mid.Y <= b.max.Y + .05
               and b.min.Z - .05 <= z <= b.max.Z + .05 for b in boxes):
            family = 'cutout/flare'
        elif z >= h - c.BASE_HEIGHT - 1e-4:
            family = 'grip'
        elif any(abs(mid.Y - y) < 1e-4 and bb.size.Y < 1e-4 for y in ends):
            family = 'end face'
        elif any(all(abs((s - q) @ n) < 1e-3 for s in samples) and abs(angle - turn) < 1
                 for q, n, turn in mitres):
            family = 'mitre joint'
        elif (abs(z) < 1e-4 or abs(z - c.TOP_CHAMFER) < 1e-4) and abs(angle - 45) < 1:
            family = 'bed chamfer'
            worst = max(worst, angle)
        elif z >= c.SNAP_WALL - 1e-4 and _inside_u(part, mid, faces):
            family = 'interior'
        else:
            family = f'UNCLASSIFIED {tuple(round(q, 2) for q in mid)} {angle:.0f}'
        families[family] = families.get(family, 0) + 1
    return families, worst


@pytest.mark.audit
@pytest.mark.parametrize('case', CASES)
def test_endpoint_audit_and_edges(case):
    values = CASES[case]
    part = build(values)
    assert part.is_valid and len(part.solids()) == 1
    raw = pa.audit(part, SPEC.print_orientation, model=case)
    assert raw.max_overhang_deg <= pa.MAX_OVERHANG_DEG + 1e-6
    assert raw.longest_bridge_mm <= pa.MAX_BRIDGE_MM
    regions = m.audit_exclusions(SPEC.name, values)
    report = pa.audit(part, SPEC.print_orientation, model=case, exclusions=flat(regions))
    assert report.ok, report.format()
    families, worst = edge_inventory(part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    print(f'AUDIT | {case} | vol {part.volume:.1f} | raw wall {raw.min_wall_mm:.3f} ovh {raw.max_overhang_deg:.1f} '
          f'bridge {raw.longest_bridge_mm:.2f} | filtered wall {report.min_wall_mm:.3f} ovh '
          f'{report.max_overhang_deg:.1f} | edges worst exposed {worst:.1f} {dict(sorted(families.items()))} '
          f'| exceptions {", ".join(k for k, r in regions.items() if r) or "none"} | PASS')
    record(case, vol=part.volume, raw_wall=raw.min_wall_mm, raw_ovh=raw.max_overhang_deg,
           raw_bridge=raw.longest_bridge_mm, filtered_wall=report.min_wall_mm,
           filtered_ovh=report.max_overhang_deg, edges_worst_exposed=worst,
           edges=dict(sorted(families.items())), exceptions=[k for k, r in regions.items() if r],
           result='PASS')


@pytest.mark.parametrize('values', [{}, D])
def test_exclusions_still_reject_a_new_thin_fin(values):
    part = build(values) + Pos(0, -30, 4)*Box(.4, 6, 4)   # a 0.4 mm fin on the bottom run's floor
    report = pa.audit(part, SPEC.print_orientation, exclusions=flat(m.audit_exclusions(SPEC.name, values)))
    assert report.min_wall_mm < pa.MIN_WALL_MM
