// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Parametric 2x3 spray-can tote carrier. Six open-front C-ring cradles
// (same geometry family as the 70mm preset of cylindrical_holder_slot.scad,
// minus the Multiboard backer) sit on a drainage base plate, with an
// arched handle spanning the long axis for standalone carry.
//
// === Load-bearing invariants (don't regress) ===
//
//   - `cell_spacing_y = 90` (st-8ac). The two rows must sit 90 mm
//     apart in Y so the handle thickness (±handle_thickness/2 at Y=0)
//     fits in the can-free corridor between them. At defaults the
//     can rims reach Y = ±20 from each row centre; the Y=0 corridor
//     is 50 mm wide (±25) — plenty for a 20 mm-thick handle. Reducing
//     cell_spacing_y below 90 would re-introduce the st-8ac can-over-
//     handle collision.
//   - **Handle posts live at Y=0.** Any other Y places a post over a
//     can. Don't move them.
//
// Handle clearance (st-8ac context): the cell spacings enable the
// handle to pass through the middle of the array without ever sitting
// over a can. The handle apex also sits above can_height + a grip-
// clearance band so a full-height can seats fully and the carrier
// can be lifted with cans in place.
//
// Arch styles (`arch_style` param):
//   - "squared" (st-kyz, default) — toolbox handle: two vertical
//     cylindrical posts plus a horizontal cylindrical crossbar
//     bridging their tops. Each post-to-crossbar inside corner is a
//     true tangent-arc blend (st-y1q): a quarter-torus of tube
//     radius `handle_post_d/2` swept on a radius of `corner_sweep_r`
//     (default 12 mm), tangent-vertical at the post end and tangent-
//     horizontal at the crossbar end. The blend replaces the v-prior
//     hull-of-two-disks corner, which read as a chamfer rather than
//     a sweep. Posts shorten and the crossbar shortens to make room
//     for the swept blend; both junctions overlap the torus by 1 mm
//     to dodge the zero-thickness coincident-face issue from st-v7k.
//     Crossbar bridge = 2·(post_center_x − corner_sweep_r)
//     (~56 mm at defaults) — comfortably bridgeable without supports.
//     Legacy `corner_fillet` is a no-op for the squared style; kept
//     in the param list only for backward compat with old presets.
//   - "ogive" (st-qt4) — two circular arcs meeting at a point above
//     the centerline. Each arc's center sits on the opposite side of
//     the arch at X = ±k·post_outer_x with radius (k+1)·post_outer_x
//     (so each arc passes through the opposite post top AND through
//     the apex). `arch_point_offset` is k; 1.4 is the default
//     pointed-but-not-extreme setting.
//   - "semicircular" — the v-prior shape (rotate_extrude of a filleted
//     rectangle, landed in st-djm b855a35). Kept as a legacy choice.
//     Its apex is a long horizontal bridge, known-problematic for
//     some slicers.
//
// Compact footprint (st-kyz): posts were pulled inward from the base
// edges (new default `post_center_x = 40`, was derived from
// `base_w/2 - ...` ≈ 94 mm) and the base margins zeroed (was 18 mm
// handle-side + 5 mm other-side). Baseplate now hugs the ring array
// with no slack; the handle posts live in the Y=0 corridor between
// the inner edges of the middle-column rings (see invariant above).
//
// Handle post-to-base reinforcement (st-qt4): the posts used to be a
// bare 14×20 mm cuboid meeting the baseplate at a sharp corner, which
// took the arch's bending moment at its most stress-concentrated spot.
// Two additions soften that joint:
//   - **Gussets** (`post_base_gussets`, on by default): small triangular
//     fillet prisms on the +X and -X faces of each post, with legs
//     along the baseplate (X) and up the post (Z). The outer gusset's
//     reach in X is clamped to available baseplate room so it can't
//     cantilever over the edge.
//   - **Bottom flare** (`post_flare`, on by default): over the lowest
//     `flare_height` of each post, the cross-section tapers linearly
//     from (handle_post_w + 2·flare_width) × (handle_thickness +
//     2·flare_width) at z=0 down to the unflared post size at
//     z=flare_height. Adds section modulus right at the joint without
//     altering the grip above.
//
// Print orientation: base down, handle up. The ogive arch is self-
// supporting everywhere (each arc's tangent tips past the bridge-free
// slope well before it reaches the apex). For `arch_style="semicircular"`
// the apex is a horizontal bridge and a slicer bridging pass is needed
// — this is what the user's first-print caught.
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
// X-Z corners are rounded by construction. The semicircular variant
// carries fillet_r on its Y-face edges (rotate_extrude of a filleted
// rectangle profile — st-djm). The ogive variant has sharp Y-face
// edges by default; the post→arch junction is continuous via the
// post's matching fillet_r + shared handle_post_w footprint.

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
handle_post_d    = 14;   // @param number min=12 max=30 step=0.5 unit=mm group=handle label="Squared-cylindrical post / crossbar diameter"
handle_post_w    = 14;   // @param number min=6 max=30 step=0.5 unit=mm group=handle label="Legacy (ogive/semicircular) post width X"
handle_thickness = 20;   // @param number min=8 max=40 step=0.5 unit=mm group=handle label="Legacy (ogive/semicircular) post thickness Y"
// Post X position. Must stay within the Y=0 can-free corridor (keeps
// posts clear of cans at Y=±cell_spacing_y/2) and clear of the middle
// column ring at X=0. At defaults (post at X=±40, inner post edge at
// ±33) that leaves ~5 mm gap to the middle ring (ring_od/2 ≈ 28.75).
post_center_x    = 40;   // @param number min=40 max=120 step=0.5 unit=mm group=handle label="Handle post X centre"

