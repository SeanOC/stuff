// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Parametric 2x3 spray-can tote carrier. Six open-front C-ring cradles
// (same geometry family as the 70mm preset of cylindrical_holder_slot.scad,
// minus the Multiboard backer) sit on a drainage base plate, with a
// squared/toolbox-style cylindrical handle spanning the long axis for
// standalone carry: two vertical cylindrical posts plus a horizontal
// cylindrical crossbar bridging their tops, with quarter-torus tangent-
// arc blends at the inside corners (st-y1q) and concave quarter-ellipse
// flares at each post base (st-y1q).
//
// === Load-bearing invariants (don't regress) ===
//
//   - `cell_spacing_y = 90` (st-8ac). The two rows must sit 90 mm
//     apart in Y so the handle posts (at Y=0) don't sit over a can.
//     At defaults the can rims reach Y = ±20 from each row centre;
//     the Y=0 corridor is 50 mm wide (±25). Reducing cell_spacing_y
//     below 90 would re-introduce the st-8ac can-over-handle
//     collision.
//   - **Handle posts live at Y=0.** Any other Y places a post over a
//     can. Don't move them.
//   - **Handle posts must clear the middle-column ring at X=0.** Each
//     post's inner X edge sits at handle_width/2 − handle_post_d/2;
//     the middle ring's outer edge sits at ring_od/2. Reducing
//     `handle_width` below ~72 mm at default ring/post sizes pulls
//     the posts into the middle ring. The @param min on
//     `handle_width` enforces the safe floor for the default
//     config; tweaking can_diameter/wall/handle_post_d may require
//     adjusting it.
//
// Handle clearance (st-8ac context): the cell spacings put the handle
// posts in the middle of the array without sitting over a can. The
// handle apex also sits above can_height + a grip-clearance band so
// a full-height can seats fully and the carrier can be lifted with
// cans in place.
//
// Compact footprint (st-kyz): posts pulled inward from the base
// edges (default `handle_width = 80` → post centres at X=±40, was
// derived from `base_w/2 − …` ≈ 94 mm) and the base margins zeroed.
// Baseplate hugs the ring array with no slack.
//
// Post-to-base reinforcement (st-4ac, refined st-y1q): a concave
// quarter-ellipse flare at each post's base, swept around the post
// axis via `rotate_extrude` of a 2D radial profile. Tangent-
// horizontal where the flare meets the baseplate (smooth fillet)
// and tangent-vertical where it meets the post wall. Semi-axes
// flare_width radial × flare_height vertical. Replaces the v-prior
// gussets-plus-linear-cone pair with a single axisymmetric organic
// blend.
//
// Post→crossbar inside corners (st-y1q): a quarter-torus tangent-arc
// blend at each junction, tube radius = handle_post_d/2, sweep
// radius = `corner_sweep_r`. Tangent-vertical at the post end,
// tangent-horizontal at the crossbar end. Posts shorten by
// corner_sweep_r so their tops meet the start of the sweep;
// crossbar shortens by corner_sweep_r on each end. 1 mm overlap on
// each junction (st-v7k) avoids zero-thickness coincident faces in
// preview.
//
// Print orientation: base down, handle up. The crossbar's apex is a
// short horizontal segment (~2·post_center_x − 2·corner_sweep_r =
// ~56 mm at defaults), comfortably bridgeable. The corner sweep is
// self-supporting at every angle (45° tangent at the post end,
// horizontal at the crossbar end, radius of curvature = post_r).
//
// Wet-safe: the base drops water through four radial slots under each
// cradle (selectable between 'slots', 'holes', or 'open' via
// base_drain_pattern), and each C-ring has horizontal drain holes bored
// through the wall at the bottom of the ring on the solid back arc so
// water can't sit between can and cradle.
//
// Kid-safe: base has rounded top-rim + vertical corners (bottom rim
// stays sharp so it prints flush against the build plate — st-so7),
// cradle top rims get an outer chamfer plus an inner lead-in, and
// the handle is all cylindrical surfaces and tangent blends — no
// sharp edges to break.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Can + cell -----
can_diameter      = 50;    // @param number min=20 max=120 step=0.5 unit=mm group=cans label="Can diameter"
can_height        = 195;   // @param number min=80 max=300 step=1 unit=mm group=cans label="Target can height"
clearance         = 0.75;  // @param number min=0 max=2 step=0.05 unit=mm group=cans label="Slip clearance"
ring_height       = 35;    // @param number min=10 max=120 step=1 unit=mm group=geometry label="Cradle ring height"
wall              = 3;     // @param number min=1.5 max=8 step=0.5 unit=mm group=geometry label="Wall thickness"
rows              = 2;     // @param integer min=1 max=6 group=geometry label="Rows"
cols              = 3;     // @param integer min=1 max=6 group=geometry label="Columns"
cell_spacing_x    = 60;    // @param number min=40 max=120 step=1 unit=mm group=geometry label="Cell X spacing — along handle"
cell_spacing_y    = 90;    // @param number min=40 max=140 step=1 unit=mm group=geometry label="Cell Y spacing — across handle"
front_opening_deg = 100;   // @param number min=0 max=200 step=5 unit=deg group=geometry label="Cradle front opening arc"

