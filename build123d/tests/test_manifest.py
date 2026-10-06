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
import subprocess
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


def test_manifest_order_independent_of_import_order():
    """A fresh interpreter imports holders in reverse of all_models()."""
    result = subprocess.run(
        [sys.executable, "-c", "\n".join([
            # Also exercise revisions before spool_cradle was registered.
            "from importlib.util import find_spec",
            "if find_spec('holders.spool_cradle'): from holders import spool_cradle",
            "from holders import cylindrical, smoke, cup_lid",
            "from scripts.manifest import manifest_text",
            "print(manifest_text(), end='')",
        ])],
        cwd=MANIFEST_PATH.parent,
        capture_output=True,
        check=True,
    )
    assert result.stdout == MANIFEST_PATH.read_bytes()


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


def test_param_filename_flag_emitted_only_when_set():
    """parse.ts ParamBase.filename is an optional bare flag: emitted as true
    (last, after choices) when set, absent otherwise — so the manifest diff
    for flagging a param is exactly one key."""
    assert Param(name="m", kind="enum", default="a", choices=("a",)).filename is False
    flagged = Param(name="m", kind="enum", default="a", choices=("a", "b"), filename=True)
    assert list(param_to_json(flagged)) == ["name", "kind", "default", "choices", "filename"]
    assert param_to_json(flagged)["filename"] is True
    assert "filename" not in param_to_json(Param(name="x", kind="number", default=1.0))
    num = Param(name="x", kind="number", default=1.0, min=0.0, filename=True)
    assert param_to_json(num) == {"name": "x", "kind": "number", "default": 1.0,
                                  "min": 0.0, "filename": True}


def test_validator_accepts_filename_on_every_kind():
    doc = _valid_doc()
    for kind, extra in (("number", {}), ("integer", {}), ("boolean", {}),
                        ("string", {}), ("enum", {"choices": ["a"]})):
        d = _mutate(doc)
        default = {"number": 1.0, "integer": 1, "boolean": True,
                   "string": "s", "enum": "a"}[kind]
        d["models"][0]["params"].append(
            {"name": f"f_{kind}", "kind": kind, "default": default, **extra,
             "filename": True})
        assert validate_manifest(d) == [], kind


def test_mount_selection_params_are_filename_flagged():
    """Mount selections and shelf dimensions/style distinguish downloads."""
    flagged = [(s.name, p.name) for s in all_models() for p in s.params if p.filename]
    assert set(flagged) == {
        ("holder_spool_cradle", "mount_style"),
        ("openconnect_gridfinity_shelf", "baseplate_style"),
        ("openconnect_gridfinity_shelf", "gridfinity_width_grids"),
        ("openconnect_gridfinity_shelf", "gridfinity_depth_grids"),
        ("littletikes_dream_machine_cartridge_holder", "mount_type"),
    }
    models = {m["slug"]: m for m in build_manifest()["models"]}
    for name, param in flagged:
        by_name = {p["name"]: p for p in models[name.replace("_", "-")]["params"]}
        assert by_name[param]["filename"] is True


def test_shelf_clearance_description_reaches_catalog():
    doc = build_manifest()
    assert validate_manifest(doc) == []
    shelf = next(m for m in doc['models'] if m['slug'] == 'openconnect-gridfinity-shelf')
    clearance = next(p for p in shelf['params'] if p['name'] == 'gridfinity_socket_clearance')
    assert 'at least 3 perimeters or keep the default 0' in clearance['description']
    assert (clearance['min'], clearance['max']) == (0, .2)
    clearance['description'] = 42
    assert any('description must be a non-empty string' in e for e in validate_manifest(doc))


def test_preset_serializes_like_parse_ts():
    pr = Preset(id="spray_can", label="Spray can (d=66, h=60)",
                values={"d": 66.0, "h": 60.0})
    assert preset_to_json(pr) == {
        "id": "spray_can",
        "label": "Spray can (d=66, h=60)",
        "values": {"d": 66.0, "h": 60.0},
    }


def test_default_view_is_a_trailing_preset_key_only_when_set():
    pr = Preset(id="p", label="P", values={}, default_view="bottom")
    assert list(preset_to_json(pr)) == ["id", "label", "values", "defaultView"]
    assert preset_to_json(pr)["defaultView"] == "bottom"
    assert "defaultView" not in preset_to_json(Preset(id="p", label="P", values={}))


def test_only_the_inlaid_label_card_preset_carries_a_view_hint():
    """pst-5b83s AC (d): the face-down inlaid card opens on its text face."""
    hinted = [(m["slug"], p["id"], p["defaultView"])
              for m in build_manifest()["models"] for p in m["presets"] if "defaultView" in p]
    assert hinted == [("holder-label-card", "inlaid", "bottom")]


def test_validator_rejects_unknown_default_view():
    doc = _mutate(_valid_doc())
    doc["models"][0]["presets"][0]["defaultView"] = "sideways"
    assert any("defaultView must be one of" in e for e in validate_manifest(doc))


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
    doc["models"][0]["params"][0]["unknown_help_field"] = "not an app field"
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


def test_registry_rejects_unknown_default_view():
    spec = ModelSpec(
        name="tmp_bad_default_view",
        build=_bare_build,
        description="x",
        params=(Param(name="a", kind="number", default=1.0),),
        presets=(Preset(id="p", label="p", values={}, default_view="top"),),
        category_id="toys",
    )
    with pytest.raises(ValueError, match="default_view"):
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
        # Mount tunables (§5) — defaults reproduce today's shipped geometry.
        "slot_count": 1, "slot_travel": 28.0, "snap_notches": True,
        "plate_margin": 3.0,
    }


def test_openconnect_plate_app_contract():
    model = next(m for m in build_manifest()['models'] if m['slug'] == 'openconnect-plate')
    assert model['categoryId'] == 'multiboard'
    assert [p['id'] for p in model['presets']] == ['default', 'one-tile', 'negslot']
    params = {p['name']: p for p in model['params']}
    assert params['slot_type']['choices'] == ['slot', 'negslot']
    assert params['extra_thickness']['default'] == 2.4
    assert params['extra_thickness']['min'] == 0.5
