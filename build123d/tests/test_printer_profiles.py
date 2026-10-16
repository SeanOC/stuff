"""Printer profiles for the 3MF download (pst-jyey1).

The profiled 3MF is a pure transform of the generic one: it may differ only
in 3D/3dmodel.model's root attributes, the two Bambu metadata lines and the
build-item transform, plus the added Metadata/project_settings.config. The
headless Bambu Studio round trip + slice (acceptance A1/A2) is recorded on
the bead; these tests pin the structure it was run against.
"""
import dataclasses
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from holders.registry import resolve_colour_parts  # noqa: E402
from profiles import PROFILES  # noqa: E402
import scripts.export as export  # noqa: E402
from scripts.export import (_place_on_plate, apply_printer_profile,  # noqa: E402
                            export_3mf_one_object, max_footprint)
from scripts.manifest import build_manifest, validate_manifest  # noqa: E402

H2C = PROFILES['bambu-h2c-0.4']
CONFIG = 'Metadata/project_settings.config'


@pytest.fixture(scope='module')
def label_3mfs(tmp_path_factory):
    """(named, generic bytes path, profiled path) for the inlaid label card."""
    from holders.label_card import SPEC

    out = tmp_path_factory.mktemp('profiles')
    named = resolve_colour_parts(SPEC, next(p for p in SPEC.presets if p.id == 'inlaid').values)
    generic, profiled = out / 'inlaid.3mf', out / f'inlaid.{H2C.id}.3mf'
    export_3mf_one_object(named, generic, f'{SPEC.slug}-inlaid')
    apply_printer_profile(generic, profiled, H2C, named)
    return named, generic, profiled


def test_registry_entries_match_their_templates():
    for profile in PROFILES.values():
        assert re.fullmatch(r'[a-z0-9][a-z0-9.-]*', profile.id)
        settings = profile.settings()
        assert len(settings['filament_colour']) == profile.filament_slots
        # Bambu Studio couples the Application version to the config's.
        assert profile.application == f'BambuStudio-{settings["version"]}'


def test_h2c_template_is_the_h2c_project_config():
    settings = H2C.settings()
    assert len(settings) == 581  # every key of Sean's export kept (rev 1)
    assert settings['printer_settings_id'] == 'Bambu Lab H2C 0.4 nozzle'
    assert settings['print_settings_id'] == '0.16mm Standard @BBL H2C'
    assert settings['filament_settings_id'] == ['Bambu PLA Basic @BBL H2C'] * 8


def test_templates_carry_no_account_or_device_keys():
    for profile in PROFILES.values():
        leaked = [key for key in profile.settings()
                  if re.search('token|serial|device|user|account', key, re.I)]
        assert leaked == [], profile.id


def test_manifest_lists_the_profiles_and_rejects_duplicates():
    doc = build_manifest()
    assert doc['printerProfiles'] == [{'id': p.id, 'displayName': p.display_name}
                                      for p in PROFILES.values()]
    assert validate_manifest(doc) == []
    doc['printerProfiles'].append(dict(doc['printerProfiles'][0]))
    assert any('duplicated' in e for e in validate_manifest(doc))


def _strip_profile(model: str) -> str:
    """The profiled 3dmodel.model with exactly the profile's additions removed."""
    model = model.replace(' xmlns:BambuStudio="http://schemas.bambulab.com/package/2021"'
                          ' requiredextensions="p"', '', 1)
    model = model.replace(f'\n\t<metadata name="Application">{H2C.application}</metadata>'
                          '\n\t<metadata name="BambuStudio:3mfVersion">1</metadata>', '', 1)
    return re.sub(r'<item transform="[^"]*" ', '<item ', model, count=1)


def test_profiled_3mf_differs_only_in_the_profile_additions(label_3mfs):
    _, generic, profiled = label_3mfs
    with zipfile.ZipFile(generic) as g, zipfile.ZipFile(profiled) as p:
        assert p.namelist() == g.namelist() + [CONFIG]
        for info in g.infolist():
            other = p.getinfo(info.filename)
            assert other.date_time == info.date_time, info.filename
            if info.filename != '3D/3dmodel.model':
                assert p.read(info.filename) == g.read(info), info.filename
        generic_model = g.read('3D/3dmodel.model').decode()
        profiled_model = p.read('3D/3dmodel.model').decode()
        assert p.getinfo(CONFIG).date_time == (1980, 1, 1, 0, 0, 0)
    assert profiled_model != generic_model
    assert _strip_profile(profiled_model) == generic_model
    # Only Application + 3mfVersion: a GUI project's DesignerUserId is an account id.
    assert re.findall(r'<metadata name="([^"]+)"', profiled_model) == [
        'Application', 'BambuStudio:3mfVersion']


