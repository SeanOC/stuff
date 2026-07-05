"""Invariants for the OpenGrid LED-remote holder (st-vmn).

Twin sidecar: led_remote_holder_55x124mm.invariants.py is identical —
both variants share one design and the checks are all param-driven.

Built-ins (watertight, orphan fragments, PRINT_ANCHOR_BBOX drift)
cover the mesh basics. The extras here pin the claims this model
exists for:

  1. **One welded solid.** openGridSnap's click nubs are face-contact
     solids that the Manifold backend leaves as detached shells; the
     model adds interior weld shims to fuse them. If the QuackWorks or
     BOSL2 pin moves and the shims stop landing inside the nubs, this
     count breaks first (25 shells instead of 1 at defaults).

  2. **Native print orientation is snaps-down.** The bed-contact patch
     (z ~ 0) must exist and span exactly the snap grid, matching the
     auto-fit formula from the .scad (cols/rows of 24.8mm footprints
     on 28mm pitch inside the plate, 1mm rim reserve).

  3. **At least 2 snaps** (bead requirement) at default dims.

  4. **Retention float stays bounded.** The 45deg lip underside only
     catches the remote's face edge if the lip reaches further than
     the sideways play, i.e. lip_over must exceed 2*side_clearance.
"""

from __future__ import annotations

import math

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8


def _grid_fit(extent: float) -> int:
    """Mirror of the .scad snap auto-fit: snaps on 28mm pitch with a
    1mm rim reserve per side."""
    return max(1, math.floor((extent - 2 - _SNAP_W) / _SNAP_PITCH) + 1)


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    remote_w = p.get("remote_w", 51)
    remote_h = p.get("remote_h", 84)
    side_clearance = p.get("side_clearance", 0.45)
    wall = p.get("wall", 2.4)
    lip_over = p.get("lip_over", 3)
    plate_len_max = p.get("plate_len_max", 90)

    outer_w = remote_w + 2 * side_clearance + 2 * wall
    plate_len = min(wall + remote_h + 2 * side_clearance, plate_len_max)
    cols = _grid_fit(outer_w)
    rows = _grid_fit(plate_len)

    if cols * rows < 2:
        failures.append(Failure(
            "snaps",
            f"only {cols * rows} snap(s) fit the default plate; the bead "
            f"requires at least 2 on the 28mm openGrid pitch",
        ))

    # Native orientation: snap faces on the bed, patch spanning the grid.
    verts = ctx["stl"].vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "orientation",
            "no vertices on z=0; model is not in its snaps-down print "
            "orientation",
        ))
        return failures

    span_x = contact[:, 0].max() - contact[:, 0].min()
    span_y = contact[:, 1].max() - contact[:, 1].min()
    want_x = (cols - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (rows - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"bed contact spans {span_x:.1f} x {span_y:.1f}mm but the "
            f"{cols}x{rows} snap grid should span {want_x:.1f} x "
            f"{want_y:.1f}mm — snap placement drifted off the auto-fit "
            f"formula",
        ))

    # Retention: the 45deg lip chamfer converges at the walls, so the
    # remote's face edge is caught after ~side_clearance of float —
    # but only while the lip reaches past the sideways play.
    if lip_over <= 2 * side_clearance:
        failures.append(Failure(
            "retention",
            f"lip_over={lip_over}mm <= 2*side_clearance="
            f"{2 * side_clearance}mm; a shifted remote can slip past "
            f"the retaining lip",
        ))

    return failures
