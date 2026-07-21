"""Invariants for the Apple TV 4th-gen VERTICAL openGrid cradle (pst-e1v).

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

  3. **The device is held VERTICALLY.** The bead's headline claim, and
     the one a regression to the old horizontal tray would break
     loudest: total reach off the bed must be exactly the snap stack
     plus plate, back relief, device thickness and lip — i.e. the
     device stands on edge rather than lying in a tray cantilevered
     ~100mm off the panel.

  4. **Snap array on the 28mm pitch, spanning the corner tiles.** The
     bed-contact patch (z ~ 0) must span exactly (units - 1) * 28 +
     24.8 per axis. A drifted pitch or a snap that moved off its corner
     tile changes this span, and contact existing at z=0 at all proves
     the snaps-down print orientation.

  5. **Directional snaps, strong nub UP the wall.** The device hangs
     off the panel, so the lever-out load must bear on the rigid 0.8mm
     front hook, not the 0.4mm flexy click side. The front nub
     protrudes measurably further than the other three (13.1mm vs
     12.3-12.7mm off the shipped mesh), so a radial probe at 13.0mm
     from each snap centre must hit solid at +Y and air at -Y. A snap
     rotated the wrong way inverts that pair. Full-depth snaps only —
     the lite variant has no nub band at this height.

  6. **The device envelope is actually clear.** A grid spanning the
     full device_w (X) x device_h (Y, up the wall) x device_t (Z, off
     the wall) box must be entirely OUTSIDE the solid. This catches a
     pocket that silently shrank, a lip or land that grew into the
     device, or an export that dropped the pocket cut.

  7. **The shelf is under the device, on both sides of the cable
     cutout.** A cradle whose shelf vanished (or whose cable cutout ate
     it) drops a 425g device down the wall.

  8. **The rails retain sideways, and their lips overlap the device's
     front face.** The lip probe sits at a radius INSIDE the device's
     own width, so a lip that shrank below real overlap fails even
     though it still exists. Paired with an air probe on the pocket
     centreline at the same height, so the check cannot pass on a
     pocket that closed over.

  9. **The cable cutout is open, full pocket depth.** Ports face down;
     if the cutout closes there is nowhere for the plug bodies to go
     and the holder is unusable with anything plugged in.

 10. **The back-relief channel is open and the lands are solid.** The
     device is passively cooled through its case — pressed flat against
     the plate it cooks. The two lands hold it off; the channel between
     them is the chimney.

 11. **Plate vent slots are through-holes and the webs between them
     survive.** They open that channel to the panel lattice. Merged
     slots would also mean the cut drifted toward a snap footprint.
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
_MIN_WALL = 2.4
_WELD = 0.02


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
    device_h = p.get("device_h", 98)
    device_t = p.get("device_t", 35)
    fit_clearance = p.get("fit_clearance", 1)
    plate_t = p.get("plate_t", 4)
    shelf_rise = p.get("shelf_rise", 10)
    shelf_t = p.get("shelf_t", 4)
    back_relief = p.get("back_relief", 2)
    lip_reach = p.get("lip_reach", 3)
    land_w = p.get("land_w", 12)
    cable_w = p.get("cable_w", 78)
    cable_x = p.get("cable_x", 0)
    vent_count = int(p.get("vent_count", 3))
    vent_w = p.get("vent_w", 10)
    snap_lite = bool(p.get("snap_lite", False))

    # Mirror of the .scad's Derived block — keep the two in step.
    pocket_w = device_w + 2 * fit_clearance
    pocket_h = device_h + fit_clearance
    pocket_t = device_t + fit_clearance
    units_w = max(int(p.get("width_units", 4)),
                  math.ceil((pocket_w + 2 * _MIN_WALL) / _SNAP_PITCH))
    units_h = max(int(p.get("height_units", 4)),
                  math.ceil((shelf_rise + pocket_h) / _SNAP_PITCH))
    plate_w = units_w * _SNAP_PITCH
    plate_h = units_h * _SNAP_PITCH
    side_wall_t = (plate_w - pocket_w) / 2
    snap_h = 3.4 if snap_lite else 6.8
    plate_z0 = snap_h - _WELD
    plate_top = plate_z0 + plate_t
    land_e = max(0.5, min(land_w, pocket_w / 2 - 5))
    lip_e = max(0.5, min(lip_reach, min(side_wall_t - 1, pocket_w / 2 - 5)))
    z_back = plate_top + back_relief
    z_face = z_back + pocket_t
    z_front = z_face + lip_e
    shelf_t_e = min(shelf_t, shelf_rise)
    y_shelf0 = shelf_rise - shelf_t_e
    cable_w_e = max(0, min(cable_w, pocket_w - 12))
    cable_x_max = max(0, (pocket_w - cable_w_e) / 2 - 6)
    cable_x_e = max(-cable_x_max, min(cable_x, cable_x_max))

    # Reference points inside the pocket, reused by several probes.
    y_mid = shelf_rise + pocket_h / 2
    z_mid = (z_back + z_face) / 2
    y_shelf_mid = y_shelf0 + shelf_t_e / 2

    # 2. Footprint = whole openGrid tiles.
    bbox = ctx["bbox_mm"]
    if abs(bbox[0] - plate_w) > 0.5 or abs(bbox[1] - plate_h) > 0.5:
        failures.append(Failure(
            "footprint",
            f"bbox {bbox[0]:.1f} x {bbox[1]:.1f}mm != {units_w}x{units_h} "
            f"openGrid tiles ({plate_w:.1f} x {plate_h:.1f}mm) — the holder "
            f"no longer aligns with the 28mm grid",
        ))

    # 3. Vertical hold: reach off the panel is the device's THICKNESS.
    if abs(bbox[2] - z_front) > 0.5:
        failures.append(Failure(
            "vertical_hold",
            f"model stands {bbox[2]:.1f}mm off the bed but the vertical "
            f"cradle should be exactly {z_front:.1f}mm (snaps + plate + "
            f"{back_relief:.1f}mm relief + {pocket_t:.1f}mm pocket + "
            f"{lip_e:.1f}mm lip) — the device is no longer held on edge",
        ))

    # 4. Bed contact spans exactly the snap grid.
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

    # 5. Every snap's strong nub points UP the wall (+Y).
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
                f"at {bad[0]}. The hang-off load bears on the top row's "
                f"front nub — a rotated snap puts it on the flexy side",
            ))

    # 6. The whole device envelope is clear, standing on edge.
    xs = np.linspace(-device_w / 2, device_w / 2, 9)
    ys = np.linspace(shelf_rise + 0.3, shelf_rise + device_h - 0.3, 8)
    zs = np.linspace(z_back + 0.3, z_back + device_t - 0.3, 7)
    env = [[x, y, z] for x in xs for y in ys for z in zs]
    hits = _inside(ctx, env)
    if hits.any():
        first = np.array(env)[hits][0]
        failures.append(Failure(
            "device_envelope",
            f"{int(hits.sum())} of {len(env)} probe points inside the "
            f"{device_w:.0f} x {device_h:.0f} x {device_t:.0f}mm vertical "
            f"device envelope hit solid material (first at {first[0]:.1f}, "
            f"{first[1]:.1f}, {first[2]:.1f}) — the device no longer fits "
            f"the cradle",
        ))

    # 7. Shelf ears carry the device either side of the cable cutout.
    # Written out per side rather than mirrored: the cutout can be
    # offset, so the two ears are not the same width.
    cut_l = cable_x_e - cable_w_e / 2
    cut_r = cable_x_e + cable_w_e / 2
    ears = [[(cut_r + pocket_w / 2) / 2, y_shelf_mid, z_mid],
            [(cut_l - pocket_w / 2) / 2, y_shelf_mid, z_mid]]
    solid = _inside(ctx, ears)
    if not solid.all():
        missing = [e for e, ok in zip(ears, solid) if not ok]
        failures.append(Failure(
            "shelf",
            f"the bottom shelf is missing at {missing} — nothing carries "
            f"the device's weight and it drops down the wall",
        ))

    # 8. Side rails, plus lips that actually overlap the device's face.
    rail_x = pocket_w / 2 + side_wall_t / 2
    if not _inside(ctx, [[rail_x, y_mid, z_mid],
                         [-rail_x, y_mid, z_mid]]).all():
        failures.append(Failure(
            "side_rails",
            f"no rail material at x=+-{rail_x:.1f} (y={y_mid:.1f}, "
            f"z={z_mid:.1f}) — the device is not constrained sideways",
        ))
    lip_x = pocket_w / 2 - lip_e + 0.3
    z_lip = z_front - 0.3
    if lip_x < device_w / 2:
        if not _inside(ctx, [[lip_x, y_mid, z_lip],
                             [-lip_x, y_mid, z_lip]]).all():
            failures.append(Failure(
                "retaining_lip",
                f"no lip material at x=+-{lip_x:.1f}, z={z_lip:.1f} — the "
                f"rails no longer overlap the device's front face and it "
                f"can tip out of the cradle",
            ))
    if _inside(ctx, [[cable_x_e, y_mid, z_lip]])[0]:
        failures.append(Failure(
            "pocket_mouth",
            f"solid material on the pocket centreline at z={z_lip:.1f} — "
            f"the cradle mouth has closed over and the device cannot be "
            f"loaded at all",
        ))

    # 9. Cable cutout open through the shelf, full pocket depth.
    cable_probes = [[cable_x_e, y_shelf_mid, z_back + 1],
                    [cable_x_e, y_shelf_mid, z_mid],
                    [cable_x_e, y_shelf_mid, z_face - 1]]
    blocked = _inside(ctx, cable_probes)
    if blocked.any():
        failures.append(Failure(
            "cable_cutout",
            f"the {cable_w_e:.0f}mm bottom cable cutout is blocked at "
            f"{int(blocked.sum())} of {len(cable_probes)} depths — the "
            f"downward-facing HDMI/power/Ethernet plugs have nowhere to go",
        ))

    # 10. Back-relief channel open, lands solid.
    if back_relief >= 1:
        z_relief = plate_top + back_relief / 2
        if _inside(ctx, [[0, y_mid, z_relief]])[0]:
            failures.append(Failure(
                "back_relief",
                f"the air channel behind the device is blocked at "
                f"(0, {y_mid:.1f}, {z_relief:.1f}) — the device would sit "
                f"flat on the plate with no way to shed heat",
            ))
        land_x = pocket_w / 2 - land_e / 2
        if not _inside(ctx, [[land_x, y_mid, z_relief],
                             [-land_x, y_mid, z_relief]]).all():
            failures.append(Failure(
                "back_lands",
                f"no land material at x=+-{land_x:.1f}, z={z_relief:.1f} — "
                f"nothing holds the device off the plate, so the relief "
                f"channel closes as soon as it is loaded",
            ))

    # 11. Plate vent slots: through-holes with surviving webs.
    vent_x_max = (min((units_w - 1) / 2 * _SNAP_PITCH - _SNAP_W / 2 - 2,
                      pocket_w / 2 - land_e - 2)
                  if units_w > 1 else 0)
    vent_y1_raw = ((units_h - 0.5) * _SNAP_PITCH - _SNAP_W / 2 - 2
                   if units_h > 1 else 0)
    vent_y0 = max(0.5 * _SNAP_PITCH + _SNAP_W / 2 + 2, shelf_rise + 2)
    vent_y1 = min(vent_y1_raw, shelf_rise + pocket_h - 2)
    vent_pitch = 2 * vent_x_max / vent_count if vent_count > 0 else 0
    vent_w_e = min(vent_w, vent_pitch - 3) if vent_count > 0 else 0
    vent_ok = (vent_count > 0 and vent_x_max > 6 and vent_w_e > 2
               and (vent_y1 - vent_y0) > 10)
    if vent_ok:
        y_vent = (vent_y0 + vent_y1) / 2
        z_plate = plate_z0 + plate_t / 2
        centres_x = [(i - (vent_count - 1) / 2) * vent_pitch
                     for i in range(vent_count)]
        blocked = _inside(ctx, [[x, y_vent, z_plate] for x in centres_x])
        if blocked.any():
            failures.append(Failure(
                "vent_slots",
                f"{int(blocked.sum())} of {vent_count} plate vent slots are "
                f"not open through the plate — the relief channel has no "
                f"path to the panel lattice",
            ))
        if vent_count > 1 and vent_pitch - vent_w_e > 1:
            web_x = centres_x[0] + vent_pitch / 2
            if not _inside(ctx, [[web_x, y_vent, z_plate]])[0]:
                failures.append(Failure(
                    "vent_web",
                    f"plate web at x={web_x:.1f} between two vent slots is "
                    f"not solid — the slots have merged, which also means "
                    f"the cut has drifted toward the snap footprints",
                ))

    return failures
