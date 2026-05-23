"""Invariants for the Blu Technology flow meter bench mount.

v1   (st-jtn): bolts entered through caps into base inserts.
v2   (st-246): bolts inverted — enter from base bottom, thread into
  cap inserts; cap inboard top edges chamfered for meter tilt.
v3   (st-lwz): LCD-forward install orientation; cap chamfer moved
  from +X-inboard +Z-top edge to +Y-top edge; added half-ring keying
  shroud in the display gap.
v3.1 (st-89c): drops the keying shroud (unprintable bridge geometry);
  adds parametric LCD-saddle dimensions and clearance invariants for
  the LCD-forward seating envelope (body-vs-base, body-vs-cap,
  body-vs-saddle-X).

Default `part="assembly"` exports the base + two caps in their
installed positions: three connected solids that share a pipe channel
but don't merge (the saddle/cap interface is a flat parting plane).

Per-part STL exports (the operator-facing outputs) are produced via
`-D 'part="base"'` and `-D 'part="cap"'`; those don't go through this
sidecar because the catalog uses the assembly view. The `part=
"assembly_with_meter"` view embeds a transparent phantom of the LCD
saddle for visual clearance confirmation — also not analyzed here
because the phantom is rendered with the % modifier (excluded from
the STL).
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

    # v3.1 LCD-forward clearance: the LCD-saddle body must fit in
    # the display gap with measurable margins. Photo-derived defaults
    # for the body envelope live in the .scad as @param so future
    # measurements can be wired in without touching the invariants.
    meter_body_l      = p.get("meter_body_l")
    meter_body_h_lcd  = p.get("meter_body_h_lcd")
    meter_body_h_perp = p.get("meter_body_h_perp")
    meter_bulge_d     = p.get("meter_lcd_bulge_d")
    base_d_p          = p.get("base_d")
    if all(v is not None for v in (meter_body_l, meter_body_h_lcd,
                                    meter_body_h_perp, meter_bulge_d,
                                    pipe_dia, slop, wall_t,
                                    pipe_len, bare_band_w, saddle_w,
                                    base_d_p)):
        pipe_channel_r  = pipe_dia / 2 + slop
        pipe_center_z   = (p.get("base_t") or 0) + wall_t + pipe_channel_r
        saddle_bottom_h = wall_t + pipe_channel_r
        cap_h           = wall_t + pipe_channel_r
        arch_top_z      = (p.get("base_t") or 0) + saddle_bottom_h + cap_h
        # Body extends ±meter_body_h_perp/2 in Z around pipe centre.
        body_top_z    = pipe_center_z + meter_body_h_perp / 2
        body_bottom_z = pipe_center_z - meter_body_h_perp / 2
        base_top_z    = p.get("base_t") or 0
        # Body extends ±meter_body_h_lcd/2 in Y around pipe centre.
        body_face_y_back = -meter_body_h_lcd / 2
        body_face_y_lcd  = +meter_body_h_lcd / 2
        bulge_tip_y      = body_face_y_lcd + meter_bulge_d
        # Body length along pipe X; display_gap is clear span between
        # saddle inboard faces.
        display_gap = (pipe_len / 2 - bare_band_w / 2) * 2 - saddle_w
        body_x_clearance_per_side = (display_gap - meter_body_l) / 2
        # Z clearances
        if body_bottom_z - base_top_z < 2:
            failures.append(Failure(
                "lcd_body_vs_base",
                f"LCD body bottom at z={body_bottom_z:.2f}mm sits "
                f"only {body_bottom_z - base_top_z:.2f}mm above the "
                f"base top at z={base_top_z:.2f}mm (want ≥2mm). Raise "
                f"pipe_center_z (bump wall_t) or shrink meter_body_h_"
                f"perp.",
            ))
        if arch_top_z - body_top_z < 2:
            failures.append(Failure(
                "lcd_body_vs_cap",
                f"LCD body top at z={body_top_z:.2f}mm sits only "
                f"{arch_top_z - body_top_z:.2f}mm below the cap top "
                f"at z={arch_top_z:.2f}mm (want ≥2mm). Bump cap_h "
                f"or shrink meter_body_h_perp.",
            ))
        # X clearance to saddle inboard faces
        if body_x_clearance_per_side < 1.0:
            failures.append(Failure(
                "lcd_body_vs_saddle_x",
                f"LCD body length {meter_body_l}mm leaves only "
                f"{body_x_clearance_per_side:.2f}mm clearance on "
                f"each side of the {display_gap:.1f}mm display gap "
                f"(want ≥1mm). Widen bare_band_w or narrow saddle_w "
                f"if a calipered meter measurement confirms the body "
                f"is longer than the default 44mm.",
            ))
        # +Y bulge tip vs base footprint edge — informational; the
        # bulge is allowed to overhang the base edge (it floats high
        # above the bench), so this is a SOFT warning at >20mm
        # overhang where the bulge would extend past the bench's
        # support footprint by a noticeable amount.
        if bulge_tip_y - base_d_p / 2 > 20:
            failures.append(Failure(
                "lcd_bulge_overhang",
                f"LCD bulge tip at y=+{bulge_tip_y:.1f}mm overhangs "
                f"the base +Y edge at y=+{base_d_p / 2:.1f}mm by "
                f">{bulge_tip_y - base_d_p / 2:.1f}mm — the meter "
                f"may rock forward off the bench. Widen base_d.",
            ))

    return failures
