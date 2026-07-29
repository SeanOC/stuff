// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// KidsCleanCar speed-knob childproof cover — friction-fit over the lower flange.
//
// A dome/cup that slips over the speed-adjust knob assembly on a
// KidsCleanCar kids' ride-on and grips the LOWER FLANGE RING only, so a
// toddler can't change the speed. The lock is DECOUPLING, not a latch:
// the cover rides on a round bore over the round flange (no anti-rotation
// feature), so twisting the cover just spins it — the motion never
// reaches the knob. Removal is a straight axial pull, which a small child
// does poorly; a single adult pry recess at the rim takes a coin/finger-
// nail. Nothing on the vehicle is modified: the 3 stock screws stay put,
// fully reversible.
//
// === How it grips (the design problem) ===
//
// The flange's grip band above the deck is only flange_h = 3.15mm tall —
// far too short for a plain interference bore to hold reliably (a 48mm
// press-fit over 3mm of engagement either won't seat or splits). Instead
// the bore clears the flange by fit_clearance and RETENTION comes from
// rib_count VERTICAL CRUSH RIBS standing proud of the bore wall. Each rib
// tip sits rib_interference PAST the flange edge, so seating the cover
// crushes the rib tips a predictable amount — ribs deform and spring back
// (PETG-friendly) and survive repeated re-fits where a solid interference
// bore would not. rib_count and rib_interference are the per-printer
// tuning knobs; print, test the pull-off force, retune.
//
// The ribs engage the flange EDGE ONLY (a short band low in the bore).
// Above them the interior opens out into two clearance pockets so nothing
// else touches the vehicle:
//   * an ANNULUS pocket clearing the 3 proud screw heads
//     (screw_head_h) by screw_clear, and
//   * a deeper central KNOB CAVITY (knob_cav_d wide, roofed knob_vclear
//     above the knob top) so the knob floats free and untouched even when
//     the cover is pressed down and spun.
//
// === Print orientation (native): MOUTH UP, zero supports ===
//
// Print the cover MOUTH-UP — the closed dome/top face flat on the bed,
// the open skirt mouth pointing up. In this orientation every interior
// ceiling (the annulus pocket roof and the knob-cavity roof) becomes an
// UP-FACING floor, fully backed by the solid it was cut from, so the wide
// interior spans never bridge. The only exterior overhang is the top-edge
// chamfer (top_chamfer), which prints against the bed as a self-support-
// ing 45deg flare. The skirt's mouth rim is the last thing printed. No
// supports anywhere. (Printing mouth-DOWN would leave the ~48mm interior
// roof as an unsupported ceiling — don't.)
//
// The interior is a single stepped rotate_extrude profile (bore ->
// annulus pocket -> knob cavity -> capped top), so the shell is one clean
// axisymmetric body; the crush ribs weld bury into the bore wall (st-v7k:
// no face-kissing unions) and the pry recess is a single rim cut.

$fn = 128;   // round-dominant revolved part

// === User-tunable parameters ===

// ----- Measured vehicle geometry (calipers, mm) -----
flange_d    = 48.1;  // @param number min=30 max=90 step=0.1 unit=mm group=vehicle label="Flange OD (grip target)"
flange_h    = 3.15;  // @param number min=1.5 max=12 step=0.05 unit=mm group=vehicle label="Flange height above deck (grip band)"
knob_d      = 29.5;  // @param number min=10 max=60 step=0.1 unit=mm group=vehicle label="Centre knob OD"
knob_h      = 6.1;   // @param number min=2 max=30 step=0.1 unit=mm group=vehicle label="Knob height above flange"
screw_head_h = 2.5;  // @param number min=0 max=8 step=0.1 unit=mm group=vehicle label="Screw-head proud height above flange"

// ----- Fit / clearances -----
fit_clearance = 0.3;  // @param number min=0 max=1.5 step=0.05 unit=mm group=fit label="Bore radial clearance over flange"
knob_clear   = 1.25;  // @param number min=0.5 max=5 step=0.05 unit=mm group=fit label="Knob cavity radial clearance"
knob_vclear  = 1.9;   // @param number min=0.5 max=6 step=0.1 unit=mm group=fit label="Clearance over knob top (Z)"
screw_clear  = 2.0;   // @param number min=0.5 max=6 step=0.1 unit=mm group=fit label="Clearance over screw heads (Z)"
skirt_gap    = 0.5;   // @param number min=0 max=4 step=0.1 unit=mm group=fit label="Skirt-bottom gap above deck"

// ----- Crush ribs (the retention tuning knobs) -----
rib_count        = 6;    // @param integer min=3 max=12 group=ribs label="Number of crush ribs"
rib_interference = 0.2;  // @param number min=0 max=0.8 step=0.05 unit=mm group=ribs label="Rib interference past flange edge"
rib_width        = 1.6;  // @param number min=0.8 max=4 step=0.1 unit=mm group=ribs label="Rib tangential width"

// ----- Body -----
wall        = 2.4;  // @param number min=1.2 max=5 step=0.1 unit=mm group=body label="Wall / roof thickness"
top_chamfer = 1.0;  // @param number min=0 max=3 step=0.1 unit=mm group=body label="Top outer-edge chamfer"

// ----- Adult pry recess -----
pry_notch   = true; // @param boolean group=pry label="Pry recess at the rim (coin/fingernail)"
pry_notch_w = 12;   // @param number min=6 max=24 step=0.5 unit=mm group=pry label="Pry recess width (tangential)"
pry_notch_h = 3.5;  // @param number min=1.5 max=8 step=0.1 unit=mm group=pry label="Pry recess height up the skirt"

