"""Invariants for the Apple TV 4th-gen openGrid cradle (pst-hn2).

Built-ins (watertight, orphan fragments, triangle ceiling,
PRINT_ANCHOR_BBOX drift, preset validity) cover the mesh basics. The
extras here pin the claims this model exists for:

  1. **One welded solid.** The snaps carry the sibling models'
     root-fillet shims; if the QuackWorks or BOSL2 pin moves and the
     shims stop landing inside the click nubs, the component count
     breaks first.

  2. **Grid-aligned footprint.** The plate is a whole number of 28mm
     openGrid tiles on both axes, so the mounted holder lines up with
     the panel. Tile counts auto-grow past the `*_units` minimums when
     the device dimensions demand it — this recomputes that rule and
     fails if the plate drifts off it.

  3. **Snap array on the 28mm pitch, spanning the corner tiles.** The
     bed-contact patch (z ~ 0) must span exactly (units - 1) * 28 +
     24.8 per axis. A drifted pitch or a snap that moved off its corner
     tile changes this span, and contact existing at z=0 at all proves
     the snaps-down print orientation.

  4. **Directional snaps, strong nub UP the wall.** The whole mount
     depends on this: the tray cantilevers a 425g device, so the
     lever-out load must bear on the rigid 0.8mm front hook, not the
     0.4mm flexy click side. The front nub protrudes measurably further
     than the other three (13.1mm vs 12.3-12.7mm off the shipped mesh),
     so a radial probe at 13.0mm from each snap centre must hit solid
     at +Y and air at -Y. A snap rotated the wrong way inverts that
     pair. Full-depth snaps only — the lite variant has no nub band at
     this height.

  5. **The device envelope is actually clear.** A grid spanning the
     full device_w x 35mm x device_d box the holder claims to hold must
     be entirely OUTSIDE the solid. This is what catches a pocket that
     silently shrank, a rib or lead-in that grew into the device, or an
     export that dropped the cavity cut.

  6. **The front lip retains.** Material must stand above the pocket
     floor just forward of the pocket, or the device slides straight
     out of a cantilevered tray. Probed on the 45deg ramp band.

  7. **The rear port cutout is open and the rib ears are not.** The
     plugs face the wall; if the cutout closes, the holder is unusable
     with a cable attached. The paired ear probe stops that check from
     passing on a rib that vanished entirely (which would let the
     device slide back and foul its own plugs).

  8. **Floor slots open, floor web intact.** Both rows — pocket vents
     (the warm device's only airflow) and plenum cable drops — must be
     through-holes, and the web between neighbours must stay solid: the
     floor is the cantilever's tension face, so slots merging into one
     opening would be a real structural regression.
"""

from __future__ import annotations

import math

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8
# Radius at which the directional front nub is solid but the other three
# nubs are air, measured off the shipped mesh (front nub reaches 13.1mm,
# click side 12.3mm, flanks 12.6mm), at the nub band's mid-height.
_NUB_PROBE_R = 13.0
_NUB_PROBE_Z = 4.2
# Device height is fixed by the model's reason to exist (Apple TV HD is
# 35mm tall); only the plan dimensions are parametric.
_DEVICE_H = 35.0


