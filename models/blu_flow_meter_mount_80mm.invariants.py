"""Invariants for the Blu Technology flow meter bench mount (st-jtn).

Default `part="assembly"` exports both the base + two caps in their
installed positions: three connected solids that share a pipe channel
but don't merge (the saddle/cap interface is a flat parting plane).
Pin the exact count so a regression that fuses or splits a piece
fails loudly.

Per-part STL exports (the operator-facing outputs) are produced via
`-D 'part="base"'` and `-D 'part="cap"'`; those don't go through this
sidecar because the catalog uses the assembly view.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids


def check(ctx):
    failures: list[Failure] = []

    # Default-render is the full assembly: one base + two caps. If
    # someone exports with a different `part`, skip the count assertion
    # (those exports aren't catalog-visible).
    p = as_default_params(ctx["params"])
    if p.get("part") == "assembly":
        failures.extend(expect_connected_solids(ctx, 3))

    # Sanity check: the display gap (clear span between saddle inner
    # faces) must be non-trivial — otherwise the operator can't lift
    # the LCD lens cover. 30 mm is the minimum we'd ever expect.
    pipe_len    = p.get("pipe_len")
    bare_band_w = p.get("bare_band_w")
    saddle_w    = p.get("saddle_w")
    if pipe_len is not None and bare_band_w is not None and saddle_w is not None:
        saddle_center_x = pipe_len / 2 - bare_band_w / 2
        display_gap     = 2 * saddle_center_x - saddle_w
        if display_gap < 30:
            failures.append(Failure(
                "clearance",
                f"display_gap={display_gap:.1f}mm < 30mm — the LCD saddle "
                f"in the meter's middle won't have room to clear the "
                f"mount saddles; widen bare_band_w or narrow saddle_w",
            ))

    return failures
