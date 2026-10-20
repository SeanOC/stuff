"""Tombstone sign (S1 pst-tl4ac.1, S3 pst-tl4ac.3, S4 pst-tl4ac.4): joint
contract, QR, guards, the type classes and rhythm, colour roles and folds,
the ghost, audit, edges."""
import functools
import json
import math
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import segno

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from build123d import Box, Compound, FontStyle, GeomType, Pos, Vector  # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common  # noqa: E402
from OCP.TopTools import TopTools_ListOfShape  # noqa: E402
from shapely.geometry import Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from holders import sign_ghost, signs  # noqa: E402
from holders import tombstone_sign as m  # noqa: E402
from holders.registry import all_models, resolve_colour_parts, resolve_preview_parts  # noqa: E402
from labels.constants import MAX_TEXT_LENGTH  # noqa: E402
from labels import label_text as lt  # noqa: E402
from labels.label_text import _polygons, load_font, min_feature_width  # noqa: E402
import print_audit  # noqa: E402
from print_audit import audit  # noqa: E402
from tests.audit_record import record  # noqa: E402
from scripts.export import export_3mf_one_object, export_stl  # noqa: E402

SPEC = m.SPEC
URL = 'https://poppystreetspooks.com'
PRESETS = {p.id: p for p in SPEC.presets}
# Tiers (codex on #206): the five per-preset sweeps carrying audit_full
# (colour count, partition, slab exclusion, byte-stable STLs, print audit)
# took bd123's serial 'audit' job past its 60 min timeout, so like
# test_cartridge_holder.test_endpoints they run in the sharded audit_full job
# (holders/** and labels/** PRs, push to main, nightly); test_print_audit.py's
# _BED_ONLY_IDS keeps every non-default preset's bed check in 'audit'.
# Expected colour parts per preset: the first N roles (D3 fold chain, D9).
PART_NAMES = {'default': m.ROLES, 'one-ams': m.ROLES[:4], 'two-colour': m.ROLES[:2],
              'pinned': m.ROLES, 'small': m.ROLES}


def values_of(preset_id: str) -> dict:
    return SPEC.resolve_values(PRESETS[preset_id].values)


@functools.cache
def frame_of(preset_id: str) -> dict:
    return m._frame(values_of(preset_id))


@functools.cache
def preset_case(preset_id: str):
    """(values, colour parts, assembled sign) for one preset, built once."""
    values = values_of(preset_id)
    parts = resolve_colour_parts(SPEC, PRESETS[preset_id].values)
    return values, parts, parts[0][1].fuse(*[p for _, p, _ in parts[1:]]).clean()


@functools.cache
def default_features():
    return m.features(values_of('default'))


def footprint(part, z: float):
    """The part's plan at height z (its downward faces there), as shapely."""
    faces = [f for f in part.faces() if abs(f.center().Z - z) < 1e-6
             and f.normal_at(f.center()).Z < -0.99]
    return unary_union([_polygons(f) for f in faces]).buffer(0)


# --- registration ---------------------------------------------------------

def test_registered_as_a_multi_colour_household_model():
    assert SPEC in all_models()
    assert SPEC.slug == 'holder-tombstone-sign'
    assert SPEC.category_id == 'household' and SPEC.is_multi_colour
    params = {p.name: p for p in SPEC.params}
    for name in m.LINES:
        assert params[name].kind == 'string'
        assert params[name].charset == 'printable-ascii'
        assert params[name].max_length == MAX_TEXT_LENGTH == 24
        assert len(params[name].default) <= MAX_TEXT_LENGTH
    for gone in ('url', 'text_style', 'footer_2', 'detail_1', 'detail_2'):
        assert gone not in params, gone
    assert m.qr_data(m.DEFAULTS) == URL
    colours = params['colours']
    assert colours.kind == 'integer' and type(colours.default) is int
    assert (colours.default, colours.min, colours.max) == (8, 2, 8)
    assert params['margin'].default == 12.0 and params['thickness'].default == 8.0
    assert (params['edge_round'].default, params['edge_round'].min, params['edge_round'].max) == (2.5, 0, 4)
    assert (params['bed_chamfer'].default, params['bed_chamfer'].min, params['bed_chamfer'].max) == (1, 0.4, 1.5)
    assert params['qr_size'].default == 120.0
    assert params['width'].max == m.MAX_WIDTH == 325 and params['height'].max == m.MAX_HEIGHT == 320
    assert list(PRESETS) == ['default', 'one-ams', 'two-colour', 'pinned', 'small']
    assert all(p.default_view is None for p in SPEC.presets)  # face up: the iso view
    assert PRESETS['one-ams'].values == {'colours': 4}
    assert PRESETS['two-colour'].values == {'colours': 2}
    assert all(type(p.values.get('colours', 8)) is int for p in SPEC.presets)
    assert PRESETS['pinned'].values == {'thickness': 8.0, 'retention': 'pin'}
    assert PRESETS['small'].values == {'width': 160.0, 'height': 240.0, 'qr_size': 74.0}
    assert PRESETS['small'].label == 'Small (160 x 240)'
    assert 'Trick Ghastly' not in repr(SPEC)


def test_the_detail_lines_are_gone_from_the_copy():
    """S4 D6/T8: no detail Param in the manifest, and no 'details' promised
    by the published description or the web catalog blurb."""
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    entry = next(e for e in manifest['models'] if e['slug'] == SPEC.slug)
    assert not any(p['name'].startswith('detail') for p in entry['params'])
    assert 'detail' not in SPEC.description
    assert 'detail' not in entry['blurb']
    catalog = (ROOT.parent / 'lib' / 'models' / 'catalog.ts').read_text()
    blurb = re.search(r'holder_tombstone_sign: \{.*?blurb:\s*"([^"]*)"', catalog, re.S)[1]
    assert 'detail' not in blurb and 'scan line' in blurb


def test_review_sections_put_the_pocket_plane_first():
    first, second = SPEC.review_sections
    assert first.origin[0] == signs.POCKET_OFFSET and first.normal == (1, 0, 0)
    assert second.label == 'art row' and second.origin[1] == m.ART_SECTION_Y


