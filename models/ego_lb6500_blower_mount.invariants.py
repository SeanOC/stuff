"""Invariants for the Ego LB6500 blower mount (st-f43, st-0of, st-82o).

st-82o replaced the import()-based conversion with a NATIVE parametric
remodel: the operator-supplied mesh stays in the repo
(models/ego_lb6500_blower_mount.stl) purely as the FIDELITY REFERENCE
for this sidecar — it is never import()ed or rendered. The model keeps
the selectable back mount fused onto the plate's wall face — a
Multiconnect slot backer (default) or a grid of directional openGrid
snaps (`mount_type`, exported as separate STLs via the filename grid).

Beyond the built-ins (watertight, PRINT_ANCHOR_BBOX drift, triangle
ceiling), this sidecar pins the claims the remodel actually makes:

  1. **Bearing surfaces match the reference mesh (<1mm).** The whole
     point of st-82o's operator constraint: everything the blower can
     touch from above must sit where the original bracket put it.
     Both meshes are raycast from +Y on a jittered ~1.5mm (x, z) grid
     (native lifted by body_lift back into the reference frame) and
     every smooth bearing point — reference height present, 3x3
     neighborhood present within a 3mm range, i.e. not a faceted
     edge — must deviate <= 1mm. Where the reference has NO material
     across the whole neighborhood, the native model must have none
     either (new material could obstruct the blower shell). Catches
     any future edit that moves the beam, shelf, or horn geometry.

  2. **Multiconnect slots exist, are open, and face the LOAD the
     right way (st-0of).** The Y+ face is the bearing face, so the
     live load points -Y and y=0 is DOWN on the wall. Probe points
     inside the five slot channels (25 mm pitch, centered on x=69.25)
     must be void; the entry mouths must be OPEN through the y=0
     edge (void near y=0); the dome band capping the closed slot
     ends must be solid at the TOP edge (y=84..89). Catches both the
     BOSL2-diff-inside-union failure mode where the generator's slot
     cuts silently vanish AND a 180-deg-flipped backer (the st-f43
     regression: dome band solid near y=0 means the mount ejects
     under load instead of seating).

  3. **Single connected solid.** The plate, arms, and back mount must
     weld into one body.

  4. **openGrid variant** (exports/<stem>-opengrid.stl, built by the
     export grid alongside the default): watertight, one connected
     solid, snaps present on the top and bottom rows only (the middle
     row is skipped — its two center snaps would float inside the
     central 68.5 x 29 obround cutout), and each snap's strong
     DIRECTIONAL front nub points +Y (up on the wall). Vertex extents
     in the snap-only z band pin the orientation: only the nubs reach
     past the 24.8 mm snap core — the strong front nub tips out
     13.2 mm from a snap center, the rear click nub 12.8 — so the +Y
     edge of the top row must reach 13.2 and the -Y edge of the
     bottom row must stop at 12.8. (mesh.contains() probes 0.2 mm
     inside the nub tips were raycast-parity-flaky across
     environments — pst-lfk, same rework as ego_powerhead_mount.)

  5. **Every snap is FULLY BACKED (st-ocs).** The plate keeps the
     original's edge notches (x=35..103.5 at both y edges), so the
     snap rows hang ~11 mm over air unless the backing bands fill the
     notches behind them. A 3x3 probe lattice per snap (center +
     edges inset 0.5 mm), 1 mm behind the plate-face plane, must be
     entirely solid. The notches must stay OPEN outside the bands
     (printability + no enclosed voids).

Uses mesh.contains() and trimesh's numpy ray engine — CI has no
shapely/scipy (hence the local union-find for the variant mesh). The
ray engine drops hits that land exactly on triangle edges, so the
fidelity grid is jittered off round coordinates and each ray keeps
its HIGHEST hit from multiple_hits=True.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure, as_default_params, expect_connected_solids

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"
REFERENCE_STL = MODELS_DIR / "ego_lb6500_blower_mount.stl"

SLOT_XS = [19.25, 44.25, 69.25, 94.25, 119.25]  # 25 mm pitch

# Bearing-fidelity sampling (st-82o). Grid is jittered off round
# coordinates so rays don't run along native triangle edges (station
# plates sit at half-integer x); z starts past the back-mount weld
# zone (bands reach 6 mm off the plate face).
FID_XS = np.arange(0.5137, 138.5, 1.5)
FID_ZS = np.arange(8.0731, 160.0, 1.5)
FID_TOL = 1.0    # max |deviation| on smooth bearing points, mm
FID_SMOOTH = 3.0  # neighborhood height range above this = faceted edge

# openGrid variant geometry (mount_type="opengrid", snap_lite=false):
# 4 cols x 3 rows on 28 mm pitch centered on the 138.5 x 89 plate face,
# middle row skipped over the central obround -> 8 snaps.
OG_LIFT = 6.78  # snap_h (6.8) - og_weld (0.02); bracket z=0 sits here
SNAP_COLS_X = [27.25, 55.25, 83.25, 111.25]
SNAP_ROWS_Y = [16.5, 72.5]  # kept rows; skipped middle row at 44.5


def check(ctx):
    failures: list[Failure] = []
    p = as_default_params(ctx["params"])
    mesh = ctx["stl"]
    lift = float(p["backer_thickness"])  # bracket z=0 sits at global z=lift

    failures += expect_connected_solids(ctx, 1)
    failures += _check_bearing_fidelity(mesh, lift)
    failures += _check_multiconnect(mesh)
    failures += _check_opengrid_variant(ctx["stem"])
    return failures


def _heightmap(mesh, zoff: float) -> np.ndarray:
    """Top-surface height h(x, z): highest +Y raycast hit per column."""
    org = np.array([[x, 200.0, z + zoff] for x in FID_XS for z in FID_ZS])
    dirs = np.tile([0.0, -1.0, 0.0], (len(org), 1))
    loc, ray_idx, _ = mesh.ray.intersects_location(org, dirs, multiple_hits=True)
    hit = np.zeros(len(org), dtype=bool)
    hit[ray_idx] = True
    top = np.full(len(org), -np.inf)
    np.maximum.at(top, ray_idx, loc[:, 1])
    h = np.where(hit, top, np.nan)
    return h.reshape(len(FID_XS), len(FID_ZS))


def _check_bearing_fidelity(mesh, lift: float) -> list[Failure]:
    if not REFERENCE_STL.exists():
        return [
            Failure(
                "bearing-reference",
                f"{REFERENCE_STL.name} missing — it is the bearing-surface "
                "fidelity reference for the native remodel (st-82o); "
                "restore it, do not delete it",
            )
        ]
    ref = trimesh.load(str(REFERENCE_STL))
    href = _heightmap(ref, 0.0)
    hnat = _heightmap(mesh, lift)

    bad_solid: list[tuple[float, float, float, float]] = []
    bad_void: list[tuple[float, float, float]] = []
    for i in range(1, len(FID_XS) - 1):
        for j in range(1, len(FID_ZS) - 1):
            nb = href[i - 1 : i + 2, j - 1 : j + 2]
            if np.isfinite(href[i, j]):
                if not np.isfinite(nb).all() or nb.max() - nb.min() > FID_SMOOTH:
                    continue  # faceted edge / feature boundary — unstable
                dev = hnat[i, j] - href[i, j]
                if not np.isfinite(dev) or abs(dev) > FID_TOL:
                    bad_solid.append((FID_XS[i], FID_ZS[j], href[i, j], hnat[i, j]))
            elif not np.isfinite(nb).any() and np.isfinite(hnat[i, j]):
                bad_void.append(
                    (round(float(FID_XS[i]), 1), round(float(FID_ZS[j]), 1),
                     round(float(hnat[i, j]), 2))
                )

    failures: list[Failure] = []
    if bad_solid:
        worst = sorted(
            bad_solid,
            key=lambda t: -(abs(t[3] - t[2]) if np.isfinite(t[3]) else np.inf),
        )[:4]
        failures.append(
            Failure(
                "bearing-fidelity",
                f"{len(bad_solid)} bearing point(s) deviate >{FID_TOL}mm from "
                f"the reference mesh (worst (x, z, ref_y, native_y): "
                f"{[(round(float(a), 1), round(float(b), 1), round(float(c), 2), round(float(d), 2) if np.isfinite(d) else None) for a, b, c, d in worst]}) "
                "— the blower will not seat as the original bracket does",
            )
        )
    if bad_void:
        failures.append(
            Failure(
                "bearing-clearance",
                f"{len(bad_void)} point(s) have native material where the "
                f"reference bracket has none (first: {bad_void[:4]}) — new "
                "material may obstruct the blower shell",
            )
        )
    return failures


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
                "detached snaps (obround overlap?) or enclosed voids",
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
    # Directional orientation: vertex extents in the snap-only z band
    # (below the plate face at z=OG_LIFT), NOT mesh.contains() —
    # raycast parity 0.2mm inside the nub tips flips across
    # environments (welded nub shims leave tangent faces; pst-lfk,
    # same rework as ego_powerhead_mount). In the band only the nubs
    # reach past the 24.8mm snap core: the strong front nub tips out
    # 13.2mm from a snap center, the rear click nub 12.8. Up on the
    # wall is +Y here, so the +Y edge of the top row must reach 13.2
    # and the -Y edge of the bottom row must stop at 12.8.
    v = mesh.vertices
    band = v[(v[:, 2] > 0.05) & (v[:, 2] < OG_LIFT - 0.05)]
    if len(band) == 0:
        failures.append(
            Failure(
                "opengrid-load-orientation",
                "no vertices in the snap-only z band below the plate "
                "face — snaps missing or plate not lifted",
            )
        )
    else:
        front_reach = float(band[:, 1].max()) - SNAP_ROWS_Y[-1]  # +Y side
        rear_reach = SNAP_ROWS_Y[0] - float(band[:, 1].min())    # -Y side
        if not (abs(front_reach - 13.2) <= 0.15
                and abs(rear_reach - 12.8) <= 0.15):
            failures.append(
                Failure(
                    "opengrid-load-orientation",
                    f"directional snap front nub not pointing +Y (up): "
                    f"+Y reach {front_reach:.2f}mm from the top snap row "
                    f"(want 13.2, the strong nub) and -Y reach "
                    f"{rear_reach:.2f}mm from the bottom row (want 12.8, "
                    "the click nub); the strong hook must take the "
                    "top-row lever-out load",
                )
            )
    # Bearing members must track body_lift in the opengrid variant too:
    # beam top, shelf, and horn ridge probed just under their surfaces.
    bear_pts = np.array(
        [[29.0, 88.0, 100.0 + OG_LIFT],   # web beam, 1mm under y=89
         [17.0, 63.8, 40.0 + OG_LIFT],    # shelf rib, 1mm under y=64.8
         [25.4, 92.5, 130.0 + OG_LIFT]]   # horn ridge, 1mm under y=93.5
    )
    bearing = mesh.contains(bear_pts)
    if not bool(bearing.all()):
        failures.append(
            Failure(
                "opengrid-bearing",
                f"bearing member probe(s) void in the opengrid variant "
                f"(beam/shelf/horn = {bearing.tolist()}) — arms not "
                "tracking body_lift",
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
