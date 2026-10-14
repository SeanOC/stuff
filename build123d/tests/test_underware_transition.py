"""Underware for openGrid transitions port (pst-fsk8s.4).

References: assets/underware-opengrid/NOTICE (OpenSCAD 2025.06.12.ai25773,
BOSL2 b86a7584). The author's sources are not committed (CC BY-NC-SA, epic
pst-fsk8s D0 outcome (b)).
"""
from __future__ import annotations

import hashlib
import sys
from math import acos, degrees, hypot
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import Box, Pos

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holders import underware_transition as m
from tests import print_audit as pa
from tests.parity import load_reference, mesh_from_part, sample_surface
from underware import constants as c
from underware import transition as t
from underware.profile import monokini_profile, monokini_profile_points

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT.parent / 'assets' / 'underware-opengrid'
# The mayor's pre-flight renders (city assets/incoming/underware-ref/SHA256SUMS).
MAYOR = {
    'width-change.stl': '5fde987cc4d332757a401264fb935c5a24bd67b91bd08cfd6a2ba039c0c670f2',
    'height-change.stl': 'f91452f49b78142323f9037f65e467dca8ac0116838a6f2cb23d4718f57f4bc7',
    'bridge.stl': '2ad232b6ba44811d466b5de5138144d76be4c45216821458c5f3651f0be5bcc2',
}
W1 = c.channel_width(1)


def flat(regions):
    return [r for family in regions.values() for r in family]


def test_mayor_transition_meshes_match_baselines():
    sums = {name: digest for digest, name in
            (line.split('  ') for line in (ASSETS / 'SHA256SUMS').read_text().splitlines())}
    for name, digest in MAYOR.items():
        assert sums[f'mesh/{name}'] == digest, f'{name} drifted from the mayor baseline'
        assert hashlib.sha256((ASSETS / 'mesh' / name).read_bytes()).hexdigest() == digest


# --- parity ------------------------------------------------------------------

def _grips(kind, **kw):
    """(y, side, flared, width, dx, dz, height) per grip for a library case."""
    if kind == 'width':
        return [(y, s, f, w, dx, 0., kw['height']) for y, s, f, w, dx in t.width_change_grips(
            kw['length'], kw['rise'], kw['from_width'], kw['to_width'], kw['height'],
            kw.get('suppress', ''), kw.get('grip_flare', 0.))]
    top = max(kw['from_height'], kw['to_height'])
    return [(y, s, False, kw['width'], 0., 0., top) for y, s, *_ in t.height_change_grips(
        kw['length'], kw['rise'], kw['width'], kw['from_height'], kw['to_height'], kw.get('suppress', ''))]


def reference_artefacts(points, grips, seam=None):
    """Reference surface with no solid behind it (NOTICE "Frames").

    grip-base: unflared grips are separate CGAL volumes on the wall top, so
      their bases (u 0.7..2 at z = h-3.4 inside each grip's y-range) are
      internal faces.
    ramp-skin: flared grips keep a zero-thickness sheet over each end ramp.
    seam: the bridge end pieces' first profile overlaps the run end by 0.005.
    """
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    mask = np.zeros(len(points), bool)
    for gy, side, flared, w, dx, dz, h in grips:
        along = np.abs(y - gy) <= c.GRIP_SIZE/2 + 0.006   # bridge end pieces sit 0.005 inward
        u = w/2 - side*(x - dx)
        if flared:
            near_end = np.abs(np.abs(y - gy) - c.GRIP_SIZE/2) <= c.GRIP_RAMP + 0.006
            mask |= (np.abs(z - (dz + h)) < 1e-3) & along & near_end & (u < c.SNAP_WALL)
        else:
            mask |= (np.abs(z - (h - c.BASE_HEIGHT)) < 1e-3) & along & (u >= c.SNAP_CAPTURE - 1e-3) \
                & (u <= c.SNAP_WALL + 1e-3)
    if seam is not None:
        mask |= np.abs(np.abs(y) - seam) <= 0.006
    return mask


