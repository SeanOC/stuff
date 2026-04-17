"""Pixel-measurement helper for orthographic top renders.

The iteration loop needs numbers, not just pixels (see vision-spike decision:
docs/brainstorms/2026-04-16-openscad-vision-spike-results.md). Given a top
PNG and the model's declared outermost bbox in mm (the PRINT_ANCHOR_BBOX
constant the `/scad-new` skill mandates), return:

- plate bbox in both px and mm
- scale_mm_per_px
- circles_top[]: each with diameter_mm, center_mm, kind ('hole' | 'counterbore')

"Holes" are interior background-colored components (through-features).
"Counterbores" are surface features rendered in Tomorrow colorscheme's
recessed-face hue — useful because the iteration loop needs to confirm
presence/absence of counterbores.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image

BG_CHANNEL_MIN = 240  # Tomorrow colorscheme background is (248,248,248)
BG_CHANNEL_RANGE = 10
COUNTERBORE_RGB = (190, 105, 24)  # Tomorrow-colorscheme recessed-face hue


class MeasurementError(RuntimeError):
    pass


@dataclass
class Circle:
    diameter_mm: float
    center_mm: tuple[float, float]
    area_px: int
    kind: str  # 'hole' or 'counterbore'


@dataclass
class Measurement:
    plate_bbox_px: tuple[int, int, int, int]  # (x0, y0, x1, y1) exclusive upper
    plate_bbox_mm: tuple[float, float]
    scale_mm_per_px: float
    circles_top: list[Circle]

    def to_json(self) -> dict:
        return {
            "plate_bbox_px": list(self.plate_bbox_px),
            "plate_bbox_mm": list(self.plate_bbox_mm),
            "scale_mm_per_px": self.scale_mm_per_px,
            "circles_top": [asdict(c) for c in self.circles_top],
        }


def measure_top(
    top_png: Path | str,
    known_bbox_mm: tuple[float, float],
) -> Measurement:
    """Measure a top-down orthographic render against a known plate bbox.

    `known_bbox_mm` is (width_x_mm, depth_y_mm) — normally PRINT_ANCHOR_BBOX's
    x/y from the model source. Z is ignored on a top view.
    """
    img = np.asarray(Image.open(top_png).convert("RGB"))
    if img.size == 0:
        raise MeasurementError(f"empty PNG: {top_png}")

    is_bg = _background_mask(img)
    is_plate = ~is_bg

    if not is_plate.any():
        raise MeasurementError(f"no plate pixels detected in {top_png}")

    ys, xs = np.where(is_plate)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    px_w, px_h = x1 - x0, y1 - y0

    if px_w <= 0 or px_h <= 0:
        raise MeasurementError(f"degenerate plate bbox in {top_png}: {px_w}x{px_h}")

    scale = known_bbox_mm[0] / px_w

    circles: list[Circle] = []
    circles += _detect_holes(is_bg, (x0, y0, x1, y1), scale)
    circles += _detect_counterbores(img, (x0, y0, x1, y1), scale)
    circles.sort(key=lambda c: -c.diameter_mm)

    return Measurement(
        plate_bbox_px=(x0, y0, x1, y1),
        plate_bbox_mm=(px_w * scale, px_h * scale),
        scale_mm_per_px=scale,
        circles_top=circles,
    )


def _background_mask(img: np.ndarray) -> np.ndarray:
    """True where pixel looks like the Tomorrow colorscheme background."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    near_gray = (
        (r >= BG_CHANNEL_MIN)
        & (g >= BG_CHANNEL_MIN)
        & (b >= BG_CHANNEL_MIN)
        & (np.abs(r.astype(int) - g.astype(int)) <= BG_CHANNEL_RANGE)
        & (np.abs(g.astype(int) - b.astype(int)) <= BG_CHANNEL_RANGE)
    )
    return near_gray


def _detect_holes(
    is_bg: np.ndarray,
    plate_bbox: tuple[int, int, int, int],
    scale: float,
) -> list[Circle]:
    """Interior background components = through-features (holes, bores)."""
    x0, y0, x1, y1 = plate_bbox
    sub = is_bg[y0:y1, x0:x1]
    labels, n = _label_cc(sub)
    out: list[Circle] = []
    for lid in range(1, n + 1):
        ys_l, xs_l = np.where(labels == lid)
        if _touches_edge(ys_l, xs_l, sub.shape):
            continue
        area = len(ys_l)
        d_px = 2 * math.sqrt(area / math.pi)
        cx = x0 + float(xs_l.mean())
        cy = y0 + float(ys_l.mean())
        out.append(Circle(
            diameter_mm=d_px * scale,
            center_mm=(cx * scale, cy * scale),
            area_px=area,
            kind="hole",
        ))
    return out


def _detect_counterbores(
    img: np.ndarray,
    plate_bbox: tuple[int, int, int, int],
    scale: float,
) -> list[Circle]:
    """Orange-hued regions (Tomorrow recessed-face shade) = counterbore annuli."""
    x0, y0, x1, y1 = plate_bbox
    sub = img[y0:y1, x0:x1]
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    tr, tg, tb = COUNTERBORE_RGB
    mask = (
        (np.abs(r.astype(int) - tr) <= 15)
        & (np.abs(g.astype(int) - tg) <= 15)
        & (np.abs(b.astype(int) - tb) <= 15)
    )
    labels, n = _label_cc(mask)
    out: list[Circle] = []
    for lid in range(1, n + 1):
        ys_l, xs_l = np.where(labels == lid)
        area = len(ys_l)
        if area < 50:
            continue
        # Counterbore is an annulus — outer diameter from bbox width, not
        # equivalent-disc area.
        w_px = xs_l.max() - xs_l.min() + 1
        h_px = ys_l.max() - ys_l.min() + 1
        d_px = (w_px + h_px) / 2.0
        cx = x0 + float(xs_l.mean())
        cy = y0 + float(ys_l.mean())
        out.append(Circle(
            diameter_mm=d_px * scale,
            center_mm=(cx * scale, cy * scale),
            area_px=area,
            kind="counterbore",
        ))
    return out


def _touches_edge(ys: np.ndarray, xs: np.ndarray, shape: tuple[int, int]) -> bool:
    h, w = shape
    return bool(
        ys.min() == 0 or xs.min() == 0 or ys.max() == h - 1 or xs.max() == w - 1
    )


def _label_cc(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """4-connected component labels. Pure numpy + stack, no scipy dep."""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    cur = 0
    # Flatten loop; iterative stack to avoid recursion depth.
    for y in range(h):
        for x in range(w):
            if mask[y, x] and labels[y, x] == 0:
                cur += 1
                stack = [(y, x)]
                while stack:
                    cy, cx = stack.pop()
                    if 0 <= cy < h and 0 <= cx < w and mask[cy, cx] and labels[cy, cx] == 0:
                        labels[cy, cx] = cur
                        stack.extend([(cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)])
    return labels, cur
