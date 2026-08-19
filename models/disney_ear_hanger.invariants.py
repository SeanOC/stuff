"""Invariants for the vendored Disney ear hanger (st-w2g / pst-3tum).

The saddle is externally-authored (MakerWorld, CC BY-NC-SA 4.0); we
don't claim its geometry, so the DEFAULT (mount_type=tab) variant is
pinned only for single-solid topology plus the built-ins (watertight,
orphan-fragment, triangle ceiling, PRINT_ANCHOR_BBOX drift). The house
contribution this file guards is the mount_type fan-out (pst-3tum): the
openGrid and Multiconnect backers that replace the tab must each fuse to
the saddle as one printable solid, sit grid-aligned on the panel plane,
and — for openGrid — carry their directional snaps' strong nub UP the
wall so the saddle's cantilever lever-out bears on the rigid hook, not
the flexy click side.

FRAMES. The .scad prints every variant with `translate([seat_x,0,seat_z])
rotate([0,-90,0])`, i.e. body (X out of wall, +Y across, +Z up the wall)
-> print (build +Z up). `_body_frame()` undoes that so the mount probes
read in the body frame the backer is placed in. The default-variant mesh
in `ctx` is mount_type=tab; the two backer variants are loaded from their
own filename-grid exports.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure, as_default_params, expect_connected_solids

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"

# Mount hardware constants — mirror of the .scad Derived block; keep in step.
_SNAP_PITCH = 28.0
_SNAP_W = 24.8
_WELD = 0.02
_MC_THICKNESS = 6.5
_MC_WELD = 0.4
_PLATE_T = 4.0
_MIN_WALL = 2.4
_SADDLE_ACROSS = 65.0
_SADDLE_UP = 19.0
_WELD_EMBED = 2.0
_SADDLE_UP_CENTER = 12.6
# Directional nub probe: radius at which the strong front nub is solid but
# the other three nubs are air, at the nub band's mid-height above the
# panel (adapted from apple_tv_4th_gen_holder's check #5).
_NUB_PROBE_R = 13.0
_NUB_PROBE_Z = 4.2
_CONTACT_EPS = 0.6


def _variant_geom(hanger_length, width_units, height_units, mount_type):
    """Mirror the .scad's mount derivation for one variant."""
    snap_h = 6.8  # full snaps only (invariants render defaults, snap_lite=False)
    units_w = max(int(width_units),
                  math.ceil((_SADDLE_ACROSS + 2 * _MIN_WALL) / _SNAP_PITCH))
    units_h = max(int(height_units),
                  math.ceil((_SADDLE_UP + 2 * _MIN_WALL) / _SNAP_PITCH))
    W = units_w * _SNAP_PITCH
    H = units_h * _SNAP_PITCH
    plate_z0 = (_MC_THICKNESS - _MC_WELD) if mount_type == "multiconnect" \
        else (snap_h - _WELD)
    plate_top = plate_z0 + _PLATE_T
    wall_face_x = -(hanger_length / 2 + 5)
    plate_front_x = wall_face_x + _WELD_EMBED
    mount_tx = plate_front_x - plate_top
    mount_tz = _SADDLE_UP_CENTER - H / 2
    seat_z = -mount_tx
    seat_x = _SADDLE_UP_CENTER
    return dict(units_w=units_w, units_h=units_h, W=W, H=H,
                mount_tx=mount_tx, mount_tz=mount_tz,
                seat_x=seat_x, seat_z=seat_z,
                saddle_front_x=hanger_length / 2 + 5)


def _body_frame(mesh, seat_x, seat_z):
    """Undo the print transform: body = Ry(+90) . (print - [seat_x,0,seat_z])."""
    m = mesh.copy()
    m.apply_translation([-seat_x, 0.0, -seat_z])
    m.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2, [0, 1, 0]))
    return m


def _inside(mesh, points):
    """Majority-voted containment — trimesh.contains flakes near snap geometry."""
    offsets = [(0, 0, 0), (0.15, 0, 0), (-0.15, 0, 0),
               (0, 0.15, 0), (0, -0.15, 0)]
    base = np.array(points, dtype=float)
    votes = np.zeros(len(points), dtype=int)
    for off in offsets:
        votes += mesh.contains(base + np.array(off)).astype(int)
    return votes * 2 > len(offsets)


