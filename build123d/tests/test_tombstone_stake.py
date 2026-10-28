"""Tombstone stake (S2 pst-tl4ac.2): joint contract, guards, the 3D joint vs the
real sign, cross-bar, audit, edges."""
import functools
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from build123d import Box, Plane, Pos, Vector  # noqa: E402
from holders import signs  # noqa: E402
from holders import tombstone_sign  # noqa: E402
from holders import tombstone_stake as m  # noqa: E402
from holders.registry import all_models  # noqa: E402
import print_audit  # noqa: E402
from print_audit import audit  # noqa: E402
from scripts.export import export_stl  # noqa: E402

SPEC = m.SPEC
PRESETS = {p.id: p for p in SPEC.presets}
OFFSET = signs.SKIN + signs.JOINT_CLEARANCE  # sign Z = stake Z + OFFSET (1.4)


@functools.cache
def preset_case(preset_id: str):
    values = SPEC.resolve_values(PRESETS[preset_id].values)
    return values, SPEC.build(values)


def common(a, b) -> float:
    """Volume of a & b (build123d returns None for an empty intersection)."""
    out = a & b
    return out.volume if out is not None else 0.0


def values_with(**overrides):
    return {**m.DEFAULTS, **overrides}


# --- registration ---------------------------------------------------------

def test_registered_as_a_household_sign_model():
    assert SPEC in all_models()
    assert SPEC.slug == 'holder-tombstone-stake'
    assert SPEC.category_id == 'household' and 'sign' in SPEC.tags
    assert not SPEC.is_multi_colour
    params = {p.name: p for p in SPEC.params}
    assert (params['width'].default, params['width'].min, params['width'].max) == (40, 25, 60)
    assert (params['length'].default, params['length'].max) == (300, 320)
    assert (params['thickness'].default, params['thickness'].min, params['thickness'].max) == (8, 5, 10)
    assert (params['head_width'].default, params['head_width'].min) == (90, pytest.approx(87.6))
    assert (params['head_height'].min, params['head_height'].max) == (20, 60)
    assert params['retention'].choices == ('none', 'pin') and params['retention'].default == 'none'
    assert params['cross_bar'].default is False
    assert (params['cross_length'].default, params['cross_length'].max) == (200, 320)
    assert {p.id: p.values for p in SPEC.presets} == {
        'default': {}, 'long': {'length': 320.0}, 'cross-bar': {'cross_bar': True},
        'pinned': {'thickness': 8.0, 'retention': 'pin'}, 'post': {'ground': 'post'}}
    assert all(p.default_view is None for p in SPEC.presets)  # see the module docstring


def test_review_sections_put_the_tenon_plane_first():
    first = SPEC.review_sections[0]
    assert first.normal == (1, 0, 0) and first.origin[0] == signs.POCKET_OFFSET
    assert m.head_top(m.DEFAULTS) < first.origin[1] < m.DEFAULTS['length']


# --- joint contract (2D) --------------------------------------------------

def test_tenon_dimensions_follow_the_contract_formulas():
    assert signs.tenon_w() == pytest.approx(7.6)
    assert signs.tenon_len() == pytest.approx(34.6)
    assert signs.tenon_t(6.0) == pytest.approx(3.2)
    assert signs.tenon_t(8.0) == pytest.approx(5.2)
    assert m.MIN_HEAD_WIDTH == pytest.approx(2 * (signs.POCKET_OFFSET + signs.tenon_w() / 2))
    assert OFFSET == pytest.approx(1.4)


@pytest.mark.parametrize('thickness', [5.0, 6.0, 8.0, 10.0])
def test_real_tenon_section_is_the_contract_tenon_flush_with_the_bed(thickness):
    """2D joint test on the real stake: its X-Z section through the tenons is
    signs.tenon_rect at each pocket centre, moved down by the 1.4 offset so
    its underside is the bed face; the pocket clears it by JOINT_CLEARANCE."""
    values = values_with(thickness=thickness)
    blade = m.stake(values)
    y = m.head_top(values) + signs.tenon_len() / 2
    section = blade & Pos(0, y, thickness / 2) * Box(300, 0.01, thickness + 2)
    solids = sorted(section.solids(), key=lambda s: s.center().X)
    assert len(solids) == 2
    for solid, x in zip(solids, signs.POCKET_XS):
        bb = solid.bounding_box()
        tx0, tz0, tx1, tz1 = signs.tenon_rect(x, thickness).bounds
        assert (bb.min.X, bb.max.X) == (pytest.approx(tx0, abs=1e-4), pytest.approx(tx1, abs=1e-4))
        assert bb.min.Z == pytest.approx(0, abs=1e-6)
        assert (bb.min.Z + OFFSET, bb.max.Z + OFFSET) == (
            pytest.approx(tz0, abs=1e-4), pytest.approx(tz1, abs=1e-4))
        px0, pz0, px1, pz1 = signs.pocket_rect(x, thickness).bounds
        for gap in (tx0 - px0, px1 - tx1, bb.min.Z + OFFSET - pz0, pz1 - bb.max.Z - OFFSET):
            assert gap == pytest.approx(signs.JOINT_CLEARANCE, abs=1e-4)


