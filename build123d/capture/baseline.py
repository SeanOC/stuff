"""Committed threshold-only oracle for the browser port; never uses truth to fit.

Run from build123d/: uv run --group capture python -m capture.baseline
"""
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import cv2

from .encoding import encode, parse
from .footprint import MM_PER_PX, DetectionError, detect_grid, footprint, rectify, segment

FIXTURES = Path(__file__).resolve().parents[1] / 'tests/fixtures/capture'


def generate(*, source_main=None):
    # Match test_capture_spike.py:62 before any raster reductions.
    cv2.setNumThreads(1)
    measurements = json.loads((FIXTURES / 'measurements.json').read_text())
    selected = [r for r in measurements['records']
                if r['png'] and r['background'] in ('bare', 'paper')]
    selected += measurements['stress_cases']
    records = []
    for reference in sorted(selected, key=lambda r: r['png']):
        path = FIXTURES / reference['png']
        row = dict(png=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   kind=None, result='error', footprint=None, error=None,
                   vertices=0, area_mm2=None, truth_mm=reference['truth_mm'])
        rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
        try:
            grid = detect_grid(rgb)
            row['kind'] = grid.kind
            rectified = rectify(rgb, grid.H, size_mm=grid.size_mm, kind=grid.kind)
            wire = encode(footprint(segment(rectified, method='threshold'),
                                    mm_per_px=rectified.mm_per_px,
                                    origin_mm=rectified.origin_mm))
            ring = parse(wire)
            area = abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(ring, ring[1:]))) / 2
            row.update(result='footprint', footprint=wire, vertices=len(ring)-1, area_mm2=area)
        except DetectionError as exc:
            row['error'] = str(exc)
        records.append(row)
    if source_main is None:
        source_main = subprocess.check_output(
            ['git', 'rev-parse', 'origin/main'], cwd=FIXTURES, text=True).strip()
    return dict(source_main=source_main, opencv=cv2.__version__, python=platform.python_version(),
                machine=platform.machine(), cpu=platform.processor(), threads=1,
                mm_per_px=MM_PER_PX, records=records)


if __name__ == '__main__':
    (FIXTURES / 'python-footprints.json').write_text(json.dumps(generate(), indent=2) + '\n')
