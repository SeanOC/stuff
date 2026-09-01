"""Tests for the build123d thumbnail mirror in scripts/render-all.py (pst-dsiq).

Only the pure helpers are exercised — no openscad runs. The mirror copies
each manifest model's committed review PNG into renders/<stem>/iso.png so
/api/thumbnail serves BD cards through the same path as SCAD models.

CI runs the top-level scripts/ pytest suite (see ci.yml "Scripts + invariant
core unit tests"); run locally with `python3 -m pytest scripts/`.
"""

from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "render-all.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scad_render_all", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _write_manifest(root: Path, slugs: list[str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({
        "schemaVersion": 1,
        "models": [{"slug": s} for s in slugs],
    }))
    return manifest


def test_bd_manifest_stems_maps_dashes_to_underscores(tmp_path, monkeypatch):
    mod = _load_module()
    root = tmp_path / "repo"
    manifest = _write_manifest(root / "build123d", ["holder-spray-can", "holder-bottle-500ml"])
    monkeypatch.setattr(mod, "BD_MANIFEST", manifest)
    assert mod.bd_manifest_stems() == {"holder_spray_can", "holder_bottle_500ml"}


def test_bd_manifest_stems_degrades_on_missing_or_bad_manifest(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setattr(mod, "BD_MANIFEST", tmp_path / "nope" / "manifest.json")
    assert mod.bd_manifest_stems() == set()

    manifest = tmp_path / "manifest.json"
    manifest.write_text("not json {")
    monkeypatch.setattr(mod, "BD_MANIFEST", manifest)
    assert mod.bd_manifest_stems() == set()
    assert "warning" in capsys.readouterr().err


def test_mirror_copies_review_png_to_iso_and_reports_missing(tmp_path, monkeypatch):
    mod = _load_module()
    root = tmp_path / "repo"
    (root / "models").mkdir(parents=True)
    renders = root / "renders"
    docs = root / "build123d" / "docs" / "renders"
    docs.mkdir(parents=True)
    (docs / "holder_spray_can.png").write_bytes(b"png-spray")
    # holder_bottle_500ml has no review PNG on purpose.
    monkeypatch.setattr(mod, "REPO_ROOT", root)
    monkeypatch.setattr(mod, "MODELS_DIR", root / "models")
    monkeypatch.setattr(mod, "RENDERS_DIR", renders)
    monkeypatch.setattr(mod, "BD_DOCS_RENDERS", docs)

    missing = mod._mirror_bd_thumbnails({"holder_spray_can", "holder_bottle_500ml"})

    assert missing == ["holder_bottle_500ml"]
    assert (renders / "holder_spray_can" / "iso.png").read_bytes() == b"png-spray"
    assert not (renders / "holder_bottle_500ml").exists()


def test_mirror_yields_when_stem_is_also_a_scad_model(tmp_path, monkeypatch):
    mod = _load_module()
    root = tmp_path / "repo"
    models = root / "models"
    models.mkdir(parents=True)
    (models / "holder_spray_can.scad").write_text("echo();\n")
    renders = root / "renders"
    docs = root / "build123d" / "docs" / "renders"
    docs.mkdir(parents=True)
    (docs / "holder_spray_can.png").write_bytes(b"png")
    monkeypatch.setattr(mod, "MODELS_DIR", models)
    monkeypatch.setattr(mod, "RENDERS_DIR", renders)
    monkeypatch.setattr(mod, "BD_DOCS_RENDERS", docs)

    missing = mod._mirror_bd_thumbnails({"holder_spray_can"})

    # Neither missing nor mirrored: the SCAD set owns the stem.
    assert missing == []
    assert not (renders / "holder_spray_can").exists()
