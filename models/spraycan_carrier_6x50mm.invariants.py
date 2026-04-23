"""Invariants for the 2x3 spraycan carrier.

Covers the CAD defect classes that already bit this model:
- st-3ta (footprint): base_d (Y) should be smaller than base_w (X).
  The handle spans X so the handle-side margins are load-bearing; the
  non-handle sides don't need the extra material and wasted footprint.
- st-8ac (clearance): the arch apex must clear a tall can plus a
  fingers-on-grip band, otherwise you can't lift a loaded carrier.

st-v7k (floating arch) is caught by the built-in orphan-fragment
check — a true zero-thickness boolean produces a tiny stray body,
which the built-in flags; legitimate multi-part designs (baseplate +
6 coplanar-seated cradles) land at 7 well-sized components and pass.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params

# Hand clearance between a fully-loaded can's top and the handle apex.
# 10mm is the minimum the design brief calls out (thumb-curl room).
_GRIP_CLEARANCE_MM = 10


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    bbox_x, bbox_y, _bbox_z = ctx["bbox_mm"]

    # st-3ta class: handle runs along X, so the Y margin can be tighter
    # than the X margin. If Y > X the base is an unintentional square
    # that wastes plastic and bed space.
    if bbox_y > bbox_x:
        failures.append(Failure(
            "footprint",
            f"base_d={bbox_y:.1f}mm > base_w={bbox_x:.1f}mm; "
            f"non-handle sides shouldn't be wider than the handle axis "
            f"(st-3ta: check base_margin_other_side)",
        ))

    # st-8ac class: apex = handle_height (measured above the baseplate).
    # A 195mm can needs apex ≥ 205mm to leave a 10mm grip band.
    apex = p.get("handle_height")
    can_height = p.get("can_height")
    if apex is not None and can_height is not None:
        min_apex = can_height + _GRIP_CLEARANCE_MM
        if apex < min_apex:
            failures.append(Failure(
                "clearance",
                f"handle_height={apex}mm < can_height+{_GRIP_CLEARANCE_MM}={min_apex}mm "
                f"(st-8ac: arch will collide with loaded cans)",
            ))

    return failures