def _bridge_grips(width, from_height, over, ends, flare=0.):
    off = over - from_height
    return [(y, s, flare > 0, width, 0., off if flare > 0 else 0., from_height if flare > 0 else over)
            for y in ends for s in (1, -1)]


# Mayor meshes: the library at the author's defaults (off-grid heights,
# Rise_Distance 25 mm), outside the registered domain.
LIBRARY = {
    'width-change': (lambda: t.width_change_channel(84, 28, W1, W1, 18),
                     lambda: _grips('width', length=84, rise=28, from_width=W1, to_width=W1, height=18), None),
    'height-change': (lambda: t.height_change_channel(84, 25, W1, 18, 12),
                      lambda: _grips('height', length=84, rise=25, width=W1, from_height=18, to_height=12), None),
    'bridge': (lambda: t.bridge_channel(W1, 22, 22, 22, 1),
               lambda: _bridge_grips(W1, 22, 44, (28, -28)), 14.),
}
# Worker renders -> registered values (NOTICE commands).
PARITY = {
    'wc-1to2-h22': {},
    'wc-2to1-l4-r2-h28-flare5': {'from_width_units': 2, 'to_width_units': 1, 'channel_length_units': 4,
                                 'transition_length_units': 2, 'from_height': 28, 'grip_flare': 5},
    'wc-1to2-l5-cutout': {'channel_length_units': 5, 'number_of_cord_cutouts': 1, 'shift_cutouts': 28,
                          'suppress_connectors': 'NBNNN'},
    'hc-22to34': {'part': 'height_change', 'from_height': 22, 'to_height': 34},
    'hc-34to16-l4-r2': {'part': 'height_change', 'from_height': 34, 'to_height': 16,
                        'channel_length_units': 4, 'transition_length_units': 2, 'suppress_connectors': 'NLRB'},
    'bridge-to28': {'part': 'bridge'},
    'bridge-half-l2-b28-f16-t22-flare5': {'part': 'bridge', 'half_bridge': True, 'bridge_length_units': 2,
                                          'bridge_height': 28, 'from_height': 16, 'to_height': 22,
                                          'grip_flare': 5},
}


def _registered(name):
    values = PARITY[name]
    v = m.SPEC.resolve_values(values)
    seam = None
    if v['part'] == 'bridge':
        seam = t.bridge_run_length(v['bridge_length_units'], v['half_bridge'])/2
    return (lambda: m.build(values)), (lambda: m.grip_list(v)), seam


def _profile_area(width, height):
    return monokini_profile(width, height).area


# Reference minus port volume: each bridge end piece overlaps the run by
# 0.005 mm in the reference (the port butts them), so the reference is short
# by 0.005 mm of the run profile per end; the cutout's $fn=50 cylinder
# removes less.
REDUCTION = {
    'bridge': -0.01*_profile_area(W1, 44),
    'bridge-to28': -0.01*_profile_area(W1, 50),
    'bridge-half-l2-b28-f16-t22-flare5': -0.005*_profile_area(W1, 50),
}
VOLUME_TOL = {'wc-1to2-l5-cutout': 1.5}


@pytest.mark.parametrize('name', [*LIBRARY, *PARITY])
def test_reference_parity(name, tmp_path):
    build, grips, seam = LIBRARY[name] if name in LIBRARY else _registered(name)
    part = build()
    ref = load_reference(ASSETS / 'mesh' / f'{name}.stl')
    if seam is None:
        ref.apply_translation((0, 0.005, 0))  # the skin spans y -L/2-0.005 .. L/2-0.005
    port = mesh_from_part(part, tmp_path / 'port.stl', tolerance=0.002, angular_tolerance=0.05)
    box = part.bounding_box()
    assert (box.min.X, box.max.X, box.min.Z, box.max.Z) == pytest.approx(
        (ref.bounds[0][0], ref.bounds[1][0], ref.bounds[0][2], ref.bounds[1][2]), abs=1e-3)
    assert (box.min.Y, box.max.Y) == pytest.approx((ref.bounds[0][1], ref.bounds[1][1]), abs=0.0051)
    reduction = REDUCTION.get(name, 0.)
    assert ref.volume - part.volume == pytest.approx(reduction, abs=VOLUME_TOL.get(name, 0.05))
    out = {}
    for label, a, b in (('port->ref', port, ref), ('ref->port', ref, port)):
        points, _ = sample_surface(a, n=20000, seed=7, sampler='even')
        points = np.vstack([points, a.vertices])
        d = trimesh.proximity.closest_point(b, points)[1]
        skip = reference_artefacts(points, grips(), seam) if a is ref else np.zeros(len(points), bool)
        out[label] = (d[~skip].max(), skip.mean())
        assert d[~skip].max() <= 0.02, (label, d[~skip].max())
    print(f'PARITY | {name} | ref vol {ref.volume:.2f} port {part.volume:.2f} reduction {reduction:.2f} | '
          + ' | '.join(f'{k} max {v[0]:.4f} artefact {100*v[1]:.2f}%' for k, v in out.items()))


