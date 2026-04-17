"""Tests for _lib/export.export.

Runs real openscad + trimesh. Slow-ish (few seconds) because openscad does
a full CGAL/Manifold render.
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

from .. import export as exp

HAVE_OPENSCAD = shutil.which("openscad") is not None
HAVE_XVFB = shutil.which("xvfb-run") is not None

pytestmark = pytest.mark.skipif(
    not (HAVE_OPENSCAD and HAVE_XVFB),
    reason="openscad and xvfb-run required",
)

SPIKE_GT = Path(__file__).resolve().parents[3].parent / "spike" / "ground_truth" / "motor_mount.scad"


def _write(tmp: Path, name: str, body: str) -> Path:
    p = tmp / name
    p.write_text(textwrap.dedent(body).lstrip())
    return p


@pytest.mark.skipif(not SPIKE_GT.exists(), reason="spike GT not present")
def test_T1_gt_motor_mount_exports_watertight(tmp_path: Path) -> None:
    out = tmp_path / "motor_mount.stl"
    res = exp.export(SPIKE_GT, out)
    assert res.is_watertight
    assert res.triangle_count > 0
    lo, hi = res.bbox_mm
    size = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    assert abs(size[0] - 60) < 1.0, f"bbox x ≈60, got {size[0]}"
    assert abs(size[1] - 40) < 1.0, f"bbox y ≈40, got {size[1]}"
    assert abs(size[2] - 7) < 1.0, f"bbox z ≈7 (plate 5 + boss 2), got {size[2]}"


def test_T2_non_manifold_model_raises(tmp_path: Path) -> None:
    """Open polyhedron — a tetrahedron with one face omitted. trimesh's
    is_watertight check requires every edge shared by exactly two faces;
    the three open edges fail the check."""
    model = _write(tmp_path, "open_tet.scad", """
        polyhedron(
            points = [[0,0,0],[10,0,0],[5,8,0],[5,4,8]],
            faces = [[0,2,1], [0,1,3], [1,2,3]],
            convexity = 2
        );
    """)
    out = tmp_path / "open_tet.stl"
    with pytest.raises(exp.ExportError) as excinfo:
        exp.export(model, out)
    assert "not watertight" in str(excinfo.value).lower()


def test_T3_missing_stl_raises(tmp_path: Path, monkeypatch) -> None:
    """If openscad exits 0 but STL is gone, helper must raise."""
    model = _write(tmp_path, "cube.scad", "cube([5,5,5]);")
    out = tmp_path / "cube.stl"

    real_run = exp.subprocess.run

    def fake_run(cmd, *a, **kw):
        result = real_run(cmd, *a, **kw)
        if out.exists():
            out.unlink()
        return result

    monkeypatch.setattr(exp.subprocess, "run", fake_run)
    with pytest.raises(exp.ExportError) as excinfo:
        exp.export(model, out)
    assert "not written" in str(excinfo.value) or "empty STL" in str(excinfo.value)


def test_missing_model_raises(tmp_path: Path) -> None:
    with pytest.raises(exp.ExportError) as excinfo:
        exp.export(tmp_path / "nope.scad", tmp_path / "nope.stl")
    assert "model not found" in str(excinfo.value)
