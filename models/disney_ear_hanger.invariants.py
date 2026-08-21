"""Invariants for the vendored Disney ear hanger (st-w2g / pst-3tum / pst-j3ej).

The saddle is externally-authored (MakerWorld, CC BY-NC-SA 4.0); we
don't claim its geometry, so the DEFAULT (mount_type=tab) variant is
pinned only for single-solid topology plus the built-ins (watertight,
orphan-fragment, triangle ceiling, PRINT_ANCHOR_BBOX drift). The house
contribution this file guards is the mount_type fan-out: the openGrid
backer that replaces the tab, and the TWO-PIECE Multiconnect mount
(pst-j3ej) — a slim slot plate with a dovetail rail
(multiconnect_plate) plus the saddle with a matching dovetail socket
(multiconnect_saddle). Each fanned STL must be one printable watertight
solid that seats min-Z on the bed for its own derived print orientation
(no default-only seating), keep the saddle it is built from intact, and
carry its half of the joint (rail undercut / socket undercut) so the two
parts actually mate.

FRAMES. The saddle-bearing variants (tab, opengrid, multiconnect_saddle)
print with `translate([seat_x,0,seat_z]) rotate([0,-90,0])`, i.e. body
(X out of wall, +Y across, +Z up the wall) -> print (build +Z up).
`_body_frame()` undoes that so the mount probes read in the body frame.
multiconnect_plate is a STANDALONE part authored directly in its own
print frame (slab flat, slot face down, dovetail rail up), so it is read
in build coordinates, not body-framed. The default-variant mesh in `ctx`
is mount_type=tab; the other variants load from their filename-grid
exports.
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
_PLATE_T = 4.0
_MIN_WALL = 2.4
_SADDLE_UP = 19.0
_WELD_EMBED = 2.0
_SADDLE_UP_CENTER = 12.6
# Slim Multiconnect slot plate + dovetail joint (pst-j3ej).
_MC_THICKNESS = 6.0
_DT_DEPTH = 4.0
_DT_NECK = 8.0
_DT_TIP = 12.0
_DT_LEN = 24.0
_DOVETAIL_Z = 11.0
_DT_CLEAR = 0.25
# Directional nub probe (opengrid): radius at which the strong front nub is
# solid but the other three nubs are air, at the nub band's mid-height.
_NUB_PROBE_R = 13.0
_NUB_PROBE_Z = 4.2
_CONTACT_EPS = 0.6
# Corner-rounding probe (pst-4g1u): a point _CORNER_AIR mm diagonally inside
# each true rectangle corner must be AIR (rounded), a point _CORNER_SOLID mm
# in must be SOLID.
_CORNER_AIR = 0.4
_CORNER_SOLID = 3.0


def _units(width_units, height_units):
    units_w = max(int(width_units), 1)  # no saddle-spanning floor (pst-gmg0)
    units_h = max(int(height_units),
                  math.ceil((_SADDLE_UP + 2 * _MIN_WALL) / _SNAP_PITCH))
    return units_w, units_h


def _opengrid_geom(hanger_length, width_units, height_units):
    """Mirror the .scad's opengrid mount derivation (body frame)."""
    snap_h = 6.8  # full snaps only (invariants render defaults, snap_lite=False)
    units_w, units_h = _units(width_units, height_units)
    W = units_w * _SNAP_PITCH
    H = units_h * _SNAP_PITCH
    plate_z0 = snap_h - _WELD
    plate_top = plate_z0 + _PLATE_T
    wall_face_x = -(hanger_length / 2 + 5)
    plate_front_x = wall_face_x + _WELD_EMBED
    mount_tx = plate_front_x - plate_top
    mount_tz = _SADDLE_UP_CENTER - H / 2
    return dict(units_w=units_w, units_h=units_h, W=W, H=H,
                plate_z0=plate_z0, plate_top=plate_top,
                mount_tx=mount_tx, mount_tz=mount_tz,
                seat_x=_SADDLE_UP_CENTER, seat_z=-mount_tx,
                wall_face_x=wall_face_x,
                saddle_front_x=hanger_length / 2 + 5)


def _body_frame(mesh, seat_x, seat_z):
    """Undo the print transform: body = Ry(+90) . (print - [seat_x,0,seat_z])."""
    m = mesh.copy()
    m.apply_translation([-seat_x, 0.0, -seat_z])
    m.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2, [0, 1, 0]))
    return m


def _inside(mesh, points):
    """Majority-voted containment — trimesh.contains flakes near thin geometry."""
    offsets = [(0, 0, 0), (0.15, 0, 0), (-0.15, 0, 0),
               (0, 0.15, 0), (0, -0.15, 0)]
    base = np.array(points, dtype=float)
    votes = np.zeros(len(points), dtype=int)
    for off in offsets:
        votes += mesh.contains(base + np.array(off)).astype(int)
    return votes * 2 > len(offsets)


