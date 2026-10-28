"""Hard-ground interface: real fits, pin access, hardware seats and endpoint audits."""
import functools
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from build123d import Box, Circle, Plane, Pos, Rot, extrude
from holders import signs, tombstone_base as base, tombstone_stake as post
from holders.registry import all_models
from print_audit import audit
from test_tombstone_stake import common, stake_mating, unfinished_edges


@functools.cache
def built(model, items):
    spec = model.SPEC
    values = spec.resolve_values(dict(items))
    return values, spec.build(values)


def case(model, **overrides):
    return built(model, tuple(sorted(overrides.items())))


def placed_post(v, part):
    return Pos(0, v['thickness'] / 2, 0) * Rot(90, 0, 0) * part


def test_registry_and_provisional_hardware_defaults():
    assert base.SPEC in all_models()
    assert base.SPEC.slug == 'holder-tombstone-base'
    assert base.SPEC.category_id == 'household'
    assert {p.id: p.values for p in base.SPEC.presets} == {'default': {}}
    assert base.DEFAULTS['thickness'] == post.DEFAULTS['thickness'] == 8
    assert {k: base.DEFAULTS[k] for k in ('stake_d', 'stake_head_d', 'stake_head_t', 'stake_count', 'stake_spacing')} == {
        'stake_d': 12.7, 'stake_head_d': 25, 'stake_head_t': 4, 'stake_count': '2', 'stake_spacing': 160}
    assert base.CHEEK_T >= 5 and base.CHEEK_H == 24
    assert math.degrees(math.atan(base.CHEEK_H / base.GUSSET_RUN)) == pytest.approx(43.83, abs=0.01)
    assert base.SPEC.review_sections


@pytest.mark.parametrize('thickness,pin', [(6, False), (8, False), (8, True)])
@pytest.mark.audit
def test_post_fits_every_mortise_wall_and_pin_has_open_access(thickness, pin):
    bv, plate = case(base, thickness=thickness)
    pv, flat = case(post, ground='post', thickness=thickness, retention='pin' if pin else 'none')
    assembled = placed_post(pv, flat)
    assert common(plate, assembled) < 1e-6
    assert assembled.bounding_box().min.Z == pytest.approx(0, abs=1e-6)
    # Includes the plate mortise AND the raised cheeks/buttresses.
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for distance, collides in ((0.19, False), (0.21, True)):
            volume = common(Pos(dx * distance, dy * distance, 0) * assembled, plate)
            assert (volume > 1e-5) == collides, (dx, dy, distance, volume)
    axis_z = bv['plate_t'] + base.CHEEK_H / 2
    assert post.stub_pin_y(pv) == axis_z
    # Each flat-printed teardrop encloses this round pin even though the post
    # roof rotates on assembly. The cylinder reaches beyond both outer cheeks.
    pin_body = extrude(Plane.YZ * Pos(0, axis_z) * Circle(signs.PIN_D / 2 - 0.001), 40, both=True)
    assert common(pin_body, plate) < 1e-6
    assert common(pin_body, assembled) < 1e-6
    # Moving the pin above its axis hits BOTH cheek and stub material.
    assert common(Pos(0, 0, 0.2) * pin_body, plate) > 0.01
    assert common(Pos(0, 0, 0.2) * pin_body, assembled) > 0.01
    assert len(base.audit_exclusions(bv)) == 2
    assert len(post.audit_exclusions(pv)) == (3 if pin else 1)
    for m, v, part in ((base, bv, plate), (post, pv, flat)):
        raw = audit(part, (0, 0, 1))
        assert raw.longest_bridge_mm <= 1.5, raw.format()
        report = audit(part, (0, 0, 1), exclusions=m.audit_exclusions(v))
        assert report.ok, report.format()


@pytest.mark.audit
def test_counterbore_depth_floor_clearance_and_one_stake():
    for count in ('1', '2'):
        v, part = case(base, stake_count=count)
        floor = v['plate_t'] - v['stake_head_t']
        assert floor >= 2
        assert len(part.solids()) == 1
        assert part.is_valid
        for x in base.stake_xs(v):
            assert abs(x) - (v['stake_head_d'] + 1) / 2 - (base.mortise_size(v)[0] / 2 + base.CHEEK_T) >= 8
            bore = extrude(Pos(x, 0, -1) * Circle((v['stake_d'] + 0.8) / 2 - 0.01), 20)
            assert common(bore, part) < 1e-6
            head = extrude(Pos(x, 0, floor) * Circle(v['stake_head_d'] / 2), v['stake_head_t'])
            assert common(head, part) < 1e-6
            assert common(Pos(0, 0, -0.1) * head, part) > 0.01
        assert part.bounding_box().size.Z == pytest.approx(v['plate_t'] + base.CHEEK_H)


