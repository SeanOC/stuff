"""Invariants for the Little Tikes Dream Machine cartridge + figure holder.

A native openGrid tray whose footprint derives from a whole number of
28mm cells, then AUTO-FILLS with cartridge slots (top face) and figure
holders (front face) whose counts are computed from the footprint and
the feature pitch. The claims below pin exactly that behaviour so a
geometry regression can't ship a tray with the wrong feature counts,
a broken floor, or a shattered snap weld:

  1. **Single connected solid.** Block, slot/figure cuts, and every snap
     weld into one printed body. A snap shim that stops landing in the
     click nubs (QuackWorks/BOSL2 pin drift) breaks this first. (The CGAL
     export the driver loads is clean single-body; the Manifold/wasm
     preview leaves tiny cosmetic nub slivers that never reach here.)

  2. **Footprint is an exact openGrid cell grid.** The XY bbox equals
     grid_cols x grid_rows * 28mm — the property that makes the back a
     clean cell grid with a snap centred in each occupied cell.

  3. **Snaps sit on the chosen cell centres, snaps-down.** Every expected
     snap cell has bed-contact material at z=0 within its 24.8mm
     footprint, the contact count equals the derived snap count, and the
     contact span matches the outermost snap cells — pins the snaps-down
     print orientation, the count, and the 28mm pitch. (Default is one
     lite snap per cell = grid_cols x grid_rows; set snap_every_cell=false
     for a sparse corner-inclusive subset that exports faster — see the
     .scad header.)

  4. **Cartridge slots auto-fill the top face.** Every packed slot centre
     is an open pocket (void above the floor) sitting on solid floor
     material (a cartridge can't drop through the back), and the packed
     count matches the pitch formula (1 x 4 = 4 at the default 2x4 tile,
     4 x 9 = 36 at a full 9x8, with the front figure strip reserved
     before packing).

  5. **Figure holders auto-fill the front face.** Every packed figure
     centre is an open domed pocket bored into the +Y face (void just
     inside the front mouth), and the packed count matches the pitch
     formula (1 at the default 2x4 tile, 5 at a full 9x8). This pins
     presence + count, not a "solid behind" wall.

  6. **Figure pockets are closed blind pockets.** A fig_floor (2mm) solid
     floor separates each figure pocket from the cartridge slot behind —
     asserted arithmetically (the widest cartridge cut stays >= fig_floor
     clear of the pocket back for the default AND off-default grids) and
     on the mesh (the floor behind each exported pocket is solid, no
     break-through). (pst-93r items 1+3.)

  7. **Top-face edges are rounded over.** The +Z outer perimeter edge is
     relieved by the top_round chamfer — the sharp top-outer corner probes
     void while the wall below it stays solid. (pst-93r item 4.)

  8. **Blank mount is a flat solid back.** The mount_type="blank" export is
     a watertight single body with a flat z=0 back and ZERO connector
     features — nothing below the back face, every cell centre solid.

  9. **openConnect mount has one receiver per cell.** The
     mount_type="openconnect" export is a watertight single body whose back
     carries exactly grid_cols x grid_rows openConnect receiver cavities on
     the 28mm cell grid, with solid ribs between adjacent cells. (pst-dg3.)

Claims 8-9 load the mount_type filename-grid siblings
(exports/<stem>-blank.stl / -openconnect.stl) directly, since the
built-in driver only hands the sidecar the default (openGrid) variant.

Uses mesh.contains() and vertex extents only (no shapely/scipy — CI has
neither). Probe frame is world coordinates: the body is lifted body_lift
= snap_h - 0.02 onto the snap tops, so a body-frame height h sits at
world z = body_lift + h.
"""

from __future__ import annotations

from math import floor
from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8
_CONTAINS_VOTES = 5

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"
# openConnect receiver cavity depth (mount_type="openconnect"): the native
# dovetail is 2.70mm deep, so a probe at z=1.2 sits inside every receiver.
_OC_PROBE_Z = 1.2