# --- invariants ----------------------------------------------------------------

def _slab(part, y, dy=1e-3):
    return part & Pos(0, y + dy/2, 0)*Box(400, dy, 400)


def _expected_slab(width, height, dx, dz, y, dy=1e-3):
    from build123d import extrude
    return Pos(dx, y, dz)*extrude(monokini_profile(width, height), dy, dir=(0, 1, 0))


END_CASES = {
    'widen': ({}, ((2, 22, 0., 0.), (1, 22, 14., 0.))),
    'narrow-r2-h28': ({'from_width_units': 2, 'to_width_units': 1, 'channel_length_units': 4,
                       'transition_length_units': 2, 'from_height': 28}, ((1, 28, 14., 0.), (2, 28, 0., 0.))),
    'widen-1to4-r2': ({'to_width_units': 4, 'transition_length_units': 2, 'channel_length_units': 4},
                      ((4, 22, 0., 0.), (1, 22, 42., 0.))),
    'raise': ({'part': 'height_change', 'from_height': 22, 'to_height': 34},
              ((1, 34, 0., 0.), (1, 22, 0., 12.))),
    'lower-72-10': ({'part': 'height_change', 'from_height': 72, 'to_height': 10, 'from_width_units': 2,
                     'channel_length_units': 4, 'transition_length_units': 3},
                    ((2, 10, 0., 62.), (2, 72, 0., 0.))),
    'bridge': ({'part': 'bridge'}, ((1, 22, 0., 28.), (1, 22, 0., 28.))),
}


@pytest.mark.parametrize('name', END_CASES)
def test_ends_match_the_plain_profile(name):
    """Both end stations are the I channel's plain monokini profile at that
    end's size (-Y end first), placed where the transition puts it. The
    1 um slab bounds the error of a ramp that starts at the end (the bridge:
    1.3e-5 mm3 of 0.11 mm3)."""
    values, ends = END_CASES[name]
    part = m.build(values)
    _, length, _ = m.dimensions(m.SPEC.resolve_values(values))
    for (units, height, dx, dz), y in zip(ends, (-length/2, length/2 - 1e-3)):
        got = _slab(part, y)
        want = _expected_slab(c.channel_width(units), height, dx, dz, y)
        assert got.volume == pytest.approx(want.volume, rel=1e-3), (name, y)
        assert (got - want).volume < 1e-3*want.volume and (want - got).volume < 1e-3*want.volume, (name, y)


GRIP_PROBES = {  # (u inward from the outer face, z below the grip top): solid?
    'nub tip': (0.1, 0.7, True),
    'undercut': (0.35, 2.7, False),
    'rail': (1.35, 2.7, True),
}


