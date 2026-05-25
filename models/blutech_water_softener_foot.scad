// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Floor-mounted "foot" for a BluTech RV water softener (8" OD ×
// 17" tall cylinder, ~20 lbs full). The foot grips the bottom of
// the cylinder laterally while leaving it removable straight up;
// the cylinder rests on the RV floor inside an open-bottom ring.
//
// === Softener being mounted ===
//
//   - Cylinder OD:          203.2 mm  (8")
//   - Cylinder height:      431.8 mm  (17")
//   - Weight full:          ~9 kg / 20 lb
//   - Bottom: flat, no fittings or protrusions to clear.
//
// === Install + load case ===
//
//   - Floor attachment: VHB tape (3M VHB or equiv). The foot's
//     bottom (-Z) face is a continuous flat annulus that bonds to
//     the RV floor. v1 spec is VHB; a future revision may swap to
//     wood-screws-through-the-flange.
//   - Grip height: mid cradle (~85 mm) — high enough to capture
//     the cylinder bottom laterally in cornering / braking, low
//     enough that the cylinder lifts straight up freely.
//   - Lateral load: 9 kg × ~0.6 g cornering ≈ 53 N (~12 lbf) at
//     cradle mid-height. Moment at the VHB joint ≈ 53 N × 45 mm =
//     2.4 N·m. Spread over an annular VHB footprint ~28,000 mm²
//     (defaults), peel stress at the outer edge stays under
//     2 kPa — well below any 3M VHB peel rating.
//
// === Coord + install orientation ===
//
//   install +Z = up (cylinder axis)
//   install -Z = down (VHB face on the RV floor; bench / floor at z=0)
//   install X/Y = lateral plane (footprint of the foot, gussets
//                 radiate outward)
//
// === Print orientation ===
//
//   Print VHB face down (z=0 face on the build plate). Cradle ring
//   walls and the radial triangular gussets print straight up; the
//   gusset hypotenuse slope at defaults is 31° from vertical (59°
//   from horizontal), well inside the 45°-from-horizontal FDM
//   support-free envelope. The top lead-in chamfer is an in-plane
//   inset on the cradle ring's top edge — prints cleanly. The
//   scupper notches at the base of the cradle ring need a short
//   bridge (scupper_w wide, default 8 mm) one layer above the
//   notch — PETG/ASA bridge that span without sagging.
//
//   Material: PETG (default — RV interior, intermittent moisture,
//   UV-tolerant) or ASA. PLA OK in cool shaded interior but check
//   the temperature envelope before relying on it in a hot RV.
//
// === Geometry ===
//
//   - Base flange (-Z face = VHB face): a thin annular disk from
//     cradle_id/2 outward to flange_or. Underside (z=0) is the VHB
//     face: pristinely flat, no holes, no ribs, no fillets — same
//     invariant pattern as goblu_filter_holder_3x90mm's -Y back.
//     ≥70% continuous bond area to keep the tape happy.
//   - Cradle ring: a vertical hollow cylinder sitting on the flange
//     top, ID = cyl_d + 2·clearance, OD = ID + 2·ring_wall_t.
//     Height cradle_h. The cylinder drops THROUGH this ring (no
//     enclosed pocket floor) and rests on the RV floor between the
//     ring's inner wall and the flange's inner edge.
//   - Top lead-in chamfer: a small inside-edge chamfer at the
//     cradle ring's top so the cylinder can be dropped in without
//     binding on the lip.
//   - Gussets (×N): radial triangular fins on the cradle ring's
//     OUTSIDE, bridging the ring wall to the flange top. Each
//     gusset is a right triangle in a vertical plane: vertical leg
//     along the ring at height gusset_h, horizontal leg along the
//     flange top at flange_overhang. Filament-economy: a small
//     count of solid gussets beats one continuous annular wall.
//   - Scupper notches: small rectangular cutouts through the cradle
//     ring wall, at the BASE of the ring (z just above the flange
//     top). Any water that lands inside the ring drains laterally
//     through the scuppers onto the flange top and off the edge.
//     The notches DO NOT cut through the flange (VHB face stays
//     continuous).
//
// === Drainage ===
//
//   Three drainage modes:
//
//   1. Outside of cradle ring → water hits the ring wall, runs
//      down the outside, lands on the flange top, runs off the
//      flange edge. No pocket, no pooling.
//   2. Top rim → water that lands on the top of the cradle ring
//      either runs in (down inside the ring → scuppers) or out
//      (down the outside, as in #1). The ring wall is thin (3 mm
//      default) so surface tension can't hold a meaningful puddle.
//   3. Inside the cradle ring → cylinder sits on the RV floor, so
//      there's no pocket floor. Water lands on the RV floor next
//      to the cylinder, then drains out through the scuppers.
//
//   Critical invariant: the VHB face (-Z face of the flange) stays
//   a continuous flat annulus, no breaches. Water that gets onto
//   the flange top drains off the OUTER edge, not under the flange
//   (the VHB tape itself blocks lateral migration at the bottom).
//
// === Version history ===
//
//   v1 (st-09w): initial design — VHB-stuck open-bottom cradle
//     with radial gussets and scupper drains. Photo-derived
//     softener spec (8" OD, 17" tall). Defaults sized for a full-
//     weight (~9 kg) cylinder under ~0.6 g lateral; sanity-check
//     the load math in the commit/PR description.

