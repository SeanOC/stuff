"""holder_bench_lip_clip: the bench-lip fit coupon (pst-czxuk.1)."""
import math

import pytest
from build123d import Vector

from holders.bench_lip_clip import (FIT_KIT, OUTER_RADIUS, PARAMS, SPEC, audit_exclusions, dimensions,
                                    holder, label_cutter, lip_clip_profile)
from holders.printer import BED_X, BED_Y, BED_Z
from labels.constants import INLAY_DEPTH, STROKE_FLOOR_INLAID
from labels.label_text import FLOOR_MARGIN, text_measures
from tests.audit_record import record
from tests.print_audit import MIN_WALL_MM, audit

NUMERIC = [q for q in PARAMS if q.kind == 'number']

# §6 item 3: every numeric endpoint plus the documented corners. An endpoint
# another guard makes unreachable at the defaults is an expected-ValueError
# row; its nearest reachable corner is listed beside it.
EXPECTED_ERRORS = {
    ('wall', 3): 'wall - lead_in',              # 3 - 1.5 < 1.6
    ('coupon_length', 15): 'coupon_length',     # '+0.8' at 9.0 is 19.83 mm > 11
    ('text_size', 12): 'coupon_length',         # '+0.8' at 12 is 26.4 mm > 21
}
CORNERS = [
    {'wall': 3, 'lead_in': 1.0},                          # thinnest reachable wall
    {'wall': 3, 'lead_in': 0},                            # no lead-in
    {'hook_depth': 6, 'lead_in': 3},                      # hook flat exactly 3
    {'coupon_length': 15, 'label_text': '1'},             # shortest coupon, user label
    {'coupon_length': 22, 'text_size': 8.1},              # shortest coupon, derived label
    {'coupon_length': 31, 'text_size': 12},               # largest text
    {'height_clearance': -0.5, 'edge_gap': 0, 'jaw_root_radius': 2, 'hook_depth': 6},  # tightest mouth
    {'slab_thickness': 70, 'height_clearance': 4, 'top_reach': 60, 'wall': 8,
     'edge_gap': 2, 'hook_depth': 20, 'coupon_length': 60},  # largest footprint
    {'slab_thickness': 31, 'height_clearance': -0.5, 'top_reach': 20, 'hook_depth': 20},
]
ENDPOINTS = [{q.name: v} for q in NUMERIC for v in (q.min, q.max)
             if (q.name, v) not in EXPECTED_ERRORS]
CASES = [{}] + ENDPOINTS + CORNERS + [p.values for p in SPEC.presets]


def _id(values):
    return ','.join(f'{k}={v}' for k, v in values.items()) or 'defaults'


def _inside(sketch, x, y):
    return any(f.is_inside(Vector(x, y, 0), tolerance=1e-6) for f in sketch.faces())


def assert_profile(p):
    """The C at its nominal sizes: probes 0.01 mm either side of each face."""
    s = lip_clip_profile(p)
    w, ih, e = p['wall'], p['inner_height'], 0.01
    mouth_x = p['edge_x'] + p['hook_depth']/2
    # Inner height: hook top at y=w, jaw underside at y=w+ih.
    assert _inside(s, mouth_x, w - e) and not _inside(s, mouth_x, w + e)
    assert not _inside(s, mouth_x, w + ih - e) and _inside(s, mouth_x, w + ih + e)
    # Wall: the spine spans x 0..w; the inner face sits edge_gap from the slab.
    mid = w + ih/2
    assert _inside(s, e, mid) and _inside(s, w - e, mid) and not _inside(s, w + e, mid)
    # Hook depth and top reach on the flat of each tip face.
    tip = (OUTER_RADIUS + w - p['lead_in'])/2
    assert _inside(s, p['hook_x'] - e, tip) and not _inside(s, p['hook_x'] + e, tip)
    assert _inside(s, p['top_x'] - e, p['height'] - tip)
    assert not _inside(s, p['top_x'] + e, p['height'] - tip)
    assert p['hook_x'] - p['edge_x'] == pytest.approx(p['hook_depth'])
    bb = s.bounding_box()
    assert bb.size.X == pytest.approx(p['footprint'][0]) and bb.size.Y == pytest.approx(p['footprint'][1])
    # §6 item 10, both halves.
    assert p['footprint'][0] <= BED_X and p['footprint'][1] <= BED_Y and p['coupon_length'] <= BED_Z


