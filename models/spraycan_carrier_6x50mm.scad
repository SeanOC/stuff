// Parametric 2x3 spray-can tote carrier. Six open-front C-ring cradles
// (same geometry family as the 70mm preset of cylindrical_holder_slot.scad,
// minus the Multiboard backer) sit on a drainage base plate, with a
// semicircular-arched handle spanning the long axis for standalone carry.
//
// Print orientation: base down, handle up. Defaults keep every overhang
// <=45deg: the handle arch is a semicircle of radius = post_outer_x, so
// max overhang is 45deg at each post-top junction and smoothly climbs to
// a horizontal tangent at the apex (printable as a gradual dome).
//
// Wet-safe: the base drops water through four radial slots under each
// cradle (selectable between 'slots', 'holes', or 'open' via
// base_drain_pattern), and each C-ring has horizontal drain holes bored
// through the wall at the bottom of the ring on the solid back arc so
// water can't sit between can and cradle.
//
// Kid-safe: base corners and handle posts are filleted (BOSL2 cuboid
// rounding), cradle top rims get an outer chamfer plus an inner lead-in,
// and the handle arch's X-Z corners are rounded by construction (annular
// half-disc). Remaining Y-faces of the arch are the only sharp edges --
// cheap to break with sandpaper.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Can + cell -----
can_diameter      = 50;    // @param number min=20 max=120 step=0.5 label="Can diameter (mm)"
clearance         = 0.75;  // @param number min=0 max=2 step=0.05 label="Slip clearance (mm)"
ring_height       = 35;    // @param number min=10 max=120 step=1 label="Cradle ring height (mm)"
wall              = 3;     // @param number min=1.5 max=8 step=0.5 label="Wall thickness (mm)"
rows              = 2;     // @param integer min=1 max=6 label="Rows"
cols              = 3;     // @param integer min=1 max=6 label="Columns"
cell_spacing      = 60;    // @param number min=40 max=120 step=1 label="Cell center-to-center (mm)"
front_opening_deg = 100;   // @param number min=0 max=200 step=5 label="Cradle front opening arc (deg)"

// ----- Base + drainage -----
base_thickness     = 3;        // @param number min=1.5 max=8 step=0.5 label="Base thickness (mm)"
base_margin        = 18;       // @param number min=6 max=40 step=0.5 label="Base margin beyond rings (mm)"
base_drain_pattern = "slots";  // @param enum choices=slots|holes|open label="Base drain pattern"
drain_hole_d       = 5;        // @param number min=2 max=15 step=0.5 label="Drain hole diameter (mm)"
drain_hole_count   = 3;        // @param integer min=0 max=8 label="Cradle drain holes per cell"

// ----- Handle -----
handle_height    = 125;  // @param number min=50 max=250 step=1 label="Handle apex height above base (mm)"
handle_post_w    = 14;   // @param number min=6 max=30 step=0.5 label="Handle post width X (mm)"
handle_thickness = 20;   // @param number min=8 max=40 step=0.5 label="Handle thickness Y (mm)"

// ----- Edge treatment -----
fillet_r  = 2;   // @param number min=0 max=5 step=0.25 label="Fillet radius (mm)"
chamfer_r = 1;   // @param number min=0 max=3 step=0.25 label="Chamfer radius (mm)"

// === Derived ===

ring_id = can_diameter + 2 * clearance;
ring_od = ring_id + 2 * wall;

function cell_x(c) = (c - (cols - 1) / 2) * cell_spacing;
function cell_y(r) = (r - (rows - 1) / 2) * cell_spacing;

base_w = cell_spacing * (cols - 1) + ring_od + 2 * base_margin;
base_d = cell_spacing * (rows - 1) + ring_od + 2 * base_margin;

// Handle posts sit in the X-margin region, centered in Y. Pulled inward
// from the base edge by fillet_r + 2mm so the post wall doesn't crowd
// the rounded base corner.
post_center_x = base_w / 2 - handle_post_w / 2 - fillet_r - 2;
post_outer_x  = post_center_x + handle_post_w / 2;
post_inner_x  = post_center_x - handle_post_w / 2;

// Semicircular arch: radius = post_outer_x, tangent-vertical at the post
// tops (45deg overhang there), climbing to a horizontal apex at z =
// handle_height. arch_z_start is where the post tops join the arch.
arch_z_start = handle_height - post_outer_x;

// PRINT_ANCHOR_BBOX at defaults (rows=2 cols=3, cell_spacing=60,
// base_margin=18, can_diameter=50, clearance=0.75, wall=3):
//   X: base_w = 60*2 + (50 + 1.5 + 6) + 2*18 = 120 + 57.5 + 36 = 213.5
//   Y: max(base_d, handle_thickness) = max(60 + 57.5 + 36, 20) = 153.5
//   Z: base_thickness + handle_height = 3 + 125 = 128
PRINT_ANCHOR_BBOX = [213.5, 153.5, 128];

// ================= Base plate =================

module base_plate() {
    difference() {
        translate([0, 0, base_thickness / 2])
            cuboid([base_w, base_d, base_thickness],
                   rounding = fillet_r,
                   edges = "Z");
        base_drains();
    }
}