@pytest.mark.parametrize('values,expected', [
    ({}, {'front': 2, 'middle': 0, 'back': 2}),
    ({'channel_length_units': 5, 'suppress_connectors': 'NLRBS'}, {'front': 3, 'middle': 0, 'back': 2}),
    ({'part': 'height_change'}, {'front': 2, 'middle': 2, 'back': 2}),
    ({'part': 'height_change', 'suppress_connectors': 'LRB'}, {'front': 1, 'middle': 1, 'back': 0}),
    ({'part': 'bridge'}, {'end': 4}),
    ({'part': 'bridge', 'suppress_connectors': 'B,L'}, {'end': 1}),
    ({'part': 'bridge', 'half_bridge': True}, {'end': 2}),
])
def test_grips_per_cell(values, expected):
    """Every listed grip is present where its section puts it, and the cell
    regions carry the author's counts ([W] none on rise cells, [H] all)."""
    v = m.SPEC.resolve_values(values)
    part = m.build(values)
    grips = m.grip_list(v)
    if v['part'] == 'bridge':
        assert {'end': len(grips)} == expected
    else:
        length = v['channel_length_units']*c.GRID
        regions = dict(t.cell_regions(length, v['transition_length_units']*c.GRID))
        counts = {'front': 0, 'middle': 0, 'back': 0}
        for y, *_ in grips:
            counts[regions[y]] += 1
        assert counts == expected
    for y, side, flared, w, dx, dz, h in grips:
        for name, (u, below, solid) in GRIP_PROBES.items():
            point = (dx + side*(w/2 - u), y, dz + h - below)
            assert part.is_inside(point) == solid, (values, y, side, name)


@pytest.mark.parametrize('preset', [p.id for p in m.SPEC.presets])
def test_presets_are_single_valid_watertight_solids(preset, tmp_path):
    part = m.build(next(p.values for p in m.SPEC.presets if p.id == preset))
    assert part.is_valid and len(part.solids()) == 1
    mesh = mesh_from_part(part, tmp_path / 'p.stl', tolerance=0.01, angular_tolerance=0.1)
    assert mesh.is_watertight
    print(f'VOLUME | {preset} | {part.volume:.1f} mm3')


def test_height_change_grip_plane_is_level():
    """[H] keeps every wall top at max(height) - 3.4: the floor steps, the
    openGrid plane does not (the part has no lip that climbs)."""
    part = m.build({'part': 'height_change', 'from_height': 10, 'to_height': 34,
                    'channel_length_units': 4, 'transition_length_units': 1})
    for y in np.linspace(-55, 55, 23):
        assert part.is_inside((W1/2 - 1, y, 34 - c.BASE_HEIGHT - 0.05))
        assert not part.is_inside((W1/2 - 1, y, 34 - c.BASE_HEIGHT + 0.05)) or \
            any(abs(y - yc) <= c.GRIP_SIZE/2 for yc, *_ in t.cell_regions(112, 28))


# --- named errors ----------------------------------------------------------------

