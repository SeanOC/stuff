"""Invariants for the OpenGrid LED-remote holder (st-vmn, pst-07o).

The holder ships a selectable back mount (`mount_type`, exported as a
separate STL per choice via the filename grid): the original openGrid
snaps (default) or a QuackWorks Multiconnect slot backer as an
alternative for Multiboard rails (pst-07o). With the filename opt-in
there is no bare `exports/led_remote_holder_55x124mm.stl`; the harness
feeds this sidecar the DEFAULT variant — `…-opengrid.stl` — as
ctx["stl"], and the multiconnect variant is loaded from its own file.

Twin sidecar: led_remote_holder_51x84mm.invariants.py stays the shared
snap-mount base; the Multiconnect block below is 55x124-only until
pst-egv ports the toggle to the twin (then this block goes param-driven
across both). Everything above it is still the common, param-driven
snap-mount design.

Built-ins (watertight, orphan fragments, PRINT_ANCHOR_BBOX drift)
cover the mesh basics. The extras here pin the claims this model
exists for:

  1. **One welded solid.** openGridSnap's click nubs are face-contact
     solids that the Manifold backend leaves as detached shells; the
     model adds interior weld shims to fuse them. If the QuackWorks or
     BOSL2 pin moves and the shims stop landing inside the nubs, this
     count breaks first (25 shells instead of 1 at defaults).

  2. **Native print orientation is snaps-down.** The bed-contact patch
     (z ~ 0) must exist and span exactly the snap grid, matching the
     auto-fit formula from the .scad (cols/rows of 24.8mm footprints
     on 28mm pitch inside the plate, 1mm rim reserve).

  3. **At least 2 snaps** (bead requirement) at default dims.

  4. **Retention float stays bounded.** The 45deg lip underside only
     catches the remote's face edge if the lip reaches further than
     the sideways play, i.e. lip_over must exceed 2*side_clearance.

  5. **Multiconnect variant** (exports/…-multiconnect.stl, built by the
     export grid alongside the default): watertight, one connected
     solid, slot channels on the 25 mm Multiconnect pitch that (a) open
     toward the wall face (-Z, the plane the openGrid snaps engage),
     (b) run the load the right way — entry mouths open through the y=0
     (bottom) edge and the closed retention domes cap the top (high y) —
     so the holder slides DOWN onto wall connectors and the remote's
     weight seats into the domes, and (c) leave the inter-slot web
     solid. A 180-deg-flipped backer inverts (b); a collapsed generator
     diff() fills (a).

Uses mesh.contains() and trimesh's numpy ray engine — CI has no
shapely/scipy, hence the local union-find for the variant mesh
component count (mirrors opengrid_bin.invariants).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure, as_default_params, expect_connected_solids

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8

# Multiconnect variant geometry at defaults (outer_w=60.7, plate_len=116).
# The QuackWorks master copy lays floor(outer_w/25)=2 vertical slots on
# the 25 mm pitch, auto-centred on the plate; both the 55x124 and 51x84
# footprints resolve to model x = +/-12.5 (web at x=0). The 6.5 mm slab
# spans z 0..6.5 with the openings at z=0 (the wall face) and the closed
# domes capping the top edge (y -> plate_len).
_MC_PITCH = 25.0
_MC_SLOT_XS = [-12.5, 12.5]  # 25 mm pitch, centred; web at x=0
_MC_THICKNESS = 6.5


def _grid_fit(extent: float) -> int:
    """Mirror of the .scad snap auto-fit: snaps on 28mm pitch with a
    1mm rim reserve per side."""
    return max(1, math.floor((extent - 2 - _SNAP_W) / _SNAP_PITCH) + 1)


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    remote_w = p.get("remote_w", 55)
    remote_h = p.get("remote_h", 124)
    side_clearance = p.get("side_clearance", 0.45)
    wall = p.get("wall", 2.4)
    lip_over = p.get("lip_over", 3)
    plate_len_max = p.get("plate_len_max", 116)

    outer_w = remote_w + 2 * side_clearance + 2 * wall
    plate_len = min(wall + remote_h + 2 * side_clearance, plate_len_max)
    cols = _grid_fit(outer_w)
    rows = _grid_fit(plate_len)

    if cols * rows < 2:
        failures.append(Failure(
            "snaps",
            f"only {cols * rows} snap(s) fit the default plate; the bead "
            f"requires at least 2 on the 28mm openGrid pitch",
        ))

    # Native orientation: snap faces on the bed, patch spanning the grid.
    verts = ctx["stl"].vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "orientation",
            "no vertices on z=0; model is not in its snaps-down print "
            "orientation",
        ))
        return failures

    span_x = contact[:, 0].max() - contact[:, 0].min()
    span_y = contact[:, 1].max() - contact[:, 1].min()
    want_x = (cols - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (rows - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"bed contact spans {span_x:.1f} x {span_y:.1f}mm but the "
            f"{cols}x{rows} snap grid should span {want_x:.1f} x "
            f"{want_y:.1f}mm — snap placement drifted off the auto-fit "
            f"formula",
        ))

    # Retention: the 45deg lip chamfer converges at the walls, so the
    # remote's face edge is caught after ~side_clearance of float —
    # but only while the lip reaches past the sideways play.
    if lip_over <= 2 * side_clearance:
        failures.append(Failure(
            "retention",
            f"lip_over={lip_over}mm <= 2*side_clearance="
            f"{2 * side_clearance}mm; a shifted remote can slip past "
            f"the retaining lip",
        ))

    # 5. Multiconnect variant (separate STL from the filename grid).
    failures.extend(
        _check_multiconnect_variant(ctx["stem"], outer_w, plate_len))

    return failures


def _check_multiconnect_variant(stem: str, want_w: float,
                                want_h: float) -> list[Failure]:
    path = EXPORTS_DIR / f"{stem}-multiconnect.stl"
    if not path.exists():
        return [Failure(
            "multiconnect-export",
            f"{path.name} missing — run scripts/export-all.py "
            "(mount_type filename grid should produce it)",
        )]
    mesh = trimesh.load(str(path))
    failures: list[Failure] = []

    if not bool(mesh.is_watertight):
        failures.append(Failure(
            "multiconnect-watertight", f"{path.name} is not watertight"))
    n = _component_count(mesh)
    if n != 1:
        failures.append(Failure(
            "multiconnect-topology",
            f"{path.name} has {n} connected components, expected 1 — "
            "backer not welded to the plate, or an enclosed void",
        ))

    # Footprint still matches the grid-aligned plate (backer spans it).
    b = mesh.bounds
    ext = b[1] - b[0]
    if abs(ext[0] - want_w) > 0.5 or abs(ext[1] - want_h) > 0.5:
        failures.append(Failure(
            "multiconnect-footprint",
            f"multiconnect bbox {ext[0]:.1f} x {ext[1]:.1f}mm != "
            f"{want_w:.1f} x {want_h:.1f}mm — backer no longer matches "
            "the plate",
        ))

    # (a) Slots exist and open toward the WALL (-Z): the channel is void
    # at the wall-side z (z~1.5) at each 25mm-pitch slot centre, while
    # the slab BACK (z~6) stays solid. A collapsed generator diff()
    # (the BOSL2-inside-union failure mode) fills the channel solid.
    zwall = 1.5
    ymid = want_h * 0.35            # below the domes, in the open channel
    ch_pts = np.array([[x, ymid, zwall] for x in _MC_SLOT_XS])
    ch_solid = mesh.contains(ch_pts)
    if bool(ch_solid.any()):
        bad = [_MC_SLOT_XS[i] for i in np.where(ch_solid)[0]]
        failures.append(Failure(
            "multiconnect-slots",
            f"slot channel probe(s) solid at x={bad} (z={zwall}) — "
            "Multiconnect slots missing (generator diff() collapsed?)",
        ))
    back_pts = np.array([[x, ymid, _MC_THICKNESS - 0.5] for x in _MC_SLOT_XS])
    if not bool(mesh.contains(back_pts).all()):
        failures.append(Failure(
            "multiconnect-backer",
            f"slab back probe (z={_MC_THICKNESS - 0.5}) void — the "
            "Multiconnect backer is missing or thinner than 6.5mm",
        ))

    # (b) Load orientation: entry mouths OPEN through the y=0 (bottom)
    # edge and the closed retention domes cap the TOP (high y) — so the
    # holder slides DOWN onto connectors and the remote's weight seats
    # them into the domes. A 180-deg flip inverts both.
    mouth = mesh.contains(np.array([[x, 1.5, zwall] for x in _MC_SLOT_XS]))
    if bool(mouth.any()):
        solid = [_MC_SLOT_XS[i] for i in np.where(mouth)[0]]
        failures.append(Failure(
            "multiconnect-load-orientation",
            f"slot entry region at y=1.5 is solid at x={solid} — mouths "
            "must open through the y=0 (bottom) edge so the holder slides "
            "DOWN onto connectors; backer looks 180deg off",
        ))
    dome = mesh.contains(np.array([[x, want_h - 3.0, zwall] for x in _MC_SLOT_XS]))
    if not bool(dome.all()):
        void = [_MC_SLOT_XS[i] for i in np.where(~dome)[0]]
        failures.append(Failure(
            "multiconnect-load-orientation",
            f"dome cap at y={want_h - 3.0} is void at x={void} — the "
            "closed retention ends must cap the TOP edge (high y) so the "
            "load seats connectors into the domes; backer 180deg off",
        ))

    # (c) Inter-slot web solid (pins the 25mm pitch: the gap between the
    # two slot channels is backer material, not another slot).
    web = mesh.contains(np.array([[0.0, ymid, zwall]]))
    if not bool(web[0]):
        failures.append(Failure(
            "multiconnect-web",
            f"inter-slot web at x=0 (z={zwall}) is void — slot pitch "
            f"drifted off {_MC_PITCH}mm or an extra slot opened",
        ))

    # Open FRONT still open on this variant too (guards an empty/broken
    # export): a probe in the remote pocket at the plate centre is air.
    pocket = mesh.contains(np.array([[0.0, want_h * 0.75, (b[1][2] + 12) / 2]]))
    if bool(pocket[0]):
        failures.append(Failure(
            "multiconnect-openfront",
            "pocket probe on the multiconnect variant is solid — the "
            "open front / remote pocket is obstructed",
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
