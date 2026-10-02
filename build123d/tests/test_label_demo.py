"""Labels spike (pst-0zfra): font guard, fit_text, face-down inlay, one-object 3MF."""
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build123d import Axis, Mesher, Plane, Pos, Rectangle, section
from holders import label_demo as demo
from holders.label_text import FONT_PATH, fit_text, load_font, text_sketch
from holders.registry import all_models

STRINGS = ('Filament', 'PLA Black', 'PETG-CF', 'W')


def test_demo_is_smoke_and_out_of_catalog():
    spec = next(s for s in all_models() if s.name == 'label_demo')
    assert spec.is_smoke
    from scripts.manifest import build_manifest
    assert 'label-demo' not in {m['slug'] for m in build_manifest()['models']}


def test_vendored_font_resolves_to_its_own_file():
    assert load_font() == 'Inter'
    assert (FONT_PATH.parent / 'OFL.txt').read_text(encoding='utf-8').startswith('Copyright')


def test_missing_or_bogus_font_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        text_sketch('PLA', path=tmp_path / 'Nope.ttf')
    bogus = tmp_path / 'bogus.ttf'
    bogus.write_text('not a font')
    with pytest.raises(Exception):
        text_sketch('PLA', path=bogus)


@pytest.mark.parametrize('text', STRINGS)
def test_fit_text_fills_box_and_centres(text):
    w, h, m = demo.CARD_W, demo.CARD_H, demo.TEXT_MARGIN
    fitted = fit_text(text, w, h, m)
    bb = fitted.part.bounding_box()
    assert fitted.part.is_valid
    # Uniform scale: the binding axis fills exactly, the other fits inside.
    assert bb.size.X <= w - 2 * m + 1e-6 and bb.size.Y <= h - 2 * m + 1e-6
    assert max(bb.size.X / (w - 2 * m), bb.size.Y / (h - 2 * m)) == pytest.approx(1, abs=1e-6)
    assert abs(bb.center().X) < 1e-6 and abs(bb.center().Y) < 1e-6
    assert fitted.min_stroke >= 0.9 and fitted.min_gap >= 0.9


def test_fit_text_reports_unprintable_long_string():
    fitted = fit_text('Bambu PLA Matte Charcoal', demo.CARD_W, demo.CARD_H, demo.TEXT_MARGIN)
    assert fitted.min_stroke < 0.9  # the model must clamp; fit_text reports, never hides


@pytest.fixture(scope='module')
def filament():
    return demo.parts('Filament')


def test_inlay_is_flush_on_the_bed_and_base_fills_the_rest(filament):
    base, inlay = filament
    assert base.is_valid and inlay.is_valid
    ib, bb = inlay.bounding_box(), base.bounding_box()
    assert ib.min.Z == pytest.approx(0, abs=1e-6)
    assert ib.max.Z == pytest.approx(demo.INLAY_DEPTH, abs=1e-6)
    assert bb.min.Z == pytest.approx(0, abs=1e-6) and bb.max.Z == pytest.approx(demo.CARD_T)
    assert base.volume + inlay.volume == pytest.approx(demo.card().volume, rel=1e-6)
    assert (base & inlay).volume < 1e-6


def test_text_is_mirrored_for_face_down(filament):
    """Model frame (+Z view): 'F' is the RIGHTMOST glyph with its stem on +X."""
    _, inlay = filament
    glyphs = section(inlay, Plane.XY.offset(demo.INLAY_DEPTH / 2)).faces()
    f = glyphs.sort_by(Axis.X)[-1]
    fb = f.bounding_box()
    assert fb.size.Y > 0.9 * max(g.bounding_box().size.Y for g in glyphs)  # cap height
    mid = fb.center().X
    # The stem half of an F holds the full-height stem; the other half only
    # the arm tips. Unmirrored, the stem half is the left one.
    half = lambda lo, hi: (f & _slab(lo, hi, fb)).area
    assert half(mid, fb.max.X) > 1.5 * half(fb.min.X, mid)


def _slab(lo, hi, fb):
    return Pos((lo + hi) / 2, fb.center().Y, fb.center().Z) * Rectangle(hi - lo, fb.size.Y + 2)


def test_3mf_is_one_object_with_two_filament_parts(filament, tmp_path):
    base, inlay = filament
    path = tmp_path / 'card.3mf'
    demo.export_3mf_one_object([('base', base, demo.BASE_RGBA),
                                ('inlay', inlay, demo.INLAY_RGBA)], path, 'card')
    with zipfile.ZipFile(path) as package:
        model = package.read('3D/3dmodel.model').decode()
        settings = package.read('Metadata/model_settings.config').decode()
    assert 'name="Application"' not in model  # Bambu Studio crashes on a fake project
    items = re.findall(r'<item objectid="(\d+)"', model)
    assert len(items) == 1
    comps = re.findall(r'<component objectid="(\d+)"', model)
    assert len(comps) == 2
    parts = dict(re.findall(r'<part id="(\d+)".*?key="extruder" value="(\d+)"', settings, re.S))
    assert parts == {comps[0]: '1', comps[1]: '2'}
    assert f'<object id="{items[0]}">' in settings


def test_stock_mesher_splits_text_into_one_object_per_glyph(filament, tmp_path):
    """Why export_3mf_one_object exists: Mesher writes a build item per solid."""
    base, inlay = filament
    mesher = Mesher()
    mesher.add_shape([base, inlay])
    path = tmp_path / 'split.3mf'
    mesher.write(str(path))
    with zipfile.ZipFile(path) as package:
        model = package.read('3D/3dmodel.model').decode()
    assert len(re.findall(r'<item ', model)) == 1 + len(inlay.solids()) > 2
