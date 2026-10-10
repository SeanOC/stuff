"""Python-only sheet baseline; PR2 will consume this separate parity contract."""
import hashlib
import json
from pathlib import Path

import cv2

from .encoding import encode, parse
from .footprint import DetectionError, _region, detect_grid, footprint, rectify, segment

FIXTURES = Path(__file__).resolve().parents[1]/'tests/fixtures/capture'


def generate(directory=FIXTURES):
    cv2.setNumThreads(1)
    measurements = json.loads((directory/'sheet-measurements.json').read_text())
    rows = []
    for ref in sorted(measurements['records'], key=lambda r: r['png']):
        path = directory/ref['png']
        row = dict(png=ref['png'], sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   kind=None, result='error', footprint=None, error=None,
                   vertices=0, area_mm2=None, truth_mm=ref['truth_mm'])
        try:
            image = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
            grid = detect_grid(image)
            row['kind'] = grid.kind
            rect = rectify(image, grid.H, size_mm=grid.size_mm, kind=grid.kind)
            wire = encode(footprint(segment(rect), roi=_region(rect),
                                    edge_message='item crosses the sheet field'))
            ring = parse(wire)
            area = abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(ring,ring[1:]))) / 2
            row.update(result='footprint', footprint=wire, vertices=len(ring)-1, area_mm2=area)
        except DetectionError as exc:
            row['error'] = str(exc)
        rows.append(row)
    return dict(source_main=measurements['source_main'], mm_per_px=.2, threads=1, records=rows)


if __name__ == '__main__':
    (FIXTURES/'sheet-footprints.json').write_text(json.dumps(generate(), indent=2)+'\n')
