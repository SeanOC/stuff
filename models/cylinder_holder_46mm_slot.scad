// Multiboard-mounted holder for a 46mm-diameter cylindrical item —
// Multiconnect slot variant. Sibling of cylinder_holder_42mm_slot;
// same backer + cradle + gusset pattern with the bore/OD bumped up
// one notch.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>

$fn = 64;

// === User-tunable parameters ===
can_diameter       = 46;     // nominal item OD (mm)
clearance          = 0.25;   // radial slip between item and ring (mm)
ring_height        = 50;     // C-ring band height along item axis (mm)
wall               = 3;      // wall thickness, ring + cup (mm)
cup_depth          = 5;      // drip-cup depth below ring (mm)
cup_floor          = 2;      // drip-cup floor thickness (mm)
front_opening_deg  = 120;    // C-ring open-front arc angle (deg)

// Multiconnect slot backer
slot_count         = 2;      // number of vertical slots side-by-side
slot_spacing_mm    = 25;     // Multiconnect pitch (25mm standard)
slot_region_height = 75;     // multiconnectGenerator cuboid Z extent
top_band_height    = 5;      // solid band above topmost slot mouth
backer_thickness   = 6.5;    // library default; accommodates slot depth

// Edge treatments + structural gusset. ring_od here is ~52.5 — only
// ~6% larger than the 42mm sibling's 49.5mm, so gusset dimensions
// carry over unchanged.
outer_chamfer      = 1.0;
inner_chamfer      = 0.5;
gusset_back_w      = 20;     // trapezoid width where gusset meets backer (mm)
gusset_front_w     = 8;      // trapezoid width where gusset meets ring wall (mm)
gusset_depth       = 6;      // gusset reach from backer into +Y (mm)

// === Derived ===
ring_id       = can_diameter + 2 * clearance;               // 46.5
ring_od       = ring_id + 2 * wall;                         // 52.5
backer_w      = slot_count * slot_spacing_mm;               // 50
backer_height = slot_region_height + top_band_height;       // 80

// === Layout ===
// X horizontal across backer, Y depth, Z vertical with item axis
// parallel to Z. Backer's -Y face slides onto the Multiboard wall;
// cradle extends into +Y.

ring_cy    = backer_thickness / 2 + ring_od / 2;
cup_z0     = -slot_region_height / 2;
ring_z0    = cup_z0 + cup_depth;
cradle_h   = cup_depth + ring_height;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z).
// X: max(backer_w=50, ring_od=52.5) = 52.5
// Y: backer_thickness(6.5) + ring_od(52.5) = 59
// Z: backer_height(80) > cup_depth+ring_height(55)
PRINT_ANCHOR_BBOX = [52.5, 59, 80];

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
        translate([0, ring_cy, ring_z0 + ring_height - inner_chamfer])
            cylinder(h = inner_chamfer + 0.01,
                     d1 = ring_id,
                     d2 = ring_id + 2 * inner_chamfer);
        translate([0, ring_cy, ring_z0 - 0.1])
            linear_extrude(height = ring_height + 0.2)
                polygon(concat(
                    [[0, 0]],
                    [for (a = [90 - opening_half : 2 : 90 + opening_half])
                        [(ring_od + 10) * cos(a), (ring_od + 10) * sin(a)]]
                ));
    }
}

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
            offset_sweep(trap, height = cradle_h,
                         top    = os_chamfer(height = outer_chamfer),
                         bottom = os_chamfer(height = outer_chamfer));
        translate([0, ring_cy, cup_z0 - 0.1])
            cylinder(h = cradle_h + 0.2, d = ring_id);
    }
}

multiconnect_backer();
top_band();
cradle();
gusset();
