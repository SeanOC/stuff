"""Invariants for the Ego LB6500 blower mount conversion (st-f43, st-0of).

First import()-based model in the repo: an operator-supplied mesh
(models/ego_lb6500_blower_mount.stl) with its six countersunk screw
holes filled and a selectable back mount fused onto the original
build-plate face — a Multiconnect slot backer (default) or a grid of
directional openGrid snaps (`mount_type`, exported as separate STLs
via the filename grid). Beyond the built-ins (watertight,
PRINT_ANCHOR_BBOX drift, triangle ceiling), this sidecar pins the
claims the conversion actually makes:

  1. **Screw holes are FILLED.** Probe points inside the original
     bore voids (axis tilted 12 deg in X, entries measured off the
     mesh) and inside the countersink/counterbore region must all be
     solid. If a plug is dropped or drifts off the hole axis, these
     points fall in air.

  2. **Multiconnect slots exist, are open, and face the LOAD the
     right way (st-0of).** The Y+ face is the bearing face, so the
     live load points -Y and y=0 is DOWN on the wall. Probe points
     inside the five slot channels (25 mm pitch, centered on x=69.25)
     must be void; the entry mouths must be OPEN through the y=0
     edge (void near y=0); the dome band capping the closed slot
     ends must be solid at the TOP edge (y=84..89). Catches both the
     BOSL2-diff-inside-union failure mode where the generator's slot
     cuts silently vanish AND a 180-deg-flipped backer (the st-f43
     regression this bead fixed: dome band solid near y=0 means the
     mount ejects under load instead of seating).

  3. **Single connected solid.** The imported mesh, the plugs, and
     the backer must weld into one body. The backer sinks 0.45 mm
     into the plate specifically to swallow two ~0.4 mm logo recesses
     in the original build face that would otherwise become enclosed
     void shells (separate components).

  4. **openGrid variant** (exports/<stem>-opengrid.stl, built by the
     export grid alongside the default): watertight, one connected
     solid, snaps present on the top and bottom rows only (the middle
     row is skipped — its two center snaps would float inside the
     central 68.5 x 29 obround cutout and its flankers would seal
     ~0.5 mm build-face recesses into enclosed voids), and each
     snap's strong DIRECTIONAL front nub points +Y (up on the wall):
     only the front nub reaches 13.0 mm from the snap center (rear
     stops at 12.8), so a solid probe at +13.0/void at -13.0 pins
     the orientation.

  5. **Every snap is FULLY BACKED (st-ocs).** The imported plate face
     is notched between x=35..103.5 at both y edges (y 0..15 and
     74..89 are open), so the snap rows hang ~11 mm over air unless
     the backing bands fill the notches behind them. A 3x3 probe
     lattice per snap (center + edges inset 0.5 mm), 1 mm behind the
     plate-face plane, must be entirely solid — catches a dropped or
     mis-sized band the moment any snap edge loses its backing. The
     notches must stay OPEN outside the bands (no full-depth fill /
     no enclosed voids).

Uses mesh.contains() (trimesh's numpy ray engine) — CI has no
shapely/scipy, so no cross-section polygon analysis (and no
trimesh.split, hence the local union-find for the variant mesh).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure, as_default_params, expect_connected_solids

# Measured off the imported mesh (mesh frame: plate build face at z=0).
# Left-trio bore entries; the right trio mirrors as plate_w - x.
BORE_ENTRIES = [(11.19, 12.0), (11.19, 77.0), (19.19, 44.5)]
CBORE_CENTERS = [(7.95, 12.0), (7.95, 77.0), (15.95, 44.5)]
PLATE_W = 138.5
TILT_SLOPE = 0.2124  # bore lean in X per mm of Z (12 deg), outward
SLOT_XS = [19.25, 44.25, 69.25, 94.25, 119.25]  # 25 mm pitch

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"

# openGrid variant geometry (mount_type="opengrid", snap_lite=false):
# 4 cols x 3 rows on 28 mm pitch centered on the 138.5 x 89 plate face,
# middle row skipped over the central obround -> 8 snaps.
OG_LIFT = 6.78  # snap_h (6.8) - og_weld (0.02); mesh z=0 sits here
SNAP_COLS_X = [27.25, 55.25, 83.25, 111.25]
SNAP_ROWS_Y = [16.5, 72.5]  # kept rows; skipped middle row at 44.5


def check(ctx):
    failures: list[Failure] = []
    p = as_default_params(ctx["params"])
    mesh = ctx["stl"]
    lift = float(p["backer_thickness"])  # mesh z=0 sits at global z=lift

    failures += expect_connected_solids(ctx, 1)
    failures += _check_screw_fill(mesh, lift)
    failures += _check_multiconnect(mesh)
    failures += _check_opengrid_variant(ctx["stem"])
    return failures


def _check_screw_fill(mesh, lift: float) -> list[Failure]:
    # Probe two depths along each tilted bore and the
    # countersink/counterbore region of each hole.
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
        return [
            Failure(
                "screw-holes-filled",
                f"{len(misses)} probe point(s) inside original screw holes "
                f"are void — plugs missing or off-axis: {misses[:4]}",
            )
        ]
    return []


def _check_multiconnect(mesh) -> list[Failure]:
    failures: list[Failure] = []

    # Slot channels open at mid-height, near the wall face (z=1).
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

    # Load orientation (st-0of): entry mouth OPEN through the y=0 down
    # edge; dome band SOLID at the top edge (y=84..89); inter-slot web
    # solid. A 180-deg-flipped backer inverts the first two.
    mouth = mesh.contains(np.array([[69.25, 1.0, 1.0]]))
    if bool(mouth[0]):
        failures.append(
            Failure(
                "slot-load-orientation",
                "slot entry region at y=1 is solid — mouths must open "
                "through the y=0 (down) edge so the mount slides DOWN "
                "onto connectors; backer looks 180 deg off",
            )
        )
    web_pts = np.array([[69.25, 86.5, 3.0], [56.75, 50.0, 1.0]])
    web = mesh.contains(web_pts)
    if not bool(web.all()):
        failures.append(
            Failure(
                "backer-solid",
                "dome band (y=84..89) or inter-slot web probe is void — "
                "backer panel/band misplaced or band still at the old "
                "y<5 (pre-st-0of) position",
            )
        )
    return failures


def _check_opengrid_variant(stem: str) -> list[Failure]:
    path = EXPORTS_DIR / f"{stem}-opengrid.stl"
    if not path.exists():
        return [
            Failure(
                "opengrid-export",
                f"{path.name} missing — run scripts/export-all.py "
                "(mount_type filename grid should produce it)",
            )
        ]
    mesh = trimesh.load(str(path))
    failures: list[Failure] = []
    if not bool(mesh.is_watertight):
        failures.append(
            Failure("opengrid-watertight", f"{path.name} is not watertight")
        )
    n = _component_count(mesh)
    if n != 1:
        failures.append(
            Failure(
                "opengrid-topology",
                f"{path.name} has {n} connected components, expected 1 — "
                "detached snaps (obround overlap?) or enclosed recess voids",
            )
        )

    core_pts = [[x, y, 3.0] for y in SNAP_ROWS_Y for x in SNAP_COLS_X]
    solid = mesh.contains(np.array(core_pts))
    if not bool(solid.all()):
        misses = [core_pts[i] for i in np.where(~solid)[0]]
        failures.append(
            Failure(
                "opengrid-snaps",
                f"snap core probe(s) void — snaps missing: {misses[:4]}",
            )
        )

    # Full-footprint backing (st-ocs): 3x3 lattice per snap (edges
    # inset 0.5 mm from the 24.8 footprint), 1 mm behind the
    # plate-face plane — solid everywhere means no snap edge
    # overhangs the stringers/backing bands.
    back_pts = [
        [x + dx, y + dy, OG_LIFT + 1.0]
        for y in SNAP_ROWS_Y
        for x in SNAP_COLS_X
        for dx in (-11.9, 0.0, 11.9)
        for dy in (-11.9, 0.0, 11.9)
    ]
    backed = mesh.contains(np.array(back_pts))
    if not bool(backed.all()):
        misses = [back_pts[i] for i in np.where(~backed)[0]]
        failures.append(
            Failure(
                "opengrid-snaps-backed",
                f"{len(misses)} probe(s) behind snap footprints are void — "
                f"snap edges overhang the stringers/backing bands: "
                f"{misses[:4]}",
            )
        )
    # Bands must fill the notches only behind the snaps — the notch
    # interior beyond the bands stays open (printability + no
    # enclosed voids).
    open_pts = np.array(
        [[69.25, 1.5, OG_LIFT + 1.0],   # bottom notch below the snap edge
         [69.25, 88.0, OG_LIFT + 1.0],  # top notch above the snap edge
         [69.25, 8.0, 15.0]]            # bottom notch behind the band
    )
    still_solid = mesh.contains(open_pts)
    if bool(still_solid.any()):
        failures.append(
            Failure(
                "opengrid-notch-open",
                f"notch probe(s) unexpectedly solid at "
                f"{[open_pts[i].tolist() for i in np.where(still_solid)[0]]} — "
                "backing bands should not fill the edge notches beyond "
                "the snap rows",
            )
        )
    # Middle row must stay clear of the central obround.
    row2 = mesh.contains(np.array([[55.25, 44.5, 3.0], [83.25, 44.5, 3.0]]))
    if bool(row2.any()):
        failures.append(
            Failure(
                "opengrid-obround-clear",
                "snap material inside the central obround row — middle-row "
                "snaps must be skipped (they float in the cutout)",
            )
        )
    # Directional orientation: only the strong front nub reaches 13.0mm
    # from the snap center; it must point +Y (up on the wall).
    front = mesh.contains(np.array([[x, 16.5 + 13.0, 4.1] for x in SNAP_COLS_X]))
    rear = mesh.contains(np.array([[x, 16.5 - 13.0, 4.1] for x in SNAP_COLS_X]))
    if not bool(front.all()) or bool(rear.any()):
        failures.append(
            Failure(
                "opengrid-load-orientation",
                "directional snap front nub not pointing +Y (up) — probe "
                f"front(+13.0)={front.tolist()} rear(-13.0)={rear.tolist()}; "
                "the strong hook must take the top-row lever-out load",
            )
        )
    # Screw plugs must also be filled at the opengrid lift.
    x = BORE_ENTRIES[0][0] - TILT_SLOPE * 2.0
    plug = mesh.contains(np.array([[x, BORE_ENTRIES[0][1], 2.0 + OG_LIFT]]))
    if not bool(plug.all()):
        failures.append(
            Failure(
                "opengrid-screw-fill",
                "screw-hole plug probe void in the opengrid variant — "
                "plugs not tracking body_lift",
            )
        )
    return failures


def _component_count(mesh) -> int:
    """Connected components via union-find over face adjacency.

    trimesh.split needs scipy/networkx which CI doesn't have; this
    mirrors scripts/check-invariants.py's built-in approach.
    """
    n = len(mesh.faces)
    if n == 0:
        return 0
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in mesh.face_adjacency:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb
    return len({find(i) for i in range(n)})