def test_fonts_resolve_to_the_vendored_files():
    """load_font raises unless OCCT resolves the face at that style to the file."""
    fonts = ROOT / 'assets' / 'fonts'
    assert {face: load_font(path, style) for face, (path, style) in m.FONTS.items()} == {
        'lexend-medium': 'Lexend', 'lexend-bold': 'Lexend', 'creepster': 'Creepster'}
    for face, (path, _) in m.FONTS.items():
        assert path.parent.parent == fonts and (path.parent / 'OFL.txt').is_file(), face
    assert set(m.FACE.values()) == set(m.FONTS)
    assert m.FACE['title'] == 'creepster'
    assert {n for n, f in m.FACE.items() if f == 'lexend-bold'} == {'scan_line', 'host'}


def test_every_preset_line_strokes_from_the_committed_cache(monkeypatch):
    """Every layout candidate has a current row; misses must be regenerated."""
    nominal = lt._nominal_stroke

    def checked(text, path, style):
        assert lt.stroke_key(text, path, style) in lt.stroke_cache(), (
            f'{text!r} ({Path(path).name}) missing: '
            'run uv run python -m labels.strokes --regen')
        return nominal(text, path, style)

    monkeypatch.setattr(lt, '_nominal_stroke', checked)
    nominal.cache_clear()
    m._ink.cache_clear()
    try:
        for preset in SPEC.presets:
            assert m._frame(values_of(preset.id)) is not None, preset.id
    finally:
        nominal.cache_clear()
        m._ink.cache_clear()


def _scan_float_noise():
    """Bound observed float accumulation against the exact decimal scan grid.

    Scan all radii up to min_feature_width's default 3 mm limit. This is
    3.9968028886505635e-14 mm today, far below one 0.02 mm stroke step.
    """
    radius, index, noise = lt._SCAN_START, 0, 0.0
    while radius < 3.0:
        exact = 2 * (Decimal(str(lt._SCAN_START))
                     + (index - 1) * Decimal(str(lt._SCAN_STEP)))
        noise = max(noise, abs(2 * (radius - lt._SCAN_STEP) - float(exact)))
        radius += lt._SCAN_STEP
        index += 1
    return noise


# Three faces (two style names), including the longest preset label (22 chars).
_STROKE_CASES = (('lexend-medium', 'Show runs dusk to 9 pm'),
                 ('lexend-bold', 'Scan to request a song'),
                 ('creepster', 'Pick the next song!'))


def _assert_live_strokes(cases):
    cache = lt.stroke_cache()
    differences = []
    tolerance = _scan_float_noise()
    for face, text in cases:
        path, style = m.FONTS[face]
        key = lt.stroke_key(text, path, style)
        live = lt.measure_stroke(text, path, style)  # never nominal_stroke/cache
        cached = cache.get(key)
        if cached is None:
            # Retain old rows in the failure message when provenance changed.
            prefix = f'{lt._font_sha(str(path))}:{style.name}:'
            old = [v for k, v in cache.items()
                   if k.startswith(prefix) and k.split(':', 3)[-1] == text]
            differences.append(f'{face} {text!r}: missing current key; '
                               f'cached(old)={old!r}, live={live:.17g}')
        elif not math.isfinite(live) or abs(cached - live) > tolerance:
            differences.append(f'{face} {text!r}: cached={cached:.17g}, '
                               f'live={live:.17g}, delta={live - cached:+.17g} mm')
    assert not differences, ('stroke cache differs (absolute tolerance '
                             f'{tolerance:.17g} mm):\n' + '\n'.join(differences))


@pytest.mark.audit
def test_representative_stroke_cache_matches_live_scans():
    _assert_live_strokes(_STROKE_CASES)


@pytest.mark.audit
@pytest.mark.audit_full
def test_stroke_cache_matches_a_live_scan():
    faces = {(lt._font_sha(str(path)), style.name): face
             for face, (path, style) in m.FONTS.items()}
    cases = []
    for key in lt.stroke_cache():
        sha, style, _, text = key.split(':', 3)
        assert (sha, style) in faces, f'{key!r}: stale face'
        cases.append((faces[sha, style], text))
    _assert_live_strokes(cases)


def test_changed_scan_changes_key_and_comparison_reports_each_string(monkeypatch):
    before = [lt.stroke_key(text, *m.FONTS[face]) for face, text in _STROKE_CASES]

    def perturbed_scan(text, path, style):
        return 123.0  # deliberate scan-code perturbation, no expensive geometry

    monkeypatch.setattr(lt, 'measure_stroke', perturbed_scan)
    assert all(lt.stroke_key(text, *m.FONTS[face]) != key
               for (face, text), key in zip(_STROKE_CASES, before))
    with pytest.raises(AssertionError) as exc:
        _assert_live_strokes(_STROKE_CASES)
    for face, text in _STROKE_CASES:
        assert f'{face} {text!r}: missing current key;' in str(exc.value)
    assert 'cached(old)=' in str(exc.value) and 'live=123' in str(exc.value)


def test_comparison_detects_value_drift_with_current_keys(monkeypatch):
    # Keep the fingerprint current for the fake scanner: exercise the numeric
    # comparison independently of the missing-provenance failure above.
    monkeypatch.setattr(lt, 'measure_stroke', lambda *args, **kwargs: 0.9)
    rows = {lt.stroke_key(text, *m.FONTS[face]): 0.92 for face, text in _STROKE_CASES}
    monkeypatch.setattr(lt, 'stroke_cache', lambda: rows)
    with pytest.raises(AssertionError, match='delta=') as exc:
        _assert_live_strokes(_STROKE_CASES)
    assert all(f'{face} {text!r}: cached=' in str(exc.value) for face, text in _STROKE_CASES)


@pytest.mark.parametrize('dependency', ['build123d', 'fonttools', 'shapely', 'OCP'])
def test_stroke_key_tracks_engine_versions(monkeypatch, dependency):
    before = lt.stroke_key('probe', lt.FONT_PATH, lt.FONT_STYLE)
    version = lt.version
    if dependency == 'OCP':
        monkeypatch.setattr(lt.OCP, '__version__', 'changed')
    else:
        monkeypatch.setattr(lt, 'version', lambda name: 'changed' if name == dependency
                            else version(name))
    assert lt.stroke_key('probe', lt.FONT_PATH, lt.FONT_STYLE) != before


