"""Invariants for the Aquor hose-bib drip deflector (st-s7b).

Single-body part; the built-in checks (watertight, anchor_bbox,
orphan-fragment, triangle ceiling) cover most of what matters. This
sidecar adds one floor — `deflector_depth` shouldn't drop below 20 mm.
Below that the part has nowhere to slope and water would just roll
straight down the wall again, defeating the point.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids


def check(ctx):
    failures = list(expect_connected_solids(ctx, 1))
    p = as_default_params(ctx["params"])
    depth = p.get("deflector_depth")
    if depth is not None and depth < 20:
        failures.append(Failure(
            "geometry",
            f"deflector_depth={depth}mm is below the 20mm floor — water "
            "wouldn't clear the wall plane with so little overhang",
        ))
    return failures
