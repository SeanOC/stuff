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
// the open skirt mouth pointing up. The exported STL is ALREADY IN THIS
// ORIENTATION: the model is authored in the deck frame for readable math
// then flipped roof-down in the final assembly, so the dome sits at z = 0
// (on the bed) and the mouth rim is at max Z. Slice as-is, no rotation.
// In this orientation every interior ceiling (the annulus pocket roof and
// the knob-cavity roof) becomes an UP-FACING floor, fully backed by the
// solid it was cut from, so the wide interior spans never bridge. The only
// exterior overhang is the top-edge chamfer (top_chamfer), which prints
// against the bed as a self-supporting 45deg flare. The skirt's mouth rim
// is the last thing printed. No supports anywhere. (Printing mouth-DOWN
// would leave the ~48mm interior roof as an unsupported ceiling — don't.)
//
// The interior is a single stepped rotate_extrude profile (bore ->
// annulus pocket -> knob cavity -> capped top), so the shell is one clean
// axisymmetric body; the crush ribs weld bury into the bore wall (st-v7k:
// no face-kissing unions) and the pry recess is a single rim cut.

$fn = 128;   // round-dominant revolved part

// === User-tunable parameters ===

// ----- Measured vehicle geometry (calipers, mm) -----
// min set so the smallest flange still fits the DEFAULT knob's cleared
// cavity plus a screw annulus inside its bore (the domain assert below
// covers flange_d/knob_d combinations that a single bound can't express).
flange_d    = 48.1;  // @param number min=34 max=90 step=0.1 unit=mm group=vehicle label="Flange OD (grip target)"
flange_h    = 3.15;  // @param number min=1.5 max=12 step=0.05 unit=mm group=vehicle label="Flange height above deck (grip band)"
// max keeps the cleared cavity inside the DEFAULT flange's bore; a knob
// too big for its actual flange is caught by the domain assert below
// (knob_cav_r + annulus_min <= bore_r), not silently mis-rendered.
knob_d      = 29.5;  // @param number min=10 max=44 step=0.1 unit=mm group=vehicle label="Centre knob OD"
knob_h      = 6.1;   // @param number min=2 max=30 step=0.1 unit=mm group=vehicle label="Knob height above flange"
screw_head_h = 2.5;  // @param number min=0 max=8 step=0.1 unit=mm group=vehicle label="Screw-head proud height above flange"

// ----- Fit / clearances -----
fit_clearance = 0.3;  // @param number min=0 max=1.5 step=0.05 unit=mm group=fit label="Bore radial clearance over flange"
knob_clear   = 1.25;  // @param number min=0.5 max=5 step=0.05 unit=mm group=fit label="Knob cavity radial clearance"
knob_vclear  = 1.9;   // @param number min=0.5 max=6 step=0.1 unit=mm group=fit label="Clearance over knob top (Z)"
screw_clear  = 2.0;   // @param number min=0.5 max=6 step=0.1 unit=mm group=fit label="Clearance over screw heads (Z)"
// max leaves >=2mm rib/flange overlap at the DEFAULT flange_h (3.15-1.0);
// smaller flanges are handled by the derived skirt_z0 clamp below, so the
// skirt always reaches down past the flange top to grip it.
skirt_gap    = 0.5;   // @param number min=0 max=1 step=0.1 unit=mm group=fit label="Skirt-bottom gap above deck"

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

// Radii (deck centre at the origin; z = 0 is the deck surface). The cover
// tracks the flange: the bore clears the flange OD, the OD is that plus a
// wall. The knob cavity ALWAYS clears the knob by knob_clear (never
// shrunk — a smaller cavity would let the cover touch/turn the knob), and
// the domain assert below guarantees it fits inside the bore with a real
// screw annulus, so we never grow the body off the flange nor clamp the
// cavity into the knob.
annulus_min = 0.6;                             // min screw-pocket ring width
flange_r  = flange_d / 2;
bore_r    = flange_r + fit_clearance;          // bore clears the flange
skirt_or  = bore_r + wall;                     // outer skirt radius
knob_cav_r = knob_d / 2 + knob_clear;          // cavity always clears the knob
rib_tip_r = flange_r - rib_interference;       // rib tip bites past the flange edge
rib_outer = bore_r + bury;                     // rib root welded into wall

// Z stack above the deck. The exterior roof sits a full `wall` above the
// HIGHER of the two interior roofs (knob cavity vs screw annulus), so a
// deep screw-clearance pocket can never punch through the top (which would
// make a non-closed mesh) — it just makes the cover taller.
knob_top_z    = flange_h + knob_h;                 // 9.25
screw_top_z   = flange_h + screw_head_h;           // 5.65
annulus_roof_z = screw_top_z + screw_clear;        // 7.65 (screw pocket roof)
knob_roof_z   = knob_top_z + knob_vclear;          // 11.15 (knob cavity roof)
top_z         = max(knob_roof_z, annulus_roof_z) + wall;   // 13.55 (exterior top)