# --- colour roles -----------------------------------------------------------

def test_fold_chain_maps_every_role_for_each_colour_count():
    expected = {  # role -> filament, N = 2 .. 8
        2: {'bone': 'bone', 'pumpkin': 'bone', 'poppy': 'bone', 'leaf': 'bone',
            'dim': 'bone', 'ink': 'hole', 'ember': 'bone'},
        3: {'bone': 'bone', 'pumpkin': 'pumpkin', 'poppy': 'pumpkin', 'leaf': 'pumpkin',
            'dim': 'bone', 'ink': 'hole', 'ember': 'pumpkin'},
        4: {'bone': 'bone', 'pumpkin': 'pumpkin', 'poppy': 'poppy', 'leaf': 'pumpkin',
            'dim': 'bone', 'ink': 'hole', 'ember': 'poppy'},
        5: {'bone': 'bone', 'pumpkin': 'pumpkin', 'poppy': 'poppy', 'leaf': 'leaf',
            'dim': 'bone', 'ink': 'hole', 'ember': 'poppy'},
        6: {'bone': 'bone', 'pumpkin': 'pumpkin', 'poppy': 'poppy', 'leaf': 'leaf',
            'dim': 'dim', 'ink': 'hole', 'ember': 'poppy'},
        7: {'bone': 'bone', 'pumpkin': 'pumpkin', 'poppy': 'poppy', 'leaf': 'leaf',
            'dim': 'dim', 'ink': 'ink', 'ember': 'poppy'},
        8: {r: r for r in m.ROLES[1:]},
    }
    for n, table in expected.items():
        assert {r: m.filament(r, n) for r in m.ROLES[1:]} == table, n
        assert m.filament('hole', n) == 'hole'
    assert m.HEX == {'base': '#120a1e', 'bone': '#f4ecdc', 'pumpkin': '#ff7a1a',
                     'poppy': '#e5322d', 'leaf': '#5b8f3a', 'dim': '#b7a9c9',
                     'ink': '#0a0a0a', 'ember': '#ff5a4e'}


@pytest.mark.audit
@pytest.mark.audit_full
def test_colour_count_gives_exactly_the_first_n_parts():
    values, feats = values_of('default'), default_features()
    for n in range(2, 9):
        parts = m.assemble({**values, 'colours': n}, feats)
        assert [name for name, _, _ in parts] == list(m.ROLES[:n]), n
        assert all(p.is_valid for _, p, _ in parts), n


@pytest.mark.audit
def test_feature_roles_follow_d3():
    roles = {name: role for name, (role, _) in default_features().items()}
    assert roles == {'eyebrow': 'dim', 'title': 'pumpkin', 'scan_line': 'bone',
                     'host': 'pumpkin',
                     'footer_1': 'dim', 'rule': 'dim', 'ghost:bone': 'bone',
                     'ghost:leaf': 'leaf', 'ghost:poppy': 'poppy', 'ghost:ember': 'ember',
                     'qr_light': 'bone', 'qr_dark': 'ink'}


# --- the ghost --------------------------------------------------------------

def test_ghost_keeps_every_element_and_drops_only_the_holes():
    """Twelve SVG elements; each non-hole one survives the document-order
    partition inside its role's region, each hole is in no region. The SVG's
    own comment lists the only art left out (the leaf vein, the seed dots)."""
    elements = sign_ghost.elements()
    assert [(i, r) for i, r, _ in elements] == [
        ('ghost-body', 'bone'), ('eye-left', 'hole'), ('eye-right', 'hole'), ('mouth', 'hole'),
        ('leaf', 'leaf'), ('petal-0', 'poppy'), ('petal-90', 'poppy'), ('petal-180', 'poppy'),
        ('petal-270', 'poppy'), ('petal-45', 'ember'), ('petal-225', 'ember'),
        ('poppy-centre', 'hole')]
    regions = sign_ghost.regions(sign_ghost.VIEW_H)  # scale 1: the SVG's own units
    assert set(regions) == {'bone', 'leaf', 'poppy', 'ember'}
    for ident, role, face in elements:
        for name, region in regions.items():
            shared = (region & face).area if (region & face).faces() else 0.0
            if role == name:
                assert shared > 0.3 * face.area, ident  # visible, not a sliver
            elif role == 'hole':
                assert shared < 1e-6, (ident, name)
    assert 'leaf vein' in sign_ghost.SVG_PATH.read_text()


@pytest.mark.parametrize('qr_size', [74.0, 120.0])
def test_ghost_regions_hold_the_raised_stroke_floor(qr_size):
    for role, region in sign_ghost.regions(m.GHOST_SHARE * qr_size).items():
        assert min_feature_width(_polygons(region), 0.6) >= m.THRESHOLD, role


# --- joint contract -------------------------------------------------------

def test_tenon_dimensions_follow_the_contract_formulas():
    assert signs.POCKET_COUNT == len(signs.POCKET_XS) == 2
    assert signs.tenon_w() == pytest.approx(7.6)
    assert signs.tenon_len() == pytest.approx(34.6)
    assert signs.tenon_t(6.0) == pytest.approx(3.2)
    assert signs.tenon_t(8.0) == pytest.approx(5.2)
    assert signs.POCKET_W <= 9.0 < print_audit.MAX_BRIDGE_MM
    assert signs.MIN_WALL_MM == print_audit.MIN_WALL_MM
    assert signs.PIN_FROM_BOTTOM < signs.POCKET_DEPTH
    assert signs.PIN_AXIS == (1.0, 0.0, 0.0)


@pytest.mark.parametrize('thickness', [5.0, 6.0, 8.0, 12.0])
def test_tenon_section_clears_each_pocket_by_the_joint_clearance(thickness):
    """2D joint test: the tenon's X-Z section sits in each pocket with exactly
    JOINT_CLEARANCE on every side (S2 re-runs this against the real stake)."""
    for x in signs.POCKET_XS:
        pocket, tenon = signs.pocket_rect(x, thickness), signs.tenon_rect(x, thickness)
        assert pocket.contains(tenon)
        (px0, pz0, px1, pz1), (tx0, tz0, tx1, tz1) = pocket.bounds, tenon.bounds
        for gap in (tx0 - px0, px1 - tx1, tz0 - pz0, pz1 - tz1):
            assert gap == pytest.approx(signs.JOINT_CLEARANCE)
    assert signs.POCKET_DEPTH - signs.tenon_len() == pytest.approx(2 * signs.JOINT_CLEARANCE)


