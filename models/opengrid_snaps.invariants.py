"""Invariants for the standalone openGrid snap connectors (pst-dhr).

`snap_type` fans the export grid into one STL per variant
(lite/full depth x directional/bidirectional), so this sidecar walks
ALL FOUR files rather than trusting the single default variant the
harness hands us as ctx["stl"]. For each variant it pins the claims the
part exists for:

  1. **Renders without error into a real solid.** A wasm/CGAL failure
     can exit 0 with a dropped mesh; every variant STL must exist and
     carry positive volume.

  2. **One welded, watertight solid.** openGridSnap's click nubs kiss
     the core along bare tangent lines (non-manifold); the model's
     0.3mm root-fillet shims fuse them into a single closed body. If a
     QuackWorks/BOSL2 pin move slides the shims off the nubs, the
     watertight or component-count check breaks first.

  3. **openGrid footprint, snaps-down.** The 24.8mm snap footprint (the
     28mm-tile connector) sits on the bed at z=0 in its native print
     orientation — the click nubs widen it only slightly (front nub to
     ~26mm, sides to ~25.6mm), never to a different grid size.

  4. **Correct depth per variant.** Lite snaps stand 3.4mm tall, full
     snaps 6.8mm — the whole reason the variant exists.

Component count uses a local union-find over face adjacency: CI has no
scipy/networkx, so trimesh.split is unavailable (mirrors
opengrid_bin.invariants / ego_lb6500_blower_mount.invariants).
"""

from __future__ import annotations

from pathlib import Path

import trimesh

from scripts.invariants import Failure

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"

_SNAP_W = 24.8            # openGrid snap footprint
_FOOTPRINT_MAX = 27.0    # footprint + proud click nubs, never a new grid size
_CONTACT_EPS_MM = 0.05

# variant name -> expected snap depth (mm)
_VARIANTS = {
    "lite-directional": 3.4,
    "lite-bidirectional": 3.4,
    "full-directional": 6.8,
    "full-bidirectional": 6.8,
}


def check(ctx):
    failures: list[Failure] = []
    for variant, want_h in _VARIANTS.items():
        failures.extend(_check_variant(ctx["stem"], variant, want_h))
    return failures


def _check_variant(stem: str, variant: str, want_h: float) -> list[Failure]:
    path = EXPORTS_DIR / f"{stem}-{variant}.stl"
    if not path.exists():
        return [Failure(
            f"{variant}-export",
            f"{path.name} missing — run scripts/export-all.py "
            "(the snap_type filename grid should produce it)",
        )]
    mesh = trimesh.load(str(path), force="mesh")
    failures: list[Failure] = []

    # 1. Positive volume: a dropped/empty CSG result exits 0 but is hollow.
    if mesh.volume <= 1.0:
        failures.append(Failure(
            f"{variant}-volume",
            f"{path.name} volume {mesh.volume:.2f}mm^3 <= 1 — the snap "
            "solid is empty or collapsed (silent wasm/CGAL drop?)",
        ))

    # 2. One welded watertight solid.
    if not bool(mesh.is_watertight):
        failures.append(Failure(
            f"{variant}-watertight",
            f"{path.name} is not watertight — the root-fillet shims are "
            "not fusing the click nubs to the core",
        ))
    n = _component_count(mesh)
    if n != 1:
        failures.append(Failure(
            f"{variant}-topology",
            f"{path.name} has {n} connected components, expected 1 — a "
            "click nub broke free of the core (shims off the tangent seam)",
        ))

    b = mesh.bounds
    ext = b[1] - b[0]

    # 3. openGrid footprint (the 24.8mm connector), snaps-down at z=0.
    if ext[0] < _SNAP_W - 0.5 or ext[0] > _FOOTPRINT_MAX or \
       ext[1] < _SNAP_W - 0.5 or ext[1] > _FOOTPRINT_MAX:
        failures.append(Failure(
            f"{variant}-footprint",
            f"{path.name} footprint {ext[0]:.1f} x {ext[1]:.1f}mm is not "
            f"the {_SNAP_W}mm openGrid snap (allowed up to "
            f"{_FOOTPRINT_MAX}mm for proud nubs)",
        ))
    if abs(b[0][2]) > _CONTACT_EPS_MM:
        failures.append(Failure(
            f"{variant}-orientation",
            f"{path.name} does not sit on z=0 (zmin={b[0][2]:.3f}) — not "
            "in its snaps-down print orientation",
        ))

    # 4. Depth is the variant's reason to exist (lite 3.4 / full 6.8).
    if abs(ext[2] - want_h) > 0.3:
        failures.append(Failure(
            f"{variant}-depth",
            f"{path.name} stands {ext[2]:.2f}mm, expected {want_h}mm for "
            f"the '{variant}' snap depth",
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

    for a, b in mesh.face_adjacency:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb
    return len({find(i) for i in range(n)})
