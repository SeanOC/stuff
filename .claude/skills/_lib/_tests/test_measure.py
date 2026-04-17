"""Tests for _lib/measure.measure_top.

Uses spike fixtures under spike/renders/ as golden inputs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from .. import measure

SPIKE = Path(__file__).resolve().parents[3].parent / "spike" / "renders"


@pytest.mark.skipif(
    not (SPIKE / "gt" / "top.png").exists(),
    reason="spike fixtures not present",
)
def test_T1_gt_motor_mount() -> None:
    m = measure.measure_top(SPIKE / "gt" / "top.png", known_bbox_mm=(60.0, 40.0))
    assert abs(m.plate_bbox_mm[0] - 60.0) < 0.01
    # scale is 60/px_w; with a 832-px plate that's ~0.0721 mm/px
    assert 0.07 <= m.scale_mm_per_px <= 0.075

    holes = [c for c in m.circles_top if c.kind == "hole"]
    cbs = [c for c in m.circles_top if c.kind == "counterbore"]
    assert len(cbs) == 4, f"expected 4 counterbore rings, got {len(cbs)}"

    hole_diams = sorted(c.diameter_mm for c in holes)
    # 1 central bore (~20 mm) + 4 clearance holes (~3.2 mm)
    assert len(holes) == 5, f"expected 5 interior holes, got {len(holes)}"
    assert 19.5 <= hole_diams[-1] <= 20.5, f"bore ≈20 mm, got {hole_diams[-1]}"
    for d in hole_diams[:4]:
        assert 2.8 <= d <= 3.6, f"clearance hole ≈3.2 mm, got {d}"

    cb_diams = [c.diameter_mm for c in cbs]
    for d in cb_diams:
        assert 5.5 <= d <= 6.5, f"counterbore ≈6 mm, got {d}"


@pytest.mark.skipif(
    not (SPIKE / "v0_perturbed" / "top.png").exists(),
    reason="spike fixtures not present",
)
def test_T2_v0_perturbed_bore_oversized_no_counterbores() -> None:
    m = measure.measure_top(
        SPIKE / "v0_perturbed" / "top.png", known_bbox_mm=(60.0, 40.0)
    )
    cbs = [c for c in m.circles_top if c.kind == "counterbore"]
    holes = [c for c in m.circles_top if c.kind == "hole"]
    assert len(cbs) == 0, "v0_perturbed should have no counterbore rings"
    # hole_dx was perturbed to 60 (plate_w=60), so clearance holes sit on the
    # plate edge and get rejected as edge-touching. Only the central bore
    # remains interior — this is exactly the signal that catches the D2
    # defect (hole spacing too wide).
    assert len(holes) == 1, f"expected just the bore, got {len(holes)}"
    bore = holes[0]
    assert 21.5 <= bore.diameter_mm <= 22.5, f"bore ≈22 mm, got {bore.diameter_mm}"


def test_T3_blank_png_raises(tmp_path: Path) -> None:
    blank = Image.new("RGB", (64, 64), color=(248, 248, 248))
    blank_path = tmp_path / "blank.png"
    blank.save(blank_path)
    with pytest.raises(measure.MeasurementError) as exc:
        measure.measure_top(blank_path, known_bbox_mm=(60.0, 40.0))
    assert "no plate" in str(exc.value).lower()


def test_background_mask_catches_near_white() -> None:
    img = np.array(
        [
            [[248, 248, 248], [247, 248, 249]],  # bg, near-bg
            [[51, 88, 135], [0, 0, 0]],  # plate, black
        ],
        dtype=np.uint8,
    )
    mask = measure._background_mask(img)
    assert mask[0, 0] and mask[0, 1]
    assert not mask[1, 0]
    assert not mask[1, 1]


def test_label_cc_counts_disjoint_regions() -> None:
    m = np.zeros((5, 5), dtype=bool)
    m[0, 0] = True
    m[4, 4] = True
    m[2, 2] = True
    labels, n = measure._label_cc(m)
    assert n == 3
