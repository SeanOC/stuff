"""Total height must include the actual rounded lip, without 7mm snapping."""

import importlib.util
from pathlib import Path

import pytest

from scripts.invariants.params import parse_params


@pytest.fixture
def bin_context():
    models = Path(__file__).resolve().parent.parent / "models"
    spec = importlib.util.spec_from_file_location(
        "gridfinity_bin_invariants", models / "gridfinity_bin.invariants.py"
    )
    sidecar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sidecar)
    ctx = {
        "params": parse_params((models / "gridfinity_bin.scad").read_text()),
        "bbox_mm": (41.5, 41.5, 24.55),
    }
    return sidecar, ctx


def test_units_default_keeps_its_existing_height(bin_context):
    sidecar, ctx = bin_context
    assert sidecar.check(ctx) == []


@pytest.mark.parametrize("height_mm", [11, 60, 65, 65.5, 68, 70, 120])
def test_total_height_contract(bin_context, height_mm):
    sidecar, ctx = bin_context
    ctx["params"]["height_mode"]["default"] = "total mm"
    ctx["params"]["height_mm"]["default"] = height_mm
    ctx["bbox_mm"] = (41.5, 41.5, height_mm)
    assert sidecar.check(ctx) == []

    # The nominal-lip subtraction misses by ~0.85mm; omitting the lip
    # compensation overshoots by ~3.55mm. Neither may pass the invariant.
    for offset in [-0.85, 3.55]:
        ctx["bbox_mm"] = (41.5, 41.5, height_mm + offset)
        assert [f.kind for f in sidecar.check(ctx)] == ["height"]
