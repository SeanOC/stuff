"""Invariants for the Ego LB6500 blower mount conversion (st-f43).

First import()-based model in the repo: an operator-supplied mesh
(models/ego_lb6500_blower_mount.stl) with its six countersunk screw
holes filled and a Multiconnect backer fused onto the original
build-plate face. Beyond the built-ins (watertight, PRINT_ANCHOR_BBOX
drift, triangle ceiling), this sidecar pins the two claims the
conversion actually makes:

  1. **Screw holes are FILLED.** Probe points inside the original
     bore voids (axis tilted 12 deg in X, entries measured off the
     mesh) and inside the countersink/counterbore region must all be
     solid. If a plug is dropped or drifts off the hole axis, these
     points fall in air.

  2. **Multiconnect slots exist and are open.** Probe points inside
     the five slot channels (25 mm pitch, centered on x=69.25, probed
     near the wall face) must be void; a point in the dome band
     (y < 5) and one between slots must be solid. Catches the
     BOSL2-diff-inside-union failure mode where the generator's slot
     cuts silently vanish, and a mislocated/missing dome band.

  3. **Single connected solid.** The imported mesh, the plugs, and
     the backer must weld into one body. The backer sinks 0.45 mm
     into the plate specifically to swallow two ~0.4 mm logo recesses
     in the original build face that would otherwise become enclosed
     void shells (separate components).

Uses mesh.contains() (trimesh's numpy ray engine) — CI has no
shapely/scipy, so no cross-section polygon analysis here.
"""

from __future__ import annotations

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids

# Measured off the imported mesh (mesh frame: plate build face at z=0).
# Left-trio bore entries; the right trio mirrors as plate_w - x.
BORE_ENTRIES = [(11.19, 12.0), (11.19, 77.0), (19.19, 44.5)]
CBORE_CENTERS = [(7.95, 12.0), (7.95, 77.0), (15.95, 44.5)]
PLATE_W = 138.5
TILT_SLOPE = 0.2124  # bore lean in X per mm of Z (12 deg), outward
SLOT_XS = [19.25, 44.25, 69.25, 94.25, 119.25]  # 25 mm pitch


def check(ctx):
    failures: list[Failure] = []
    p = as_default_params(ctx["params"])
    mesh = ctx["stl"]
    lift = float(p["backer_thickness"])  # mesh z=0 sits at global z=lift

    failures += expect_connected_solids(ctx, 1)

    # 1. Screw-hole fill: probe two depths along each tilted bore and
    # the countersink/counterbore region of each hole.
    fill_pts = []
    for x0, y in BORE_ENTRIES:
        for zm in (2.0, 8.0):  # mesh-frame depths inside the old bore
            x = x0 - TILT_SLOPE * zm
            fill_pts.append([x, y, zm + lift])
            fill_pts.append([PLATE_W - x, y, zm + lift])
    for x, y in CBORE_CENTERS:
        fill_pts.append([x, y, 13.0 + lift])  # countersink/counterbore zone
        fill_pts.append([PLATE_W - x, y, 13.0 + lift])
    solid = mesh.contains(np.array(fill_pts))
    if not bool(solid.all()):
        misses = [fill_pts[i] for i in np.where(~solid)[0]]
        failures.append(
            Failure(
                "screw-holes-filled",
                f"{len(misses)} probe point(s) inside original screw holes "
                f"are void — plugs missing or off-axis: {misses[:4]}",
            )
        )

    # 2. Slot channels open at mid-height, near the wall face (z=1).
    slot_pts = np.array([[x, 50.0, 1.0] for x in SLOT_XS])
    in_slot = mesh.contains(slot_pts)
    if bool(in_slot.any()):
        failures.append(
            Failure(
                "multiconnect-slots",
                f"slot channel probe(s) unexpectedly solid at "
                f"x={[SLOT_XS[i] for i in np.where(in_slot)[0]]} — "
                "Multiconnect slots missing (generator diff() collapsed?)",
            )
        )
    # Dome band and inter-slot web must be solid.
    web_pts = np.array([[69.25, 2.5, 3.0], [56.75, 50.0, 1.0]])
    web = mesh.contains(web_pts)
    if not bool(web.all()):
        failures.append(
            Failure(
                "backer-solid",
                "dome band (y<5) or inter-slot web probe is void — backer "
                "panel/band misplaced",
            )
        )

    return failures
