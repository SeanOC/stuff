"""Invariants for the openGrid panel alignment tool (st-72j, knob rev st-7lc).

Built-ins (watertight, orphan fragments, PRINT_ANCHOR_BBOX drift)
cover the mesh basics. The extras here pin the claims this model
exists for:

  1. **One welded solid.** The snap root-fillet shims (st-v7k class)
     must keep the click nubs fused, and the knob must stay buried in
     the plate. If the QuackWorks/BOSL2 pin moves or an overlap
     degrades to face-kissing, the component count breaks first.

  2. **Native print orientation is snaps-down** with bed contact
     spanning exactly the grid_x x grid_y snap array: 24.8 mm
     footprints on the 28 mm openGrid pitch. Also asserts the
     between-snap channels are OPEN at the bed (no geometry may ever
     creep into the trapped-support zone between snaps).

  3. **Snaps fully backed** (st-ocs): the plate must overhang the
     snap array on every side, and the rim chamfer is clamped in the
     .scad so it never crosses a snap footprint — checked here at the
     param level (margin >= 1 mm).

  4. **The knob is support-free** (the whole point of st-7lc, which
     replaced the arched loop handle and its breakaway fin): the grip
     is a revolved cylinder+dome with NO flare/undercut/mushroom lip,
     so nothing above the plate ever overhangs past the knob wall.
     With the snap side support-free by design, the model slices and
     prints with ZERO supports — none built in, none from the slicer.

  5. **The knob is actually there and grippable**: solid at its core,
     comfortable diameter, on the plate with margin.
"""

from __future__ import annotations

import numpy as np

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
    knob_d = p.get("knob_d", 25)
    knob_h = p.get("knob_h", 34)

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

    # --- knob is grippable and fits the plate ---
    span_x = (grid_x - 1) * _SNAP_PITCH + _SNAP_W
    span_y = (grid_y - 1) * _SNAP_PITCH + _SNAP_W
    plate_w = span_x + 2 * plate_margin
    plate_d = span_y + 2 * plate_margin
    # The .scad clamps the actual knob radius to keep it >= 1mm inside
    # the plate edge; mirror that clamp here so the mesh checks below
    # test the radius that was actually built.
    knob_r = min(knob_d, min(plate_w, plate_d) - 2) / 2
    if knob_d < 18:
        failures.append(Failure(
            "knob",
            f"knob_d={knob_d}mm < 18mm; too thin to grip comfortably",
        ))
    if knob_h < 24:
        failures.append(Failure(
            "knob",
            f"knob_h={knob_h}mm < 24mm; not enough height for a full-hand "
            f"grip on the knob",
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

    want_x = span_x
    want_y = span_y
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

    # --- nothing but snaps below the plate: no geometry may hang below
    # the plate bottom outside the snap array envelope ---
    # (+0.6 allowance: the snap click nubs protrude 0.4mm past the
    # 24.8mm footprint by design.)
    below_plate = verts[verts[:, 2] < snap_h - 0.1]
    if len(below_plate):
        off_x = abs(below_plate[:, 0]).max() - (want_x / 2 + 0.6)
        off_y = abs(below_plate[:, 1]).max() - (want_y / 2 + 0.6)
        if off_x > 0 or off_y > 0:
            failures.append(Failure(
                "backing",
                "geometry below the plate extends beyond the snap array "
                "envelope — nothing but the snaps may live down there",
            ))

    # --- support-free knob: everything above the plate top must stay
    # inside the knob's cylinder wall. A flare/undercut/mushroom lip
    # would poke past knob_r and reintroduce the overhang the knob
    # exists to remove (st-7lc). 0.3mm slack covers facet chords. ---
    above_plate = verts[verts[:, 2] > plate_top + 0.05]
    if len(above_plate) == 0:
        failures.append(Failure(
            "knob",
            "no geometry above the plate top — the knob is missing",
        ))
        return failures
    radial = np.hypot(above_plate[:, 0], above_plate[:, 1])
    worst = radial.max()
    if worst > knob_r + 0.3:
        failures.append(Failure(
            "knob",
            f"geometry above the plate reaches {worst:.2f}mm from the knob "
            f"axis but the knob wall is at {knob_r:.2f}mm — a flare or "
            f"undercut would need supports, which this model forbids",
        ))

    # --- the knob is solid, centered, and full height ---
    knob_mid = [0.0, 0.0, plate_top + knob_h / 2]
    if not bool(ctx["stl"].contains([knob_mid])[0]):
        failures.append(Failure(
            "knob",
            f"the point {knob_mid} at the knob core is empty space — the "
            f"knob is missing or off-center",
        ))
    got_apex = verts[:, 2].max()
    want_apex = plate_top + knob_h
    if abs(got_apex - want_apex) > 0.5:
        failures.append(Failure(
            "knob",
            f"model apex at z={got_apex:.2f}mm; expected the knob top at "
            f"{want_apex:.2f}mm",
        ))

    return failures
