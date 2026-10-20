"""Underware for openGrid text label plate port (pst-fsk8s.6).

References: assets/underware-opengrid/NOTICE (OpenSCAD 2025.06.12.ai25773,
BOSL2 b86a7584), monokini_text_label.scad rendered with Add_Label=false: the
author's text is Raleway and the port's is Inter Bold, so parity is the plate
body and the text is a legibility test.
"""
from __future__ import annotations

import sys
from math import acos, degrees, sqrt
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holders import underware_text_label as m
from tests import print_audit as pa
from tests.audit_record import record
from tests.parity import load_reference, mesh_from_part, sample_surface
from tests.test_underware import GRIP_PROBES, _part_thickness, _ray_thickness
from underware import channel, constants as c
from underware.channel import cell_centres, present_grips
from underware.profile import monokini_profile

ASSETS = Path(__file__).resolve().parents[2] / 'assets' / 'underware-opengrid'
# Reference mesh -> port values; references span y -L/2-0.015 .. L/2-0.005.
PARITY = {
    'text-label-1x5': {},
    'text-label-2x3': {'label_width_units': 2, 'label_length_units': 3},
}
REF_SHIFT = (0, 0.005, 0)


def reference(name):
    ref = load_reference(ASSETS / 'mesh' / f'{name}.stl')
    ref.apply_translation(REF_SHIFT)
    return ref


def resolved(values):
    return m.SPEC.resolve_values(values)


def flat(regions):
    return [r for family in regions.values() for r in family]


# --- parity: the plate body ----------------------------------------------------

@pytest.mark.parametrize('name', PARITY)
def test_reference_parity(name, tmp_path):
    v = resolved(PARITY[name])
    width, length = m.dimensions(v)
    body = m.plate(width, length)
    ref = reference(name)
    # Bounds: X and Z identical; the reference is NUDGE longer at -Y.
    box = body.bounding_box()
    assert (box.min.X, box.max.X, box.min.Z, box.max.Z) == pytest.approx(
        (ref.bounds[0][0], ref.bounds[1][0], ref.bounds[0][2], ref.bounds[1][2]), abs=1e-3)
    assert (box.min.Y - ref.bounds[0][1], ref.bounds[1][1] - box.max.Y) == pytest.approx((0.01, 0.), abs=1e-3)
    # Volume: exactly the reference's extra 0.01 mm of 2 mm floor.
    nudge = 0.01*width*c.SNAP_WALL
    assert ref.volume - body.volume == pytest.approx(nudge, abs=1e-3)
    port = mesh_from_part(body, tmp_path / 'port.stl', tolerance=0.002, angular_tolerance=0.05)
    worst = {}
    for label, a, b in (('port->ref', port, ref), ('ref->port', ref, port)):
        points, _ = sample_surface(a, n=20000, seed=7, sampler='even')
        points = np.vstack([points, a.vertices])
        worst[label] = trimesh.proximity.closest_point(b, points)[1].max()
        assert worst[label] <= 0.02, (label, worst[label])
    # The finished plate adds only the bed chamfer: c^2/2 per mm of bed
    # perimeter less the 4 corner overlaps (c^3/3 each).
    finished = m.blank(v)
    k = m.BED_CHAMFER
    chamfer = k*k/2*2*(width + length) - 4*k**3/3
    assert body.volume - finished.volume == pytest.approx(chamfer, abs=1e-3)
    assert tuple(finished.bounding_box().size) == pytest.approx(tuple(box.size), abs=1e-6)
    print(f'PARITY | {name} | +y {REF_SHIFT[1]} | ref vol {ref.volume:.3f} body {body.volume:.3f} '
          f'nudge {nudge:.3f} | finished {finished.volume:.3f} chamfer {chamfer:.3f} | '
          + ' | '.join(f'{k_} max {d:.4f}' for k_, d in worst.items()))


def test_plate_reaches_the_profile_only_through_top_chamfer(monkeypatch):
    """topChamfer 0 is threaded through U1's profile, not a copied rectangle."""
    calls = []
    real = channel.monokini_profile

    def spy(width, height, top_chamfer=c.TOP_CHAMFER):
        calls.append((width, height, top_chamfer))
        return real(width, height, top_chamfer)
    monkeypatch.setattr(channel, 'monokini_profile', spy)
    m.build({'text': ''})
    assert calls == [(26.4, c.SNAP_WALL + c.BASE_HEIGHT, 0.)]
    assert monokini_profile(26.4, 5.4, 0.).area == pytest.approx(26.4*c.SNAP_WALL)
    with pytest.raises(ValueError, match='top_chamfer 1'):
        monokini_profile(26.4, 22, 1.)


