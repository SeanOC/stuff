"""Tests for scad-export/scripts/export.py.

Runs openscad + trimesh end-to-end. Slow-ish (~2-4 s per test).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3].parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "scad-export" / "scripts" / "export.py"

HAVE_OPENSCAD = shutil.which("openscad") is not None
HAVE_XVFB = shutil.which("xvfb-run") is not None

pytestmark = pytest.mark.skipif(
    not (HAVE_OPENSCAD and HAVE_XVFB),
    reason="openscad and xvfb-run required",
)


def _write(tmp: Path, name: str, body: str) -> Path:
    p = tmp / name
    p.write_text(textwrap.dedent(body).lstrip())
    return p


def _run(model: Path, tmp_path: Path, *extra: str) -> tuple[int, dict]:
    """Invoke export.py with EXPORTS_DIR redirected into tmp_path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("scad_export_script", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.EXPORTS_DIR = tmp_path / "exports"

    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        rc = mod.main(["--model", str(model), *extra])
        out_text = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    try:
        payload = json.loads(out_text)
    except json.JSONDecodeError:
        pytest.fail(f"non-JSON stdout: {out_text!r}")
    return rc, payload


def test_T1_simple_box_exports_ok(tmp_path: Path) -> None:
    model = _write(tmp_path, "box.scad", """
        cube([60, 40, 7], center = true);
    """)
    rc, out = _run(model, tmp_path)
    assert rc == 0, f"rc={rc} payload={out}"
    assert out["verdict"] == "export_ok"
    assert out["is_watertight"] is True
    assert out["triangle_count"] > 0
    lo, hi = out["bbox_mm"]
    assert abs((hi[0] - lo[0]) - 60) < 0.5
    assert abs((hi[1] - lo[1]) - 40) < 0.5
    assert abs((hi[2] - lo[2]) - 7) < 0.5
    stl = tmp_path / "exports" / "box.stl"
    assert stl.exists() and stl.stat().st_size > 0


def test_T2_non_manifold_fails(tmp_path: Path) -> None:
    """Open polyhedron — 4 vertices, 3 faces (missing 4th). trimesh's
    watertight check fails on the 3 unpaired edges."""
    model = _write(tmp_path, "open.scad", """
        polyhedron(
            points = [[0,0,0],[10,0,0],[5,8,0],[5,4,8]],
            faces  = [[0,2,1],[0,1,3],[1,2,3]],
            convexity = 2
        );
    """)
    rc, out = _run(model, tmp_path)
    assert rc != 0
    assert out["verdict"] == "not_watertight"
    assert "watertight" in out["error"].lower()


def test_T3_missing_model_fails(tmp_path: Path) -> None:
    rc, out = _run(tmp_path / "nope.scad", tmp_path)
    assert rc != 0
    assert out["verdict"] == "export_failed"
    assert "not found" in out["error"].lower()


def test_T4_parametric_override(tmp_path: Path) -> None:
    """-D forwarded to openscad changes the geometry."""
    model = _write(tmp_path, "plate.scad", """
        plate_t = 5;
        translate([-30, -20, 0]) cube([60, 40, plate_t]);
    """)
    rc_default, out_default = _run(model, tmp_path, "--name", "default")
    rc_thick, out_thick = _run(model, tmp_path, "--name", "thick", "-D", "plate_t=12")
    assert rc_default == 0 and rc_thick == 0
    _, hi_d = out_default["bbox_mm"]
    _, hi_t = out_thick["bbox_mm"]
    assert abs(hi_d[2] - 5) < 0.5, f"default z ≈5, got {hi_d[2]}"
    assert abs(hi_t[2] - 12) < 0.5, f"override z ≈12, got {hi_t[2]}"
