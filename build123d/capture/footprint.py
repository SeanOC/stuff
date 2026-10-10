"""Image-only metric recovery. RGB uint8 in; no ground truth or camera hints.

Unmarked plates require the entire rectangular boundary and a visible perimeter
row of sockets. The grid's rotational/translation symmetry is resolved by using
the visible upper-left board corner as origin, +X right and +Y down.
"""
from dataclasses import dataclass
import json
from pathlib import Path

import cv2
import numpy as np

PITCH = 42.0
MM_PER_PX = 0.2
SHEET_RANSAC_TOLERANCE_MM = 0.8
SHEET_MAX_MEAN_REPROJECTION_MM = 0.8
ARUCO_POSITIONS = np.array([
    [[3,3],[13,3],[13,13],[3,13]],
    [[71,3],[81,3],[81,13],[71,13]],
    [[71,71],[81,71],[81,81],[71,81]],
    [[3,71],[13,71],[13,81],[3,81]],
], dtype=np.float32)


class DetectionError(ValueError):
    pass


@dataclass
class Grid:
    H: np.ndarray  # image pixels -> millimetres
    confidence: float
    size_mm: tuple[float, float]
    kind: str
    polarity: str = 'pale'
    sheet_id: str | None = None
    reprojection_mm: float | None = None


@dataclass
class Rectified:
    image: np.ndarray
    mm_per_px: float
    origin_mm: tuple[float, float]
    kind: str = 'bare'
    polarity: str = 'pale'


def _ordered_quad(points):
    p = np.asarray(points, np.float32).reshape(4, 2)
    center = p.mean(axis=0)
    p = p[np.argsort(np.arctan2(p[:,1]-center[1], p[:,0]-center[0]))]
    return np.roll(p, -np.argmin(p.sum(axis=1)), axis=0)


def _period_count(profile):
    """Find a repeated perimeter socket signal, reject featureless backgrounds."""
    p = profile.astype(float)
    p -= p.mean()
    if p.std() < 3:
        raise DetectionError('no perimeter lattice contrast')
    # Test integer counts 2..6; do not assume the fixture has four cells.
    scores = []
    for n in range(2, 7):
        lag = int(round(len(p) / n))
        a, b = p[:-lag], p[lag:]
        score = float(np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b)+1e-9))
        scores.append((score, n))
    best = max(scores)
    # Harmonics at two cells can also match a four-cell plate. Prefer the
    # shortest repeat among scores close to the best supported correlation.
    candidates = [s for s in scores if s[0] >= max(.60, best[0]-.06)]
    if not candidates:
        raise DetectionError('perimeter does not support a 42 mm lattice')
    score, count = max(candidates, key=lambda s: s[1])
    return count, score


def _interior_count(rough, axis):
    """Whole-grid autocorrelation tolerates a rim without socket lips."""
    profile = rough.mean(axis=axis).astype(float)
    profile -= profile.mean()
    if profile.std() < 3:
        raise DetectionError('no perimeter lattice contrast')
    scores = []
    for n in range(2, 7):
        lag = round(len(profile)/n)
        a, b = profile[:-lag], profile[lag:]
        score = float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9))
        scores.append((score, n))
    best = max(scores)[0]
    return max((s for s in scores if s[0] >= best-.06), key=lambda s:s[1])[::-1]


def sheet_profiles():
    """Read the checked-in metric profiles; the generator owns their constants."""
    return json.loads(Path(__file__).with_name('sheets.json').read_text())


def marker_corners(sheet, ids=range(4)):
    size = sheet['marker_size_mm']
    offsets = np.array([[0, 0], [size, 0], [size, size], [0, size]])
    return np.concatenate([np.asarray(sheet['markers_mm'][str(i)]) + offsets
                           for i in ids]).astype(np.float32)