// ----- Arch style (st-qt4) -----
// `squared` = toolbox-style posts + crossbar (new default, st-kyz);
// `ogive` = pointed arch, self-supporting; `semicircular` = the v-prior
// half-donut arch (legacy; apex bridges horizontally).
arch_style        = "squared"; // @param enum choices=squared|ogive|semicircular group=handle label="Arch style"
arch_point_offset = 1.4;       // @param number min=1.1 max=2.5 step=0.05 group=handle label="Ogive point offset (k-factor)"
corner_sweep_r    = 12;        // @param number min=0 max=25 step=0.5 unit=mm group=handle label="Squared-handle corner sweep radius (st-y1q)"
corner_fillet     = 4;         // @param number min=0 max=10 step=0.25 unit=mm group=handle label="Legacy squared-handle corner fillet (no-op since st-y1q)"

// ----- Post-base reinforcement (st-4ac, refined st-y1q) -----
// Concave quarter-ellipse flare at the bottom of each squared-style
// post, replacing the v-prior linear cone. The flare profile is a
// 2D arc swept around the post axis via `rotate_extrude`; the arc
// is tangent-horizontal where it meets the baseplate (so the
// transition is a smooth fillet rather than a chamfer) and tangent-
// vertical where it meets the post wall (so the post→flare
// transition is also smooth). Semi-axes: flare_width radial,
// flare_height vertical. Legacy ogive/semicircular arch styles keep
// the prismoid linear-taper flare on their rectangular posts —
// their 2D-extrude arch maths assume rectangular post cross-
// sections, so the cylindrical-flare path doesn't apply there.
post_flare   = true;  // @param boolean group=handle label="Post bottom flare"
flare_height = 12;    // @param number min=0 max=25 step=0.5 unit=mm group=handle label="Flare height (Z)"
flare_width  = 5;     // @param number min=0 max=10 step=0.25 unit=mm group=handle label="Flare widening (radial, each side)"

// ----- Edge treatment -----
fillet_r  = 2;   // @param number min=0 max=5 step=0.25 unit=mm group=handle label="Fillet radius (posts + arch Y-faces)"
chamfer_r = 1;   // @param number min=0 max=3 step=0.25 unit=mm group=handle label="Chamfer radius"

// @preset id="stock" label="Stock 2×3 / 50mm (cylindrical, compact)" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=0 base_margin_other_side=0 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_post_d=14 handle_post_w=14 handle_thickness=20 post_center_x=40 arch_style="squared" arch_point_offset=1.4 corner_sweep_r=12 corner_fillet=8 post_flare=true flare_height=12 flare_width=5 fillet_r=2 chamfer_r=1
// @preset id="legacy-ogive" label="Legacy ogive (st-qt4)" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=18 base_margin_other_side=5 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_post_d=14 handle_post_w=14 handle_thickness=20 post_center_x=94 arch_style="ogive" arch_point_offset=1.4 corner_fillet=4 post_flare=true flare_height=12 flare_width=5 fillet_r=2 chamfer_r=1
// @preset id="legacy-semicircular" label="Legacy semicircular (v-prior)" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=18 base_margin_other_side=5 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_post_d=14 handle_post_w=14 handle_thickness=20 post_center_x=94 arch_style="semicircular" arch_point_offset=1.4 corner_fillet=4 post_flare=false flare_height=12 flare_width=5 fillet_r=2 chamfer_r=1

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

