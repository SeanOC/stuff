"""Tests for scad-render/scripts/render.py.

Invokes the script as a subprocess so we exercise the CLI surface the
skill contract advertises. Parses stdout as JSON and asserts verdict +
render paths + measurement shape.
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
SCRIPT = REPO_ROOT / ".claude" / "skills" / "scad-render" / "scripts" / "render.py"

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


def _run(model: Path, *extra: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--model", str(model), *extra],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"render.py stdout not JSON. rc={proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc.returncode, payload


def test_T1_motor_mount_rendered_ok(tmp_path: Path) -> None:
    """Render a motor-mount-shaped model with PRINT_ANCHOR_BBOX declared;
    verify all four PNGs land and bore ≈20 mm."""
    model = _write(tmp_path, "motor_mount.scad", """
        $fn = 96;
        PRINT_ANCHOR_BBOX = [60, 40, 5];
        plate_w = 60; plate_d = 40; plate_t = 5;
        bore = 20; boss = 2;
        hole_d = 3.2; hole_dx = 48; hole_dy = 28;
        cb_d = 6; cb_depth = 2;

        difference() {
            union() {
                translate([-plate_w/2, -plate_d/2, 0])
                    cube([plate_w, plate_d, plate_t]);
                cylinder(h = plate_t + boss, d = bore + 6);
            }
            translate([0, 0, -1]) cylinder(h = plate_t + boss + 2, d = bore);
            for (sx = [-1, 1]) for (sy = [-1, 1]) {
                translate([sx * hole_dx/2, sy * hole_dy/2, -1])
                    cylinder(h = plate_t + boss + 2, d = hole_d);
                translate([sx * hole_dx/2, sy * hole_dy/2, plate_t - cb_depth])
                    cylinder(h = cb_depth + 0.1, d = cb_d);
            }
        }
    """)
    rc, out = _run(model, "--name", "t1_motor_mount")
    assert rc == 0, f"expected rc=0, got {rc}. payload={out}"
    assert out["verdict"] == "rendered_ok"
    for view in ("top", "front", "side", "iso"):
        assert view in out["renders"], f"missing render for {view}"
        png = REPO_ROOT / out["renders"][view]
        assert png.exists() and png.stat().st_size > 0, f"empty PNG: {png}"

    m = out["measurements"]
    assert m is not None, "expected measurements for top view"
    holes = [c for c in m["circles_top"] if c["kind"] == "hole"]
    diams = sorted(c["diameter_mm"] for c in holes)
    assert diams, "no holes detected"
    assert 19.0 <= diams[-1] <= 21.0, f"bore ≈20 mm, got {diams[-1]}"


def test_T2_parametric_override_changes_render(tmp_path: Path) -> None:
    """-D plate_t=8 should change what actually gets rendered. We verify
    the override reached openscad by rendering twice (default vs override)
    and confirming the top-view PNGs differ in byte content."""
    model = _write(tmp_path, "plate.scad", """
        PRINT_ANCHOR_BBOX = [60, 40, plate_t];
        plate_t = 5;
        translate([-30, -20, 0]) cube([60, 40, plate_t]);
    """)
    rc1, out1 = _run(model, "--name", "t2_default", "--angles", "top,front")
    rc2, out2 = _run(model, "--name", "t2_thick", "--angles", "top,front", "-D", "plate_t=8")
    assert rc1 == 0 and rc2 == 0
    assert out1["verdict"] == "rendered_ok"
    assert out2["verdict"] == "rendered_ok"

    front_default = (REPO_ROOT / out1["renders"]["front"]).read_bytes()
    front_thick = (REPO_ROOT / out2["renders"]["front"]).read_bytes()
    assert front_default != front_thick, (
        "front view identical — -D plate_t=8 did not reach openscad"
    )


def test_T3_unresolved_use_fails(tmp_path: Path) -> None:
    """A model referencing a non-existent library must surface as
    render_failed with a non-zero exit code."""
    model = _write(tmp_path, "broken.scad", """
        use <definitely/does_not_exist.scad>;
        PRINT_ANCHOR_BBOX = [10, 10, 1];
        cube([10, 10, 1]);
    """)
    rc, out = _run(model, "--name", "t3_broken")
    assert rc != 0, f"expected non-zero exit for unresolved use<>, got {rc}"
    assert out["verdict"] == "render_failed"
    assert out["warnings"], "expected populated warnings on failure"


def test_T4_missing_anchor_warns_but_renders(tmp_path: Path) -> None:
    """No PRINT_ANCHOR_BBOX + no --known-bbox-mm → PNGs still produced,
    measurements skipped with a warning. Verdict stays rendered_ok."""
    model = _write(tmp_path, "no_anchor.scad", """
        cube([10, 10, 2]);
    """)
    rc, out = _run(model, "--name", "t4_no_anchor", "--angles", "top")
    assert rc == 0
    assert out["verdict"] == "rendered_ok"
    assert out["measurements"] is None
    assert any("PRINT_ANCHOR_BBOX" in w for w in out["warnings"]), (
        f"expected PRINT_ANCHOR_BBOX warning, got {out['warnings']}"
    )


def test_T5_missing_model_fails(tmp_path: Path) -> None:
    rc, out = _run(tmp_path / "nope.scad")
    assert rc != 0
    assert out["verdict"] == "render_failed"
    assert "not found" in out["error"].lower()
