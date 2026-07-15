"""Invariants for the Ego MultiHead EA0820 edger tool mount (pst-bly).

The model import()s the operator-supplied mesh
(models/ego_ea0820_edger_mount_source.stl) directly, plugs its four
countersunk screw holes, extends the back plate +Y to the 5-cell
openGrid line (y=140), fuses a 2x5 directional openGrid snap grid onto
the wall face, and grows one breakaway support rib inside each hook
tower's tool slot (printability fix — rationale in the .scad header).
Because import() renders that silently drop the mesh are a known
failure mode (st-zph), this sidecar pins the mesh's actual presence
and fidelity, not just the added geometry:

  1. **Single connected solid.** Mesh, plugs, plate extension, ribs,
     and snaps must weld into one body. A dropped import leaves ~12
     floating plugs/snaps and breaks this first.

  2. **Top surfaces match the source mesh (<=0.5mm).** Both meshes are
     raycast from +Y on a jittered ~1.5mm (x, z) grid (the export
     lifted by body_lift back into the source frame) and every smooth
     point — reference height present, 3x3 neighborhood within a 3mm
     range, i.e. not a faceted edge — must deviate <=0.5mm. Where the
     reference has NO material across the whole neighborhood the
     export must have none either. The screw holes are invisible to a
     +Y raycast (they run in z through the y-interior of the plate),
     the snaps sit below the sampled z range, and the breakaway ribs
     hide behind the tower walls (the +Y silhouette in the slot z band
     is the y=22 tower top), so this holds EXACTLY despite the added
     geometry — with one carve-out: across the plate band (source
     z < 16) the +Y silhouette is now owned by the blended plate
     extension, so the expected top there is a flat y=140
     (PLATE_EXT_Y) below the edge rounding (z < EXT_ROUND_Z), and the
     rounded band plus the plan-rounded corner columns are skipped.

  3. **Screw holes are plugged.** Probes inside each hole's measured
     shaft (z=8 slice center) and countersink (z=14.5 slice center)
     must be solid — the part no longer screw-mounts and the wall face
     must present a full flat plane to the grid.

  4. **Bed contact spans exactly the 2x5 snap grid** on the 28mm
     pitch (52.8 x 136.8mm): proves the snaps-down print orientation
     and pins snap count and pitch.

  5. **Directional snaps point their strong nub -Y (usage-up).** In
     real usage 'up' on the wall is the model's -Y vector
     (operator-stated, pst-bly — the axis mapping is an operator
     input, never a geometric inference). In the snap-only z band the
     only geometry reaching past the 24.8mm core is the nubs: the
     strong front nub tips out 13.2mm from a snap center, the rear
     click nub 12.8mm. Vertex extents therefore pin the orientation:
     the -Y edge of the bottom row must reach 13.2, the +Y edge of the
     top row must stop at 12.8. (mesh.contains() probes 0.2mm inside
     the nub tips were raycast-parity-flaky across environments —
     pst-ozs — so this check is vertex-based, not contains()-based.)
     The cantilevered edger head's lever-out moment must bear on the
     rigid hook, not the flexy click side.

  6. **The holder still holds.** Each tower's tool slot stays open
     beside the rib (the EA0820's mounting bar drops in from usage-up
     y=0), and the tower walls that bear it are present, tracking
     body_lift.

  7. **Supportless print.** The two breakaway ribs are present inside
     the tool slots (solid probes mid-rib), the 0.2mm breakaway gap
     under each slot ceiling is open (a fused rib can't be snapped out
     and would scar the tool-bearing slot), and the plate underside's
     floating rim beyond the outermost snap footprints stays a <=1.8mm
     lip on every side — the geometric guarantee behind the "prints
     supportless" claim (everything else >50 deg from vertical is on
     the bed, a 3.2mm channel bridge, or the vendored snap's own
     sub-mm nub relief).

Uses mesh.contains() and trimesh's numpy ray engine — CI has no
shapely/scipy. The ray engine drops hits that land exactly on
triangle edges, so the fidelity grid is jittered off round
coordinates and each ray keeps its HIGHEST hit from
multiple_hits=True (ego_lb6500_blower_mount convention).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure, as_default_params, expect_connected_solids

MODELS_DIR = Path(__file__).resolve().parent
SOURCE_STL = MODELS_DIR / "ego_ea0820_edger_mount_source.stl"

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8
SNAP_COLS_X = [14.0, 42.0]  # 2 cols centered on the 56mm width
SNAP_ROWS_Y = [14.0, 42.0, 70.0, 98.0, 126.0]  # 5 rows centered on the
                                               # extended 140mm back plate
PLATE_EXT_Y = 140.0  # back plate extended +Y to the 5-cell grid line
EXT_ROUND_Z = 13.0   # above this source-frame z the extension's outer
                     # face is rounded (r2 top-edge roundover starts at
                     # z=14), so the flat-face pin stops here
MAX_RIM_LIP = 1.8    # worst allowed floating plate-rim reach beyond the
                     # outermost snap footprints, mm

# Breakaway slot-support ribs: probe points in the SOURCE frame
# (global z = source z + lift). Solid probes sit mid-rib (ribs at
# x 12.0..13.0 / 43.0..44.0, y 1.4..6.8, z 102.75..148.65); the gap
# probe z sits inside the 0.2mm breakaway gap between the rib tops
# (148.65) and the slot ceiling (148.85).
RIB_PROBES = [
    (12.5, 4.0, 125.0),
    (43.5, 4.0, 125.0),
]
RIB_GAP_Z = 148.75

# Fidelity sampling (source frame; global z = source z + lift). Grid
# is jittered off round coordinates so rays don't run along mesh
# triangle edges; z starts above the snap zone (snap tops reach
# global z=6.8, source z ~0.02).
FID_XS = np.arange(0.5137, 56.0, 1.5)
FID_ZS = np.arange(0.6731, 152.4, 1.5)
FID_TOL = 0.5     # max |deviation| on smooth points, mm
FID_SMOOTH = 3.0  # neighborhood height range above this = faceted edge

# Screw-hole probe points (source frame), from slicing the source
# mesh: shaft circle centers at z=8 (the tilted shafts drift outward
# with z), countersink centers at z=14.5. x mirrors about 28; y rows
# at 50.2 and 107.2.
HOLE_PROBES = [
    (11.2, 50.2, 8.0), (11.2, 107.2, 8.0),
    (44.8, 50.2, 8.0), (44.8, 107.2, 8.0),
    (10.0, 50.2, 14.5), (10.0, 107.2, 14.5),
    (46.0, 50.2, 14.5), (46.0, 107.2, 14.5),
]


def check(ctx):
    failures: list[Failure] = []
    p = as_default_params(ctx["params"])
    mesh = ctx["stl"]
    snap_lite = bool(p.get("snap_lite", False))
    lift = (3.4 if snap_lite else 6.8) - 0.02  # body_lift in the model

    failures += expect_connected_solids(ctx, 1)
    failures += _check_fidelity(mesh, lift)
    failures += _check_plugs(mesh, lift)
    failures += _check_snap_grid(mesh)
    failures += _check_snap_orientation(mesh, lift)
    failures += _check_holder_function(mesh, lift)
    failures += _check_printability(mesh, lift)
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


def _check_fidelity(mesh, lift: float) -> list[Failure]:
    if not SOURCE_STL.exists():
        return [
            Failure(
                "source-reference",
                f"{SOURCE_STL.name} missing — it is both the import() "
                "source and the fidelity reference for this model; "
                "restore it, do not delete it",
            )
        ]
    ref = trimesh.load(str(SOURCE_STL))
    href = _heightmap(ref, 0.0)
    hexp = _heightmap(mesh, lift)

    # Across the plate band the +Y silhouette is now owned by the
    # blended back-plate extension — a flat y=140 face below the edge
    # rounding. Pin the flat face; skip the rounded band
    # (z >= EXT_ROUND_Z, where the r2 top-edge roundover pulls the
    # silhouette in by up to 2mm) and the corner columns
    # (x < 3 / x > 53, plan-corner rounding). The bracket body beyond
    # z=16 still tracks the source mesh exactly.
    plate = FID_ZS < 16.0
    href[:, plate & (FID_ZS < EXT_ROUND_Z)] = PLATE_EXT_Y
    href[:, plate & (FID_ZS >= EXT_ROUND_Z)] = np.nan
    href[np.ix_((FID_XS < 3.0) | (FID_XS > 53.0), plate)] = np.nan

    bad_solid: list[tuple[float, float, float, float]] = []
    bad_void: list[tuple[float, float, float]] = []
    for i in range(1, len(FID_XS) - 1):
        for j in range(1, len(FID_ZS) - 1):
            nb = href[i - 1 : i + 2, j - 1 : j + 2]
            if np.isfinite(href[i, j]):
                if not np.isfinite(nb).all() or nb.max() - nb.min() > FID_SMOOTH:
                    continue  # faceted edge / feature boundary — unstable
                dev = hexp[i, j] - href[i, j]
                if not np.isfinite(dev) or abs(dev) > FID_TOL:
                    bad_solid.append((FID_XS[i], FID_ZS[j], href[i, j], hexp[i, j]))
            elif not np.isfinite(nb).any() and np.isfinite(hexp[i, j]):
                bad_void.append(
                    (round(float(FID_XS[i]), 1), round(float(FID_ZS[j]), 1),
                     round(float(hexp[i, j]), 2))
                )

    failures: list[Failure] = []
    if bad_solid:
        worst = sorted(
            bad_solid,
            key=lambda t: -(abs(t[3] - t[2]) if np.isfinite(t[3]) else np.inf),
        )[:4]
        failures.append(
            Failure(
                "import-fidelity",
                f"{len(bad_solid)} point(s) deviate >{FID_TOL}mm from the "
                f"source mesh (worst (x, z, ref_y, export_y): "
                f"{[(round(float(a), 1), round(float(b), 1), round(float(c), 2), round(float(d), 2) if np.isfinite(d) else None) for a, b, c, d in worst]}) "
                "— the import() body is missing, shifted, or mangled",
            )
        )
    if bad_void:
        failures.append(
            Failure(
                "import-clearance",
                f"{len(bad_void)} point(s) have material where the source "
                f"mesh has none (first: {bad_void[:4]}) — new material may "
                "obstruct the edger head",
            )
        )
    return failures


def _check_plugs(mesh, lift: float) -> list[Failure]:
    pts = np.array([[x, y, z + lift] for x, y, z in HOLE_PROBES])
    solid = mesh.contains(pts)
    if bool(solid.all()):
        return []
    misses = [HOLE_PROBES[i] for i in np.where(~solid)[0]]
    return [
        Failure(
            "screw-holes-plugged",
            f"probe(s) inside the original screw holes are void — holes "
            f"not plugged: {misses[:4]}",
        )
    ]


def _check_snap_grid(mesh) -> list[Failure]:
    verts = mesh.vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        return [
            Failure(
                "orientation",
                "no vertices on z=0; model is not in its snaps-down print "
                "orientation",
            )
        ]
    span_x = contact[:, 0].max() - contact[:, 0].min()
    span_y = contact[:, 1].max() - contact[:, 1].min()
    want_x = (len(SNAP_COLS_X) - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (len(SNAP_ROWS_Y) - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        return [
            Failure(
                "snapgrid",
                f"bed contact spans {span_x:.1f} x {span_y:.1f}mm but the "
                f"{len(SNAP_COLS_X)}x{len(SNAP_ROWS_Y)} snap grid on the "
                f"28mm pitch should span {want_x:.1f} x {want_y:.1f}mm — "
                "snap count or pitch drifted",
            )
        ]
    return []


def _check_snap_orientation(mesh, lift: float) -> list[Failure]:
    # Vertex extents in the snap-only z band (below the lifted bracket
    # body): only the nubs reach past the 24.8mm snap core, the strong
    # front nub to 13.2mm from a snap center, the rear click nub to
    # 12.8. Usage-up is -Y (operator-stated, pst-bly), so the 13.2
    # reach must sit on the -Y side of the bottom row and the +Y side
    # of the top row must stop at 12.8. Deliberately NOT
    # mesh.contains(): raycast parity 0.2mm inside the nub tips flips
    # across environments (the welded nub shims leave tangent faces,
    # pst-ozs).
    v = mesh.vertices
    band = v[(v[:, 2] > 0.05) & (v[:, 2] < lift - 0.05)]
    if len(band) == 0:
        return [
            Failure(
                "snap-load-orientation",
                "no vertices in the snap-only z band below the bracket "
                "body — snaps missing or body not lifted",
            )
        ]
    front_reach = SNAP_ROWS_Y[0] - float(band[:, 1].min())  # -Y side
    rear_reach = float(band[:, 1].max()) - SNAP_ROWS_Y[-1]  # +Y side
    if abs(front_reach - 13.2) <= 0.15 and abs(rear_reach - 12.8) <= 0.15:
        return []
    return [
        Failure(
            "snap-load-orientation",
            f"directional snap front nub not pointing -Y (usage-up): "
            f"-Y reach {front_reach:.2f}mm from the bottom snap row "
            f"(want 13.2, the strong nub) and +Y reach "
            f"{rear_reach:.2f}mm from the top row (want 12.8, the "
            "click nub); the strong hook must take the lever-out load",
        )
    ]


def _check_holder_function(mesh, lift: float) -> list[Failure]:
    failures: list[Failure] = []
    # Tool slots stay open beside the ribs (source frame: slot void
    # runs x 10.3..14.65 / mirror, y 0..9, z 102.45..148.85; the rib
    # occupies x 12.0..13.0 / 43.0..44.0, so probe at x 13.8 / 42.2).
    open_pts = np.array(
        [[13.8, 4.0, 125.0 + lift], [42.2, 4.0, 125.0 + lift]]
    )
    solid = mesh.contains(open_pts)
    if bool(solid.any()):
        failures.append(
            Failure(
                "tool-slot-open",
                f"tool slot probe(s) unexpectedly solid at "
                f"{[open_pts[i].tolist() for i in np.where(solid)[0]]} — "
                "the edger head's mounting bar can no longer drop in",
            )
        )
    # Tower walls bearing the slot present on both sides.
    bear_pts = np.array(
        [[8.5, 15.0, 125.0 + lift], [47.5, 15.0, 125.0 + lift],
         [8.5, 4.0, 125.0 + lift], [47.5, 4.0, 125.0 + lift]]
    )
    bearing = mesh.contains(bear_pts)
    if not bool(bearing.all()):
        failures.append(
            Failure(
                "bearing-members",
                f"hook tower probe(s) void ({bearing.tolist()}) — bearing "
                "members missing or not tracking body_lift",
            )
        )
    return failures


def _check_printability(mesh, lift: float) -> list[Failure]:
    """Pin the supportless-print fix (rationale in the .scad header) —
    breakaway ribs present, their top gap open, and the plate-underside
    rim never floating more than a small lip."""
    failures: list[Failure] = []

    ribs = np.array([[x, y, z + lift] for x, y, z in RIB_PROBES])
    solid = mesh.contains(ribs)
    if not bool(solid.all()):
        misses = [RIB_PROBES[i] for i in np.where(~solid)[0]]
        failures.append(
            Failure(
                "breakaway-ribs",
                f"slot support rib probe(s) void: {misses} — the tool-slot "
                "ceilings print mid-air without them",
            )
        )

    gaps = np.array([[x, y, RIB_GAP_Z + lift] for x, y, _ in RIB_PROBES])
    fused = mesh.contains(gaps)
    if bool(fused.any()):
        hits = [RIB_PROBES[i][:2] for i in np.where(fused)[0]]
        failures.append(
            Failure(
                "breakaway-gap",
                f"rib(s) fused to the slot ceiling at (x, y) {hits} — "
                "the 0.2mm breakaway gap is gone; the rib can't be "
                "snapped out and would scar the tool-bearing slot",
            )
        )

    v = mesh.vertices
    lips = {
        "-X": (SNAP_COLS_X[0] - _SNAP_W / 2) - float(v[:, 0].min()),
        "+X": float(v[:, 0].max()) - (SNAP_COLS_X[-1] + _SNAP_W / 2),
        "-Y": (SNAP_ROWS_Y[0] - _SNAP_W / 2) - float(v[:, 1].min()),
        "+Y": float(v[:, 1].max()) - (SNAP_ROWS_Y[-1] + _SNAP_W / 2),
    }
    bad = {k: round(d, 2) for k, d in lips.items() if d > MAX_RIM_LIP}
    if bad:
        failures.append(
            Failure(
                "plate-rim-overhang",
                f"plate underside floats past the outermost snap "
                f"footprints by {bad} (max {MAX_RIM_LIP}mm) — the wall "
                "face starts mid-air again in the snaps-down print "
                "orientation",
            )
        )
    return failures