// ----- Base + drainage -----
// base_margin is split per-axis (st-3ta). X (handle side) must leave room
// for the handle posts — reducing below ~10mm detaches the posts from a
// valid seat, the existing geometry failure mode. Y (other side) has no
// structural role once the rings are fully under the plate, so its floor
// can drop much lower; 5mm leaves just the corner fillet + a narrow rim.
base_thickness          = 3;        // @param number min=1.5 max=8 step=0.5 unit=mm group=geometry label="Base thickness"
base_margin_handle_side = 0;        // @param number min=0 max=40 step=0.5 unit=mm group=geometry label="Base margin — handle side (X)"
base_margin_other_side  = 0;        // @param number min=0 max=40 step=0.5 unit=mm group=geometry label="Base margin — other side (Y)"
base_drain_pattern      = "slots";  // @param enum choices=slots|holes|open group=geometry label="Base drain pattern"
drain_hole_d            = 5;        // @param number min=2 max=15 step=0.5 unit=mm group=geometry label="Drain hole diameter"
drain_hole_count        = 3;        // @param integer min=0 max=8 group=geometry label="Cradle drain holes per cell"

// ----- Handle -----
// handle_height default = can_height + 55mm so fingers clear the tallest
// can top comfortably when lifting. Lower values still print, but the
// arch will intrude into the can's vertical envelope.
handle_height    = 250;  // @param number min=50 max=400 step=1 unit=mm group=handle label="Handle apex height above base"
// handle_width is the centre-to-centre span between the two posts in X
// (st-q1y). Default 80 mm matches the v-prior post_center_x=40. Floor
// of 72 mm keeps the post inner edges clear of the middle-column ring
// outer edge at default ring_od (≈57.5) and handle_post_d (14). See
// the load-bearing-invariants header.
handle_width     = 80;   // @param number min=72 max=180 step=1 unit=mm group=handle label="Handle width — post-centre to post-centre span (X)"
handle_post_d    = 14;   // @param number min=12 max=30 step=0.5 unit=mm group=handle label="Handle post / crossbar diameter"
corner_sweep_r   = 12;   // @param number min=0 max=25 step=0.5 unit=mm group=handle label="Squared-handle corner sweep radius (st-y1q)"

// ----- Post-base reinforcement (st-4ac, refined st-y1q) -----
// Concave quarter-ellipse flare at the bottom of each post, swept via
// `rotate_extrude` around the post axis. Tangent-horizontal at the
// baseplate, tangent-vertical at the post wall.
post_flare   = true;  // @param boolean group=handle label="Post bottom flare"
flare_height = 12;    // @param number min=0 max=25 step=0.5 unit=mm group=handle label="Flare height (Z)"
flare_width  = 5;     // @param number min=0 max=10 step=0.25 unit=mm group=handle label="Flare widening (radial, each side)"

