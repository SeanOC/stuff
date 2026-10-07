"""Offline contracts + replay of the committed representative photo fixtures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
cv2 = pytest.importorskip('cv2')  # MUST precede every capture import (audit image has no cv2)
import numpy as np
from shapely.geometry import Polygon
import trimesh

from capture.encoding import encode, parse, validate
from capture.footprint import DetectionError, detect_grid, footprint, rectify, segment
from capture.synth import measure, render_topdown

FIXTURES = Path(__file__).parent/'fixtures'/'capture'


@pytest.fixture(scope='module')
def measurements():
    return json.loads((FIXTURES/'measurements.json').read_text())


def test_experiment_coverage_and_reported_failures(measurements):
    records = measurements['records']
    assert len(records) == 108
    assert len({r['object'] for r in records}) == 6
    for obj in {r['object'] for r in records}:
        rows = [r for r in records if r['object'] == obj]
        assert len(rows) == 18
        assert {r['tilt_deg'] for r in rows} == {0,15}
        assert {r['background'] for r in rows} == {'bare','paper','aruco'}
        assert len({r['pose']['rotation_deg'] for r in rows}) == 3
    for r in records:
        assert Polygon(r['truth_mm']).is_valid
        assert r['detection_seconds'] >= 0
        if not r['detected']:
            assert r['failure'] and not r['methods']
        else:
            assert set(r['methods']) == {'threshold','periodic','grabcut'}
            for m in r['methods'].values():
                assert m['seconds'] >= r['detection_seconds']
                assert 'failure' in m or (m['hausdorff_mm'] >= 0 and m['area_error_pct'] >= 0 and 3 <= m['vertices'] <= 256)


def test_fixture_size_and_integrity(measurements):
    pngs = list(FIXTURES.glob('*.png'))
    assert len(pngs) <= 24
    assert all(p.stat().st_size <= 200_000 for p in pngs)
    selected = [r for r in measurements['records'] if r['png']]
    assert len(selected) == 18
    for r in selected:
        assert hashlib.sha256((FIXTURES/r['png']).read_bytes()).hexdigest() == r['sha256']


@pytest.mark.parametrize('background',['bare','paper','aruco'])
def test_grid_recall_footprint_error_and_area_replay(measurements,background):
    cv2.setNumThreads(1)
    for row in measurements['records']:
        if not row['png'] or row['background'] != background:
            continue
        rgb = cv2.cvtColor(cv2.imread(str(FIXTURES/row['png'])),cv2.COLOR_BGR2RGB)
        actual = measure(rgb,row['truth_mm'])
        assert actual['detected'] == row['detected'], row['id']
        if not actual['detected']:
            assert actual['failure'] == row['failure']
            continue
        for method,expected in row['methods'].items():
            result = actual['methods'][method]
            assert ('failure' in result) == ('failure' in expected), (row['id'],method)
            if 'failure' not in result:
                assert result['hausdorff_mm'] == pytest.approx(expected['hausdorff_mm'],abs=.05), (row['id'],method)
                assert result['area_error_pct'] == pytest.approx(expected['area_error_pct'],abs=.1)
        # The selected baseline has an independent accuracy requirement, not
        # merely a snapshot of whatever output the current code happens to emit.
        if background == 'bare':
            assert actual['methods']['threshold']['hausdorff_mm'] < 2.0


def test_metric_rectification_without_extent():
    rgb = np.full((100,120,3),180,np.uint8)
    H = np.array([[.2,0,-3],[0,.2,-2],[0,0,1.]])
    result = rectify(rgb,H)
    assert result.origin_mm == (-3.,-2.)
    assert result.image.shape[:2] == (100,120)
    mask = np.zeros((100,100),np.uint8)
    mask[10:61,20:71] = 1
    ring = footprint(mask,origin_mm=(5,10))
    polygon = Polygon(ring)
    assert polygon.bounds == pytest.approx((9,12,19,22))
    assert polygon.area == pytest.approx(100)


def test_detection_rejects_featureless_and_clipped_images():
    for image in (np.full((300,300,3),180,np.uint8),np.zeros((300,300,3),np.uint8)):
        with pytest.raises(DetectionError):
            detect_grid(image)


def test_grid_is_measured_not_hardcoded():
    from capture.footprint import _period_count
    for cells in (2,3,4,5,6):
        x = np.arange(840)
        signal = 150+50*np.cos(2*np.pi*x*cells/840)
        assert _period_count(signal)[0] == cells
    with pytest.raises(DetectionError):
        _period_count(np.ones(840))


def test_renderer_fixed_scale_light_and_golden():
    mesh = trimesh.creation.box(extents=(8,6,2))
    mesh.visual.face_colors = [60,120,180,255]
    actual = render_topdown(mesh,.5,(.7,.4,.5),bounds=(-6,-6,6,6))
    golden = cv2.cvtColor(cv2.imread(str(FIXTURES/'renderer-golden.png'),cv2.IMREAD_UNCHANGED),cv2.COLOR_BGRA2RGBA)
    np.testing.assert_array_equal(actual,golden)
    assert actual.shape == (24,24,4)
    rows,cols = np.where(actual[:,:,3] != 0)
    assert (cols.max()-cols.min())*.5 == 8
    assert (rows.max()-rows.min())*.5 == 6
    darker = render_topdown(mesh,.5,(0,0,-1),bounds=(-6,-6,6,6))
    assert darker[:,:,:3].sum() < actual[:,:,:3].sum()


def test_encoding_roundtrip_and_budget():
    ring = [(0,0),(10.123,0),(10.123,10),(0,10),(0,0)]
    value = encode(ring)
    assert parse(value) == [(0,0),(10.12,0),(10.12,10),(0,10),(0,0)]
    angle = np.arange(256)*2*np.pi/256
    circle = np.c_[100+50*np.cos(angle),100+50*np.sin(angle)]
    assert len(parse(encode(np.vstack((circle,circle[0]))))) == 257
    assert len(encode(np.vstack((circle,circle[0]))).encode()) <= 16*1024
    assert validate([(0,0),(252,0),(252,252),(0,252),(0,0)])


@pytest.mark.parametrize('value',[
    'v2;0,0;10,0;10,10;0,0',
    'v1;0,0;10,0;10,10',  # unclosed
    'v1;0,0;2,0;2,2;0,0',  # too small
    'v1;0,0;253,0;253,10;0,0',
    'v1;0,0;10,10;0,10;10,0;0,0',  # crossing
    'v1;0,0;10,0;5,0;5,10;0,0',  # adjacent overlap
    'v1;0,0;10,0;10,10;10,0;0,0',  # repeated vertex
    'v1;0,0;NaN,0;10,10;0,0',
    'v1;0,0;1e2,0;10,10;0,0',
    'v1;0,0;10.001,0;10,10;0,0',
    'v1;0,0;10,0,5;10,10;0,0',
    'v1;'+'0'*16384,
])
def test_encoding_rejects_invalid_wire_values(value):
    with pytest.raises(ValueError):
        parse(value)


def test_quantization_cannot_create_degenerate_ring():
    with pytest.raises(ValueError):
        encode([(0,0),(.001,0),(10,10),(0,10),(0,0)])


def test_encoding_is_available_without_opencv():
    # CB2 can import the parser unchanged without importing the image pipeline.
    code = "import sys; sys.modules['cv2']=None; from capture.encoding import parse; assert parse('v1;0,0;10,0;10,10;0,0')"
    subprocess.run([sys.executable,'-c',code],cwd=FIXTURES.parents[2],check=True)


def test_public_pipeline_exports():
    from capture import detect_grid, rectify, segment, footprint
    assert all(callable(f) for f in (detect_grid, rectify, segment, footprint))


def test_adverse_cases_are_reported(measurements):
    rows = measurements['stress_cases']
    assert {r['id'] for r in rows} == {'same-colour','shadow','edge-overhang'}
    for row in rows:
        rgb = cv2.cvtColor(cv2.imread(str(FIXTURES/row['png'])),cv2.COLOR_BGR2RGB)
        actual = measure(rgb,row['truth_mm'])
        assert actual['detected'] == row['detected']
        for method,expected in row['methods'].items():
            result = actual['methods'][method]
            assert ('failure' in result) == ('failure' in expected)
            if 'failure' not in result:
                assert result['hausdorff_mm'] == pytest.approx(expected['hausdorff_mm'],abs=.05)


@pytest.mark.parametrize('nx,ny',[(2,3),(3,5),(6,2)])
def test_rectangular_lattice_dimensions_from_pixels(nx,ny):
    # Reuse a real rendered socket, not detector internals or the truth H.
    image = cv2.cvtColor(cv2.imread(str(FIXTURES/'label-p0-bare-t0.png')),cv2.COLOR_BGR2RGB)
    socket = image[48:216,48:216]
    board = np.pad(np.tile(socket,(ny,nx,1)),((24,24),(24,24),(0,0)),constant_values=40)
    grid = detect_grid(board)
    assert grid.size_mm == (nx*42,ny*42)
    recovered = cv2.perspectiveTransform(np.array([[[24,24],[24+168*nx-1,24+168*ny-1]]],np.float32),grid.H)[0]
    np.testing.assert_allclose(recovered,[[0,0],[nx*42,ny*42]],atol=.3)
