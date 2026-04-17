"""Tests for scad-new/scripts/new.py.

Exercises the CLI surface (write + delegate-to-render). We redirect
MODELS_DIR to a tmp path so test runs don't litter the real models/ dir.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3].parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "scad-new" / "scripts" / "new.py"

HAVE_OPENSCAD = shutil.which("openscad") is not None
HAVE_XVFB = shutil.which("xvfb-run") is not None

BOX_BODY = """
PRINT_ANCHOR_BBOX = [20, 20, 10];
cube([20, 20, 10], center = true);
""".lstrip()


def _run(
    tmp_path: Path,
    *args: str,
    stdin: str | None = None,
) -> tuple[int, dict]:
    """Run new.py with MODELS_DIR redirected to tmp_path/models."""
    env_patch = (
        f"import sys; from pathlib import Path; "
        f"import importlib.util as u; "
        f"spec = u.spec_from_file_location('new', r'{SCRIPT}'); "
        f"mod = u.module_from_spec(spec); "
        f"mod.MODELS_DIR = Path(r'{tmp_path}') / 'models'; "
        f"spec.loader.exec_module.__self__ = spec.loader; "
    )
    # Simpler: monkeypatch via a wrapper script. But subprocess + env is
    # cleaner — pass the override through an env var the script could read.
    # Since new.py uses a module-level constant, run it in-process instead.
    import importlib.util
    spec = importlib.util.spec_from_file_location("scad_new_script", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.MODELS_DIR = tmp_path / "models"

    old_stdin = sys.stdin
    old_stdout = sys.stdout
    import io
    if stdin is not None:
        sys.stdin = io.StringIO(stdin)
    sys.stdout = io.StringIO()
    try:
        rc = mod.main(list(args))
        out_text = sys.stdout.getvalue()
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout
    try:
        payload = json.loads(out_text)
    except json.JSONDecodeError:
        pytest.fail(f"non-JSON stdout: {out_text!r}")
    return rc, payload


def test_T1_writes_file_and_skips_render(tmp_path: Path) -> None:
    """--no-render: verify file lands at models/<name>.scad without
    shelling to openscad (keeps test fast + independent of openscad)."""
    rc, out = _run(tmp_path, "--name", "test_box", "--no-render", stdin=BOX_BODY)
    assert rc == 0
    assert out["verdict"] == "authored_ok"
    assert out["render"] is None
    model_path = tmp_path / "models" / "test_box.scad"
    assert model_path.exists()
    assert "PRINT_ANCHOR_BBOX" in model_path.read_text()
    assert not out["versioned"]


def test_T2_versioned_increments(tmp_path: Path) -> None:
    for expected in ("test_box_001.scad", "test_box_002.scad", "test_box_003.scad"):
        rc, out = _run(
            tmp_path, "--name", "test_box", "--versioned", "--no-render",
            stdin=BOX_BODY,
        )
        assert rc == 0
        assert out["verdict"] == "authored_ok"
        assert out["versioned"] is True
        assert out["model"].endswith(expected), f"expected {expected}, got {out['model']}"
        assert (tmp_path / "models" / expected).exists()


def test_T3_edit_in_place_overwrites(tmp_path: Path) -> None:
    body_a = "PRINT_ANCHOR_BBOX = [10, 10, 1];\ncube([10, 10, 1]);\n"
    body_b = "PRINT_ANCHOR_BBOX = [20, 20, 2];\ncube([20, 20, 2]);\n"
    rc, _ = _run(tmp_path, "--name", "thing", "--no-render", stdin=body_a)
    assert rc == 0
    rc, _ = _run(tmp_path, "--name", "thing", "--no-render", stdin=body_b)
    assert rc == 0
    content = (tmp_path / "models" / "thing.scad").read_text()
    assert "20, 20, 2" in content
    assert "10, 10, 1" not in content
    # Exactly one file — no implicit versioning.
    scads = list((tmp_path / "models").glob("thing*.scad"))
    assert len(scads) == 1, f"expected 1 file, got {scads}"


def test_T4_empty_body_fails(tmp_path: Path) -> None:
    rc, out = _run(tmp_path, "--name", "empty", "--no-render", stdin="   \n\n")
    assert rc != 0
    assert out["verdict"] == "authoring_failed"


@pytest.mark.skipif(
    not (HAVE_OPENSCAD and HAVE_XVFB),
    reason="openscad + xvfb-run required for render path",
)
def test_T5_renders_end_to_end(tmp_path: Path) -> None:
    """With render enabled, the combined JSON carries the render payload."""
    rc, out = _run(
        tmp_path, "--name", "e2e_box", "--angles", "top",
        stdin=BOX_BODY,
    )
    assert rc == 0, f"rc={rc} payload={out}"
    assert out["verdict"] == "authored_ok"
    assert out["render"] is not None
    assert out["render"]["verdict"] == "rendered_ok"