@pytest.mark.parametrize('units,length', [(1, 5), (2, 3), (4, 1), (3, 11)])
def test_width_and_grips_per_cell(units, length):
    part = m.build({'label_width_units': units, 'label_length_units': length, 'text': ''})
    assert part.bounding_box().size.X == pytest.approx(26.4 + (units-1)*28, abs=1e-6)
    grips = present_grips(length*c.GRID, '')
    for side in (1, -1):
        ys = sorted(y for y, s, _ in grips if s == side)
        assert len(ys) == length
        assert np.allclose(np.diff(ys), c.GRID)


def test_grip_probe():
    """U1's grip probes on every cell of the plate: nub, undercut, rail, floor."""
    part = m.build({})
    w, _ = m.dimensions(resolved({}))
    h = m.PLATE_HEIGHT
    for y in cell_centres(140):
        for side in (1, -1):
            for name, (u, dz, solid) in GRIP_PROBES.items():
                assert part.is_inside((side*(w/2-u), y, h-dz)) == solid, (y, side, name)


@pytest.mark.parametrize('preset', [p.id for p in m.SPEC.presets])
def test_presets_are_single_valid_watertight_solids(preset, tmp_path):
    values = next(p.values for p in m.SPEC.presets if p.id == preset)
    part = m.build(values)
    assert part.is_valid and len(part.solids()) == 1
    mesh = mesh_from_part(part, tmp_path / 'p.stl', tolerance=0.01, angular_tolerance=0.1)
    assert mesh.is_watertight
    for name, shape, _ in m.colour_parts(values):
        assert shape.is_valid, name
    print(f'VOLUME | {preset} | {part.volume:.1f} mm3 | ' + ', '.join(
        f'{n} {s.volume:.1f}' for n, s, _ in m.colour_parts(values)))


# --- text: the labels seam ----------------------------------------------------------

def test_text_is_inter_bold_at_openscad_size():
    from labels.label_text import FONT_PATH, load_font
    assert load_font(FONT_PATH)
    _, inlay, _ = m.colour_parts({})[1]
    # U1's measured Inter Bold cap height at size 10 (i-1x5-h22-label.stl: 10.39 mm).
    assert inlay.bounding_box().size.X == pytest.approx(10.39, abs=.05)


def test_inlay_is_flush_and_debossed_is_the_same_recess():
    v = resolved({})
    blank = m.blank(v)
    (_, base, _), (_, inlay, _) = m.colour_parts({})
    bb = inlay.bounding_box()
    assert (bb.min.Z, bb.max.Z) == pytest.approx((0, v['text_depth']), abs=1e-6)
    assert base.volume + inlay.volume == pytest.approx(blank.volume, abs=1e-3)
    assert m.build({}).volume == pytest.approx(blank.volume, abs=1e-3)
    (_, debossed, _), = m.colour_parts({'text_style': 'debossed'})
    assert debossed.volume == pytest.approx(base.volume, abs=1e-3)
    # Read from below: mirrored in the model frame, like U1's label.
    assert not inlay.is_inside((0, 0, v['text_depth'] + 0.1))
    assert [n for n, *_ in m.colour_parts({'text': '   '})] == ['base']


@pytest.mark.parametrize('values', [{}, {'text': 'A'}, {'text': 'ABCDEFGHIJKLMNOPQRSTUVWX', 'text_size': 6}])
def test_strokes_hold_the_labels_inlay_floor(values):
    from labels.constants import STROKE_FLOOR_INLAID
    from labels.label_text import stroke_and_gap, text_sketch, text_measures
    v = resolved(values)
    size = v['text_size']*c.OPENSCAD_TEXT_SCALE
    stroke = text_measures(v['text'], size)[0]
    assert stroke >= STROKE_FLOOR_INLAID
    if len(v['text']) < 3:  # the direct scan is slow on long text
        assert stroke == pytest.approx(stroke_and_gap(text_sketch(v['text'], size))[0], abs=.02)
    print(f'STROKE | {v["text"]!r} size {v["text_size"]} | {stroke:.3f} mm')


