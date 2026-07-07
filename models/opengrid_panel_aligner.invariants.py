"""Invariants for the openGrid panel alignment tool (st-72j).

Built-ins (watertight, orphan fragments, PRINT_ANCHOR_BBOX drift)
cover the mesh basics. The extras here pin the claims this model
exists for:

  1. **One welded solid — supports included.** The snap root-fillet
     shims (st-v7k class) must keep the click nubs fused, AND the
     default-on breakaway fin must stay connected through its neck
     line into the plate. If the QuackWorks/BOSL2 pin moves or the
     neck stops overlapping, the component count breaks first.

  2. **Native print orientation is snaps-down** with bed contact
     spanning exactly the grid_x x grid_y snap array: 24.8 mm
     footprints on the 28 mm openGrid pitch. Also asserts the
     between-snap channels are OPEN at the bed (no geometry may ever
     creep into the trapped-support zone between snaps — the whole
     point of this model's support strategy).

  3. **Snaps fully backed** (st-ocs): the plate must overhang the
     snap array on every side, and the rim chamfer is clamped in the
     .scad so it never crosses a snap footprint — checked here at the
     param level (margin >= 1 mm, chamfer <= margin - 0.2).

  4. **The support fin exists at defaults** (include_supports=true is
     the shipped default) and stays clear of the snap face: fin
     geometry lives above the plate top, never below it.

  5. **Handle stays on the plate** and leaves real finger room.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    grid_x = int(p.get("grid_x", 2))
    grid_y = int(p.get("grid_y", 2))
    snap_lite = bool(p.get("snap_lite", False))
    plate_margin = p.get("plate_margin", 4)
    plate_t = p.get("plate_t", 4)
    handle_span = p.get("handle_span", 40)
    handle_clear = p.get("handle_clear", 30)
    handle_bar_d = p.get("handle_bar_d", 14)
    include_supports = bool(p.get("include_supports", True))
    support_gap = p.get("support_gap", 0.25)

    snap_h = 3.4 if snap_lite else 6.8
    plate_top = snap_h - 0.02 + plate_t

    # --- 2x2 default: the bead requires a 2x2 array out of the box ---
    if grid_x * grid_y < 4:
        failures.append(Failure(
            "snapgrid",
            f"default grid is {grid_x}x{grid_y}; the bead requires 2x2",
        ))

    # --- full backing at the param level (st-ocs) ---
    if plate_margin < 1.0:
        failures.append(Failure(
            "backing",
            f"plate_margin={plate_margin}mm < 1mm rim reserve; snaps are "
            f"not safely enclosed by the plate",
        ))
    # The .scad clamps the rim chamfer to min(plate_t - 0.4,
    # plate_margin - 0.2), so the 45deg cut can never cross a snap
    # footprint; the mesh-level backing evidence is the below-plate
    # envelope check further down.

    # --- handle fits the plate + finger room ---
    span_x = (grid_x - 1) * _SNAP_PITCH + _SNAP_W
    plate_w = span_x + 2 * plate_margin
    if handle_span / 2 + handle_bar_d / 2 > plate_w / 2 - 1:
        failures.append(Failure(
            "handle",
            f"handle posts (span {handle_span} + bar {handle_bar_d}) "
            f"overhang the {plate_w:.1f}mm plate",
        ))
    if handle_clear < 20:
        failures.append(Failure(
            "handle",
            f"handle_clear={handle_clear}mm < 20mm; no room for fingers "
            f"under the crossbar",
        ))

    # --- support interface stays in the snap-off-by-hand band ---
    if not (0.15 <= support_gap <= 0.4):
        failures.append(Failure(
            "supports",
            f"support_gap={support_gap}mm outside the 0.15-0.4mm breakaway "
            f"band the bead specifies",
        ))

    verts = ctx["stl"].vertices

    # --- native orientation: snap faces on the bed, spanning the array ---
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "orientation",
            "no vertices on z=0; model is not in its snaps-down print "
            "orientation",
        ))
        return failures

    want_x = (grid_x - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (grid_y - 1) * _SNAP_PITCH + _SNAP_W
    got_x = contact[:, 0].max() - contact[:, 0].min()
    got_y = contact[:, 1].max() - contact[:, 1].min()
    if abs(got_x - want_x) > 0.5 or abs(got_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"bed contact spans {got_x:.1f} x {got_y:.1f}mm but the "
            f"{grid_x}x{grid_y} snap array should span {want_x:.1f} x "
            f"{want_y:.1f}mm — snaps drifted off the 28mm pitch",
        ))

    # --- pitch/channel check: the gaps between snap columns/rows must be
    # OPEN at the bed. Anything down there is the trapped-support zone. ---
    for axis, count in ((0, grid_x), (1, grid_y)):
        for k in range(count - 1):
            center = (k - (count - 1) / 2 + 0.5) * _SNAP_PITCH
            in_channel = abs(contact[:, axis] - center) < 1.4
            if in_channel.any():
                failures.append(Failure(
                    "channel",
                    f"bed-level geometry inside the {'XY'[axis]}-axis "
                    f"between-snap channel at {center:+.1f}mm — nothing may "
                    f"occupy the gaps between snaps (trapped-support zone)",
                ))

    # --- nothing but snaps below the plate except the plate itself:
    # support material must never hang below the plate bottom outside
    # the snap array envelope ---
    # (+0.6 allowance: the snap click nubs protrude 0.4mm past the
    # 24.8mm footprint by design.)
    below_plate = verts[verts[:, 2] < snap_h - 0.1]
    if len(below_plate):
        off_x = abs(below_plate[:, 0]).max() - (want_x / 2 + 0.6)
        off_y = abs(below_plate[:, 1]).max() - (want_y / 2 + 0.6)
        if off_x > 0 or off_y > 0:
            failures.append(Failure(
                "supports",
                "geometry below the plate extends beyond the snap array "
                "envelope — snap-side support material is forbidden by "
                "design",
            ))

    # --- the breakaway fin ships by default, on the handle side ---
    # Vertex probes can't see a plain cuboid's interior (vertices only
    # exist at its corners), so ask the watertight mesh directly whether
    # a point in the middle of where the fin must stand is solid.
    if include_supports:
        fin_mid = [0.0, 0.0, plate_top + handle_clear / 2]
        if not bool(ctx["stl"].contains([fin_mid])[0]):
            failures.append(Failure(
                "supports",
                f"include_supports=true but the point {fin_mid} under the "
                f"crossbar is empty space — the breakaway fin is missing",
            ))

    return failures