def _components(mesh) -> int:
    """Connected components via union-find over face adjacency.

    trimesh.split needs scipy/networkx which CI doesn't have; this
    mirrors scripts/check-invariants.py's built-in approach (and the
    sibling mount sidecars, e.g. apple_tv_4th_gen_holder).
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


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    # --- Default variant (mount_type=tab): the shipped saddle + fin. ---
    failures.extend(expect_connected_solids(ctx, 1))

    hanger_length = float(p.get("hangerLength", 28))
    width_units = int(p.get("width_units", 2))
    height_units = int(p.get("height_units", 2))
    stem = ctx["stem"]

    # --- Backer variants: openGrid + Multiconnect, each its own export. ---
    for mount_type in ("opengrid", "multiconnect"):
        g = _variant_geom(hanger_length, width_units, height_units, mount_type)
        path = EXPORTS_DIR / f"{stem}-{mount_type}.stl"
        if not path.exists():
            failures.append(Failure(
                f"{mount_type}-export",
                f"{path.name} missing — run scripts/export-all.py "
                "(the mount_type filename grid should produce it)",
            ))
            continue
        mesh = trimesh.load(str(path), force="mesh")

        if not bool(mesh.is_watertight):
            failures.append(Failure(
                f"{mount_type}-watertight", f"{path.name} is not watertight"))
        n = _components(mesh)
        if n != 1:
            failures.append(Failure(
                f"{mount_type}-topology",
                f"{path.name} has {n} connected components, expected 1 — the "
                "backer is not welded to the saddle (a smaller weld_embed or a "
                "moved plate breaks the fusion first)",
            ))

        # Footprint = whole openGrid tiles. Print frame: the plate lies flat
        # on the bed, so its in-plane dims are build-X (= body up-wall, H) and
        # build-Y (= body across, W).
        ext = mesh.bounds[1] - mesh.bounds[0]
        if abs(ext[0] - g["H"]) > 0.5 or abs(ext[1] - g["W"]) > 0.5:
            failures.append(Failure(
                f"{mount_type}-footprint",
                f"backer plate reads {ext[0]:.1f} x {ext[1]:.1f}mm != "
                f"{g['units_h']}x{g['units_w']} openGrid tiles "
                f"({g['H']:.1f} x {g['W']:.1f}mm) — off the 28mm grid",
            ))

        # Into the body frame for the wall-end probes.
        bm = _body_frame(mesh, g["seat_x"], g["seat_z"])
        bext = bm.bounds

        # Panel plane (snap/slot faces) sits at the most -X face = mount_tx.
        if abs(bext[0][0] - g["mount_tx"]) > 0.6:
            failures.append(Failure(
                f"{mount_type}-panel-plane",
                f"panel face at body x={bext[0][0]:.1f} != mount_tx="
                f"{g['mount_tx']:.1f} — the print-frame rotation in the .scad "
                "no longer matches _body_frame(), or the backer moved",
            ))
            continue

        # Saddle preserved: the arch still reaches its front at x = hL/2+5.
        if abs(bext[1][0] - g["saddle_front_x"]) > 1.0:
            failures.append(Failure(
                f"{mount_type}-saddle",
                f"saddle front at body x={bext[1][0]:.1f} != "
                f"{g['saddle_front_x']:.1f} — the saddle was altered or "
                "dropped (the backer must ADD to it, not replace it)",
            ))

        # Full grid — a snap in every tile (see grid_snaps() in the .scad).
        centres = [((cx - (g["units_w"] - 1) / 2) * _SNAP_PITCH,
                    (ry + 0.5) * _SNAP_PITCH + g["mount_tz"])
                   for cx in range(g["units_w"]) for ry in range(g["units_h"])]

        if mount_type == "opengrid":
            # Panel-contact patch spans exactly the corner-snap grid.
            v = bm.vertices
            contact = v[v[:, 0] < g["mount_tx"] + _CONTACT_EPS]
            if len(contact):
                span_y = contact[:, 1].max() - contact[:, 1].min()
                span_z = contact[:, 2].max() - contact[:, 2].min()
                want_y = (g["units_w"] - 1) * _SNAP_PITCH + _SNAP_W
                want_z = (g["units_h"] - 1) * _SNAP_PITCH + _SNAP_W
                if abs(span_y - want_y) > 0.6 or abs(span_z - want_z) > 0.6:
                    failures.append(Failure(
                        "opengrid-snapgrid",
                        f"panel contact spans {span_y:.1f} x {span_z:.1f}mm "
                        f"but a {g['units_w']}x{g['units_h']} snap grid should "
                        f"span {want_y:.1f} x {want_z:.1f}mm — pitch or snap "
                        "count drifted",
                    ))
            else:
                failures.append(Failure(
                    "opengrid-snapgrid",
                    "no vertices on the panel plane — snaps missing or frame "
                    "mismatch",
                ))

            # Strong nub UP the wall (+Z body): solid at +Z of each snap
            # centre, air at -Z (the flexy click side).
            xr = g["mount_tx"] + _NUB_PROBE_Z
            strong = _inside(bm, [[xr, cy, cz + _NUB_PROBE_R]
                                  for cy, cz in centres])
            click = _inside(bm, [[xr, cy, cz - _NUB_PROBE_R]
                                 for cy, cz in centres])
            bad = [centres[i] for i in range(len(centres))
                   if not (strong[i] and not click[i])]
            if bad:
                failures.append(Failure(
                    "opengrid-snap-direction",
                    f"{len(bad)} of {len(centres)} snaps are not directional-"
                    f"with-strong-nub-up: a probe {_NUB_PROBE_R}mm from a snap "
                    "centre must be solid at +Z (the 0.8mm front hook, up the "
                    "wall) and air at -Z (the 0.4mm click side). The saddle's "
                    f"cantilever levers the top row out. First offender {bad[0]}",
                ))

    return failures