def test_stroke_floor_is_a_named_error(monkeypatch):
    monkeypatch.setattr(m, 'text_measures', lambda text, size: (0.5, 1., 1.))
    with pytest.raises(ValueError, match='0.500 mm stroke, under the 0.71 mm floor'):
        m.build({})


@pytest.mark.parametrize('values,message', [
    ({'text_depth': 0}, 'text_depth 0 makes no label'),
    ({'text_depth': 0, 'text_style': 'debossed'}, 'text_depth 0 makes no label'),
    ({'label_length_units': 1}, 'the closed face is 27.2 x 25.6 mm'),
    ({'text': 'A very long cable label!', 'text_size': 16}, 'the closed face is 139.2 x 25.6 mm'),
    ({'text': 'ABCDEFGHIJKLMNOPQRSTUVWX', 'text_size': 6}, 'is 139.9 x 6.6 mm'),
])
def test_named_errors(values, message):
    with pytest.raises(ValueError) as exc:
        m.build(values)
    assert message in str(exc.value)


# --- print audit, exceptions and edges -------------------------------------------

CASES = {
    'label-1x5': {}, 'label-2x3': PARITY['text-label-2x3'],
    'debossed': {'text_style': 'debossed'},
    'blank': {'text': ''},
    'width-4': {'label_width_units': 4}, 'length-1': {'label_length_units': 1, 'text': 'A'},
    'length-11': {'label_length_units': 11},
    'max-corner': {'label_width_units': 4, 'label_length_units': 11, 'text_size': 16,
                   'text': 'Hello cables 0123', 'text_depth': 1},
    'min-corner': {'label_length_units': 1, 'text': 'A', 'text_size': 6, 'text_depth': 0.2},
    # 24 wide capitals at size 6 are 139.9 mm: one cell past the 5-cell face.
    'size-6-24ch': {'text': 'ABCDEFGHIJKLMNOPQRSTUVWX', 'text_size': 6, 'label_length_units': 6},
    'size-16': {'text_size': 16},
    'depth-0.2': {'text_depth': 0.2}, 'depth-1': {'text_depth': 1},
    'debossed-depth-0.2': {'text_style': 'debossed', 'text_depth': 0.2},
    'debossed-depth-1': {'text_style': 'debossed', 'text_depth': 1},
    'debossed-size-6-24ch': {'text_style': 'debossed', 'text': 'ABCDEFGHIJKLMNOPQRSTUVWX', 'text_size': 6,
                             'label_length_units': 6},
    'debossed-max-corner': {'text_style': 'debossed', 'label_width_units': 4, 'label_length_units': 11,
                            'text_size': 16, 'text': 'Hello cables 0123', 'text_depth': 1},
}