def test_profiled_config_maps_our_colours_and_keeps_the_rest(label_3mfs):
    named, generic, profiled = label_3mfs
    with zipfile.ZipFile(profiled) as p:
        settings = json.loads(p.read(CONFIG))
    with zipfile.ZipFile(generic) as g:
        display = re.findall(r'displaycolor="(#[0-9A-F]{6})FF"', g.read('3D/3dmodel.model').decode())
    template = H2C.settings()
    n = len(named)
    assert settings['filament_colour'][:n] == display  # same hex lib3mf wrote
    assert settings['filament_colour'][n:] == template['filament_colour'][n:]
    changed = {k for k in template if settings[k] != template[k]}
    assert changed == {'filament_colour', 'wipe_tower_x', 'wipe_tower_y'}
    assert settings.keys() == template.keys()


def test_profiled_3mf_is_byte_stable(label_3mfs, tmp_path):
    named, generic, profiled = label_3mfs
    again = tmp_path / 'again.3mf'
    apply_printer_profile(generic, again, H2C, named)
    assert again.read_bytes() == profiled.read_bytes()


def test_more_parts_than_filament_slots_fails_loudly(label_3mfs, tmp_path):
    named, generic, _ = label_3mfs
    with pytest.raises(ValueError, match='filament slots'):
        apply_printer_profile(generic, tmp_path / 'x.3mf', H2C, named * 5)


def _box_model(dx: float, dy: float, dz: float = 5.0) -> str:
    corners = [(x, y, z) for x in (-dx / 2, dx / 2) for y in (0.0, dy) for z in (0.0, dz)]
    return ''.join(f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}" />' for x, y, z in corners)


def _placed(transform: str, dx: float, dy: float):
    m = [float(v) for v in transform.split()]
    corners = [(x * m[0] + y * m[3] + m[9], x * m[1] + y * m[4] + m[10])
               for x in (-dx / 2, dx / 2) for y in (0.0, dy)]
    xs, ys = zip(*corners)
    return min(xs), max(xs), min(ys), max(ys)


@pytest.mark.parametrize('dx, dy, turned', [
    (60, 17, False),    # label card
    (160, 240, False),  # small sign: the tower fits behind it
    (240, 300, True),   # full sign: only turned leaves room (Bambu's own arrange does the same)
])
def test_placement_puts_part_and_tower_on_the_h2c_plate(dx, dy, turned):
    settings = H2C.settings()
    transform, tower_x, tower_y = _place_on_plate(_box_model(dx, dy), settings)
    assert transform.startswith('0 1 0 -1 0 0' if turned else '1 0 0 0 1 0')
    x0, x1, y0, y1 = _placed(transform, dx, dy)
    # Inside the 330 x 320 plate, tower 60 wide behind the part, inside the
    # area both extruders reach (x 25..325).
    assert 0 < x0 and x1 < 330 and 0 < y0 and y1 < tower_y
    assert 25 <= tower_x and tower_x + float(settings['prime_tower_width']) <= 325
    assert tower_y + 66.2 < 320  # measured 8-filament tower depth (A2)


def test_placement_refuses_a_part_the_nozzle_cannot_reach():
    with pytest.raises(ValueError, match=r"does not fit the printing nozzle's 325 x 320 mm reach "
                                         r'.*max footprint 323 x 244 mm'):
        _place_on_plate(_box_model(320, 320), H2C.settings())


def test_h2c_max_footprint_is_the_printing_nozzles_reach_not_the_plate():
    """Every filament maps to extruder 1 (filament_map "1" = array index 0),
    whose extruder_printable_area is X 0..325 of the 330 x 320 plate: one
    2 mm plate margin at the left edge (X 2..325) by the plate's depth less
    three margins and the 70 mm tower reserve. Tighter than both the plate
    (326) and the print audit's build volume (325 x 320, which passes e.g.
    300 x 300; pst-68fpi A1, pst-8tp6w)."""
    settings = H2C.settings()
    assert settings['filament_map'] == ['1'] * len(settings['filament_map'])
    assert settings['extruder_printable_area'][0] == '0x0,325x0,325x320,0x320'
    assert settings['extruder_printable_height'][0] == '320'
    assert max_footprint(settings) == (323.0, 244.0)


