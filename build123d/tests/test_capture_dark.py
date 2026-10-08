"""Real-photo acceptance cases for the dark-plate detection contract."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
cv2 = pytest.importorskip('cv2')
from capture.footprint import DetectionError, _region, detect_grid, footprint, rectify, segment

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


def test_item_crossing_plate_edge_is_named():
    image = photo('sharpie-daylight')
    grid = detect_grid(image)
    rectified = rectify(image, grid.H, size_mm=grid.size_mm,
                        kind=grid.kind, polarity=grid.polarity)
    mask = segment(rectified)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest = max(contours, key=cv2.contourArea)
    assert max(cv2.minAreaRect(largest)[1])*.2 >= 150
    with pytest.raises(DetectionError, match='^item crosses the plate edge$'):
        footprint(mask, roi=_region(rectified))


def test_real_item_inside_plate_bbox():
    import json
    from shapely.geometry import Polygon, LineString
    rows = json.loads((REAL/'real-footprints.json').read_text())['records']
    rows = [r for r in rows if r.get('case') == 'inside-plate' and r.get('truth', {}).get('length_mm')
            and r.get('truth', {}).get('width_mm') and (REAL/r['png']).exists()]
    if not rows:
        pytest.skip('awaiting a real photo with the item fully inside the plate')
    for row in rows:
        image = cv2.cvtColor(cv2.imread(str(REAL/row['png'])), cv2.COLOR_BGR2RGB)
        grid = detect_grid(image)
        rect = rectify(image,grid.H,size_mm=grid.size_mm,kind=grid.kind,polarity=grid.polarity)
        mask = segment(rect)
        assert mask.sum()/np.count_nonzero(_region(rect)) <= .08
        ring = footprint(mask, roi=_region(rect))
        box = cv2.minAreaRect(ring.astype(np.float32))
        length,width = sorted(box[1], reverse=True)
        assert length == pytest.approx(row['truth']['length_mm'], abs=1.5)
        assert width == pytest.approx(row['truth']['width_mm'], abs=1.5)
        if row['truth'].get('barrel_width_mm'):
            corners = cv2.boxPoints(box)
            edges = np.roll(corners,-1,axis=0)-corners
            axis = edges[np.argmax(np.linalg.norm(edges,axis=1))]/length
            noncap = np.array(row['truth']['non_cap_end_mm'])
            if np.dot(np.array(box[0])-noncap,axis) < 0:
                axis = -axis
            normal = np.array([-axis[1],axis[0]])
            start = np.array(box[0])-axis*length/2
            polygon = Polygon(ring)
            widths = []
            for station in (.25,.35,.45):
                center = start+axis*length*station
                cross = polygon.intersection(LineString([center-normal*width,center+normal*width]))
                widths.append(cross.length)
            assert np.median(widths) == pytest.approx(row['truth']['barrel_width_mm'],abs=1.5)


def synthetic_item(illumination=False):
    from capture.synth import white_skeleton_image
    image = white_skeleton_image(illumination)
    grid = detect_grid(image)
    assert grid.polarity == 'dark'
    rect = rectify(image,grid.H,size_mm=grid.size_mm,kind=grid.kind,polarity=grid.polarity)
    return rect


@pytest.mark.parametrize('illumination',[False,True])
def test_structural_segments_white_item_on_black_skeleton(illumination):
    rect = synthetic_item(illumination)
    mask = segment(rect)
    ring = footprint(mask,roi=_region(rect))
    import json
    oracle = json.loads((REAL.parent/'structural-footprints.json').read_text())
    expected = oracle['illuminated' if illumination else 'plain']
    assert ring == pytest.approx(np.array(expected['ring']),abs=.05)
    assert np.ptp(ring,axis=0) == pytest.approx((30,12),abs=1)
    assert mask.sum()/np.count_nonzero(_region(rect)) < .10


@pytest.mark.parametrize('option,value', [('confidence_floor',.3),('confidence_floor',.8),
    ('k',3),('k',8),('coverage_limit',.2),('coverage_limit',.5),
    ('shift_tolerance',1),('shift_tolerance',3)])
def test_structural_parameter_endpoints(option,value):
    image = photo('sharpie-daylight')
    try:
        grid = detect_grid(image, **({option:value} if option == 'confidence_floor' else {}))
        rect = rectify(image,grid.H,size_mm=grid.size_mm,kind=grid.kind,polarity=grid.polarity)
        mask = segment(rect, **({option:value} if option != 'confidence_floor' else {}))
        footprint(mask,roi=_region(rect))
    except DetectionError as exc:
        assert str(exc) in {'item crosses the plate edge',
            'item too large for the plate or background not modelled',
            'perimeter does not support a 42 mm lattice'}


def test_pale_plate_threshold_unchanged():
    import json
    from shapely.geometry import Polygon
    fixtures = REAL.parent
    rows = json.loads((fixtures/'measurements.json').read_text())['records']
    errors = {'bare':[], 'paper':[]}
    for row in rows:
        if not row['png'] or row['background'] not in errors:
            continue
        image = cv2.cvtColor(cv2.imread(str(fixtures/row['png'])),cv2.COLOR_BGR2RGB)
        grid = detect_grid(image)
        assert grid.polarity == 'pale' and grid.size_mm == (168,168)
        rect = rectify(image,grid.H,size_mm=grid.size_mm,kind=grid.kind,polarity=grid.polarity)
        assert np.array_equal(segment(rect),segment(rect,'threshold'))
        errors[row['background']].append(Polygon(footprint(segment(rect))).hausdorff_distance(Polygon(row['truth_mm'])))
    for bg,mean in (('bare',.835),('paper',.832)):
        assert len(errors[bg]) == 6
        assert np.mean(errors[bg]) <= mean and max(errors[bg]) <= 1.612
