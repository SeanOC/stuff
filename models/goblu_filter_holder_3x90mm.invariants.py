"""Invariants for the goBlu RV water filter holder (st-r3t, st-hxk, st-toz, st-yuu, st-6xj, st-nn5, st-e6q).

Beyond the built-in checks (watertight, single-body component count,
PRINT_ANCHOR_BBOX drift, triangle ceiling), this sidecar pins the
load-bearing structural claims the bead spelled out:

  1. **Pocket fit.** pocket_id == housing_diameter + 2·clearance —
     the geometric contract between housing OD and the bore the user
     drops it into. Slipping this silently means the part either
     binds on the housing or rattles. Bead anchor: pocket ID 91 mm at
     defaults (90 mm housing + 0.5 mm radial clearance).

  2. **VHB back wall stays mountable.** back_wall_t ≤ 10 mm — past
     that, the holder stands off the RV wall too far and loads the
     VHB in a worse direction than pure shear.

  3. **Dovetail doesn't punch through the side wall.** dovetail_depth
     ≤ side_wall_t / 2 — if the tongue goes deeper than half the wall
     it leaves no material between the slot floor and the pocket
     bore, which collapses on the next bump.

  4. **Bottom drain is a drain, not a fall-through.** When
     bottom_lip_w == 0 the bottom of the pocket has no retaining lip,
     so a flipped or shaken assembly would let the housing drop out
     the bottom. Allowed but flagged as a non-default config.

  5. **Pocket axial budget.** pocket_depth + collar_headroom ≤
     housing body height (118 mm at goBlu stock). Past that, the top
     rim presses into the underside of the housing's stainless
     collar before the bottom seats, which puts the collar in shear
     rather than the housing body in compression.

  6. **Array extent matches the layout formula (st-hxk).** The X
     bounding-box of the assembly must equal pod_count · pod_w +
     (pod_count − 1) · pod_gap. Catches three regressions at once:
     stock_3up accidentally widening (default pod_gap drifting off 0),
     slicer_3up not actually separating pods (pod_gap not threaded
     through pod_x), or the pod_w derivation desyncing from
     housing_diameter + 2·clearance + 2·side_wall_t.

  7. **Topology matches gap config (st-hxk, st-toz, st-yuu, st-6xj).**
     At pod_gap > 0 each pod is its own connected component (N pods →
     N components). At pod_gap == 0 the pods fuse via face contact;
     each dovetail joint's clearance-air ring vents to outside through
     the slot's bottom opening (st-6xj), so no sealed inner cavities
     and the whole assembly is 1 connected component.

  8. **Slot opens through the pod base (st-6xj).** Folded into #7:
     if the slot is closed at both top AND bottom (the pre-st-6xj
     regression), each dovetail joint becomes a sealed inner cavity
     again and the connected-components check rejects with 3 instead
     of 1. The slot's bottom-open extent is the *reason* the count
     drops to 1, so the same assertion guards both.

  9. **Tongue + slot tops taper to a point for support-free print
     (st-nn5).** Param-level guards:
       • dovetail_top_taper_h ≥ dovetail_w_tip / 2 — keeps the taper
         shallow enough (≥ 45° from horizontal) that FDM bridging
         can produce the closed apex without support. The default
         (9 mm at w_tip = 18 mm) sits exactly at the limit. Set to
         0 to opt back into a flat top (and supports).
       • dovetail_top_taper_h ≤ dovetail_height — the taper must
         fit inside the dovetail's vertical extent; pushing it past
         dovetail_height leaves no straight mating region.

  10. **-Y/VHB face stays a flat rectangle (st-e6q).** The outer-edge
     rounding scope was tightened in st-e6q to not bleed onto the
     -Y face. Measure the surface area of the y_min plane and
     require it to equal the expected `pod_count · pod_w · pod_h`
     (within a few mm² tolerance for triangle-edge noise). If any
     corner rounding spilled onto -Y, the rounded corner pulls
     vertices off the y_min plane and the area shrinks. Same check
     pins the related claim that no debossing, slot, or hole ever
     gets cut into the back face.
"""

from __future__ import annotations

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids


# Stock goBlu spec — used for the "axial budget" claim.
_HOUSING_BODY_HEIGHT_MM = 118.0


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    housing_diameter = p.get("housing_diameter")
    clearance = p.get("clearance")
    back_wall_t = p.get("back_wall_t")
    side_wall_t = p.get("side_wall_t")
    dovetail_depth = p.get("dovetail_depth")
    bottom_lip_w = p.get("bottom_lip_w")
    pocket_depth = p.get("pocket_depth")
    collar_headroom = p.get("collar_headroom")
    pod_count = p.get("pod_count")
    dovetail_enabled = p.get("dovetail_enabled")
    pod_gap = p.get("pod_gap")
    dovetail_top_taper_h = p.get("dovetail_top_taper_h")
    dovetail_height = p.get("dovetail_height")
    dovetail_w_tip = p.get("dovetail_w_tip")

    # 1. Pocket ID = housing OD + 2·clearance — at defaults this is the
    #    bead's "91 mm" anchor. Not directly observable from the STL,
    #    but a regression to default clearance < 0.25 mm or > 1.0 mm
    #    radial would change the housing fit class.
    if clearance is not None and (clearance < 0.25 or clearance > 1.0):
        failures.append(Failure(
            "housing_fit",
            f"clearance={clearance}mm radial — bead spec is 0.5-0.75mm "
            f"(pocket ID 91-91.5mm at 90mm housing). Outside this range "
            f"the housing will bind (< 0.25) or rattle (> 1.0).",
        ))

    # 2. VHB back wall ≤ 10 mm.
    if back_wall_t is not None and back_wall_t > 10:
        failures.append(Failure(
            "vhb_standoff",
            f"back_wall_t={back_wall_t}mm exceeds the 10mm spec ceiling; "
            f"holder will stand off the RV wall too far.",
        ))

    # 3. Dovetail depth ≤ side_wall_t / 2.
    if (dovetail_enabled and dovetail_depth is not None
            and side_wall_t is not None
            and dovetail_depth > side_wall_t / 2):
        failures.append(Failure(
            "dovetail_wall",
            f"dovetail_depth={dovetail_depth}mm exceeds half of "
            f"side_wall_t={side_wall_t}mm — slot floor would punch "
            f"through into the pocket bore.",
        ))

    # 4. Drain lip warning.
    if bottom_lip_w is not None and bottom_lip_w == 0:
        failures.append(Failure(
            "drain_lip",
            "bottom_lip_w=0 — pocket has no retaining lip, the housing "
            "will fall through if the assembly is ever flipped. "
            "Acceptable if the user is intentionally going full-drain.",
        ))

    # 5. Pocket axial budget ≤ housing body height.
    if (pocket_depth is not None and collar_headroom is not None
            and pocket_depth + collar_headroom > _HOUSING_BODY_HEIGHT_MM):
        failures.append(Failure(
            "axial_budget",
            f"pocket_depth+collar_headroom={pocket_depth + collar_headroom}mm "
            f"> housing body height {_HOUSING_BODY_HEIGHT_MM}mm; the holder "
            f"rim will load the collar in shear before the housing seats.",
        ))

    # 6. Array X-extent matches the layout formula. Re-derives pod_w
    #    from the housing/wall params so this also catches drift between
    #    the .scad's pod_w expression and what actually got rendered.
    if (housing_diameter is not None and clearance is not None
            and side_wall_t is not None and pod_count is not None
            and pod_gap is not None):
        pod_w = housing_diameter + 2 * clearance + 2 * side_wall_t
        expected_x = pod_count * pod_w + (pod_count - 1) * pod_gap
        actual_x = ctx["bbox_mm"][0]
        # 1mm tolerance matches the built-in PRINT_ANCHOR_BBOX check.
        if abs(actual_x - expected_x) > 1.0:
            failures.append(Failure(
                "array_extent",
                f"STL x-extent {actual_x:.2f}mm ≠ "
                f"pod_count·pod_w + (pod_count−1)·pod_gap = "
                f"{pod_count}·{pod_w:.2f} + {pod_count - 1}·{pod_gap} = "
                f"{expected_x:.2f}mm. Either pod_x() lost the pod_gap "
                f"term, the default pod_gap drifted off 0, or pod_w "
                f"desynced from housing_diameter + 2·clearance + "
                f"2·side_wall_t.",
            ))

    # 7. Topology matches gap config. At pod_gap > 0 each pod is its
    #    own connected body. At pod_gap == 0 (st-6xj) the open slot
    #    bottoms vent each dovetail joint's clearance ring to outside,
    #    so the whole assembly is one connected component.
    if pod_count is not None and pod_count >= 1:
        expected_components = (
            pod_count if (pod_gap is not None and pod_gap > 0) else 1
        )
        failures.extend(expect_connected_solids(ctx, expected_components))

    # 10. -Y/VHB face stays a flat rectangle. Sum the surface area of
    #     triangles that lie entirely in the y_min plane and compare
    #     to the expected rectangle area. A corner rounding that
    #     spilled onto -Y would pull the corner vertices off-plane
    #     and shrink the measured area.
    if (housing_diameter is not None and clearance is not None
            and side_wall_t is not None and pod_count is not None
            and pod_gap is not None and back_wall_t is not None
            and pocket_depth is not None and collar_headroom is not None):
        bottom_ring_thickness = p.get("bottom_ring_thickness")
        if bottom_ring_thickness is not None:
            pod_w = housing_diameter + 2 * clearance + 2 * side_wall_t
            pod_h = bottom_ring_thickness + pocket_depth + collar_headroom
            expected_area = pod_count * pod_w * pod_h
            actual_area = _y_min_face_area(ctx["stl"])
            # 5 mm² tolerance: triangle-edge noise on a ~44 000 mm² face
            # is well under 1 mm²; loosen to 5 to absorb the BOSL2 corner
            # mesh discretization at the dovetail base where the rounded
            # +Y front corner meets a sharp ±X mating face.
            if abs(actual_area - expected_area) > 5.0:
                failures.append(Failure(
                    "vhb_face_flat",
                    f"-Y face area {actual_area:.1f}mm² ≠ expected "
                    f"{expected_area:.1f}mm² (pod_count·pod_w·pod_h). "
                    "Either edge rounding bled onto the back face "
                    "(breaks VHB flat-bond invariant) or a debossing/"
                    "hole was cut into -Y.",
                ))

    # 9. Tapered tops must be ≥ 45° (≥ w_tip/2) and fit within the
    #    dovetail's vertical extent. Both guards apply only when the
    #    feature is opted-in (taper > 0 and dovetails enabled).
    if (dovetail_enabled and dovetail_top_taper_h is not None
            and dovetail_top_taper_h > 0):
        if (dovetail_w_tip is not None
                and dovetail_top_taper_h < dovetail_w_tip / 2):
            failures.append(Failure(
                "taper_angle",
                f"dovetail_top_taper_h={dovetail_top_taper_h}mm < "
                f"dovetail_w_tip/2={dovetail_w_tip / 2}mm — taper slope "
                "is shallower than 45° (steeper than horizontal); FDM "
                "bridging will sag at the closed apex.",
            ))
        if (dovetail_height is not None
                and dovetail_top_taper_h > dovetail_height):
            failures.append(Failure(
                "taper_height",
                f"dovetail_top_taper_h={dovetail_top_taper_h}mm > "
                f"dovetail_height={dovetail_height}mm — taper exceeds "
                "the dovetail's vertical extent, leaving no straight "
                "mating region for the slip-fit slide.",
            ))

    return failures


def _y_min_face_area(mesh, plane_tol_mm: float = 0.01) -> float:
    """Sum the area of triangles that lie entirely in the y_min plane.

    The -Y face must be a flat rectangle (VHB invariant). A triangle
    counts only if all three of its vertices sit on the y_min plane
    within `plane_tol_mm`; rounded chamfer triangles whose vertices
    drift off-plane are correctly excluded.
    """
    y_min = float(mesh.bounds[0, 1])
    verts = mesh.vertices
    faces = mesh.faces
    ys = verts[faces][:, :, 1]  # (n_faces, 3)
    on_plane = np.all(np.abs(ys - y_min) < plane_tol_mm, axis=1)
    return float(mesh.area_faces[on_plane].sum())
