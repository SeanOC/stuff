"""Tests for scad-lib/scripts/lib.py.

`list` tests use the real libs/README.md. `add` tests create a local
bare git repo to clone from — no network required.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3].parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "scad-lib" / "scripts" / "lib.py"


def _load_mod():
    import importlib.util
    spec = importlib.util.spec_from_file_location("scad_lib_script", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(mod, *args: str) -> tuple[int, dict]:
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        rc = mod.main(list(args))
        out_text = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    return rc, json.loads(out_text)


def _make_local_repo(tmp: Path) -> Path:
    """Create a tiny git repo in tmp/ that can be `git clone`d."""
    src = tmp / "src_repo"
    src.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(src)], check=True)
    (src / "thing.scad").write_text("module thing() { cube([1,1,1]); }\n")
    subprocess.run(["git", "-C", str(src), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(src), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init"],
        check=True,
    )
    return src


def test_T1_list_shows_vendored_libs() -> None:
    """`list` against the real libs/README.md finds the expected names."""
    mod = _load_mod()
    rc, out = _run(mod, "list")
    assert rc == 0
    assert out["verdict"] == "listed_ok"
    names = {lib["name"] for lib in out["libs"]}
    # After U3, the repo has at minimum NopSCADlib, threads-scad, MCAD.
    for expected in ("NopSCADlib", "threads-scad", "MCAD"):
        assert expected in names, f"{expected} missing from {names}"
    # Each lib should have at least one use<> example.
    for lib in out["libs"]:
        if lib["name"] in ("NopSCADlib", "threads-scad", "MCAD"):
            assert lib["use_examples"], f"{lib['name']} has no use examples"


def test_T2_add_clones_and_stubs(tmp_path: Path) -> None:
    """`add` clones a local repo and appends a stub entry."""
    mod = _load_mod()
    mod.LIBS_DIR = tmp_path / "libs"
    mod.README = mod.LIBS_DIR / "README.md"
    mod.LIBS_DIR.mkdir()
    mod.README.write_text("# Vendored OpenSCAD Libraries\n\nTop prose.\n")

    src = _make_local_repo(tmp_path)
    rc, out = _run(mod, "add", "--name", "test-lib", "--url", str(src))
    assert rc == 0, f"rc={rc} payload={out}"
    assert out["verdict"] == "added_ok"
    assert out["commit"], "missing commit sha"
    assert (mod.LIBS_DIR / "test-lib" / "thing.scad").exists()

    readme_text = mod.README.read_text()
    assert "## test-lib" in readme_text
    assert f"Commit: `{out['commit']}`" in readme_text
    assert "_TODO — fill in" in readme_text


def test_T3_add_rejects_duplicate(tmp_path: Path) -> None:
    mod = _load_mod()
    mod.LIBS_DIR = tmp_path / "libs"
    mod.README = mod.LIBS_DIR / "README.md"
    mod.LIBS_DIR.mkdir()
    mod.README.write_text("# Vendored OpenSCAD Libraries\n")
    (mod.LIBS_DIR / "dup").mkdir()

    src = _make_local_repo(tmp_path)
    rc, out = _run(mod, "add", "--name", "dup", "--url", str(src))
    assert rc != 0
    assert out["verdict"] == "add_failed"
    assert "already exists" in out["error"]


def test_T4_add_rejects_bad_name(tmp_path: Path) -> None:
    mod = _load_mod()
    mod.LIBS_DIR = tmp_path / "libs"
    mod.README = mod.LIBS_DIR / "README.md"
    mod.LIBS_DIR.mkdir()

    rc, out = _run(mod, "add", "--name", "../evil", "--url", "https://example.invalid/x")
    assert rc != 0
    assert out["verdict"] == "add_failed"
    assert "invalid name" in out["error"]


def test_T5_parse_readme_extracts_examples(tmp_path: Path) -> None:
    mod = _load_mod()
    sample = (
        "# Title\n\n"
        "Preamble.\n\n"
        "## foo — `use <foo/bar.scad>`\n\n"
        "Short summary line.\n\n"
        "- `use <foo/a.scad>;` — thing\n"
        "- `use <foo/b.scad>;` — other\n\n"
        "## bar\n\n"
        "Another summary.\n\n"
        "- `include <bar/std.scad>;` — base\n"
    )
    libs = mod._parse_readme(sample)
    names = [lib["name"] for lib in libs]
    assert names == ["foo", "bar"]
    assert libs[0]["summary"] == "Short summary line."
    assert any("foo/a.scad" in ex for ex in libs[0]["use_examples"])
    assert any("bar/std.scad" in ex for ex in libs[1]["use_examples"])