// ----- Edge treatment -----
fillet_r  = 2;   // @param number min=0 max=5 step=0.25 unit=mm group=handle label="Base-plate top-rim fillet radius"
chamfer_r = 1;   // @param number min=0 max=3 step=0.25 unit=mm group=handle label="Cradle top-rim chamfer radius"

// @preset id="stock" label="Stock 2×3 / 50mm" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=0 base_margin_other_side=0 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_width=80 handle_post_d=14 corner_sweep_r=12 post_flare=true flare_height=12 flare_width=5 fillet_r=2 chamfer_r=1
// @preset id="wide-grip" label="Wide grip (handle_width=120)" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=0 base_margin_other_side=0 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_width=120 handle_post_d=14 corner_sweep_r=12 post_flare=true flare_height=12 flare_width=5 fillet_r=2 chamfer_r=1

// === Derived ===

ring_id = can_diameter + 2 * clearance;
ring_od = ring_id + 2 * wall;

function cell_x(c) = (c - (cols - 1) / 2) * cell_spacing_x;
function cell_y(r) = (r - (rows - 1) / 2) * cell_spacing_y;

// Base is sized so the TOP FACE is flush with the outermost ring
// ODs (st-4ac). The baseplate's top edges are rounded by `fillet_r`,
// which shrinks the top-face extent relative to base_w/base_d by
// that radius; without the compensation the rings poked over the
// top-face rim into the rounded-edge curve. So the baseplate total
// extent is ring_span + 2·fillet_r + 2·margin, leaving the top face
// at ring_span + 2·margin exactly.
_ring_span_x = cell_spacing_x * (cols - 1) + ring_od;
_ring_span_y = cell_spacing_y * (rows - 1) + ring_od;
base_w = _ring_span_x + 2 * (fillet_r + base_margin_handle_side);
base_d = _ring_span_y + 2 * (fillet_r + base_margin_other_side);

// Each post's X centre. Derived from `handle_width` (st-q1y) so the
// user's grip span is the discoverable parameter.
post_center_x = handle_width / 2;

// PRINT_ANCHOR_BBOX at defaults. Base extent includes fillet_r on
// each side so the rounded top edges don't clip the outer rings;
// with margin=0 that yields base 181.5 × 151.5 at defaults. Z is
// dominated by handle_height + base_thickness.
//   X = _ring_span_x + 2·fillet_r = 177.5 + 4 = 181.5
//   Y = _ring_span_y + 2·fillet_r = 147.5 + 4 = 151.5
//   Z = base_thickness + handle_height = 3 + 250 = 253
PRINT_ANCHOR_BBOX = [181.5, 151.5, 253];

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

// Squared / toolbox cylindrical handle. Two vertical posts + one
// horizontal crossbar + concave quarter-ellipse flares at each post
// base + true tangent-arc quarter-torus blends at each post→crossbar
// inside corner. Posts and crossbar share `handle_post_d`.
//
// Geometry: post tops sit `corner_sweep_r` below the crossbar axis;
// crossbar endpoints sit `corner_sweep_r` inside the post X. The
// quarter-torus blend bridges the gap, tangent-vertical at the post
// and tangent-horizontal at the crossbar. Each post and each crossbar
// end overlaps the torus by 1 mm to dodge the zero-thickness
// coincident-face issue from st-v7k.
module handle() {
    post_r          = handle_post_d / 2;
    apex_z          = base_thickness + handle_height;   // top of crossbar
    crossbar_axis_z = apex_z - post_r;
    overlap         = 1;  // st-v7k: avoid zero-thickness coincident faces

    if (corner_sweep_r > 0) {
        post_total_h    = crossbar_axis_z - corner_sweep_r + overlap;
        crossbar_half_x = post_center_x - corner_sweep_r + overlap;
        for (sx = [-1, 1]) {
            _post_cyl(sx, post_r, post_total_h);
            _handle_corner_sweep(sx, post_r, crossbar_axis_z);
        }
        _crossbar_cyl(post_r, crossbar_axis_z, crossbar_half_x);
    } else {
        // No corner sweep: post extends to crossbar axis, crossbar
        // extends past each post axis by post_r (legacy join).
        post_total_h    = crossbar_axis_z;
        crossbar_half_x = post_center_x + post_r;
        for (sx = [-1, 1])
            _post_cyl(sx, post_r, post_total_h);
        _crossbar_cyl(post_r, crossbar_axis_z, crossbar_half_x);
    }
}

