"""Independent, manually annotated scale check for the daylight fixture.

This is a diagnostic, NOT segmentation or an oracle used by production. The
landmarks are the visible marker's left end and right tip in the original,
orientation-baked 2576x1932 PNG. Allow +/-3 source pixels when re-picking them.
Run from build123d: uv run python scripts/probe_capture_photo_scale.py
Optionally pass --overlay /path/to/overlay.png to inspect the annotations.
"""
import argparse
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capture.footprint import detect_grid

# Human-read landmarks, not recovered by the segmentation under investigation.
ENDPOINTS_PX = np.array([[650, 820], [1930, 858]], dtype=np.float32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay', type=Path)
    args = parser.parse_args()
    image = cv2.imread(str(ROOT/'tests/fixtures/capture/real/sharpie-daylight.png'))
    assert image.shape == (1932, 2576, 3)
    grid = detect_grid(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    mm = cv2.perspectiveTransform(ENDPOINTS_PX[None], grid.H)[0]
    print(f'plate: {grid.size_mm} mm, polarity={grid.polarity}, confidence={grid.confidence:.6f}')
    print(f'manually annotated endpoints (original PNG pixels): {ENDPOINTS_PX.tolist()}')
    print(f'endpoints through production homography (mm): {mm.tolist()}')
    print(f'endpoint distance: {np.linalg.norm(mm[1]-mm[0]):.3f} mm')
    # Exhaust all +/-3 px corner perturbations of both annotations. This is
    # annotation sensitivity only; it is not a camera-calibration error bound.
    shifts = np.array([[-3,-3],[-3,3],[3,-3],[3,3]], np.float32)
    ends = [cv2.perspectiveTransform((p+shifts)[None], grid.H)[0] for p in ENDPOINTS_PX]
    lengths = [np.linalg.norm(b-a) for a in ends[0] for b in ends[1]]
    print(f'+/-3 px annotation sensitivity: {min(lengths):.3f}..{max(lengths):.3f} mm')
    print('rev 5 invariant (d) allows only 120..150 mm; an intact marker exceeds that bound.')
    print('The right tip also lies beyond x=168 mm; the current ROI clips it at x=165 mm.')
    if args.overlay:
        for point, label in zip(ENDPOINTS_PX, ('left end', 'right tip')):
            xy = tuple(point.astype(int))
            cv2.circle(image, xy, 12, (255,0,255), 3)
            cv2.putText(image, label, (xy[0]-20,xy[1]-25), cv2.FONT_HERSHEY_SIMPLEX,
                        .9, (255,0,255), 2)
        if not cv2.imwrite(str(args.overlay), image):
            raise OSError(f'cannot write {args.overlay}')


if __name__ == '__main__':
    main()
