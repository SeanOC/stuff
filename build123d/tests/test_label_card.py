"""Label card (labels L2, pst-qznya): text rules, fit, wrap, mirror, 3MF, audit, edges."""
import functools
import locale
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from build123d import Axis, Plane, Pos, Rectangle, section  # noqa: E402
from holders.label_card import SPEC, STROKE_FLOOR, card, colour_parts, fitted_text  # noqa: E402
from holders.registry import Param, _validate_param, all_models, resolve_colour_parts  # noqa: E402
from labels import constants as C  # noqa: E402
from labels.label_text import FLOOR_MARGIN, fit_text, layout_text, two_lines  # noqa: E402
from print_audit import MIN_WALL_MM, audit  # noqa: E402
from scripts.export import export_3mf_one_object, export_stl  # noqa: E402

# Longest strings each style accepts that we pin (A3): 24 characters inlaid
# (two lines, the thinnest accepted stroke found), 18 raised.
LONGEST = {'inlaid': 'Polymaker PolyTerra Teal', 'raised': 'PETG HF JADE WHITE'}
TOO_LONG = 'Bambu PLA Matte Charcoal'  # 24 characters, 0.69 mm on two lines


@functools.cache
def case(style: str, text: str):
    """(values, fitted text, colour parts, assembled card) for one label."""
    values = SPEC.resolve_values({'text': text, 'text_style': style})
    return values, fitted_text(values), colour_parts(values), SPEC.build(values)


def test_registered_as_multi_colour_label():
    spec = next(s for s in all_models() if s.name == 'holder_label_card')
    assert not spec.is_smoke and spec.is_multi_colour and spec.category_id == 'label'
    assert [(p.id, p.values['text_style']) for p in spec.presets] == [
        ('inlaid', 'inlaid'), ('raised', 'raised')]
    text = next(p for p in spec.params if p.name == 'text')
    assert (text.default, text.max_length, text.charset) == ('Filament', 24, 'printable-ascii')
    assert spec.resolve_values()['text_style'] == 'inlaid'


@pytest.mark.parametrize('bad', ['x' * 25, 'Grün', 'a\nb', 'tab\there', '\x7f'])
def test_text_param_rejects_long_or_non_printable_ascii(bad):
    with pytest.raises(ValueError):
        SPEC.resolve_values({'text': bad})


def test_text_param_accepts_the_whole_printable_range():
    SPEC.resolve_values({'text': 'x' * 24})
    SPEC.resolve_values({'text': ' ~!@#'})


@pytest.mark.parametrize('param', [
    Param('n', 'number', 1, max_length=3),
    Param('s', 'string', 'x', charset='latin-1'),
    Param('s', 'string', 'abcd', max_length=3),
    Param('s', 'string', 'é', charset='printable-ascii'),
    Param('s', 'string', 'x', max_length=0),
])
def test_registry_rejects_bad_text_rules(param):
    assert _validate_param(param)


def assert_fits_and_centred(fitted):
    bb = fitted.part.bounding_box()
    assert bb.size.X <= C.CARD_W - 2 * C.TEXT_MARGIN + 1e-6
    assert bb.size.Y <= C.CARD_H - 2 * C.TEXT_MARGIN + 1e-6
    assert abs(bb.center().X) < 1e-6 and abs(bb.center().Y) < 1e-6
    assert (bb.min.Z, bb.max.Z) == pytest.approx((0, C.INLAY_DEPTH), abs=1e-6)


@pytest.mark.parametrize('style', ['inlaid', 'raised'])
def test_petg_cf_builds_on_one_line(style):
    values, fitted, parts, part = case(style, 'PETG-CF')
    assert part.is_valid and len(part.solids()) == 1
    assert fitted.lines == ('PETG-CF',)
    assert fitted.min_stroke >= STROKE_FLOOR[style]
    assert_fits_and_centred(fitted)


def test_24_characters_wrap_to_two_lines():
    text = LONGEST['inlaid']
    one_line = fit_text(text, C.CARD_W, C.CARD_H, C.TEXT_MARGIN, C.INLAY_DEPTH)
    assert one_line.min_stroke < C.STROKE_FLOOR_INLAID
    _, fitted, _, part = case('inlaid', text)
    assert fitted.lines == ('Polymaker', 'PolyTerra Teal')
    assert fitted.min_stroke >= C.STROKE_FLOOR_INLAID + FLOOR_MARGIN
    assert_fits_and_centred(fitted)
    assert part.is_valid


