"""Real-photo acceptance cases for the dark-plate detection contract."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
cv2 = pytest.importorskip('cv2')
from capture.footprint import DetectionError, detect_grid

REAL = Path(__file__).parent / 'fixtures' / 'capture' / 'real'


def photo(name):
    return cv2.cvtColor(cv2.imread(str(REAL / f'{name}.png')), cv2.COLOR_BGR2RGB)


def test_detects_dark_skeleton_plate_on_light_surround():
    grid = detect_grid(photo('sharpie-daylight'))
    assert grid.kind == 'lattice'
    assert grid.polarity == 'dark'
    assert grid.size_mm == pytest.approx((168, 168), abs=1)
    assert grid.confidence >= .5


def test_obstructed_plate_is_named():
    with pytest.raises(DetectionError, match='board obstructed by an object crossing its edge'):
        detect_grid(photo('sharpie-calipers'))
