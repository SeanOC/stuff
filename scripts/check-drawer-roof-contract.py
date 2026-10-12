#!/usr/bin/env python3
"""Independently measure REV 5 inward-roof opening counts from source cutters.

Run from the repository root:
  uv run --directory build123d python ../scripts/check-drawer-roof-contract.py

Only chords above 10 mm receive a roof; floor-reaching roofs may split cells.
The source cutter's bottom-wall XZ section is a convex polygon; +Z is print
up. Intersecting V with the opening stops the roof at its floor/side edges,
as D2-R1/R3 specify. Count connected voids, not input polygon IDs.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "build123d"))

from shapely.geometry import Polygon

from drawer import shell
from holders.openconnect_drawer import SPEC


def inspect(name, values, expected_count):
    source = shell.source_honeycomb_cutters(values)
    assert len(source) == expected_count, "source baseline changed"
    components = 0
    splits = []
    removed_area = 0.0
    expected_splits = 0
    for hole in source:
        opening = Polygon([(v.X, v.Z) for v in hole.vertices()]).convex_hull
        vertices = list(opening.exterior.coords)[:-1]
        ceiling = max(z for _, z in vertices)
        ends = sorted((x, z) for x, z in vertices if abs(z-ceiling) < 1e-7)
        if len(ends) == 1:
            # A side-clipped cell may end at a vertex, with no flat chord.
            components += 1
            continue
        assert len(ends) == 2, "unexpected ceiling boundary"
        left, right = ends
        chord = right[0]-left[0]
        if chord <= 10:
            components += 1
            continue
        expected_splits += opening.bounds[3]-opening.bounds[1] < chord/2
        apex = ((left[0]+right[0])/2, ceiling-chord/2)
        triangle = Polygon([left, right, apex])
        roofed = opening.difference(triangle.intersection(opening))
        assert not roofed.is_empty, "roof filled a source opening"
        assert roofed.geom_type in ("Polygon", "MultiPolygon")
        count = 1 if roofed.geom_type == "Polygon" else len(roofed.geoms)
        components += count
        removed_area += opening.area-roofed.area
        if count != 1:
            splits.append({"ceiling_ends_xz": ends, "apex_xz": apex,
                           "floor_z": opening.bounds[1], "components": count})
    result = {"case": name, "source_openings": len(source),
              "roofed_openings": components, "split_source_openings": len(splits),
              "removed_area_mm2": removed_area,
              "first_split": splits[0] if splits else None}
    assert components == len(source)+expected_splits
    return result


def main():
    small = dict(next(p.values for p in SPEC.presets if p.id == "small"))
    cases = [("default", {}, 97), ("small", small, 17),
             ("strut-2", {"honeycomb_strut_hyp": 2.0}, 99)]
    # The counts are also pinned against this independent 3D-source oracle.
    results = [inspect(name, {**values, "honeycomb_ceiling": "source"}, count)
               for name, values, count in cases]
    for result in results:
        print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
