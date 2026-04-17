#!/usr/bin/env python3
"""Export a .scad model to STL with watertight verification.

Thin wrapper over _lib/export.export. Emits a single JSON object to
stdout. Non-zero exit on any failure (non-watertight, missing STL,
openscad error). The human-in-the-loop approval gate lives in SKILL.md
prose — this script trusts that Claude has already obtained approval.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3].parent
EXPORTS_DIR = REPO_ROOT / "exports"
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills"))

from _lib import export as _exp


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    model = Path(args.model).resolve()
    if not model.exists():
        _emit({"verdict": "export_failed", "model": str(model), "error": f"model not found: {model}"})
        return 2

    name = args.name or model.stem
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_stl = (EXPORTS_DIR / f"{name}.stl").resolve()

    defines = _parse_defines(args.defines)

    try:
        result = _exp.export(model, out_stl, defines=defines)
    except _exp.ExportError as e:
        verdict = "not_watertight" if "not watertight" in str(e).lower() else "export_failed"
        _emit({
            "verdict": verdict,
            "model": _rel(model),
            "stl": _rel(out_stl) if out_stl.exists() else None,
            "error": str(e),
            "warnings": [str(e)],
        })
        return 3

    _emit({
        "verdict": "export_ok",
        "model": _rel(model),
        "stl": _rel(out_stl),
        "bbox_mm": [list(result.bbox_mm[0]), list(result.bbox_mm[1])],
        "triangle_count": result.triangle_count,
        "is_watertight": result.is_watertight,
        "warnings": [],
    })
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export .scad → STL")
    p.add_argument("--model", required=True)
    p.add_argument("--name")
    p.add_argument("-D", dest="defines", action="append", default=[])
    return p.parse_args(argv)


def _parse_defines(raw: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in raw:
        if "=" not in entry:
            raise SystemExit(f"-D entry missing '=': {entry!r}")
        k, v = entry.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _rel(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT)) if p.is_relative_to(REPO_ROOT) else str(p)


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
