"""Invariants for the parametric Gridfinity bin (st-7hq).

The built-in invariants (`is_watertight`, `connected_solids == 1`,
`PRINT_ANCHOR_BBOX` match) cover the structural claims a bin must
satisfy. This sidecar adds parameter-level guards the wrapper
can't enforce at the @param level:

  1. screw_holes implies magnet_holes — the gridfinity-rebuilt
     library puts the screw threads inside the magnet socket, so
     `screw_holes` without `magnet_holes` produces a stub that
     dangles in space.
  2. wall_thickness can't exceed half the cell pitch — once the wall
     swallows half the cell width there's no compartment volume left.
  3. Total-mm mode must match the requested bed-to-lip height within 0.1mm.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params

# Gridfinity unit pitch (GRID_DIMENSIONS_MM in the library).
CELL_PITCH_MM = 42.0


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    if p.get("screw_holes") and not p.get("magnet_holes"):
        failures.append(Failure(
            "base",
            "screw_holes=true requires magnet_holes=true; "
            "screw threads live inside the magnet socket",
        ))

    wall = p.get("wall_thickness")
    if wall is not None and wall * 2 >= CELL_PITCH_MM / 2:
        failures.append(Failure(
            "walls",
            f"wall_thickness={wall}mm leaves no compartment volume "
            f"in a {CELL_PITCH_MM}mm cell",
        ))

    if p.get("height_mode") == "total mm":
        requested = p["height_mm"]
        actual = ctx["bbox_mm"][2]
        if abs(actual - requested) > 0.1:
            failures.append(Failure(
                "height",
                f"total height including lip is {actual:.3f}mm, "
                f"expected {requested}mm ±0.1mm",
            ))

    return failures
