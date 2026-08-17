"""Invariants for the openGrid-to-Multiconnect wall adapter (pst-9xgx).

`size` fans the export grid into one STL per width (single / double), so
this sidecar walks BOTH files rather than trusting the single default
variant the harness hands as ctx["stl"]. For each variant it pins the
claims the adapter exists for:

  1. **Renders into a real, single, watertight solid.** A wasm/CGAL
     failure can exit 0 with a dropped mesh; every variant STL must
     exist, carry positive volume, be watertight, and be ONE connected
     body — the snaps, plate and receiver welded together (openGridSnap's
     click nubs kiss the core along bare tangent lines; the 0.3mm shims
     fuse them, st-v7k).

  2. **openGrid back, snaps-down.** Bed contact at z=0 is exactly the
     snap grid: one snap per 28mm tile (single = 1, double = 2), so the
     contact span pins both pitch and count and proves the snaps-down
     print orientation. The overall footprint is the whole-tile plate
     (single 28x28, double 56x28).

  3. **Multiconnect receiver on the front.** Each 25mm-pitch slot is a
     real carved channel: a probe point inside the slot mouth (near the
     front face) must fall OUTSIDE the solid, while the back plate below
     it stays solid. Guards against the receiver silently unioning shut.

Component count uses a local union-find over face adjacency: CI has no
scipy/networkx, so trimesh.split is unavailable (mirrors
opengrid_snaps.invariants / opengrid_bin.invariants).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"

_SNAP_PITCH = 28.0
_SNAP_W = 24.8
_CONTACT_EPS_MM = 0.05

# variant name -> (plate width W, snap count, slot X centers)
_VARIANTS = {
    "single": (28.0, 1, [0.0]),
    "double": (56.0, 2, [-12.5, 12.5]),
}
_PLATE_H = 28.0  # one openGrid tile tall


def check(ctx):
    failures: list[Failure] = []
    for variant, (w, snaps, slot_cx) in _VARIANTS.items():
        failures.extend(_check_variant(ctx["stem"], variant, w, snaps, slot_cx))
    return failures


def _check_variant(stem, variant, w, snap_count, slot_cx) -> list[Failure]:
    path = EXPORTS_DIR / f"{stem}-{variant}.stl"
    if not path.exists():
        return [Failure(
            f"{variant}-export",
            f"{path.name} missing — run scripts/export-all.py "
            "(the size filename grid should produce it)",
        )]
    mesh = trimesh.load(str(path), force="mesh")
    failures: list[Failure] = []

    # 1. Real, single, watertight solid.
    if mesh.volume <= 1.0:
        failures.append(Failure(
            f"{variant}-volume",
            f"{path.name} volume {mesh.volume:.2f}mm^3 <= 1 — the solid "
            "is empty or collapsed (silent wasm/CGAL drop?)",
        ))
    if not bool(mesh.is_watertight):
        failures.append(Failure(
            f"{variant}-watertight",
            f"{path.name} is not watertight — a snap shim or the "
            "receiver weld is not fusing",
        ))
    n = _component_count(mesh)
    if n != 1:
        failures.append(Failure(
            f"{variant}-topology",
            f"{path.name} has {n} connected components, expected 1 — the "
            "snaps, plate or receiver broke apart",
        ))

    b = mesh.bounds
    ext = b[1] - b[0]

    # 2. Whole-tile plate footprint, snaps-down at z=0.
    if abs(ext[0] - w) > 0.5 or abs(ext[1] - _PLATE_H) > 0.5:
        failures.append(Failure(
            f"{variant}-footprint",
            f"{path.name} footprint {ext[0]:.1f} x {ext[1]:.1f}mm is not "
            f"the {w:.0f} x {_PLATE_H:.0f}mm whole-tile plate",
        ))
    if abs(b[0][2]) > _CONTACT_EPS_MM:
        failures.append(Failure(
            f"{variant}-orientation",
            f"{path.name} does not sit on z=0 (zmin={b[0][2]:.3f}) — not "
            "in its snaps-down print orientation",
        ))

    # Bed contact = the snap grid (one snap per tile, 28mm pitch).
    verts = mesh.vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            f"{variant}-snapgrid",
            f"{path.name} has no z=0 vertices — no snaps on the bed",
        ))
    else:
        span_x = contact[:, 0].max() - contact[:, 0].min()
        want_x = (snap_count - 1) * _SNAP_PITCH + _SNAP_W
        if abs(span_x - want_x) > 0.6:
            failures.append(Failure(
                f"{variant}-snapgrid",
                f"{path.name} bed contact spans {span_x:.1f}mm but "
                f"{snap_count} snap(s) on the 28mm pitch should span "
                f"{want_x:.1f}mm — snap count or pitch drifted",
            ))

    # 3. Multiconnect receiver: each slot is a real carved channel.
    front_z = ext[2]
    for cx in slot_cx:
        void = np.array([[cx, _PLATE_H / 2, front_z - 1.5],
                         [cx, _PLATE_H / 2 - 4, front_z - 2.5]])
        if any(mesh.contains(void)):
            failures.append(Failure(
                f"{variant}-slot-void",
                f"{path.name} slot at x={cx:.1f} is not open — a probe "
                "inside the slot mouth reads as solid (receiver unioned "
                "shut?)",
            ))
        # The back plate directly under the slot must stay solid.
        plate_pt = np.array([[cx, _PLATE_H / 2, 8.5]])
        if not mesh.contains(plate_pt)[0]:
            failures.append(Failure(
                f"{variant}-plate-solid",
                f"{path.name} back plate under the slot at x={cx:.1f} is "
                "hollow — the slot cut punched through the plate",
            ))

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

    for a, c in mesh.face_adjacency:
        ra, rc = find(int(a)), find(int(c))
        if ra != rc:
            parent[ra] = rc
    return len({find(i) for i in range(n)})