@pytest.mark.parametrize('values,message', [
    ({'from_height': 18}, 'from_height 18 mm is off the 6 mm height steps'),
    ({'to_height': 68}, 'to_height 68 mm is off the 6 mm height steps'),
    ({'bridge_height': 12}, 'bridge_height 12 mm is off'),
    ({'grip_flare': 10}, 'grip_flare above 9.9 degrees'),
    ({'suppress_connectors': 'X'}, 'unknown code(s) X'),
    ({'suppress_connectors': 'NNNN'}, 'has 4 codes but the channel has only 3'),
    ({'channel_length_units': 1}, 'leaves no straight end'),
    ({'transition_length_units': 3}, 'leaves no straight end'),
    ({'to_width_units': 3}, 'slants the -X wall to 0.89 mm'),
    ({'from_width_units': 4, 'to_width_units': 1, 'transition_length_units': 1}, 'slants the -X wall to 0.63 mm'),
    ({'number_of_cord_cutouts': 1}, 'reaches the 28 mm transition'),
    ({'number_of_cord_cutouts': 1, 'shift_cutouts': 28}, 'crosses the grip at y=-28 mm on the +X wall'),
    ({'number_of_cord_cutouts': 12, 'channel_length_units': 11}, 'runs past the 308 mm channel end'),
    ({'number_of_cord_cutouts': 2, 'distance_between_cutouts': 56, 'channel_length_units': 5,
      'suppress_connectors': 'NBNBN', 'cord_side_cutouts': 'Right Side'}, 'misses the narrow end'),
    ({'number_of_cord_cutouts': 3, 'distance_between_cutouts': 56}, 'runs past the 84 mm channel end'),
    ({'add_label': True}, 'runs off the closed face'),
    ({'add_label': True, 'text_depth': 0}, 'text_depth 0 makes no label'),
    ({'part': 'height_change', 'from_height': 10, 'to_height': 72}, 'slopes the floor more than 45'),
    ({'part': 'height_change', 'number_of_cord_cutouts': 1}, 'height_change prints standing on end'),
    ({'part': 'height_change', 'add_label': True}, 'height_change prints standing on end'),
    ({'part': 'height_change', 'grip_flare': 5}, 'height_change prints standing on end'),
    ({'part': 'height_change', 'channel_length_units': 1}, 'leaves no straight end'),
    ({'part': 'bridge', 'to_height': 22}, 'ramp undersides 51.8 degrees from vertical'),
    ({'part': 'bridge', 'to_height': 40, 'bridge_height': 40}, 'tilts its 2 mm floor to 0.87 mm'),
    ({'part': 'bridge', 'suppress_connectors': 'N,N,N'}, 'a bridge takes two comma fields'),
    ({'part': 'bridge', 'suppress_connectors': 'NN'}, 'has 2 codes but the channel has only 1'),
    ({'part': 'bridge', 'number_of_cord_cutouts': 2}, 'leaves the bridge run'),
    ({'part': 'bridge', 'number_of_cord_cutouts': 1, 'from_height': 34, 'bridge_height': 10,
      'to_height': 28}, 'below the 52 mm wall top'),
    ({'part': 'bridge', 'half_bridge': True, 'add_label': True}, 'halve the centred label'),
])
def test_named_errors(values, message):
    with pytest.raises(ValueError) as exc:
        m.build(values)
    assert message in str(exc.value)


# --- print audit, exceptions and edges -------------------------------------------

CASES = {
    # width_change (base-down)
    'wc-default': {},
    'wc-narrow': {'from_width_units': 2, 'to_width_units': 1},
    'wc-straight-1': {'to_width_units': 1},
    'wc-4to3': {'from_width_units': 4, 'to_width_units': 3},
    'wc-1to4-r2': {'to_width_units': 4, 'transition_length_units': 2, 'channel_length_units': 4},
    'wc-max-corner': {'from_width_units': 4, 'to_width_units': 1, 'transition_length_units': 2,
                      'channel_length_units': 11, 'from_height': 72},
    'wc-l2': {'channel_length_units': 2},
    'wc-l11-r10': {'channel_length_units': 11, 'transition_length_units': 10},
    'wc-h10': {'from_height': 10},
    'wc-h72': {'from_height': 72},
    'wc-flare-9.9': {'grip_flare': 9.9},
    'wc-flare5-narrow-r2-h28': PARITY['wc-2to1-l4-r2-h28-flare5'],
    'wc-suppress-mixed-flare': {'suppress_connectors': 'SNL', 'grip_flare': 5},
    'wc-suppress-all': {'suppress_connectors': 'BBB'},
    'wc-cutout': PARITY['wc-1to2-l5-cutout'],
    'wc-cutout-left-narrow-w20': {'channel_length_units': 5, 'number_of_cord_cutouts': 2,
                                  'distance_between_cutouts': 56, 'cord_side_cutouts': 'Left Side',
                                  'cord_cutout_width': 20, 'suppress_connectors': 'NBNBN'},
    'wc-cutout-w6-flare': {'channel_length_units': 5, 'number_of_cord_cutouts': 1, 'shift_cutouts': 28,
                           'cord_cutout_width': 6, 'suppress_connectors': 'NBNNN', 'grip_flare': 9.9},
    'wc-label-straight': {'to_width_units': 1, 'add_label': True},
    'wc-label-s16-d1-w4': {'from_width_units': 4, 'to_width_units': 4, 'add_label': True,
                           'channel_length_units': 4, 'text_size': 16, 'text_depth': 1},
    # height_change (standing on its lower end)
    'hc-default': {'part': 'height_change'},
    'hc-raise-22-34': {'part': 'height_change', 'from_height': 22, 'to_height': 34},
    'hc-lower-34-22': {'part': 'height_change', 'from_height': 34, 'to_height': 22},
    'hc-10-72-r3-l4': {'part': 'height_change', 'from_height': 10, 'to_height': 72,
                       'transition_length_units': 3, 'channel_length_units': 4},
    'hc-72-10-r3-l4': {'part': 'height_change', 'from_height': 72, 'to_height': 10,
                       'transition_length_units': 3, 'channel_length_units': 4},
    'hc-10-16': {'part': 'height_change', 'from_height': 10, 'to_height': 16},
    'hc-same-72': {'part': 'height_change', 'from_height': 72, 'to_height': 72},
    'hc-w4-l11-22-46': {'part': 'height_change', 'from_width_units': 4, 'channel_length_units': 11,
                        'from_height': 22, 'to_height': 46},
    'hc-l2': {'part': 'height_change', 'channel_length_units': 2},
    'hc-suppress': {'part': 'height_change', 'suppress_connectors': 'NLR'},
    'hc-suppress-all': {'part': 'height_change', 'suppress_connectors': 'BBB'},
}
# The rev 4 §8 parameter cases for the height-change step patches.
STEP_PATCH_CASES = ('hc-raise-22-34', 'hc-default', 'hc-10-72-r3-l4', 'hc-72-10-r3-l4')