// Handle-post X span. `post_center_x` is now a user-tunable @param
// (st-kyz). Posts live at Y=0 on the handle-axis corridor; see the
// load-bearing invariants in the header.
post_outer_x  = post_center_x + handle_post_w / 2;
post_inner_x  = post_center_x - handle_post_w / 2;

// Arch apex height above the post tops:
//   - squared: the cylindrical crossbar's diameter IS the apex rise
//     (handle_post_d).
//   - semicircular: radius = post_outer_x, apex rises by post_outer_x.
//   - ogive: two arcs with centers at (±k·post_outer_x, post_top) and
//     radius (k+1)·post_outer_x. The apex sits at X=0 at a height
//     post_outer_x · sqrt(2k+1) above the post tops.
arch_apex_rise =
    arch_style == "squared" ? handle_post_d
  : arch_style == "ogive"   ? post_outer_x * sqrt(2 * arch_point_offset + 1)
  :                           post_outer_x;  // semicircular

// handle_height = apex above baseplate top (unchanged). arch_z_start is
// the z of the post tops above the baseplate top. For the ogive default
// (k=1.4) arch_apex_rise ≈ 1.95 · post_outer_x, so the post height
// drops ~95 mm below the v-prior semicircle when keeping apex fixed —
// that's the price of an apex-matched pointed arch. If you need taller
// posts (e.g. to clear a can-plus-grip band), increase handle_height.
arch_z_start = handle_height - arch_apex_rise;

// PRINT_ANCHOR_BBOX at defaults (st-4ac). Base extent now includes
// fillet_r on each side so the rounded top edges don't clip the
// outer rings; with margin=0 that yields base 181.5 × 151.5 at
// defaults. Z still dominated by handle_height + base_thickness.
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

// Post top Z (above baseplate top); arch sits above this.
post_top_z = base_thickness + arch_z_start;
// Posts overlap the arch by 1mm at their top — see st-v7k. Posts span
// z=0 through post_top_z + post_arch_overlap.
post_arch_overlap = 1;
post_h = post_top_z + post_arch_overlap;

module handle() {
    if (arch_style == "squared") {
        _handle_squared_cyl();
    } else {
        // Legacy rectangular posts + ogive/semicircular arch.
        for (sx = [-1, 1]) _post_rect(sx);
        if (arch_style == "ogive") _arch_ogive();
        else                       _arch_semicircle();
    }
}

// --- Squared / toolbox cylindrical handle (st-4ac, refined st-y1q) ---
// Two vertical rods + one horizontal crossbar rod + concave quarter-
// ellipse flares at each post base + true tangent-arc quarter-torus
// blends at each post→crossbar inside corner. No gussets, no hull-
// of-disks chamfers — the flare and corner sweep carry the bending-
// moment reinforcement by themselves and read as continuous
// curvature in the viewer/STL.
//
// Geometry: post tops sit `corner_sweep_r` below the crossbar axis;
// crossbar endpoints sit `corner_sweep_r` inside the post X. The
// quarter-torus blend bridges the gap, tangent-vertical at the post
// (matching the post's wall direction) and tangent-horizontal at
// the crossbar (matching the crossbar's axis direction). Each post
// and each crossbar end overlaps the torus by 1 mm to dodge the
// zero-thickness coincident-face issue from st-v7k.
module _handle_squared_cyl() {
    post_r          = handle_post_d / 2;
    apex_z          = base_thickness + handle_height;   // top of crossbar
    crossbar_axis_z = apex_z - post_r;
    overlap         = 1;  // st-v7k: avoid zero-thickness coincident faces