def _component_count(mesh) -> int:
    """Connected components via union-find over face adjacency (CI has no
    scipy/networkx for trimesh.split) — mirrors the blower-mount sidecar."""
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


def _contains(mesh, pts) -> np.ndarray:
    """Majority vote over _CONTAINS_VOTES independent mesh.contains() calls.

    trimesh casts one random-direction ray per point; with one lite snap
    per cell (the default) a slot floor probe sits directly above the
    welded snap geometry, and a single ray occasionally miscounts the
    surface crossings — a lone contains() flaked ~1/8 runs there (pst-93r).
    Each call re-randomizes, so majority-of-5 collapses that to negligible
    while keeping the exact probe points and pass/fail semantics."""
    pts = np.asarray(pts, dtype=float)
    votes = np.zeros(len(pts), dtype=int)
    for _ in range(_CONTAINS_VOTES):
        votes += mesh.contains(pts).astype(int)
    return votes * 2 > _CONTAINS_VOTES


def _spread(c: int, n: int) -> list[int]:
    """Even, corner-inclusive pick of n cell indices out of c (mirror of
    the .scad `_spread`)."""
    if n >= c:
        return list(range(c))
    if n <= 1:
        return [floor((c - 1) / 2)]
    return [round(k * (c - 1) / (n - 1)) for k in range(n)]


def _derive(p):
    """Reproduce the .scad's derived layout from the params."""
    d = {}
    d["grid_cols"] = int(p.get("grid_cols", 2))
    d["grid_rows"] = int(p.get("grid_rows", 4))
    d["snap_lite"] = bool(p.get("snap_lite", True))
    d["dense"] = bool(p.get("snap_every_cell", True))
    d["body_h"] = float(p.get("body_h", 41))
    d["slot_w"] = float(p.get("slot_w", 52))
    d["slot_l"] = float(p.get("slot_l", 14))
    d["slot_depth"] = float(p.get("slot_depth", 36))
    d["floor_z"] = float(p.get("floor_z", 5))
    d["slot_col_pitch"] = float(p.get("slot_col_pitch", 56))
    d["slot_row_pitch"] = float(p.get("slot_row_pitch", 22))
    d["fig_w"] = float(p.get("fig_w", 43.5))
    d["fig_rect_h"] = float(p.get("fig_rect_h", 9))
    d["fig_depth"] = float(p.get("fig_depth", 10))
    d["fig_pitch"] = float(p.get("fig_pitch", 49.25))
    d["top_round"] = float(p.get("top_round", 1.2))
    d["fig_floor"] = 2.0   # mirror of the .scad constant (pst-93r item 3)

    d["snap_h"] = 3.4 if d["snap_lite"] else 6.8
    d["body_lift"] = d["snap_h"] - 0.02
    d["body_w"] = d["grid_cols"] * _SNAP_PITCH
    d["body_d"] = d["grid_rows"] * _SNAP_PITCH

    # Front figure strip (fig_depth) + a fig_floor solid floor are reserved
    # before packing (items 1+3). Slots are straight-walled (pst-d3x), so
    # the widest cartridge cut is just slot_l deep in Y — no mouth reserve.
    d["cart_depth"] = d["body_d"] - d["fig_depth"] - d["fig_floor"]
    d["n_slot_cols"] = max(0, floor((d["body_w"] - d["slot_w"]) / d["slot_col_pitch"]) + 1)
    d["n_slot_rows"] = max(0, floor((d["cart_depth"] - d["slot_l"]) / d["slot_row_pitch"]) + 1)
    # Phase-lock the column array's first column onto the nearest 2-cell
    # openGrid module centre (snap_pitch*(2k+1) = 28, 84, 140...) — mirror
    # of the .scad slot_x0 (pst-62f). round() matches OpenSCAD's round
    # (ties away from zero); the argument is non-negative here.
    d["slot_module"] = 2 * _SNAP_PITCH
    _sx_centered = (d["body_w"] - (d["n_slot_cols"] - 1) * d["slot_col_pitch"]) / 2
    d["slot_x0"] = _SNAP_PITCH + d["slot_module"] * floor(
        (_sx_centered - _SNAP_PITCH) / d["slot_module"] + 0.5)
    d["slot_y0"] = (d["cart_depth"] - (d["n_slot_rows"] - 1) * d["slot_row_pitch"]) / 2
    d["slot_bottom"] = max(d["floor_z"], d["body_h"] - d["slot_depth"])

    d["n_figs"] = max(0, floor((d["body_w"] - d["fig_w"]) / d["fig_pitch"]) + 1)
    d["fig_x0"] = (d["body_w"] - (d["n_figs"] - 1) * d["fig_pitch"]) / 2

    if d["dense"]:
        d["col_idx"] = list(range(d["grid_cols"]))
        d["row_idx"] = list(range(d["grid_rows"]))
    else:
        d["col_idx"] = _spread(d["grid_cols"], 4)
        d["row_idx"] = _spread(d["grid_rows"], 3)
    d["snap_count"] = len(d["col_idx"]) * len(d["row_idx"])
    return d


