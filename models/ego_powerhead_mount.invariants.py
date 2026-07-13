"""Invariants for the Ego Power+ powerhead mount (pst-3m2).

The model import()s the operator-supplied mesh
(models/ego_powerhead_mount_source.stl) directly, plugs its four
countersunk screw holes, and fuses a 2x3 directional openGrid snap
grid onto the wall face. Because import() renders that silently drop
the mesh are a known failure mode (st-zph), this sidecar pins the
mesh's actual presence and fidelity, not just the added geometry:

  1. **Single connected solid.** Mesh, plugs, and snaps must weld into
     one body. A dropped import leaves ~10 floating plugs/snaps and
     breaks this first.

  2. **Top surfaces match the source mesh (<=0.5mm).** Both meshes are
     raycast from +Y on a jittered ~1.5mm (x, z) grid (the export
     lifted by body_lift back into the source frame) and every smooth
     point — reference height present, 3x3 neighborhood within a 3mm
     range, i.e. not a faceted edge — must deviate <=0.5mm. Where the
     reference has NO material across the whole neighborhood the
     export must have none either. The screw holes are invisible to a
     +Y raycast (they run in z through the y-interior of the plate)
     and the snaps sit below the sampled z range, so this holds
     EXACTLY despite the added geometry — any drift means the import
     or its frame broke.

  3. **Screw holes are plugged.** Probes inside each hole's measured
     shaft (z=8 slice center) and countersink (z=13.5 slice center)
     must be solid — the part no longer screw-mounts and the wall face
     must present a full flat plane to the grid.

  4. **Bed contact spans exactly the 2x3 snap grid** on the 28mm
     pitch (52.8 x 80.8mm): proves the snaps-down print orientation
     and pins snap count and pitch.

  5. **Directional snaps point their strong nub +Y (up the wall).**
     Only the front nub reaches 13.0mm from a snap center (rear click
     nub stops at 12.8), so a solid probe at +13.0/void at -13.0 on
     the bottom snap row pins the orientation (st-0of rationale: the
     cantilevered powerhead's lever-out moment must bear on the rigid
     hook, not the flexy click side).

  6. **The holder still holds.** The ~27mm central shaft slot at the
     outer end stays open through both levels, and the fork-prong and
     shelf-rail bearing bodies are present at the outer end, tracking
     body_lift.

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
SOURCE_STL = MODELS_DIR / "ego_powerhead_mount_source.stl"

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8
SNAP_COLS_X = [14.0, 42.0]         # 2 cols centered on the 56mm width
SNAP_ROWS_Y = [27.0, 55.0, 83.0]   # 3 rows centered on the 110mm height

# Fidelity sampling (source frame; global z = source z + lift). Grid
# is jittered off round coordinates so rays don't run along mesh
# triangle edges; z starts above the snap zone (snap tops reach
# global z=6.8, source z ~0.02).
FID_XS = np.arange(0.5137, 56.0, 1.5)
FID_ZS = np.arange(0.6731, 135.0, 1.5)
FID_TOL = 0.5     # max |deviation| on smooth points, mm
FID_SMOOTH = 3.0  # neighborhood height range above this = faceted edge

# Screw-hole probe points (source frame), from slicing the source
# mesh: shaft circle centers at z=8, countersink centers at z=13.5.
# x mirrors about 28; y rows at 40 and 97.
HOLE_PROBES = [
    (10.98, 40.0, 8.0), (10.98, 97.0, 8.0),
    (45.02, 40.0, 8.0), (45.02, 97.0, 8.0),
    (9.71, 40.0, 13.5), (9.71, 97.0, 13.5),
    (46.29, 40.0, 13.5), (46.29, 97.0, 13.5),
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
    failures += _check_snap_orientation(mesh)
    failures += _check_holder_function(mesh, lift)
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
                "obstruct the powerhead",
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
                f"2x3 snap grid on the 28mm pitch should span "
                f"{want_x:.1f} x {want_y:.1f}mm — snap count or pitch "
                "drifted",
            )
        ]
    return []


def _check_snap_orientation(mesh) -> list[Failure]:
    # Bottom snap row (y=27): only the strong front nub reaches 13.0mm
    # from the snap center (tip at 13.2; the rear click nub stops at
    # 12.8). z=4.1 sits in the full-depth snap's nub band.
    y = SNAP_ROWS_Y[0]
    front = mesh.contains(np.array([[x, y + 13.0, 4.1] for x in SNAP_COLS_X]))
    rear = mesh.contains(np.array([[x, y - 13.0, 4.1] for x in SNAP_COLS_X]))
    if bool(front.all()) and not bool(rear.any()):
        return []
    return [
        Failure(
            "snap-load-orientation",
            "directional snap front nub not pointing +Y (up) — probe "
            f"front(+13.0)={front.tolist()} rear(-13.0)={rear.tolist()}; "
            "the strong hook must take the top-row lever-out load",
        )
    ]


def _check_holder_function(mesh, lift: float) -> list[Failure]:
    failures: list[Failure] = []
    # Central shaft slot open through both levels at the outer end
    # (source frame: fork level y=63, shelf level y=11, slot spans
    # x~14.7..41.4 at z>=120).
    open_pts = np.array(
        [[28.0, 63.0, 130.0 + lift], [28.0, 11.0, 130.0 + lift]]
    )
    solid = mesh.contains(open_pts)
    if bool(solid.any()):
        failures.append(
            Failure(
                "shaft-slot-open",
                f"central shaft slot probe(s) unexpectedly solid at "
                f"{[open_pts[i].tolist() for i in np.where(solid)[0]]} — "
                "the powerhead shaft can no longer drop in",
            )
        )
    # Fork prongs and shelf rails present at the outer end.
    bear_pts = np.array(
        [[10.7, 63.0, 130.0 + lift], [45.3, 63.0, 130.0 + lift],
         [7.0, 11.0, 130.0 + lift], [49.0, 11.0, 130.0 + lift]]
    )
    bearing = mesh.contains(bear_pts)
    if not bool(bearing.all()):
        failures.append(
            Failure(
                "bearing-members",
                f"fork/shelf probe(s) void at the outer end "
                f"({bearing.tolist()}) — bearing members missing or not "
                "tracking body_lift",
            )
        )
    return failures
