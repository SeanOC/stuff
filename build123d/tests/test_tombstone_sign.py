"""Tombstone sign (S1 pst-tl4ac.1): joint contract, QR, guards, colour parts, audit, edges."""
import functools
import math
import subprocess
import sys
from pathlib import Path

import pytest
import segno

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from build123d import Compound, GeomType, Plane, Vector, mirror  # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common  # noqa: E402
from OCP.TopTools import TopTools_ListOfShape  # noqa: E402
from holders import signs  # noqa: E402
from holders import tombstone_sign as m  # noqa: E402
from holders.registry import all_models, resolve_colour_parts, resolve_preview_parts  # noqa: E402
from labels.constants import INLAY_DEPTH, MAX_TEXT_LENGTH  # noqa: E402
import print_audit  # noqa: E402
from print_audit import audit  # noqa: E402
from scripts.export import export_3mf_one_object, export_stl  # noqa: E402

SPEC = m.SPEC
URL = 'https://poppystreetspooks.com'
PRESETS = {p.id: p for p in SPEC.presets}
# Geometry cases: every preset plus the one enum corner no preset covers.
CASES = {**{p.id: p.values for p in SPEC.presets}, 'colours-two': {'colours': 'two'}}


@functools.cache
def preset_case(preset_id: str):
    """(values, colour parts, assembled plate) for one preset, built once."""
    values = SPEC.resolve_values(CASES[preset_id])
    return values, resolve_colour_parts(SPEC, CASES[preset_id]), SPEC.build(values)


# --- registration ---------------------------------------------------------

def test_registered_as_a_multi_colour_household_model():
    assert SPEC in all_models()
    assert SPEC.slug == 'holder-tombstone-sign'
    assert SPEC.category_id == 'household' and SPEC.is_multi_colour
    params = {p.name: p for p in SPEC.params}
    for name in m.LINES:
        assert params[name].kind == 'string'
        assert params[name].max_length == MAX_TEXT_LENGTH
        assert params[name].charset == 'printable-ascii'
    assert params['url'].max_length == 64 and len(params['url'].default) == 29
    assert params['width'].max == m.MAX_WIDTH == 325 and params['height'].max == m.MAX_HEIGHT == 320
    assert params['thickness'].default == 6.0
    views = {p.id: p.default_view for p in SPEC.presets}
    assert views == {'default': 'bottom', 'three-colour': 'bottom', 'raised': None,
                     'pinned': 'bottom', 'small': 'bottom'}
    assert PRESETS['pinned'].values == {'thickness': 8.0, 'retention': 'pin'}
    assert PRESETS['small'].values == {'width': 160.0, 'height': 200.0, 'qr_size': 74.0}


def test_review_sections_put_the_pocket_plane_first():
    first, second = SPEC.review_sections
    assert first.origin[0] == signs.POCKET_OFFSET and first.normal == (1, 0, 0)
    assert second.label == 'QR centre'


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
    m.validate(SPEC.resolve_values({'retention': 'pin', 'thickness': 7.8}))


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
    assert round(signs.qr_pitch(URL, 100), 2) == 2.70
    assert signs.qr_pitch(URL, 74) == 2.0
    assert signs.min_qr_size(URL) == 74.0
    with pytest.raises(ValueError, match=r'1\.97 mm module pitch.*>= 74 mm'):
        signs.qr_regions(URL, 73)


def test_qr_regions_partition_the_block():
    dark, light = signs.qr_regions(URL, 100)
    assert dark.intersection(light).area < 1e-6
    assert dark.area + light.area == pytest.approx(100 * 100)
    modules = sum(map(sum, signs.qr_matrix(URL)))
    assert dark.area == pytest.approx(modules * (100 / 37) ** 2, rel=0.01)  # eps shrink only


# --- guards ---------------------------------------------------------------

def test_width_guard_names_the_pocket_bound():
    with pytest.raises(ValueError, match=r'width 105 mm < 108 mm'):
        m.validate(SPEC.resolve_values({'width': 105.0, 'margin': 10.0, 'qr_size': 80.0}))


def test_qr_size_guard_names_the_inset_width():
    with pytest.raises(ValueError, match=r'qr_size 150 mm > width - 2 x margin = 148 mm'):
        m.validate(SPEC.resolve_values({'width': 160.0, 'qr_size': 150.0}))


def test_height_guard_names_a_minimum_that_works():
    values = SPEC.resolve_values({'height': 180.0})
    with pytest.raises(ValueError, match=r'height must be >= ([\d.]+) mm') as err:
        m.validate(values)
    minimum = float(err.value.args[0].rsplit('>= ', 1)[1].split(' mm')[0])
    m.validate({**values, 'height': minimum})
    assert m.min_height(SPEC.resolve_values(PRESETS['small'].values)) <= 200