include <BOSL2/std.scad>

$fn = 96;

// === User-tunable parameters ===

part = "assembly";  // @param enum choices=assembly|assembly_with_cylinder group=part label="Which view to render"

// ----- Softener cylinder (the thing being mounted) -----
cyl_d           = 203.2;  // @param number min=100 max=300 step=0.1 unit=mm group=cylinder label="Softener cylinder OD (8 in = 203.2 mm)"
cyl_h           = 431.8;  // @param number min=200 max=600 step=0.5 unit=mm group=cylinder label="Softener cylinder height (17 in = 431.8 mm; phantom only)"

// ----- Fit -----
clearance       = 1.5;   // @param number min=0.5 max=5   step=0.1 unit=mm group=fit label="Radial slip clearance between cylinder OD and cradle ID"

// ----- Cradle ring -----
cradle_h        = 85;    // @param number min=75 max=100 step=1   unit=mm group=cradle label="Cradle ring height above flange top (mid-cradle grip)"
ring_wall_t     = 3;     // @param number min=2  max=8   step=0.5 unit=mm group=cradle label="Cradle ring wall thickness"
top_chamfer     = 2;     // @param number min=0  max=6   step=0.5 unit=mm group=cradle label="Cradle top inside lead-in chamfer (45° inset)"

// ----- Base flange + gussets -----
flange_t        = 4;     // @param number min=3  max=10  step=0.5 unit=mm group=base label="Base flange thickness (VHB face = bottom of this)"
flange_overhang = 30;    // @param number min=10 max=60  step=1   unit=mm group=base label="Flange radial overhang past cradle outer wall"
gusset_count    = 6;     // @param number min=4  max=12  step=1   group=base label="Radial gusset count"
gusset_h        = 50;    // @param number min=20 max=80  step=1   unit=mm group=base label="Gusset vertical leg height along cradle ring"
gusset_w        = 4;     // @param number min=2  max=8   step=0.5 unit=mm group=base label="Gusset tangential thickness"

// ----- Drainage -----
scupper_count   = 4;     // @param number min=0  max=8   step=1   group=drain label="Scupper notch count (cut through cradle wall at base)"
scupper_w       = 8;     // @param number min=3  max=20  step=1   unit=mm group=drain label="Scupper notch width (along ring tangent)"
scupper_h       = 3;     // @param number min=1  max=10  step=0.5 unit=mm group=drain label="Scupper notch height above flange top"

// @preset id="default" label="BluTech 8x17 in softener (default)" part="assembly" cyl_d=203.2 cyl_h=431.8 clearance=1.5 cradle_h=85 ring_wall_t=3 top_chamfer=2 flange_t=4 flange_overhang=30 gusset_count=6 gusset_h=50 gusset_w=4 scupper_count=4 scupper_w=8 scupper_h=3

// === Derived ===

cradle_id = cyl_d + 2 * clearance;
cradle_ir = cradle_id / 2;
cradle_or = cradle_ir + ring_wall_t;
flange_or = cradle_or + flange_overhang;

total_h   = flange_t + cradle_h;

// PRINT_ANCHOR_BBOX: outermost footprint × full height.
PRINT_ANCHOR_BBOX = [2 * flange_or, 2 * flange_or, total_h];

// === Geometry — flange + cradle ring (one solid, one inner hole) ===
//
// v1 built the flange and the cradle ring as two separate
// linear_extrude(difference) annuli union'd at z=flange_t. openscad
// ≥2025.09.06 (the Docker image we now use in CI) left non-manifold
// edges at the shared inner cylinder r=cradle_ir, z=flange_t±eps
// (st-7o3). The fix: build the OUTER profile (wide flange + narrower
// ring stack) as one union of solid cylinders, then subtract a
// SINGLE through-hole cylinder at r=cradle_ir. The inner cylinder
// becomes one continuous boundary, no overlap, no T-junctions.

module _flange_and_ring() {
    eps = 0.01;
    difference() {
        union() {
            // Wide flange disk: r=flange_or, z=0..flange_t.
            cylinder(r = flange_or, h = flange_t);
            // Narrower ring above, overlapping the flange by eps so
            // the union step at z=flange_t merges cleanly.
            translate([0, 0, flange_t - eps])
                cylinder(r = cradle_or, h = cradle_h + eps);
        }
        // ONE through-hole at r=cradle_ir spanning from below the
        // VHB face to above the cradle top — produces a single
        // continuous inner cylinder boundary in the resulting solid.
        translate([0, 0, -eps])
            cylinder(r = cradle_ir,
                     h = flange_t + cradle_h + 2 * eps);
    }
}

