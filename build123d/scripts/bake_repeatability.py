"""Diagnose byte differences between two fresh-process production bakes.

This is NOT a geometry-acceptance gate or an upstream re-baseline tool.
Exit 0 means byte identity; exit 1 means differences needing review.
See docs/bake-repeatability.md for the comparison contract and bake recipe.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def _rows(values):
    """Sort exact numeric rows, treating signed zero as the same coordinate."""
    values = np.asarray(values, dtype=np.float64).copy()
    if not np.isfinite(values).all():
        raise ValueError("non-finite mesh coordinates")
    values[values == 0] = 0
    return values[np.lexsort(values.T[::-1])]


def _oriented_triangles(mesh):
    """Ignore face order and cyclic starts, retaining winding and duplicates."""
    triangles = mesh.triangles.copy()
    following = np.roll(triangles, -1, axis=1)
    # The following vertex breaks ties for collapsed triangles such as A,A,B.
    first = np.lexsort(
        (following[:, :, 2], following[:, :, 1], following[:, :, 0],
         triangles[:, :, 2], triangles[:, :, 1], triangles[:, :, 0]), axis=1
    )[:, 0]
    triangles = triangles[
        np.arange(len(triangles))[:, None], (first[:, None] + np.arange(3)) % 3
    ]
    return _rows(triangles.reshape(-1, 9))


def _metrics(raw):
    # Match the production bake's welded watertightness check, but NEVER use
    # this rounded/welded copy for exact triangle-coordinate comparisons.
    mesh = raw.copy()
    mesh.process()
    return {
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
        "volume_mm3": float(mesh.volume),
        "bounds_mm": mesh.bounds.tolist(),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
    }


def compare_stl(before: Path, after: Path) -> dict:
    a, b = (trimesh.load_mesh(path, process=False) for path in (before, after))
    same_triangles = np.array_equal(_oriented_triangles(a), _oriented_triangles(b))
    same_vertices = np.array_equal(
        np.unique(_rows(a.vertices), axis=0), np.unique(_rows(b.vertices), axis=0)
    )
    # "connectivity" is deliberately NOT labelled equivalent geometry.
    return {
        "classification": ("same-oriented-triangles" if same_triangles else
                           "connectivity-or-winding" if same_vertices else
                           "vertex-coordinates"),
        "same_oriented_triangles": same_triangles,
        "same_vertex_coordinates": same_vertices,
        "before": _metrics(a),
        "after": _metrics(b),
    }


def _hashes(directory: Path) -> dict:
    if not directory.is_dir():
        raise ValueError(f"not a bake directory: {directory}")
    hashes = {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()
    }
    if not hashes:
        raise ValueError(f"empty bake directory: {directory}")
    return hashes


def compare_bakes(before: Path, after: Path) -> dict:
    """Compare all files; classify changed STLs without silently accepting any."""
    a, b = _hashes(before), _hashes(after)
    changes = {}
    for name in sorted(a.keys() & b.keys()):
        if a[name] == b[name]:
            continue
        row = {"sha256": [a[name], b[name]]}
        if Path(name).suffix == ".stl":
            row.update(compare_stl(before / name, after / name))
        changes[name] = row
    missing_before, missing_after = sorted(b.keys() - a.keys()), sorted(a.keys() - b.keys())
    return {
        "byte_identical": a == b,
        "file_counts": [len(a), len(b)],
        "missing_before": missing_before,
        "missing_after": missing_after,
        "changes": changes,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    try:
        report = compare_bakes(args.before, args.after)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report["byte_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