def _partial_sheet(found, sheets):
    # Fit all observed marker corners together, then check both local marker
    # size and inter-marker spacing in the recovered page frame. A local fit
    # to one rasterised marker is too noisy to extrapolate across a full page.
    ids = sorted(found)
    src = np.concatenate([found[i] for i in ids])
    for sheet in sheets.values():
        dst = marker_corners(sheet, ids)
        H, _ = cv2.findHomography(src, dst, 0)
        if H is None:
            continue
        projected = cv2.perspectiveTransform(src[None], H)[0].reshape(-1,4,2)
        expected = dst.reshape(-1,4,2)
        size = sheet['marker_size_mm']
        lengths = np.linalg.norm(np.roll(projected,-1,axis=1)-projected,axis=2)
        if np.any(abs(lengths-size) > .1*size):
            continue
        if np.any(np.linalg.norm(projected-expected,axis=2) > .1*size):
            continue
        centres = projected.mean(axis=1)
        target_centres = expected.mean(axis=1)
        if all(abs(np.linalg.norm(centres[i]-centres[j]) /
                   np.linalg.norm(target_centres[i]-target_centres[j])-1) <= .1
               for i in range(len(ids)) for j in range(i)):
            return True
    return False


def detect_grid(image, *, confidence_floor=.5, sheets=None, bar_mm=100.0):
    """Return metric H, confidence, extent and calibration kind or raise.

    ArUco IDs 0..3 identify either a reference sheet or the legacy 84 mm plate.
    bar_mm is the measured printed 100 mm check bar (90..110 mm).
    Unmarked rectangular boards infer cell counts from periodic perimeter rails.
    Confidence is a correlation/reprojection score, not a calibrated probability.
    """
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError('expected RGB uint8 image')
    if not np.isfinite(bar_mm) or not 90 <= bar_mm <= 110:
        raise ValueError('bar_mm must be in 90..110')
    sheets = sheet_profiles() if sheets is None else sheets
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    corners, ids, _ = cv2.aruco.ArucoDetector(dictionary).detectMarkers(gray)
    found = {} if ids is None else {int(i): c.reshape(4, 2)
                                    for i, c in zip(ids.ravel(), corners) if i in range(4)}
    if len(found) == 4:
        src = np.concatenate([found[i] for i in range(4)])
        # Preserve the established small square ArUco plate calibration. Its
        # marker-size/spacing ratio differs from both printed sheet profiles.
        dst = ARUCO_POSITIONS.reshape(-1,2)
        H, inliers = cv2.findHomography(src, dst, cv2.RANSAC, .4)
        if H is not None and inliers.sum() >= 14:
            error = np.linalg.norm(cv2.perspectiveTransform(src[None], H)[0]-dst, axis=1).mean()
            return Grid(H, float(np.exp(-error)), (84.,84.), 'aruco')
        src = cv2.cornerSubPix(gray, src.copy(), (3,3), (-1,-1),
                               (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 30, .01))
        fits = []
        for sheet_id, sheet in sheets.items():
            dst = marker_corners(sheet)
            # Reprojection residuals are measured in dst coordinates: page mm.
            H, _ = cv2.findHomography(src, dst, cv2.RANSAC, SHEET_RANSAC_TOLERANCE_MM)
            if H is not None:
                error = float(np.linalg.norm(cv2.perspectiveTransform(src[None], H)[0]-dst, axis=1).mean())
                fits.append((error, sheet_id, H))
        if not fits or min(fits, key=lambda fit: fit[0])[0] >= SHEET_MAX_MEAN_REPROJECTION_MM:
            raise DetectionError('sheet is not flat or the print is scaled')
        error, sheet_id, H = min(fits, key=lambda fit: fit[0])
        x0, y0, x1, y1 = sheets[sheet_id]['field_mm']
        k = bar_mm / 100.0
        field_frame = np.array([[k, 0, -k*x0], [0, k, -k*y0], [0, 0, 1.]])
        return Grid(field_frame@H, float(np.exp(-error)), ((x1-x0)*k, (y1-y0)*k),
                    'sheet', sheet_id=sheet_id, reprojection_mm=error)
    if len(found) in (2, 3) and _partial_sheet(found, sheets):
        raise DetectionError('a reference marker is hidden — keep all four corners visible and uncovered')
    if not .3 <= confidence_floor <= .8:
        raise ValueError('confidence_floor must be in 0.3..0.8')
    candidates = []
    errors = []
    obstructed = False
    h, w = gray.shape
    for polarity, mode in (('pale', cv2.THRESH_BINARY), ('dark', cv2.THRESH_BINARY_INV)):
        _, binary = cv2.threshold(gray, 85, 255, mode)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) < .15*gray.size:
                continue
            hull = cv2.convexHull(contour)
            hull_quad = cv2.approxPolyDP(hull, .015*cv2.arcLength(hull, True), True)
            if len(hull_quad) > 4:
                obstructed = True
                continue
            # Preserve the existing pale path's exact corner samples.
            quad = cv2.approxPolyDP(contour, .015*cv2.arcLength(contour, True), True)
            if len(quad) != 4 and polarity == 'dark':
                quad = hull_quad
            if len(quad) != 4 or cv2.contourArea(quad) < .15*gray.size:
                errors.append('board boundary is not a visible rectangle')
                continue
            src = _ordered_quad(quad)
            if np.any(src < 2) or np.any(src[:,0] > w-3) or np.any(src[:,1] > h-3):
                errors.append('board touches image edge')
                continue
            square = np.array([[0,0],[839,0],[839,839],[0,839]], np.float32)
            rough = cv2.warpPerspective(gray, cv2.getPerspectiveTransform(src, square), (840,840))
            px = np.concatenate((rough[12:45, :], rough[-45:-12, :]), axis=0).mean(0)
            py = np.concatenate((rough[:,12:45], rough[:,-45:-12]), axis=1).mean(1)
            try:
                nx, cx = _period_count(px)
                ny, cy = _period_count(py)
            except DetectionError:
                try:
                    nx, cx = _interior_count(rough, 0)
                    ny, cy = _interior_count(rough, 1)
                except DetectionError as exc:
                    errors.append(str(exc))
                    continue
            confidence = min(cx, cy)
            if confidence < confidence_floor:
                errors.append('perimeter does not support a 42 mm lattice')
                continue
            dst = np.array([[0,0],[nx*PITCH,0],[nx*PITCH,ny*PITCH],[0,ny*PITCH]], np.float32)
            candidates.append(Grid(cv2.getPerspectiveTransform(src, dst), confidence,
                                   (nx*PITCH,ny*PITCH), 'lattice', polarity))
    if obstructed:
        raise DetectionError('board obstructed by an object crossing its edge')
    if not candidates:
        raise DetectionError(errors[0] if errors else 'board boundary is not a visible rectangle')
    return max(candidates, key=lambda candidate: candidate.confidence)


