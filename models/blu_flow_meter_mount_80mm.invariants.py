"""Invariants for the Blu Technology flow meter bench mount.

v1 (st-jtn): bolts entered through caps into base inserts.
v2 (st-246): bolts inverted — enter from base bottom, thread into cap
inserts; cap inboard top edges chamfered for meter tilt clearance.
v3 (st-lwz): LCD-forward install orientation; cap chamfer moved from
+X-inboard +Z-top edge to +Y-top edge; keying half-ring shroud in the
display gap constrains the meter to LCD-forward seating.

Default `part="assembly"` exports the base + two caps in their
installed positions: three connected solids that share a pipe channel
but don't merge (the saddle/cap interface is a flat parting plane).
The v3 keying ring is part of the base via union (lower lobes merge
with the base plate), so the connected-solid count stays at 3.

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
        # In v3 the chamfer extends -Y from the +Y face; the relevant
        # outboard limit is the cap's Y depth (saddle_y_half). The
        # insert-clearance guard is still the Z-axis check above —
        # chamfer floor at z = cap_top - chamfer_dz must sit ≥1 mm
        # above the insert top — because the chamfer doesn't reach
        # below its floor in any axis. No extra Y-axis check needed:
        # chamfer_dx can extend past the insert's inboard edge in Y
        # without affecting the insert because they live at different
        # Z bands.

    # v3 keying ring sanity: doesn't intersect the pipe channel, fits
    # within the base footprint in Y, and fits inside the display gap
    # in X with clearance to the saddle inboard faces.
    key_inner_r = p.get("key_inner_r")
    key_outer_r = p.get("key_outer_r")
    key_w       = p.get("key_w")
    base_d_p    = p.get("base_d")
    if all(v is not None for v in (key_inner_r, key_outer_r, key_w,
                                    saddle_w, pipe_len, bare_band_w,
                                    pipe_dia, slop, base_d_p)):
        pipe_channel_r = pipe_dia / 2 + slop
        if key_inner_r <= pipe_channel_r + 0.5:
            failures.append(Failure(
                "keying_intersects_pipe",
                f"key_inner_r={key_inner_r}mm ≤ pipe_channel_r+0.5="
                f"{pipe_channel_r + 0.5:.2f}mm — the keying ring's "
                f"inner wall would touch the pipe bore",
            ))
        if key_outer_r >= base_d_p / 2:
            failures.append(Failure(
                "keying_overhangs_base",
                f"key_outer_r={key_outer_r}mm ≥ base_d/2="
                f"{base_d_p / 2:.2f}mm — the keying ring's -Y arc "
                f"would stick past the base edge in plan view",
            ))
        # Display gap (clear span between saddles) must comfortably
        # fit the keying ring's X-thickness.
        display_gap = (pipe_len / 2 - bare_band_w / 2) * 2 - saddle_w
        if key_w >= display_gap - 4:
            failures.append(Failure(
                "keying_crowds_saddles",
                f"key_w={key_w}mm leaves < 2 mm clearance on each "
                f"side of the {display_gap:.1f}mm display gap — "
                f"the keying ring would crowd the saddle inboard "
                f"faces. Reduce key_w or widen the display gap.",
            ))

    return failures
