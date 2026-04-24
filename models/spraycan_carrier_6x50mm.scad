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
//     posts plus a horizontal crossbar (cross-section
//     `handle_post_w × handle_thickness`) bridging their tops, with
//     `corner_fillet` rounding at the crossbar corners. Crossbar
//     bridge = 2·post_center_x (~80 mm at defaults) — comfortably
//     bridgeable without supports for typical slicer settings.
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
handle_post_w    = 14;   // @param number min=6 max=30 step=0.5 unit=mm group=handle label="Handle post width X"
handle_thickness = 20;   // @param number min=8 max=40 step=0.5 unit=mm group=handle label="Handle thickness Y"
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
corner_fillet     = 4;         // @param number min=0 max=10 step=0.25 unit=mm group=handle label="Squared-handle crossbar corner fillet"

// ----- Post-to-base reinforcement (st-qt4) -----
post_base_gussets = true;  // @param boolean group=handle label="Post-base gussets (±X faces)"
gusset_base_len   = 10;    // @param number min=0 max=25 step=0.5 unit=mm group=handle label="Gusset base length (X)"
gusset_height     = 12;    // @param number min=0 max=30 step=0.5 unit=mm group=handle label="Gusset height (Z)"
gusset_thickness  = 3;     // @param number min=1 max=8  step=0.5 unit=mm group=handle label="Gusset thickness (Y)"
post_flare        = true;  // @param boolean group=handle label="Post bottom flare"
flare_height      = 10;    // @param number min=0 max=25 step=0.5 unit=mm group=handle label="Flare height (Z)"
flare_width       = 4;     // @param number min=0 max=10 step=0.25 unit=mm group=handle label="Flare widening (each side)"

// ----- Edge treatment -----
fillet_r  = 2;   // @param number min=0 max=5 step=0.25 unit=mm group=handle label="Fillet radius (posts + arch Y-faces)"
chamfer_r = 1;   // @param number min=0 max=3 step=0.25 unit=mm group=handle label="Chamfer radius"

// @preset id="stock" label="Stock 2×3 / 50mm (squared, compact)" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=0 base_margin_other_side=0 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_post_w=14 handle_thickness=20 post_center_x=40 arch_style="squared" arch_point_offset=1.4 corner_fillet=4 post_base_gussets=true gusset_base_len=10 gusset_height=12 gusset_thickness=3 post_flare=true flare_height=10 flare_width=4 fillet_r=2 chamfer_r=1
// @preset id="legacy-ogive" label="Legacy ogive (st-qt4)" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=18 base_margin_other_side=5 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_post_w=14 handle_thickness=20 post_center_x=94 arch_style="ogive" arch_point_offset=1.4 corner_fillet=4 post_base_gussets=true gusset_base_len=10 gusset_height=12 gusset_thickness=3 post_flare=true flare_height=10 flare_width=4 fillet_r=2 chamfer_r=1
// @preset id="legacy-semicircular" label="Legacy semicircular (v-prior)" can_diameter=50 can_height=195 clearance=0.75 ring_height=35 wall=3 rows=2 cols=3 cell_spacing_x=60 cell_spacing_y=90 front_opening_deg=100 base_thickness=3 base_margin_handle_side=18 base_margin_other_side=5 drain_hole_d=5 drain_hole_count=3 handle_height=250 handle_post_w=14 handle_thickness=20 post_center_x=94 arch_style="semicircular" arch_point_offset=1.4 corner_fillet=4 post_base_gussets=false gusset_base_len=10 gusset_height=12 gusset_thickness=3 post_flare=false flare_height=10 flare_width=4 fillet_r=2 chamfer_r=1

// === Derived ===

ring_id = can_diameter + 2 * clearance;
ring_od = ring_id + 2 * wall;

function cell_x(c) = (c - (cols - 1) / 2) * cell_spacing_x;
function cell_y(r) = (r - (rows - 1) / 2) * cell_spacing_y;

base_w = cell_spacing_x * (cols - 1) + ring_od + 2 * base_margin_handle_side;
base_d = cell_spacing_y * (rows - 1) + ring_od + 2 * base_margin_other_side;

// Handle-post X span. `post_center_x` is now a user-tunable @param
// (st-kyz). Posts live at Y=0 on the handle-axis corridor; see the
// load-bearing invariants in the header.
post_outer_x  = post_center_x + handle_post_w / 2;
post_inner_x  = post_center_x - handle_post_w / 2;

// Arch apex height above the post tops:
//   - squared: the crossbar height IS the apex rise (handle_post_w).
//   - semicircular: radius = post_outer_x, apex rises by post_outer_x.
//   - ogive: two arcs with centers at (±k·post_outer_x, post_top) and
//     radius (k+1)·post_outer_x. The apex sits at X=0 at a height
//     post_outer_x · sqrt(2k+1) above the post tops.
arch_apex_rise =
    arch_style == "squared" ? handle_post_w
  : arch_style == "ogive"   ? post_outer_x * sqrt(2 * arch_point_offset + 1)
  :                           post_outer_x;  // semicircular