// A single cylindrical post with optional concave quarter-ellipse
// flare at the base. Post + flare are a single rotate_extrude of a
// 2D radial profile so the flare→post transition is one manifold
// surface (no seam, no zero-thickness boolean junction). The flare
// arc is tangent-horizontal at z=0 (smooth fillet into the
// baseplate) and tangent-vertical at z=flare_height (smooth into
// the post wall).
module _post_cyl(sx, post_r, post_total_h) {
    translate([sx * post_center_x, 0, 0])
        rotate_extrude(convexity = 4)
            _post_profile_2d(post_r, post_total_h);
}

// Radial profile (X = radius, Y = z) for the post + base flare.
// Polygon walks: origin → flare bottom-outer corner → up the
// concave arc to flare top-inner corner → up the post wall to the
// top → back to the axis → close.
module _post_profile_2d(post_r, post_total_h) {
    if (post_flare && flare_height > 0 && flare_width > 0) {
        // Concave quarter-ellipse from (post_r+flare_width, 0)
        // [tangent-horizontal] sweeping to (post_r, flare_height)
        // [tangent-vertical]. Centre at (post_r+flare_width,
        // flare_height); semi-axes (flare_width, flare_height).
        n = 24;
        flare_arc = [
            for (i = [0 : n])
                let(t = i * 90 / n)
                    [post_r + flare_width - flare_width * sin(t),
                     flare_height - flare_height * cos(t)]
        ];
        polygon(concat(
            [[0, 0]],
            flare_arc,
            [[post_r, post_total_h], [0, post_total_h]]
        ));
    } else {
        polygon([[0, 0],
                 [post_r, 0],
                 [post_r, post_total_h],
                 [0, post_total_h]]);
    }
}

// Horizontal cylinder (crossbar) spanning between the two corner-
// sweep endpoints. Diameter matches the posts. `half_len` is the
// crossbar's half-length (centre to one endpoint) — the caller
// pre-computes it from post_center_x, corner_sweep_r, and the
// junction overlap so this module stays geometry-agnostic.
module _crossbar_cyl(post_r, crossbar_axis_z, half_len) {
    crossbar_len = 2 * half_len;
    translate([-half_len, 0, crossbar_axis_z])
        rotate([0, 90, 0])
            cylinder(h = crossbar_len, r = post_r);
}

// True tangent-arc inside-corner blend at a post→crossbar junction
// (st-y1q). Quarter-torus of tube radius `post_r`, swept on radius
// `corner_sweep_r` around an axis parallel to Y. Sweep centre sits
// at (sx·(post_center_x − corner_sweep_r), 0,
//     crossbar_axis_z − corner_sweep_r), so the tube traces from
// (sx·post_center_x, 0, crossbar_axis_z − corner_sweep_r) [tangent-
// vertical, joining the post] to (sx·(post_center_x −
// corner_sweep_r), 0, crossbar_axis_z) [tangent-horizontal, joining
// the crossbar]. scale([sx,1,1]) mirrors the right-side construction
// for the left side.
//
// rotate_extrude sweeps around the Z axis by default; rotate([90,
// 0, 0]) tilts the sweep axis from Z to −Y, which puts the swept
// arc into the X-Z plane (where the post and crossbar already
// live).
module _handle_corner_sweep(sx, post_r, crossbar_axis_z) {
    if (corner_sweep_r > 0)
        scale([sx, 1, 1])
            translate([post_center_x - corner_sweep_r, 0,
                       crossbar_axis_z - corner_sweep_r])
                rotate([90, 0, 0])
                    rotate_extrude(angle = 90, convexity = 4)
                        translate([corner_sweep_r, 0])
                            circle(r = post_r);
}

// ================= Assembly =================

base_plate();
cradles();
handle();