def base_functional(v, c):
    mw, md = base.mortise_size(v)
    # Exact mortise boundary, pin mouths, and head-bearing seats only.
    if abs(c.X) <= mw / 2 + 1e-4 and abs(c.Y) <= md / 2 + 1e-4:
        return True
    if abs(c.Y) <= signs.PIN_D / 2 + 1e-4 and abs(c.Z - (v['plate_t'] + base.CHEEK_H / 2)) <= signs.PIN_D / 2 + 1e-4:
        return True
    return any(abs(math.hypot(c.X - x, c.Y) - (v['stake_head_d'] + 1) / 2) < 1e-4
               and abs(c.Z - (v['plate_t'] - v['stake_head_t'])) < 1e-4 for x in base.stake_xs(v))


def exposed_edge_angle(v, part):
    """Largest normal discontinuity on nonfunctional edges.

    Face-to-bevel transitions are 45 degrees; where two 45-degree bevels
    meet at a rectangular corner their normal discontinuity is 60 degrees.

    Adjacent face normals are evaluated at the same point, so tangencies at
    rounds give zero, independently of edge enumeration or audit exclusions.
    """
    worst = 0.0
    for edge in part.edges():
        c = edge.center()
        if base_functional(v, c):
            continue
        faces = [f for f in part.faces() if any(e.is_same(edge) for e in f.edges())]
        if len(faces) == 2:
            dot = faces[0].normal_at(c).dot(faces[1].normal_at(c))
            angle = math.degrees(math.acos(max(-1, min(1, dot))))
            worst = max(worst, angle)
    return worst


def endpoints():
    for model, initial in ((base, {}), (post, {'ground': 'post'}), (post, {'ground': 'blade'})):
        label = 'base' if model is base else initial['ground']
        yield label + '/default', model, initial
        for param in model.PARAMS:
            if param.kind in ('number', 'integer'):
                for bound in (param.min, param.max):
                    yield f'{label}/{param.name}={bound:g}', model, {**initial, param.name: bound}
    for preset in post.SPEC.presets:
        yield 'preset/' + preset.id, post, preset.values
    for label, model, values in (
        ('base/large-hardware', base, {'stake_d': 25, 'stake_head_d': 45, 'stake_head_t': 10, 'plate_t': 12}),
        ('base/max-spacing', base, {'stake_spacing': 240, 'plate_w': 325}),
        ('base/min-plate', base, {'plate_w': 180, 'plate_d': 80, 'stake_spacing': 110}),
        ('base/one-stake', base, {'stake_count': '1'}),
        ('post/max-stack', post, {'ground': 'post', 'post_depth': 200, 'head_height': 60, 'head_width': 140, 'width': 25}),
        ('post/min-width-thick', post, {'ground': 'post', 'width': 25, 'thickness': 10}),
        ('post/max-width-thin', post, {'ground': 'post', 'width': 60, 'thickness': 6}),
        ('post/pinned', post, {'ground': 'post', 'retention': 'pin'}),
    ):
        yield label, model, values


CASES = list(endpoints())


@pytest.mark.audit
@pytest.mark.parametrize('label,model,overrides', CASES, ids=[c[0] for c in CASES])
def test_endpoint_audit_and_edges(label, model, overrides):
    v = model.SPEC.resolve_values(overrides)
    try:
        model.validate(v)
    except ValueError as exc:
        # Named cross-parameter geometry constraints, never audit failures.
        assert any(text in str(exc) for text in ('counterbore floor', 'radial bearing', 'clear the mortise',
                   'plate edge', 'taper would', 'cross-bar lap', 'post thickness', 'post_depth'))
        print(f'ENDPOINT {label} | invalid: {exc}')
        return
    _, part = built(model, tuple(sorted(overrides.items())))
    raw = audit(part, (0, 0, 1))
    assert raw.longest_bridge_mm <= 1.5, raw.format()
    report = audit(part, (0, 0, 1), exclusions=model.audit_exclusions(v))
    assert report.ok, report.format()
    if model is base:
        angle = exposed_edge_angle(v, part)
        assert angle <= 60.01, angle
    else:
        assert not unfinished_edges(post.stake(v), stake_mating(v))
        angle = 45.0  # the stake classifier recognizes its 45-degree rims
    print(f'ENDPOINT {label} | {report.min_wall_mm:.3f} | {report.max_overhang_deg:.2f} | {angle:.2f} | PASS | volume={part.volume:.3f}')


def test_post_specific_guards_and_length():
    v = post.SPEC.resolve_values({'ground': 'post'})
    assert post.printed_length(v) == pytest.approx(129.6)
    assert post.shoulder_bottom(v) == pytest.approx(v['post_depth'])
    with pytest.raises(ValueError, match='cross_bar'):
        post.build({**v, 'cross_bar': True})
    with pytest.raises(ValueError, match='7.8'):
        post.build({**v, 'thickness': 6, 'retention': 'pin'})
    with pytest.raises(ValueError, match='post_depth'):
        post.build({**v, 'post_depth': 30, 'base_plate_t': 12})
