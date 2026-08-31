"""Emit build123d/manifest.json — the app-facing model catalog.

Usage:
    uv run python scripts/manifest.py            # write build123d/manifest.json
    uv run python scripts/manifest.py --check    # exit 1 if stale (CI freshness gate)

The manifest shape mirrors the web app's contracts so the app can ingest
it verbatim:

    {
      "schemaVersion": 1,
      "models": [
        {
          "slug": "holder-spray-can",      # URL-safe, unique (name with '_' -> '-')
          "engine": "build123d",           # engine metadata for the catalog
          "title": "Spray can holder",     # app display title
          "blurb": "...",                  # catalog card blurb
          "categoryId": "multiboard",      # id from lib/models/catalog.ts
          "params": [ ... Param ... ],     # lib/scad-params/parse.ts shapes
          "presets": [ ... Preset ... ]    # {id, label, values}
        },
        ...
      ]
    }

Serialization rules (must match parse.ts output exactly):
  - params: base fields name, label?, group?, unit? — only emitted when
    set; then per kind:
      number/integer: kind, default, min?, max?, step? (only when set)
      boolean:        kind, default
      string:         kind, default
      enum:           kind, default, choices (tuple -> array)
  - presets: {id, label, values} — values keep Python JSON types
    (int/float/bool/string); ints stay ints.
  - key order is fixed; output is 2-space indented + trailing newline so
    regeneration is byte-identical everywhere.

Smoke-tagged models are EXCLUDED: they are toolchain artifacts, not
app-listed models.

--check mode: regenerate in memory and compare against the tracked file.
CI runs `git diff --exit-code build123d/manifest.json` after regenerating,
so a stale manifest (forgot to run the emitter after a model change)
fails the check.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from holders.registry import CATEGORY_IDS, ModelSpec, SAFE_ID_RE  # noqa: E402
from holders.registry import all_models  # noqa: E402

SCHEMA_VERSION = 1
MANIFEST_PATH = ROOT / "manifest.json"

# Fixed key orders — deterministic output, and a shape check against
# lib/scad-params/parse.ts (unknown/missing fields fail validate_manifest).
_MODEL_FIELDS = ("slug", "engine", "title", "blurb", "categoryId", "params", "presets")
_PRESET_FIELDS = ("id", "label", "values")
_ROOT_FIELDS = ("schemaVersion", "models")

# Per-kind key rules: (optional display keys, required kind-specific keys).
# parse.ts emits ONLY set keys, so the strict check is: key SET equals
# required + (optionals actually present) — no unknowns — and every key
# appears in canonical order (a subsequence of the full canonical order).
_PARAM_CANONICAL = ("name", "label", "group", "unit", "kind", "default", "min", "max", "step", "choices")
_PARAM_OPTIONALS = ("label", "group", "unit", "min", "max", "step")
_KIND_REQUIRED = {
    "number": ("kind", "default"),
    "integer": ("kind", "default"),
    "boolean": ("kind", "default"),
    "string": ("kind", "default"),
    "enum": ("kind", "default", "choices"),
}


def _param_field_errors(keys: list[str], kind: str, where: str) -> list[str]:
    required = set(_KIND_REQUIRED.get(kind, ()))
    allowed = set(_PARAM_OPTIONALS) | required | {"name"}
    unknown = [k for k in keys if k not in allowed]
    if unknown:
        return [f"{where}: unknown param fields {unknown}"]
    missing = [k for k in {"name"} | required if k not in keys]
    if missing:
        return [f"{where}: missing required fields {sorted(missing)}"]
    # canonical order: keys must appear as a subsequence of _PARAM_CANONICAL
    index = {k: i for i, k in enumerate(_PARAM_CANONICAL)}
    if [index[k] for k in keys if k in index] != sorted(index[k] for k in keys):
        return [f"{where}: fields not in canonical order: {keys}"]
    return []


def param_to_json(param) -> dict[str, Any]:
    """Serialize a registry Param to the app Param shape (parse.ts)."""
    out: dict[str, Any] = {"name": param.name}
    for field in ("label", "group", "unit"):
        value = getattr(param, field)
        if value is not None:
            out[field] = value
    out["kind"] = param.kind
    if param.kind in ("number", "integer"):
        out["default"] = param.default
        for bound in ("min", "max", "step"):
            value = getattr(param, bound)
            if value is not None:
                out[bound] = value
    else:
        out["default"] = param.default
    if param.kind == "enum":
        out["choices"] = list(param.choices)
    return out


def preset_to_json(preset) -> dict[str, Any]:
    return {"id": preset.id, "label": preset.label, "values": dict(preset.values)}


def spec_to_json(spec: ModelSpec) -> dict[str, Any]:
    return {
        "slug": spec.slug,
        "engine": "build123d",
        "title": spec.title or spec.slug.replace("-", " ").title(),
        "blurb": spec.description,
        "categoryId": spec.category_id,
        "params": [param_to_json(p) for p in spec.params],
        "presets": [preset_to_json(p) for p in spec.presets],
    }


def build_manifest(specs: list[ModelSpec] | None = None) -> dict[str, Any]:
    """Assemble the manifest dict from registered (non-smoke) specs."""
    if specs is None:
        specs = all_models()
    app_listed = [s for s in specs if not s.is_smoke]
    return {"schemaVersion": SCHEMA_VERSION, "models": [spec_to_json(s) for s in app_listed]}


def manifest_text(specs: list[ModelSpec] | None = None) -> str:
    return json.dumps(build_manifest(specs), indent=2) + "\n"


# --------------------------------------------------------------------------
# Strict schema validation (the "reject unknown/missing fields" gate).
# Mirrors parse.ts + the app catalog contract at the JSON level.
# --------------------------------------------------------------------------

def _field_order_errors(actual: list[str], expected: tuple[str, ...], where: str) -> list[str]:
    if actual != list(expected):
        return [
            f"{where}: field set/order {actual} != expected {list(expected)} "
            "(unknown or missing fields are not allowed)"
        ]
    return []


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_manifest(doc: Any, category_ids: set[str] | None = None) -> list[str]:
    """Return a list of problems (empty = valid). Strict on purpose."""
    if category_ids is None:
        category_ids = set(CATEGORY_IDS)
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["manifest root must be an object"]
    errors += _field_order_errors(list(doc), _ROOT_FIELDS, "root")
    if errors:
        return errors
    if doc["schemaVersion"] != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")

    seen_slugs: set[str] = set()
    for i, model in enumerate(doc["models"]):
        mwhere = f"models[{i}]"
        if not isinstance(model, dict):
            errors.append(f"{mwhere} must be an object")
            continue
        errors += _field_order_errors(list(model), _MODEL_FIELDS, mwhere)
        if errors and list(model) != list(_MODEL_FIELDS):
            continue
        slug = model["slug"]
        if not isinstance(slug, str) or not SAFE_ID_RE.match(slug or ""):
            errors.append(f"{mwhere}: slug {slug!r} must be a URL-safe string")
        elif slug in seen_slugs:
            errors.append(f"{mwhere}: duplicate slug {slug!r}")
        else:
            seen_slugs.add(slug)
        if not isinstance(model["engine"], str) or model["engine"] != "build123d":
            errors.append(f"{mwhere}: engine must be 'build123d'")
        for field in ("title", "blurb", "categoryId"):
            if not isinstance(model[field], str) or not model[field]:
                errors.append(f"{mwhere}: {field} must be a non-empty string")
        if isinstance(model["categoryId"], str) and model["categoryId"] not in category_ids:
            errors.append(
                f"{mwhere}: categoryId {model['categoryId']!r} not in {sorted(category_ids)}"
            )

        seen_params: set[str] = set()
        for j, param in enumerate(model["params"]):
            pwhere = f"{mwhere}.params[{j}]"
            if not isinstance(param, dict):
                errors.append(f"{pwhere} must be an object")
                continue
            kind = param.get("kind")
            if kind not in _KIND_REQUIRED:
                errors.append(f"{pwhere}: unknown kind {kind!r}")
                continue
            errors += _param_field_errors(list(param), kind, pwhere)
            if any(p.startswith(pwhere) for p in errors):
                continue
            name = param["name"]
            if not isinstance(name, str) or not name:
                errors.append(f"{pwhere}: name must be a non-empty string")
            elif name in seen_params:
                errors.append(f"{pwhere}: duplicate param name {name!r}")
            else:
                seen_params.add(name)
            for field in ("label", "group", "unit"):
                if field in param and (not isinstance(param[field], str) or not param[field]):
                    errors.append(f"{pwhere}: {field} must be a non-empty string")
            if kind in ("number", "integer"):
                default = param["default"]
                if not _is_number(default):
                    errors.append(f"{pwhere}: default must be a number")
                elif kind == "integer" and isinstance(default, float):
                    errors.append(f"{pwhere}: integer default must be an int, got float")
                for bound in ("min", "max", "step"):
                    if bound in param and not _is_number(param[bound]):
                        errors.append(f"{pwhere}: {bound} must be a number")
                if (
                    _is_number(param.get("min"))
                    and _is_number(param.get("max"))
                    and param["min"] > param["max"]
                ):
                    errors.append(f"{pwhere}: min > max")
                if _is_number(param.get("step")) and param["step"] <= 0:
                    errors.append(f"{pwhere}: step must be > 0")
                if _is_number(default):
                    if _is_number(param.get("min")) and default < param["min"]:
                        errors.append(f"{pwhere}: default < min")
                    if _is_number(param.get("max")) and default > param["max"]:
                        errors.append(f"{pwhere}: default > max")
            elif kind == "boolean":
                if not isinstance(param["default"], bool):
                    errors.append(f"{pwhere}: boolean default must be a bool")
            elif kind == "string":
                if not isinstance(param["default"], str):
                    errors.append(f"{pwhere}: string default must be a string")
            elif kind == "enum":
                choices = param["choices"]
                if (
                    not isinstance(choices, list)
                    or not choices
                    or not all(isinstance(c, str) and c for c in choices)
                    or len(set(choices)) != len(choices)
                ):
                    errors.append(f"{pwhere}: choices must be a non-empty, unique string array")
                elif not isinstance(param["default"], str) or param["default"] not in choices:
                    errors.append(f"{pwhere}: default not in choices")

        seen_preset_ids: set[str] = set()
        for k, preset in enumerate(model["presets"]):
            rwhere = f"{mwhere}.presets[{k}]"
            if not isinstance(preset, dict):
                errors.append(f"{rwhere} must be an object")
                continue
            errors += _field_order_errors(list(preset), _PRESET_FIELDS, rwhere)
            if list(preset) != list(_PRESET_FIELDS):
                continue
            pid = preset["id"]
            if not isinstance(pid, str) or not SAFE_ID_RE.match(pid or ""):
                errors.append(f"{rwhere}: id must be a URL-safe string")
            elif pid in seen_preset_ids:
                errors.append(f"{rwhere}: duplicate preset id {pid!r}")
            else:
                seen_preset_ids.add(pid)
            if not isinstance(preset["label"], str) or not preset["label"]:
                errors.append(f"{rwhere}: label must be a non-empty string")
            values = preset["values"]
            if not isinstance(values, dict):
                errors.append(f"{rwhere}: values must be an object")
                continue
            for pname, pvalue in values.items():
                param = next(
                    (p for p in model["params"] if p.get("name") == pname), None
                )
                if param is None:
                    errors.append(f"{rwhere}: value references unknown param {pname!r}")
                    continue
                kind = param["kind"]
                if kind in ("number", "integer"):
                    if not _is_number(pvalue):
                        errors.append(f"{rwhere}.{pname}: not a number")
                    elif kind == "integer" and isinstance(pvalue, float):
                        errors.append(f"{rwhere}.{pname}: integer param expects int")
                    if _is_number(pvalue):
                        if _is_number(param.get("min")) and pvalue < param["min"]:
                            errors.append(f"{rwhere}.{pname}: below min")
                        if _is_number(param.get("max")) and pvalue > param["max"]:
                            errors.append(f"{rwhere}.{pname}: above max")
                elif kind == "boolean":
                    if not isinstance(pvalue, bool):
                        errors.append(f"{rwhere}.{pname}: not a boolean")
                elif kind == "string":
                    if not isinstance(pvalue, str):
                        errors.append(f"{rwhere}.{pname}: not a string")
                elif kind == "enum":
                    if not isinstance(pvalue, str) or pvalue not in param["choices"]:
                        errors.append(f"{rwhere}.{pname}: not in choices")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if the tracked manifest is stale"
    )
    args = parser.parse_args()

    doc = build_manifest()
    errors = validate_manifest(doc)
    if errors:
        print("manifest validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    if args.check:
        if not MANIFEST_PATH.exists():
            print(f"{MANIFEST_PATH} missing — run: uv run python scripts/manifest.py")
            return 1
        current = MANIFEST_PATH.read_text()
        if current != manifest_text():
            print(f"{MANIFEST_PATH} is stale — run: uv run python scripts/manifest.py")
            return 1
        print(f"manifest.json fresh ({len(doc['models'])} models)")
        return 0

    MANIFEST_PATH.write_text(manifest_text())
    print(f"wrote {MANIFEST_PATH} ({len(doc['models'])} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
