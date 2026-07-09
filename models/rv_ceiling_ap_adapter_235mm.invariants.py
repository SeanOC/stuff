"""Invariants for the RV ceiling speaker-hole -> WiFi AP adapter (st-nhd).

Built-ins (watertight, orphan fragments, PRINT_ANCHOR_BBOX drift) cover
the mesh basics. The extras here pin the claims this model exists for:

  1. **One revolved solid.** The whole axisymmetric body is a single
     rotate_extrude; ribs and holes are volumetric unions/cuts. If an
     overlap ever degrades to face-kissing (st-v7k class), the
     component count breaks first.

  2. **The recess actually nests.** recess dia = ceiling_hole_dia -
     2*hole_clearance, and NOTHING above the flange+lip plane may poke
     past that radius — any stray geometry up there would jam against
     the ceiling cutout instead of self-centering in it.

  3. **One-piece bed fit.** flange_outer_dia <= 318 (Bambu H2S bed,
     340 x 320 mm — the round plate is limited by the 320 mm axis,
     minus ~1 mm margin per side). REVISED (st-035) from the X1C's
     254 mm after the operator moved to an H2S; the one-piece
     no-split default still holds.

  4. **AP interface is right.** 4 insert holes at exactly 90 deg on
     the 82.16 mm bolt circle (bolt-circle-DIAMETER = center-to-center
     of opposing holes; measured, st-035 — was the nominal 3.25 in =
     82.55), each open to insert_depth and closed past it,
     with solid boss between them; the mating face + surrounds sit on
     the room plane.

  5. **Zero-support orientation.** Room face down: bed contact spans
     the full chamfered flange AND includes the boss mating face
     (coplanarity is the entire print strategy); no downward-facing
     surface exists above the small self-bridging features (insert
     hole tops / groove ceiling) — nothing needs support.

  6. **Offset cable pass-through (st-so4).** The AP bracket's center
     hub is solid, so the dead-center hole defaults OFF (center of the
     plate is solid) and the cable routes through arc slots offset
     from center: each slot centerline must be open through the plate,
     the slots must stay >= ~2 mm clear of the insert holes, and the
     boss must remain solid between adjacent slots. The .scad trims
     every slot to a pie-wedge budget of 360/count - 15 deg (round end
     caps included), so a >= 15 deg material bridge between slots is
     GUARANTEED at any count/arc/width combo — the count=6 sweep case
     used to ring-cut the center island free (2 shells). The bridge
     probe here is therefore unconditional for count >= 2.
"""

from __future__ import annotations

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_BED_LIMIT_MM = 318.0