def rectify(image, H, *, mm_per_px=MM_PER_PX, size_mm=None, kind='bare', polarity='pale'):
    """Warp to uniform metric pixels. H maps source pixel centres to mm.

    Pass size_mm from Grid to crop to the baseplate; without it, cover the
    transformed source image and return the (possibly negative) metric origin.
    """
    if not np.isfinite(mm_per_px) or mm_per_px <= 0:
        raise ValueError('mm_per_px must be positive')
    origin = np.zeros(2)
    include_last_sample = size_mm is None
    if size_mm is None:
        h,w = image.shape[:2]
        corners = cv2.perspectiveTransform(np.array([[[0,0],[w-1,0],[w-1,h-1],[0,h-1]]], np.float64), H)[0]
        origin = np.floor(corners.min(0)/mm_per_px)*mm_per_px
        size_mm = corners.max(0)-origin
    # Source bounds describe sample centres, so an uncropped warp includes
    # both endpoints. Explicit board extents describe a half-open metric area.
    size = np.ceil(np.asarray(size_mm)/mm_per_px - 1e-9).astype(int)
    size += int(include_last_sample)
    if np.any(size <= 0) or np.any(size > 4096):
        raise ValueError('invalid or excessive rectified extent')
    to_pixels = np.array([[1/mm_per_px,0,-origin[0]/mm_per_px],[0,1/mm_per_px,-origin[1]/mm_per_px],[0,0,1]])
    rgb = cv2.warpPerspective(image, to_pixels@H, tuple(size), borderValue=(0,0,0))
    return Rectified(rgb, mm_per_px, tuple(origin), kind, polarity)


def _region(rectified, *, with_paper=False):
    rgb = rectified.image
    h,w = rgb.shape[:2]
    roi = np.zeros((h,w), np.uint8)
    inset = round(3/rectified.mm_per_px)
    roi[inset:h-inset,inset:w-inset] = 1
    if rectified.kind == 'aruco':
        corner = round(14/rectified.mm_per_px)
        roi[:corner,:corner] = roi[:corner,-corner:] = 0
        roi[-corner:,:corner] = roi[-corner:,-corner:] = 0
    # White paper interior is detected from colour, never supplied from truth.
    white = (rgb.min(axis=2) > 225).astype(np.uint8)
    paper = False
    if rectified.polarity == 'pale' and rectified.kind not in ('aruco', 'sheet') and white.any():
        x,y,bw,bh = cv2.boundingRect(white)
        if white.sum() > .12*h*w and bw < .9*w and bh < .9*h:
            paper = True
            roi[:] = 0
            roi[y+2:y+bh-2,x+2:x+bw-2] = 1
    return (roi, paper) if with_paper else roi