def test_two_lines_splits_at_the_space_nearest_the_middle():
    assert two_lines('Bambu PLA Matte Charcoal') == 'Bambu PLA\nMatte Charcoal'
    assert two_lines('a b c') == 'a\nb c'  # tie -> the earlier space
    assert two_lines('  ab  cd ') == 'ab\ncd'
    assert two_lines('PETG-CF') is None


@pytest.mark.parametrize('style,text', [('inlaid', TOO_LONG), ('raised', LONGEST['inlaid']),
                                        ('inlaid', 'W' * 24)])
def test_text_that_fails_the_floor_on_two_lines_is_rejected(style, text):
    with pytest.raises(ValueError) as err:
        layout_text(text, C.CARD_W, C.CARD_H, C.TEXT_MARGIN, C.INLAY_DEPTH, STROKE_FLOOR[style])
    message = str(err.value)
    stroke = float(re.search(r'thinnest stroke would be ([\d.]+) mm', message).group(1))
    assert stroke < STROKE_FLOOR[style] + FLOOR_MARGIN
    assert f'below the {STROKE_FLOOR[style]:g} mm floor' in message
    longest = re.search(r"the longest that fits is '(.*)' \((\d+) characters\)", message)
    prefix = longest.group(1)
    assert len(prefix) == int(longest.group(2)) and 0 < len(prefix) < len(text)
    assert text.startswith(prefix)
    fitted = layout_text(prefix, C.CARD_W, C.CARD_H, C.TEXT_MARGIN, C.INLAY_DEPTH,
                         STROKE_FLOOR[style])
    assert fitted.min_stroke >= STROKE_FLOOR[style]


# Raised text on the 60 x 20 card, 2.0 mm margin (pst-l4hsl): (text, lines,
# min_stroke, min_gap, min_clearance), regression values. There is no gap or
# clearance floor for raised text (docs/labels-spike.md, 'Raised: no
# inter-glyph floor'): 'PLA Matte' (M crotch, tt pair) and 'Smart PLA' (r-t
# pair) must keep building.
RAISED_TABLE = [('Filament', 1, 1.222, 1.250, 0.968),
                ('PETG-CF Black', 2, 0.957, 1.096, 0.910),
                (LONGEST['raised'], 2, 1.020, 1.001, 0.818),
                ('PLA Matte', 1, 1.022, 0.204, 0.482),
                ('Smart PLA', 1, 1.064, 0.288, 0.308)]


@pytest.mark.parametrize('text,lines,stroke,gap,clearance', RAISED_TABLE)
def test_raised_text_metrics_and_no_gap_floor(text, lines, stroke, gap, clearance):
    _, fitted, _, part = case('raised', text)
    assert len(fitted.lines) == lines
    assert (fitted.min_stroke, fitted.min_gap, fitted.min_clearance) == pytest.approx(
        (stroke, gap, clearance), abs=0.01)
    assert fitted.min_stroke >= STROKE_FLOOR['raised'] and part.is_valid


def test_clearance_ignores_notches_inside_one_glyph():
    """min_gap reads the 'M' crotch as a gap; the clearance has one piece, so inf."""
    fitted = fit_text('M', C.CARD_W, C.CARD_H, C.TEXT_MARGIN, C.INLAY_DEPTH)
    assert fitted.min_gap < 0.5 and fitted.min_clearance == math.inf
    skipped = fit_text('M', C.CARD_W, C.CARD_H, C.TEXT_MARGIN, C.INLAY_DEPTH, measure=False)
    assert math.isnan(skipped.min_clearance)


@pytest.mark.parametrize('style', ['inlaid', 'raised'])
@pytest.mark.parametrize('text', ['', '   '])
def test_blank_text_is_a_blank_card(style, text):
    values = SPEC.resolve_values({'text': text, 'text_style': style})
    assert [name for name, _, _ in colour_parts(values)] == ['base']
    assert SPEC.build(values).volume == pytest.approx(card().volume, rel=1e-9)


def test_card_envelope_comes_from_constants():
    bb = card().bounding_box()
    assert (bb.size.X, bb.size.Y, bb.size.Z) == pytest.approx((C.CARD_W, C.CARD_H, C.CARD_T))
    _, _, _, raised = case('raised', 'Filament')
    assert raised.bounding_box().max.Z == pytest.approx(C.CARD_T + C.INLAY_DEPTH)


