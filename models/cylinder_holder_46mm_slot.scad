// Multiboard-mounted holder for a 46mm-diameter cylindrical item —
// Multiconnect slot variant. Sibling of cylinder_holder_42mm_slot;
// same backer + cradle + gusset pattern with the bore/OD bumped up
// one notch.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>

$fn = 64;

// === User-tunable parameters ===
can_diameter       = 46;     // @param number min=20 max=200 step=0.5 label="Can diameter (mm)"
clearance          = 0.25;   // @param number min=0 max=2 step=0.05 label="Slip clearance (mm)"
ring_height        = 50;     // @param number min=5 max=200 step=1 label="Ring height (mm)"
wall               = 3;      // @param number min=1 max=10 step=0.5 label="Wall thickness (mm)"
cup_depth          = 5;      // @param number min=0 max=30 step=0.5 label="Drip-cup depth (mm)"
cup_floor          = 2;      // drip-cup floor thickness (mm)
front_opening_deg  = 120;    // @param number min=0 max=270 step=5 label="Front opening arc (deg)"

// Multiconnect slot backer
slot_count         = 2;      // @param integer min=1 max=6 label="Slot count"
slot_spacing_mm    = 25;     // Multiconnect pitch (25mm standard)
slot_region_height = 75;     // @param number min=25 max=150 step=5 label="Slot region height (mm)"
top_band_height    = 5;      // solid band above topmost slot mouth
backer_thickness   = 6.5;    // library default; accommodates slot depth

// Edge treatments + structural gusset. Gusset enlarged for build-plate
// adhesion (st-skn): the backer's bed contact is a thin 50×6.5 strip
// and prints were curling at the corners. Widening the trapezoid so
// it spans nearly the full backer width and reaches past the ring's
// near tangent (Y≈3.25 at X=0) lets the gusset's footprint blend into
// the cup floor, turning two narrow contact patches into one large
// bonded region. The gusset's bottom chamfer is also dropped — it
// faces the build plate, so chamfering it just shrinks first-layer
// area for an invisible edge.
outer_chamfer      = 1.0;
inner_chamfer      = 0.5;
gusset_back_w      = 46;     // ~full backer width (2mm clear each side); was 20
gusset_front_w     = 30;     // wide front so trap embraces the cup tangent zone; was 8
gusset_depth       = 10;     // reach past ring tangent into the cup-wall region; was 6

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
                         top    = os_chamfer(height = outer_chamfer));
        translate([0, ring_cy, cup_z0 - 0.1])
            cylinder(h = cradle_h + 0.2, d = ring_id);
    }
}

multiconnect_backer();
top_band();
cradle();
gusset();