def _structural(rectified, roi, *, k, coverage_limit, shift_tolerance):
    """Phase median + background-inlier RGB gain/offset fit + local matching."""
    if not 3 <= k <= 8 or not .2 <= coverage_limit <= .5:
        raise ValueError('k must be in 3..8 and coverage_limit in 0.2..0.5')
    if shift_tolerance not in (1, 2, 3):
        raise ValueError('shift_tolerance must be 1, 2 or 3 pixels')
    rgb = rectified.image
    pitch = round(PITCH/rectified.mm_per_px)
    h, w = rgb.shape[:2]
    ny, nx = h//pitch, w//pitch
    if nx*ny < 4:
        raise DetectionError('item too large for the plate or background not modelled')
    # A phase median discards objects/shadows present in a minority of cells.
    tiles = rgb[:ny*pitch,:nx*pitch].astype(float).reshape(ny,pitch,nx,pitch,3)
    template = np.median(tiles, axis=(0,2))
    x = template.reshape(-1,3)
    # Learn intensity strata from the template, not from a hand-drawn class
    # map. Trimming each stratum keeps both bright and dark background samples
    # in the illumination fit even when an item contaminates one brightness.
    levels = x.mean(axis=1)
    bins = np.digitize(levels,np.percentile(levels,[25,50,75]))
    def inliers(error):
        good = np.zeros(len(error),bool)
        for index in range(4):
            selected = bins == index
            values = error[selected]
            if not len(values): continue
            mid = np.median(values)
            good[selected] = values <= max(1.,mid+2*np.median(abs(values-mid)))
        return good
    residual = np.full((h,w), np.inf)
    for iy in range(ny):
        for ix in range(nx):
            tile = tiles[iy,:,ix]
            y = tile.reshape(-1,3)
            error = np.linalg.norm(y-x, axis=1)
            good = inliers(error)
            # Six trimmed least-squares updates fit illumination only on the
            # background inliers. Never normalise by an occupied tile's median.
            for _ in range(6):
                xm, ym = x[good].mean(0), y[good].mean(0)
                variance = np.sum((x[good]-xm)**2, axis=0)
                covariance = np.sum((x[good]-xm)*(y[good]-ym), axis=0)
                gain = np.divide(covariance, variance, out=np.ones(3), where=variance>1)
                offset = ym-gain*xm
                error = np.linalg.norm(y-(x*gain+offset), axis=1)
                good = inliers(error)
            background = template*gain+offset
            lo, hi = background.copy(), background.copy()
            for dy in range(-shift_tolerance,shift_tolerance+1):
                for dx in range(-shift_tolerance,shift_tolerance+1):
                    shifted = np.roll(background, (dy,dx), axis=(0,1))
                    lo, hi = np.minimum(lo,shifted), np.maximum(hi,shifted)
            # Local colour envelope also tolerates fractional-pixel resampling.
            cell = np.linalg.norm(tile-np.clip(tile,lo,hi), axis=2)
            residual[iy*pitch:(iy+1)*pitch,ix*pitch:(ix+1)*pitch] = cell
    values = residual[roi != 0]
    median = np.median(values)
    threshold = max(1., median + k*np.median(np.abs(values-median)))
    mask = ((residual > threshold) & (roi != 0)).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
    if mask.sum() > coverage_limit*np.count_nonzero(roi):
        raise DetectionError('item too large for the plate or background not modelled')
    return mask