// Inside top edge chamfer — a thin tapered ring subtracted from the
// cradle top so the cylinder slides in without catching the lip.
// Both ends of the chamfer cone overshoot the cradle by eps so the
// CGAL subtraction in openscad ≥2025.09.06 doesn't leave T-junctions
// at the chamfer's bottom (z=cradle_top-top_chamfer) or top (z=
// cradle_top) plane (st-7o3).
module _top_chamfer_cut() {
    if (top_chamfer > 0) {
        z_top = flange_t + cradle_h;
        eps   = 0.1;
        translate([0, 0, z_top - top_chamfer - eps])
            cylinder(h = top_chamfer + 2 * eps,
                     r1 = cradle_ir - eps,
                     r2 = cradle_ir + top_chamfer + eps);
    }
}

// === Geometry — gussets ===

// One radial gusset: a right-triangle prism in a vertical plane,
// radial line from pipe-axis at angle `theta`. Triangle vertices:
//   inner-bottom  at (cradle_or, 0, flange_t)
//   outer-bottom  at (flange_or, 0, flange_t)
//   inner-top     at (cradle_or, 0, flange_t + gusset_h)
// Thickness gusset_w along the tangential direction (Y after the
// initial rotate).
module _gusset(theta) {
    // Epsilon-overlap into the flange top (st-7o3): drop the gusset
    // 0.1 mm below z=flange_t (the same overlap as _cradle_ring) so
    // the gusset's bottom face merges INTO the flange rather than
    // sitting coincident with the flange top. Grow the vertical leg
    // by the same amount so the triangle profile above z=flange_t
    // is unchanged.
    eps = 0.1;
    rotate([0, 0, theta])
        translate([0, -gusset_w / 2, flange_t - eps])
            rotate([90, 0, 0])
                linear_extrude(height = gusset_w)
                    polygon(points = [
                        [cradle_or, 0],
                        [flange_or, 0],
                        [cradle_or, gusset_h + eps],
                    ]);
}

module _gussets() {
    if (gusset_count > 0) {
        for (i = [0 : gusset_count - 1])
            _gusset(i * 360 / gusset_count);
    }
}

// === Geometry — scupper drains through cradle ring wall ===

// One scupper: a rectangular cutout that breaches the cradle ring
// wall from inside to outside at the base. Cuts from z = flange_t
// (just above the VHB face — never INTO the VHB face) up to
// z = flange_t + scupper_h.
module _scupper_cut(theta) {
    // Cut deep enough into both sides of the ring wall (cradle_ir
    // and cradle_or) that no CSG boundary face is coincident with
    // the ring's surfaces. The top face of the scupper at z=flange_t
    // + scupper_h + eps overshoots the ring material above so the
    // subtraction doesn't leave a T-junction (st-7o3).
    eps = 0.5;
    z_overshoot = 0.1;
    rotate([0, 0, theta])
        translate([cradle_ir - eps,
                   -scupper_w / 2,
                   flange_t + 0.01])
            cube([ring_wall_t + 2 * eps,
                  scupper_w,
                  scupper_h + z_overshoot]);
}

// Public helper: angular position of the i-th scupper (in degrees).
// Lifted out of the cut module so the invariants sidecar can call
// the same function to assert no notch lands on a gusset.
//
// Geometry (st-4t8): each scupper sits at a MIDPOINT between two
// adjacent gussets, never on a gusset. With gusset_count gussets at
// angles {i · 360/gusset_count}, the available midpoints are at
// {i · 360/gusset_count + 180/gusset_count}. For scupper_count ≤
// gusset_count, distribute the scupper count across the midpoints
// via floor(i · gusset_count / scupper_count) — picks evenly-spread
// midpoints when scupper_count divides gusset_count, biased-but-
// never-overlapping otherwise (e.g. 4 scuppers / 6 gussets lands
// scuppers at the 0,1,3,4-th midpoints = 30°, 90°, 210°, 270°).
function scupper_angle_deg(i) =
    (gusset_count > 0)
        ? let(midpoint_idx = floor(i * gusset_count / scupper_count))
          midpoint_idx * (360 / gusset_count) + (180 / gusset_count)
        : i * (360 / scupper_count);

module _scupper_cuts() {
    if (scupper_count > 0) {
        for (i = [0 : scupper_count - 1])
            _scupper_cut(scupper_angle_deg(i));
    }
}

// === Assembly ===

module foot() {
    difference() {
        union() {
            _flange_and_ring();
            _gussets();
        }
        _top_chamfer_cut();
        _scupper_cuts();
    }
}

// Translucent phantom of the softener cylinder, sitting on the RV
// floor (z=0) inside the cradle ring. Excluded from STL by the %
// modifier. Toggle via part = "assembly_with_cylinder".
module _phantom_cylinder() {
    %cylinder(d = cyl_d, h = cyl_h);
}

if (part == "assembly_with_cylinder") {
    foot();
    _phantom_cylinder();
} else {
    foot();
}
