"""Reference-sheet asset contracts, independent of PDF generation timestamps."""
import hashlib
import importlib.util
import json
from pathlib import Path

import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
cv2 = pytest.importorskip("cv2")
import numpy as np
from shapely.geometry import Polygon

from capture.footprint import (DetectionError, _region, detect_grid, footprint,
                               marker_corners, rectify, segment, sheet_profiles)
from capture.synth import _phone_warp, sheet_background

ROOT = Path(__file__).resolve().parents[2]


def test_sheet_manifest_roundtrip():
    source = ROOT/'build123d/capture/sheets.json'
    public = ROOT/'public/capture'
    assert source.read_bytes() == (public/'sheets.json').read_bytes()
    sheets = json.loads(source.read_text())
    assert set(sheets) == {'letter-v1', 'a4-v1'}
    for sheet_id, sheet in sheets.items():
        assert sheet['id'] == sheet_id
        assert sheet['dictionary'] == 'DICT_4X4_50'
        assert set(sheet['markers_mm']) == {'0', '1', '2', '3'}
        assert sheet['marker_size_mm'] == 24
        assert sheet['check_bar_mm']['length_mm'] == 100
        pdf = public/sheet['pdf']
        assert pdf.read_bytes().startswith(b'%PDF-')
        assert hashlib.sha256(pdf.read_bytes()).hexdigest() == sheet['pdf_sha256']


