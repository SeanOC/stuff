"""Invariants for the openGrid wall bin (st-3mk, pst-uim).

The bin ships a selectable back mount (`mount_type`, exported as a
separate STL per choice via the filename grid): the original directional
openGrid snaps (default) or a QuackWorks Multiconnect slot backer as an
alternative for Multiboard rails (pst-uim). With the filename opt-in
there is no bare `exports/opengrid_bin.stl`; the harness feeds this
sidecar the DEFAULT variant — `opengrid_bin-opengrid.stl` — as
ctx["stl"], and the multiconnect variant is loaded from its own file
below.

Built-ins (watertight, orphan fragments, PRINT_ANCHOR_BBOX drift)
cover the mesh basics. The extras here pin the claims this model
exists for:

  1. **One welded solid.** The snaps carry the ego_lb6500 root-fillet
     shims; if the QuackWorks or BOSL2 pin moves and the shims stop
     landing inside the click nubs, the component count breaks first.

  2. **Grid-aligned footprint.** The bead's core requirement: the
     plate is exactly width_units x height_units openGrid tiles
     (28 mm each), so the mounted bin lines up with the panel.

  3. **Snap array on the 28 mm pitch, one snap per tile.** The
     bed-contact patch (z ~ 0) must span exactly the snap grid:
     (units - 1) * 28 + 24.8 per axis. A drifted pitch or a wrong
     snap count moves this span.

  4. **Wall/floor thickness bounds.** Structural minimums for a
     load-bearing cantilevered bin.

  5. **Open top actually open.** A probe point over the cavity, below
     the wall tops, must be OUTSIDE the solid — and a probe inside
     the floor must be INSIDE — so "open-topped" can't silently
     regress into a capped box (or an empty export).

  6. **Multiconnect variant** (exports/opengrid_bin-multiconnect.stl,
     built by the export grid alongside the default): watertight, one
     connected solid, slot channels on the 25 mm Multiconnect pitch
     that (a) open toward the wall face (-Z, the plane the openGrid
     snaps engage), (b) run the load the right way — entry mouths open
     through the y=0 (down) edge and the closed retention domes cap the
     top (high y) — so the bin slides DOWN onto wall connectors and its
     load seats into the domes (mirrors ego_lb6500's st-0of rule), and
     (c) leave the inter-slot web solid. A 180-deg-flipped backer
     inverts (b); a collapsed generator diff() fills (a).

Uses mesh.contains() and trimesh's numpy ray engine — CI has no
shapely/scipy, hence the local union-find for the variant mesh
component count (mirrors ego_lb6500_blower_mount.invariants).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from scripts.invariants import Failure, as_default_params, expect_connected_solids

MODELS_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = MODELS_DIR.parent / "exports"

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8

# Multiconnect variant geometry at defaults (width_units=2 -> W=56,
# height_units=2 -> H=56). The QuackWorks master copy lays
# floor(W/25)=2 vertical slots on the 25 mm pitch, auto-centred on the
# plate: local centres 15.5 and 40.5, mapped to model x = W/2 - local
# = +/-12.5. The 6.5 mm slab spans z 0..6.5 with the openings at z=0
# (the wall face) and the closed domes capping the top edge (y -> H).
_MC_PITCH = 25.0
_MC_SLOT_XS = [-12.5, 12.5]  # 25 mm pitch, centred; web at x=0
_MC_THICKNESS = 6.5


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    width_units = int(p.get("width_units", 2))
    height_units = int(p.get("height_units", 2))
    depth = p.get("depth", 60)
    wall = p.get("wall", 2.4)
    floor_t = p.get("floor_t", 3)
    plate_t = p.get("plate_t", 4)

    # 2. Footprint = whole openGrid tiles (grid alignment on the wall).
    bbox = ctx["bbox_mm"]
    want_w = width_units * _SNAP_PITCH
    want_h = height_units * _SNAP_PITCH
    if abs(bbox[0] - want_w) > 0.5 or abs(bbox[1] - want_h) > 0.5:
        failures.append(Failure(
            "footprint",
            f"bbox {bbox[0]:.1f} x {bbox[1]:.1f}mm != "
            f"{width_units}x{height_units} openGrid tiles "
            f"({want_w:.1f} x {want_h:.1f}mm) — the bin no longer "
            f"aligns with the 28mm grid",
        ))

    # 3. Bed contact spans exactly the snap grid: one snap per tile on
    # the 28mm pitch. Pins both pitch and count.
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
    want_x = (width_units - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (height_units - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"bed contact spans {span_x:.1f} x {span_y:.1f}mm but a "
            f"{width_units}x{height_units} snap grid on the 28mm pitch "
            f"should span {want_x:.1f} x {want_y:.1f}mm — snap count or "
            f"pitch drifted",
        ))

    # 4. Shell thickness bounds for a cantilevered load-bearing bin.
    if wall < 1.6:
        failures.append(Failure(
            "shell", f"wall={wall}mm < 1.6mm minimum for a wall bin"))
    if floor_t < 2:
        failures.append(Failure(
            "shell", f"floor_t={floor_t}mm < 2mm minimum for a wall bin"))
    if plate_t < 3:
        failures.append(Failure(
            "shell",
            f"plate_t={plate_t}mm < 3mm; the snap plate carries the "
            f"whole cantilever moment"))

    # 5. Open top: probe over the cavity center, well below the wall
    # tops, must be air; a probe inside the floor slab must be solid.
    # Frame: y=0 bin bottom, z=0 bed; plate spans z up to ~6.8+plate_t.
    plate_top = 6.8 + plate_t
    z_mid = (plate_top + (6.8 + depth)) / 2
    cavity_probe = [0.0, want_h * 0.75, z_mid]
    floor_probe = [0.0, 1.0, z_mid]
    inside = ctx["stl"].contains([cavity_probe, floor_probe])
    if inside[0]:
        failures.append(Failure(
            "opentop",
            f"probe {cavity_probe} inside the cavity region is solid — "
            f"the open top / interior is obstructed",
        ))
    if not inside[1]:
        failures.append(Failure(
            "opentop",
            f"probe {floor_probe} inside the floor slab is not solid — "
            f"bin body missing or shifted",
        ))

    # 6. Multiconnect variant (separate STL from the filename grid).
    failures.extend(_check_multiconnect_variant(ctx["stem"], want_w, want_h))

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

    # Footprint still whole openGrid tiles (backer matches the plate).
    b = mesh.bounds
    ext = b[1] - b[0]
    if abs(ext[0] - want_w) > 0.5 or abs(ext[1] - want_h) > 0.5:
        failures.append(Failure(
            "multiconnect-footprint",
            f"multiconnect bbox {ext[0]:.1f} x {ext[1]:.1f}mm != "
            f"{want_w:.1f} x {want_h:.1f}mm — backer no longer matches "
            "the grid-aligned plate",
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

    # (b) Load orientation (mirrors ego_lb6500 st-0of): entry mouths
    # OPEN through the y=0 (down) edge and the closed retention domes
    # cap the TOP (high y). A 180-deg flip inverts both.
    mouth = mesh.contains(np.array([[x, 1.5, zwall] for x in _MC_SLOT_XS]))
    if bool(mouth.any()):
        solid = [_MC_SLOT_XS[i] for i in np.where(mouth)[0]]
        failures.append(Failure(
            "multiconnect-load-orientation",
            f"slot entry region at y=1.5 is solid at x={solid} — mouths "
            "must open through the y=0 (down) edge so the bin slides "
            "DOWN onto connectors; backer looks 180deg off",
        ))
    dome = mesh.contains(np.array([[x, want_h - 3.0, zwall] for x in _MC_SLOT_XS]))
    if not bool(dome.all()):
        void = [_MC_SLOT_XS[i] for i in np.where(~dome)[0]]
        failures.append(Failure(
            "multiconnect-load-orientation",
            f"dome cap at y={want_h - 3.0} is void at x={void} — the "
            "closed retention ends must cap the TOP edge (high y) so "
            "the load seats connectors into the domes; backer 180deg off",
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

    # Open top still open on this variant too (guards an empty/broken
    # export): a probe over the cavity below the wall tops is air.
    cavity = mesh.contains(np.array([[0.0, want_h * 0.75, (b[1][2] + 12) / 2]]))
    if bool(cavity[0]):
        failures.append(Failure(
            "multiconnect-opentop",
            "cavity probe on the multiconnect variant is solid — the "
            "open top / interior is obstructed",
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
