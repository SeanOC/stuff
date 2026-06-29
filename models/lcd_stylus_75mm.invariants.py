"""Invariants for the kids' LCD-drawing-pad stylus.

Built-ins (watertight, single connected body, PRINT_ANCHOR_BBOX drift) cover
the structural claims. The extra checks below guard the two properties the
design exists for: a single solid body, and a tip-up taper that stays
self-supporting (the body only narrows going up — no overhang past the base
rim) so it prints without supports.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    R = p.get("body_diameter", 7.5) / 2
    rt = p.get("tip_radius", 2)
    bf = p.get("base_flat", 1.5)

    # Tip must stay rounded and clearly narrower than the body, or it reads as
    # a blunt nub (and risks the LCD film if it sharpens).
    if rt >= R:
        failures.append(Failure(
            "tip",
            f"tip_radius={rt}mm >= body radius {R}mm; tip won't taper to a dome",
        ))

    # The base-cut must not eat into the body proper. With a bottom bulb of
    # radius R, cutting deeper than R removes the widest section and the part
    # loses its flat-base / rounded-rim geometry.
    if bf >= R:
        failures.append(Failure(
            "base",
            f"base_flat={bf}mm >= bulb radius {R}mm; cut removes the body, not just the rim",
        ))

    return failures