def test_pin_needs_a_7_8_mm_plate():
    assert signs.PIN_MIN_THICKNESS == pytest.approx(7.8)
    assert signs.tenon_t(7.8) - signs.PIN_D == pytest.approx(2 * signs.MIN_WALL_MM)
    values = SPEC.resolve_values({'retention': 'pin', 'thickness': 7.6})
    with pytest.raises(ValueError, match=r"thickness >= 7\.8 mm"):
        m.validate(values)


def test_pin_profile_is_pin_d_square_with_a_short_flat_roof():
    face = signs.pin_profile(0, 0)
    bb = face.bounding_box()
    assert bb.size.Y == pytest.approx(signs.PIN_D) and bb.size.Z == pytest.approx(signs.PIN_D)
    roof = [f for f in face.edges() if f.geom_type == GeomType.LINE
            and abs(f.center().Z - signs.PIN_D / 2) < 1e-6 and f.length > 1e-6]
    r = signs.PIN_D / 2
    assert sum(e.length for e in roof) == pytest.approx(2 * r * (math.sqrt(2) - 1))


# --- QR -------------------------------------------------------------------

def test_qr_matrix_is_segnos_matrix_at_level_m():
    qr = segno.make(URL, error='m', micro=False, boost_error=False)
    assert qr.error == 'M' and qr.version == 3
    assert signs.qr_matrix(URL) == tuple(tuple(bool(v) for v in row) for row in qr.matrix)
    assert signs.qr_symbol_size(URL) == qr.symbol_size(border=4)[0] == 37


def test_qr_pitch_for_the_default_and_small_presets():
    assert round(signs.qr_pitch(URL, 120), 2) == 3.24
    assert signs.qr_pitch(URL, 74) == 2.0
    assert signs.min_qr_size(URL) == 74.0
    with pytest.raises(ValueError, match=r'1\.97 mm module pitch.*>= 74 mm'):
        signs.qr_regions(URL, 73)


@pytest.mark.parametrize('qr_size', [74.0, 120.0])
def test_qr_panel_is_rounded_inside_the_quiet_zone(qr_size):
    values = {**m.DEFAULTS, 'qr_size': qr_size}
    dark, light = m.qr_panel(values)
    assert dark.intersection(light).area < 1e-6
    panel = unary_union([dark, light])
    corner_cut = qr_size ** 2 - panel.area
    # buffer(quad_segs=32) rounds each corner with a quarter of a 128-gon,
    # which falls short of the true arc by 0.08 mm^2 in all.
    polygon = 64 * math.sin(2 * math.pi / 128)
    assert corner_cut == pytest.approx((4 - polygon) * m.QR_CORNER_R ** 2, rel=1e-6)
    # The corner arcs reach 6 (1 - 1/sqrt 2) = 1.76 mm in: inside the quiet zone.
    quiet = signs.QR_QUIET * signs.qr_pitch(URL, qr_size)
    assert m.QR_CORNER_R * (1 - 1 / math.sqrt(2)) < quiet
    half = qr_size / 2 - quiet
    assert dark.bounds[0] >= -half - 1e-9 and dark.bounds[2] <= half + 1e-9


# --- guards ---------------------------------------------------------------

def test_width_guard_names_the_pocket_bound():
    with pytest.raises(ValueError, match=r'width 105 mm < 108 mm'):
        m.validate(SPEC.resolve_values({'width': 105.0, 'margin': 10.0, 'qr_size': 80.0}))


def test_art_row_guard_names_the_inset_width():
    with pytest.raises(ValueError, match=r'qr_size 120 mm: the art row .* wider than '
                                         r'width - 2 x margin = 136 mm'):
        m.validate(SPEC.resolve_values({'width': 160.0, 'qr_size': 120.0}))


def test_blank_host_is_a_guard():
    with pytest.raises(ValueError, match=r'host is blank'):
        m.validate(SPEC.resolve_values({'host': '  '}))


def test_rim_guards_name_the_margin_and_the_thickness():
    with pytest.raises(ValueError, match=r'edge_round 3 mm \+ the 0\.9 mm stroke floor must '
                                         r'stay < margin 3\.5 mm.*< 2\.6 mm'):
        m.validate(SPEC.resolve_values({'edge_round': 3.0, 'margin': 3.5}))
    m.validate(SPEC.resolve_values({'edge_round': 2.5, 'margin': 3.5}))
    with pytest.raises(ValueError, match=r'edge_round 4 mm \+ bed_chamfer 1\.5 mm must stay '
                                         r'< thickness 5 mm'):
        m.validate(SPEC.resolve_values({'edge_round': 4.0, 'bed_chamfer': 1.5, 'thickness': 5.0}))


def test_height_below_the_arch_radius_is_a_guard_not_a_kernel_error():
    """Codex B2: a lens outline (arch centre below the bottom edge) used to
    pass validate() and fail in OCCT's fillet."""
    values = SPEC.resolve_values({'width': 325.0, 'height': 160.0, 'margin': 3.0,
                                  'host': 'pb.co/s', 'qr_size': 58.0})
    with pytest.raises(ValueError, match=r'height must be >= 168.5 mm for width 325 mm'):
        m.validate(values)
    m.plate({**values, 'height': 168.5})  # the named minimum builds


@pytest.mark.parametrize('arch', ['round', 'shoulder'])
@pytest.mark.parametrize('width', [100.0, 325.0])
def test_outline_builds_at_its_minimum_height(width, arch):
    signs.outline(width, signs.min_outline_height(width, arch), arch)


def _named_minimum(err) -> float:
    return float(err.value.args[0].rsplit('>= ', 1)[1].split(' mm')[0])


@pytest.mark.audit
def test_height_guard_names_a_minimum_that_works():
    # The default copy at s = 1 needs 266.1 mm; below that s shrinks until a
    # line reaches its stroke floor, and below THAT the guard names the height.
    values = SPEC.resolve_values({'height': 190.0})
    with pytest.raises(ValueError, match=r'height must be >= ([\d.]+) mm') as err:
        m.validate(values)
    m.validate({**values, 'height': _named_minimum(err)})
    assert m.min_height(values_of('small')) <= 240