    if (corner_sweep_r > 0) {
        // Posts shorten so their tops meet the start of the corner
        // sweep (with `overlap` of interpenetration). Crossbar
        // shortens so its endpoints meet the end of the corner
        // sweep (with `overlap` on each side).
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

// --- Legacy rectangular post (for ogive / semicircular styles) ---
// Same prismoid-flared post the v-prior design used. Kept for the
// non-squared arch styles which assume rectangular post cross-
// sections in their arch-silhouette math.
module _post_rect(sx) {
    cx = sx * post_center_x;
    if (post_flare && flare_height > 0 && flare_width > 0) {
        translate([cx, 0, 0])
            prismoid(
                size1 = [handle_post_w + 2 * flare_width,
                         handle_thickness + 2 * flare_width],
                size2 = [handle_post_w, handle_thickness],
                h     = flare_height,
                anchor = BOTTOM
            );
        straight_h = post_h - flare_height;
        translate([cx, 0, flare_height + straight_h / 2])
            cuboid([handle_post_w, handle_thickness, straight_h],
                   rounding = fillet_r,
                   edges = "Z");
    } else {
        translate([cx, 0, post_h / 2])
            cuboid([handle_post_w, handle_thickness, post_h],
                   rounding = fillet_r,
                   edges = "Z");
    }
}

// --- Semicircular arch (legacy; st-djm rotate_extrude) ---
// Kept as a choice under arch_style="semicircular" for reprints of the
// v-prior design. The profile is a filleted rectangle handle_post_w
// (radial) × handle_thickness (along the sweep-axis direction), with
// rounding = fillet_r on all four corners. After sweeping 180° and
// rotating [90, 0, 0] into the XZ plane, those four corners become the
// arch's Y-face edges — the radius matches the post's Z-edge fillet.
// rotate_extrude closes the swept volume into a manifold solid by
// construction. Endpoints at θ=0°/θ=180° sit flush on the posts with
// the same 1mm interpenetration the posts use with the baseplate.
module _arch_semicircle() {
    arch_r_mid = (post_outer_x + post_inner_x) / 2;
    translate([0, 0, post_top_z])
        rotate([90, 0, 0])
            rotate_extrude(angle = 180, convexity = 4)
                translate([arch_r_mid, 0])
                    rect([handle_post_w, handle_thickness],
                         rounding = fillet_r, anchor = CENTER);
}

// --- Ogive arch (st-qt4, new default) ---
// Two circular arcs meeting at a point directly above the centerline.
// 2D silhouette of the arch band (annular ogive) in OpenSCAD's XY plane
// — which maps to world's XZ after linear_extrude + rotate([90,0,0]).
// OpenSCAD-2D X = world X; OpenSCAD-2D Y = world Z (offset by post_top_z
// after the final translate).
//
// Construction: outer polygon (filled ogive of radius r_out) minus
// inner polygon (same construction with r_in = r_out - handle_post_w).
// Both polygons close at Y=0 via their implicit last→first edge, so the
// band at Y=0 covers only the post-top X strips [-post_outer_x, -
// post_inner_x] and [+post_inner_x, +post_outer_x] — flush with the
// posts beneath.
module _arch_ogive() {
    translate([0, 0, post_top_z])
        rotate([90, 0, 0])
            linear_extrude(height = handle_thickness, center = true)
                _arch_ogive_band_2d();
}

module _arch_ogive_band_2d() {
    difference() {
        _arch_ogive_filled_2d((arch_point_offset + 1) * post_outer_x);
        _arch_ogive_filled_2d((arch_point_offset + 1) * post_outer_x
                              - handle_post_w);
    }
}

// Filled ogive polygon of outer radius `r`, centered on X=0 with its
// flat bottom at Y=0. The two arcs share centers at (±k·post_outer_x,
// 0) and meet at (0, sqrt(r² − (k·post_outer_x)²)). Guarded against
// degenerate r ≤ k·post_outer_x (which would make the inner subtract
// vanish) — callers ensure r > k·post_outer_x.
module _arch_ogive_filled_2d(r) {
    k       = arch_point_offset;
    kR      = k * post_outer_x;
    footprint_half = r - kR;   // 2D X at Y=0 of the arc endpoints.
    y_apex  = sqrt(r * r - kR * kR);
    // Angle at the apex, measured CCW from +X from the right-arc
    // centre (-kR, 0). At this angle the right arc reaches (0, y_apex).
    apex_angle = atan2(y_apex, kR);
    n = 40;
    // Left arc: centre (+kR, 0), from angle 180° (→ (-footprint_half, 0))
    // sweeping CW to (180° - apex_angle) (→ apex).
    left_arc = [
        for (i = [0 : n])
            let(t = 180 - i * apex_angle / n)
                [kR + r * cos(t), r * sin(t)]
    ];
    // Right arc: centre (-kR, 0), from angle apex_angle (→ apex) sweeping
    // CW to 0° (→ (+footprint_half, 0)).
    right_arc = [
        for (i = [0 : n])
            let(t = apex_angle - i * apex_angle / n)
                [-kR + r * cos(t), r * sin(t)]
    ];
    // Polygon: (-footprint_half, 0) → apex → (+footprint_half, 0) →
    // implicit close along Y=0.
    polygon(concat(left_arc, right_arc));
}

// ================= Assembly =================

base_plate();
cradles();
handle();