def _air_span_z(mesh, x, y, z0, z1, step=0.2):
    """Span of the AIR interval in z at (x,y) over [z0,z1] — 0 if none."""
    zs = np.arange(z0, z1 + 1e-9, step)
    air = ~_inside(mesh, [[x, y, z] for z in zs])
    zin = zs[air]
    return (zin.max() - zin.min()) if len(zin) else 0.0


def _components(mesh) -> int:
    """Connected components via union-find over face adjacency."""
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


def _load(stem, suffix, key, failures):
    path = EXPORTS_DIR / f"{stem}-{suffix}.stl"
    if not path.exists():
        failures.append(Failure(
            f"{key}-export",
            f"{path.name} missing — run scripts/export-all.py "
            "(the mount_type filename grid should produce it)",
        ))
        return None
    mesh = trimesh.load(str(path), force="mesh")
    if not bool(mesh.is_watertight):
        failures.append(Failure(f"{key}-watertight", f"{path.name} is not watertight"))
    n = _components(mesh)
    if n != 1:
        failures.append(Failure(
            f"{key}-topology",
            f"{path.name} has {n} connected components, expected 1"))
    if abs(mesh.bounds[0][2]) > 0.05:
        failures.append(Failure(
            f"{key}-seat",
            f"{path.name} min build-Z = {mesh.bounds[0][2]:.2f} != 0 — the part "
            "must seat flat on the bed (pst-t9ri: no default-only seating)"))
    return mesh


def _check_opengrid(stem, hanger_length, width_units, height_units, failures):
    g = _opengrid_geom(hanger_length, width_units, height_units)
    mesh = _load(stem, "opengrid", "opengrid", failures)
    if mesh is None:
        return
    bm = _body_frame(mesh, g["seat_x"], g["seat_z"])
    bext = bm.bounds

    # Footprint = whole openGrid tiles, measured on the panel side of the weld.
    panel = bm.vertices[bm.vertices[:, 0] < g["wall_face_x"] - 0.5]
    if len(panel):
        w_meas = panel[:, 1].max() - panel[:, 1].min()
        h_meas = panel[:, 2].max() - panel[:, 2].min()
        if abs(w_meas - g["W"]) > 0.5 or abs(h_meas - g["H"]) > 0.5:
            failures.append(Failure(
                "opengrid-footprint",
                f"backer plate reads {w_meas:.1f} x {h_meas:.1f}mm != "
                f"{g['units_w']}x{g['units_h']} openGrid tiles "
                f"({g['W']:.1f} x {g['H']:.1f}mm) — off the 28mm grid"))
    else:
        failures.append(Failure(
            "opengrid-footprint",
            "no plate vertices on the panel side of the saddle weld"))

    # Uniform rounded corners (pst-4g1u), plate cap layer.
    corners = [(sy * g["W"] / 2, g["mount_tz"] + sz * g["H"])
               for sy in (1, -1) for sz in (0, 1)]
    x_probe = g["mount_tx"] + (g["plate_z0"] + g["plate_top"]) / 2
    near_pts, far_pts = [], []
    for cy, cz in corners:
        iy = -1.0 if cy > 0 else 1.0
        iz = -1.0 if cz > g["mount_tz"] + g["H"] / 2 else 1.0
        near_pts.append([x_probe, cy + iy * _CORNER_AIR, cz + iz * _CORNER_AIR])
        far_pts.append([x_probe, cy + iy * _CORNER_SOLID, cz + iz * _CORNER_SOLID])
    near_solid = _inside(bm, near_pts)
    far_solid = _inside(bm, far_pts)
    sharp = [corners[i] for i in range(4) if near_solid[i] or not far_solid[i]]
    if sharp:
        failures.append(Failure(
            "opengrid-corner-rounding",
            f"{len(sharp)} of 4 plate corners are not rounded (pst-4g1u stray "
            f"post or rounding regressed). First offender (body y,z)={sharp[0]}"))

    # Panel plane at the most -X face = mount_tx.
    if abs(bext[0][0] - g["mount_tx"]) > 0.6:
        failures.append(Failure(
            "opengrid-panel-plane",
            f"panel face at body x={bext[0][0]:.1f} != mount_tx="
            f"{g['mount_tx']:.1f} — print-frame rotation or backer moved"))
        return

    # Saddle preserved: arch still reaches its front.
    if abs(bext[1][0] - g["saddle_front_x"]) > 1.0:
        failures.append(Failure(
            "opengrid-saddle",
            f"saddle front at body x={bext[1][0]:.1f} != "
            f"{g['saddle_front_x']:.1f} — the saddle was altered or dropped"))

    centres = [((cx - (g["units_w"] - 1) / 2) * _SNAP_PITCH,
                (ry + 0.5) * _SNAP_PITCH + g["mount_tz"])
               for cx in range(g["units_w"]) for ry in range(g["units_h"])]

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
                f"panel contact spans {span_y:.1f} x {span_z:.1f}mm but a "
                f"{g['units_w']}x{g['units_h']} snap grid should span "
                f"{want_y:.1f} x {want_z:.1f}mm — pitch or snap count drifted"))
    else:
        failures.append(Failure(
            "opengrid-snapgrid", "no vertices on the panel plane"))

    # Strong nub UP the wall (+Z body).
    xr = g["mount_tx"] + _NUB_PROBE_Z
    strong = _inside(bm, [[xr, cy, cz + _NUB_PROBE_R] for cy, cz in centres])
    click = _inside(bm, [[xr, cy, cz - _NUB_PROBE_R] for cy, cz in centres])
    bad = [centres[i] for i in range(len(centres))
           if not (strong[i] and not click[i])]
    if bad:
        failures.append(Failure(
            "opengrid-snap-direction",
            f"{len(bad)} of {len(centres)} snaps are not directional-with-"
            f"strong-nub-up. First offender {bad[0]}"))