@pytest.mark.audit
def test_the_old_small_plate_is_too_short_for_the_floors():
    """T4: 160 x 200 needs s ~ 0.68, which puts the eyebrow and the footer
    under their stroke floors; the guard names a height that builds."""
    values = SPEC.resolve_values({'width': 160.0, 'height': 200.0, 'qr_size': 74.0})
    with pytest.raises(ValueError, match=r'height 200 mm cannot hold .* height must be '
                                         r'>= ([\d.]+) mm') as err:
        m.validate(values)
    minimum = _named_minimum(err)
    assert 200 < minimum < 240
    m.validate({**values, 'height': minimum})


@pytest.mark.audit
def test_height_guard_says_when_the_minimum_is_above_the_cap():
    values = SPEC.resolve_values({'width': 325.0, 'height': 320.0, 'qr_size': 170.0})
    with pytest.raises(ValueError, match=r'above the 320 mm maximum: reduce qr_size'):
        m.validate(values)


@pytest.mark.audit
def test_text_below_the_stroke_floor_names_the_line_and_the_longest_fit():
    values = SPEC.resolve_values({**PRESETS['small'].values, 'title': 'W' * 24})
    with pytest.raises(ValueError, match=r"^title: label text 'W{24}'.*the longest that fits is"):
        m.features(values)


# --- the D1-D4 layout (pure 2D; measures the text once per process) ---------

def _gap_after(f: dict, above: str, below: str) -> float:
    return f['bands'][above][0] - f['bands'][below][1]


@pytest.mark.audit
@pytest.mark.parametrize('preset_id', list(PRESETS))
def test_type_classes_and_rhythm_hold_at_every_preset(preset_id):
    """T1: every band is set at its class x s, or (width-bound) shrinks alone
    to the inset box; gaps are 1 U within a group, 2 U between, 1.5 U either
    side of the rule; the leftover goes equally to the art row's flanks."""
    values, f = values_of(preset_id), frame_of(preset_id)
    w, m_, qr = values['width'], values['margin'], values['qr_size']
    s, unit, box_w = f['s'], f['unit'], w - 2 * m_
    assert 0 < s <= 1 and unit == pytest.approx(m_ / 3 * s)
    assert f['leftover'] >= 0 and (s == 1 or f['leftover'] == 0)
    present = [n for n in m.LINES if values[n].strip()]
    assert list(f['lines']) == present
    order = list(f['bands'])
    assert order == [n for n in m.ORDER if n in f['bands']]
    for n in present:
        y_lo, y_hi = f['bands'][n]
        path, style = m.FONTS[m.FACE[n]]
        chord = signs.inner_width(f['region'], y_hi)
        fitted = lt.layout_text(f['lines'][n], chord, y_hi - y_lo, 0.0, m.RAISE_H, m.FLOOR,
                                path, style, max_lines=1, stroke_only=True)
        cap = fitted.scale * m.cap_height(m.FACE[n])  # the 'H' at the fitted size
        width = fitted.part.bounding_box().size.X
        if f['bound'][n]:
            assert width == pytest.approx(box_w, abs=1e-6) and cap < m.CAP[n] * s, n
        else:
            assert cap == pytest.approx(m.CAP[n] * s, rel=0.01), n
            assert width <= box_w + 1e-6, n
        assert width <= chord + 1e-6, n  # inside the arch
        assert fitted.min_stroke >= m.THRESHOLD - 1e-9, n
        assert f['lines'][n].count('\n') < m.MAX_LINES[n]
        # the wrap is the fewest lines that fit the chord at the band top
        fits = [c for c in m._candidates(n, m._line(values, n))
                if m.line_ink(n, c, m.CAP[n] * s)[0] <= chord + 1e-9]
        if fits and not f['bound'][n]:
            assert f['lines'][n] == fits[0], n
    for above, below in zip(order, order[1:]):
        gap = _gap_after(f, above, below)
        if 'rule' in (above, below):
            expected = m.RULE_CLEAR * unit
        elif m.GROUP[above] == m.GROUP[below]:
            expected = unit
        else:
            expected = 2 * unit
        if 'art' in (above, below):
            expected += f['leftover'] / 2
        assert gap == pytest.approx(expected, abs=1e-6), (above, below)  # no preset pushes below the eyebrow
    assert f['bands'][order[0]][1] <= f['top'] + 1e-9
    assert f['bands'][order[-1]][0] == pytest.approx(m_, abs=1e-6)  # on the bottom margin
    art = f['bands']['art']
    assert art[1] - art[0] == pytest.approx(qr)
    assert signs.inner_width(f['region'], art[1]) >= m.art_width(qr, 2 * unit)
    assert box_w >= m.art_width(qr, 2 * unit)
    rule = f['bands']['rule']
    assert rule[1] - rule[0] == pytest.approx(m.RULE_W)


@pytest.mark.audit
def test_default_layout_matches_the_spec_numbers():
    """T2: the S4 D8 numbers as measured on the vendored fonts (layout_text
    at the fitted sizes): s = 1 and exactly four cap sizes, 20 / 11 / 8 / 7."""
    f, values = frame_of('default'), values_of('default')
    assert f['s'] == 1.0 and f['unit'] == 4.0
    assert f['top'] == pytest.approx(273.53, abs=0.01)
    assert f['leftover'] == pytest.approx(8.77, abs=0.01)
    assert sorted(set(f['caps'].values())) == [7.0, 8.0, 11.0, 20.0]
    assert not any(f['bound'].values())
    bands = {n: (round(lo, 2), round(hi, 2)) for n, (lo, hi) in f['bands'].items()}
    assert bands == pytest.approx({
        'eyebrow': (263.11, 270.33), 'title': (214.76, 259.11), 'art': (82.37, 202.37),
        'scan_line': (55.12, 69.99), 'host': (35.88, 51.12), 'rule': (28.97, 29.88),
        'footer_1': (12.00, 22.97)}, abs=0.02)
    upper, lower = _gap_after(f, 'title', 'art'), _gap_after(f, 'art', 'scan_line')
    assert upper == pytest.approx(lower, abs=1e-9)
    assert upper == pytest.approx(2 * f['unit'] + f['leftover'] / 2, abs=1e-6)
    assert upper > 2 * f['unit'] + 4  # the leftover lands here, not on the footer
    assert f['bands']['footer_1'][0] == pytest.approx(values['margin'], abs=1e-6)
    assert f['lines']['title'] == 'Pick the\nnext song!'  # two lines in the arch
    assert f['lines']['eyebrow'] == 'POPPY STREET SPOOKS'  # caps
    eyebrow_top = f['bands']['eyebrow'][1]
    assert f['top'] - eyebrow_top == pytest.approx(3.20, abs=0.02)  # pushed out of the arch
    assert signs.inner_width(f['region'], eyebrow_top) == pytest.approx(
        m.line_ink('eyebrow', f['lines']['eyebrow'], 7.0)[0], abs=1e-6)
    art = f['bands']['art']
    assert art[0] + 30 < m.ART_SECTION_Y < art[1] - 30  # the review section cuts the art


