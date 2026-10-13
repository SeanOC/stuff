"""Underware for openGrid I channel port (pst-fsk8s.1).

References: assets/underware-opengrid/NOTICE (OpenSCAD 2025.06.12.ai25773,
BOSL2 b86a7584). The author's source is not committed (CC BY-NC-SA, epic
pst-fsk8s D0 outcome (b)); the cross-file module test reads it only when the
staged copy is present.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from math import acos, degrees, sqrt
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holders import underware_i_channel as m
from tests import print_audit as pa
from tests.parity import load_reference, mesh_from_part, sample_surface
from underware import constants as c
from underware.channel import cell_centres, cord_cutouts, present_grips
from underware.profile import midline_positions, monokini_profile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT.parent / 'assets' / 'underware-opengrid'
STAGED = Path(os.environ.get('UNDERWARE_SOURCE_DIR',
                             '/home/seanoconnor/gc-pilot/city/assets/incoming/underware-opengrid'))
# The mayor's pre-flight renders (city assets/incoming/underware-ref/SHA256SUMS).
MAYOR = {
    'i-1x5-h22.stl': '028e5f6e59239496c253b91222b6f8996d94996fd93e9231089cf787bd967f2a',
    'l.stl': 'bbbed61e37e8525e0baecb9f4d5789ddf2d9119b099fc503f66c2d1fd195df7e',
    't.stl': 'b78a8a69ebef3b02c4bcb594d98b47bf31f3e544ed5969111cf66a6c679fa606',
    'x.stl': 'ea0376c0d9e2723ea625475785fe9db0e6dd15ad40243d268ca131ad4ef503c9',
}
# Reference mesh -> port values. References span y -L/2-0.015 .. L/2-0.005
# (the source's 0.01 Nudge); shifting them +0.005 centres the grips.
PARITY = {
    'i-1x5-h22': {},
    'i-2x3-h34': {'channel_width_units': 2, 'channel_length_units': 3, 'channel_total_height': 34},
    'i-1x5-h22-cutouts': {'number_of_cord_cutouts': 2},
    'i-1x5-h22-label': {'add_label': True},
    'i-1x5-h22-flare5': {'grip_flare': 5},
    'i-1x5-h22-flare9p9': {'grip_flare': 9.9},
}
REF_SHIFT = (0, 0.005, 0)


def reference(name):
    ref = load_reference(ASSETS / 'mesh' / f'{name}.stl')
    ref.apply_translation(REF_SHIFT)
    return ref


def flat(regions):
    return [r for family in regions.values() for r in family]


# --- reference provenance ----------------------------------------------------

def test_reference_meshes_match_sha256sums_and_mayor_baselines():
    sums = {name: digest for digest, name in
            (line.split('  ') for line in (ASSETS / 'SHA256SUMS').read_text().splitlines())}
    files = sorted(p.name for p in (ASSETS / 'mesh').glob('*.stl'))
    assert sorted(Path(k).name for k in sums) == files
    for name in files:
        digest = hashlib.sha256((ASSETS / 'mesh' / name).read_bytes()).hexdigest()
        assert sums[f'mesh/{name}'] == digest
    for name, digest in MAYOR.items():
        assert sums[f'mesh/{name}'] == digest, f'{name} drifted from the mayor baseline'


def test_notice_lists_every_mesh_command_and_hash():
    notice = (ASSETS / 'NOTICE').read_text()
    assert 'CC BY-NC-SA 4.0' in notice and 'b86a7584db6d324eb856c2d19d041f94435e6c32' in notice
    for line in (ASSETS / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ')
        assert digest in notice and name in notice


# --- parity ------------------------------------------------------------------

def _profile_area(width, height):
    return monokini_profile(width, height).area


def reference_artefacts(points, values):
    """Reference surface with no solid behind it (CGAL keeps touching volumes).

    grip-base: unflared grips are separate volumes standing on the wall top,
      so their bases (u 0.7..2 at z = h-3.4, inside each grip's y-range) are
      internal faces ("Volumes: 12" in the I render log).
    ramp-skin: on flared grips the end-ramp cutter's top coincides with the
      grip top, leaving a zero-thickness sheet over each ramp at z = h.
    """
    v = m.SPEC.resolve_values(values)
    w, length, h = m.dimensions(v)
    x, y, z = np.abs(points[:, 0]), points[:, 1], points[:, 2]
    near = np.zeros(len(points), bool)
    for yc in cell_centres(length):
        near |= np.abs(y - yc) <= c.GRIP_SIZE/2 + 1e-3
    if v['grip_flare'] > 0:
        dy = np.min([np.abs(np.abs(y - yc) - c.GRIP_SIZE/2) for yc in cell_centres(length)], axis=0)
        return (np.abs(z - h) < 1e-3) & near & (dy <= c.GRIP_RAMP + 1e-3) & (x > w/2 - c.SNAP_WALL)
    return (np.abs(z - (h - c.BASE_HEIGHT)) < 1e-3) & near & (x >= w/2 - c.SNAP_WALL - 1e-3) \
        & (x <= w/2 - c.SNAP_CAPTURE + 1e-3)


@pytest.mark.parametrize('name', PARITY)
def test_reference_parity(name, tmp_path):
    values = PARITY[name]
    part = m.build(values)
    width, length, height = m.dimensions(m.SPEC.resolve_values(values))
    ref = reference(name)
    port = mesh_from_part(part, tmp_path / 'port.stl', tolerance=0.002, angular_tolerance=0.05)
    # Bounds: X and Z identical; the reference is NUDGE longer at -Y.
    box = part.bounding_box()
    assert (box.min.X, box.max.X, box.min.Z, box.max.Z) == pytest.approx(
        (ref.bounds[0][0], ref.bounds[1][0], ref.bounds[0][2], ref.bounds[1][2]), abs=1e-3)
    assert (box.min.Y - ref.bounds[0][1], ref.bounds[1][1] - box.max.Y) == pytest.approx((0.01, 0.), abs=1e-3)
    # Volume: the reference's extra 0.01 mm of profile is the analytic
    # reduction. Cutouts: the reference's $fn=50 cylinders cut ~0.3 mm2 less
    # section per opening; label: the font engines' letter spacing.
    reduction = 0.01*_profile_area(width, height)
    tol = {'i-1x5-h22-cutouts': 1.5, 'i-1x5-h22-label': 1.5}.get(name, 0.05)
    assert ref.volume - part.volume == pytest.approx(reduction, abs=tol)
    # Surface distance both ways, cap 0.02 mm (the $fn=50 cylinders sit
    # 0.012 mm inside the true circle). Bands: the label's glyph slab (z <=
    # 0.21) allows 0.25 mm for letter spacing (ink length 54.00 vs 53.62 mm);
    # reference artefacts (reference_artefacts) carry no solid and are
    # reported, not compared.
    text = name.endswith('label')
    out = {}
    for label, a, b in (('port->ref', port, ref), ('ref->port', ref, port)):
        points, _ = sample_surface(a, n=20000, seed=7, sampler='even')
        points = np.vstack([points, a.vertices])
        d = trimesh.proximity.closest_point(b, points)[1]
        band = points[:, 2] <= 0.21 if text else np.zeros(len(points), bool)
        skip = reference_artefacts(points, values) if a is ref else np.zeros(len(points), bool)
        keep = ~band & ~skip
        out[label] = (d[keep].max(), d[band].max() if band.any() else 0., band.mean(), skip.mean())
        assert d[keep].max() <= 0.02, (label, d[keep].max())
        if text:
            assert d[band].max() <= 0.25
    print(f'PARITY | {name} | +y {REF_SHIFT[1]} | ref vol {ref.volume:.2f} port {part.volume:.2f} '
          f'reduction {reduction:.2f} | ' + ' | '.join(
              f'{k} max {v[0]:.4f} text-band max {v[1]:.3f} ({100*v[2]:.1f}%) artefact {100*v[3]:.2f}%'
              for k, v in out.items()))


# --- invariants (planner rig parts/monokini_i.invariants.py) -------------------

@pytest.mark.parametrize('units,length', [(1, 5), (2, 3), (4, 1), (3, 12)])
def test_profile_width_grip_spacing_and_count(units, length):
    v = {'channel_width_units': units, 'channel_length_units': length}
    part = m.build(v)
    assert part.bounding_box().size.X == pytest.approx(26.4 + (units-1)*28, abs=1e-6)
    grips = present_grips(length*c.GRID, '')
    for side in (1, -1):
        ys = sorted(y for y, s, _ in grips if s == side)
        assert len(ys) == length
        assert np.allclose(np.diff(ys), c.GRID)


@pytest.mark.parametrize('preset', [p.id for p in m.SPEC.presets])
def test_presets_are_single_valid_watertight_solids(preset, tmp_path):
    part = m.build(next(p.values for p in m.SPEC.presets if p.id == preset))
    assert part.is_valid and len(part.solids()) == 1
    mesh = mesh_from_part(part, tmp_path / 'p.stl', tolerance=0.01, angular_tolerance=0.1)
    assert mesh.is_watertight
    print(f'VOLUME | {preset} | {part.volume:.1f} mm3')


# --- grip probe (the grips ARE the mount; no KNOWN_MOUNTS contract applies) ----

GRIP_PROBES = {  # (u inward from the outer face, z below the full height): solid?
    'nub tip': (0.1, 0.7, True),          # u=0 face between z=h-1 and h-0.4
    'undercut': (0.35, 2.7, False),        # the tile edge seats here
    'rail': (1.35, 2.7, True),
    'wall under rail': (1.0, 4.0, True),
}


@pytest.mark.parametrize('suppress', ['', 'LRSNB', 'BBBBB'])
def test_grip_probe(suppress):
    v = {'suppress_connectors': suppress}
    part = m.build(v)
    w, _, h = m.dimensions(m.SPEC.resolve_values(v))
    kept = {(y, s) for y, s, _ in present_grips(140, suppress)}
    for k, y in enumerate(cell_centres(140)):
        for side in (1, -1):
            for name, (u, dz, solid) in GRIP_PROBES.items():
                point = (side*(w/2-u), y, h-dz)
                expect = solid and ((y, side) in kept or name == 'wall under rail')
                assert part.is_inside(point) == expect, (suppress, k, side, name)


# --- named errors (three-outcome domains) --------------------------------------

@pytest.mark.parametrize('values,message', [
    ({'grip_flare': 10}, 'grip_flare above 9.9 degrees'),
    ({'grip_flare': 15}, 'grip_flare above 9.9 degrees'),
    ({'suppress_connectors': 'X'}, "unknown code(s) X"),
    ({'suppress_connectors': 'NNNNNN'}, 'has 6 codes but the channel has only 5'),
    ({'channel_separators': 'SSS'}, 'has 3 codes but the channel has only 2'),
    ({'number_of_cord_cutouts': 1}, 'crosses the grip at y=0 mm'),
    ({'number_of_cord_cutouts': 2, 'cord_cutout_width': 20}, 'crosses the grip at y=-28 mm'),
    ({'number_of_cord_cutouts': 2, 'grip_flare': 5}, 'crosses the grip at y=-28 mm'),
    ({'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Right Side Top', 'channel_total_height': 28},
     'below the 24.6 mm wall top'),
    ({'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Left Side Top', 'channel_total_height': 16},
     'bottoms out at z=1.9 mm'),
    ({'add_label': True, 'text_depth': 0}, 'text_depth 0 makes no label'),
    ({'add_label': True, 'text': 'A very long cable label!', 'text_size': 16}, 'the closed face is 140 x 18.4 mm'),
    ({'filament_show': True}, 'leaves less than 0.9 mm of floor'),
    ({'filament_show': True, 'filament_depth': 50}, 'puts the groove below the part'),
    ({'filament_show': True, 'filament_depth': 0.2, 'filament_offset': 50}, 'past the 8.37 mm flat floor'),
    ({'filament_show': True, 'filament_depth': 0.2, 'filament_repeat': 2, 'filament_spacing': 0},
     'less than 0.9 mm between grooves'),
    ({'filament_show': True, 'filament_diameter': 0}, 'must be positive'),
    ({'filament_show': True, 'filament_diameter': 10, 'filament_depth': 3}, 'leaves less than 0.9 mm of floor'),
    ({'filament_show': True, 'filament_depth': -50}, 'leaves less than 0.9 mm of floor'),
    ({'filament_show': True, 'filament_depth': 0.2, 'filament_offset': -50}, 'past the 8.37 mm flat floor'),
    ({'filament_show': True, 'filament_depth': 0.2, 'filament_repeat': 2, 'filament_spacing': 50},
     'past the 8.37 mm flat floor'),
])
def test_named_errors(values, message):
    with pytest.raises(ValueError) as exc:
        m.build(values)
    assert message in str(exc.value)


# --- print audit, exceptions and edges -------------------------------------------

CASES = {
    'default': {}, 'wide-tall': PARITY['i-2x3-h34'], 'cutouts': {'number_of_cord_cutouts': 2},
    'label': {'add_label': True},
    'width-4': {'channel_width_units': 4}, 'length-1': {'channel_length_units': 1},
    'length-12': {'channel_length_units': 12}, 'height-10': {'channel_total_height': 10},
    'height-16': {'channel_total_height': 16}, 'height-70': {'channel_total_height': 70},
    'height-72': {'channel_total_height': 72},
    'max-corner': {'channel_width_units': 4, 'channel_length_units': 12, 'channel_total_height': 72},
    'min-corner': {'channel_length_units': 1, 'channel_total_height': 10},
    'cut-n12': {'number_of_cord_cutouts': 12}, 'cut-w6': {'number_of_cord_cutouts': 2, 'cord_cutout_width': 6},
    'cut-w20-suppressed': {'number_of_cord_cutouts': 1, 'cord_cutout_width': 20, 'suppress_connectors': 'NNBNN'},
    'cut-d56': {'number_of_cord_cutouts': 2, 'distance_between_cutouts': 56, 'shift_cutouts': 14},
    'cut-d14': {'number_of_cord_cutouts': 2, 'distance_between_cutouts': 14, 'shift_cutouts': 7},
    'cut-shift28': {'number_of_cord_cutouts': 2, 'shift_cutouts': 28},
    'cut-left': {'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Left Side'},
    'cut-right': {'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Right Side'},
    'cut-left-top': {'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Left Side Top'},
    'cut-right-top': {'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Right Side Top'},
    'cut-top-h10': {'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Left Side Top', 'channel_total_height': 10},
    'cut-top-w20-suppressed': {'number_of_cord_cutouts': 1, 'cord_side_cutouts': 'Right Side Top',
                               'cord_cutout_width': 20, 'suppress_connectors': 'NNLNN'},
    'label-s6-24ch': {'add_label': True, 'text': 'ABCDEFGHIJKLMNOPQRSTUVWX', 'text_size': 6},
    'label-s16-d1': {'add_label': True, 'text_size': 16, 'text_depth': 1},
    'label-max-corner': {'add_label': True, 'channel_width_units': 4, 'channel_length_units': 12,
                         'text_size': 16, 'text': 'Hello cables 0123'},
    'flare-5': {'grip_flare': 5}, 'flare-9.9': {'grip_flare': 9.9},
    'flare-9.9-max-corner': {'grip_flare': 9.9, 'channel_width_units': 4, 'channel_total_height': 72},
    'suppress-mixed-flare': {'suppress_connectors': 'SNLNR', 'grip_flare': 5},
    'suppress-all': {'suppress_connectors': 'BBBBB'},
    'separators-w1': {'channel_separators': 'S'},
    'separators-w4-all': {'channel_width_units': 4, 'channel_separators': 'SSSSSSSS'},
    'filament-ok': {'filament_show': True, 'filament_depth': 0.2},
    'filament-w4-x7': {'filament_show': True, 'channel_width_units': 4, 'filament_depth': 0.2,
                       'filament_repeat': 7, 'filament_spacing': 6},
    'filament-d4': {'filament_show': True, 'filament_diameter': 4, 'filament_depth': 1.9},
}


def _cutters(values):
    v = m.SPEC.resolve_values(values)
    w, _, h = m.dimensions(v)
    return cord_cutouts(w, h, number=v['number_of_cord_cutouts'], side=v['cord_side_cutouts'],
                        cutout_width=v['cord_cutout_width'], spacing=v['distance_between_cutouts'],
                        shift=v['shift_cutouts'])


def edge_inventory(part, values):
    """Every edge with a >= 1 degree turn, by family; anything else fails.

    end face: the cut channel ends butt against the next part (mating).
    grip: rails, nubs, ramps and wall tops face the board (openGrid mating).
    bed chamfer: the author's 4 mm 45 degree exterior chamfer, the only
      edges the user sees when the channel is mounted (turn 45 degrees).
    interior: inside the U, facing the board (hidden; cables run here).
    cutout / label / filament / flare: the author's cord exits, glyph and
      groove edges and flare reliefs stay sharp (inventoried author edges).
    """
    v = m.SPEC.resolve_values(values)
    w, length, h = m.dimensions(v)
    cuts = [cut.bounding_box() for cut in _cutters(values)]
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
        x, y, z = abs(mid.X), mid.Y, mid.Z
        bb = edge.bounding_box()
        if any(b.min.X - .05 <= mid.X <= b.max.X + .05 and b.min.Y - .05 <= y <= b.max.Y + .05
               and b.min.Z - .05 <= z <= b.max.Z + .05 for b in cuts):
            family = 'cutout'
        elif abs(abs(y) - length/2) < 1e-4 and abs(bb.max.Y - bb.min.Y) < 1e-4:
            family = 'end face'
        elif v['add_label'] and z <= v['text_depth'] + 1e-4:
            family = 'label'
        elif v['filament_show'] and z <= c.SNAP_WALL:
            family = 'filament'
        elif z >= h - c.BASE_HEIGHT - 1e-4:
            family = 'grip'
        elif v['grip_flare'] > 0 and z >= c.TOP_CHAMFER - 1e-4 and x >= w/2 - c.SNAP_WALL - .02:
            family = 'flare'
        elif (abs(z) < 1e-4 and abs(x - (w/2 - c.TOP_CHAMFER)) < 1e-4) or \
                (abs(z - c.TOP_CHAMFER) < 1e-4 and abs(x - w/2) < 1e-4):
            family = 'bed chamfer'
            worst = max(worst, angle)
        elif x <= w/2 - c.SNAP_WALL + 1e-4 and z >= c.SNAP_WALL - 1e-4:
            family = 'interior'
        else:
            family = f'UNCLASSIFIED {tuple(round(q, 2) for q in mid)}'
        families[family] = families.get(family, 0) + 1
    return families, worst


@pytest.mark.audit
@pytest.mark.parametrize('name', CASES)
def test_endpoint_audit_and_edges(name):
    values = CASES[name]
    part = m.build(values)
    assert part.is_valid and len(part.solids()) == 1
    raw = pa.audit(part, m.SPEC.print_orientation, model=name)
    # Bridges are measured BEFORE any exclusion (label recess ceilings).
    assert raw.longest_bridge_mm <= pa.MAX_BRIDGE_MM
    regions = m.audit_exclusions(values)
    report = pa.audit(part, m.SPEC.print_orientation, model=name, exclusions=flat(regions))
    assert report.ok, report.format()
    families, worst = edge_inventory(part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    print(f'AUDIT | {name} | vol {part.volume:.1f} | raw wall {raw.min_wall_mm:.3f} ovh {raw.max_overhang_deg:.1f} '
          f'bridge {raw.longest_bridge_mm:.2f} | filtered wall {report.min_wall_mm:.3f} ovh '
          f'{report.max_overhang_deg:.1f} | edges worst exposed {worst:.1f} {dict(sorted(families.items()))} '
          f'| exceptions {", ".join(k for k, r in regions.items() if r) or "none"} | PASS')


def _ray_thickness(mesh, origin, direction):
    """Distance between the first two crossings of a ray (Moller-Trumbore, no rtree)."""
    o, d = np.asarray(origin, float), np.asarray(direction, float)
    d = d/np.linalg.norm(d)
    tri = mesh.triangles
    e1, e2 = tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
    p = np.cross(d, e2)
    det = (e1*p).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1/np.where(ok, det, 1), 0)
    s = o - tri[:, 0]
    u = (s*p).sum(1)*inv
    q = np.cross(s, e1)
    vv = (q*d).sum(1)*inv
    t = (e2*q).sum(1)*inv
    hit = ok & (u >= -1e-9) & (vv >= -1e-9) & (u+vv <= 1+1e-9) & (t > 1e-9)
    ts = np.unique(np.round(t[hit], 6))
    return ts[1] - ts[0]


def _part_thickness(part, origin, direction, cap=5.):
    o, d = np.asarray(origin, float), np.asarray(direction, float)/np.linalg.norm(direction)
    ts = np.arange(0, cap, 0.0005)
    inside = [part.is_inside(tuple(o + t*d)) for t in ts]
    first = inside.index(True)
    return ts[first + inside[first:].index(False)] - ts[first]


# One probe per exception family: (reference, values, origin outside the
# face, direction into the material, port/reference thickness).
W, H = 13.2, 22.
EXCEPTION_PROBES = {
    # Grip-end wedge: the 45 degree ramp at the -Y end of cell 0, 0.6 mm in
    # from the outer face, marched along the ramp's inward normal.
    'grip-end-wedge': ('i-1x5-h22', {}, (W-.6, -63.5+.6-.05/sqrt(2), 20.6+.05/sqrt(2)), (0, 1, -1), .6465),
    # Flare slit fin: the slit's inner face at z=4.4, marched outward... into
    # the fin toward the inset chamfer (-X on the +X wall).
    'flare-slit-fin': ('i-1x5-h22-flare5', {'grip_flare': 5}, (W-2.015+.05, -63.7, 4.4), (-1, 0, 0), .413),
    # Flare slit floor: 0.6 mm in from the outer face, down to the chamfer.
    'flare-slit-floor': ('i-1x5-h22-flare5', {'grip_flare': 5}, (W-.6, -63.7, 4.05), (0, 0, -1), .6),
    # Cutout sill: 0.5 mm in from the outer face under the cut floor.
    'cutout-sill': ('i-1x5-h22-cutouts', {'number_of_cord_cutouts': 2}, (W-.5, 14, 4.05), (0, 0, -1), .5),
    # Label recess: the glyph ceiling sits at text_depth over a stroke of 'C'.
    'label-recess': ('i-1x5-h22-label', {'add_label': True}, None, (0, 0, 1), .2),
}


@pytest.mark.parametrize('family', EXCEPTION_PROBES)
def test_exception_probe_matches_reference(family):
    name, values, origin, direction, expected = EXCEPTION_PROBES[family]
    ref = reference(name)
    part = m.build(values)
    if family == 'label-recess':
        # A ceiling point: deepest port face inside the slab.
        region = m.audit_exclusions(values)['label-recess'][0]
        ceiling = [f for f in part.faces() if abs(f.center().Z - .2) < 1e-6
                   and region.is_inside(f.center())]
        p = ceiling[0].center()
        assert part.is_inside((p.X, p.Y, .3)) and not part.is_inside((p.X, p.Y, .1))
        d = ref.vertices[np.abs(ref.vertices[:, 2] - .205) < 1e-3]
        assert len(d), 'reference glyph ceiling at text depth + Nudge/2'
        print(f'EXCEPTION | {family} | port ceiling z=0.200 | reference ceiling z=0.205 (Nudge)')
        return
    port_t = _part_thickness(part, origin, direction)
    ref_t = _ray_thickness(ref, np.asarray(origin) + REF_SHIFT, direction)
    assert port_t == pytest.approx(expected, abs=.005)
    assert ref_t == pytest.approx(port_t, abs=.01)
    print(f'EXCEPTION | {family} | {name} | point {origin} dir {direction} | port {port_t:.3f} ref {ref_t:.3f}')


@pytest.mark.parametrize('values,family,count', [
    ({}, 'grip-end-wedge', 20), ({'suppress_connectors': 'LRSNB'}, 'grip-end-wedge', 12),
    ({'grip_flare': 5}, 'flare-slit-fin', 20), ({'suppress_connectors': 'SNLNR', 'grip_flare': 5}, 'flare-slit-fin', 12),
    ({'number_of_cord_cutouts': 2}, 'cutout-sill', 4), ({'number_of_cord_cutouts': 3, 'cord_side_cutouts': 'Left Side',
                                                          'distance_between_cutouts': 28, 'shift_cutouts': 14}, 'cutout-sill', 3),
    ({'number_of_cord_cutouts': 2, 'cord_side_cutouts': 'Left Side Top'}, 'cutout-sill', 0),
    ({'add_label': True}, 'label-recess', 1), ({}, 'label-recess', 0),
])
def test_exception_membership(values, family, count):
    assert len(m.audit_exclusions(values)[family]) == count


@pytest.mark.parametrize('values', [{}, {'grip_flare': 5}, {'number_of_cord_cutouts': 2}, {'add_label': True}])
def test_exclusions_still_reject_a_new_thin_fin(values):
    from build123d import Box, Pos
    part = m.build(values) + Pos(0, 30, 2 + 2)*Box(.4, 6, 4)  # a 0.4 mm fin on the floor
    report = pa.audit(part, m.SPEC.print_orientation, exclusions=flat(m.audit_exclusions(values)))
    assert report.min_wall_mm < pa.MIN_WALL_MM


def test_label_uses_inter_bold_at_openscad_size():
    from labels.label_text import FONT_PATH, load_font
    assert load_font(FONT_PATH)
    ref = reference('i-1x5-h22-label')
    v = ref.vertices[np.abs(ref.vertices[:, 2] - .205) < 1e-3]
    region = m.audit_exclusions({'add_label': True})['label-recess'][0].bounding_box()
    assert region.size.X - .02 == pytest.approx(np.ptp(v[:, 0]), abs=.05)   # glyph height 10.39
    assert region.size.Y - .02 == pytest.approx(np.ptp(v[:, 1]), rel=.01)   # text length


# --- cross-file module identity ---------------------------------------------------

HASHES = json.loads((Path(__file__).with_name('underware_module_hashes.json')).read_text())
EXPECTED_DIVERGENCES = {
    # Junction/path files drop the separators and filament blocks (L) or keep
    # the older inline profile (X); bridge/height_change raise the flared rail
    # by topChamfer; the text label plate offsets its grip by a clearance.
    'monokiniChannel': 11, 'monokiniGrip': 1, 'monokiniGripFlared': 3, 'monokiniGripFlaredCut': 1,
    'monokini_offset_profile': 0, 'monokini_midline_points': 0, 'monokini_midline_rects': 0,
}


def test_module_hash_table_records_divergences():
    assert len(HASHES['files']) == 13
    assert {k: len(v) for k, v in HASHES['divergences'].items()} == EXPECTED_DIVERGENCES
    ref = HASHES['files']['monokini_I_channel.scad']['modules']
    assert set(ref) == set(EXPECTED_DIVERGENCES)
    notice = (ASSETS / 'NOTICE').read_text()
    for name, entry in HASHES['files'].items():
        assert entry['sha256'] in notice, name


@pytest.mark.skipif(not STAGED.is_dir(), reason='staged Underware sources not present '
                    '(set UNDERWARE_SOURCE_DIR); the committed hash table is still checked')
def test_module_hashes_match_staged_sources():
    sys.path.insert(0, str(ROOT / 'scripts'))
    from underware_module_hashes import table
    assert table(STAGED) == HASHES