def check(ctx):
    failures: list[Failure] = []
    p = as_default_params(ctx["params"])
    d = _derive(p)
    mesh = ctx["stl"]
    lift = d["body_lift"]

    # ctx["stl"] is the DEFAULT (mount_type="opengrid") variant — the
    # filename grid produces no bare <stem>.stl, so check-invariants
    # resolves the default enum value. The claims below are the openGrid
    # back; the blank / openConnect backs are checked on their own
    # exports/<stem>-<value>.stl siblings (mirrors the blower mount).
    failures += expect_connected_solids(ctx, 1)
    failures += _check_footprint(mesh, d)
    failures += _check_snaps(mesh, d)
    failures += _check_slots(mesh, d, lift)
    failures += _check_slot_phase_lock(d)
    failures += _check_figures(mesh, d, lift)
    failures += _check_figure_floor(mesh, d, lift)
    failures += _check_top_roundover(mesh, d, lift)
    failures += _check_blank_variant(ctx["stem"], d)
    failures += _check_openconnect_variant(ctx["stem"], d)
    return failures


def _load_variant(stem: str, value: str, tag: str) -> tuple[object, list[Failure]]:
    """Load exports/<stem>-<value>.stl (a mount_type filename-grid sibling),
    asserting it exists, is watertight, and is a single body."""
    path = EXPORTS_DIR / f"{stem}-{value}.stl"
    if not path.exists():
        return None, [Failure(
            f"{tag}-export",
            f"{path.name} missing — run scripts/export-all.py (the "
            "mount_type filename grid should produce it)",
        )]
    mesh = trimesh.load(str(path))
    failures: list[Failure] = []
    if not bool(mesh.is_watertight):
        failures.append(Failure(f"{tag}-watertight", f"{path.name} is not watertight"))
    n = _component_count(mesh)
    if n != 1:
        failures.append(Failure(
            f"{tag}-topology",
            f"{path.name} has {n} connected components, expected 1",
        ))
    return mesh, failures


def _cell_centres(d) -> list[tuple[float, float]]:
    return [((i + 0.5) * _SNAP_PITCH, (j + 0.5) * _SNAP_PITCH)
            for i in range(d["grid_cols"]) for j in range(d["grid_rows"])]


