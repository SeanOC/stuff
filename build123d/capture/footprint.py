"""Image-only metric recovery. RGB uint8 in; no ground truth or camera hints.

Unmarked plates require the entire rectangular boundary and a visible perimeter
row of sockets. The grid's rotational/translation symmetry is resolved by using
the visible upper-left board corner as origin, +X right and +Y down.
"""
from dataclasses import dataclass

import cv2
import numpy as np

PITCH = 42.0
MM_PER_PX = 0.2
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


@dataclass
class Rectified:
    image: np.ndarray
    mm_per_px: float
    origin_mm: tuple[float, float]
    kind: str = 'bare'


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


def detect_grid(image):
    """Return metric H, confidence, extent and calibration kind or raise.

    ArUco IDs 0..3 encode a known 84 mm plate, not a inferred lattice.
    Unmarked rectangular boards infer cell counts from periodic perimeter rails.
    Confidence is a correlation/reprojection score, not a calibrated probability.
    """
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError('expected RGB uint8 image')
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    corners, ids, _ = cv2.aruco.ArucoDetector(dictionary).detectMarkers(gray)
    if ids is not None and set(range(4)).issubset(set(ids.ravel())):
        found = {int(i): c.reshape(4,2) for i,c in zip(ids.ravel(), corners)}
        src = np.concatenate([found[i] for i in range(4)])
        dst = ARUCO_POSITIONS.reshape(-1,2)
        H, inliers = cv2.findHomography(src, dst, cv2.RANSAC, .4)
        if H is None or inliers.sum() < 14:
            raise DetectionError('inconsistent fiducials')
        error = np.linalg.norm(cv2.perspectiveTransform(src[None], H)[0]-dst, axis=1).mean()
        return Grid(H, float(np.exp(-error)), (84.,84.), 'aruco')
    # A pale board on a contrasting dark surround is the explicit capture
    # protocol for the unmarked baseline. Fail if its outer rectangle is clipped.
    _, binary = cv2.threshold(gray, 85, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise DetectionError('no board boundary')
    contour = max(contours, key=cv2.contourArea)
    quad = cv2.approxPolyDP(contour, .015*cv2.arcLength(contour, True), True)
    if len(quad) != 4 or cv2.contourArea(quad) < .15*gray.size:
        raise DetectionError('board boundary is not a visible rectangle')
    src = _ordered_quad(quad)
    h, w = gray.shape
    if np.any(src < 2) or np.any(src[:,0] > w-3) or np.any(src[:,1] > h-3):
        raise DetectionError('board touches image edge')
    square = np.array([[0,0],[839,0],[839,839],[0,839]], np.float32)
    rough_H = cv2.getPerspectiveTransform(src, square)
    rough = cv2.warpPerspective(gray, rough_H, (840,840))
    # Sample strips through the socket lips, keeping the central paper/item out.
    px = np.concatenate((rough[12:45, :], rough[-45:-12, :]), axis=0).mean(0)
    py = np.concatenate((rough[:,12:45], rough[:,-45:-12]), axis=1).mean(1)
    nx, cx = _period_count(px)
    ny, cy = _period_count(py)
    dst = np.array([[0,0],[nx*PITCH,0],[nx*PITCH,ny*PITCH],[0,ny*PITCH]], np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    return Grid(H, min(cx,cy), (nx*PITCH,ny*PITCH), 'lattice')


def rectify(image, H, *, mm_per_px=MM_PER_PX, size_mm=None, kind='bare'):
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
    return Rectified(rgb, mm_per_px, tuple(origin), kind)


def _region(rectified):
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
    if rectified.kind != 'aruco' and white.any():
        x,y,bw,bh = cv2.boundingRect(white)
        if white.sum() > .12*h*w and bw < .9*w and bh < .9*h:
            roi[:] = 0
            roi[y+2:y+bh-2,x+2:x+bw-2] = 1
    return roi


def segment(rectified, method='threshold'):
    """Compare threshold, periodic median background, and lattice-seeded GrabCut."""
    rgb = rectified.image
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    roi = _region(rectified)
    chroma = rgb.max(axis=2).astype(float) - rgb.min(axis=2)
    # Known neutral baseplate/paper: saturated colour or a dark item.
    seed = ((chroma > 35) | (gray < 65)) & (roi != 0)
    if method == 'threshold':
        mask = seed.astype(np.uint8)
    elif method == 'periodic':
        pitch = round(PITCH/rectified.mm_per_px)
        h,w = gray.shape
        if rectified.kind == 'aruco' or np.mean(rgb.min(2) > 225) > .12:
            # Flat backgrounds are the zero-texture special case.
            bg = np.median(rgb[roi != 0], axis=0)
            residual = np.linalg.norm(rgb.astype(float)-bg, axis=2)
        else:
            ny,nx = h//pitch,w//pitch
            if min(nx,ny) < 2:
                raise DetectionError('too few cells for periodic median')
            tiles = rgb[:ny*pitch,:nx*pitch].reshape(ny,pitch,nx,pitch,3)
            template = np.median(tiles, axis=(0,2))
            bg = np.tile(template, (ny+1,nx+1,1))[:h,:w]
            residual = np.linalg.norm(rgb.astype(float)-bg, axis=2)
        mask = ((residual > 48) & (roi != 0)).astype(np.uint8)
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
    # Close only sub-mm raster gaps; do not erase thin hex keys with an opening.
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))


def footprint(mask, *, mm_per_px=MM_PER_PX, origin_mm=(0.,0.), tolerance_mm=.3):
    """Largest external contour, closed ring, <=256 vertices; holes ignored."""
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise DetectionError('no item contour')
    contour = max(contours, key=cv2.contourArea)
    poly = cv2.approxPolyDP(contour, tolerance_mm/mm_per_px, True).reshape(-1,2)
    if len(poly) < 3 or len(poly) > 256:
        raise DetectionError('contour cannot meet the 0.3 mm / 256 vertex contract')
    points = poly.astype(float)*mm_per_px + origin_mm
    return np.vstack((points,points[0]))