module base_drains() {
    for (c = [0:cols - 1], r = [0:rows - 1])
        translate([cell_x(c), cell_y(r), 0])
            if      (base_drain_pattern == "open")  base_drain_open();
            else if (base_drain_pattern == "holes") base_drain_holes();
            else                                    base_drain_slots();
}

module base_drain_open() {
    // Large single bore under each can: maximum flow, minimum support
    // footprint on the base. Keep a 4mm lip around the ring ID so the
    // cradle's bottom edge has something to sit on.
    translate([0, 0, -0.1])
        cylinder(h = base_thickness + 0.2, d = max(ring_id - 8, 5));
}

module base_drain_holes() {
    // Ring of six drain holes + one central hole (flat-top printable).
    translate([0, 0, -0.1])
        cylinder(h = base_thickness + 0.2, d = drain_hole_d);
    n = 6;
    r_ring = (ring_id - drain_hole_d * 1.5) / 2;
    for (a = [0:360 / n:359])
        translate([r_ring * cos(a), r_ring * sin(a), -0.1])
            cylinder(h = base_thickness + 0.2, d = drain_hole_d);
}

module base_drain_slots() {
    // Four rounded radial slots. Slots (not rectangles) per the kid-safe
    // spec. Slot ends are round so water beads don't stick in a corner.
    n = 4;
    slot_len = max(ring_id / 2 - 8, 5);
    slot_w   = drain_hole_d;
    for (a = [0:360 / n:359])
        rotate([0, 0, a + 45])
            hull() {
                translate([4, 0, -0.1])
                    cylinder(h = base_thickness + 0.2, d = slot_w);
                translate([4 + slot_len, 0, -0.1])
                    cylinder(h = base_thickness + 0.2, d = slot_w);
            }
}

// ================= Cradles =================

module cradle_ring() {
    // Open-front C-ring + top-rim chamfer + inner lead-in. Opens +Y by
    // default; the grid rotates back-row cradles 180deg so openings face
    // away from grid center.
    opening_half = front_opening_deg / 2;
    difference() {
        cyl(h = ring_height, d = ring_od,
            chamfer2 = chamfer_r, anchor = BOTTOM);
        translate([0, 0, -0.1])
            cylinder(h = ring_height + 0.2, d = ring_id);
        translate([0, 0, ring_height - chamfer_r])
            cylinder(h = chamfer_r + 0.01,
                     d1 = ring_id, d2 = ring_id + 2 * chamfer_r);
        if (front_opening_deg > 0)
            translate([0, 0, -0.1])
                linear_extrude(height = ring_height + 0.2)
                    polygon(concat(
                        [[0, 0]],
                        [for (a = [90 - opening_half:2:90 + opening_half])
                            [(ring_od + 10) * cos(a), (ring_od + 10) * sin(a)]]
                    ));
        if (drain_hole_count > 0) {
            // Drain holes through the wall at the bottom of the C-ring,
            // distributed along the solid back arc only (40deg guard
            // band on each side of the front opening). Radius-through
            // cylinder drilled inside-out so it always cuts the wall.
            span = max(360 - front_opening_deg - 80, 40);
            for (i = [0:drain_hole_count - 1]) {
                a = 270 + span * ((i + 0.5) / drain_hole_count - 0.5);
                rotate([0, 0, a])
                    translate([0, 0, drain_hole_d * 0.9])
                        rotate([0, 90, 0])
                            cylinder(h = ring_od / 2 + 1, d = drain_hole_d);
            }
        }
    }
}

module cradles() {
    for (c = [0:cols - 1], r = [0:rows - 1])
        translate([cell_x(c), cell_y(r), base_thickness])
            rotate([0, 0, (rows > 1 && r < (rows - 1) / 2) ? 180 : 0])
                cradle_ring();
}

// ================= Handle =================

module handle() {
    translate([0, 0, base_thickness]) {
        // Two posts, one at each short end of the base, centered in Y.
        for (sx = [-1, 1])
            translate([sx * post_center_x, 0, arch_z_start / 2])
                cuboid([handle_post_w, handle_thickness, arch_z_start],
                       rounding = fillet_r,
                       edges = "Z");
        // Semicircular annular arch. Outer radius = post_outer_x (touches
        // post outer face); inner radius = post_inner_x (touches post
        // inner face). Extruded along Y by handle_thickness.
        translate([0, 0, arch_z_start])
            rotate([90, 0, 0])
                linear_extrude(height = handle_thickness, center = true, convexity = 4)
                    handle_arch_2d();
    }
}

module handle_arch_2d() {
    difference() {
        // Upper half-disc at radius = post_outer_x
        intersection() {
            circle(r = post_outer_x);
            translate([0, post_outer_x])
                square([4 * post_outer_x, 2 * post_outer_x], center = true);
        }
        // Subtract inner half-disc at radius = post_inner_x
        intersection() {
            circle(r = post_inner_x);
            translate([0, post_outer_x])
                square([4 * post_outer_x, 2 * post_outer_x], center = true);
        }
    }
}

// ================= Assembly =================

base_plate();
cradles();
handle();
