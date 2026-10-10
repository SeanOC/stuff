"""Record RAW ArUco corners; run from build123d: uv run python ../scripts/capture-sheet-markers.py.

Unlike the footprint oracle this deliberately does not call cornerSubPix, which
is unavailable in the browser runtime. Existing footprint records stay intact.
"""
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build123d'))
from capture.footprint import DetectionError, detect_grid, marker_corners, sheet_profiles  # noqa: E402


def main():
    fixtures = ROOT / 'build123d/tests/fixtures/capture'
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary)
    records = []
    for path in sorted((fixtures / 'sheet').glob('*.png')):
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        corners, ids, _ = detector.detectMarkers(gray)
        found = {int(i): c.reshape(4, 2) for i, c in zip(ids.ravel(), corners)}
        assert set(found) == {0, 1, 2, 3}, path
        src = np.concatenate([found[i] for i in range(4)])
        fits = []
        for sheet_id, sheet in sheet_profiles().items():
            dst = marker_corners(sheet)
            H, _ = cv2.findHomography(src, dst, cv2.RANSAC, .8)
            error = float(np.linalg.norm(cv2.perspectiveTransform(src[None], H)[0] - dst, axis=1).mean())
            fits.append((error, sheet_id))
        error, sheet_id = min(fits)
        field = sheet_profiles()[sheet_id]['field_mm']
        records.append(dict(png=path.relative_to(fixtures).as_posix(),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            corners={str(i): found[i].tolist() for i in range(4)},
                            sheet_id=sheet_id, size_mm=[field[2]-field[0], field[3]-field[1]],
                            reprojection_mm=error))
    (fixtures / 'sheet-markers.json').write_text(json.dumps(dict(corner_refinement='none', records=records), indent=2)+'\n')

    # The same hidden-marker and displaced-marker inputs as test_capture_sheet.
    from capture.synth import _phone_warp, sheet_background
    errors = fixtures / 'sheet-errors'
    errors.mkdir(exist_ok=True)
    inputs = {}
    profile = sheet_profiles()['letter-v1']
    for hidden in ((0,), (0, 1)):
        for tilt in (0, 15):
            rgb = sheet_background()
            rgb[400:520, 280:480] = (35, 65, 190)
            for i in hidden:
                x, y = profile['markers_mm'][str(i)]
                rgb[round(y*4):round((y+24)*4)+1, round(x*4):round((x+24)*4)+1] = 245
            rgb = cv2.copyMakeBorder(rgb, 48,48,48,48,cv2.BORDER_CONSTANT,value=(40,40,40))
            inputs[f'hidden-{len(hidden)}-t{tilt}.png'] = _phone_warp(rgb, tilt, 42)[0]
    rgb = sheet_background()
    x, y = (round(v*4) for v in profile['markers_mm']['2'])
    marker = rgb[y:y+96,x:x+96].copy()
    rgb[y:y+96,x:x+96] = 245
    rgb[y-32:y+64,x-24:x+72] = marker
    inputs['not-flat.png'] = rgb
    rows = []
    for filename, rgb in inputs.items():
        try:
            detect_grid(rgb)
        except DetectionError as exc:
            rows.append(dict(png=f'sheet-errors/{filename}', error=str(exc)))
        else:
            raise AssertionError(filename)
        cv2.imwrite(str(errors / filename), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    (errors / 'errors.json').write_text(json.dumps(rows, indent=2)+'\n')


if __name__ == '__main__':
    main()