def _polar(r, ang_deg, z):
    a = np.radians(ang_deg)
    return [r * np.cos(a), r * np.sin(a), z]


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    hole_dia = p.get("ceiling_hole_dia", 235)
    clearance = p.get("hole_clearance", 1.25)
    flange_outer = p.get("flange_outer_dia", 270)
    flange_t = p.get("flange_t", 4)
    lip_h = p.get("lip_h", 1.0)
    recess_depth = p.get("recess_depth", 9)
    bc_dia = p.get("ap_bolt_circle_dia", 82.16)
    insert_depth = p.get("insert_depth", 8.0)
    insert_hole_dia = p.get("insert_hole_dia", 4.2)
    cable_dia = p.get("cable_hole_dia", 0)
    rib_count = p.get("rib_count", 6)
    boss_r = p.get("ap_mount_dia", 100) / 2
    slot_count = int(p.get("cable_slot_count", 2))
    slot_bc_dia = p.get("cable_slot_bc_dia", 54)
    slot_arc = p.get("cable_slot_arc_deg", 60)
    slot_w = p.get("cable_slot_w", 14)
    slot_rot = p.get("cable_slot_rot_deg", 0)

    recess_r = (hole_dia - 2 * clearance) / 2
    total_h = flange_t + recess_depth

    # --- one-piece bed fit (st-035: H2S bed 340x320, round plate
    # limited by the 320 mm axis, <= ~318 flange) ---
    if flange_outer > _BED_LIMIT_MM:
        failures.append(Failure(
            "envelope",
            f"flange_outer_dia={flange_outer}mm > {_BED_LIMIT_MM}mm; won't "
            f"print one-piece on the H2S bed (bead requires one-piece default)",
        ))

    mesh = ctx["stl"]
    verts = mesh.vertices

    # --- overall extents: flange dia in XY, flange_t + recess_depth in Z ---
    bx, by, bz = ctx["bbox_mm"]
    if abs(bx - flange_outer) > 0.5 or abs(by - flange_outer) > 0.5:
        failures.append(Failure(
            "footprint",
            f"XY extents {bx:.2f} x {by:.2f}mm; expected the flange disk at "
            f"{flange_outer}mm both ways",
        ))
    if abs(bz - total_h) > 0.5:
        failures.append(Failure(
            "footprint",
            f"Z extent {bz:.2f}mm; expected flange_t + recess_depth = "
            f"{total_h:.2f}mm",
        ))

    # --- recess nests: nothing above the flange+lip plane may poke past
    # the recess radius, and the recess must reach full depth ---
    above = verts[verts[:, 2] > flange_t + lip_h + 0.1]
    if len(above) == 0:
        failures.append(Failure(
            "recess",
            "no geometry above the flange/lip plane — the recess cup that "
            "self-centers in the ceiling hole is missing",
        ))
    else:
        worst = np.hypot(above[:, 0], above[:, 1]).max()
        if worst > recess_r + 0.3:
            failures.append(Failure(
                "recess",
                f"geometry above the flange reaches r={worst:.2f}mm but the "
                f"recess must stay inside r={recess_r:.2f}mm "
                f"(= (hole - 2*clearance)/2) to nest into the ceiling cutout",
            ))

    # --- AP interface: 4 inserts at 90deg on the bolt circle ---
    bc_r = bc_dia / 2
    probe_z = min(insert_depth - 1.0, 2.0)
    hole_pts = [_polar(bc_r, a, probe_z) for a in (0, 90, 180, 270)]
    web_pts = [_polar(bc_r, a, probe_z) for a in (45, 135, 225, 315)]
    past_pts = [_polar(bc_r, a, insert_depth + 1.0) for a in (0, 90, 180, 270)]
    inside = mesh.contains(hole_pts + web_pts + past_pts)
    if inside[:4].any():
        failures.append(Failure(
            "ap_mount",
            f"solid material inside an insert hole position on the "
            f"{bc_dia}mm bolt circle — expected 4 open holes at 0/90/180/270",
        ))
    if not inside[4:8].all():
        failures.append(Failure(
            "ap_mount",
            f"empty space between insert positions at r={bc_r:.2f}mm — the "
            f"boss must be solid between the 4 holes",
        ))
    if not inside[8:].all():
        failures.append(Failure(
            "ap_mount",
            f"insert holes extend past insert_depth={insert_depth}mm — "
            f"blind holes must close above the insert",
        ))

    # --- cable pass-through (recorded st-nhd addition) ---
    if cable_dia > 0:
        if mesh.contains([[0.0, 0.0, total_h / 2]])[0]:
            failures.append(Failure(
                "cable",
                "cable_hole_dia > 0 but the plate center is solid — the "
                "Ethernet pass-through is missing",
            ))

    # --- offset cable slots (st-so4): each slot open through the full
    # plate height, outer edge >= ~2mm clear of the insert holes, and
    # the boss solid between adjacent slots (the .scad trims every slot
    # to a 360/count - 15deg pie-wedge budget, caps included, so the
    # bridge is guaranteed at any param combo). The clamp math mirrors
    # slot_r / slot_span_max in the .scad. ---
    if slot_count > 0:
        rib_in_r = boss_r - 5
        slot_out_max_r = min(
            bc_r - insert_hole_dia / 2 - 2,
            (rib_in_r - 1) if rib_count > 0 else boss_r - 1.5,
        )
        slot_r = max(slot_w / 2 + 0.5,
                     min(slot_bc_dia / 2, slot_out_max_r - slot_w / 2))
        bridge_deg = 15.0
        span_budget = 360.0 / slot_count - bridge_deg

        outer_edge = slot_r + slot_w / 2
        insert_clear = (bc_r - insert_hole_dia / 2) - outer_edge
        if insert_clear < 2.0 - 0.05:
            failures.append(Failure(
                "cable_slots",
                f"slot outer edge at r={outer_edge:.2f}mm leaves only "
                f"{insert_clear:.2f}mm to the insert holes on the "
                f"{bc_dia}mm bolt circle — need >= 2mm of meat",
            ))

        # Openness probes stay 3deg inside the wedge budget so a
        # trimmed slot (e.g. count=6 x 60deg nominal -> 45deg wedge)
        # isn't probed in the flat-cut region beyond its ends.
        probe_half = min(slot_arc / 2, max(0.0, span_budget / 2 - 3.0))
        probe_zs = (0.5, total_h / 2, total_h - 0.5)
        for i in range(slot_count):
            center = slot_rot + i * 360.0 / slot_count
            pts = [_polar(slot_r, center + off, z)
                   for off in (-probe_half, 0, probe_half)
                   for z in probe_zs]
            if mesh.contains(pts).any():
                failures.append(Failure(
                    "cable_slots",
                    f"cable slot {i} (center {center:.0f}deg, "
                    f"r={slot_r:.2f}mm) is not open through the plate — "
                    f"the offset cable pass-through is blocked",
                ))

        if slot_count >= 2:
            # True angular half-span of a slot = half the arc between
            # end-cap centers + the end cap itself, hard-capped by the
            # wedge budget. The budget leaves >= bridge_deg between
            # adjacent slots, so the midpoint bridge probe is
            # unconditional: the boss must be solid there at ANY
            # count/arc/width combo (this is the sweep-safe single-
            # shell guarantee — count=6 used to sever the center).
            cap_half = np.degrees(np.arcsin(min(1.0, (slot_w / 2) / slot_r)))
            half_span = min(slot_arc / 2 + cap_half, span_budget / 2)
            gap = 180.0 / slot_count - half_span
            if gap < bridge_deg / 2 - 0.05:
                failures.append(Failure(
                    "cable_slots",
                    f"slot half-span {half_span:.1f}deg leaves only "
                    f"{gap:.1f}deg to the midpoint between slots — the "
                    f"wedge budget must guarantee >= {bridge_deg}deg "
                    f"bridges (clamp math drifted from the .scad)",
                ))
            mid_pts = [
                _polar(slot_r,
                       slot_rot + (i + 0.5) * 360.0 / slot_count,
                       total_h / 2)
                for i in range(slot_count)
            ]
            if not mesh.contains(mid_pts).all():
                failures.append(Failure(
                    "cable_slots",
                    f"boss is open between cable slots at "
                    f"r={slot_r:.2f}mm — slots must stay discrete "
                    f"cutouts with a material bridge, not merge into "
                    f"a moat",
                ))

    # --- zero-support orientation: coplanar room face on the bed ---
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "orientation",
            "no vertices on z=0; model is not in its room-face-down print "
            "orientation",
        ))
        return failures
    span = max(contact[:, 0].max() - contact[:, 0].min(),
               contact[:, 1].max() - contact[:, 1].min())
    # bed contact ends at the 0.6 mm bed-edge chamfer
    if span < flange_outer - 2.0:
        failures.append(Failure(
            "orientation",
            f"bed contact spans {span:.1f}mm but the flange room face should "
            f"contact out to ~{flange_outer - 1.2:.1f}mm — the flange is "
            f"floating, which breaks the coplanar zero-support strategy",
        ))
    if not (np.hypot(contact[:, 0], contact[:, 1]) < bc_r).any():
        failures.append(Failure(
            "orientation",
            "no bed contact inside the bolt circle — the AP boss mating face "
            "must be coplanar with the flange room face (flush-boss design)",
        ))

    # --- support-free proof: no downward-facing surface above the small
    # self-bridging features (insert tops at insert_depth, groove ceiling).
    # Anything steeper-than-45deg-overhang higher up would need support. ---
    ceiling_limit = max(insert_depth, 2.5) + 0.6
    normals = mesh.face_normals
    centers = mesh.triangles_center
    bad = (normals[:, 2] < -0.75) & (centers[:, 2] > ceiling_limit)
    if bad.any():
        worst_z = centers[bad, 2].max()
        failures.append(Failure(
            "supports",
            f"{int(bad.sum())} downward-facing face(s) above "
            f"z={ceiling_limit:.1f}mm (worst at z={worst_z:.2f}mm) — this "
            f"model must print room-face-down with zero supports",
        ))

    return failures
