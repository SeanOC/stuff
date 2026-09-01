"""Render worker for the build123d live-render service (bead pst-so26).

Spawned as a short-lived subprocess by ``server.py`` for exactly ONE
render, so the parent HTTP server can enforce a hard wall-clock timeout by
killing this process — OCP builds run in C++ and cannot be interrupted
cleanly from a Python thread, so a subprocess is the only reliable way to
bound a pathological (but in-range) parameter combo (mirrors how the SCAD
service shells ``openscad`` out of ``services/render/server.ts``).

Contract
--------
argv:   <slug> <format:"glb"|"stl"> <out_path>
stdin:  JSON object of param overrides (``{}`` for defaults)
stdout: nothing on success (the geometry is written to ``out_path``)
stderr: on failure, a single JSON line ``{"ok": false, "errorMessage": …}``
exit:   0 = wrote a non-empty mesh to out_path
        3 = unknown / non-app-listed slug   (defensive; parent pre-checks)
        4 = param resolution error          (defensive; parent pre-checks)
        5 = empty / zero-volume mesh (fail-loud, never a silent empty file)
        6 = build / export failure

Only exit 0 ever produces bytes; every other path writes an error line and
leaves ``out_path`` untouched — the parent maps a non-zero exit (or a
timeout it enforced) to a 4xx/5xx JSON response.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# build123d/ (registry + holders + OCP) must be importable. The layout is
# <repo>/services/bd-render/render_worker.py and <repo>/build123d/, so
# parents[2] is the repo root; BD_BUILD123D_ROOT overrides it in the
# container image (where build123d/ is baked at a fixed path).
BUILD123D_ROOT = Path(
    os.environ.get("BD_BUILD123D_ROOT")
    or (Path(__file__).resolve().parents[2] / "build123d")
).resolve()
sys.path.insert(0, str(BUILD123D_ROOT))


def _fail(code: int, message: str) -> int:
    sys.stderr.write(json.dumps({"ok": False, "errorMessage": message}) + "\n")
    return code


def main() -> int:
    if len(sys.argv) != 4:
        return _fail(6, "usage: render_worker.py <slug> <glb|stl> <out_path>")
    slug, fmt, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    if fmt not in ("glb", "stl"):
        return _fail(6, f"unknown format {fmt!r}")

    try:
        raw = sys.stdin.read()
        overrides = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        return _fail(4, f"invalid params JSON: {e}")
    if not isinstance(overrides, dict):
        return _fail(4, "params must be a JSON object")

    # Import inside main so a usage error above doesn't pay the OCP import.
    from build123d import export_gltf, export_stl
    from holders.registry import all_models

    spec = next(
        (m for m in all_models() if not m.is_smoke and m.slug == slug), None
    )
    if spec is None:
        return _fail(3, f"unknown model slug: {slug}")

    # Authoritative param contract: fills defaults, raises on unknown key or
    # out-of-range / kind-mismatched value. Same call the bake path uses.
    try:
        values = spec.resolve_values(overrides)
    except ValueError as e:
        return _fail(4, str(e))

    try:
        part = spec.build(values)
    except Exception as e:  # noqa: BLE001 - any build failure is a 5xx
        return _fail(6, f"build failed: {e}")

    # Fail loud on a degenerate mesh rather than shipping an empty file
    # (mirrors export_presets_only's zero-volume guard).
    try:
        volume = float(part.volume)
    except Exception as e:  # noqa: BLE001
        return _fail(6, f"could not measure volume: {e}")
    if volume <= 0:
        return _fail(5, "empty/zero-volume mesh")

    try:
        if fmt == "glb":
            export_gltf(part, out_path, binary=True)
        else:
            export_stl(part, out_path)
    except Exception as e:  # noqa: BLE001
        return _fail(6, f"export failed: {e}")

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return _fail(6, "exporter wrote no output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
