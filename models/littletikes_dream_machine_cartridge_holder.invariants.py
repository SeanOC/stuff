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
     print orientation, the count, and the 28mm pitch. (Default is the
     sparse 4x3 corner-inclusive subset; snap_every_cell fills all
     cells but is a browser/preview-only mode — see the .scad header.)

  4. **Cartridge slots auto-fill the top face.** Every packed slot centre
     is an open pocket (void above the floor) sitting on solid floor
     material (a cartridge can't drop through the back), and the packed
     count matches the pitch formula (4 x 10 = 40 at the default grid).

  5. **Figure holders auto-fill the front face.** Every packed figure
     centre is an open domed pocket bored into the +Y face (void just
     inside the front mouth), and the packed count matches the pitch
     formula (5 at the default grid). The front cartridge row sits only
     ~fig_depth behind the +Y edge, so this pins presence + count, not
     a "solid behind" wall.

Uses mesh.contains() and vertex extents only (no shapely/scipy — CI has
neither). Probe frame is world coordinates: the body is lifted body_lift
= snap_h - 0.02 onto the snap tops, so a body-frame height h sits at
world z = body_lift + h.
"""

from __future__ import annotations

from math import floor

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8


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
    d["grid_cols"] = int(p.get("grid_cols", 9))
    d["grid_rows"] = int(p.get("grid_rows", 8))
    d["snap_lite"] = bool(p.get("snap_lite", True))
    d["dense"] = bool(p.get("snap_every_cell", False))
    d["body_h"] = float(p.get("body_h", 41))
    d["slot_w"] = float(p.get("slot_w", 51))
    d["slot_l"] = float(p.get("slot_l", 14))
    d["slot_depth"] = float(p.get("slot_depth", 36))
    d["floor_z"] = float(p.get("floor_z", 5))
    d["slot_col_pitch"] = float(p.get("slot_col_pitch", 60))
    d["slot_row_pitch"] = float(p.get("slot_row_pitch", 22))
    d["fig_w"] = float(p.get("fig_w", 43))
    d["fig_depth"] = float(p.get("fig_depth", 10))
    d["fig_pitch"] = float(p.get("fig_pitch", 49.25))

    d["snap_h"] = 3.4 if d["snap_lite"] else 6.8
    d["body_lift"] = d["snap_h"] - 0.02
    d["body_w"] = d["grid_cols"] * _SNAP_PITCH
    d["body_d"] = d["grid_rows"] * _SNAP_PITCH

    d["n_slot_cols"] = max(0, floor((d["body_w"] - d["slot_w"]) / d["slot_col_pitch"]) + 1)
    d["n_slot_rows"] = max(0, floor((d["body_d"] - d["slot_l"]) / d["slot_row_pitch"]) + 1)
    d["slot_x0"] = (d["body_w"] - (d["n_slot_cols"] - 1) * d["slot_col_pitch"]) / 2
    d["slot_y0"] = (d["body_d"] - (d["n_slot_rows"] - 1) * d["slot_row_pitch"]) / 2
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

    failures += expect_connected_solids(ctx, 1)
    failures += _check_footprint(mesh, d)
    failures += _check_snaps(mesh, d)
    failures += _check_slots(mesh, d, lift)
    failures += _check_figures(mesh, d, lift)
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
    void_probes, floor_probes = [], []
    for i in range(d["n_slot_cols"]):
        cx = d["slot_x0"] + i * d["slot_col_pitch"]
        for j in range(d["n_slot_rows"]):
            cy = d["slot_y0"] + j * d["slot_row_pitch"]
            void_probes.append([cx, cy, lift + d["slot_bottom"] + 3.0])
            floor_probes.append([cx, cy, lift + max(0.5, d["floor_z"] - 2.5)])
    failures = []
    solid_in_void = mesh.contains(np.array(void_probes))
    if bool(solid_in_void.any()):
        bad = [void_probes[k][:2] for k in np.where(solid_in_void)[0]]
        failures.append(Failure(
            "cartridge-slots",
            f"{int(solid_in_void.sum())}/{len(void_probes)} cartridge slot "
            f"centres are solid, not open pockets (first {bad[:4]}) — "
            "auto-fill count/placement regressed",
        ))
    void_floor = ~mesh.contains(np.array(floor_probes))
    if bool(void_floor.any()):
        bad = [floor_probes[k][:2] for k in np.where(void_floor)[0]]
        failures.append(Failure(
            "slot-floor",
            f"{int(void_floor.sum())} cartridge pocket(s) have no floor "
            f"beneath them (first {bad[:4]}) — a cartridge would drop "
            "through to the wall face",
        ))
    return failures


def _check_figures(mesh, d, lift) -> list[Failure]:
    # Each packed figure centre must be an open pocket in the +Y face:
    # probe just inside the front mouth, up in the dome. (No "solid
    # behind" probe — the front cartridge row is only ~fig_depth from the
    # +Y edge so material behind a figure can legitimately be an adjacent
    # slot cavity; and with fig_depth << body_d a figure cannot bore
    # through the tray. Presence + count is what this pins.)
    if d["n_figs"] == 0:
        return []
    z = lift + d["floor_z"] + max(2.0, d["fig_w"] / 4)  # up inside the dome
    void_probes = [
        [d["fig_x0"] + k * d["fig_pitch"], d["body_d"] - 3.0, z]
        for k in range(d["n_figs"])
    ]
    solid = mesh.contains(np.array(void_probes))
    if bool(solid.any()):
        bad = [round(void_probes[k][0], 1) for k in np.where(solid)[0]]
        return [Failure(
            "figure-holders",
            f"{int(solid.sum())}/{d['n_figs']} figure pockets are solid at "
            f"the front face (x {bad[:4]}) — auto-fill count/placement "
            "regressed",
        )]
    return []
