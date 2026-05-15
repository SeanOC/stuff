"""Invariants for the Blu black-tank flush valve bench mount.

Companion to the v2 flow meter mount (st-246) — same hardware pattern
(bottom-entry M3 SHCS, heat-set inserts in caps) but ASYMMETRIC
saddles (left bore 31.5 mm, right bore 29.25 mm) and an extra handle-
clearance cut so the T-handle's swept volume stays free.

Default `part="assembly"` exports the base + two caps in their
installed positions: three connected solids that share pipe channels
but don't merge (each saddle/cap interface is a flat parting plane).
Pin the count so a regression that fuses or splits a piece fails.

Per-part STL exports (the operator-facing outputs) use
`-D 'part="base"'`, `-D 'part="cap_left"'`, `-D 'part="cap_right"'`
and don't go through this sidecar — the catalog uses the assembly view.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids


def check(ctx):
    failures: list[Failure] = []

    p = as_default_params(ctx["params"])

    # Assembly view: one base + two caps.
    if p.get("part") == "assembly":
        failures.extend(expect_connected_solids(ctx, 3))

    bore_left   = p.get("bore_left")
    bore_right  = p.get("bore_right")
    fitting_gap = p.get("fitting_gap")
    saddle_w    = p.get("saddle_w")
    wall_t      = p.get("wall_t")
    slop        = p.get("slop")
    base_t      = p.get("base_t")
    m3_head_depth = p.get("m3_head_depth")
    m3_insert_h   = p.get("m3_insert_h")
    bolt_y_offset = p.get("bolt_y_offset")
    handle_excl_r = p.get("handle_excl_r")

    # Asymmetric saddles: the whole point of this part vs the flow
    # meter mount is that the two fittings have distinct OD. If they
    # ever collapse onto the same value the part has silently lost the
    # asymmetric-saddle property the bead spec'd.
    if bore_left is not None and bore_right is not None:
        if abs(bore_left - bore_right) < 0.5:
            failures.append(Failure(
                "asymmetric_bores",
                f"bore_left={bore_left} bore_right={bore_right} differ "
                f"by < 0.5 mm; per st-i32 spec these are 31.5 vs 29.25 "
                f"mm — saddles would no longer seat correctly",
            ))

    # Display/middle gap: keep enough room for the valve body and
    # T-handle pivot between the two saddle inner faces.
    if fitting_gap is not None and fitting_gap < 25:
        failures.append(Failure(
            "fitting_gap_too_small",
            f"fitting_gap={fitting_gap} mm < 25 mm — the valve body "
            f"won't fit between the saddles and the T-handle has no "
            f"swept volume",
        ))

    # Stack math: bolt path from below the counterbore floor up to the
    # insert top. v2 baseline is M3×30 (30 mm under head). Flag any
    # parameter combo that would exceed 32 mm — the polecat must then
    # spec a longer bolt in the header.
    if all(v is not None for v in (base_t, wall_t, slop, m3_head_depth,
                                    m3_insert_h, bore_left, bore_right)):
        max_r           = max(bore_left, bore_right) / 2 + slop
        pipe_center_z   = base_t + wall_t + max_r
        saddle_bottom_h = pipe_center_z - base_t
        bolt_path       = (base_t + saddle_bottom_h + m3_insert_h) - m3_head_depth
        if bolt_path > 32:
            failures.append(Failure(
                "bolt_length",
                f"under-head bolt path = {bolt_path:.2f} mm exceeds the "
                f"M3×30 baseline; update the header to spec M3×35 SHCS",
            ))

    # Handle exclusion cylinder geometry sanity.
    #   - Cap inboard face sits at x = saddle_center_x - saddle_w/2.
    #   - Cap outboard face sits at x = saddle_center_x + saddle_w/2.
    #   - Insert pockets sit at x = ±saddle_center_x, y = ±bolt_y_offset.
    # If the exclusion cylinder reaches the cap outboard face it would
    # sever the cap. If it reaches the insert pockets it would carve
    # them open. Flag both.
    if all(v is not None for v in (saddle_w, fitting_gap, handle_excl_r,
                                    bolt_y_offset)):
        saddle_center_x = fitting_gap / 2 + saddle_w / 2
        cap_outboard_x  = saddle_center_x + saddle_w / 2
        if handle_excl_r >= cap_outboard_x:
            failures.append(Failure(
                "handle_exclusion_severs_cap",
                f"handle_excl_r={handle_excl_r} mm reaches the cap "
                f"outboard face at x={cap_outboard_x:.1f} mm — the "
                f"exclusion cut would split the cap into two pieces. "
                f"Reduce handle_excl_r or widen fitting_gap",
            ))
        # Insert pocket distance from the exclusion axis.
        from math import hypot
        insert_r_from_axis = hypot(saddle_center_x, bolt_y_offset)
        if handle_excl_r >= insert_r_from_axis - 2:
            failures.append(Failure(
                "handle_exclusion_carves_inserts",
                f"handle_excl_r={handle_excl_r} mm is within 2 mm of "
                f"the insert pockets at radial distance "
                f"{insert_r_from_axis:.1f} mm from the valve axis — "
                f"the exclusion cut would weaken the bolt anchorages",
            ))

    return failures
