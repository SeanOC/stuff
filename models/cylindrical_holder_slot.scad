// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Multiboard-mounted holder for a cylindrical item — Multiconnect slot variant.
// Consolidates four earlier _slot variants (42mm, 46mm, 70mm, 77mm) that shared
// an identical backer + cradle + gusset pattern and differed only in tunable
// numbers (st-0br). All previously-fixed choices are now @param-exposed so any
// of the four historic configurations is reachable without editing this file.
//
// Historic presets (dial via the param editor):
//   42mm cylinder: can_diameter=42, clearance=0.25, ring_height=50,
//                  gusset_back_w=20, gusset_front_w=8,  gusset_depth=6,
//                  gusset_bottom_chamfer=true
//   46mm cylinder: can_diameter=46, clearance=0.25, ring_height=50,
//                  gusset_back_w=46, gusset_front_w=30, gusset_depth=10,
//                  gusset_bottom_chamfer=false   // st-skn: bed-adhesion tweak
//   70mm spraycan: can_diameter=70, clearance=0.75, ring_height=35,
//                  gusset_back_w=28, gusset_front_w=10, gusset_depth=6,
//                  gusset_bottom_chamfer=true
//   77mm spraycan: can_diameter=77, clearance=0.75, ring_height=35,
//                  gusset_back_w=32, gusset_front_w=10, gusset_depth=6,
//                  gusset_bottom_chamfer=true

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>

$fn = 64;

// === User-tunable parameters ===
can_diameter          = 70;    // @param number min=20 max=200 step=0.5 unit=mm group=item label="Item diameter"
clearance             = 0.5;   // @param number min=0 max=2 step=0.05 unit=mm group=item label="Slip clearance"
ring_height           = 40;    // @param number min=5 max=200 step=1 unit=mm group=ring label="Ring height"
wall                  = 3;     // @param number min=1 max=10 step=0.5 unit=mm group=ring label="Wall thickness"
cup_depth             = 5;     // @param number min=0 max=30 step=0.5 unit=mm group=ring label="Drip-cup depth"
cup_floor             = 2;     // drip-cup floor thickness (mm)
front_opening_deg     = 120;   // @param number min=0 max=270 step=5 unit=deg group=ring label="Front opening arc"

// Multiconnect slot backer
slot_count            = 2;     // @param integer min=1 max=6 group=mount label="Slot count"
slot_spacing_mm       = 25;    // Multiconnect pitch (25mm standard)
slot_region_height    = 75;    // @param number min=25 max=150 step=5 unit=mm group=mount label="Slot region height"
top_band_height       = 5;     // solid band above topmost slot mouth
backer_thickness      = 6.5;   // library default; accommodates slot depth

// Edge treatments + structural gusset. Gusset trapezoid bonds the
// backer-to-cradle joint; wider/deeper values brace heavier rings
// (77mm: 32/10/6) or boost build-plate adhesion (46mm: 46/30/10 with
// bottom chamfer dropped — st-skn).
outer_chamfer         = 1.0;
inner_chamfer         = 0.5;
gusset_back_w         = 28;    // @param number min=5 max=60 step=1 unit=mm group=gusset label="Gusset back width"
gusset_front_w        = 10;    // @param number min=2 max=40 step=1 unit=mm group=gusset label="Gusset front width"
gusset_depth          = 6;     // @param number min=2 max=20 step=0.5 unit=mm group=gusset label="Gusset depth"
gusset_bottom_chamfer = true;  // @param boolean group=gusset label="Chamfer gusset bottom (false = max bed adhesion)"

// Historic presets — four configurations that existed as separate
// .scad files before st-0br consolidated them. Each was
// field-tested; keep these as the stock roster the detail page
// surfaces in the left rail. (st-1j9)
// @preset id="42mm-cylinder"  label="42mm cylinder"  can_diameter=42 clearance=0.25 ring_height=50 gusset_back_w=20 gusset_front_w=8  gusset_depth=6  gusset_bottom_chamfer=true
// @preset id="46mm-cylinder"  label="46mm cylinder"  can_diameter=46 clearance=0.25 ring_height=50 gusset_back_w=46 gusset_front_w=30 gusset_depth=10 gusset_bottom_chamfer=false
// @preset id="70mm-spraycan"  label="70mm spraycan"  can_diameter=70 clearance=0.75 ring_height=35 gusset_back_w=28 gusset_front_w=10 gusset_depth=6  gusset_bottom_chamfer=true
// @preset id="77mm-spraycan"  label="77mm spraycan"  can_diameter=77 clearance=0.75 ring_height=35 gusset_back_w=32 gusset_front_w=10 gusset_depth=6  gusset_bottom_chamfer=true

