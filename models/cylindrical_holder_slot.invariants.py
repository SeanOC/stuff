"""Invariants for the Multiboard cylindrical holder.

Seed set per st-cjn: the built-in `connected_solids == 1` and
`is_watertight` invariants already cover the big structural claims
this model makes. The per-model sidecar exists mostly as a placeholder
that will grow as new defect classes teach us what to check.

The model doesn't currently declare a PRINT_ANCHOR_BBOX so the anchor
invariant (also built-in) silently no-ops.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    # Backer slot region must leave room for at least one Multiconnect
    # mouth plus the top-band solid. 25mm is the library's slot pitch.
    slot_region = p.get("slot_region_height")
    if slot_region is not None and slot_region < 25:
        failures.append(Failure(
            "mount",
            f"slot_region_height={slot_region}mm < 25mm (one Multiconnect pitch); "
            "backer has no room to mount",
        ))

    # Ring wall must exceed the drain hole's radius or the drain breaks
    # through the outer face, not just the inner wall.
    wall = p.get("wall")
    drain_d = p.get("drain_hole_d", 5)
    if wall is not None and wall * 2 <= drain_d:
        failures.append(Failure(
            "ring",
            f"wall={wall}mm can't fit drain_hole_d={drain_d}mm "
            "without punching through the outer face",
        ))

    return failures
