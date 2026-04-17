// Multiboard-mounted holder for 70mm spray can — Multiconnect slot variant.
// Open-front C-ring cradle + drip cup + slide-on Multiconnect slot backer.
// v2 of st-ivh (snap variant). Uses QuackWorks Multiconnect slot instead of
// the snap connector; both paths are now patch-free at the pin in
// libs/README.md (BOSL2 456fcd8, QuackWorks 6123129).

include <BOSL2/std.scad>
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>

$fn = 64;

// === User-tunable parameters ===
can_diameter       = 70;     // nominal can OD (mm)
clearance          = 0.75;   // radial slip between can and ring (mm)
ring_height        = 35;     // C-ring band height along can axis (mm)
wall               = 3;      // wall thickness, ring + cup (mm)
cup_depth          = 5;      // drip-cup depth below ring (mm)
cup_floor          = 2;      // drip-cup floor thickness (mm)
front_opening_deg  = 120;    // C-ring open-front arc angle (deg)

// Multiconnect slot backer
slot_count         = 2;      // number of vertical slots side-by-side
slot_spacing_mm    = 25;     // Multiconnect pitch (25mm standard)
backer_height      = 75;     // backer Z extent; longer = more dimple engagements
backer_thickness   = 6.5;    // library default; accommodates slot depth (~4.15mm)

// === Derived ===
ring_id    = can_diameter + 2 * clearance;      // 71.5
ring_od    = ring_id + 2 * wall;                // 77.5
backer_w   = slot_count * slot_spacing_mm;      // 50 at default

// === Layout ===
// X — horizontal across backer
// Y — depth. multiconnectGenerator produces a cuboid centered at origin
//     with slot openings on its -Y face (BOSL2 FRONT). That face slides
//     onto the Multiboard wall, so the accessory (cradle) extends into
//     +Y (away from the wall).
// Z — vertical; can axis parallel to Z.
// Origin at backer geometric center.

ring_cy    = backer_thickness / 2 + ring_od / 2;  // ring center in +Y
cup_z0     = -backer_height / 2;                  // cup floor at bottom of backer
ring_z0    = cup_z0 + cup_depth;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z).
// X: max(backer_w=50, ring_od=77.5) = 77.5
// Y: backer_thickness(6.5) + ring_od(77.5) = 84
// Z: max(backer_height=75, cup_depth+ring_height=40) = 75
PRINT_ANCHOR_BBOX = [77.5, 84, 75];

// === Geometry ===

module multiconnect_backer() {
    multiconnectGenerator(
        width = backer_w,
        height = backer_height,
        multiconnectPartType = "Backer",
        distanceBetweenSlots = slot_spacing_mm,
        slotOrientation = "Vertical"
    );
}

module cradle() {
    opening_half = front_opening_deg / 2;
    difference() {
        union() {
            translate([0, ring_cy, ring_z0])
                cylinder(h = ring_height, d = ring_od);
            translate([0, ring_cy, cup_z0])
                cylinder(h = cup_depth, d = ring_od);
        }
        translate([0, ring_cy, ring_z0 - 0.1])
            cylinder(h = ring_height + 0.2, d = ring_id);
        translate([0, ring_cy, cup_z0 + cup_floor])
            cylinder(h = cup_depth - cup_floor + 0.1, d = ring_id);
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

// Sibling expressions at root: multiconnectGenerator uses BOSL2 diff()
// tags internally and breaks when nested inside an outer union().
multiconnect_backer();
cradle();