def assert_finished_edges(part, p):
    """Edge classifier (the spool-cradle assert_finished_edges pattern).

    label: glyph recess walls, sharp by design, inside the exclusion slab.
    tangent: fillet runs. eased: every other edge, dihedral < 90 degrees
    (45 degree bed chamfers and lead-ins). tip: lead_in 0 only, the square
    jaw-tip inner corner the user asked for. No other class exists: the inner
    bearing faces meet only the root fillets, lead-ins, top fillets and bed
    chamfers.
    """
    tips = [] if p['lead_in'] else [(p['hook_x'], p['wall']), (p['top_x'], p['wall'] + p['inner_height'])]
    boxes = [b.bounding_box() for b in audit_exclusions({k: p[k] for k in SPEC.param_names()})]
    adjacency = {}
    for f in part.faces():
        for edge in f.edges():
            adjacency.setdefault(edge, []).append(f)
    counts, worst = {'label': 0, 'tangent': 0, 'eased': 0}, 0.0
    for edge, faces in adjacency.items():
        assert len(faces) == 2
        c = edge.center()
        if any(b.min.X - 1e-6 <= c.X <= b.max.X + 1e-6 and b.min.Y <= c.Y <= b.max.Y
               and b.min.Z <= c.Z <= b.max.Z for b in boxes):
            counts['label'] += 1
            continue
        if any(abs(c.X - x) < 1e-6 and abs(c.Y - y) < 1e-6 for x, y in tips):
            counts['tip'] = counts.get('tip', 0) + 1
            continue
        n0, n1 = (f.normal_at(c) for f in faces)
        angle = math.degrees(math.acos(max(-1, min(1, n0.dot(n1)))))
        if angle < 1e-3:
            counts['tangent'] += 1
        else:
            assert angle < 90 - 1e-3, (tuple(c), angle)
            counts['eased'] += 1
            worst = max(worst, angle)
    assert all(counts.values()) and counts.get('tip', 0) == len(tips), counts
    bed = min(part.faces().filter_by(lambda f: f.normal_at().Z < -0.99), key=lambda f: f.center().Z)
    for edge in bed.edges():
        other = next(f for f in adjacency[edge] if f != bed)
        assert other.normal_at(edge.center()).Z == pytest.approx(-math.sqrt(.5), abs=1e-4)
    return counts, worst


@pytest.mark.parametrize('values', [{}] + ENDPOINTS + CORNERS, ids=_id)
def test_profile_dimensions(values):
    p = dimensions(values)
    assert p['inner_height'] == pytest.approx(p['slab_thickness'] + p['height_clearance'])
    assert_profile(p)


@pytest.mark.parametrize('key,message', sorted(EXPECTED_ERRORS.items()), ids=lambda v: str(v))
def test_unreachable_endpoints_raise(key, message):
    with pytest.raises(ValueError, match=message):
        dimensions({key[0]: key[1]})


@pytest.mark.parametrize('values,message', [
    ({'hook_depth': 6, 'lead_in': 3.5}, 'lead_in'),
    ({'hook_depth': 6, 'lead_in': 3}, None),
    ({'wall': 4.5, 'lead_in': 3}, 'wall - lead_in'),
    ({'top_reach': 15, 'hook_depth': 15.5}, 'top_reach'),
    ({'label_text': 'BENCH LIP COUPON'}, 'coupon_length'),
    ({'coupon_length': 15}, 'coupon_length'),
    ({'jaw_root_radius': 0.5}, 'jaw_root_radius'),
    ({'nope': 1}, 'unknown'),
])
def test_guards_name_the_parameter(values, message):
    if message is None:
        dimensions(values)
        return
    with pytest.raises(ValueError, match=message):
        dimensions(values)


def test_label_stroke_floor_satisfied_at_domain_min():
    floor = STROKE_FLOOR_INLAID + FLOOR_MARGIN
    assert text_measures('+0.8', 8.1)[0] == pytest.approx(0.940, abs=5e-4)
    for c in FIT_KIT:
        assert text_measures(f'{c:+.1f}', 8.1)[0] >= floor
    assert dimensions({'text_size': 8.1, 'height_clearance': -0.5})['label_stroke'] >= floor


def test_label_derives_from_clearance():
    assert dimensions({})['label'] == '+0.8'
    assert dimensions({'height_clearance': -0.5})['label'] == '-0.5'
    assert dimensions({'label_text': '  '})['label'] == '+0.8'
    assert dimensions({'label_text': 'A'})['label'] == 'A'


def test_presets_are_the_fit_kit():
    assert [p.values for p in SPEC.presets] == [{'height_clearance': c} for c in FIT_KIT]
    assert SPEC.slug == 'holder-bench-lip-clip'
    assert dimensions({})['height_clearance'] == 0.8  # the default is fit-plus-0-8


@pytest.mark.parametrize('values', [p.values for p in SPEC.presets], ids=[p.id for p in SPEC.presets])
def test_preset_label_deboss(values):
    p = dimensions(values)
    part = holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    bb = label_cutter(p).bounding_box()
    floors = [f for f in part.faces() if f.geom_type.name == 'PLANE' and f.normal_at().X < -0.99
              and f.center().X > 1e-3]
    assert floors, 'no recess floor'
    for f in floors:
        assert f.center().X == pytest.approx(INLAY_DEPTH, abs=0.05)
        assert bb.min.Y - 1e-6 <= f.center().Y <= bb.max.Y + 1e-6
    # Not through the wall: the spine keeps more than the audit floor behind the ink.
    assert p['wall'] - INLAY_DEPTH >= MIN_WALL_MM + 1.5
    # Baseline along Z: the label is wider in Z than tall in Y and fits the room.
    assert bb.size.Z > bb.size.Y
    assert bb.size.Z <= p['coupon_length'] - 4


@pytest.mark.audit
@pytest.mark.parametrize('values', CASES, ids=_id)
def test_endpoint_audit(values):
    p = dimensions(values)
    part = holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    counts, edge = assert_finished_edges(part, p)
    report = audit(part, SPEC.print_orientation, exclusions=audit_exclusions(values),
                   model=SPEC.name)
    assert report.ok, report.format()
    assert not report.downward_fillets
    record('bench-lip-clip-endpoint', case=_id(values), min_wall=report.min_wall_mm,
           max_overhang=report.max_overhang_deg, exposed_edge_angle=edge, volume=part.volume, ok=report.ok, **counts)
    print(f"ENDPOINT {_id(values)}: min_wall={report.min_wall_mm:.3f} "
          f"overhang={report.max_overhang_deg:.1f} edge={edge:.1f} {counts} volume={part.volume:.0f} ok={report.ok}")