@pytest.mark.audit
def test_small_scales_the_type_down_and_holds_every_floor():
    """T3: 160 x 240 needs s < 1; the scan line and host are width-bound to
    the 136 mm box; the eyebrow is pushed out of the arch; nothing is under
    its stroke floor (s >= every line's floor cap / class cap)."""
    f, values = frame_of('small'), values_of('small')
    assert values['width'] - 2 * values['margin'] == 136
    assert list(f['bands']) == ['eyebrow', 'title', 'art', 'scan_line', 'host', 'rule',
                                'footer_1']
    assert f['s'] == pytest.approx(0.926, abs=0.001) and f['leftover'] == 0
    assert f['bound'] == {'eyebrow': False, 'title': False, 'scan_line': True, 'host': True,
                          'footer_1': False}
    for n in ('scan_line', 'host'):
        assert m.line_ink(n, f['lines'][n], f['caps'][n])[0] == pytest.approx(136, abs=1e-6)
    for n, cap in f['caps'].items():
        assert m.line_ink(n, f['lines'][n], cap)[2] >= m.THRESHOLD, n
    eyebrow_top = f['bands']['eyebrow'][1]
    assert f['top'] == pytest.approx(218.89, abs=0.01)
    assert f['top'] - eyebrow_top > 18  # pushed ~18.7 mm down
    assert signs.inner_width(f['region'], eyebrow_top) == pytest.approx(
        m.line_ink('eyebrow', f['lines']['eyebrow'], f['caps']['eyebrow'])[0], abs=1e-6)
    assert f['lines']['title'].count('\n') == 1


@pytest.mark.audit
def test_footer_is_present_unless_blank():
    for preset_id in PRESETS:
        assert 'footer_1' in frame_of(preset_id)['bands'], preset_id
    assert 'rule' in default_features() and 'footer_1' in default_features()
    f = m._frame(SPEC.resolve_values({'footer_1': ''}))
    assert 'footer_1' not in f['bands'] and 'rule' not in f['bands']
    assert list(f['bands'])[-1] == 'host'


# --- geometry (one build per preset) --------------------------------------

@pytest.mark.audit
@pytest.mark.audit_full
@pytest.mark.parametrize('preset_id', list(PRESETS))
def test_colour_parts_partition_the_raised_slab(preset_id):
    values, parts, whole = preset_case(preset_id)
    t = values['thickness']
    assert [n for n, _, _ in parts] == list(PART_NAMES[preset_id])
    assert all(p.is_valid for _, p, _ in parts) and whole.is_valid
    assert len(whole.solids()) == 1
    base, raised = parts[0][1], parts[1:]
    assert base.volume == pytest.approx(m.plate(values).volume, rel=1e-9)
    # The raised parts fill exactly what the fused sign adds over the plate.
    # rel 1e-5, not 1e-6: OCCT's volume integral is not exact on the ghost
    # body's Bezier/B-spline walls — that one solid integrates to 591.846 mm^3
    # alone and adds 591.812 when fused (its bottom face x 0.6 = 591.863), a
    # 0.03 mm^3 drift on ~9050 mm^3 of slab; adaptive GProp eps is worse (+3).
    added = whole.volume - base.volume
    assert sum(p.volume for _, p, _ in raised) == pytest.approx(added, rel=1e-5)
    for i, (a, pa, _) in enumerate(raised):
        bb = pa.bounding_box()
        assert bb.min.Z == pytest.approx(t) and bb.max.Z == pytest.approx(t + m.RAISE_H), a
        for b, pb, _ in raised[i + 1:]:
            assert _overlap(pa, pb) <= 1e-6, (a, b)


def _overlap(a, b) -> float:
    """Shared volume of two multi-solid parts, skipping solid pairs whose boxes only touch."""
    def boxes_meet(p, q):
        bp, bq = p.bounding_box(), q.bounding_box()
        return all(min(tuple(bp.max)[k], tuple(bq.max)[k])
                   - max(tuple(bp.min)[k], tuple(bq.min)[k]) > 1e-6 for k in range(3))
    shared = (p & q for p in a.solids() for q in b.solids() if boxes_meet(p, q))
    return sum(r.volume for r in shared if r is not None)  # an empty Solid & Solid is None


def _common_volume(a, b) -> float:
    """Volume of a & b by one OCCT Common run in parallel (build123d's & is serial)."""
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(a.wrapped)
    tools.Append(b.wrapped)
    op = BRepAlgoAPI_Common()
    op.SetArguments(args)
    op.SetTools(tools)
    op.SetRunParallel(True)
    op.Build()
    assert op.IsDone()
    return Compound(op.Shape()).volume


@pytest.mark.audit
def test_raised_parts_sit_on_the_plate_without_entering_it():
    _, parts, _ = preset_case('default')
    base, raised = parts[0][1], parts[1:]
    assert _common_volume(base, Compound([s for _, p, _ in raised for s in p.solids()])) < 1e-6


