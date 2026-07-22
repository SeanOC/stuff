"""Invariants for the Apple TV 4th-gen VERTICAL openGrid cradle (pst-e1v).

FRAMES (pst-mfy). The .scad authors its geometry in the MOUNT frame — X
across the wall, +Y up the wall, +Z out of the panel — and rotates the
assembly by rotate([90, 0, 0]) at the end so the exported STL is in the
PRINT frame, build axis +Z, bed at z = 0, like every sibling model. The
probes below are all written in the MOUNT frame, because that is the
frame the design reasons in; `_mount_frame()` rotates the loaded mesh
back into it once, and everything downstream uses that. The one check
that cares about the print frame — the overhang scan — says so.

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
     loudest: total reach off the PANEL must be exactly the snap stack
     plus plate, back relief, device thickness and lip — i.e. the
     device stands on edge rather than lying in a tray cantilevered
     ~100mm off the panel.

  4. **Snap array on the 28mm pitch, spanning the corner tiles.** The
     panel-plane patch (mount z ~ 0) must span exactly (units - 1) * 28
     + 24.8 per axis. A drifted pitch or a snap that moved off its
     corner tile changes this span.

 12. **It stands on the plate's bottom edge.** The print orientation
     claim (pst-mfy), checked two ways. The bed plane (mount y = 0)
     must carry BOTH the plate's bottom edge and the two shelf ears —
     a shelf that drifts back up the wall is the single biggest
     overhang this design can grow. And a slicer-style scan of the
     exported mesh in the PRINT frame must find no unsupported
     downward face outside the four snap footprints: the cradle is a
     constant cross-section sweep along the build axis, so anything
     else appearing there means a feature started in mid-air.

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

 11. **The plate vent window is open through the plate, and stops
     clear of the snap rows and the lands.** It opens that channel to
     the panel lattice, and it is also the model's main lightening cut
     (pst-mfy), so it is the cut most likely to be grown carelessly. A
     window that reached a snap row would undercut a snap footprint;
     one that reached past a land's inner edge would open into a rail
     instead of into the relief channel.
"""

from __future__ import annotations

import math

import numpy as np
import trimesh

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
# Overhang scan (print frame): a face is flagged when it faces down the
# build axis and is tilted more than this far from vertical. 50deg
# rather than the usual 45 so the model's many exactly-45deg
# self-supporting ramps sit clear of the threshold instead of on it —
# at 45 they flip in and out on the last bit of float.
_OVERHANG_FROM_VERTICAL_DEG = 50.0
_OVERHANG_AREA_CEILING_MM2 = 1100.0