def test_tenon_centres_are_the_pocket_centres():
    _, whole = preset_case('default')
    yh = m.head_top(m.DEFAULTS)
    above = whole & Pos(0, yh + 50, 10) * Box(300, 100, 40)
    xs = sorted(round(s.center().X, 6) for s in above.solids())
    assert tuple(xs) == signs.POCKET_XS


# --- guards ---------------------------------------------------------------

def test_head_width_guard_names_the_pocket_bound():
    with pytest.raises(ValueError, match=r'head_width 87 mm < 87\.6 mm: the tenons at \+-40'):
        m.validate(values_with(head_width=87.0))
    m.validate(values_with(head_width=87.6))


def test_pin_needs_a_7_8_mm_blade():
    with pytest.raises(ValueError, match=r"thickness >= 7\.8 mm"):
        m.validate(SPEC.resolve_values({'retention': 'pin', 'thickness': 6.0}))
    m.validate(SPEC.resolve_values({'retention': 'pin', 'thickness': 7.8}))


def test_taper_reaching_the_head_is_a_named_error():
    values = SPEC.resolve_values({'length': 150.0, 'head_height': 60.0, 'head_width': 140.0})
    with pytest.raises(ValueError, match=r'taper would reach the head; length must be >= '):
        m.validate(values)
    need = m.min_length(values)
    m.validate({**values, 'length': need})
    with pytest.raises(ValueError, match='taper would reach the head'):
        m.validate({**values, 'length': need - 0.2})


def test_cross_bar_lap_must_clear_the_point():
    values = SPEC.resolve_values({'cross_bar': True, 'length': 150.0})
    with pytest.raises(ValueError, match=r'cross-bar lap .* length must be >= '):
        m.validate(values)
    m.validate({**values, 'length': m.min_length(values)})


def test_point_is_45_degrees_included_and_ends_below_the_shoulders():
    assert m.taper_run(40.0) == pytest.approx(20 / math.tan(math.radians(22.5)))
    assert round(m.taper_run(40.0), 1) == 48.3
    for preset in PRESETS.values():
        if preset.id == 'post':
            continue
        values = SPEC.resolve_values(preset.values)
        assert m.taper_run(values['width']) < m.shoulder_bottom(values)


# --- the 3D joint against the real sign -----------------------------------

def test_stake_default_thickness_is_the_signs():
    """The tenons are the contract's formula of the stake's OWN thickness
    Param: a sign default that moved alone would ship a loose joint
    (tenon_t(6) = 3.2 in an 8 mm sign's 5.6 mm pocket)."""
    assert m.DEFAULTS['thickness'] == tombstone_sign.DEFAULTS['thickness'] == 8.0


def _assembled(thickness: float, pin: bool, ground="blade"):
    """(sign, stake placed in the sign frame) for one thickness."""
    retention = {'sign': 'pin' if pin else 'friction', 'stake': 'pin' if pin else 'none'}
    sign_values = tombstone_sign.SPEC.resolve_values(
        {'thickness': thickness, 'retention': retention['sign']})
    stake_values = SPEC.resolve_values({'thickness': thickness, 'retention': retention['stake'], 'ground': ground})
    sign = tombstone_sign.plate(sign_values)
    placed = Pos(0, -m.head_top(stake_values), OFFSET) * m.stake(stake_values)
    return sign_values, sign, placed