def segment(rectified, method=None, *, k=5., coverage_limit=.35, shift_tolerance=2):
    """Default to threshold for pale plates and structural residuals for dark plates."""
    rgb = rectified.image
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    roi, paper = _region(rectified, with_paper=True)
    if rectified.kind == 'sheet' and method not in (None, 'periodic'):
        raise ValueError('sheet segmentation requires the periodic method')
    if method is None:
        method = ('periodic' if rectified.kind == 'sheet' else
                  'structural' if rectified.polarity == 'dark' else 'threshold')
    chroma = rgb.max(axis=2).astype(float) - rgb.min(axis=2)
    # Known neutral baseplate/paper: saturated colour or a dark item.
    seed = ((chroma > 35) | (gray < 65)) & (roi != 0)
    if method == 'threshold':
        mask = seed.astype(np.uint8)
    elif method == 'periodic':
        pitch = round(PITCH/rectified.mm_per_px)
        h,w = gray.shape
        if rectified.kind in ('aruco', 'sheet') or (rectified.polarity == 'pale' and paper):
            # Flat backgrounds are the zero-texture special case.
            pixels = rgb
            if rectified.kind == 'sheet':
                median = np.median(rgb[roi != 0], axis=0)
                gains = median.mean() / np.maximum(median, 1)
                pixels = np.clip(rgb.astype(float)*gains, 0, 255)
            bg = np.median(pixels[roi != 0], axis=0)
            residual = np.linalg.norm(pixels.astype(float)-bg, axis=2)
        else:
            ny,nx = h//pitch,w//pitch
            if min(nx,ny) < 2:
                raise DetectionError('too few cells for periodic median')
            tiles = rgb[:ny*pitch,:nx*pitch].reshape(ny,pitch,nx,pitch,3)
            template = np.median(tiles, axis=(0,2))
            bg = np.tile(template, (ny+1,nx+1,1))[:h,:w]
            residual = np.linalg.norm(rgb.astype(float)-bg, axis=2)
        mask = ((residual > 48) & (roi != 0)).astype(np.uint8)
        if rectified.kind == 'sheet':
            chroma = pixels.max(axis=2)-pixels.min(axis=2)
            lightness = pixels.mean(axis=2)
            item = (chroma > 20) | (lightness < .55*bg.mean()) | (lightness > 1.30*bg.mean())
            # Chroma independently identifies tinted items close to field lightness.
            mask = (item & (roi != 0)).astype(np.uint8)
    elif method == 'structural':
        mask = _structural(rectified, roi, k=k, coverage_limit=coverage_limit, shift_tolerance=shift_tolerance)
    elif method == 'grabcut':
        labels = np.full(gray.shape, cv2.GC_BGD, np.uint8)
        labels[roi != 0] = cv2.GC_PR_BGD
        labels[seed] = cv2.GC_PR_FGD
        # Calibrated 42 mm cells with no item candidates supply hard background
        # seeds. Occupied cells retain probable background around their item.
        pitch = round(PITCH/rectified.mm_per_px)
        for y in range(0, gray.shape[0], pitch):
            for x in range(0, gray.shape[1], pitch):
                cell = np.s_[y:y+pitch, x:x+pitch]
                if not seed[cell].any():
                    labels[cell] = cv2.GC_BGD
        sure = cv2.erode(seed.astype(np.uint8), np.ones((3,3),np.uint8)) != 0
        labels[sure] = cv2.GC_FGD
        if not sure.any():
            raise DetectionError('no foreground seeds')
        cv2.setRNGSeed(0)
        cv2.grabCut(rgb, labels, None, np.zeros((1,65)), np.zeros((1,65)), 2, cv2.GC_INIT_WITH_MASK)
        mask = ((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD)).astype(np.uint8)
    else:
        raise ValueError('unknown segmentation method')
    if rectified.kind == 'sheet':
        size = max(1, round(1/rectified.mm_per_px)) | 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    # Close only sub-mm raster gaps; do not erase thin hex keys with an opening.
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))


def footprint(mask, *, mm_per_px=MM_PER_PX, origin_mm=(0.,0.), tolerance_mm=.3, roi=None,
              edge_message='item crosses the plate edge'):
    """Largest external contour, closed ring, <=256 vertices; holes ignored."""
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise DetectionError('no item contour')
    contour = max(contours, key=cv2.contourArea)
    if roi is not None:
        boundary = (roi != 0) & (cv2.erode(roi.astype(np.uint8), np.ones((3,3),np.uint8)) == 0)
        points = contour.reshape(-1,2)
        if boundary[points[:,1],points[:,0]].any():
            raise DetectionError(edge_message)
    poly = cv2.approxPolyDP(contour, tolerance_mm/mm_per_px, True).reshape(-1,2)
    if len(poly) < 3 or len(poly) > 256:
        raise DetectionError('contour cannot meet the 0.3 mm / 256 vertex contract')
    points = poly.astype(float)*mm_per_px + origin_mm
    return np.vstack((points,points[0]))