def test_inlaid_parts_partition_the_card_and_share_the_bed_face():
    _, _, parts, part = case('inlaid', 'Filament')
    (base_name, base, _), (inlay_name, inlay, _) = parts
    assert (base_name, inlay_name) == ('base', 'inlay')
    assert base.is_valid and inlay.is_valid
    assert base.bounding_box().min.Z == pytest.approx(0, abs=1e-6)
    assert inlay.bounding_box().min.Z == pytest.approx(0, abs=1e-6)
    assert inlay.bounding_box().max.Z == pytest.approx(C.INLAY_DEPTH, abs=1e-6)
    assert base.volume + inlay.volume == pytest.approx(card().volume, rel=1e-6)
    assert (base & inlay).volume < 1e-6
    assert part.volume == pytest.approx(card().volume, rel=1e-6)


def f_stem_side(glyphs, f) -> float:
    """+1 if glyph f (the F of 'Filament') has its stem on +X."""
    fb = f.bounding_box()
    assert fb.size.Y > 0.9 * max(g.bounding_box().size.Y for g in glyphs)  # cap height
    mid = fb.center().X
    def half(lo, hi):
        slab = Pos((lo + hi) / 2, fb.center().Y, fb.center().Z) * Rectangle(hi - lo, fb.size.Y + 2)
        return (f & slab).area
    right, left = half(mid, fb.max.X), half(fb.min.X, mid)
    assert max(right, left) > 1.5 * min(right, left)
    return math.copysign(1, right - left)


def test_inlaid_text_is_mirrored_for_face_down():
    """From +Z the inlay reads backwards: 'F' is the RIGHTMOST glyph, stem on +X."""
    _, _, parts, _ = case('inlaid', 'Filament')
    glyphs = section(parts[1][1], Plane.XY.offset(C.INLAY_DEPTH / 2)).faces()
    assert f_stem_side(glyphs, glyphs.sort_by(Axis.X)[-1]) > 0


def test_raised_text_reads_from_above():
    _, _, parts, _ = case('raised', 'Filament')
    text = parts[1][1]
    assert text.bounding_box().min.Z == pytest.approx(C.CARD_T)
    glyphs = section(text, Plane.XY.offset(C.CARD_T + C.INLAY_DEPTH / 2)).faces()
    assert f_stem_side(glyphs, glyphs.sort_by(Axis.X)[0]) < 0


def read_3mf(path):
    """[(object name, [(part name, min z, max z)])] per build item, via lib3mf."""
    import lib3mf
    model = lib3mf.get_wrapper().CreateModel()
    model.QueryReader('3mf').ReadFromFile(str(path))
    items, out = model.GetBuildItems(), []
    while items.MoveNext():
        obj = items.GetCurrent().GetObjectResource()
        assert obj.IsComponentsObject()
        comps = model.GetComponentsObjectByID(obj.GetResourceID())
        parts = []
        for i in range(comps.GetComponentCount()):
            mesh = model.GetMeshObjectByID(comps.GetComponent(i).GetObjectResource().GetResourceID())
            zs = [mesh.GetVertex(j).Coordinates[2] for j in range(mesh.GetVertexCount())]
            parts.append((mesh.GetName(), min(zs), max(zs)))
        out.append((obj.GetName(), parts))
    return out


def test_3mf_is_one_object_with_base_and_inlay_on_two_filaments(tmp_path):
    named = resolve_colour_parts(SPEC, {'text': 'PETG-CF'})
    path = tmp_path / 'card.3mf'
    saved = locale.setlocale(locale.LC_ALL)
    export_3mf_one_object(named, path, 'label-card')
    assert locale.setlocale(locale.LC_ALL) == saved  # lib3mf's C-locale reset is undone
    [(name, parts)] = read_3mf(path)
    assert name == 'label-card'
    assert [p[0] for p in parts] == ['base', 'inlay']
    assert all(abs(z0) < 1e-6 for _, z0, _ in parts)  # both on the bed face
    assert parts[1][2] == pytest.approx(C.INLAY_DEPTH, abs=1e-6)
    import zipfile
    with zipfile.ZipFile(path) as package:
        model = package.read('3D/3dmodel.model').decode()
        settings = package.read('Metadata/model_settings.config').decode()
    assert 'name="Application"' not in model
    extruders = re.findall(r'<part id="\d+".*?key="name" value="(\w+)".*?key="extruder" value="(\d)"',
                           settings, re.S)
    assert extruders == [('base', '1'), ('inlay', '2')]


_WRITE = '''
import sys; sys.path.insert(0, {root!r})
from holders.label_card import SPEC, colour_parts
from scripts.export import export_3mf_one_object
export_3mf_one_object(colour_parts(SPEC.resolve_values({{'text': 'PETG-CF'}})), {out!r}, 'label-card')
'''