def edge_inventory(part, values):
    """Every edge with a >= 1 degree turn, by family; anything else fails.

    end face: the plate ends butt against the next part (mating).
    grip: rails, nubs, ramps and the floor top face the board (openGrid
      mating), z >= the floor top.
    bed chamfer: the 0.4 mm 45 degree bed-face chamfer, the edges the user
      sees round the text face (turn 45 degrees); chamfer corner: the four
      mitres where two of its faces meet (turn 60 degrees, between 45 degree
      faces, so no sharper than the chamfer's own faces' edges allow).
    label: debossed glyph edges stay sharp (they are the feature, as on the
      label card).
    """
    v = resolved(values)
    w, length = m.dimensions(v)
    k, top = m.BED_CHAMFER, m.PLATE_HEIGHT - c.BASE_HEIGHT
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
        x, y, z = abs(mid.X), abs(mid.Y), mid.Z
        bb = edge.bounding_box()
        if abs(y - length/2) < 1e-4 and abs(bb.max.Y - bb.min.Y) < 1e-4:
            family = 'end face'
        elif z >= top - 1e-4:
            family = 'grip'
        elif (abs(z) < 1e-4 and (abs(x - (w/2 - k)) < 1e-4 or abs(y - (length/2 - k)) < 1e-4)) or \
                (abs(z - k) < 1e-4 and abs(x - w/2) < 1e-4):
            family = 'bed chamfer'
            worst = max(worst, angle)
        elif z <= k + 1e-4 and abs(x - (w/2 - k + z)) < 1e-4 and abs(y - (length/2 - k + z)) < 1e-4:
            family = 'chamfer corner'
        elif v['text_style'] == 'debossed' and z <= v['text_depth'] + 1e-4 and x < w/2 - k:
            family = 'label'
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
    # Bridges are measured BEFORE any exclusion (debossed recess ceilings).
    assert raw.longest_bridge_mm <= pa.MAX_BRIDGE_MM
    regions = m.audit_exclusions(values)
    report = pa.audit(part, m.SPEC.print_orientation, model=name, exclusions=flat(regions))
    assert report.ok, report.format()
    families, worst = edge_inventory(part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    assert worst == pytest.approx(45, abs=.01)
    print(f'AUDIT | {name} | vol {part.volume:.1f} | raw wall {raw.min_wall_mm:.3f} ovh {raw.max_overhang_deg:.1f} '
          f'bridge {raw.longest_bridge_mm:.2f} | filtered wall {report.min_wall_mm:.3f} ovh '
          f'{report.max_overhang_deg:.1f} | edges worst exposed {worst:.1f} {dict(sorted(families.items()))} '
          f'| exceptions {", ".join(k for k, r in regions.items() if r) or "none"} | PASS')
    record(name, vol=part.volume, raw_wall=raw.min_wall_mm, raw_ovh=raw.max_overhang_deg,
           raw_bridge=raw.longest_bridge_mm, filtered_wall=report.min_wall_mm,
           filtered_ovh=report.max_overhang_deg, edges_worst_exposed=worst,
           edges=dict(sorted(families.items())), exceptions=[k for k, r in regions.items() if r],
           result='PASS')


def test_grip_end_wedge_matches_reference():
    """U1's grip-end-wedge probe on the plate: the same 0.6465 mm wedge."""
    w, h = 13.2, m.PLATE_HEIGHT
    origin = (w-.6, -63.5+.6-.05/sqrt(2), h-1.4+.05/sqrt(2))
    port_t = _part_thickness(m.build({}), origin, (0, 1, -1))
    ref_t = _ray_thickness(reference('text-label-1x5'), np.asarray(origin) + REF_SHIFT, (0, 1, -1))
    assert port_t == pytest.approx(.6465, abs=.005)
    assert ref_t == pytest.approx(port_t, abs=.01)
    print(f'EXCEPTION | grip-end-wedge | text-label-1x5 | point {origin} | port {port_t:.3f} ref {ref_t:.3f}')


def test_debossed_recess_ceiling_is_at_text_depth():
    values = {'text_style': 'debossed'}
    part = m.build(values)
    d = resolved(values)['text_depth']
    region = m.audit_exclusions(values)['label-recess'][0]
    ceilings = [f for f in part.faces() if abs(f.center().Z - d) < 1e-6 and region.is_inside(f.center())]
    assert ceilings
    p = ceilings[0].center()
    assert part.is_inside((p.X, p.Y, d + .1)) and not part.is_inside((p.X, p.Y, d - .1))


@pytest.mark.parametrize('values,family,count', [
    ({}, 'grip-end-wedge', 20), ({'label_width_units': 2, 'label_length_units': 3}, 'grip-end-wedge', 12),
    ({'label_length_units': 1, 'text': 'A'}, 'grip-end-wedge', 4),
    ({'text_style': 'debossed'}, 'label-recess', 1), ({}, 'label-recess', 0),
    ({'text_style': 'debossed', 'text': ''}, 'label-recess', 0),
])
def test_exception_membership(values, family, count):
    assert len(m.audit_exclusions(values)[family]) == count


@pytest.mark.parametrize('values', [{}, {'text_style': 'debossed'}])
def test_exclusions_still_reject_a_new_thin_fin(values):
    from build123d import Box, Pos
    part = m.build(values) + Pos(0, 30, 2 + 2)*Box(.4, 6, 4)  # a 0.4 mm fin on the floor
    report = pa.audit(part, m.SPEC.print_orientation, exclusions=flat(m.audit_exclusions(values)))
    assert report.min_wall_mm < pa.MIN_WALL_MM
