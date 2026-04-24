"""Tests for the invariants core.

Doesn't drive openscad or trimesh loading — those are exercised in CI
via a live STL check. Here we validate the invariant logic against
mock `ctx` dicts so failures can be pinned deterministically.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.invariants import (
    Failure,
    as_default_params,
    expect_connected_solids,
    parse_anchor_bbox,
    run_builtins,
)


def _stl(is_watertight: bool = True, faces: int = 1000):
    """Minimal stand-in for a trimesh.Trimesh — attrs the built-ins read."""
    return SimpleNamespace(
        is_watertight=is_watertight,
        faces=list(range(faces)),
    )


def _ctx(**overrides):
    base = {
        "stem": "fake",
        "source": "",
        "params": {},
        "stl": _stl(),
        "bbox_mm": (10.0, 10.0, 10.0),
        "anchor_bbox_mm": None,
        "connected_solids": 1,
        "component_sizes": [1000],
    }
    base.update(overrides)
    return base


class TestBuiltinTopology:
    def test_single_component_passes(self):
        assert run_builtins(_ctx(connected_solids=1, component_sizes=[1000])) == []

    def test_multi_body_without_orphans_passes(self):
        # 7-component design (baseplate + 6 cradles) — each is "big
        # enough" to plausibly be a legitimate part, not a scrap.
        ctx = _ctx(connected_solids=7, component_sizes=[7000, 1700, 1700, 1700, 1700, 1700, 1700])
        assert run_builtins(ctx) == []

    def test_tiny_orphan_fails(self):
        # Main body 10000 tris + a 6-tri scrap — typical zero-thickness
        # boolean bug that st-v7k's class of invariants wants to catch.
        ctx = _ctx(connected_solids=2, component_sizes=[10000, 6])
        failures = [f for f in run_builtins(ctx) if f.kind == "topology"]
        assert len(failures) == 1
        assert "orphan" in failures[0].detail

    def test_single_small_component_passes(self):
        # Lone-component parts can legitimately be small (thin bent
        # plate, ~30 tris — st-2ln bent-plate deflector). With nothing
        # else in the STL to "orphan from," the orphan check should
        # skip rather than flag the main body as its own fragment.
        ctx = _ctx(connected_solids=1, component_sizes=[28])
        failures = [f for f in run_builtins(ctx) if f.kind == "topology"]
        assert failures == []


class TestBuiltinWatertight:
    def test_pass(self):
        assert run_builtins(_ctx(stl=_stl(is_watertight=True))) == []

    def test_fail(self):
        failures = run_builtins(_ctx(stl=_stl(is_watertight=False)))
        kinds = {f.kind for f in failures}
        assert "watertight" in kinds


class TestBuiltinTriangleCount:
    def test_pass(self):
        ctx = _ctx(stl=_stl(faces=500_000))
        assert run_builtins(ctx) == []

    def test_fail(self):
        ctx = _ctx(stl=_stl(faces=2_000_000), component_sizes=[2_000_000])
        failures = [f for f in run_builtins(ctx) if f.kind == "triangle_count"]
        assert len(failures) == 1


class TestBuiltinAnchorBbox:
    def test_no_anchor_is_noop(self):
        ctx = _ctx(anchor_bbox_mm=None, bbox_mm=(999, 999, 999))
        assert [f for f in run_builtins(ctx) if f.kind == "anchor_bbox"] == []

    def test_within_tolerance_passes(self):
        ctx = _ctx(anchor_bbox_mm=(100, 50, 20), bbox_mm=(100.5, 50.2, 19.9))
        assert [f for f in run_builtins(ctx) if f.kind == "anchor_bbox"] == []

    def test_drift_fails_per_axis(self):
        ctx = _ctx(anchor_bbox_mm=(100, 50, 20), bbox_mm=(95, 50, 20))
        failures = [f for f in run_builtins(ctx) if f.kind == "anchor_bbox"]
        assert len(failures) == 1
        assert "x-extent" in failures[0].detail


class TestExpectConnectedSolids:
    def test_match(self):
        assert expect_connected_solids(_ctx(connected_solids=7), 7) == []

    def test_mismatch(self):
        failures = expect_connected_solids(_ctx(connected_solids=2), 1)
        assert len(failures) == 1
        assert failures[0].kind == "connected_solids"


class TestAsDefaultParams:
    def test_flattens(self):
        params = {
            "w": {"kind": "number", "default": 10, "min": 0, "max": 20},
            "flag": {"kind": "boolean", "default": True},
        }
        assert as_default_params(params) == {"w": 10, "flag": True}


class TestParseAnchorBbox:
    def test_literal_triple(self):
        src = "// blah\nPRINT_ANCHOR_BBOX = [213.5, 157.5, 253];\nmore;"
        assert parse_anchor_bbox(src) == (213.5, 157.5, 253.0)

    def test_integer_triple(self):
        src = "PRINT_ANCHOR_BBOX = [60, 40, 5];"
        assert parse_anchor_bbox(src) == (60.0, 40.0, 5.0)

    def test_missing(self):
        assert parse_anchor_bbox("no anchor here") is None

    def test_expression_silently_skipped(self):
        # Non-literal values (`x + y`) shouldn't crash — we just return
        # None and the anchor invariant becomes a no-op.
        assert parse_anchor_bbox("PRINT_ANCHOR_BBOX = [a, b, c];") is None


class TestFailureFormat:
    def test_format(self):
        f = Failure("footprint", "base_d=180 > base_w=100")
        assert f.format() == "[footprint] base_d=180 > base_w=100"


class TestPresetInvariant:
    def _params(self):
        return {
            "can_d": {"kind": "number", "default": 46.0, "min": 20, "max": 200},
            "rows": {"kind": "integer", "default": 2},
            "open": {"kind": "boolean", "default": True},
            "shape": {"kind": "enum", "default": "round", "choices": ["round", "square"]},
        }

    def test_ok_preset_produces_no_failures(self):
        src = '// @preset id="default" label="Default" can_d=46 rows=2 open=true shape="round"'
        ctx = _ctx(source=src, params=self._params())
        failures = [f for f in run_builtins(ctx) if f.kind == "preset"]
        assert failures == []

    def test_unknown_param_key_fails(self):
        src = '// @preset id="bad" label="Bad" made_up_param=5'
        failures = [
            f for f in run_builtins(_ctx(source=src, params=self._params()))
            if f.kind == "preset"
        ]
        assert len(failures) == 1
        assert 'unknown param "made_up_param"' in failures[0].detail

    def test_type_mismatch_fails(self):
        src = '// @preset id="bad" label="Bad" can_d=not_a_number'
        failures = [
            f for f in run_builtins(_ctx(source=src, params=self._params()))
            if f.kind == "preset"
        ]
        assert len(failures) == 1
        assert "not numeric" in failures[0].detail

    def test_enum_value_out_of_choices_fails(self):
        src = '// @preset id="hex" label="Hex" shape="hex"'
        failures = [
            f for f in run_builtins(_ctx(source=src, params=self._params()))
            if f.kind == "preset"
        ]
        assert len(failures) == 1
        assert "not in choices" in failures[0].detail

    def test_boolean_non_true_false_fails(self):
        src = '// @preset id="bad" label="Bad" open=maybe'
        failures = [
            f for f in run_builtins(_ctx(source=src, params=self._params()))
            if f.kind == "preset"
        ]
        assert len(failures) == 1
        assert "true/false" in failures[0].detail

    def test_missing_id_fails(self):
        src = '// @preset label="Nameless" can_d=46'
        failures = [
            f for f in run_builtins(_ctx(source=src, params=self._params()))
            if f.kind == "preset"
        ]
        assert len(failures) == 1
        assert "missing id" in failures[0].detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
