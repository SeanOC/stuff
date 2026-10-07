"""The raster oracle is structurally stable across platforms, not byte-exact."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
pytest.importorskip('cv2')
from capture.baseline import FIXTURES, generate
from capture.encoding import parse


def test_python_baseline_is_fresh():
    expected = json.loads((FIXTURES / 'python-footprints.json').read_text())
    actual = generate(source_main=expected['source_main'])
    assert actual['threads'] == expected['threads'] == 1
    assert actual['mm_per_px'] == expected['mm_per_px'] == .2
    assert [r['png'] for r in actual['records']] == sorted(r['png'] for r in expected['records'])
    for a, e in zip(actual['records'], expected['records']):
        for key in ('png', 'sha256', 'result', 'kind', 'error', 'vertices', 'truth_mm'):
            assert a[key] == e[key], (e['png'], key)
        if e['result'] == 'footprint':
            # Only the parsed ring is compared: 0.01 mm encoding may round differently.
            for xy, expected_xy in zip(parse(a['footprint']), parse(e['footprint'])):
                assert xy == pytest.approx(expected_xy, abs=.05)
            assert a['area_mm2'] == pytest.approx(e['area_mm2'], abs=.1)
        else:
            assert a['footprint'] is e['footprint'] is None
            assert a['area_mm2'] is e['area_mm2'] is None


def test_python_baseline_expectations():
    baseline = json.loads((FIXTURES / 'python-footprints.json').read_text())
    rows = baseline['records']
    assert len(rows) == 15
    assert not any('aruco' in r['png'] for r in rows)
    assert len({r['png'] for r in rows}) == 15
    for r in rows:
        assert r['truth_mm']
        assert r['sha256'] == hashlib.sha256((FIXTURES / r['png']).read_bytes()).hexdigest()
        if not r['png'].startswith('stress-') or r['png'] == 'stress-shadow.png':
            assert r['result'] == 'footprint'
            assert r['kind'] == 'lattice'
    same = next(r for r in rows if r['png'] == 'stress-same-colour.png')
    assert (same['result'], same['kind'], same['error']) == ('error', 'lattice', 'no item contour')
    edge = next(r for r in rows if r['png'] == 'stress-edge-overhang.png')
    assert (edge['result'], edge['kind']) == ('error', None)
    measurements = json.loads((FIXTURES / 'measurements.json').read_text())
    reference = next(r for r in measurements['stress_cases'] if r['png'] == edge['png'])
    assert reference['detected'] is False
    assert edge['error'] == reference['failure']