def test_exports_are_byte_stable(tmp_path):
    named = resolve_colour_parts(SPEC, {'text': 'PETG-CF'})
    for run in ('a', 'b'):
        export_3mf_one_object(named, tmp_path / f'{run}.3mf', 'label-card')
        for name, shape, _ in named:
            export_stl(shape, str(tmp_path / f'{run}-{name}.stl'))
    for name in ('3mf', 'base.stl', 'inlay.stl'):
        sep = '.' if name == '3mf' else '-'
        assert (tmp_path / f'a{sep}{name}').read_bytes() == (tmp_path / f'b{sep}{name}').read_bytes()
    other = tmp_path / 'process.3mf'  # a fresh process: no shared OCCT / lib3mf state
    subprocess.run([sys.executable, '-c', _WRITE.format(root=str(ROOT), out=str(other))],
                   cwd=ROOT, check=True, capture_output=True)
    assert other.read_bytes() == (tmp_path / 'a.3mf').read_bytes()


@pytest.mark.parametrize('style', ['inlaid', 'raised'])
def test_every_card_edge_is_eased_coplanar_or_a_glyph_edge(style):
    """Card rims are 45-degree chamfers; glyph edges are the feature (left sharp)."""
    _, fitted, _, part = case(style, 'Filament')
    ink = fitted.part.bounding_box()
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    counts = {'coplanar': 0, 'eased': 0, 'glyph': 0}
    for edge, faces in adjacency.items():
        assert len(faces) == 2
        c = edge.center()
        normals = [f.normal_at(c) for f in faces]
        angle = math.degrees(math.acos(max(-1, min(1, normals[0].dot(normals[1])))))
        if angle < 1e-3:
            counts['coplanar'] += 1
        elif (style == 'raised' and c.Z >= C.CARD_T - 1e-6
              and ink.min.X - 1e-3 <= c.X <= ink.max.X + 1e-3
              and ink.min.Y - 1e-3 <= c.Y <= ink.max.Y + 1e-3):
            counts['glyph'] += 1
        else:
            assert angle == pytest.approx(45, abs=1e-3), (tuple(c), angle)
            counts['eased'] += 1
    assert counts['eased'] > 0 and (counts['glyph'] > 0) == (style == 'raised')


def raised_text(values):
    """The raised text solid: the approved audit exclusion for the raised style."""
    return colour_parts(values)[1][1]


# Audit cases (AC d): each preset and the longest pinned string per style.
AUDIT_CASES = [('inlaid', 'Filament'), ('raised', 'Filament'),
               ('inlaid', LONGEST['inlaid']), ('raised', LONGEST['raised'])]


@pytest.mark.audit
@pytest.mark.parametrize('style,text', AUDIT_CASES)
def test_print_audit_on_the_assembled_card(style, text, capsys):
    """Inlaid: glyphs are interior to the fused card, audited as is. Raised: the
    raised text is excluded (its strokes are gated by fit_text, below; see
    test_raised_text_is_the_only_audit_exclusion), the card is audited."""
    values, fitted, _, part = case(style, text)
    exclusions = [raised_text(values)] if style == 'raised' else []
    report = audit(part, SPEC.print_orientation, exclusions=exclusions,
                   model=f'{style}:{text}')
    with capsys.disabled():
        print(f'\n{style:6} {text!r:28} lines={len(fitted.lines)} '
              f'min_stroke={fitted.min_stroke:.3f} min_gap={fitted.min_gap:.3f} '
              f'min_clearance={fitted.min_clearance:.3f} '
              f'min_wall={report.min_wall_mm:.3f} overhang={report.max_overhang_deg:.1f} '
              f'bridge={report.longest_bridge_mm:.2f} volume={part.volume:.1f} ok={report.ok}')
    assert report.ok, report.format()
    assert report.min_wall_mm >= MIN_WALL_MM
    assert fitted.min_stroke >= STROKE_FLOOR[style]  # the stroke floor, D5


@pytest.mark.audit
def test_raised_text_is_the_only_audit_exclusion():
    """Unexcluded, the raised card fails ONLY the wall check, on tapered glyph
    terminals the stroke scan ignores by design; the exclusion is the exact
    text solid above the card, nothing of the card itself."""
    values, fitted, _, part = case('raised', 'Filament')
    raw = audit(part, SPEC.print_orientation, model='raised_unexcluded')
    assert raw.failures() and all('wall' in f for f in raw.failures())
    assert raw.max_overhang_deg <= 45 and raw.longest_bridge_mm <= 10
    assert not raw.downward_fillets
    region = raised_text(values)
    assert region.bounding_box().min.Z == pytest.approx(C.CARD_T)
    assert region.volume == pytest.approx(fitted.part.volume, rel=1e-6)
    assert (region & card()).volume < 1e-6