@pytest.mark.audit
@pytest.mark.parametrize('preset_id', ['default', 'two-colour'])
def test_holes_show_the_plate_and_the_qr_reads_back(preset_id):
    """D8: sampled at every module centre, the printed QR is segno's symbol for
    https://{host} (quiet zone included), with dark = ink when ink is active,
    else the plate showing through. The ghost's eyes, mouth and poppy centre
    are in no part."""
    values, parts, _ = preset_case(preset_id)
    t = values['thickness']
    plans = {name: footprint(p, t) for name, p, _ in parts[1:]}
    _, (qx, qy) = m.art_layout(values, frame_of(preset_id))
    qr = segno.make(m.qr_data(values), error='m', micro=False, boost_error=False)
    pitch = signs.qr_pitch(m.qr_data(values), values['qr_size'])
    half = values['qr_size'] / 2
    dark_colour = 'ink' if 'ink' in plans else None
    for r, row in enumerate(qr.matrix_iter(border=4)):
        for c, dark in enumerate(row):
            if min(r, c, len(qr.matrix) + 7 - r, len(qr.matrix) + 7 - c) == 0:
                continue  # the outer ring: its corner modules are rounded off the panel
            p = Point(qx - half + (c + 0.5) * pitch, qy + half - (r + 0.5) * pitch)
            hit = [n for n, plan in plans.items() if plan.contains(p)]
            assert hit == ([dark_colour] if dark and dark_colour else [] if dark
                           else ['bone']), (r, c, hit)
    (gx, gy), _ = m.art_layout(values, frame_of(preset_id))
    k = m.GHOST_SHARE * values['qr_size'] / sign_ghost.VIEW_H
    for ident, role, face in sign_ghost.elements():
        if role == 'hole':
            cx, cy = face.center().X, face.center().Y
            p = Point(gx + cx * k, gy + cy * k)
            assert not any(plan.contains(p) for plan in plans.values()), ident


@pytest.mark.audit
@pytest.mark.audit_full
@pytest.mark.parametrize('preset_id', list(PRESETS))
def test_slab_exclusion_contains_every_raised_feature(preset_id):
    """The direction the S1 docstring claimed but nothing checked: the slab
    box holds every raised region (from the margin floor up), and nothing but."""
    values, parts, whole = preset_case(preset_id)
    x0, y0, z0, x1, y1, z1 = m.audit_exclusions(values)[-1]
    assert y0 == pytest.approx(values['margin'], abs=0.01)
    for name, part, _ in parts[1:]:
        bb = part.bounding_box()
        assert (x0 <= bb.min.X and bb.max.X <= x1 and y0 <= bb.min.Y and bb.max.Y <= y1
                and z0 <= bb.min.Z and bb.max.Z <= z1), name
    if preset_id == 'default':
        slab = Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)
        raised = sum(p.volume for _, p, _ in parts[1:])
        assert (whole & slab).volume == pytest.approx(raised, rel=1e-3)  # plus a 1e-6 skin of plate


@pytest.mark.audit
@pytest.mark.parametrize('preset_id', ['default', 'pinned'])
def test_pockets_and_pin_hole(preset_id):
    values, _, whole = preset_case(preset_id)
    t = values['thickness']
    for x in signs.POCKET_XS:
        for y in (0.5, 17.5, signs.POCKET_DEPTH - 0.5):
            assert not whole.is_inside(Vector(x, y, t / 2))
            assert whole.is_inside(Vector(x, y, signs.SKIN / 2))
            assert whole.is_inside(Vector(x, y, t - signs.SKIN / 2))
        assert whole.is_inside(Vector(x, signs.POCKET_DEPTH + 0.5, t / 2))
    pin_point = Vector(0, signs.PIN_FROM_BOTTOM, t / 2)
    assert whole.is_inside(pin_point) == (values['retention'] == 'friction')


@pytest.mark.audit
def test_preview_parts_are_the_colour_parts():
    names = [n for n, _, _ in resolve_preview_parts(SPEC, PRESETS['two-colour'].values)]
    assert names == ['base', 'bone']


@pytest.mark.audit
def test_3mf_is_one_object_with_a_part_per_filament(tmp_path):
    _, parts, _ = preset_case('default')
    assert len(parts) == 8
    export_3mf_one_object(parts, tmp_path / 'sign.3mf', 'tombstone')  # raises if not manifold
    import zipfile
    config = zipfile.ZipFile(tmp_path / 'sign.3mf').read('Metadata/model_settings.config').decode()
    for filament, name in enumerate(m.ROLES, start=1):
        assert f'<metadata key="name" value="{name}"/>' in config
        assert f'<metadata key="extruder" value="{filament}"/>' in config


_WRITE = '''
import sys; sys.path.insert(0, {root!r})
from holders.tombstone_sign import SPEC, colour_parts
from scripts.export import export_stl
for name, shape, _ in colour_parts(SPEC.resolve_values({values!r})):
    export_stl(shape, {out!r} + '-' + name + '.stl')
'''


@pytest.mark.audit
@pytest.mark.audit_full
def test_part_stls_are_byte_stable_across_processes(tmp_path):
    values = PRESETS['small'].values
    _, parts, _ = preset_case('small')
    for name, shape, _ in parts:
        export_stl(shape, str(tmp_path / f'a-{name}.stl'))
    subprocess.run([sys.executable, '-c', _WRITE.format(root=str(ROOT), values=values,
                                                        out=str(tmp_path / 'b'))],
                   cwd=ROOT, check=True, capture_output=True)
    for name, _, _ in parts:
        a, b = (tmp_path / f'{run}-{name}.stl' for run in 'ab')
        assert a.read_bytes() == b.read_bytes(), name


# --- print audit + edges --------------------------------------------------