def _frame(values):
    return m.print_frame(m.SPEC.resolve_values(values))


def _envelope(values):
    """The channel with its U filled to the wall top: faces whose outward
    normal leaves it are on the outside of the part."""
    v = m.SPEC.resolve_values(values)
    width, length, height = m.dimensions(v)
    if v['part'] == 'width_change':
        a = (c.channel_width(v['from_width_units']), height, (width - c.channel_width(v['from_width_units']))/2, 0.)
        b = (c.channel_width(v['to_width_units']), height, (width - c.channel_width(v['to_width_units']))/2, 0.)
    else:
        a = (width, v['from_height'], 0., height - v['from_height'])
        b = (width, v['to_height'], 0., height - v['to_height'])
    rise = v['transition_length_units']*c.GRID

    def outer(section, y):
        w, h, dx, dz = section
        return [pt for pt in t._points(w, h, y, dx, dz)][:6]
    stations = [(-length/2, b), (-rise/2, b), (rise/2, a), (length/2, a)]
    body = None
    for (y0, s0), (y1, s1) in zip(stations, stations[1:]):
        seg = t._ruled_segment(outer(s0, y0), outer(s1, y1))
        body = seg if body is None else body + seg
    return body


def edge_inventory(part, values):
    """Every edge with a >= 1 degree turn, by family; anything else fails.

    end face: the channel ends butt against the next part (mating).
    grip: wall tops, rails, nubs and ramps face the board (openGrid mating).
    flare / cutout / label: the author's reliefs, cord exits and glyphs.
    exterior: both faces on the outside of the U (the author's 45 degree
      chamfers and the rise seams where the transition turns the outside;
      the edges a user sees, left as the author drew them).
    interior: both faces inside the U (cables run here, facing the board).
    """
    v = m.SPEC.resolve_values(values)
    width, length, height = m.dimensions(v)
    envelope = _envelope(values)
    cuts = [cut.bounding_box() for cut in t.side_cutouts(width, height, **m._cut_args(v))]
    # Each flared grip: the sheared rail and its two relief slits, on its own
    # (possibly offset or lifted) wall.
    flares = []
    for gy, side, flared, w, dx, dz, h in m.grip_list(v):
        if flared:
            x = dx + side*w/2
            reach = c.SNAP_WALL + h*np.tan(np.radians(v['grip_flare'])) + 1
            half = c.GRIP_SIZE/2 + c.FLARE_SLIT + .05
            flares.append((x - reach, x + reach, gy - half, gy + half, dz + c.TOP_CHAMFER - .05, dz + h + .05))
    adjacent = {}
    for face in part.faces():
        for edge in face.edges():
            adjacent.setdefault(edge, []).append(face)

    def outside(face, at):
        n = face.normal_at(at)
        probe = at + n*0.05
        return not envelope.is_inside(probe)
    families, worst = {}, 0.
    for edge, faces in adjacent.items():
        if len(faces) != 2:
            continue
        mid = edge.position_at(.5)
        angle = degrees(acos(max(-1., min(1., faces[0].normal_at(mid).dot(faces[1].normal_at(mid))))))
        if angle < 1:
            continue
        bb = edge.bounding_box()
        if any(b.min.X - .05 <= mid.X <= b.max.X + .05 and b.min.Y - .05 <= mid.Y <= b.max.Y + .05
               and b.min.Z - .05 <= mid.Z <= b.max.Z + .05 for b in cuts):
            family = 'cutout'
        elif abs(abs(mid.Y) - length/2) < 1e-4 and bb.max.Y - bb.min.Y < 1e-4:
            family = 'end face'
        elif v['add_label'] and mid.Z <= v['text_depth'] + 1e-4:
            family = 'label'
        elif mid.Z >= height - c.BASE_HEIGHT - 1e-4:
            family = 'grip'
        elif any(x0 <= mid.X <= x1 and y0 <= mid.Y <= y1 and z0 <= mid.Z <= z1
                 for x0, x1, y0, y1, z0, z1 in flares):
            family = 'flare'
        else:
            out = [outside(f, mid) for f in faces]
            if all(out):
                family = 'exterior'
                worst = max(worst, angle)
            elif not any(out):
                family = 'interior'
            else:
                family = f'UNCLASSIFIED {tuple(round(q, 2) for q in mid)}'
        families[family] = families.get(family, 0) + 1
    return families, worst