def test_height_guard_says_when_the_minimum_is_above_the_cap():
    values = SPEC.resolve_values({'width': 325.0, 'height': 320.0, 'qr_size': 200.0})
    with pytest.raises(ValueError, match=r'above the 320 mm maximum: reduce qr_size'):
        m.validate(values)


def test_height_below_the_arch_radius_is_a_guard_not_a_kernel_error():
    """Codex B2: a lens outline (arch centre below the bottom edge) used to
    pass validate() and fail in OCCT's fillet."""
    values = SPEC.resolve_values({'width': 325.0, 'height': 160.0, 'margin': 3.0,
                                  'url': 'pb.co/s', 'qr_size': 58.0})
    with pytest.raises(ValueError, match=r'height must be >= 168.5 mm for width 325 mm'):
        m.validate(values)
    m.plate({**values, 'height': 168.5})  # the named minimum builds


@pytest.mark.parametrize('arch', ['round', 'shoulder'])
@pytest.mark.parametrize('width', [100.0, 325.0])
def test_outline_builds_at_its_minimum_height(width, arch):
    signs.outline(width, signs.min_outline_height(width, arch), arch)


def test_text_below_the_stroke_floor_names_the_line_and_the_longest_fit():
    values = SPEC.resolve_values({**PRESETS['small'].values, 'title': 'W' * 24})
    with pytest.raises(ValueError, match=r"^title: label text 'W{24}'.*the longest that fits is"):
        m.features(values)


def test_every_band_and_the_qr_sit_above_the_inlay_floor():
    for preset in SPEC.presets:
        values = SPEC.resolve_values(preset.values)
        frame = m._frame(values)
        for name in (*m.LINES, 'qr'):
            assert frame[name][0] >= signs.INLAY_FLOOR - 1e-9, (preset.id, name)
        assert frame['qr'][2] >= values['qr_size']


# --- geometry (one build per preset) --------------------------------------

@pytest.mark.audit
@pytest.mark.parametrize('preset_id', list(CASES))
def test_colour_parts_partition_the_plate(preset_id):
    values, parts, whole = preset_case(preset_id)
    names = [n for n, _, _ in parts]
    expected = {'default': ['base', 'bone', 'ink', 'accent'],
                'three-colour': ['base', 'bone', 'ink'],
                'raised': ['base', 'bone'],
                'pinned': ['base', 'bone', 'ink', 'accent'],
                'small': ['base', 'bone', 'ink', 'accent'],
                'colours-two': ['base', 'ink']}[preset_id]
    assert names == expected
    assert all(p.is_valid for _, p, _ in parts) and whole.is_valid
    total = sum(p.volume for _, p, _ in parts)
    assert total == pytest.approx(whole.volume, rel=1e-3)
    # The base is disjoint from the inlays by construction (it is the plate
    # minus their pockets); test_colour_parts_are_pairwise_disjoint proves it
    # with booleans once. Here the colours are checked against each other,
    # boolean-testing only the glyph solids whose boxes overlap.
    for i, (a, pa, _) in enumerate(parts[1:]):
        for b, pb, _ in parts[i + 2:]:
            assert _overlap(pa, pb) < 1e-3, (a, b)
    t = values['thickness']
    for name, part, _ in parts[1:]:
        bb = part.bounding_box()
        assert bb.min.Y >= signs.INLAY_FLOOR - 1e-6, name
        if values['text_style'] == 'inlaid':
            assert bb.min.Z == pytest.approx(0, abs=1e-6)
            assert bb.max.Z == pytest.approx(INLAY_DEPTH)
        else:
            assert bb.min.Z == pytest.approx(t) and bb.max.Z == pytest.approx(t + INLAY_DEPTH)


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
@pytest.mark.audit_full
def test_colour_parts_are_pairwise_disjoint():
    """Full booleans on the four-colour default, base included.

    The base meets ALL inlay solids in one parallel Common: the shared volume
    is zero iff every base/inlay pair's is, and one pass over the 1.7k-face
    base takes ~25 s where three serial ones took ~130 s (local). The per-pair
    version pushed the sweep's shard 3 past its 30 min ceiling, because this
    test sorts last and runs alone at the shard's tail.
    """
    _, parts, _ = preset_case('default')
    base, inlays = parts[0][1], parts[1:]
    assert _common_volume(base, Compound([s for _, p, _ in inlays for s in p.solids()])) < 1e-3
    for i, (a, pa, _) in enumerate(inlays):
        for b, pb, _ in inlays[i + 1:]:
            assert _overlap(pa, pb) < 1e-3, (a, b)