def test_sheet_manifest_matches_generator_constants():
    pytest.importorskip('cv2')
    spec = importlib.util.spec_from_file_location(
        'make_capture_sheet', ROOT/'build123d/scripts/make_capture_sheet.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    sheets = json.loads((ROOT/'build123d/capture/sheets.json').read_text())
    for name in generator.SHEETS:
        generated = generator.manifest(name)
        stored = sheets[generated['id']]
        assert generated == {k: v for k, v in stored.items()
                             if k not in ('pdf', 'pdf_sha256')}


FIXTURES = ROOT/'build123d/tests/fixtures/capture'
OCCLUDED = 'a reference marker is hidden — keep all four corners visible and uncovered'
FIELD_EDGE = 'item crosses the sheet field'


def photo(sheet_id='letter-v1', tilt=0, *, scale=1., item=True, hidden=()):
    rgb = sheet_background(sheet_id, print_scale=scale)
    profile = sheet_profiles()[sheet_id]
    if item:
        # Physical 50 x 30 mm item; independent of the printer scale.
        rgb[400:520, 280:480] = (35, 65, 190)
    for i in hidden:
        x, y = profile['markers_mm'][str(i)]
        rgb[round(y*4*scale):round((y+24)*4*scale)+1,
            round(x*4*scale):round((x+24)*4*scale)+1] = 245
    rgb = cv2.copyMakeBorder(rgb, 48,48,48,48,cv2.BORDER_CONSTANT,value=(40,40,40))
    return _phone_warp(rgb, tilt, 42)


def recover(image, **kwargs):
    grid = detect_grid(image, **kwargs)
    rect = rectify(image, grid.H, size_mm=grid.size_mm, kind=grid.kind)
    ring = footprint(segment(rect), roi=_region(rect), edge_message=FIELD_EDGE)
    return grid, rect, ring


@pytest.mark.parametrize('sheet_id', ['letter-v1', 'a4-v1'])
@pytest.mark.parametrize('tilt', [0, 15])
def test_sheet_detects_all_four_markers(sheet_id, tilt):
    image, _ = photo(sheet_id, tilt)
    grid = detect_grid(image)
    assert (grid.kind, grid.sheet_id) == ('sheet', sheet_id)
    assert grid.reprojection_mm < .8


@pytest.mark.parametrize('sheet_id', ['letter-v1', 'a4-v1'])
@pytest.mark.parametrize('tilt', [0, 15])
def test_sheet_h_is_field_based(sheet_id, tilt):
    image, camera = photo(sheet_id, tilt)
    grid = detect_grid(image)
    x0,y0,x1,y1 = sheet_profiles()[sheet_id]['field_mm']
    source = np.array([[[x0*4+48,y0*4+48],[x1*4+48,y1*4+48]]], np.float64)
    actual = cv2.perspectiveTransform(source, grid.H@camera)[0]
    assert actual == pytest.approx(np.array([[0,0],grid.size_mm]), abs=.2)


@pytest.mark.parametrize('hidden', [(2,), (1,2)])
@pytest.mark.parametrize('tilt', [0,15])
def test_sheet_one_marker_hidden_raises(hidden, tilt):
    image, _ = photo(tilt=tilt, hidden=hidden)
    with pytest.raises(DetectionError, match=OCCLUDED):
        detect_grid(image)


def test_sheet_scaled_print_recovers():
    image, _ = photo(scale=.97)
    grid, _, corrected = recover(image, bar_mm=97)
    uncorrected_grid, _, uncorrected = recover(image)
    sides = lambda ring: sorted(cv2.minAreaRect(ring.astype(np.float32))[1])
    assert sides(corrected) == pytest.approx([30,50], abs=.3)
    assert sides(uncorrected) == pytest.approx([30/.97,50/.97], abs=.3)
    assert np.asarray(grid.size_mm) == pytest.approx(np.asarray(uncorrected_grid.size_mm)*.97)
    assert grid.H[:2] == pytest.approx(uncorrected_grid.H[:2]*.97)


@pytest.mark.parametrize('bar_mm', [0,89,111,float('nan'),float('inf')])
def test_sheet_rejects_invalid_bar(bar_mm):
    image, _ = photo()
    with pytest.raises(ValueError, match='bar_mm must be in 90..110'):
        detect_grid(image, bar_mm=bar_mm)


def test_sheet_empty_raises_no_item():
    image, _ = photo(item=False)
    with pytest.raises(DetectionError, match='^no item contour$'):
        recover(image)


def test_sheet_item_crossing_field_raises():
    rgb = sheet_background()
    rgb[140:300, 300:440] = (30,70,190)
    with pytest.raises(DetectionError, match=FIELD_EDGE):
        recover(rgb)


def test_sheet_shadow_rule():
    rgb = sheet_background()
    # Soft neutral shadow next to, and under, a chromatic rectangle.
    shadow = np.zeros(rgb.shape[:2], np.float32)
    shadow[410:570, 300:530] = 1
    shadow = cv2.GaussianBlur(shadow, (31,31), 8)
    rgb = (rgb*(1-.3*shadow[:,:,None])).astype(np.uint8)
    rgb[400:520,280:480] = (35,65,190)
    image, _ = _phone_warp(cv2.copyMakeBorder(rgb,48,48,48,48,cv2.BORDER_CONSTANT,value=(40,40,40)),15,42)
    _, rect, ring = recover(image)
    truth = Polygon([[62,64],[112,64],[112,94],[62,94]])
    assert Polygon(ring).hausdorff_distance(truth) < 1
    before = rect.image.copy()
    segment(rect)
    assert np.array_equal(rect.image, before), 'white balance must not mutate input'


def test_sheet_not_flat_raises():
    rgb = sheet_background()
    x,y = (round(v*4) for v in sheet_profiles()['letter-v1']['markers_mm']['2'])
    marker = rgb[y:y+96,x:x+96].copy()
    rgb[y:y+96,x:x+96] = 245
    rgb[y-32:y+64,x-24:x+72] = marker
    with pytest.raises(DetectionError, match='sheet is not flat or the print is scaled'):
        detect_grid(rgb)


def test_unrelated_partial_markers_fall_through_to_plate():
    rgb = np.full((600,600,3),245,np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for i, x in enumerate((100,220)):
        marker = cv2.aruco.generateImageMarker(dictionary,i,96)
        rgb[100:196,x:x+96] = marker[:,:,None]
    with pytest.raises(DetectionError) as exc:
        detect_grid(rgb)
    assert str(exc.value) != OCCLUDED


@pytest.mark.parametrize('light', ['neutral', 'warm'])
@pytest.mark.parametrize('tilt', [0,15])
def test_sheet_matrix(light, tilt):
    records = json.loads((FIXTURES/'sheet-measurements.json').read_text())['records']
    assert len(records) == 72
    rows = [r for r in records if r['lighting']==light and r['tilt_deg']==tilt]
    assert len(rows) == 18
    assert len({(r['object'],r['pose']['rotation_deg']) for r in rows}) == 18
    assert all(r['detected'] and r['kind']=='sheet' for r in rows)
    assert np.mean([r['hausdorff_mm'] for r in rows]) <= 1.5


def test_sheet_fixture_replay():
    cv2.setNumThreads(1)
    from capture.sheet_oracle import generate
    from capture.encoding import parse
    records = json.loads((FIXTURES/'sheet-measurements.json').read_text())['records']
    for row in records:
        path = FIXTURES/row['png']
        assert path.stat().st_size <= 200_000
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
        image = cv2.cvtColor(cv2.imread(str(path)),cv2.COLOR_BGR2RGB)
        _,_,ring = recover(image)
        error = Polygon(ring).hausdorff_distance(Polygon(row['truth_mm']))
        assert error == pytest.approx(row['hausdorff_mm'], abs=.05)
        corners, ids, _ = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)).detectMarkers(cv2.cvtColor(image,cv2.COLOR_RGB2GRAY))
        assert set(ids.ravel()) == {0,1,2,3}
        for i,c in zip(ids.ravel(), corners):
            assert c.reshape(4,2) == pytest.approx(np.array(row['markers'][str(int(i))]), abs=.05)
    expected = json.loads((FIXTURES/'sheet-footprints.json').read_text())
    actual = generate()
    for a,e in zip(actual['records'],expected['records'],strict=True):
        for key in ('png','sha256','kind','result','error','vertices','truth_mm'):
            assert a[key] == e[key]
        assert a['result'] == 'footprint'
        assert np.array(parse(a['footprint'])) == pytest.approx(np.array(parse(e['footprint'])),abs=.05)
        assert a['area_mm2'] == pytest.approx(e['area_mm2'],abs=.1)


