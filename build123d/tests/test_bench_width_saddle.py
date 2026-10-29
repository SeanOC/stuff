"""holder_bench_width_saddle: the bench-width fit coupon (pst-czxuk.3)."""
import math

import pytest
from build123d import Vector

from holders.bench_width_saddle import (FIT_KIT, OUTER_RADIUS, PARAMS, SPEC, audit_exclusions, dimensions,
                                        holder, label_cutter, saddle_profile)
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
    ('wall', 3): 'wall - lead_in',      # 3 - 1.5 < 1.6
    ('lead_in', 3): 'wall - lead_in',   # 4 - 3 < 1.6
}
CORNERS = [
    {'wall': 3, 'lead_in': 1.0},                          # thinnest reachable wall
    {'wall': 3, 'lead_in': 0},                            # no lead-in
    {'wall': 5, 'lead_in': 3},                            # longest lead-in
    {'cheek_depth': 6, 'lead_in': 2},                     # cheek flat exactly 3
    {'coupon_length': 15, 'text_size': 12},               # largest text, shortest coupon
    {'coupon_length': 15, 'label_text': 'BENCH 310'},     # user label
    {'width_clearance': -2, 'cheek_depth': 6, 'lead_in': 1, 'jaw_root_radius': 2},  # tightest mouth
    {'bench_width': 315, 'width_clearance': 4, 'wall': 3, 'lead_in': 1,
     'cheek_depth': 20, 'coupon_length': 60},             # largest footprint: exactly BED_X
    {'bench_width': 250, 'width_clearance': -2, 'wall': 3, 'lead_in': 1, 'cheek_depth': 6},  # smallest
]
ENDPOINTS = [{q.name: v} for q in NUMERIC for v in (q.min, q.max)
             if (q.name, v) not in EXPECTED_ERRORS]
CASES = [{}] + ENDPOINTS + CORNERS + [p.values for p in SPEC.presets]


def _id(values):
    return ','.join(f'{k}={v}' for k, v in values.items()) or 'defaults'


def _inside(sketch, x, y):
    return any(f.is_inside(Vector(x, y, 0), tolerance=1e-6) for f in sketch.faces())


def assert_profile(p):
    """The inverted U at its nominal sizes: probes 0.01 mm either side of each face."""
    s = saddle_profile(p)
    w, W, cd, h, e = p['wall'], p['width'], p['cheek_depth'], p['height'], 0.01
    # Inner width on the flat of both cheek faces, between lead-in and root fillet.
    y = (p['lead_in'] + cd - p['jaw_root_radius'])/2
    assert _inside(s, w - e, y) and not _inside(s, w + e, y)
    assert not _inside(s, W - w - e, y) and _inside(s, W - w + e, y)
    assert (W - w) - w == pytest.approx(p['bench_width'] + p['width_clearance'])
    # Cheek walls and their depth down the edge face.
    tip = (OUTER_RADIUS + w - p['lead_in'])/2
    assert _inside(s, e, y) and _inside(s, tip, e) and not _inside(s, tip, -e)
    assert _inside(s, W - tip, e) and not _inside(s, W - tip, -e)
    # Bar: underside on the slab top at y=cheek_depth, wall thick.
    assert not _inside(s, W/2, cd - e) and _inside(s, W/2, cd + e)
    assert _inside(s, W/2, h - e) and not _inside(s, W/2, h + e)
    assert h - cd == pytest.approx(w)
    bb = s.bounding_box()
    assert bb.size.X == pytest.approx(p['footprint'][0]) and bb.size.Y == pytest.approx(p['footprint'][1])
    # §6 item 10, both halves.
    assert p['footprint'][0] <= BED_X and p['footprint'][1] <= BED_Y and p['coupon_length'] <= BED_Z


def assert_finished_edges(part, p):
    """Edge classifier (the bench_lip_clip / spool-cradle pattern).

    label: glyph recess walls, sharp by design, inside the exclusion slab.
    tangent: fillet runs. eased: every other edge, dihedral < 90 degrees
    (45 degree bed chamfers and lead-ins). tip: lead_in 0 only, the square
    cheek-tip inner corner the user asked for. No other class exists.
    """
    tips = [] if p['lead_in'] else [(p['wall'], 0), (p['width'] - p['wall'], 0)]
    boxes = [b.bounding_box() for b in audit_exclusions({k: p[k] for k in SPEC.param_names()})]
    adjacency = {}
    for f in part.faces():
        for edge in f.edges():
            adjacency.setdefault(edge, []).append(f)
    counts, worst = {'label': 0, 'tangent': 0, 'eased': 0}, 0.0
    for edge, faces in adjacency.items():
        assert len(faces) == 2
        c = edge.center()
        if any(b.min.X - 1e-6 <= c.X <= b.max.X + 1e-6 and b.min.Y - 1e-6 <= c.Y <= b.max.Y + 1e-6
               and b.min.Z - 1e-6 <= c.Z <= b.max.Z + 1e-6 for b in boxes):
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
    assert p['inner_width'] == pytest.approx(p['bench_width'] + p['width_clearance'])
    assert_profile(p)