def _down_faces(part, frame):
    """Planar faces off the bed steeper than 45 degrees from vertical in the
    print frame: (area, short extent, angle, centre)."""
    placed = frame*part
    zmin = placed.bounding_box().min.Z
    out = []
    for face in placed.faces():
        if face.geom_type.name != 'PLANE':
            continue
        n = face.normal_at(face.center())
        probe = face.center() + n*0.01
        if placed.is_inside(probe):
            n = -n
        if n.Z >= -pa._DOWN_EPS or face.bounding_box().max.Z <= zmin + 1e-4:
            continue
        angle = degrees(np.arcsin(min(1., -n.Z)))
        if angle <= pa.MAX_OVERHANG_DEG + pa._ANGLE_TOL_DEG:
            continue
        bb = face.bounding_box()
        dims = sorted([bb.size.X, bb.size.Y, bb.size.Z])
        out.append((face.area, dims[1], angle, face.center()))
    return out


@pytest.mark.audit
@pytest.mark.parametrize('name', CASES)
def test_endpoint_audit_and_edges(name):
    values = CASES[name]
    v = m.SPEC.resolve_values(values)
    part = m.build(values)
    assert part.is_valid and len(part.solids()) == 1
    frame = _frame(values)
    raw = pa.audit(part, print_frame=frame, model=name)
    regions = m.audit_exclusions(values)
    report = pa.audit(part, print_frame=frame, model=name, exclusions=flat(regions))
    assert report.ok, report.format()
    # Bridges are measured BEFORE any exclusion: the standing step patches
    # are <= 1.5 mm; a label recess ceiling is bounded by the audit's own
    # limit (its glyph counters span up to ~4.3 mm).
    assert raw.longest_bridge_mm <= (pa.MAX_BRIDGE_MM if v['add_label'] else 1.5)
    families, worst = edge_inventory(part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    print(f'AUDIT | {name} | vol {part.volume:.1f} | raw wall {raw.min_wall_mm:.3f} ovh {raw.max_overhang_deg:.1f} '
          f'bridge {raw.longest_bridge_mm:.2f} | filtered wall {report.min_wall_mm:.3f} ovh '
          f'{report.max_overhang_deg:.1f} bridge {report.longest_bridge_mm:.2f} | edges worst exposed '
          f'{worst:.1f} {dict(sorted(families.items()))} | exceptions '
          f'{", ".join(f"{k}:{len(r)}" for k, r in regions.items() if r) or "none"} | PASS')


@pytest.mark.audit
@pytest.mark.parametrize('name', STEP_PATCH_CASES)
def test_step_patch_row(name):
    """rev 4 §8 height-change step patches: >= 1 and <= 8 faces totalling <=
    40 mm2, each down-facing planar, short extent <= 1.5 mm, area <= 10 mm2;
    every down-facing face off the bed in the standing frame is one of them
    (exactly one per grip: the 1.30 x 1.40 mm rail end), and nothing else."""
    values = CASES[name]
    v = m.SPEC.resolve_values(values)
    part = m.build(values)
    frame = _frame(values)
    regions = [frame*r for r in m.audit_exclusions(values)['height-change-step-patch']]
    down = _down_faces(part, frame)
    inside = [f for f in down if any(r.is_inside(f[3]) for r in regions)]
    assert inside == down, [f for f in down if f not in inside]
    assert 1 <= len(down) <= 8 and len(down) == len(m.grip_list(v))
    assert sum(f[0] for f in down) <= 40
    for area, short, angle, _ in down:
        assert short <= 1.5 and area <= 10
        assert area == pytest.approx((c.SNAP_WALL - c.SNAP_CAPTURE)*(c.BASE_HEIGHT - c.GRIP_RAMP), abs=1e-6)
        assert short == pytest.approx(c.SNAP_WALL - c.SNAP_CAPTURE, abs=1e-6)
        assert angle == pytest.approx(90, abs=1e-6)
    raw = pa.audit(part, print_frame=frame, model=name)
    print(f'STEP PATCH | {name} | {len(down)} faces, {sum(f[0] for f in down):.2f} mm2, each '
          f'{down[0][0]:.2f} mm2 / {down[0][1]:.2f} mm wide / {down[0][2]:.0f} deg | raw ovh '
          f'{raw.max_overhang_deg:.1f} bridge {raw.longest_bridge_mm:.2f}')


@pytest.mark.parametrize('values', [{}, {'grip_flare': 5}, PARITY['wc-1to2-l5-cutout'],
                                    {'part': 'height_change'}])
def test_exclusions_still_reject_a_new_thin_fin(values):
    """A 0.4 mm fin away from every published envelope still fails."""
    part = m.build(values)
    v = m.SPEC.resolve_values(values)
    width, _, _ = m.dimensions(v)
    fin = Pos(0, 0, c.SNAP_WALL + 3)*Box(0.4, 6, 6)
    report = pa.audit(part + fin, print_frame=_frame(values), exclusions=flat(m.audit_exclusions(values)))
    assert not report.ok and report.min_wall_mm < 0.9


def test_no_lip_faces_in_the_fused_port():
    """rev 4's 'interlock lips' are the references' CGAL grip-base faces
    (NOTICE "Frames"); the fused width change has no down-facing face off the
    bed in its print frame."""
    for values in ({}, {'grip_flare': 5}):
        assert _down_faces(m.build(values), _frame(values)) == []


def test_jog_wall_thickness_matches_the_named_error_bound():
    """The width-change jog wall's perpendicular thickness is SNAP_WALL*R/hypot(R, jog)."""
    for units, rise in ((2, 1), (3, 2), (4, 2)):
        jog = c.channel_width(units) - W1
        expected = c.SNAP_WALL*rise*c.GRID/hypot(rise*c.GRID, jog)
        part = m.build({'to_width_units': units, 'transition_length_units': rise,
                        'channel_length_units': rise + 2})
        assert expected >= 0.9
        # March across the wall at mid-rise, normal to its face.
        wide = c.channel_width(units)
        nx, ny = rise*c.GRID/hypot(rise*c.GRID, jog), -jog/hypot(rise*c.GRID, jog)
        x0 = -wide/2 + jog/2
        start = (x0 - nx*0.5, -ny*0.5, 10.)
        inside = [part.is_inside((start[0] + nx*s, start[1] + ny*s, 10.))
                  for s in np.arange(0, expected + 1.0, 0.01)]
        assert sum(inside)*0.01 == pytest.approx(expected, abs=0.02)