// handle_height = apex above baseplate top (unchanged). arch_z_start is
// the z of the post tops above the baseplate top. For the ogive default
// (k=1.4) arch_apex_rise ≈ 1.95 · post_outer_x, so the post height
// drops ~95 mm below the v-prior semicircle when keeping apex fixed —
// that's the price of an apex-matched pointed arch. If you need taller
// posts (e.g. to clear a can-plus-grip band), increase handle_height.
arch_z_start = handle_height - arch_apex_rise;

// PRINT_ANCHOR_BBOX at defaults. With compact margins (both 0) and
// posts pulled in to ±40 (st-kyz):
//   X = base_w = cell_spacing_x*(cols-1) + ring_od = 120 + 57.5 = 177.5
//   Y = base_d = cell_spacing_y*(rows-1) + ring_od = 90  + 57.5 = 147.5
//   Z = base_thickness + handle_height = 3 + 250 = 253
// The posts (X=±40±7) and crossbar (spans X=±47) sit well within the
// baseplate X footprint.
PRINT_ANCHOR_BBOX = [177.5, 147.5, 253];

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

// Outer gusset X-reach is clamped so the gusset doesn't cantilever past
// the baseplate. Inner gusset reaches the default length (there's
// ample room between the post's inner face and the carrier centerline).
_outer_gusset_len_limit = max(0, base_w / 2 - post_outer_x);
_outer_gusset_len = min(gusset_base_len, _outer_gusset_len_limit);
_inner_gusset_len = gusset_base_len;

module handle() {
    for (sx = [-1, 1]) {
        _post(sx);
        if (post_base_gussets) _post_gussets(sx);
    }
    if      (arch_style == "squared") _arch_squared();
    else if (arch_style == "ogive")   _arch_ogive();
    else                              _arch_semicircle();
}

// --- Squared / toolbox crossbar (st-kyz, new default) ---
// Horizontal crossbar sitting on top of the two posts. Cross-section
// `handle_post_w × handle_thickness` — the crossbar is the same
// thickness (Y) as the posts, so post sides and crossbar Y-faces are
// flush. Extends in X to ±post_outer_x so its outer faces line up
// with the posts' outer faces. Bridges `2·post_inner_x` of open air
// between the posts — trivially bridgeable at default defaults
// (~66 mm between post inner faces). Rounded at the 4 X-Z corners
// with `corner_fillet` so the silhouette has a toolbox-ish soft top.
module _arch_squared() {
    crossbar_w = 2 * post_outer_x;
    translate([0, 0, post_top_z + handle_post_w / 2])
        cuboid([crossbar_w, handle_thickness, handle_post_w],
               rounding = corner_fillet,
               edges    = "Y");
}

// A single handle post. Optionally flared over the lowest flare_height
// of its Z extent. Above flare_height the post is the plain filleted
// cuboid from the v-prior design.
module _post(sx) {
    cx = sx * post_center_x;
    if (post_flare && flare_height > 0 && flare_width > 0) {
        // Flared base: prismoid from (hpw + 2fw, hth + 2fw) at z=0 to
        // (hpw, hth) at z=flare_height. BOSL2 prismoid anchors to BOTTOM
        // so `translate([cx, 0, 0])` puts its base flush on the ground.
        translate([cx, 0, 0])
            prismoid(
                size1 = [handle_post_w + 2 * flare_width,
                         handle_thickness + 2 * flare_width],
                size2 = [handle_post_w, handle_thickness],
                h     = flare_height,
                anchor = BOTTOM
            );
        // Unflared section above the flare. Z ∈ [flare_height, post_h].
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

// Four gussets per post pair (two per post, on the +X and -X faces).
// Each is a right-triangle prism in the XZ plane: base along X from the
// post face outward by `gl`, height along Z from the baseplate top to
// `base_thickness + gusset_height`. Thickness in Y = gusset_thickness
// centered on the post.
module _post_gussets(sx) {
    for (side = [+1, -1]) {
        // side = +1 → gusset on the post face further from the carrier
        // center (outer); side = -1 → inner face. Post faces sit at
        //   outer face: sx * post_outer_x
        //   inner face: sx * post_inner_x
        face_x = sx * (side > 0 ? post_outer_x : post_inner_x);
        gl = side > 0 ? _outer_gusset_len : _inner_gusset_len;
        if (gl > 0 && gusset_height > 0) {
            // The triangle in XZ (extruded along Y):
            //   A = (face_x, base_thickness)                — inner corner at post+base
            //   B = (face_x + sx*side*gl, base_thickness)   — outer tip at base level
            //   C = (face_x, base_thickness + gusset_height) — top corner at post
            // The X offset uses sx*side so the gusset always grows AWAY
            // from the post face: +sx for outer (away from center), -sx
            // for inner (toward center).
            ax = face_x;
            bx = face_x + sx * side * gl;
            z0 = base_thickness;
            z1 = base_thickness + gusset_height;
            translate([0, 0, 0])
                rotate([90, 0, 0])
                    translate([0, 0, -gusset_thickness / 2])
                        linear_extrude(height = gusset_thickness)
                            polygon([[ax, z0],
                                     [bx, z0],
                                     [ax, z1]]);
        }
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