@pytest.mark.audit
def test_inlays_are_mirrored_for_face_down():
    values, parts, _ = preset_case('default')
    accent = dict((n, p) for n, p, _ in parts)['accent']
    title = m.features(values)['title']
    assert (accent & mirror(title, Plane.YZ)).volume == pytest.approx(accent.volume, rel=1e-6)
    # 'P' (the first letter) prints on the +X side: it reads left to right face up.
    first = min(title.solids(), key=lambda s: s.center().X)
    assert (accent & mirror(first, Plane.YZ)).volume == pytest.approx(first.volume, rel=1e-6)
    assert mirror(first, Plane.YZ).center().X > 0


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
def test_preview_parts_for_inlaid_only():
    assert resolve_preview_parts(SPEC, PRESETS['raised'].values) is None
    names = [n for n, _, _ in resolve_preview_parts(SPEC, PRESETS['three-colour'].values)]
    assert names == ['base', 'bone', 'ink']


@pytest.mark.audit
def test_3mf_is_one_object_with_a_part_per_filament(tmp_path):
    _, parts, _ = preset_case('default')
    export_3mf_one_object(parts, tmp_path / 'sign.3mf', 'tombstone')  # raises if not manifold
    import zipfile
    config = zipfile.ZipFile(tmp_path / 'sign.3mf').read('Metadata/model_settings.config').decode()
    for filament, name in enumerate(['base', 'bone', 'ink', 'accent'], start=1):
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
@pytest.mark.parametrize('preset_id', list(PRESETS))
def test_print_audit_per_preset(preset_id, capsys):
    """Unexcluded, the only failure is the flat pocket roofs (and the pin
    hole's 1.33 mm flat): measured as bridges <= POCKET_W first, then
    excluded as exact thin planes. Raised keeps its raised-feature slab
    excluded in both runs (see test_raised_slab_holds_only_the_raised_features)."""
    values, parts, whole = preset_case(preset_id)
    regions = m.audit_exclusions(values)
    raised = regions[-1:] if values['text_style'] == 'raised' else []
    raw = audit(whole, SPEC.print_orientation, exclusions=raised, model=f'{preset_id} raw')
    assert raw.longest_bridge_mm == pytest.approx(signs.POCKET_W, abs=0.5)
    assert all('overhang' in f for f in raw.failures()), raw.format()
    report = audit(whole, SPEC.print_orientation, exclusions=regions, model=preset_id)
    with capsys.disabled():
        print(f'\n{preset_id:13} raw_overhang={raw.max_overhang_deg:.1f} '
              f'raw_bridge={raw.longest_bridge_mm:.2f} overhang={report.max_overhang_deg:.1f} '
              f'bridge={report.longest_bridge_mm:.2f} min_wall={report.min_wall_mm:.3f} '
              f'volume={whole.volume:.0f} ok={report.ok}')
    assert report.ok, report.format()
    assert report.max_overhang_deg <= 45.0 + 1e-3


@pytest.mark.audit
def test_raised_slab_holds_only_the_raised_features():
    from build123d import Box, Pos
    values, parts, whole = preset_case('raised')
    x0, y0, z0, x1, y1, z1 = m.audit_exclusions(values)[-1]
    slab = Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)
    raised = parts[1][1]
    assert z0 > values['thickness'] and z1 > values['thickness'] + INLAY_DEPTH
    inside = (whole & slab).volume
    assert inside == pytest.approx((raised & slab).volume, rel=1e-6)
    assert inside == pytest.approx(raised.volume, rel=1e-3)  # all but the 1e-4 skin


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


def unfinished_edges(values, whole):
    """Plate edges that are neither eased (on a 45-degree rim chamfer),
    tangent (outline seams) nor joint (pocket / pin: mating, left sharp)."""
    t = values['thickness']
    joint = [(x - signs.POCKET_W / 2 - 1e-3, x + signs.POCKET_W / 2 + 1e-3) for x in signs.POCKET_XS]
    bad = []
    for edge in whole.edges():
        c = edge.center()
        faces = [f for f in whole.faces() if any(e.is_same(edge) for e in f.edges())]
        normals = [f.normal_at(c) for f in faces]
        chamfered = any(abs(abs(n.Z) - math.sqrt(0.5)) < 1e-3 for n in normals)
        tangent = len(normals) == 2 and normals[0].dot(normals[1]) > 0.999
        in_pocket = c.Y <= signs.POCKET_DEPTH + 1e-3 and any(a <= c.X <= b for a, b in joint) \
            and signs.SKIN - 1e-3 <= c.Z <= t - signs.SKIN + 1e-3
        in_pin = values['retention'] == 'pin' and abs(c.Y - signs.PIN_FROM_BOTTOM) <= signs.PIN_D
        if not (chamfered or tangent or in_pocket or in_pin):
            bad.append((round(c.X, 2), round(c.Y, 2), round(c.Z, 2)))
    return bad


@pytest.mark.audit
@pytest.mark.parametrize('preset_id', ['default', 'pinned'])
def test_every_plate_edge_is_eased_tangent_or_a_mating_edge(preset_id):
    """Rims carry the 0.4 chamfer; outline seams are tangent; pocket and pin
    edges are the joint (mating, left sharp)."""
    values, _, whole = preset_case(preset_id)
    assert not unfinished_edges(values, whole)
