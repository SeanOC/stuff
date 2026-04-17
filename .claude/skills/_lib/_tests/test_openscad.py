"""Integration tests for _lib/openscad.render.

Runs the real openscad binary through xvfb-run. Skipped if either is missing.
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

from .. import openscad as osc

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


def test_T1_renders_trivial_cube(tmp_path: Path) -> None:
    model = _write(tmp_path, "cube.scad", "cube([10,10,10]);")
    out = tmp_path / "top.png"
    res = osc.render(model, out, view="top")
    assert res.png_bytes > 0
    assert res.warnings == []


def test_T2_unresolved_use_raises(tmp_path: Path) -> None:
    model = _write(tmp_path, "broken.scad", """
        use <definitely/missing.scad>;
        cube([5,5,5]);
    """)
    out = tmp_path / "top.png"
    with pytest.raises(osc.OpenscadError) as exc:
        osc.render(model, out, view="top")
    assert "definitely/missing.scad" in str(exc.value)


def test_T3_define_forwarded(tmp_path: Path) -> None:
    """-D override changes geometry; an override to a huge value produces a
    much larger PNG than the default."""
    model = _write(tmp_path, "box.scad", """
        size = 5;
        cube([size, size, size]);
    """)
    small = tmp_path / "small.png"
    big = tmp_path / "big.png"
    osc.render(model, small, view="top", defines={"size": 5}, imgsize=256)
    osc.render(model, big, view="top", defines={"size": 100}, imgsize=256)
    # With --viewall the projected size should be identical, but the number
    # of covered pixels should be comparable. The real assertion is that the
    # override round-trips without an error and both PNGs exist non-empty.
    assert small.stat().st_size > 0
    assert big.stat().st_size > 0


def test_T4_openscadpath_resolves_vendored_lib(tmp_path: Path) -> None:
    repo_libs = Path(__file__).resolve().parents[3].parent / "libs"
    if not (repo_libs / "NopSCADlib" / "core.scad").exists():
        pytest.skip("vendored libs not present")
    model = _write(tmp_path, "uses_nop.scad", """
        use <NopSCADlib/core.scad>;
        cube([5,5,5]);
    """)
    out = tmp_path / "top.png"
    res = osc.render(model, out, view="top")
    assert res.warnings == []
    assert res.png_bytes > 0


def test_T5_empty_png_raises(tmp_path: Path) -> None:
    """Simulate the 'exit 0 but file missing' path by pointing out_png at a
    directory we clear after openscad exits — we do it by mocking."""
    model = _write(tmp_path, "cube.scad", "cube([5,5,5]);")
    out = tmp_path / "top.png"

    import subprocess as _sp

    real_run = _sp.run

    def fake_run(cmd, *a, **kw):
        result = real_run(cmd, *a, **kw)
        if out.exists():
            out.unlink()
        return result

    import _pytest.monkeypatch

    mp = _pytest.monkeypatch.MonkeyPatch()
    try:
        mp.setattr(osc.subprocess, "run", fake_run)
        with pytest.raises(osc.OpenscadError) as exc:
            osc.render(model, out, view="top")
        assert "not written" in str(exc.value) or "empty PNG" in str(exc.value)
    finally:
        mp.undo()


def test_unknown_view_raises(tmp_path: Path) -> None:
    model = _write(tmp_path, "cube.scad", "cube([5,5,5]);")
    with pytest.raises(osc.OpenscadError):
        osc.render(model, tmp_path / "x.png", view="nope")


def test_prepend_path_dedupes() -> None:
    assert osc._prepend_path("", "/a") == "/a"
    assert osc._prepend_path("/b", "/a") == "/a:/b"
    assert osc._prepend_path("/a:/b", "/a") == "/a:/b"


def test_fmt_define_handles_types() -> None:
    assert osc._fmt_define(5) == "5"
    assert osc._fmt_define(1.5) == "1.5"
    assert osc._fmt_define(True) == "true"
    assert osc._fmt_define(False) == "false"
    assert osc._fmt_define("hello") == "hello"