def _check_blank_variant(stem: str, d) -> list[Failure]:
    """mount_type="blank": a flat solid z=0 back with ZERO connector
    features. The back face sits flat on the bed (no lift, no snaps hanging
    below z=0) and every cell centre is SOLID just inside the back (no
    openConnect cavity, no snap void)."""
    mesh, failures = _load_variant(stem, "blank", "blank")
    if mesh is None:
        return failures
    # No connector geometry protrudes below the flat back face.
    if float(mesh.bounds[0, 2]) < -0.05:
        failures.append(Failure(
            "blank-flat-back",
            f"blank back has material at z={float(mesh.bounds[0, 2]):.2f} "
            "below the flat z=0 face — a connector feature leaked in",
        ))
    # The base is a solid slab: cell centres (and a mid-cell lattice) are
    # solid just above the back face — no receiver cavities were cut.
    centres = _cell_centres(d)
    probes = [[cx, cy, z] for cx, cy in centres for z in (0.4, _OC_PROBE_Z)]
    void = ~_contains(mesh, probes)
    if bool(void.any()):
        bad = [[round(probes[k][0], 1), round(probes[k][1], 1)]
               for k in np.where(void)[0]]
        failures.append(Failure(
            "blank-connector-features",
            f"{int(void.sum())} probe(s) in the blank back are VOID "
            f"(first {bad[:4]}) — the back is not a flat solid slab",
        ))
    return failures


def _check_openconnect_variant(stem: str, d) -> list[Failure]:
    """mount_type="openconnect": one openConnect receiver per cell, on the
    28mm grid. Every cell centre is an open receiver cavity (VOID just
    inside the back face), the cavity count equals grid_cols*grid_rows, and
    the ribs between cells stay solid (receivers don't merge across cells)."""
    mesh, failures = _load_variant(stem, "openconnect", "openconnect")
    if mesh is None:
        return failures
    centres = _cell_centres(d)
    n_expected = d["grid_cols"] * d["grid_rows"]
    # Each cell centre must be an open cavity at the mouth AND deeper in.
    cav = [[cx, cy, z] for cx, cy in centres for z in (0.1, _OC_PROBE_Z)]
    solid = _contains(mesh, cav)
    # Count cells whose BOTH probes read void (a real through-mouth cavity).
    per_cell = (~solid).reshape(len(centres), 2).all(axis=1)
    n_recv = int(per_cell.sum())
    if n_recv != n_expected:
        missing = [[round(centres[k][0], 1), round(centres[k][1], 1)]
                   for k in np.where(~per_cell)[0]]
        failures.append(Failure(
            "openconnect-count",
            f"{n_recv}/{n_expected} openConnect receivers present on the "
            f"cell grid (missing cells {missing[:4]}) — receiver "
            "count/placement drifted",
        ))
    # Ribs at the cell boundaries stay solid (17.2mm-wide receivers centred
    # in 28mm cells leave >=5mm walls; a merge would read void here).
    ribs = []
    for i in range(d["grid_cols"] - 1):
        for cy in {c[1] for c in centres}:
            ribs.append([(i + 1) * _SNAP_PITCH, cy, _OC_PROBE_Z])
    if ribs:
        rib_void = ~_contains(mesh, ribs)
        if bool(rib_void.any()):
            failures.append(Failure(
                "openconnect-rib",
                f"{int(rib_void.sum())} cell-boundary rib probe(s) are VOID "
                "— adjacent openConnect receivers merged across a cell wall",
            ))
    return failures