def test_real_sheet_rows():
    from capture.real_sheet_oracle import REAL, generate
    rows = json.loads((REAL/'sheet-footprints.json').read_text())['records']
    assert {r['png'] for r in rows} == {p.name for p in REAL.glob('*.png')}
    actual = generate(rows)
    assert actual == rows
    by_case = {r['case']:r for r in actual}
    assert by_case['empty-sheet']['error'] == 'no item contour'
    assert by_case['edge']['error'] == FIELD_EDGE
    ring = np.array(by_case['tall-item']['ring'],np.float32)
    short, long = sorted(cv2.minAreaRect(ring)[1])
    assert 95 <= long <= 110
    assert 28 <= short <= 42
    for row in rows:
        assert len(row['original_jpeg_sha256']) == 64
        assert (REAL/row['png']).stat().st_size <= 8_000_000
        if row['case'] == 'inside-sheet':
            short,long = sorted(cv2.minAreaRect(np.array(row['ring'],np.float32))[1])
            assert [short,long] == pytest.approx(sorted([row['truth']['width_mm'],row['truth']['length_mm']]),abs=1.5)


def test_real_sheet_flat_item():
    rows = json.loads((FIXTURES/'real/sheet/sheet-footprints.json').read_text())['records']
    if not any(r['case']=='inside-sheet' for r in rows):
        pytest.skip('awaiting Sean’s flat item (<=2 mm) inside the sheet with measured truth')
    test_real_sheet_rows()


def test_real_plate_markers_and_errors_unchanged():
    from capture.real_oracle import REAL, generate
    from capture.real_sheet_oracle import REAL as SHEET_REAL, generate as generate_sheet
    rows = json.loads((REAL/'real-footprints.json').read_text())['records']
    new_rows = [r for r in json.loads((SHEET_REAL/'sheet-footprints.json').read_text())['records']
                if r['case'] == 'negative-plate']
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    assert len(rows) + len(new_rows) == 8
    for directory, refs in ((REAL, rows), (SHEET_REAL, new_rows)):
        for row in refs:
            image = cv2.imread(str(directory/row['png']))
            _,ids,_ = cv2.aruco.ArucoDetector(dictionary).detectMarkers(image)
            assert ids is None
            assert row['result'] == 'error'
    assert generate(rows) == rows
    assert generate_sheet(new_rows) == new_rows