// === Derived ===
ring_id       = can_diameter + 2 * clearance;
ring_od       = ring_id + 2 * wall;
backer_w      = slot_count * slot_spacing_mm;
backer_height = slot_region_height + top_band_height;

// === Layout ===
// X horizontal across backer, Y depth, Z vertical with item axis parallel
// to Z. Backer's -Y face slides onto the Multiboard wall; cradle extends
// into +Y. Cup/ring anchor at the bottom of the multiconnect region so
// absolute positions match the pre-consolidation variants.

ring_cy    = backer_thickness / 2 + ring_od / 2;
cup_z0     = -slot_region_height / 2;
ring_z0    = cup_z0 + cup_depth;
cradle_h   = cup_depth + ring_height;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at defaults.
// X: max(backer_w=50, ring_od=77) = 77
// Y: backer_thickness(6.5) + ring_od(77) = 83.5
// Z: backer_height(80) > cup_depth+ring_height(45)
PRINT_ANCHOR_BBOX = [77, 83.5, 80];

// === Geometry ===

module multiconnect_backer() {
    multiconnectGenerator(
        width = backer_w,
        height = slot_region_height,
        multiconnectPartType = "Backer",
        distanceBetweenSlots = slot_spacing_mm,
        slotOrientation = "Vertical"
    );
}

// Solid cap above the multiconnect slot mouths. multiconnectGenerator anchors
// each slot's rounded-end opening to the top of its cuboid with shiftout=0.01,
// so without this band the slot domes break the panel's top edge.
module top_band() {
    translate([0, 0, slot_region_height / 2 - 0.01])
        linear_extrude(top_band_height + 0.01)
            square([backer_w, backer_thickness], center = true);
}

module cradle() {
    opening_half = front_opening_deg / 2;
    difference() {
        union() {
            translate([0, ring_cy, ring_z0])
                cyl(h = ring_height, d = ring_od,
                    chamfer2 = outer_chamfer, anchor = BOTTOM);
            translate([0, ring_cy, cup_z0])
                cyl(h = cup_depth, d = ring_od,
                    chamfer1 = outer_chamfer, anchor = BOTTOM);
        }
        translate([0, ring_cy, ring_z0 - 0.1])
            cylinder(h = ring_height + 0.2, d = ring_id);
        translate([0, ring_cy, cup_z0 + cup_floor])
            cylinder(h = cup_depth - cup_floor + 0.1, d = ring_id);
        // Lead-in chamfer at top of bore.
        translate([0, ring_cy, ring_z0 + ring_height - inner_chamfer])
            cylinder(h = inner_chamfer + 0.01,
                     d1 = ring_id,
                     d2 = ring_id + 2 * inner_chamfer);
        // Open-front wedge faces +Y.
        translate([0, ring_cy, ring_z0 - 0.1])
            linear_extrude(height = ring_height + 0.2)
                polygon(concat(
                    [[0, 0]],
                    [for (a = [90 - opening_half : 2 : 90 + opening_half])
                        [(ring_od + 10) * cos(a), (ring_od + 10) * sin(a)]]
                ));
    }
}

// Trapezoidal fillet bonding the backer to the ring wall. gusset_bottom_chamfer
// controls whether the build-plate-facing edge is chamfered (true — cosmetic on
// lighter variants) or left square (false — st-skn's fix for corner-curling on
// the 46mm where the backer's bed contact is a thin 50×6.5 strip).
module gusset() {
    back_y  = backer_thickness / 2 - 0.05;
    front_y = backer_thickness / 2 + gusset_depth;
    trap = [
        [-gusset_back_w / 2,  back_y],
        [ gusset_back_w / 2,  back_y],
        [ gusset_front_w / 2, front_y],
        [-gusset_front_w / 2, front_y],
    ];
    difference() {
        translate([0, 0, cup_z0])
            if (gusset_bottom_chamfer)
                offset_sweep(trap, height = cradle_h,
                             top    = os_chamfer(height = outer_chamfer),
                             bottom = os_chamfer(height = outer_chamfer));
            else
                offset_sweep(trap, height = cradle_h,
                             top    = os_chamfer(height = outer_chamfer));
        translate([0, ring_cy, cup_z0 - 0.1])
            cylinder(h = cradle_h + 0.2, d = ring_id);
    }
}

// Sibling expressions at root: multiconnectGenerator uses BOSL2 diff()
// tags internally and breaks when nested inside an outer union().
multiconnect_backer();
top_band();
cradle();
gusset();
