"""Reproduce pst-g7npe rev-6 structural acceptance on the real daylight image.

From build123d: uv run python scripts/probe_capture_structural.py > probe.log
The parameter sweep uses production segmentation, not a replacement algorithm.
"""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capture.footprint import DetectionError, _region, detect_grid, footprint, rectify, segment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-oracle', type=Path,
                        help='write reproducible plain/illuminated white-item parity rings')
    args = parser.parse_args()
    if args.synthetic_oracle:
        from capture.synth import white_skeleton_image
        rows = {}
        for key,illumination in (('plain',False),('illuminated',True)):
            rgb = white_skeleton_image(illumination)
            grid = detect_grid(rgb)
            rect = rectify(rgb,grid.H,size_mm=grid.size_mm,kind=grid.kind,polarity=grid.polarity)
            ring = footprint(segment(rect),roi=_region(rect))
            rows[key] = {'ring':ring.tolist(),'method':'structural','polarity':grid.polarity}
        args.synthetic_oracle.write_text(json.dumps(rows,indent=2)+'\n')
        return
    image = cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/capture/real/sharpie-daylight.png')),
                         cv2.COLOR_BGR2RGB)
    grid = detect_grid(image)
    rectified = rectify(image, grid.H, size_mm=grid.size_mm,
                        kind=grid.kind, polarity=grid.polarity)
    print('| k | shift px | foreground % | largest long axis mm | result |')
    print('|---|---|---|---|---|')
    roi = _region(rectified)
    for k in (3,5,8):
        for shift in (1,2,3):
            try:
                mask = segment(rectified, k=k, shift_tolerance=shift)
                coverage = np.count_nonzero(mask)/np.count_nonzero(roi)
                contours, _ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                largest = max(contours,key=cv2.contourArea)
                length = max(cv2.minAreaRect(largest)[1])*rectified.mm_per_px
                try:
                    footprint(mask,roi=roi)
                    result = 'unexpected footprint'
                except DetectionError as exc:
                    result = str(exc)
                print(f'| {k} | {shift} | {coverage*100:.4f} | {length:.3f} | {result} |')
            except DetectionError as exc:
                print(f'| {k} | {shift} | — | — | {exc} |')


if __name__ == '__main__':
    main()