// @preset id="default" label="KidsCleanCar (measured)" flange_d=48.1 flange_h=3.15 knob_d=29.5 knob_h=6.1 rib_count=6 rib_interference=0.2 wall=2.4 pry_notch=true
// @preset id="tight_grip" label="Tighter grip (8 ribs, 0.3mm)" rib_count=8 rib_interference=0.3
// @preset id="no_pry" label="No pry recess (max child-resistance)" pry_notch=false

// === Derived ===

// Zero-overlap (face-kissing) unions leave detached shells / non-manifold
// tangent edges (st-v7k): weld the ribs this far into the bore wall.
bury = 0.3;
eps  = 0.1;

// Radii (deck centre at the origin; z = 0 is the deck surface).
flange_r  = flange_d / 2;
bore_r    = flange_r + fit_clearance;          // bore clears the flange
skirt_or  = bore_r + wall;                     // outer skirt radius
knob_cav_r = knob_d / 2 + knob_clear;          // knob cavity radius
rib_tip_r = flange_r - rib_interference;       // rib tip bites past the edge
rib_outer = bore_r + bury;                     // rib root welded into wall

// Z stack above the deck.
knob_top_z    = flange_h + knob_h;                 // 9.25
screw_top_z   = flange_h + screw_head_h;           // 5.65
annulus_roof_z = screw_top_z + screw_clear;        // 7.65 (screw pocket roof)
knob_roof_z   = knob_top_z + knob_vclear;          // 11.15 (knob cavity roof)
top_z         = knob_roof_z + wall;                // 13.55 (exterior top)

// Ribs span the flange band (from the skirt mouth up just past the flange
// top), staying clear of the proud screw heads above.
rib_z0    = skirt_gap;                              // 0.5
rib_top_z = flange_h + 1;                           // 4.15

// Pry recess lands in a between-rib gap (half a rib pitch off a rib), so
// it never eats a crush rib no matter the rib count.
pry_angle = 180 / rib_count;

// PRINT_ANCHOR_BBOX at defaults (literal numbers — the invariants gate
// fails on >1mm drift from the exported STL):
//   X = Y = skirt_od = flange_d + 2*fit_clearance + 2*wall
//                    = 48.1 + 0.6 + 4.8            = 53.5
//   Z = top_z - skirt_gap
//     = (flange_h + knob_h + knob_vclear + wall) - skirt_gap
//     = (3.15 + 6.1 + 1.9 + 2.4) - 0.5            = 13.05
PRINT_ANCHOR_BBOX = [53.5, 53.5, 13.05];

// === Shell ===

// Right-half (r, z) cross-section of the axisymmetric cover, walked outer
// contour bottom->top then inner contour top->bottom. rotate_extrude
// sweeps it into the one-piece stepped cup (bore -> screw annulus pocket
// -> deep knob cavity -> capped top with a chamfered outer rim).
shell_profile = [
    [skirt_or,               skirt_gap],           // skirt bottom outer
    [skirt_or,               top_z - top_chamfer],  // up the outer wall
    [skirt_or - top_chamfer, top_z],                // top-edge chamfer
    [0,                      top_z],                // top centre
    [0,                      knob_roof_z],          // knob cavity roof centre
    [knob_cav_r,             knob_roof_z],          // knob cavity roof rim
    [knob_cav_r,             annulus_roof_z],       // step down to annulus
    [bore_r,                 annulus_roof_z],       // annulus pocket roof
    [bore_r,                 skirt_gap],            // down the bore to mouth
];

module shell() {
    rotate_extrude(convexity = 4) polygon(shell_profile);
}

// === Crush ribs ===

// One vertical crush rib, drawn in the (r, z) plane and extruded
// tangentially by rib_width. The tip stands at rib_tip_r (rib_interference
// past the flange edge); the root welds bury into the bore wall. The
// bottom edge is a 45deg lead-in ramp so the flange self-centres on seating.
rib_profile = [
    [rib_tip_r, rib_z0 + (rib_outer - rib_tip_r)],  // top of the lead-in ramp
    [rib_tip_r, rib_top_z],                          // tip, top
    [rib_outer, rib_top_z],                          // root, top
    [rib_outer, rib_z0],                             // root, bottom
];

module rib() {
    rotate([90, 0, 0])
        linear_extrude(rib_width, center = true)
            polygon(rib_profile);
}

module ribs() {
    for (i = [0 : rib_count - 1])
        rotate([0, 0, i * 360 / rib_count]) rib();
}

// === Adult pry recess ===

// A single rectangular window cut through the skirt wall at the mouth rim,
// so an adult can slip a coin/fingernail under the cover and lever it off.
// Everywhere else the skirt runs down to skirt_gap above the deck, leaving
// nothing for a child to grab.
module pry_cut() {
    r_in  = bore_r - 1;
    r_out = skirt_or + 1;
    rotate([0, 0, pry_angle])
        translate([(r_in + r_out) / 2, 0, skirt_gap + pry_notch_h / 2])
            cube([r_out - r_in, pry_notch_w, pry_notch_h + 2 * eps], center = true);
}

// === Assembly ===

difference() {
    union() {
        shell();
        ribs();
    }
    if (pry_notch) pry_cut();
}