def _check_mc_plate(stem, width_units, height_units, failures):
    """multiconnect_plate: standalone slim slot slab + dovetail rail, read in
    the build (print) frame — slab flat at z[0,mc_thickness], rail up."""
    units_w, units_h = _units(width_units, height_units)
    W, H = units_w * _SNAP_PITCH, units_h * _SNAP_PITCH
    mesh = _load(stem, "multiconnect_plate", "mc_plate", failures)
    if mesh is None:
        return
    ext = mesh.bounds[1] - mesh.bounds[0]

    # Footprint = the W x H slab; total build height = slab + rail.
    if abs(ext[0] - W) > 0.6 or abs(ext[1] - H) > 0.6:
        failures.append(Failure(
            "mc_plate-footprint",
            f"slot slab reads {ext[0]:.1f} x {ext[1]:.1f}mm != {units_w}x"
            f"{units_h} tiles ({W:.1f} x {H:.1f}mm) — off the 28mm grid"))
    want_z = _MC_THICKNESS + _DT_DEPTH
    if abs(ext[2] - want_z) > 0.6:
        failures.append(Failure(
            "mc_plate-thickness",
            f"build height {ext[2]:.2f}mm != slim slab + rail "
            f"({_MC_THICKNESS:.1f}+{_DT_DEPTH:.1f}={want_z:.1f}mm) — the plate is "
            "not the slimmed ~6mm slab or the rail height drifted (pst-j3ej A1)"))

    # Slab really is only mc_thickness thick where there is no rail: probe a
    # near-corner column, clear of the central rail (x~W/2,y~H/2) and the
    # central slot — solid inside the slab, air above mc_thickness.
    cx, cy = W * 0.12, H * 0.12
    if not _inside(mesh, [[cx, cy, _MC_THICKNESS / 2]])[0]:
        failures.append(Failure(
            "mc_plate-thickness",
            "no slab where a corner column was probed — frame/footprint mismatch"))
    elif _inside(mesh, [[cx, cy, _MC_THICKNESS + 1.0]])[0]:
        failures.append(Failure(
            "mc_plate-thickness",
            f"slab is solid above z={_MC_THICKNESS}mm away from the rail — the "
            "slot plate is thicker than the slim ~6mm target (pst-j3ej A1)"))

    # Dovetail rail is a real undercut: at the plate centre the rail is WIDER
    # in Y near its tip than at its base (self-supporting flare that captures
    # pull-out). Measure the solid Y-span at two heights on the rail.
    x0 = W / 2
    def rail_width(zoff):
        z = _MC_THICKNESS + zoff
        ys = np.arange(H / 2 - 10, H / 2 + 10, 0.2)
        solid = _inside(mesh, [[x0, y, z] for y in ys])
        yin = ys[solid]
        return (yin.max() - yin.min()) if len(yin) else 0.0
    w_base = rail_width(0.5)
    w_tip = rail_width(_DT_DEPTH - 0.5)
    if not (w_base > 1 and w_tip > w_base + 1.0):
        failures.append(Failure(
            "mc_plate-rail",
            f"dovetail rail is not an undercut: width at base={w_base:.1f}mm, "
            f"near tip={w_tip:.1f}mm (tip must be clearly wider). The rail "
            "must flare so it captures the socket against pull-out (pst-j3ej)"))
    # Rail runs a finite length along X (the slide axis) ~ dt_len, not the
    # whole plate — so the joint is a fixed interface.
    xs = np.arange(W / 2 - 15, W / 2 + 15, 0.25)
    solid = _inside(mesh, [[x, H / 2, _MC_THICKNESS + _DT_DEPTH / 2] for x in xs])
    xin = xs[solid]
    rail_len = (xin.max() - xin.min()) if len(xin) else 0.0
    if abs(rail_len - _DT_LEN) > 2.0:
        failures.append(Failure(
            "mc_plate-rail",
            f"dovetail rail length {rail_len:.1f}mm != {_DT_LEN:.0f}mm interface "
            "— the fixed-size joint drifted"))