@pytest.mark.audit
@pytest.mark.audit_full
@pytest.mark.parametrize('preset_id', list(PRESETS))
def test_print_audit_per_preset(preset_id, capsys):
    """Unexcluded, the only failure is the flat pocket roofs (and the pin
    hole's 1.33 mm flat): measured as bridges <= POCKET_W first, then
    excluded as exact thin planes. The raised-feature slab is excluded in
    both runs (see test_slab_exclusion_contains_every_raised_feature)."""
    values, parts, whole = preset_case(preset_id)
    regions = m.audit_exclusions(values)
    raw = audit(whole, SPEC.print_orientation, exclusions=regions[-1:], model=f'{preset_id} raw')
    assert raw.longest_bridge_mm == pytest.approx(signs.POCKET_W, abs=0.5)
    assert all('overhang' in f for f in raw.failures()), raw.format()
    report = audit(whole, SPEC.print_orientation, exclusions=regions, model=preset_id)
    with capsys.disabled():
        print(f'\n{preset_id:11} raw_overhang={raw.max_overhang_deg:.1f} '
              f'raw_bridge={raw.longest_bridge_mm:.2f} overhang={report.max_overhang_deg:.1f} '
              f'bridge={report.longest_bridge_mm:.2f} min_wall={report.min_wall_mm:.3f} '
              f'volume={whole.volume:.0f} parts={len(parts)} ok={report.ok}')
    record(preset_id, wall=report.min_wall_mm, overhang=report.max_overhang_deg,
           bridge=report.longest_bridge_mm, volume=whole.volume, parts=len(parts),
           result='PASS' if report.ok else 'FAIL')
    assert report.ok, report.format()
    assert report.max_overhang_deg <= 45.0 + 1e-3


@pytest.mark.audit
def test_raw_audit_fails_only_on_the_excluded_ceilings():
    """Every downward face steeper than 45 degrees lies in an approved plane."""
    values, _, whole = preset_case('pinned')
    boxes = m.audit_exclusions(values)
    for face in whole.faces():
        n = face.normal_at(face.center())
        if n.Z < -0.75 and face.center().Z > 1e-3:  # a downward ceiling above the bed
            c = face.center()
            assert any(x0 <= c.X <= x1 and y0 <= c.Y <= y1 and z0 <= c.Z <= z1
                       for x0, y0, z0, x1, y1, z1 in boxes), c


def unfinished_edges(values, plate):
    """Plate edges that are neither eased (on a 45-degree rim chamfer),
    tangent (outline seams, and every edge of the top round-over) nor joint
    (pocket / pin: mating, left sharp)."""
    t = values['thickness']
    joint = [(x - signs.POCKET_W / 2 - 1e-3, x + signs.POCKET_W / 2 + 1e-3) for x in signs.POCKET_XS]
    bad = []
    for edge in plate.edges():
        c = edge.center()
        faces = [f for f in plate.faces() if any(e.is_same(edge) for e in f.edges())]
        normals = [f.normal_at(c) for f in faces]
        # 45 degrees, or up to ~2 degrees STEEPER on the bed rim's corner
        # ramp, whose chamfer tilts as its size changes (never an overhang)
        chamfered = any(-0.03 < abs(n.Z) - math.sqrt(0.5) < 1e-3 for n in normals)
        tangent = len(normals) == 2 and normals[0].dot(normals[1]) > 0.999
        in_pocket = c.Y <= signs.POCKET_DEPTH + 1e-3 and any(a <= c.X <= b for a, b in joint) \
            and signs.SKIN - 1e-3 <= c.Z <= t - signs.SKIN + 1e-3
        in_pin = values['retention'] == 'pin' and abs(c.Y - signs.PIN_FROM_BOTTOM) <= signs.PIN_D
        if not (chamfered or tangent or in_pocket or in_pin):
            bad.append((round(c.X, 2), round(c.Y, 2), round(c.Z, 2)))
    return bad


@pytest.mark.parametrize('preset_id', ['default', 'pinned'])
def test_every_plate_edge_is_eased_tangent_or_a_mating_edge(preset_id):
    """Rims carry the round-over / bed chamfer; outline seams are tangent;
    pocket and pin edges are the joint (mating, left sharp). Raised feature
    edges are the feature (sharp, as on the label card)."""
    values = values_of(preset_id)
    assert not unfinished_edges(values, m.plate(values))


def _eased(plate, point, inward, up, depth):
    """Is the rim corner at `point` cut back `depth` along the diagonal
    (`inward` in plan, `up` = +-Z into the plate)?"""
    return not plate.is_inside(point + inward * depth + up * depth)


@pytest.mark.parametrize('overrides', [{}, {'arch': 'shoulder', 'edge_round': 1.5},
                                       {'edge_round': 0.0}])
def test_pocket_edge_keeps_04_and_the_arch_and_sides_take_edge_round_and_bed_chamfer(overrides):
    """A rim eased by a 45-degree chamfer d is cut along its corner diagonal
    to d / 2, a round-over r to r (1 - 1/sqrt 2); probe 10 % either side.
    The Y = 0 pocket edge keeps 0.4 on both rims (a 0.4 round on top), so a
    2.5 round-over cannot reach the 1.2 mm skin over the pocket mouths."""
    values = SPEC.resolve_values(overrides)
    plate = m.plate(values)
    w, h, t = values['width'], values['height'], values['thickness']
    r, d = values['edge_round'], values['bed_chamfer']
    top_cut = r * (1 - math.sqrt(0.5)) if r else m.EDGE_CHAMFER / 2
    pocket_top_cut = m.EDGE_CHAMFER * (1 - math.sqrt(0.5)) if r else m.EDGE_CHAMFER / 2
    down, up = Vector(0, 0, -1), Vector(0, 0, 1)
    rims = [  # (point on the outline at Z 0, inward, top cut, bed cut)
        (Vector(0, 0, 0), Vector(0, 1, 0), pocket_top_cut, m.EDGE_CHAMFER / 2),
        (Vector(signs.POCKET_OFFSET + 8, 0, 0), Vector(0, 1, 0), pocket_top_cut,
         m.EDGE_CHAMFER / 2),
        (Vector(w / 2, h / 3, 0), Vector(-1, 0, 0), top_cut, d / 2),
        (Vector(-w / 2, h / 3, 0), Vector(1, 0, 0), top_cut, d / 2),
        (Vector(0, h, 0), Vector(0, -1, 0), top_cut, d / 2),
    ]
    for point, inward, top, bed in rims:
        crown = point + Vector(0, 0, t)
        assert _eased(plate, crown, inward, down, 0.9 * top), (point, 'top')
        assert not _eased(plate, crown, inward, down, 1.1 * top), (point, 'top')
        assert _eased(plate, point, inward, up, 0.9 * bed), (point, 'bed')
        assert not _eased(plate, point, inward, up, 1.1 * bed), (point, 'bed')