def _mount_frame(ctx):
    """A ctx whose mesh is rotated from the PRINT frame to the MOUNT frame.

    The .scad ends with rotate([90, 0, 0]), i.e. mount (x, y, z) ->
    print (x, -z, y). This undoes it, so every probe below can be
    written in the frame the design reasons in.
    """
    m = ctx["stl"].copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(
        -math.pi / 2, [1, 0, 0]))
    out = dict(ctx)
    out["stl"] = m
    return out


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
    plate_t = p.get("plate_t", 3)
    shelf_t = p.get("shelf_t", 4)
    back_relief = p.get("back_relief", 2)
    lip_reach = p.get("lip_reach", 3)
    land_w = p.get("land_w", 12)
    cable_w = p.get("cable_w", 78)
    cable_x = p.get("cable_x", 0)
    vent_margin = p.get("vent_margin", 2)
    snap_lite = bool(p.get("snap_lite", False))

    # Mirror of the .scad's Derived block — keep the two in step.
    pocket_w = device_w + 2 * fit_clearance
    pocket_h = device_h + fit_clearance
    pocket_t = device_t + fit_clearance
    units_w = max(int(p.get("width_units", 4)),
                  math.ceil((pocket_w + 2 * _MIN_WALL) / _SNAP_PITCH))
    units_h = max(int(p.get("height_units", 4)),
                  math.ceil((shelf_t + pocket_h) / _SNAP_PITCH))
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
    # The shelf sits ON the plate's bottom edge (pst-mfy): underside at
    # y = 0, device resting on top at y = shelf_t.
    y_shelf = shelf_t
    y_cradle_top = y_shelf + pocket_h
    cable_w_e = max(0, min(cable_w, pocket_w - 12, pocket_w - 2 * land_e))
    cable_x_max = max(0, (pocket_w - cable_w_e) / 2 - 6)
    cable_x_e = max(-cable_x_max, min(cable_x, cable_x_max))

    # Everything below probes the MOUNT frame; the export is rotated.
    print_ctx = ctx
    ctx = _mount_frame(ctx)

    # Reference points inside the pocket, reused by several probes.
    y_mid = y_shelf + pocket_h / 2
    z_mid = (z_back + z_face) / 2
    y_shelf_mid = y_shelf / 2

    # 2. Footprint = whole openGrid tiles. The export is in the print
    # frame, so the plate's two in-plane dimensions are bbox X and Z.
    bbox = ctx["bbox_mm"]
    if abs(bbox[0] - plate_w) > 0.5 or abs(bbox[2] - plate_h) > 0.5:
        failures.append(Failure(
            "footprint",
            f"plate reads {bbox[0]:.1f} x {bbox[2]:.1f}mm != {units_w}x"
            f"{units_h} openGrid tiles ({plate_w:.1f} x {plate_h:.1f}mm) — "
            f"the holder no longer aligns with the 28mm grid",
        ))

    # 3. Vertical hold: reach off the panel is the device's THICKNESS.
    # Print-frame Y is the wall normal.
    if abs(bbox[1] - z_front) > 0.5:
        failures.append(Failure(
            "vertical_hold",
            f"model reaches {bbox[1]:.1f}mm off the panel but the vertical "
            f"cradle should be exactly {z_front:.1f}mm (snaps + plate + "
            f"{back_relief:.1f}mm relief + {pocket_t:.1f}mm pocket + "
            f"{lip_e:.1f}mm lip) — the device is no longer held on edge",
        ))

    # 4. The panel-contact patch spans exactly the snap grid.
    verts = ctx["stl"].vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "orientation",
            "no vertices on the panel plane (mount z=0); the snap faces "
            "have moved off the grid, or the print-frame rotation in the "
            ".scad no longer matches _mount_frame()",
        ))
        return failures
    span_x = contact[:, 0].max() - contact[:, 0].min()
    span_y = contact[:, 1].max() - contact[:, 1].min()
    want_x = (units_w - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (units_h - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"panel contact spans {span_x:.1f} x {span_y:.1f}mm but a "
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
    ys = np.linspace(y_shelf + 0.3, y_shelf + device_h - 0.3, 8)
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

    # 11. Plate vent window: open through the plate, and stopping clear
    # of both snap rows and both lands.
    vent_x_max = (pocket_w / 2 - land_e - vent_margin) if units_w > 1 else 0
    vent_y0 = max(0.5 * _SNAP_PITCH + _SNAP_W / 2 + vent_margin,
                  y_shelf + vent_margin)
    vent_y1 = (min((units_h - 0.5) * _SNAP_PITCH - _SNAP_W / 2 - vent_margin,
                   y_cradle_top - vent_margin)
               if units_h > 1 else 0)
    vent_flat = min(2 * vent_x_max, 20)
    vent_roof = vent_x_max - vent_flat / 2
    vent_ok = vent_x_max > 6 and (vent_y1 - vent_roof - vent_y0) > 4
    if vent_ok:
        z_plate = plate_z0 + plate_t / 2
        # Probe the window's own body, not its gable, so the check does
        # not depend on where the 45deg roof starts.
        y_body = (vent_y0 + (vent_y1 - vent_roof)) / 2
        if _inside(ctx, [[0, y_body, z_plate]])[0]:
            failures.append(Failure(
                "vent_window",
                f"the plate vent window is not open through the plate at "
                f"(0, {y_body:.1f}, {z_plate:.1f}) — the relief channel has "
                f"no path to the panel lattice",
            ))
        # The window must not have eaten into a snap row or a land: the
        # plate stays solid just outside each of its four edges.
        margins = {
            "below the bottom snap row": [0, vent_y0 - 1, z_plate],
            "above the top snap row": [0, vent_y1 + 1, z_plate],
            "inboard of the +X land": [vent_x_max + 1, y_body, z_plate],
            "inboard of the -X land": [-vent_x_max - 1, y_body, z_plate],
        }
        gone = [name for name, pt in margins.items()
                if not _inside(ctx, [pt])[0]]
        if gone:
            failures.append(Failure(
                "vent_window_margin",
                f"plate is not solid {', '.join(gone)} — the vent window has "
                f"grown past the {vent_margin:.1f}mm margin it is supposed to "
                f"keep, which either undercuts a snap footprint or opens the "
                f"window into a rail instead of the relief channel",
            ))

    # The vent gable's apex is a deliberate flat bridge, not a support
    # case: at most vent_flat wide through the plate's thickness.
    bridge_allow = vent_flat * plate_t if vent_ok else 0.0

    failures.extend(_check_print_orientation(
        print_ctx, units_w, units_h, plate_z0, cable_x_e, cable_w_e,
        bridge_allow))

    return failures


def _check_print_orientation(ctx, units_w, units_h, plate_z0,
                             cable_x_e, cable_w_e, bridge_allow):
    """12. Stands on the plate's bottom edge, and nothing else overhangs.

    `ctx` here is the untouched PRINT-frame context: build axis +Z, bed
    at z = 0, mount y mapping to print z and mount z to -print y.
    """
    failures = []
    mesh = ctx["stl"]

    # (a) The bed plane carries the plate's bottom edge AND both shelf
    # ears. Vertices alone would pass on a single stray point, so this
    # asks for face area on the bed either side of the cable gap.
    on_bed = (mesh.face_normals[:, 2] < -0.99) & \
             (mesh.triangles_center[:, 2] < _CONTACT_EPS_MM)
    bed_x = mesh.triangles_center[on_bed][:, 0]
    bed_area = mesh.area_faces[on_bed]
    ear_r = float(bed_area[bed_x > cable_w_e / 2 + cable_x_e].sum())
    ear_l = float(bed_area[bed_x < -cable_w_e / 2 + cable_x_e].sum())
    if min(ear_r, ear_l) < 100.0:
        failures.append(Failure(
            "shelf_on_bed",
            f"bed contact is {ear_l:.0f}mm2 left / {ear_r:.0f}mm2 right of "
            f"the cable gap, and both shelf ears should be sitting on it "
            f"(>100mm2 each) — the shelf has drifted back up off the "
            f"plate's bottom edge, which is the biggest overhang this "
            f"design can grow in its standing print orientation",
        ))

    # (b) No unsupported downward face outside the snap footprints.
    down = mesh.face_normals[:, 2] < -math.sin(
        math.radians(_OVERHANG_FROM_VERTICAL_DEG))
    airborne = mesh.triangles_center[:, 2] > _CONTACT_EPS_MM
    flagged = down & airborne
    c = mesh.triangles_center[flagged]
    area = mesh.area_faces[flagged]

    # Snap footprints in the print frame: centred on their corner tiles
    # in x/z, and living between the panel plane and the plate underside
    # in y (print y = -mount z, so the snap band is negative y).
    cols = [0, units_w - 1] if units_w > 1 else [0]
    rows = [0, units_h - 1] if units_h > 1 else [0]
    half = _SNAP_W / 2 + 0.5
    in_snap = np.zeros(len(c), dtype=bool)
    for cx in cols:
        for ry in rows:
            sx = (cx - (units_w - 1) / 2) * _SNAP_PITCH
            sz = (ry + 0.5) * _SNAP_PITCH
            in_snap |= ((np.abs(c[:, 0] - sx) <= half)
                        & (np.abs(c[:, 2] - sz) <= half)
                        & (c[:, 1] >= -plate_z0 - 0.5) & (c[:, 1] <= 0.5))
    stray = float(area[~in_snap].sum())
    total = float(area.sum())
    if stray > bridge_allow + 20.0:
        worst = c[~in_snap][np.argmax(area[~in_snap])]
        failures.append(Failure(
            "overhang",
            f"{stray:.0f}mm2 of unsupported downward face outside the snap "
            f"footprints, over the {bridge_allow:.0f}mm2 the vent gable's "
            f"bridge is allowed (largest at print x={worst[0]:.1f}, "
            f"y={worst[1]:.1f}, z={worst[2]:.1f}) — the cradle is a constant "
            f"cross-section sweep along the build axis, so every face in it "
            f"should be a vertical wall; this one starts in mid-air",
        ))
    if total > _OVERHANG_AREA_CEILING_MM2:
        failures.append(Failure(
            "overhang_budget",
            f"{total:.0f}mm2 of unsupported downward face, over the "
            f"{_OVERHANG_AREA_CEILING_MM2:.0f}mm2 budget — the four snap "
            f"undersides plus the vent gable's bridge should come to ~912",
        ))
    return failures