@pytest.mark.audit
@pytest.mark.parametrize('thickness,pin', [(6.0, False), (8.0, False), (8.0, True)])
@pytest.mark.parametrize('ground', ['blade', 'post'])
def test_tenons_fill_the_real_pockets_with_the_contract_clearance(thickness, pin, ground):
    sign_values, sign, placed = _assembled(thickness, pin, ground)
    assert common(sign, placed) < 1e-6  # no interference anywhere
    tenons = placed & Pos(0, 25, thickness / 2) * Box(300, 50, 3 * thickness)  # Y > 0
    assert len(tenons.solids()) == 2
    eps = 0.01
    for x in signs.POCKET_XS:
        pocket = Pos(x, signs.POCKET_DEPTH / 2, thickness / 2) * Box(
            signs.POCKET_W, signs.POCKET_DEPTH, signs.pocket_height(thickness))
        assert common(pocket, sign) < 1e-6  # the real sign is void there
        tenon = tenons & Pos(x, 25, thickness / 2) * Box(20, 50, 3 * thickness)
        assert common(tenon, pocket) == pytest.approx(tenon.volume, rel=1e-3)
        # Every pocket wall: clear by exactly its gap (0.2 sides, 0.4 at the end).
        for move, gap in (((-1, 0, 0), 0.2), ((1, 0, 0), 0.2), ((0, 0, -1), 0.2),
                          ((0, 0, 1), 0.2), ((0, 1, 0), 2 * signs.JOINT_CLEARANCE)):
            near = Pos(*(c * (gap - eps) for c in move)) * tenon
            far = Pos(*(c * (gap + eps) for c in move)) * tenon
            assert common(near, sign) < 1e-6, (x, move)
            assert common(far, sign) > 1e-4, (x, move)
    # The head's top edge bears on the sign's bottom edge.
    assert common(Pos(0, eps, 0) * placed, sign) > 1e-3
    if pin:  # one hole by construction: the tenon's hole is the sign's hole
        hole = signs.pin_hole(sign_values['width'], thickness)
        _, _, plain = _assembled(thickness, pin=False, ground=ground)
        plain_tenons = plain & Pos(0, 25, thickness / 2) * Box(300, 50, 3 * thickness)
        assert common(tenons, hole) < 1e-6
        removed = (plain_tenons - tenons).volume
        assert removed > 0 and removed == pytest.approx(common(plain_tenons, hole), rel=1e-3)


# --- cross-bar ------------------------------------------------------------

@pytest.mark.audit
def test_cross_bar_is_two_flat_blades_on_the_bed():
    values, whole = preset_case('cross-bar')
    solids = whole.solids()
    assert len(solids) == 2
    for solid in solids:
        bb = solid.bounding_box()
        assert bb.min.Z == pytest.approx(0, abs=1e-6)
        assert bb.max.Z == pytest.approx(values['thickness'])
    bb = whole.bounding_box()
    assert bb.size.X <= tombstone_sign.MAX_WIDTH and bb.size.Y <= tombstone_sign.MAX_HEIGHT
    assert solids[0].distance_to(solids[1]) == pytest.approx(m.BAR_GAP)


@pytest.mark.audit
def test_cross_bar_half_lap_interlocks_flush():
    """Turned over and rotated into the lap, the bar fills the shaft's notch:
    no interference, both faces flush, the lap clearance on each side."""
    values = SPEC.resolve_values({'cross_bar': True})
    t = values['thickness']
    blade, bar = m.stake(values), m.cross_bar(values)
    flipped = Pos(0, m.lap_centre(values), t) * (Plane.XY.rotated((180, 0, 0)).location * bar)
    assert common(blade, flipped) < 1e-6
    bb = flipped.bounding_box()
    assert (bb.min.Z, bb.max.Z) == (pytest.approx(0, abs=1e-6), pytest.approx(t))
    lap = Pos(0, m.lap_centre(values), t / 2) * Box(values['width'] - 4, values['width'] - 4, t)
    assert (lap & (blade + flipped)).volume == pytest.approx(lap.volume, rel=1e-6)
    eps = 0.01
    for move in ((0, 1, 0), (0, -1, 0)):
        near = Pos(*(c * (m.LAP_CLEARANCE - eps) for c in move)) * flipped
        far = Pos(*(c * (m.LAP_CLEARANCE + eps) for c in move)) * flipped
        assert common(near, blade) < 1e-6 and common(far, blade) > 1e-4


# --- print audit + edges --------------------------------------------------

@pytest.mark.audit
@pytest.mark.parametrize('preset_id', list(PRESETS))
def test_print_audit_per_preset(preset_id, capsys):
    """Every preset passes flat, with no exclusion except the pinned preset's
    pin-hole roofs (measured as a <= 1.5 mm bridge first). Both cross-bar
    blades are inspected: the audit's faces and samples cover every solid."""
    values, whole = preset_case(preset_id)
    regions = m.audit_exclusions(values)
    raw = audit(whole, SPEC.print_orientation, model=f'{preset_id} raw')
    if regions:
        assert raw.longest_bridge_mm <= 1.5
        assert all('overhang' in f for f in raw.failures()), raw.format()
    else:
        assert raw.ok, raw.format()
    report = audit(whole, SPEC.print_orientation, exclusions=regions, model=preset_id)
    with capsys.disabled():
        print(f'\n{preset_id:10} raw_overhang={raw.max_overhang_deg:.1f} '
              f'bridge={report.longest_bridge_mm:.2f} overhang={report.max_overhang_deg:.1f} '
              f'min_wall={report.min_wall_mm:.3f} volume={whole.volume:.0f} ok={report.ok}')
    assert report.ok, report.format()
    assert report.max_overhang_deg <= 45.0 + 1e-3


