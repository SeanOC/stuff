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

  3. **One-piece bed fit.** flange_outer_dia <= 254 (256 mm X1C bed
     minus ~1 mm margin per side) — the bead's explicit constraint for
     the no-split default.

  4. **AP interface is right.** 4 insert holes at exactly 90 deg on
     the 82.55 mm bolt circle (bolt-circle-DIAMETER reading of
     "3.25 in across"), each open to insert_depth and closed past it,
     with solid boss between them; the mating face + surrounds sit on
     the room plane.

  5. **Zero-support orientation.** Room face down: bed contact spans
     the full chamfered flange AND includes the boss mating face
     (coplanarity is the entire print strategy); no downward-facing
     surface exists above the small self-bridging features (insert
     hole tops / groove ceiling) — nothing needs support.
"""

from __future__ import annotations

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_BED_LIMIT_MM = 254.0


def _polar(r, ang_deg, z):
    a = np.radians(ang_deg)
    return [r * np.cos(a), r * np.sin(a), z]


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    hole_dia = p.get("ceiling_hole_dia", 235)
    clearance = p.get("hole_clearance", 1.25)
    flange_outer = p.get("flange_outer_dia", 252)
    flange_t = p.get("flange_t", 4)
    lip_h = p.get("lip_h", 1.0)
    recess_depth = p.get("recess_depth", 9)
    bc_dia = p.get("ap_bolt_circle_dia", 82.55)
    insert_depth = p.get("insert_depth", 5.5)
    cable_dia = p.get("cable_hole_dia", 25)

    recess_r = (hole_dia - 2 * clearance) / 2
    total_h = flange_t + recess_depth

    # --- one-piece bed fit (bead: 256 mm bed, <= ~254 flange) ---
    if flange_outer > _BED_LIMIT_MM:
        failures.append(Failure(
            "envelope",
            f"flange_outer_dia={flange_outer}mm > {_BED_LIMIT_MM}mm; won't "
            f"print one-piece on the X1C bed (bead requires one-piece default)",
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
