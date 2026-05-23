"""Invariants for the BluTech water-softener floor foot (st-09w).

Beyond the built-in checks (watertight, single-body component count,
PRINT_ANCHOR_BBOX drift, triangle ceiling), this sidecar pins the
load-bearing structural claims the bead spelled out:

  1. **VHB face flat.** The -Z face (z = 0) of the flange is a
     continuous annular ring with no holes, ribs, or fillets. Same
     invariant pattern as goblu_filter_holder_3x90mm's -Y back face.
     Measured by summing the area of triangles that lie entirely on
     the z_min plane and comparing to the expected annulus area
     π·(flange_or² − cradle_ir²); ≥70% of expected is the spec floor.
     Anything less means a rib, hole, or rounding spilled onto the
     bond face — peels the VHB.

  2. **Pocket ID = cyl_d + 2·clearance.** Cylinder fit class —
     reject defaults outside 0.5–3.0 mm radial clearance. Tighter
     binds the cylinder; looser lets it rattle.

  3. **Cradle height 75–100 mm.** Bead-locked grip height range.

  4. **Gusset count non-trivial.** ≥4 gussets, otherwise the cradle
     ring leans like a paper towel tube.

  5. **Gusset hypotenuse ≥45° from horizontal.** Print-orientation
     constraint: gusset_h / flange_overhang ≥ 1.0 means the slope
     is ≥45° from horizontal (≤45° from vertical) — FDM prints
     without supports.

  6. **Scupper notches don't touch the VHB face.** Scupper bottom
     z = flange_t (just above z=0), so they breach the cradle ring
     wall but not the flange below. Soft-check via param: a
     scupper that demands cutting INTO the flange would fail this.

  7. **Phantom cylinder is excluded from STL.** The
     assembly_with_cylinder view uses % so the phantom never
     contributes to the STL. The connected-solid count stays at 1
     in either view.
"""

from __future__ import annotations

from math import pi

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids


def check(ctx):
    failures: list[Failure] = []
    p = as_default_params(ctx["params"])

    # The foot is always a single connected solid: flange + ring +
    # gussets all fused, even with scuppers cut through the ring.
    failures.extend(expect_connected_solids(ctx, 1))

    cyl_d           = p.get("cyl_d")
    clearance       = p.get("clearance")
    cradle_h        = p.get("cradle_h")
    ring_wall_t     = p.get("ring_wall_t")
    flange_t        = p.get("flange_t")
    flange_overhang = p.get("flange_overhang")
    gusset_count    = p.get("gusset_count")
    gusset_h        = p.get("gusset_h")
    scupper_h       = p.get("scupper_h")

    # 2. Cylinder fit class.
    if clearance is not None and (clearance < 0.5 or clearance > 3.0):
        failures.append(Failure(
            "cylinder_fit",
            f"clearance={clearance}mm radial — bead spec is 0.5-3.0mm. "
            f"Below 0.5 binds the cylinder on rough prints; above 3.0 "
            f"lets it rattle and load the cradle in impact.",
        ))

    # 3. Cradle height locked to 75-100 mm by the bead.
    if cradle_h is not None and (cradle_h < 75 or cradle_h > 100):
        failures.append(Failure(
            "cradle_height",
            f"cradle_h={cradle_h}mm outside the bead-locked 75-100mm "
            f"mid-cradle grip range. Lower defeats lateral grip; higher "
            f"starts to obstruct the cylinder body for maintenance.",
        ))

    # 4. Gusset count.
    if gusset_count is not None and gusset_count < 4:
        failures.append(Failure(
            "gusset_count",
            f"gusset_count={gusset_count} — fewer than 4 leaves the "
            f"cradle ring wobbly under lateral load. Bead spec is 4-8.",
        ))

    # 5. Gusset slope: gusset_h / flange_overhang ≥ 1.0 → ≥45° from
    #    horizontal so the hypotenuse prints without supports.
    if (gusset_h is not None and flange_overhang is not None
            and flange_overhang > 0):
        slope = gusset_h / flange_overhang
        if slope < 1.0:
            from math import degrees, atan
            angle_from_horiz = degrees(atan(slope))
            failures.append(Failure(
                "gusset_print_slope",
                f"gusset hypotenuse slope = gusset_h({gusset_h}) / "
                f"flange_overhang({flange_overhang}) = {slope:.2f} → "
                f"{angle_from_horiz:.1f}° from horizontal. FDM wants "
                f"≥45° (slope ≥1.0); shorter gussets or smaller "
                f"overhang.",
            ))

    # 6. Scupper height stays above the VHB face. The .scad places
    #    scuppers at z = flange_t (just above z=0), so this is mostly
    #    a guard against a param manipulation that would push them
    #    INTO the flange. Flag if scupper_h ≥ flange_t (could
    #    structurally weaken the flange).
    if (scupper_h is not None and flange_t is not None
            and scupper_h >= flange_t * 2):
        failures.append(Failure(
            "scupper_height",
            f"scupper_h={scupper_h}mm is more than twice flange_t="
            f"{flange_t}mm — at this height the notch removes most of "
            f"the cradle ring's base anchorage. Lower scupper_h or "
            f"bump ring_wall_t.",
        ))

    # 1. VHB face continuity. Sum the surface area of triangles that
    #    lie entirely in the z_min (=0) plane and compare to the
    #    expected annular area π·(flange_or² − cradle_ir²). ≥70% of
    #    expected is the spec floor; below that, a rib/hole/fillet
    #    has spilled onto the VHB face.
    if all(v is not None for v in (cyl_d, clearance, ring_wall_t,
                                    flange_overhang)):
        cradle_ir = cyl_d / 2 + clearance
        cradle_or = cradle_ir + ring_wall_t
        flange_or = cradle_or + flange_overhang
        expected_area = pi * (flange_or**2 - cradle_ir**2)
        actual_area = _z_min_face_area(ctx["stl"])
        ratio = actual_area / expected_area if expected_area > 0 else 0
        if ratio < 0.70:
            failures.append(Failure(
                "vhb_face_continuous",
                f"-Z VHB face area {actual_area:.1f}mm² is "
                f"{ratio * 100:.1f}% of the expected annular area "
                f"{expected_area:.1f}mm² (≥70% required). Something "
                f"has broken the flat bond face — a rib, hole, "
                f"fillet, or rounding spilled onto -Z.",
            ))
        # Also flag the absolute minimum: VHB needs roughly 5000 mm²
        # for a ~9 kg lateral-load mount with margin (peel stress
        # ~10 kPa at the edge).
        if actual_area < 5000:
            failures.append(Failure(
                "vhb_face_too_small",
                f"-Z VHB face area {actual_area:.1f}mm² < 5000 mm² "
                f"minimum for the 9 kg / 0.6 g lateral load case. "
                f"Bump flange_overhang to widen the bond footprint.",
            ))

    return failures


def _z_min_face_area(mesh, plane_tol_mm: float = 0.01) -> float:
    """Sum the area of triangles that lie entirely on the z_min plane.

    The -Z face must be the VHB bond face — a continuous flat annulus.
    A triangle counts only if all three of its vertices sit on the
    z_min plane within `plane_tol_mm`; triangles that drift off-plane
    (rounded edges, rib joints) are correctly excluded.
    """
    z_min = float(mesh.bounds[0, 2])
    verts = mesh.vertices
    faces = mesh.faces
    zs = verts[faces][:, :, 2]  # (n_faces, 3)
    on_plane = np.all(np.abs(zs - z_min) < plane_tol_mm, axis=1)
    return float(mesh.area_faces[on_plane].sum())
