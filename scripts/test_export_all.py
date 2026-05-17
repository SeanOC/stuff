"""Tests for scripts/export-all.py variant planning.

Only the pure planning function is exercised here — no openscad runs.
The end-to-end export path is covered by .claude/skills/scad-export/_tests/.
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "export-all.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scad_export_all", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _write_model(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(body).lstrip())
    return path


def test_no_filename_flag_yields_single_default_variant(tmp_path: Path):
    mod = _load_module()
    model = _write_model(
        tmp_path,
        "plain.scad",
        """
        // === User-tunable parameters ===
        w = 10;  // @param number min=1 max=20
        // === Internals ===
        cube([w, w, w]);
        """,
    )
    variants = mod.plan_variants(model)
    assert variants == [("plain", {})]


def test_single_filename_param_expands_one_stl_per_choice(tmp_path: Path):
    mod = _load_module()
    model = _write_model(
        tmp_path,
        "valve.scad",
        """
        // === User-tunable parameters ===
        part = "assembly";  // @param enum choices=assembly|base|cap_left|cap_right filename
        // === Internals ===
        cube([1,1,1]);
        """,
    )
    variants = mod.plan_variants(model)
    assert variants == [
        ("valve-assembly", {"part": "assembly"}),
        ("valve-base", {"part": "base"}),
        ("valve-cap_left", {"part": "cap_left"}),
        ("valve-cap_right", {"part": "cap_right"}),
    ]


def test_multiple_filename_params_use_keyed_suffix(tmp_path: Path):
    mod = _load_module()
    model = _write_model(
        tmp_path,
        "grid.scad",
        """
        // === User-tunable parameters ===
        side = "left"; // @param enum choices=left|right filename
        mode = "thin"; // @param enum choices=thin|thick filename
        // === Internals ===
        cube([1,1,1]);
        """,
    )
    variants = mod.plan_variants(model)
    # Cartesian product, with `<param>=<value>` joined by `-` so each
    # token in the filename is unambiguous.
    assert variants == [
        ("grid-side=left-mode=thin", {"side": "left", "mode": "thin"}),
        ("grid-side=left-mode=thick", {"side": "left", "mode": "thick"}),
        ("grid-side=right-mode=thin", {"side": "right", "mode": "thin"}),
        ("grid-side=right-mode=thick", {"side": "right", "mode": "thick"}),
    ]
