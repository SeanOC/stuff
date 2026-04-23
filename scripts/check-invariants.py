#!/usr/bin/env python3
"""Run the per-model invariants sidecar plus built-in checks for one model.

Usage: scripts/check-invariants.py <stem>
  e.g. scripts/check-invariants.py spraycan_carrier_6x50mm

Loads models/<stem>.scad and exports/<stem>.stl, optionally dynamic-
imports models/<stem>.invariants.py, and runs both the built-in
invariants (topology, watertight, triangle ceiling, PRINT_ANCHOR_BBOX)
and anything the sidecar's `check(ctx)` returns.

Exits 0 on all green; non-zero with a report on any failure.

Per st-cjn: the sidecar is "stop-the-bleeding" infra for three known
defect classes (st-v7k topology, st-8ac clearance, st-3ta footprint).
Continuity/C¹ issues — st-hnd class — are a separate P1 bead.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

import trimesh

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
EXPORTS_DIR = REPO_ROOT / "exports"

# Make `scripts.invariants` importable whether invoked as `python3
# scripts/check-invariants.py ...` (no package context) or via `-m`.
sys.path.insert(0, str(REPO_ROOT))

from scripts.invariants import Failure, parse_anchor_bbox, run_builtins  # noqa: E402
from scripts.invariants.params import parse_params  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    stem = args.stem

    scad = MODELS_DIR / f"{stem}.scad"
    stl = EXPORTS_DIR / f"{stem}.stl"

    if not scad.exists():
        print(f"error: model not found: {scad}", file=sys.stderr)
        return 2
    if not stl.exists():
        print(
            f"error: export not found: {stl}\n"
            f"  run the export skill or scripts/export-all.py first",
            file=sys.stderr,
        )
        return 2

    source = scad.read_text(encoding="utf-8")
    mesh = trimesh.load(stl, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        print(f"error: trimesh could not load {stl} as a single mesh", file=sys.stderr)
        return 2

    ctx = _build_context(stem, source, mesh)

    failures: list[Failure] = []
    failures.extend(run_builtins(ctx))
    failures.extend(_run_sidecar(stem, ctx))

    if failures:
        print(f"\n{stem}: {len(failures)} invariant(s) failed")
        for f in failures:
            print(f"  {f.format()}")
        return 1

    print(f"{stem}: ok")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check invariants for one model")
    p.add_argument("stem", help="model stem, e.g. spraycan_carrier_6x50mm")
    return p.parse_args(argv)


def _build_context(
    stem: str,
    source: str,
    mesh: trimesh.Trimesh,
) -> dict[str, Any]:
    bounds = mesh.bounds
    bbox = (
        float(bounds[1, 0] - bounds[0, 0]),
        float(bounds[1, 1] - bounds[0, 1]),
        float(bounds[1, 2] - bounds[0, 2]),
    )
    sizes = _component_sizes(mesh)
    return {
        "stem": stem,
        "source": source,
        "params": parse_params(source),
        "stl": mesh,
        "bbox_mm": bbox,
        "anchor_bbox_mm": parse_anchor_bbox(source),
        "connected_solids": len(sizes),
        "component_sizes": sizes,
    }


def _component_sizes(mesh: trimesh.Trimesh) -> list[int]:
    """Triangle count per connected component, descending.

    trimesh.Trimesh.split needs scipy or networkx; rather than drag in
    another dep for CI, walk face_adjacency with Union-Find. Linear in
    face count, good enough for our < 1M-triangle ceiling.
    """
    n = len(mesh.faces)
    if n == 0:
        return []
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in mesh.face_adjacency:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb

    counts: dict[int, int] = {}
    for i in range(n):
        root = find(i)
        counts[root] = counts.get(root, 0) + 1
    return sorted(counts.values(), reverse=True)


def _run_sidecar(stem: str, ctx: dict[str, Any]) -> list[Failure]:
    sidecar = MODELS_DIR / f"{stem}.invariants.py"
    if not sidecar.exists():
        return []
    spec = importlib.util.spec_from_file_location(
        f"models.{stem}.invariants", sidecar
    )
    if spec is None or spec.loader is None:
        print(f"warning: could not load {sidecar}", file=sys.stderr)
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    check = getattr(module, "check", None)
    if not callable(check):
        print(
            f"warning: {sidecar} has no check(ctx) function — skipping",
            file=sys.stderr,
        )
        return []
    result = check(ctx)
    if not isinstance(result, list):
        print(
            f"warning: {sidecar}.check returned {type(result).__name__}, "
            "expected list[Failure]",
            file=sys.stderr,
        )
        return []
    return result


if __name__ == "__main__":
    raise SystemExit(main())