def _check_slot_phase_lock(d) -> list[Failure]:
    """Cartridge columns are PHASE-LOCKED to the openGrid, not just pitched
    (pst-62f). Two arithmetic claims, for the exported grid AND off-default
    corners (all at the default 56mm = 2-cell pitch):

      (a) Every cartridge column centre lands on a 2-cell openGrid module
          centre (snap_pitch*(2k+1) = 28, 84, 140... over the same grid
          origin the snaps use) — so each 51mm slot sits centred over a
          2x(depth) block of cells, consistent with the back-face snaps.
      (b) The columns clear the reserved front figure strip: the front-most
          cartridge cut stays >= fig_floor clear of the figure-pocket back
          wall (re-asserts non-collision under the new column placement).
    """
    failures: list[Failure] = []
    module = 2 * _SNAP_PITCH
    tol = 1e-6
    grids = [
        (d["grid_cols"], d["grid_rows"]),   # the exported/default grid
        (3, 3), (9, 8), (5, 6),             # off-default corners
    ]
    for gc, gr in grids:
        dd = _derive({"grid_cols": gc, "grid_rows": gr})
        if dd["n_slot_cols"] == 0:
            continue
        # (a) module alignment: |centre - nearest module centre| ~ 0.
        for i in range(dd["n_slot_cols"]):
            cx = dd["slot_x0"] + i * dd["slot_col_pitch"]
            k = round((cx - _SNAP_PITCH) / module)
            nearest = _SNAP_PITCH + module * k
            off = abs(cx - nearest)
            if off > tol:
                failures.append(Failure(
                    "slot-phase-lock",
                    f"grid {gc}x{gr}: cartridge column {i} centre x={cx:.3f} "
                    f"is {off:.3f}mm off the nearest 2-cell module centre "
                    f"{nearest:.1f} (snap_pitch*(2k+1)) — columns are no "
                    "longer phase-locked to the openGrid",
                ))
        # (b) columns clear the reserved figure strip.
        if dd["n_slot_rows"] > 0:
            wall_start = dd["body_d"] - dd["fig_depth"]
            front_cy = dd["slot_y0"] + (dd["n_slot_rows"] - 1) * dd["slot_row_pitch"]
            front_edge = front_cy + dd["slot_l"] / 2
            gap = wall_start - front_edge
            if gap < dd["fig_floor"] - 1e-6:
                failures.append(Failure(
                    "slot-figure-strip-collision",
                    f"grid {gc}x{gr}: front cartridge cut is only {gap:.2f}mm "
                    f"from the figure strip (< {dd['fig_floor']:.1f}mm) — a "
                    "column collides with the reserved figure strip",
                ))
    return failures


def _check_figure_floor(mesh, d, lift) -> list[Failure]:
    """Each figure pocket is a closed BLIND pocket: a solid floor at least
    fig_floor thick separates it from the cartridge slot behind, at every
    grid/param (pst-93r items 1+3). Two claims:

      (a) Arithmetic — the front-most straight-walled cartridge cut stays
          >= fig_floor clear of the figure-strip back wall, for the default
          grid AND off-default corners.
      (b) Mesh — the reserved floor directly behind each exported figure
          pocket is solid (no break-through into a slot).
    """
    failures: list[Failure] = []

    # (a) packing arithmetic across grid sizes.
    grids = [
        (d["grid_cols"], d["grid_rows"]),   # the exported/default grid
        (3, 3), (9, 9), (5, 6),             # off-default corners
    ]
    for gc, gr in grids:
        dd = _derive({"grid_cols": gc, "grid_rows": gr})
        if dd["n_slot_rows"] == 0:
            continue
        wall_start = dd["body_d"] - dd["fig_depth"]      # figure-pocket back
        front_cy = dd["slot_y0"] + (dd["n_slot_rows"] - 1) * dd["slot_row_pitch"]
        front_edge = front_cy + dd["slot_l"] / 2
        gap = wall_start - front_edge
        if gap < dd["fig_floor"] - 1e-6:
            failures.append(Failure(
                "figure-floor-thin",
                f"grid {gc}x{gr}: only {gap:.2f}mm between the front "
                f"cartridge cut and the figure-pocket back wall — less than "
                f"the {dd['fig_floor']:.1f}mm solid floor the pocket needs",
            ))

    # (b) the floor behind each exported figure pocket is solid material.
    if d["n_figs"] > 0:
        y = d["body_d"] - d["fig_depth"] - d["fig_floor"] / 2   # mid-floor
        z = lift + d["floor_z"] + d["fig_rect_h"] / 2           # in the pocket
        probes = [[d["fig_x0"] + k * d["fig_pitch"], y, z]
                  for k in range(d["n_figs"])]
        void = ~_contains(mesh, probes)
        if bool(void.any()):
            bad = [round(probes[k][0], 1) for k in np.where(void)[0]]
            failures.append(Failure(
                "figure-floor-breakthrough",
                f"{int(void.sum())}/{d['n_figs']} figure pockets have a VOID "
                f"floor behind them (x {bad[:4]}) — the pocket opens through "
                "into a cartridge slot",
            ))
    return failures