@pytest.mark.audit
def test_raw_audit_fails_only_on_the_pin_roofs():
    values, whole = preset_case('pinned')
    boxes = m.audit_exclusions(values)
    for face in whole.faces():
        n = face.normal_at(face.center())
        if n.Z < -0.75 and face.center().Z > 1e-3:  # a downward ceiling above the bed
            c = face.center()
            assert any(x0 <= c.X <= x1 and y0 <= c.Y <= y1 and z0 <= c.Z <= z1
                       for x0, y0, z0, x1, y1, z1 in boxes), c


@pytest.mark.audit
def test_cross_bar_audit_sees_both_blades():
    """A ceiling planted on the bar alone fails the compound's audit."""
    values, whole = preset_case('cross-bar')
    bar = m.bar_placement(values) * m.cross_bar(values)
    bb = bar.bounding_box()
    shelf = Pos(bb.center().X, bb.center().Y, bb.max.Z + 2) * Box(bb.size.X + 20, 20, 1)
    report = audit(whole + shelf, SPEC.print_orientation, model='cross-bar + shelf')
    assert not report.ok


def unfinished_edges(part, mating):
    """Edges that are neither eased (on a 45-degree chamfer), tangent, nor in a
    mating region (tenon, pin, lap notch, the tip): (x0, y0, z0, x1, y1, z1)."""
    bad = []
    for edge in part.edges():
        c = edge.center()
        faces = [f for f in part.faces() if any(e.is_same(edge) for e in f.edges())]
        normals = [f.normal_at(c) for f in faces]
        chamfered = any(abs(abs(n.Z) - math.sqrt(0.5)) < 1e-3 for n in normals)
        tangent = len(normals) == 2 and normals[0].dot(normals[1]) > 0.999
        in_mating = any(x0 - 1e-3 <= c.X <= x1 + 1e-3 and y0 - 1e-3 <= c.Y <= y1 + 1e-3
                        and z0 - 1e-3 <= c.Z <= z1 + 1e-3 for x0, y0, z0, x1, y1, z1 in mating)
        if not (chamfered or tangent or in_mating):
            bad.append((round(c.X, 2), round(c.Y, 2), round(c.Z, 2)))
    return bad


def stake_mating(values):
    t, yh = values['thickness'], m.head_top(values)
    out = [(x - signs.tenon_w() / 2, yh - m.TENON_OVERLAP, 0,
            x + signs.tenon_w() / 2, values['length'], t) for x in signs.POCKET_XS]
    out.append((-1e-3, -1e-3, 0, 1e-3, 1e-3, t))  # the tip's vertical edge
    if values['ground'] == 'post':
        y, half = m.stub_pin_y(values), signs.PIN_D / 2
        out.append((-values['width'] / 2, y - half, t / 2 - half,
                    values['width'] / 2, y + half, t / 2 + half))
    if values['cross_bar']:
        y, half = m.lap_centre(values), m.lap_span(values) / 2
        out.append((-values['width'], y - half, t / 2, values['width'], y + half, t))
    return out


def bar_mating(values):
    t, half = values['thickness'], values['width'] / 2 + m.LAP_CLEARANCE
    return [(-half, -values['width'], t / 2, half, values['width'], t)]


@pytest.mark.audit
@pytest.mark.parametrize('preset_id', list(PRESETS))
def test_every_edge_is_eased_tangent_or_a_mating_edge(preset_id):
    values, _ = preset_case(preset_id)
    assert not unfinished_edges(m.stake(values), stake_mating(values))
    if values['cross_bar']:
        assert not unfinished_edges(m.cross_bar(values), bar_mating(values))


_WRITE = '''
import sys; sys.path.insert(0, {root!r})
from holders.tombstone_stake import SPEC
from scripts.export import export_stl
export_stl(SPEC.build(SPEC.resolve_values({values!r})), {out!r})
'''


@pytest.mark.audit
def test_stl_is_byte_stable_across_processes(tmp_path):
    values, whole = preset_case('cross-bar')
    export_stl(whole, str(tmp_path / 'a.stl'))
    subprocess.run([sys.executable, '-c', _WRITE.format(
        root=str(ROOT), values=PRESETS['cross-bar'].values, out=str(tmp_path / 'b.stl'))],
        cwd=ROOT, check=True, capture_output=True)
    assert (tmp_path / 'a.stl').read_bytes() == (tmp_path / 'b.stl').read_bytes()


def test_audit_constants_are_the_contracts():
    assert signs.MIN_WALL_MM == print_audit.MIN_WALL_MM
    assert m.MAX_LENGTH == tombstone_sign.MAX_HEIGHT
