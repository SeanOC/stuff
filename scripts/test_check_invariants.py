"""Regression checks for selecting the current default export artifact."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def checker(tmp_path, monkeypatch):
    script = Path(__file__).with_name("check-invariants.py")
    spec = importlib.util.spec_from_file_location("check_invariants", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "EXPORTS_DIR", tmp_path)
    return mod


def test_filename_grid_ignores_stale_unfanned_export(checker, tmp_path):
    source = (Path(__file__).resolve().parent.parent / "models" /
              "disney_ear_hanger.scad").read_text()
    legacy = tmp_path / "disney_ear_hanger.stl"
    legacy.touch()
    current = tmp_path / "disney_ear_hanger-tab.stl"
    current.touch()

    assert checker._resolve_stl("disney_ear_hanger", source) == current

    # Missing current exports must be reported missing, not silently replaced
    # by obsolete geometry from before filename-grid opt-in.
    current.unlink()
    assert checker._resolve_stl("disney_ear_hanger", source) == current


def test_non_grid_model_uses_unfanned_export(checker, tmp_path):
    expected = tmp_path / "plain.stl"
    assert checker._resolve_stl("plain", "cube([1, 1, 1]);") == expected
    expected.touch()
    assert checker._resolve_stl("plain", "cube([1, 1, 1]);") == expected
