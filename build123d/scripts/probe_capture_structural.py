"""Reproduce pst-g7npe rev-4 structural acceptance on the real daylight image.

From build123d: uv run python scripts/probe_capture_structural.py > probe.log
The parameter sweep uses production segmentation, not a replacement algorithm.
"""
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capture.footprint import DetectionError, _region, detect_grid, footprint, rectify, segment


def main():
    image = cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/capture/real/sharpie-daylight.png')),
                         cv2.COLOR_BGR2RGB)
    grid = detect_grid(image)
    rectified = rectify(image, grid.H, size_mm=grid.size_mm,
                        kind=grid.kind, polarity=grid.polarity)
    gray = cv2.cvtColor(rectified.image, cv2.COLOR_RGB2GRAY)
    pitch = round(42/rectified.mm_per_px)
    ny, nx = gray.shape[0]//pitch, gray.shape[1]//pitch
    medians = np.median(gray[:ny*pitch,:nx*pitch].reshape(ny,pitch,nx,pitch), axis=(1,3))
    print('tile luminance medians:', medians.tolist())
    print('normalisation gains:', (np.median(medians)/np.maximum(medians,1)).tolist())
    print('| k | shift px | foreground % | bbox mm | acceptance |')
    print('|---|---|---|---|---|')
    roi = _region(rectified)
    for k in (3,5,8):
        for shift in (1,2,3):
            try:
                mask = segment(rectified, k=k, shift_tolerance=shift)
                coverage = np.count_nonzero(mask)/np.count_nonzero(roi)
                ring = footprint(mask)
                sides = np.ptp(ring, axis=0)
                ok = coverage <= .08 and max(sides) >= 100 and abs(min(sides)-12.75) <= 1.5
                print(f'| {k} | {shift} | {coverage*100:.4f} | {sides.tolist()} | {ok} |')
            except DetectionError as exc:
                print(f'| {k} | {shift} | — | {exc} | False |')


if __name__ == '__main__':
    main()
