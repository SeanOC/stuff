"""Invariants for the openGrid wall bin (st-3mk).

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
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8


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

    return failures
