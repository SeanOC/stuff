"""Real-photo parity oracle, separate from the unchanged synthetic baseline.

Regenerate: uv run python -m capture.real_oracle
Source JPEG hashes and caliper truth are provenance supplied at fixture import;
regeneration preserves them and recomputes PNG hashes and all recovered results.
"""
import hashlib
import json
from pathlib import Path

import cv2

from .encoding import encode
from .footprint import DetectionError, _region, detect_grid, footprint, rectify, segment

REAL = Path(__file__).resolve().parents[1]/'tests/fixtures/capture/real'


def generate(references):
    cv2.setNumThreads(1)
    rows = []
    for ref in references:
        path = REAL/ref['png']
        row = {k:ref[k] for k in ('png','original_jpeg_sha256','truth','case')}
        row.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), method='structural',
                   kind=None, polarity=None, result='error', error=None, ring=None, footprint=None)
        try:
            image = cv2.cvtColor(cv2.imread(str(path)),cv2.COLOR_BGR2RGB)
            grid = detect_grid(image)
            row.update(kind=grid.kind,polarity=grid.polarity,
                       method='structural' if grid.polarity == 'dark' else 'threshold')
            rect = rectify(image,grid.H,size_mm=grid.size_mm,kind=grid.kind,polarity=grid.polarity)
            ring = footprint(segment(rect),roi=_region(rect) if grid.polarity == 'dark' else None)
            row.update(result='footprint',ring=ring.tolist(),footprint=encode(ring))
        except DetectionError as exc:
            row['error'] = str(exc)
        rows.append(row)
    return rows


if __name__ == '__main__':
    path = REAL/'real-footprints.json'
    metadata = json.loads(path.read_text())
    metadata['records'] = generate(metadata['records'])
    path.write_text(json.dumps(metadata,indent=2)+'\n')
