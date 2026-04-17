#!/usr/bin/env python3
"""Render a .scad model to multi-angle PNGs + dimensional JSON.

Composes _lib/openscad.render (per view) with _lib/measure.measure_top (on
the top view). Emits a single JSON object to stdout. Non-zero exit on any
failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3].parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills"))

from _lib import measure as _measure
from _lib import openscad as _osc

ANGLES_DEFAULT = ["top", "front", "side", "iso"]
_ANCHOR_RE = re.compile(
    r"PRINT_ANCHOR_BBOX\s*=\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]",
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    model = Path(args.model).resolve()
    if not model.exists():
        _emit_fail(model, [], f"model not found: {model}")
        return 2

    name = args.name or model.stem
    out_dir = (REPO_ROOT / "renders" / name).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    defines = _parse_defines(args.defines)
    angles = _parse_angles(args.angles)

    known_bbox_mm = _resolve_known_bbox(model, args.known_bbox_mm, defines)

    renders: dict[str, str] = {}
    warnings: list[str] = []
    try:
        for view in angles:
            out_png = out_dir / f"{view}.png"
            result = _osc.render(model, out_png, view=view, defines=defines)
            renders[view] = str(out_png.relative_to(REPO_ROOT))
            warnings.extend(result.warnings)
    except _osc.OpenscadError as e:
        _emit_fail(model, list(renders.keys()), str(e), renders=renders)
        return 3

    measurements: dict | None = None
    if "top" in renders and known_bbox_mm is not None:
        try:
            m = _measure.measure_top(out_dir / "top.png", known_bbox_mm=known_bbox_mm)
            measurements = {
                "bbox_mm": list(m.plate_bbox_mm),
                "scale_mm_per_px": m.scale_mm_per_px,
                "circles_top": [asdict(c) for c in m.circles_top],
            }
        except _measure.MeasurementError as e:
            warnings.append(f"measurement skipped: {e}")
    elif known_bbox_mm is None:
        warnings.append(
            "no PRINT_ANCHOR_BBOX in model source and no --known-bbox-mm — "
            "measurements skipped"
        )

    out = {
        "verdict": "rendered_ok",
        "model": str(model.relative_to(REPO_ROOT))
        if model.is_relative_to(REPO_ROOT)
        else str(model),
        "renders": renders,
        "measurements": measurements,
        "warnings": warnings,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render .scad → PNGs + JSON")
    p.add_argument("--model", required=True)
    p.add_argument("--name")
    p.add_argument("-D", dest="defines", action="append", default=[])
    p.add_argument("--angles", default=",".join(ANGLES_DEFAULT))
    p.add_argument("--known-bbox-mm", dest="known_bbox_mm")
    return p.parse_args(argv)


def _parse_defines(raw: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in raw:
        if "=" not in entry:
            raise SystemExit(f"-D entry missing '=': {entry!r}")
        k, v = entry.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _parse_angles(raw: str) -> list[str]:
    parts = [s.strip() for s in raw.split(",") if s.strip()]
    unknown = [a for a in parts if a not in _osc.VIEWS]
    if unknown:
        raise SystemExit(f"unknown angles: {unknown}; valid: {list(_osc.VIEWS)}")
    return parts


def _resolve_known_bbox(
    model: Path,
    cli_override: str | None,
    defines: dict[str, str],
) -> tuple[float, float] | None:
    if cli_override:
        parts = [float(x) for x in cli_override.split(",")]
        if len(parts) < 2:
            raise SystemExit("--known-bbox-mm must be 'X,Y' or 'X,Y,Z'")
        return (parts[0], parts[1])
    src = model.read_text()
    m = _ANCHOR_RE.search(src)
    if m:
        x, y, _z = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return (x, y)
    return None


def _emit_fail(
    model: Path,
    attempted: list[str],
    error: str,
    renders: dict[str, str] | None = None,
) -> None:
    out = {
        "verdict": "render_failed",
        "model": str(model),
        "renders": renders or {},
        "attempted_angles": attempted,
        "error": error,
        "warnings": [error],
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
