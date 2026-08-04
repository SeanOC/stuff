"""Invariants for the standalone Multiconnect connectors (pst-ks2).

`connector_type` fans the export grid into one STL per variant
(snap-regular, snap-moderate-wb, snap-heavy-wb, pushfit), so this sidecar
walks ALL FOUR files rather than trusting the single default variant the
harness hands us as ctx["stl"]. The three snap tiers are derived from the
one vendored snap primitive (snapConnectBacker) along its real levers —
bumpout directionality (bidirectional "Regular" vs unidirectional
"Wing Back") and grip strength — via patch 0004's `bumpoutSides` param;
pushfit is the vendored push-fit module. See the .scad header for the
full derivation. The wing-back tiers drop the left/right retention
bumpouts, so their X footprint is smaller than Y (asymmetric) — the
expected extents below are per-axis for exactly that reason.

For each variant it pins the claims the part exists for:

  1. **Renders without error into a real solid.** A wasm/CGAL failure
     can exit 0 with a dropped mesh; every variant STL must exist and
     carry positive volume.

  2. **One watertight solid.** A connector that presses into a board has
     to be a single closed body — a split shell would slice or leak in
     the slicer. snapConnectBacker's BOSL2 diff() tags survive the
     print-orientation transform only if the pinned BOSL2 456fcd8 is in
     force; a bad pin move shows up here first (dropped/split mesh).

  3. **Fits one Multiboard cell, connector-side down.** Both connectors
     seat on the 25mm (1 MU) grid, so the footprint must fit inside one
     pitch; and each sits min-Z on the bed in its support-free print
     orientation (slots-down snap / collar-down peg).

  4. **Engagement depth on the order of the 6.25mm standoff.** The snap
     and peg both stand ~6.5mm — the Part-A standoff height that lets
     them reach through the tile and lock. A collapsed or doubled height
     means the geometry drifted.

Component count uses a local union-find over face adjacency: CI has no
scipy/networkx, so trimesh.split is unavailable (mirrors
opengrid_snaps.invariants / opengrid_bin.invariants).
"""

from __future__ import annotations

from pathlib import Path

import trimesh

from scripts.invariants import Failure

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"

_MB_PITCH = 25.0       # mm, one Multiboard grid unit — a connector fits inside it
_MB_STANDOFF = 6.25    # mm, Part-A standoff — the engagement-depth anchor
_CONTACT_EPS_MM = 0.05
_FOOTPRINT_TOL = 0.6   # mm, allowed drift on the measured footprint
_HEIGHT_TOL = 0.5      # mm, allowed drift on the measured height

# variant name -> (expected x footprint mm, expected y footprint mm, expected height mm)
# Regular is square (bumpouts all four sides); the wing-back tiers drop
# the left/right bumpouts so X < Y, and the heavy tier's stronger grip
# grows the Y bumpouts further out (still inside the 25mm cell).
_VARIANTS = {
    "snap-regular": (23.37, 23.37, 6.58),
    "snap-moderate-wb": (23.12, 23.37, 6.58),
    "snap-heavy-wb": (23.12, 24.27, 6.58),
    "pushfit": (13.50, 13.50, 6.50),
}


def check(ctx):
    failures: list[Failure] = []
    for variant, (want_x, want_y, want_h) in _VARIANTS.items():
        failures.extend(_check_variant(ctx["stem"], variant, want_x, want_y, want_h))
    return failures


def _check_variant(stem: str, variant: str, want_x: float, want_y: float, want_h: float) -> list[Failure]:
    path = EXPORTS_DIR / f"{stem}-{variant}.stl"
    if not path.exists():
        return [Failure(
            f"{variant}-export",
            f"{path.name} missing — run scripts/export-all.py "
            "(the connector_type filename grid should produce it)",
        )]
    mesh = trimesh.load(str(path), force="mesh")
    failures: list[Failure] = []

    # 1. Positive volume: a dropped/empty CSG result exits 0 but is hollow.
    if mesh.volume <= 1.0:
        failures.append(Failure(
            f"{variant}-volume",
            f"{path.name} volume {mesh.volume:.2f}mm^3 <= 1 — the connector "
            "solid is empty or collapsed (silent wasm/CGAL drop?)",
        ))

    # 2. One watertight solid.
    if not bool(mesh.is_watertight):
        failures.append(Failure(
            f"{variant}-watertight",
            f"{path.name} is not watertight — the connector is not a single "
            "closed body (BOSL2 diff()/pin drift on the snap?)",
        ))
    n = _component_count(mesh)
    if n != 1:
        failures.append(Failure(
            f"{variant}-topology",
            f"{path.name} has {n} connected components, expected 1 — the "
            "connector broke into pieces",
        ))

    b = mesh.bounds
    ext = b[1] - b[0]

    # 3. Fits one Multiboard cell, connector-side down at z=0.
    for axis, label, want in ((0, "x", want_x), (1, "y", want_y)):
        if abs(ext[axis] - want) > _FOOTPRINT_TOL:
            failures.append(Failure(
                f"{variant}-footprint-{label}",
                f"{path.name} {label} footprint {ext[axis]:.2f}mm != "
                f"{want}mm (+/-{_FOOTPRINT_TOL}) for '{variant}'",
            ))
        if ext[axis] > _MB_PITCH:
            failures.append(Failure(
                f"{variant}-pitch-{label}",
                f"{path.name} {label} footprint {ext[axis]:.2f}mm exceeds the "
                f"{_MB_PITCH}mm Multiboard cell — a connector must fit one cell",
            ))
    if abs(b[0][2]) > _CONTACT_EPS_MM:
        failures.append(Failure(
            f"{variant}-orientation",
            f"{path.name} does not sit on z=0 (zmin={b[0][2]:.3f}) — not in "
            "its support-free connector-side-down print orientation",
        ))

    # 4. Engagement depth on the order of the 6.25mm standoff.
    if abs(ext[2] - want_h) > _HEIGHT_TOL:
        failures.append(Failure(
            f"{variant}-depth",
            f"{path.name} stands {ext[2]:.2f}mm, expected {want_h}mm for "
            f"'{variant}'",
        ))
    if abs(ext[2] - _MB_STANDOFF) > 1.0:
        failures.append(Failure(
            f"{variant}-standoff",
            f"{path.name} height {ext[2]:.2f}mm is not within 1mm of the "
            f"{_MB_STANDOFF}mm Multiboard standoff — engagement depth drifted",
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