def _check_top_roundover(mesh, d, lift) -> list[Failure]:
    """The +Z top face's outer perimeter edge is rounded/chamfered over
    (pst-93r item 4): the sharp top-outer corner is relieved. Probes the
    -X mid-edge — a point in the removed wedge just under the top face is
    VOID, while the same column well below the round-over is SOLID.
    """
    r = d["top_round"]
    if r <= 0:
        return []
    top = lift + d["body_h"]
    ymid = d["body_d"] / 2
    x = min(0.4, r / 2)                       # just inside the -X wall
    removed = [x, ymid, top - r * 0.15]       # in the beveled wedge
    kept = [x, ymid, top - r - 1.5]           # full wall, below the bevel
    res = _contains(mesh, [removed, kept])
    failures: list[Failure] = []
    if bool(res[0]):
        failures.append(Failure(
            "top-roundover-missing",
            f"top-outer edge at z={removed[2]:.2f} is still solid — the "
            f"{r}mm top round-over is missing",
        ))
    if not bool(res[1]):
        failures.append(Failure(
            "top-roundover-overcut",
            f"the wall below the round-over (z={kept[2]:.2f}) is void — the "
            "top round-over cut too deep",
        ))
    return failures


def _check_footprint(mesh, d) -> list[Failure]:
    ext = mesh.extents
    if abs(ext[0] - d["body_w"]) > 0.5 or abs(ext[1] - d["body_d"]) > 0.5:
        return [Failure(
            "cell-footprint",
            f"footprint {ext[0]:.1f} x {ext[1]:.1f}mm != the derived cell "
            f"grid {d['grid_cols']}x{d['grid_rows']} * 28 = "
            f"{d['body_w']:.0f} x {d['body_d']:.0f}mm — the body is no "
            "longer an integer openGrid grid",
        )]
    return []


def _check_snaps(mesh, d) -> list[Failure]:
    # The default (dense) layout is exactly one lite snap per cell.
    if d["dense"] and d["snap_count"] != d["grid_cols"] * d["grid_rows"]:
        return [Failure(
            "snap-count-default",
            f"dense snap count {d['snap_count']} != grid_cols*grid_rows = "
            f"{d['grid_cols'] * d['grid_rows']} — one-per-cell layout "
            "regressed",
        )]
    verts = mesh.vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        return [Failure(
            "orientation",
            "no vertices on z=0; model is not in its snaps-down print "
            "orientation",
        )]
    # Every expected snap cell must own bed-contact material inside its
    # 24.8mm footprint; the count of populated cells is the snap count.
    missing = []
    populated = 0
    for i in d["col_idx"]:
        cx = (i + 0.5) * _SNAP_PITCH
        for j in d["row_idx"]:
            cy = (j + 0.5) * _SNAP_PITCH
            near = contact[
                (np.abs(contact[:, 0] - cx) < _SNAP_W / 2)
                & (np.abs(contact[:, 1] - cy) < _SNAP_W / 2)
            ]
            if len(near):
                populated += 1
            else:
                missing.append((round(cx, 1), round(cy, 1)))
    if missing:
        return [Failure(
            "snap-count",
            f"{len(missing)} expected snap cell(s) have no z=0 contact "
            f"(first {missing[:4]}); {populated}/{d['snap_count']} present "
            "— snap placement drifted",
        )]
    # Outer span pins the pitch and that no stray contact bled outside.
    span_x = contact[:, 0].max() - contact[:, 0].min()
    span_y = contact[:, 1].max() - contact[:, 1].min()
    want_x = (max(d["col_idx"]) - min(d["col_idx"])) * _SNAP_PITCH + _SNAP_W
    want_y = (max(d["row_idx"]) - min(d["row_idx"])) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.6 or abs(span_y - want_y) > 0.6:
        return [Failure(
            "snap-span",
            f"bed contact spans {span_x:.1f} x {span_y:.1f}mm but the snap "
            f"cells should span {want_x:.1f} x {want_y:.1f}mm on the 28mm "
            "pitch",
        )]
    return []