@pytest.mark.parametrize('key,message', sorted(EXPECTED_ERRORS.items()), ids=lambda v: str(v))
def test_unreachable_endpoints_raise(key, message):
    with pytest.raises(ValueError, match=message):
        dimensions({key[0]: key[1]})


@pytest.mark.parametrize('values,message', [
    ({'cheek_depth': 6, 'lead_in': 2.5, 'wall': 5}, 'cheek_depth - lead_in - jaw_root_radius'),
    ({'cheek_depth': 6, 'lead_in': 2}, None),
    ({'wall': 4, 'lead_in': 2.5}, 'wall - lead_in'),
    ({'bench_width': 314, 'width_clearance': 3}, None),                 # 314 + 3 + 8 = BED_X exactly
    ({'bench_width': 315, 'width_clearance': 4}, 'reduce bench_width'),  # 327 > BED_X
    ({'wall': 6, 'width_clearance': 4}, 'reduce bench_width'),           # 326 > BED_X
    ({'coupon_length': 15, 'text_size': 12, 'label_text': 'Hg'}, 'coupon_length'),  # 11.32 mm tall
    ({'bench_width': 250, 'width_clearance': -2, 'label_text': 'W'*24, 'text_size': 12}, 'bench_width'),
    ({'coupon_length': 61}, 'coupon_length'),
    ({'jaw_root_radius': 0.5}, 'jaw_root_radius'),
    ({'nope': 1}, 'unknown'),
])
def test_guards_name_the_parameter(values, message):
    if message is None:
        dimensions(values)
        return
    with pytest.raises(ValueError, match=message):
        dimensions(values)


def test_kit_fits_the_bed():
    """310 + 3 + 2*4 = 321 <= BED_X 325 at the widest preset: why wall defaults to 4."""
    assert max(dimensions(p.values)['width'] for p in SPEC.presets) == pytest.approx(321)
    assert max(FIT_KIT) == 3.0 and dimensions({})['wall'] == 4


def test_label_stroke_floor_satisfied_at_domain_min():
    floor = STROKE_FLOOR_INLAID + FLOOR_MARGIN
    for c in FIT_KIT:
        assert text_measures(f'{c:+.1f}', 8.1)[0] >= floor
    assert dimensions({'text_size': 8.1, 'width_clearance': -2})['label_stroke'] >= floor


def test_label_derives_from_clearance():
    assert dimensions({})['label'] == '+1.0'
    assert dimensions({'width_clearance': -1})['label'] == '-1.0'
    assert dimensions({'width_clearance': 0})['label'] == '+0.0'
    assert dimensions({'label_text': '  '})['label'] == '+1.0'
    assert dimensions({'label_text': 'A'})['label'] == 'A'


def test_presets_are_the_fit_kit():
    assert [p.values for p in SPEC.presets] == [{'width_clearance': c} for c in FIT_KIT]
    assert [p.id for p in SPEC.presets] == ['fit-minus-1-0', 'fit-plus-0-0', 'fit-plus-1-0',
                                            'fit-plus-2-0', 'fit-plus-3-0']
    assert SPEC.slug == 'holder-bench-width-saddle'
    assert dimensions({})['width_clearance'] == 1.0  # the default is fit-plus-1-0


@pytest.mark.parametrize('values', [p.values for p in SPEC.presets], ids=[p.id for p in SPEC.presets])
def test_preset_label_deboss(values):
    p = dimensions(values)
    part = holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    bb = label_cutter(p).bounding_box()
    floors = [f for f in part.faces() if f.geom_type.name == 'PLANE' and f.normal_at().Y > 0.99
              and f.center().Y < p['height'] - 1e-3]
    assert floors, 'no recess floor'
    for f in floors:
        assert f.center().Y == pytest.approx(p['height'] - INLAY_DEPTH, abs=0.05)
        assert bb.min.X - 1e-6 <= f.center().X <= bb.max.X + 1e-6
    # Not through the bar: it keeps more than the audit floor behind the ink.
    assert p['wall'] - INLAY_DEPTH >= MIN_WALL_MM + 1.5
    # Baseline along X (the bench width): wider in X than tall in Z, and the
    # glyph height fits the coupon with LABEL_END_MARGIN at each end.
    assert bb.size.X > bb.size.Z
    assert bb.size.Z <= p['coupon_length'] - 4
    assert bb.center().X == pytest.approx(p['width']/2, abs=1e-6)


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
    record('bench-width-saddle-endpoint', case=_id(values), min_wall=report.min_wall_mm,
           max_overhang=report.max_overhang_deg, exposed_edge_angle=edge, volume=part.volume, ok=report.ok, **counts)
    print(f"ENDPOINT {_id(values)}: min_wall={report.min_wall_mm:.3f} "
          f"overhang={report.max_overhang_deg:.1f} edge={edge:.1f} {counts} volume={part.volume:.0f} ok={report.ok}")
