// Multiboard-mounted holder for 70mm spray can.
// Open-front C-ring cradle + drip cup + 3x3 Multiboard snap backer.
// First exercise of the /scad-new → /scad-render → /scad-export loop.

include <BOSL2/std.scad>
use <QuackWorks/Modules/snapConnector.scad>

$fn = 64;

// === User-tunable parameters ===
can_diameter       = 70;     // nominal can OD (mm)
clearance          = 0.75;   // radial slip between can and ring (mm)
ring_height        = 35;     // C-ring band height along can axis (mm)
wall               = 3;      // wall thickness, ring + cup (mm)
cup_depth          = 5;      // drip-cup depth below ring (mm)
backer_cells_x     = 3;      // Multiboard grid cells, X
backer_cells_y     = 3;      // Multiboard grid cells, Z (vertical on wall)
snap_type          = "Moderate WB";  // informational label; geometry uses
                                     // QuackWorks snapConnectBacker (default)
holding_tolerance  = 1.0;    // QuackWorks snap snugness (0.5..1.5)
grid_pitch         = 25;     // Multiboard grid pitch (mm)
front_opening_deg  = 120;    // C-ring open-front arc angle (deg)
backer_thickness   = 3;      // backer plate thickness (mm)
cup_floor          = 2;      // drip-cup floor thickness (mm)

// === Derived ===
ring_id    = can_diameter + 2 * clearance;    // 71.5
ring_od    = ring_id + 2 * wall;              // 77.5
backer_w   = backer_cells_x * grid_pitch;     // 75
backer_h   = backer_cells_y * grid_pitch;     // 75
snap_h     = 6.2;                             // snapConnectBacker height

// === Layout ===
// X — horizontal across backer (width)
// Y — depth; backer back at Y = -backer_thickness, front at Y = 0
//     snaps extend into -Y, cradle extends into +Y
// Z — vertical; can axis parallel to Z
// Origin at backer front-face center.

ring_cy    = ring_od / 2;                         // ring center in +Y
cup_z0     = -backer_h / 2;                        // cup floor = bottom of backer
ring_z0    = cup_z0 + cup_depth;
ring_z1    = ring_z0 + ring_height;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z).
// X: max(backer_w=75, ring_od=77.5) = 77.5
// Y: (backer_thickness=3 + snap_h=6.2) + (ring_cy=38.75 + ring_od/2=38.75) = 86.7
// Z: max(backer_h=75, cup_depth+ring_height=40) = 75
// Literal values required for scad-render anchor parser.
PRINT_ANCHOR_BBOX = [77.5, 86.7, 75];

// === Geometry ===

module multiboard_backer() {
    // Flat plate in XZ, Y-thickness backer_thickness (back at Y=-backer_thickness).
    translate([0, -backer_thickness / 2, 0])
        cube([backer_w, backer_thickness, backer_h], center=true);

    // Snap grid on the back face. Snaps extend into -Y.
    // snapConnectBacker natural orientation: height along +Z, base at Z=0 (anchor=BOT).
    // After rotate([90,0,0]): +Z -> -Y. Base placed at back face plane.
    for (ix = [0 : backer_cells_x - 1], iz = [0 : backer_cells_y - 1]) {
        x = (ix - (backer_cells_x - 1) / 2) * grid_pitch;
        z = (iz - (backer_cells_y - 1) / 2) * grid_pitch;
        translate([x, -backer_thickness, z])
            rotate([90, 0, 0])
                snapConnectBacker(
                    holdingTolerance = holding_tolerance,
                    anchor = BOT
                );
    }
}

module cradle() {
    // C-ring + drip cup in front of backer. Can axis parallel to +Z.
    opening_half = front_opening_deg / 2;
    difference() {
        union() {
            // Ring band
            translate([0, ring_cy, ring_z0])
                cylinder(h = ring_height, d = ring_od);
            // Drip cup (same OD, below ring)
            translate([0, ring_cy, cup_z0])
                cylinder(h = cup_depth, d = ring_od);
        }
        // Ring bore (full height)
        translate([0, ring_cy, ring_z0 - 0.1])
            cylinder(h = ring_height + 0.2, d = ring_id);
        // Cup well (floor thickness cup_floor at bottom)
        translate([0, ring_cy, cup_z0 + cup_floor])
            cylinder(h = cup_depth - cup_floor + 0.1, d = ring_id);
        // Open-front pie slice: remove wedge facing +Y through ring height only
        translate([0, ring_cy, ring_z0 - 0.1])
            linear_extrude(height = ring_height + 0.2)
                polygon(concat(
                    [[0, 0]],
                    [for (a = [90 - opening_half : 2 : 90 + opening_half])
                        [(ring_od + 10) * cos(a), (ring_od + 10) * sin(a)]]
                ));
    }
}

union() {
    multiboard_backer();
    cradle();
}