def _check_mc_saddle(stem, hanger_length, failures):
    """multiconnect_saddle: the saddle with a solid wall-end backing and a
    dovetail socket relieved into it, read in the body frame."""
    seat_x, seat_z = _SADDLE_UP_CENTER, hanger_length / 2 + 5.05
    wall_face_x = -(hanger_length / 2 + 5)
    saddle_front_x = hanger_length / 2 + 5
    mesh = _load(stem, "multiconnect_saddle", "mc_saddle", failures)
    if mesh is None:
        return
    bm = _body_frame(mesh, seat_x, seat_z)
    bext = bm.bounds

    # Saddle preserved: the arch still reaches its front at x = hL/2+5.
    if abs(bext[1][0] - saddle_front_x) > 1.0:
        failures.append(Failure(
            "mc_saddle-saddle",
            f"saddle front at body x={bext[1][0]:.1f} != {saddle_front_x:.1f} — "
            "the saddle was altered or dropped (the socket must only RELIEVE it)"))

    # Socket void present in solid backing: air inside the socket, solid on
    # the back wall behind it and in the roof/floor around it.
    x_in = wall_face_x + _DT_DEPTH / 2          # mid-depth, inside the socket
    x_back = wall_face_x + _DT_DEPTH + 1.5      # behind the blind end
    air = _inside(bm, [[x_in, 0, _DOVETAIL_Z]])[0]
    back = _inside(bm, [[x_back, 0, _DOVETAIL_Z]])[0]
    roof = _inside(bm, [[x_in, 0, _DOVETAIL_Z + _DT_TIP / 2 + 2.5]])[0]
    floor = _inside(bm, [[x_in, 0, _DOVETAIL_Z - _DT_TIP / 2 - 2.5]])[0]
    if air:
        failures.append(Failure(
            "mc_saddle-socket",
            "no socket void at the wall-end centre — the dovetail socket is "
            "missing or the wall-end backing was not relieved (pst-j3ej)"))
    if not (back and roof and floor):
        failures.append(Failure(
            "mc_saddle-backing",
            f"the wall-end socket is not embedded in solid backing "
            f"(back={bool(back)} roof={bool(roof)} floor={bool(floor)}) — the "
            "arch is hollow there, so the socket would have nothing to grip "
            "(pst-j3ej: the backing must refill the wall-end channel)"))

    # Socket is a real dovetail undercut: the air channel is WIDER in body-z
    # deeper in (near the blind end) than at the mouth.
    span_mouth = _air_span_z(bm, wall_face_x + 0.6, 0,
                             _DOVETAIL_Z - 9, _DOVETAIL_Z + 9)
    span_deep = _air_span_z(bm, wall_face_x + _DT_DEPTH - 0.4, 0,
                            _DOVETAIL_Z - 9, _DOVETAIL_Z + 9)
    if not (span_mouth > 3 and span_deep > span_mouth + 1.5):
        failures.append(Failure(
            "mc_saddle-socket",
            f"socket is not an undercut: air-span at the mouth={span_mouth:.1f}mm, "
            f"deep={span_deep:.1f}mm (deep must be clearly wider to trap the "
            "rail against pull-out, pst-j3ej)"))


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    # --- Default variant (mount_type=tab): the shipped saddle + fin. ---
    failures.extend(expect_connected_solids(ctx, 1))

    hanger_length = float(p.get("hangerLength", 28))
    width_units = int(p.get("width_units", 1))
    height_units = int(p.get("height_units", 2))
    stem = ctx["stem"]

    # --- Width control must reach the minimal single-tile backer (pst-gmg0). ---
    floor_w = 1
    declared_min_w = ctx["params"].get("width_units", {}).get("min")
    if declared_min_w is not None and int(declared_min_w) != floor_w:
        failures.append(Failure(
            "width-range-min",
            f"width_units @param min={int(declared_min_w)} != the {floor_w}-"
            f"tile structural floor. The minimal backer has no saddle-spanning "
            f"floor (pst-gmg0): pin the @param min to {floor_w} so units_w == "
            f"width_units 1:1 and width=1 is reachable.",
        ))

    # --- The fanned mount variants, each its own export. ---
    _check_opengrid(stem, hanger_length, width_units, height_units, failures)
    _check_mc_plate(stem, width_units, height_units, failures)
    _check_mc_saddle(stem, hanger_length, failures)

    return failures