def _check_slots(mesh, d, lift) -> list[Failure]:
    if d["n_slot_cols"] == 0 or d["n_slot_rows"] == 0:
        return []
    # Floor solidity is sampled at FIVE points spread across each pocket
    # footprint, not one at the centre: a single floor probe can sit
    # directly above a snap where the random-ray contains() is *biased*
    # (majority-of-votes can't rescue a biased point), but the five points
    # sit over different snap/non-snap regions, so a genuinely floorless
    # pocket reads all-void while a lone biased point cannot flip the
    # verdict. A pocket "has floor" if >= 3 of its 5 points are solid.
    fz = lift + max(0.5, d["floor_z"] - 2.5)
    ox, oy = d["slot_w"] / 4, d["slot_l"] / 4
    floor_offsets = [(0, 0), (ox, oy), (-ox, oy), (ox, -oy), (-ox, -oy)]
    void_probes, floor_probes = [], []
    for i in range(d["n_slot_cols"]):
        cx = d["slot_x0"] + i * d["slot_col_pitch"]
        for j in range(d["n_slot_rows"]):
            cy = d["slot_y0"] + j * d["slot_row_pitch"]
            void_probes.append([cx, cy, lift + d["slot_bottom"] + 3.0])
            floor_probes.append([[cx + dx, cy + dy, fz] for dx, dy in floor_offsets])
    failures = []
    solid_in_void = _contains(mesh, void_probes)
    if bool(solid_in_void.any()):
        bad = [void_probes[k][:2] for k in np.where(solid_in_void)[0]]
        failures.append(Failure(
            "cartridge-slots",
            f"{int(solid_in_void.sum())}/{len(void_probes)} cartridge slot "
            f"centres are solid, not open pockets (first {bad[:4]}) — "
            "auto-fill count/placement regressed",
        ))
    flat = np.array(floor_probes).reshape(-1, 3)
    solid = _contains(mesh, flat).reshape(len(floor_probes), len(floor_offsets))
    floorless = solid.sum(axis=1) < 3
    if bool(floorless.any()):
        bad = [void_probes[k][:2] for k in np.where(floorless)[0]]
        failures.append(Failure(
            "slot-floor",
            f"{int(floorless.sum())} cartridge pocket(s) have no floor "
            f"beneath them (first {bad[:4]}) — a cartridge would drop "
            "through to the wall face",
        ))
    return failures


def _check_figures(mesh, d, lift) -> list[Failure]:
    # Each packed figure centre must be an open pocket in the +Y face:
    # probe just inside the front mouth, up in the dome. (No "solid
    # behind" probe — with the figure strip now reserved, the front
    # cartridge row sits fig_depth + wall clearance behind the +Y edge;
    # and with fig_depth << body_d a figure cannot bore through the tray.
    # Presence + count is what this pins.)
    if d["n_figs"] == 0:
        return []
    z = lift + d["floor_z"] + max(2.0, d["fig_w"] / 4)  # up inside the dome
    void_probes = [
        [d["fig_x0"] + k * d["fig_pitch"], d["body_d"] - 3.0, z]
        for k in range(d["n_figs"])
    ]
    solid = _contains(mesh, void_probes)
    if bool(solid.any()):
        bad = [round(void_probes[k][0], 1) for k in np.where(solid)[0]]
        return [Failure(
            "figure-holders",
            f"{int(solid.sum())}/{d['n_figs']} figure pockets are solid at "
            f"the front face (x {bad[:4]}) — auto-fill count/placement "
            "regressed",
        )]
    return []