def _inside(ctx, points):
    """Majority-voted containment.

    trimesh's contains() flakes on points that land near the dense snap
    geometry, so every probe is voted over a small jittered cloud rather
    than trusted as a single ray cast.
    """
    mesh = ctx["stl"]
    offsets = [
        (0.0, 0.0, 0.0),
        (0.15, 0.0, 0.0),
        (-0.15, 0.0, 0.0),
        (0.0, 0.15, 0.0),
        (0.0, -0.15, 0.0),
    ]
    votes = np.zeros(len(points), dtype=int)
    base = np.array(points, dtype=float)
    for off in offsets:
        votes += mesh.contains(base + np.array(off)).astype(int)
    return votes * 2 > len(offsets)


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    failures.extend(expect_connected_solids(ctx, 1))

    device_w = p.get("device_w", 98)
    device_d = p.get("device_d", 98)
    fit_clearance = p.get("fit_clearance", 1)
    floor_t = p.get("floor_t", 3)
    plate_t = p.get("plate_t", 4)
    wall_h = p.get("wall_h", 20)
    rib_h = p.get("rib_h", 8)
    port_gap = p.get("port_gap", 20)
    port_cutout_w = p.get("port_cutout_w", 62)
    slot_count = int(p.get("slot_count", 4))
    slot_w = p.get("slot_w", 9)
    snap_lite = bool(p.get("snap_lite", False))

    # Mirror of the .scad's Derived block — keep the two in step.
    pocket_w = device_w + 2 * fit_clearance
    pocket_d = device_d + 2 * fit_clearance
    body_h = floor_t + wall_h
    units_w = max(int(p.get("width_units", 4)),
                  math.ceil((pocket_w + 2 * 2.4) / _SNAP_PITCH))
    units_h = max(int(p.get("height_units", 2)),
                  math.ceil((body_h + 2) / _SNAP_PITCH))
    snap_h = 3.4 if snap_lite else 6.8
    plate_top = snap_h - 0.02 + plate_t
    rib_e = min(rib_h, wall_h - 2)
    z_rib0 = plate_top + port_gap
    z_rib1 = z_rib0 + rib_e
    z_bend = z_rib1 + pocket_d

    # 2. Footprint = whole openGrid tiles.
    bbox = ctx["bbox_mm"]
    want_w = units_w * _SNAP_PITCH
    want_h = units_h * _SNAP_PITCH
    if abs(bbox[0] - want_w) > 0.5 or abs(bbox[1] - want_h) > 0.5:
        failures.append(Failure(
            "footprint",
            f"bbox {bbox[0]:.1f} x {bbox[1]:.1f}mm != {units_w}x{units_h} "
            f"openGrid tiles ({want_w:.1f} x {want_h:.1f}mm) — the holder "
            f"no longer aligns with the 28mm grid",
        ))

    # 3. Bed contact spans exactly the snap grid.
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
    want_x = (units_w - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (units_h - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"bed contact spans {span_x:.1f} x {span_y:.1f}mm but a "
            f"{units_w}x{units_h} snap grid on the 28mm pitch should span "
            f"{want_x:.1f} x {want_y:.1f}mm — snap count or pitch drifted",
        ))

    # 4. Every snap's strong nub points UP the wall (+Y).
    if not snap_lite:
        cols = [0, units_w - 1] if units_w > 1 else [0]
        rows = [0, units_h - 1] if units_h > 1 else [0]
        centres = [((cx - (units_w - 1) / 2) * _SNAP_PITCH,
                    (ry + 0.5) * _SNAP_PITCH)
                   for cx in cols for ry in rows]
        strong = _inside(ctx, [[cx, cy + _NUB_PROBE_R, _NUB_PROBE_Z]
                               for cx, cy in centres])
        click = _inside(ctx, [[cx, cy - _NUB_PROBE_R, _NUB_PROBE_Z]
                              for cx, cy in centres])
        bad = [centres[i] for i in range(len(centres))
               if not (strong[i] and not click[i])]
        if bad:
            failures.append(Failure(
                "snap_direction",
                f"{len(bad)} of {len(centres)} snaps do not read as "
                f"directional-with-strong-nub-up: a probe {_NUB_PROBE_R}mm "
                f"from the snap centre must be solid at +Y (the 0.8mm front "
                f"hook) and air at -Y (the 0.4mm click side). First offender "
                f"at {bad[0]}. The cantilever load bears on the top row's "
                f"front nub — a rotated snap puts it on the flexy side",
            ))

    # 5. The whole device envelope is clear.
    xs = np.linspace(-device_w / 2, device_w / 2, 9)
    ys = np.linspace(floor_t + 0.2, floor_t + _DEVICE_H - 0.2, 6)
    zs = np.linspace(z_rib1 + 0.2, z_bend - 0.2, 9)
    env = [[x, y, z] for x in xs for y in ys for z in zs]
    hits = _inside(ctx, env)
    if hits.any():
        first = np.array(env)[hits][0]
        failures.append(Failure(
            "device_envelope",
            f"{int(hits.sum())} of {len(env)} probe points inside the "
            f"{device_w:.0f} x {device_d:.0f} x {_DEVICE_H:.0f}mm device "
            f"envelope hit solid material (first at {first[0]:.1f}, "
            f"{first[1]:.1f}, {first[2]:.1f}) — the device no longer fits "
            f"the pocket",
        ))

    # 6. Front lip stands above the pocket floor, probed mid-band on the
    # 45deg ramp 3mm forward of the pocket.
    if not _inside(ctx, [[0, floor_t + 1.5, z_bend + 3]])[0]:
        failures.append(Failure(
            "retaining_lip",
            f"no material at the front lip (0, {floor_t + 1.5:.1f}, "
            f"{z_bend + 3:.1f}) — nothing stops the device sliding out of "
            f"the tray",
        ))

    # 7. Port cutout open, rib ears solid.
    y_rib = floor_t + rib_e / 2
    z_rib = z_rib1 - rib_e / 2
    if _inside(ctx, [[0, y_rib, z_rib]])[0]:
        failures.append(Failure(
            "port_cutout",
            f"the {port_cutout_w:.0f}mm rear port opening is blocked at "
            f"(0, {y_rib:.1f}, {z_rib:.1f}) — the wall-facing HDMI/power "
            f"plugs have nowhere to go",
        ))
    ear_x = pocket_w / 2 - 3
    if not _inside(ctx, [[-ear_x, y_rib, z_rib], [ear_x, y_rib, z_rib]]).all():
        failures.append(Failure(
            "rear_rib",
            f"rear retaining rib missing at x=+-{ear_x:.1f} (y={y_rib:.1f}, "
            f"z={z_rib:.1f}) — the device can slide back into the plenum and "
            f"foul its own plugs",
        ))

    # 8. Both floor slot rows are through-holes; the web between them is
    # still solid.
    if slot_count > 0:
        pitch = pocket_w / slot_count
        eff_w = min(slot_w, pitch - 3)
        if eff_w > 0:
            y_floor = floor_t / 2
            z_vent = (z_rib1 + z_bend) / 2
            z_cable = (plate_top + 3 + z_rib0 - 3) / 2
            centres_x = [(i - (slot_count - 1) / 2) * pitch
                         for i in range(slot_count)]
            blocked = _inside(ctx, [[x, y_floor, z_vent] for x in centres_x])
            if blocked.any():
                failures.append(Failure(
                    "vent_slots",
                    f"{int(blocked.sum())} of {slot_count} pocket vent slots "
                    f"are not open through the floor — the device runs warm "
                    f"and these are its only airflow",
                ))
            if (z_rib0 - 3) - (plate_top + 3) > eff_w / 2 + 2:
                blocked = _inside(ctx, [[x, y_floor, z_cable]
                                        for x in centres_x])
                if blocked.any():
                    failures.append(Failure(
                        "cable_slots",
                        f"{int(blocked.sum())} of {slot_count} plenum cable "
                        f"slots are not open through the floor — the cables "
                        f"cannot route down the wall",
                    ))
            if slot_count > 1 and pitch - eff_w > 1:
                web_x = centres_x[0] + pitch / 2
                if not _inside(ctx, [[web_x, y_floor, z_vent]])[0]:
                    failures.append(Failure(
                        "floor_web",
                        f"floor web at x={web_x:.1f} between two vent slots "
                        f"is not solid — the slots have merged and the "
                        f"cantilevered floor lost its tension face",
                    ))

    return failures
