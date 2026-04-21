// Multiboard-mounted holder for 70mm spray can — Multiconnect slot variant.
// Open-front C-ring cradle + drip cup + slide-on Multiconnect slot backer.
// v2 of st-ivh (snap variant). Uses QuackWorks Multiconnect slot instead of
// the snap connector; both paths are now patch-free at the pin in
// libs/README.md (BOSL2 456fcd8, QuackWorks 6123129).

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>

$fn = 64;

// === User-tunable parameters ===
can_diameter       = 70;     // @param number min=30 max=200 step=0.5 label="Can diameter (mm)"
clearance          = 0.75;   // @param number min=0 max=2 step=0.05 label="Slip clearance (mm)"
ring_height        = 35;     // @param number min=10 max=200 step=1 label="Ring height (mm)"
wall               = 3;      // @param number min=1 max=10 step=0.5 label="Wall thickness (mm)"
cup_depth          = 5;      // @param number min=0 max=30 step=0.5 label="Drip-cup depth (mm)"
cup_floor          = 2;      // drip-cup floor thickness (mm)
front_opening_deg  = 120;    // @param number min=0 max=270 step=5 label="Front opening arc (deg)"

// Multiconnect slot backer
slot_count         = 2;      // @param integer min=1 max=6 label="Slot count"
slot_spacing_mm    = 25;     // Multiconnect pitch (25mm standard)
slot_region_height = 75;     // @param number min=25 max=150 step=5 label="Slot region height (mm)"
top_band_height    = 5;      // solid band above the topmost slot mouth (st-6zw: keeps top edge continuous)
backer_thickness   = 6.5;    // library default; accommodates slot depth (~4.15mm)

// Edge treatments + structural gusset (st-8nc)
outer_chamfer      = 1.0;    // outer/touchable edges (top of ring, bottom of cup)
inner_chamfer      = 0.5;    // can-entry lead-in at top of bore
gusset_back_w      = 28;     // trapezoid width where gusset meets backer (mm)
gusset_front_w     = 10;     // trapezoid width where gusset meets ring wall (mm)
gusset_depth       = 6;      // gusset reach from backer into +Y (mm)

// === Derived ===
ring_id       = can_diameter + 2 * clearance;               // 71.5
ring_od       = ring_id + 2 * wall;                         // 77.5
backer_w      = slot_count * slot_spacing_mm;               // 50 at default
backer_height = slot_region_height + top_band_height;       // total printed Z extent (80)

// === Layout ===
// X — horizontal across backer
// Y — depth. multiconnectGenerator produces a cuboid centered at origin
//     with slot openings on its -Y face (BOSL2 FRONT). That face slides
//     onto the Multiboard wall, so the accessory (cradle) extends into
//     +Y (away from the wall).
// Z — vertical; can axis parallel to Z. The multiconnect region is
//     centered at origin (z = -slot_region_height/2 .. +slot_region_height/2);
//     the top band sits above it. Cup/ring anchor at the bottom of the
//     multiconnect region so their absolute position matches v2 (st-ljl).

ring_cy    = backer_thickness / 2 + ring_od / 2;  // ring center in +Y
cup_z0     = -slot_region_height / 2;             // cup floor at bottom of multiconnect region
ring_z0    = cup_z0 + cup_depth;
cradle_h   = cup_depth + ring_height;             // total Z extent of cup + ring stack

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z).
// X: max(backer_w=50, ring_od=77.5) = 77.5
// Y: backer_thickness(6.5) + ring_od(77.5) = 84
// Z: backer_height(80) > cup_depth+ring_height(40)
PRINT_ANCHOR_BBOX = [77.5, 84, 80];

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
            // Ring: chamfer the top (touchable + visual).
            translate([0, ring_cy, ring_z0])
                cyl(h = ring_height, d = ring_od,
                    chamfer2 = outer_chamfer, anchor = BOTTOM);
            // Drip cup: chamfer the bottom (touchable + first-layer release).
            translate([0, ring_cy, cup_z0])
                cyl(h = cup_depth, d = ring_od,
                    chamfer1 = outer_chamfer, anchor = BOTTOM);
        }
        translate([0, ring_cy, ring_z0 - 0.1])
            cylinder(h = ring_height + 0.2, d = ring_id);
        translate([0, ring_cy, cup_z0 + cup_floor])
            cylinder(h = cup_depth - cup_floor + 0.1, d = ring_id);
        // Lead-in chamfer at top of can bore: conical frustum widening upward
        // makes the can drop in without scraping the ring's top inner edge.
        translate([0, ring_cy, ring_z0 + ring_height - inner_chamfer])
            cylinder(h = inner_chamfer + 0.01,
                     d1 = ring_id,
                     d2 = ring_id + 2 * inner_chamfer);
        // Open-front wedge faces +Y (away from the backer).
        translate([0, ring_cy, ring_z0 - 0.1])
            linear_extrude(height = ring_height + 0.2)
                polygon(concat(
                    [[0, 0]],
                    [for (a = [90 - opening_half : 2 : 90 + opening_half])
                        [(ring_od + 10) * cos(a), (ring_od + 10) * sin(a)]]
                ));
    }
}

// Trapezoidal fillet bonding the backer to the ring wall. Widens the
// backer-to-cradle bonded region so the cradle is less prone to peeling
// off the backer under load. Subtracts the can bore so it never intrudes.
module gusset() {
    back_y  = backer_thickness / 2 - 0.05;        // slight overlap into backer
    front_y = backer_thickness / 2 + gusset_depth;
    trap = [
        [-gusset_back_w / 2,  back_y],
        [ gusset_back_w / 2,  back_y],
        [ gusset_front_w / 2, front_y],
        [-gusset_front_w / 2, front_y],
    ];
    difference() {
        // offset_sweep default anchor is "base" (bottom at z=0); translate
        // by cup_z0 so the gusset spans the full cradle height (cup + ring).
        translate([0, 0, cup_z0])
            offset_sweep(trap, height = cradle_h,
                         top    = os_chamfer(height = outer_chamfer),
                         bottom = os_chamfer(height = outer_chamfer));
        // Keep gusset clear of the can bore.
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
