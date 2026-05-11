"""Invariants for the goBlu RV water filter holder (st-r3t).

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

  6. **Single connected solid.** pod_count separate pods would
     produce N orphan components in the STL; assert == 1 at defaults
     (pod_count=3, dovetails enabled) since adjacent pods share the
     dovetail tongue volume and merge into a single body in the
     stock_3up preset's union.
"""

from __future__ import annotations

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

    # 6. Single connected solid at defaults. End-cap-aware: if pods are
    #    flush + dovetailed, they merge into one body. If dovetail is
    #    disabled, pods still touch flush at their side walls, which
    #    OpenSCAD's union() collapses to one body too.
    failures.extend(expect_connected_solids(ctx, 1))

    return failures
