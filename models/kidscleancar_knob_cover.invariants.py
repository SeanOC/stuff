"""Invariants for kidscleancar_knob_cover.

The cover's reason to exist is a friction grip on the LOWER FLANGE that
deliberately never couples to the knob. These claims pin that intent
against the exported STL:

1. TOPOLOGY: one printed solid.
2. FOOTPRINT: round, OD = flange_d + 2*fit_clearance + 2*wall — big
   enough to swallow the flange plus a wall, not so big it's a hazard.
3. KNOB FLOATS: the central cavity is hollow over the whole knob
   envelope (a point at the knob's radius and mid-height is empty), and a
   solid roof caps it — the knob is never touched, so spinning the cover
   can't turn it.
4. SCREW CLEARANCE: the annulus pocket over the 3 proud screw heads is
   hollow above the screw band.
5. CRUSH RIBS BITE, BORE SPINS FREE: at each rib azimuth the material
   reaches INSIDE the flange radius (interference retention); halfway
   between ribs the same radius is empty (a round, free-spinning bore —
   no anti-rotation feature). Both together are the whole locking story.

COORDINATES: the model is authored in the deck frame (z = 0 = deck, mouth
low, roof high) but the exported STL is FLIPPED roof-down into the print
frame (dome on the bed at z = 0, mouth up). Probes are written in the
readable deck frame and mapped through `_flip` — deck (x, y, z) ->
print (x, -y, top_z - z) — to match the exported geometry.
"""

from __future__ import annotations

import math

import numpy as np

from scripts.invariants import Failure, as_default_params, expect_connected_solids


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    stl = ctx["stl"]
    bx, by, bz = ctx["bbox_mm"]

    # Deck-frame -> print-frame map (mirrors the final assembly flip).
    top_z = p["flange_h"] + p["knob_h"] + p["knob_vclear"] + p["wall"]

    def solid(deck_pts):
        """Containment for deck-frame points, mapped into the exported STL frame."""
        pts = [(x, -y, top_z - z) for (x, y, z) in deck_pts]
        return stl.contains(np.array(pts, dtype=float))

    # 1. One monolithic solid.
    failures.extend(expect_connected_solids(ctx, 1))

    flange_r = p["flange_d"] / 2
    wall = p["wall"]
    fit = p["fit_clearance"]
    skirt_od = p["flange_d"] + 2 * fit + 2 * wall

    # 2. Footprint: round + correctly sized.
    if abs(bx - by) > 0.5:
        failures.append(Failure(
            "footprint",
            f"footprint not round: X={bx:.2f} vs Y={by:.2f} (>0.5mm apart)",
        ))
    if abs(bx - skirt_od) > 1.0:
        failures.append(Failure(
            "footprint",
            f"OD={bx:.2f}mm off expected skirt_od={skirt_od:.2f}mm "
            f"(flange_d + 2*fit_clearance + 2*wall)",
        ))

    # Z stack (deck at z=0).
    knob_top = p["flange_h"] + p["knob_h"]
    knob_roof = knob_top + p["knob_vclear"]
    screw_top = p["flange_h"] + p["screw_head_h"]

    # 3. Knob floats: cavity hollow over the knob, solid roof above.
    knob_r = p["knob_d"] / 2
    knob_mid_z = p["flange_h"] + p["knob_h"] / 2
    knob_probes = [
        (0.0, 0.0, knob_mid_z),               # dead centre, empty
        (knob_r - 0.5, 0.0, knob_mid_z),      # at the knob wall, empty
    ]
    if any(solid(knob_probes)):
        failures.append(Failure(
            "knob-cavity",
            f"knob cavity not clear at r<={knob_r:.1f}, z={knob_mid_z:.1f}; "
            f"the cover would touch/turn the knob",
        ))
    if not solid([(0.0, 0.0, knob_roof + wall / 2)])[0]:
        failures.append(Failure(
            "knob-cavity",
            f"no solid roof above the knob cavity at z={knob_roof + wall / 2:.1f}",
        ))

    # 4. Screw-head annulus cleared: hollow above the screw band.
    annulus_r = (knob_r + flange_r) / 2
    if solid([(annulus_r, 0.0, screw_top - 0.5)])[0]:
        failures.append(Failure(
            "screw-clearance",
            f"screw annulus not clear at r={annulus_r:.1f}, z={screw_top - 0.5:.1f}",
        ))

    # 5. Ribs bite past the flange edge; bore is free-spinning between them.
    n = int(p["rib_count"])
    bite_r = flange_r - p["rib_interference"] / 2   # inside the flange radius
    z_rib = p["flange_h"] / 2 + 0.5                 # low in the flange band
    on_rib, between_rib = [], []
    for i in range(n):
        a_on = math.radians(i * 360 / n)
        a_bt = math.radians((i + 0.5) * 360 / n)
        on_rib.append((bite_r * math.cos(a_on), bite_r * math.sin(a_on), z_rib))
        between_rib.append((bite_r * math.cos(a_bt), bite_r * math.sin(a_bt), z_rib))
    if not all(solid(on_rib)):
        failures.append(Failure(
            "ribs",
            f"a crush rib is missing or doesn't reach r={bite_r:.2f}mm "
            f"(inside flange_r={flange_r:.2f}) — no interference grip",
        ))
    if any(solid(between_rib)):
        failures.append(Failure(
            "ribs",
            f"bore is solid between ribs at r={bite_r:.2f}mm — the cover would "
            f"key to the flange instead of spinning free",
        ))

    return failures