def test_a_profile_without_per_extruder_reach_falls_back_to_the_plate():
    settings = H2C.settings()
    del settings['extruder_printable_area'], settings['extruder_printable_height']
    assert max_footprint(settings) == (326.0, 244.0)
    _place_on_plate(_box_model(326, 244, 325), settings)
    with pytest.raises(ValueError, match=r'does not fit the 330 x 320 mm plate'):
        _place_on_plate(_box_model(326.5, 10), settings)
    with pytest.raises(ValueError, match=r'the printer prints up to 325 mm'):
        _place_on_plate(_box_model(10, 10, 325.5), settings)


@pytest.mark.parametrize('dx, dy, fits', [
    (323, 244, True),     # the limit, as is
    (244, 323, True),     # the limit, turned
    (324, 244, False),    # one past the nozzle's reach
    (324, 100, False),    # fit the 330 mm plate before pst-8tp6w
    (326, 244, False),    # the old plate-derived limit, as is
    (244, 326, False),    # the old plate-derived limit, turned
    (326.5, 10, False),   # wider than the plate either way
    (245, 245, False),    # deeper than the reserve leaves either way
    (300, 300, False),    # audit-legal, not profile-legal
])
def test_placement_accepts_exactly_the_max_footprint(dx, dy, fits):
    if fits:
        _place_on_plate(_box_model(dx, dy), H2C.settings())
    else:
        with pytest.raises(ValueError, match='does not fit'):
            _place_on_plate(_box_model(dx, dy), H2C.settings())


@pytest.mark.parametrize('dx, x0, x1', [
    (323, 2.0, 325.0),    # the whole band
    (320, 5.0, 325.0),    # was 8..328, past the nozzle's X 325 (pst-8tp6w)
    (160, 95.0, 255.0),   # small sign: centred on the common reach, unchanged
])
def test_placement_clamps_to_the_printing_nozzles_reach(dx, x0, x1):
    transform, tower_x, _ = _place_on_plate(_box_model(dx, 100), H2C.settings())
    assert _placed(transform, dx, 100)[:2] == pytest.approx((x0, x1))
    assert tower_x == pytest.approx(145.0)  # the tower corner stays on the common reach


def test_turned_full_sign_stays_centred_on_the_common_reach():
    # 240 x 300 turned = 300 along X: centre 175, X 25..325, tower corner 145
    # exactly as before pst-8tp6w (the baked profiled 3MFs are byte-identical).
    transform, tower_x, tower_y = _place_on_plate(_box_model(240, 300), H2C.settings())
    assert transform.startswith('0 1 0 -1 0 0')
    assert _placed(transform, 240, 300) == pytest.approx((25.0, 325.0, 2.0, 242.0))
    assert (tower_x, tower_y) == pytest.approx((145.0, 244.0))


@pytest.mark.parametrize('dz, fits', [(320, True), (321, False)])
def test_placement_refuses_a_part_taller_than_the_printing_nozzle(dz, fits):
    if fits:
        _place_on_plate(_box_model(100, 100, dz), H2C.settings())
    else:
        with pytest.raises(ValueError, match=r'part 100.0 x 100.0 mm is 321.0 mm tall; '
                                             r'the printing nozzle \(extruder 1\) prints up to 320 mm'):
            _place_on_plate(_box_model(100, 100, dz), H2C.settings())


def test_bake_names_every_preset_a_profile_cannot_hold(tmp_path, monkeypatch, capsys):
    """A preset too large for a profile fails the bake (every profiled 3MF is
    expected downstream) with one line per preset x profile naming the
    footprint and the max, not a bare traceback (pst-68fpi)."""
    from holders.label_card import SPEC

    settings = H2C.settings()
    settings['printable_area'] = ['0x0', '50x0', '50x80', '0x80']  # max 46 x 4: holds no label
    template = tmp_path / 'tiny.json'
    template.write_text(json.dumps(settings), encoding='utf-8')
    tiny = dataclasses.replace(H2C, id='tiny', template=template)
    monkeypatch.setattr(export, 'all_models', lambda: [SPEC])
    monkeypatch.setattr(export, 'PROFILES', {H2C.id: H2C, tiny.id: tiny})

    assert export.export_presets_only(tmp_path / 'bake') == 1
    fails = [line for line in capsys.readouterr().err.splitlines() if line.startswith('FAIL ')]
    assert len(fails) == len(SPEC.presets) == 2
    for preset, line in zip(SPEC.presets, fails):
        assert line.startswith(f'FAIL {SPEC.name}/{preset.id}: printer profile tiny: part ')
        assert 'max footprint 46 x 4 mm' in line
    # The profile that holds the label still baked.
    assert all((tmp_path / 'bake' / SPEC.slug / f'{p.id}.{H2C.id}.3mf').exists() for p in SPEC.presets)
