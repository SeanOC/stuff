"""Invariants for us_electrical_box_extender.

The part is a faithful port of BlackjackDuck's MakerWorld extension
ring: a rounded rectangular tube (open front-to-back) with `gang_count`
columns x 2 rows of screw posts, each bridged to its nearer wall and
drilled through with a screw clearance hole. Claims pinned here, beyond
the built-ins (watertight / orphan fragments / triangle ceiling /
PRINT_ANCHOR_BBOX drift):

1. **Single body.** The shell + every bridged screw post fuse into one
   printed solid. A post whose bridge failed to reach a wall would
   surface as an orphan component; this nails topology explicitly.

2. **Outer width scales with gang count.** The box width follows the
   gang lookup (2.25 in / 102 mm / 5.75 in / 7.6 in for 1..4 gang; the
   2-gang value is operator-measured, pst-4vp). At the default gang
   count the X bbox must equal the mapped width.

3. **Screw-hole count is gang-dependent.** Each gang contributes one
   column of 2 posts, each a through-hole; the shell itself is one
   frame opening. So the surface genus is `2 * gang_count + 1`
   (euler = 2 - 2 * genus). Pinning euler pins the post/hole count
   without measuring circles off the mesh.

4. **Walls present / it is a hollow ring.** The central opening is
   empty (you can see the wall behind), while the perimeter wall is
   solid. Guards against a regression to a solid slab.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids

# US device-box outer width by gang count, inches. 1/3/4-gang are the
# source's US-box lookup; 2-gang = 102mm operator-measured (pst-4vp),
# expressed in inches (102 / 25.4) so this stays a single source of truth.
_IN_TO_MM = 25.4
_BOX_WIDTH_IN = {1: 2.25, 2: 102 / _IN_TO_MM, 3: 5.75, 4: 7.6}


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    # 1. Single printed solid.
    failures.extend(expect_connected_solids(ctx, 1))

    gang = int(p["gang_count"])
    override_in = float(p["box_width_override_in"])
    bbox = ctx["bbox_mm"]
    mesh = ctx["stl"]

    # 2. Outer width tracks the gang-count lookup (or the override).
    expected_width_in = override_in if override_in != 0 else _BOX_WIDTH_IN[gang]
    expected_width_mm = expected_width_in * _IN_TO_MM
    if abs(bbox[0] - expected_width_mm) > 0.5:
        failures.append(Failure(
            "geometry",
            f"outer width {bbox[0]:.2f}mm != expected {expected_width_mm:.2f}mm "
            f"for gang_count={gang} (US box lookup {expected_width_in} in). The "
            "gang->width mapping regressed.",
        ))

    # 3. Genus = 2*gang + 1 (2 through-holes per gang + 1 frame opening).
    expected_genus = 2 * gang + 1
    expected_euler = 2 - 2 * expected_genus
    actual_euler = int(mesh.euler_number)
    if actual_euler != expected_euler:
        actual_genus = (2 - actual_euler) // 2
        failures.append(Failure(
            "topology",
            f"surface genus {actual_genus} (euler {actual_euler}) != expected "
            f"{expected_genus} for gang_count={gang}. Expected {2 * gang} screw "
            "through-holes + 1 frame opening — a hole count that does not match "
            "means posts, holes, or the open front/back regressed.",
        ))

    # 4. Hollow ring: central opening empty, perimeter wall solid.
    z_mid = bbox[2] / 2.0
    half_w = expected_width_mm / 2.0
    wall_probe_x = half_w - 1.0  # 1mm inside the outer face, within the wall
    inside = mesh.contains([
        [0.0, 0.0, z_mid],          # opening center — should be empty
        [wall_probe_x, 0.0, z_mid],  # left/right perimeter wall — should be solid
    ])
    if bool(inside[0]):
        failures.append(Failure(
            "geometry",
            "the box opening (0,0) is filled — the extender should be an open "
            "ring, not a solid slab.",
        ))
    if not bool(inside[1]):
        failures.append(Failure(
            "geometry",
            f"the perimeter wall at x={wall_probe_x:.1f}mm is hollow — the shell "
            "wall is missing.",
        ))

    # 5. Defaults conform to the standard US device-box spec (pst-c6l).
    #    The defaults ARE the NEMA/industry numbers (documented in the
    #    .scad header); this guard fails loudly on a silent drift so the
    #    "spec-faithful" claim can't rot. 6-32 device screws (3.505mm
    #    major) self-tap the 3.25mm posts — see the header for the
    #    assembly-method reasoning; not asserted here (it's a tunable).
    for key, want in (
        ("box_height_in", 3.75),        # single-gang box face height
        ("screw_row_spacing_in", 3.28125),  # device-screw vertical pitch (3-9/32)
        ("screw_col_spacing_in", 1.8125),   # yoke lateral pitch (1-13/16)
    ):
        got = float(p[key])
        if abs(got - want) > 1e-6:
            failures.append(Failure(
                "standards",
                f"default {key}={got} drifted from the US device-box standard "
                f"{want} in. This model is spec-faithful — if the change is "
                "intentional, update the conformance note in the .scad header.",
            ))

    return failures
