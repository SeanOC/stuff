// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Parametric 2x3 spray-can tote carrier. Six open-front C-ring cradles
// (same geometry family as the 70mm preset of cylindrical_holder_slot.scad,
// minus the Multiboard backer) sit on a drainage base plate, with a
// semicircular-arched handle spanning the long axis for standalone carry.
//
// Handle clearance (st-8ac fix): cell_spacing_x and cell_spacing_y are
// split so the two rows sit far enough apart in Y that the handle's
// thickness (y=+-handle_thickness/2) fits in the gap between the rows
// without ever passing over a can. The handle apex also sits above
// can_height + a grip-clearance band so a full-height can seats fully
// and the carrier can be lifted with cans in place.
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
// Kid-safe: base has rounded top-rim + vertical corners (bottom rim
// stays sharp so it prints flush against the build plate — st-so7),
// handle posts are filleted (BOSL2 cuboid rounding), cradle top rims
// get an outer chamfer plus an inner lead-in, and the handle arch's
// X-Z corners are rounded by construction (annular half-disc). The
// arch's Y-face edges carry the same fillet_r via rotate_extrude of
// a filleted rectangle profile (st-djm, restoring the st-hnd intent
// with manifold-safe geometry that passes the st-cjn watertight
// invariant). Result: the post→arch junction is visually continuous.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Can + cell -----
can_diameter      = 50;    // @param number min=20 max=120 step=0.5 unit=mm group=cans short=d label="Can diameter"
can_height        = 195;   // @param number min=80 max=300 step=1 unit=mm group=cans short=ch label="Target can height"
clearance         = 0.75;  // @param number min=0 max=2 step=0.05 unit=mm group=cans short=c label="Slip clearance"
ring_height       = 35;    // @param number min=10 max=120 step=1 unit=mm group=geometry short=rh label="Cradle ring height"
wall              = 3;     // @param number min=1.5 max=8 step=0.5 unit=mm group=geometry short=w label="Wall thickness"
rows              = 2;     // @param integer min=1 max=6 group=geometry short=r label="Rows"
cols              = 3;     // @param integer min=1 max=6 group=geometry short=co label="Columns"
cell_spacing_x    = 60;    // @param number min=40 max=120 step=1 unit=mm group=geometry short=sx label="Cell X spacing — along handle"
cell_spacing_y    = 90;    // @param number min=40 max=140 step=1 unit=mm group=geometry short=sy label="Cell Y spacing — across handle"
front_opening_deg = 100;   // @param number min=0 max=200 step=5 unit=deg group=geometry short=fo label="Cradle front opening arc"

// ----- Base + drainage -----
// base_margin is split per-axis (st-3ta). X (handle side) must leave room
// for the handle posts — reducing below ~10mm detaches the posts from a
// valid seat, the existing geometry failure mode. Y (other side) has no
// structural role once the rings are fully under the plate, so its floor
// can drop much lower; 5mm leaves just the corner fillet + a narrow rim.
base_thickness          = 3;        // @param number min=1.5 max=8 step=0.5 unit=mm group=geometry short=bt label="Base thickness"
base_margin_handle_side = 18;       // @param number min=6 max=40 step=0.5 unit=mm group=geometry short=mx label="Base margin — handle side (X)"
base_margin_other_side  = 5;        // @param number min=1 max=40 step=0.5 unit=mm group=geometry short=my label="Base margin — other side (Y)"
base_drain_pattern      = "slots";  // @param enum choices=slots|holes|open group=geometry short=bd label="Base drain pattern"
drain_hole_d            = 5;        // @param number min=2 max=15 step=0.5 unit=mm group=geometry short=dh label="Drain hole diameter"
drain_hole_count        = 3;        // @param integer min=0 max=8 group=geometry short=dn label="Cradle drain holes per cell"

// ----- Handle -----
// handle_height default = can_height + 55mm so fingers clear the tallest
// can top comfortably when lifting. Lower values still print, but the
// arch will intrude into the can's vertical envelope.
handle_height    = 250;  // @param number min=50 max=400 step=1 unit=mm group=handle short=hh label="Handle apex height above base"
handle_post_w    = 14;   // @param number min=6 max=30 step=0.5 unit=mm group=handle short=hw label="Handle post width X"
handle_thickness = 20;   // @param number min=8 max=40 step=0.5 unit=mm group=handle short=ht label="Handle thickness Y"

