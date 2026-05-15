"""Invariants for the Blu Technology flow meter bench mount.

v1 (st-jtn): bolts entered through caps into base inserts.
v2 (st-246): bolts inverted — enter from base bottom, thread into cap
inserts; cap inboard top edges chamfered for meter tilt clearance.

Default `part="assembly"` exports the base + two caps in their
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

    p = as_default_params(ctx["params"])

    # Default-render is the full assembly: one base + two caps.
    if p.get("part") == "assembly":
        failures.extend(expect_connected_solids(ctx, 3))

    # Display gap (clear span between saddle inner faces) must be
    # non-trivial — otherwise the operator can't lift the LCD lens
    # cover. 30 mm is the minimum we'd ever expect.
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

    # v2 chamfer: dz must stay above the cap's insert pocket with
    # ≥1 mm of wall. dx must stay within the cap width so the
    # chamfer doesn't blow out the outboard face.
    slop          = p.get("slop")
    wall_t        = p.get("wall_t")
    pipe_dia      = p.get("pipe_dia")
    m3_insert_h   = p.get("m3_insert_h")
    relief_angle  = p.get("display_relief_angle")
    if all(v is not None for v in (slop, wall_t, pipe_dia, m3_insert_h,
                                    relief_angle, saddle_w)):
        from math import tan, radians
        pipe_channel_r = pipe_dia / 2 + slop
        cap_h          = wall_t + pipe_channel_r
        chamfer_dz     = max(0.0, cap_h - m3_insert_h - 1.0)
        chamfer_dx     = chamfer_dz * tan(radians(relief_angle))
        # Insert pocket safety: chamfer floor at z = cap_top - chamfer_dz
        # must sit ≥1 mm above the insert top (which is at cap_bottom +
        # m3_insert_h). With the chamfer_dz formula above, this margin
        # is built in — assert it doesn't get squeezed by an unexpected
        # param combination.
        wall_left = cap_h - m3_insert_h - chamfer_dz
        if wall_left < 1.0 - 1e-6:
            failures.append(Failure(
                "chamfer_insert_clearance",
                f"chamfer floor leaves {wall_left:.2f}mm of cap wall "
                f"above the insert pocket; want ≥1.0mm so the brass "
                f"insert isn't pressed into a thin lip",
            ))
        # Chamfer can't eat past the cap outboard face. Leave ≥1 mm.
        if chamfer_dx > saddle_w - 1.0:
            failures.append(Failure(
                "chamfer_outboard_clearance",
                f"chamfer_dx={chamfer_dx:.2f}mm exceeds saddle_w-1="
                f"{saddle_w - 1.0:.2f}mm at display_relief_angle="
                f"{relief_angle}°; lower the angle or widen saddle_w",
            ))

    return failures
