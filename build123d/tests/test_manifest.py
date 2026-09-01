"""Manifest emitter + strict schema validator (bead pst-pa1o).

Registry-driven: every app-listed (non-smoke) model must produce a valid
manifest entry. The validator is strict — unknown/missing fields,
duplicate slugs/param names, unknown preset param references, and
enum/default mismatches all fail (AC: 'reject unknown/missing fields,
duplicate model slugs, duplicate param names, params referenced by
unknown presets, and mismatched enum/default values').

Shape pinning: the emitter must mirror lib/scad-params/parse.ts EXACTLY
(Param base fields name/label?/group?/unit?, kind-specific fields,
EnumParam.choices, Preset {id, label, values}) — the app ingests the
manifest verbatim.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holders.registry import (  # noqa: E402
    CATEGORY_IDS,
    ModelSpec,
    Param,
    Preset,
    all_models,
    register,
)
from scripts.manifest import (  # noqa: E402
    MANIFEST_PATH,
    build_manifest,
    manifest_text,
    param_to_json,
    preset_to_json,
    validate_manifest,
)


# --------------------------------------------------------------------------
# Registry-driven schema validation
# --------------------------------------------------------------------------

def test_manifest_is_schema_valid():
    doc = build_manifest()
    errors = validate_manifest(doc)
    assert errors == [], "manifest failed strict schema validation:\n" + "\n".join(errors)


def test_manifest_covers_every_app_listed_model_and_no_smoke():
    doc = build_manifest()
    specs = all_models()
    expected = {s.slug for s in specs if not s.is_smoke}
    got = {m["slug"] for m in doc["models"]}
    assert got == expected, f"manifest models {sorted(got)} != app-listed {sorted(expected)}"
    assert doc["schemaVersion"] == 1
    for model in doc["models"]:
        assert model["engine"] == "build123d"
        assert model["categoryId"] in CATEGORY_IDS
        assert model["presets"], f"{model['slug']}: app-listed models need presets"


def test_manifest_file_is_fresh():
    """The committed manifest.json must match the deterministic emitter
    output (CI re-runs this as regenerate + git diff --exit-code)."""
    assert MANIFEST_PATH.exists(), "build123d/manifest.json not committed"
    assert MANIFEST_PATH.read_text() == manifest_text()


def test_emitter_is_deterministic():
    assert manifest_text() == manifest_text()
    # Round-trip through JSON must be stable (no float/int churn).
    assert json.loads(json.dumps(build_manifest())) == build_manifest()


# --------------------------------------------------------------------------
# parse.ts shape pinning (mirror the app's types EXACTLY)
# --------------------------------------------------------------------------

def test_param_serializes_like_parse_ts():
    p = Param(
        name="d", kind="number", default=66.0, min=30.0, max=120.0, step=1.0,
        label="Cylinder diameter", group="geometry", unit="mm",
    )
    assert param_to_json(p) == {
        "name": "d",
        "label": "Cylinder diameter",
        "group": "geometry",
        "unit": "mm",
        "kind": "number",
        "default": 66.0,
        "min": 30.0,
        "max": 120.0,
        "step": 1.0,
    }


def test_param_optional_fields_are_omitted():
    """parse.ts emits only set keys — a bare param has no label/group/unit,
    a number param has no min/max/step unless declared."""
    assert param_to_json(Param(name="x", kind="number", default=1.0)) == {
        "name": "x", "kind": "number", "default": 1.0,
    }
    assert param_to_json(Param(name="on", kind="boolean", default=True)) == {
        "name": "on", "kind": "boolean", "default": True,
    }
    e = param_to_json(Param(name="m", kind="enum", default="a", choices=("a", "b")))
    assert e == {"name": "m", "kind": "enum", "default": "a", "choices": ["a", "b"]}
    assert "options" not in e  # the app field is `choices`, never `options`


def test_preset_serializes_like_parse_ts():
    pr = Preset(id="spray_can", label="Spray can (d=66, h=60)",
                values={"d": 66.0, "h": 60.0})
    assert preset_to_json(pr) == {
        "id": "spray_can",
        "label": "Spray can (d=66, h=60)",
        "values": {"d": 66.0, "h": 60.0},
    }


def test_shipped_holder_params_match_registry():
    """The shipped presets must round-trip through the emitter exactly."""
    spec = next(s for s in all_models() if s.name == "holder_spray_can")
    doc = build_manifest()
    model = next(m for m in doc["models"] if m["slug"] == "holder-spray-can")
    by_id = {p["id"]: p for p in model["presets"]}
    assert by_id["spray_can"] == {
        "id": "spray_can",
        "label": "Spray can (d=66, h=60)",
        "values": {"d": 66.0, "h": 60.0},
    }
    by_name = {p["name"]: p for p in model["params"]}
    assert by_name["d"]["kind"] == "number"
    assert "choices" not in by_name["d"]  # number params never carry choices


# --------------------------------------------------------------------------
# Strict validator negatives
# --------------------------------------------------------------------------

def _valid_doc():
    return build_manifest()


def _mutate(doc, model_idx=0):
    import copy
    return copy.deepcopy(doc)


def test_validator_rejects_unknown_model_field():
    doc = _mutate(_valid_doc())
    doc["models"][0]["category"] = "multiboard"  # app field is categoryId
    errors = validate_manifest(doc)
    assert any("field set/order" in e for e in errors)


def test_validator_rejects_missing_field():
    doc = _mutate(_valid_doc())
    del doc["models"][0]["blurb"]
    errors = validate_manifest(doc)
    assert any("field set/order" in e for e in errors)


def test_validator_rejects_unknown_param_field():
    doc = _mutate(_valid_doc())
    doc["models"][0]["params"][0]["description"] = "not an app field"
    errors = validate_manifest(doc)
    assert any("unknown param fields" in e for e in errors)


def test_validator_rejects_enum_options_instead_of_choices():
    doc = _mutate(_valid_doc())
    # Synthetic enum param with the wrong field name.
    doc["models"][0]["params"].append(
        {"name": "m", "kind": "enum", "default": "a", "options": ["a", "b"]}
    )
    errors = validate_manifest(doc)
    assert any("unknown param fields" in e for e in errors)


def test_validator_rejects_duplicate_slugs():
    doc = _mutate(_valid_doc())
    model = doc["models"][0]
    doc["models"].append(dict(model, slug=model["slug"]))
    errors = validate_manifest(doc)
    assert any("duplicate slug" in e for e in errors)


def test_validator_rejects_duplicate_param_names():
    doc = _mutate(_valid_doc())
    params = doc["models"][0]["params"]
    doc["models"][0]["params"] = params + [dict(params[0])]
    errors = validate_manifest(doc)
    assert any("duplicate param name" in e for e in errors)


def test_validator_rejects_preset_referencing_unknown_param():
    doc = _mutate(_valid_doc())
    doc["models"][0]["presets"][0]["values"]["nope"] = 1.0
    errors = validate_manifest(doc)
    assert any("unknown param" in e for e in errors)


def test_validator_rejects_enum_default_not_in_choices():
    doc = _mutate(_valid_doc())
    doc["models"][0]["params"].append(
        {"name": "m", "kind": "enum", "default": "z", "choices": ["a", "b"]}
    )
    errors = validate_manifest(doc)
    assert any("default not in choices" in e for e in errors)


def test_validator_rejects_preset_enum_value_not_in_choices():
    doc = _mutate(_valid_doc())
    doc["models"][0]["params"].append(
        {"name": "m", "kind": "enum", "default": "a", "choices": ["a", "b"]}
    )
    doc["models"][0]["presets"][0]["values"]["m"] = "nope"
    errors = validate_manifest(doc)
    assert any("not in choices" in e for e in errors)


def test_validator_rejects_bad_category_id():
    doc = _mutate(_valid_doc())
    doc["models"][0]["categoryId"] = "shelves"
    errors = validate_manifest(doc)
    assert any("categoryId" in e for e in errors)


def test_validator_rejects_bad_schema_version():
    doc = _mutate(_valid_doc())
    doc["schemaVersion"] = 2
    errors = validate_manifest(doc)
    assert any("schemaVersion" in e for e in errors)


def test_validator_rejects_number_default_on_integer_kind():
    doc = _mutate(_valid_doc())
    doc["models"][0]["params"].append(
        {"name": "n", "kind": "integer", "default": 1.5}
    )
    errors = validate_manifest(doc)
    assert any("integer" in e and "default" in e for e in errors)


# --------------------------------------------------------------------------
# Registry-level fail-fast (registration validates before anything else)
# --------------------------------------------------------------------------

def _bare_build(values):
    from build123d import Box

    return Box(1, 1, 1)


def test_registry_rejects_preset_with_unknown_param():
    spec = ModelSpec(
        name="tmp_bad_preset_ref",
        build=_bare_build,
        description="x",
        params=(Param(name="a", kind="number", default=1.0),),
        presets=(Preset(id="p", label="p", values={"b": 1.0}),),
        category_id="toys",
    )
    with pytest.raises(ValueError, match="unknown param"):
        register(spec)


def test_registry_rejects_preset_value_outside_choices():
    spec = ModelSpec(
        name="tmp_bad_enum_value",
        build=_bare_build,
        description="x",
        params=(Param(name="m", kind="enum", default="a", choices=("a", "b")),),
        presets=(Preset(id="p", label="p", values={"m": "z"}),),
        category_id="toys",
    )
    with pytest.raises(ValueError, match="not in choices"):
        register(spec)


def test_resolve_values_rejects_unknown_and_out_of_range():
    spec = next(s for s in all_models() if s.name == "holder_spray_can")
    with pytest.raises(ValueError, match="unknown param"):
        spec.resolve_values({"nope": 1.0})
    with pytest.raises(ValueError, match="min"):
        spec.resolve_values({"d": 10.0})
    with pytest.raises(ValueError, match="max"):
        spec.resolve_values({"h": 999.0})
    assert spec.resolve_values({"d": 40.0})["d"] == 40.0
    assert spec.resolve_values() == {
        "d": 66.0, "h": 60.0, "wall": 2.4, "opening_deg": 90.0,
        "floor_thickness": 4.8,
    }