// Effective skirt-bottom height. The skirt must reach DOWN past the flange
// top to grip it, so the requested skirt_gap is clamped so the mouth always
// sits at least engage_min below the flange top — this guarantees rib/flange
// overlap even at the flange_h minimum (where a raw skirt_gap could exceed
// flange_h and lift every rib off the flange). engage_min exceeds the rib
// lead-in ramp so a band of FULL-depth rib still bites the flange (grip =
// engage_min - lead-in). At defaults skirt_z0 == skirt_gap.
engage_min = 1.5;
skirt_z0 = max(0, min(skirt_gap, flange_h - engage_min));  // 0.5 default

// Ribs span from the skirt mouth up just past the flange top, staying clear
// of the proud screw heads above.
rib_z0    = skirt_z0;                               // 0.5
rib_top_z = flange_h + 1;                           // 4.15

// Pry recess lands in a between-rib gap (half a rib pitch off a rib), so
// it never eats a crush rib no matter the rib count.
pry_angle = 180 / rib_count;

// === Domain validity ===
//
// Every SINGLE param min/max excursion from the defaults renders valid
// geometry on its own (that's what the @param bounds guarantee). These
// asserts catch the CROSS-parameter combinations that no single bound can
// express, and fail LOUDLY with a fix hint instead of emitting a broken or
// silently-wrong mesh. They never fire for the measured defaults.
assert(knob_cav_r + annulus_min <= bore_r,
       str("knob too large for this flange: cleared knob cavity r=", knob_cav_r,
           "mm + ", annulus_min, "mm screw annulus exceeds the flange bore r=",
           bore_r, "mm. Reduce knob_d/knob_clear or increase flange_d/fit_clearance."));
assert(flange_h - skirt_z0 >= 1.0,
       str("skirt_gap too large for this flange_h: only ", flange_h - skirt_z0,
           "mm of skirt reaches the flange band. Reduce skirt_gap or increase flange_h."));
assert(rib_top_z > rib_z0,
       "rib has no height: rib_top_z <= rib_z0. Increase flange_h or reduce skirt_gap.");

// PRINT_ANCHOR_BBOX at defaults (literal numbers — the invariants gate
// fails on >1mm drift from the exported STL):
//   X = Y = skirt_od = flange_d + 2*fit_clearance + 2*wall
//                    = 48.1 + 0.6 + 4.8            = 53.5
//   Z = top_z - skirt_z0, with top_z = max(knob_roof_z, annulus_roof_z) + wall
//     = (max(3.15+6.1+1.9, 3.15+2.5+2.0) + 2.4) - 0.5
//     = (max(11.15, 7.65) + 2.4) - 0.5            = 13.05
PRINT_ANCHOR_BBOX = [53.5, 53.5, 13.05];

// === Shell ===

// Right-half (r, z) cross-section of the axisymmetric cover, walked outer
// contour bottom->top then inner contour top->bottom. rotate_extrude
// sweeps it into the one-piece stepped cup (bore -> screw annulus pocket
// -> deep knob cavity -> capped top with a chamfered outer rim).
shell_profile = [
    [skirt_or,               skirt_z0],            // skirt bottom outer
    [skirt_or,               top_z - top_chamfer],  // up the outer wall
    [skirt_or - top_chamfer, top_z],                // top-edge chamfer
    [0,                      top_z],                // top centre
    [0,                      knob_roof_z],          // knob cavity roof centre
    [knob_cav_r,             knob_roof_z],          // knob cavity roof rim
    [knob_cav_r,             annulus_roof_z],       // step down to annulus
    [bore_r,                 annulus_roof_z],       // annulus pocket roof
    [bore_r,                 skirt_z0],             // down the bore to mouth
];

module shell() {
    rotate_extrude(convexity = 4) polygon(shell_profile);
}

// === Crush ribs ===

// One vertical crush rib, drawn in the (r, z) plane and extruded
// tangentially by rib_width. The tip stands at rib_tip_r (rib_interference
// past the flange edge); the root welds bury into the bore wall. The
// bottom edge is a 45deg lead-in ramp so the flange self-centres on seating.
// rib_leadin is clamped to the rib's straight height so a shallow rib (large
// skirt_gap) can never invert the polygon into a non-closed mesh.
rib_leadin = max(0, min(rib_outer - rib_tip_r, rib_top_z - rib_z0 - 0.3));
rib_profile = [
    [rib_tip_r, rib_z0 + rib_leadin],                // top of the lead-in ramp
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
        translate([(r_in + r_out) / 2, 0, skirt_z0 + pry_notch_h / 2])
            cube([r_out - r_in, pry_notch_w, pry_notch_h + 2 * eps], center = true);
}

// === Assembly ===
//
// Built above in the deck frame (z = 0 = deck, mouth low, roof high) for
// readable measured math, then flipped ROOF-DOWN into the print frame so
// the exported STL matches the documented support-free orientation: the
// closed dome lands on the bed at z = 0 and the open mouth points up
// (z = top_z - skirt_gap at the rim). rotate([180,0,0]) keeps handedness
// (mirror would flip the pry recess); translate lifts the roof back to z=0.
translate([0, 0, top_z])
    rotate([180, 0, 0])
        difference() {
            union() {
                shell();
                ribs();
            }
            if (pry_notch) pry_cut();
        }