// ----- Edge treatment -----
fillet_r  = 2;   // @param number min=0 max=5 step=0.25 unit=mm group=handle short=fr label="Fillet radius (posts + arch Y-faces)"
chamfer_r = 1;   // @param number min=0 max=3 step=0.25 unit=mm group=handle short=cr label="Chamfer radius"

// @preset id="stock" label="Stock 2×3 / 50mm" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=18 base_margin_other_side=5 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_post_w=14 handle_thickness=20 fillet_r=2 chamfer_r=1

// === Derived ===

ring_id = can_diameter + 2 * clearance;
ring_od = ring_id + 2 * wall;

function cell_x(c) = (c - (cols - 1) / 2) * cell_spacing_x;
function cell_y(r) = (r - (rows - 1) / 2) * cell_spacing_y;

base_w = cell_spacing_x * (cols - 1) + ring_od + 2 * base_margin_handle_side;
base_d = cell_spacing_y * (rows - 1) + ring_od + 2 * base_margin_other_side;

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

// PRINT_ANCHOR_BBOX at defaults (rows=2 cols=3, cell_spacing_x=60,
// cell_spacing_y=90, base_margin_handle_side=18, base_margin_other_side=5,
// can_diameter=50, clearance=0.75, wall=3, handle_height=250):
//   X: base_w = 60*2 + (50 + 1.5 + 6) + 2*18 = 120 + 57.5 + 36 = 213.5
//   Y: max(base_d, handle_thickness) = max(90 + 57.5 + 10, 20) = 157.5
//   Z: base_thickness + handle_height = 3 + 250 = 253
// Y footprint dropped 26mm vs the pre-st-3ta single base_margin=18 default
// (was 183.5mm) — the Y margin had no structural role and the cleaner
// rectangle saves roughly 14% of base-plate plastic.
PRINT_ANCHOR_BBOX = [213.5, 157.5, 253];

// ================= Base plate =================

module base_plate() {
    difference() {
        translate([0, 0, base_thickness / 2])
            // Round the 4 top-rim edges + 4 vertical corners; leave the
            // 4 bottom-rim edges sharp so the plate sits flush against
            // the build plate (a fillet there would pull the print off
            // the bed and introduce an unneeded overhang). st-so7.
            cuboid([base_w, base_d, base_thickness],
                   rounding = fillet_r,
                   edges    = "ALL",
                   except   = BOTTOM);
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
    // Posts span z=0 (baseplate bottom) through arch_z_start+1, so they
    // overlap the base fully and interpenetrate the arch by 1mm. Without
    // this overlap, post-base and post-arch join at zero-thickness planes,
    // which preview renderers (e.g. WASM OpenSCAD F5) display as floating
    // disconnected bodies (st-v7k).
    post_h = base_thickness + arch_z_start + 1;
    for (sx = [-1, 1])
        translate([sx * post_center_x, 0, post_h / 2])
            cuboid([handle_post_w, handle_thickness, post_h],
                   rounding = fillet_r,
                   edges = "Z");
    // Semicircular arch swept around the Z axis by rotate_extrude
    // (st-djm). The profile is a filleted rectangle handle_post_w
    // (radial) × handle_thickness (along the sweep-axis direction),
    // with rounding = fillet_r on all four corners. After sweeping 180°
    // and rotating [90, 0, 0] into the XZ plane, those four corners
    // become the arch's Y-face edges — the radius matches the post's
    // Z-edge fillet, so the post→arch junction is continuous.
    //
    // rotate_extrude closes the swept volume into a manifold solid by
    // construction — unlike path_sweep which needs explicit endpoint
    // caps (the st-hnd approach that broke watertight and was reverted
    // by st-so7). The endpoints at θ=0° / θ=180° are the natural start
    // and end of the extrusion; they sit flush on the posts with the
    // same 1mm interpenetration the posts use with the baseplate.
    arch_r_mid = (post_outer_x + post_inner_x) / 2;
    translate([0, 0, base_thickness + arch_z_start])
        rotate([90, 0, 0])
            rotate_extrude(angle = 180, convexity = 4)
                translate([arch_r_mid, 0])
                    rect([handle_post_w, handle_thickness],
                         rounding = fillet_r, anchor = CENTER);
}

// ================= Assembly =================

base_plate();
cradles();
handle();
