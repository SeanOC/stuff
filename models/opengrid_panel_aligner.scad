// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// OpenGrid panel alignment tool: a stiff plate with a grid_x x grid_y
// (default 2x2) array of openGrid snaps on one face and a toolbox-style
// loop handle on the other. While installing openGrid panels on a wall
// you grip the handle, click the snap array into the already-mounted
// grid, and use the tool to register/hold the next panel's position and
// spacing as you seat it.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived tool is for personal use only; do not
// sell prints or files.
//
// === Print orientation (native) + where supports are actually needed ===
//
// Prints snaps-down: the snap faces are the first layers — the
// orientation the snap geometry was designed to print in (nubs and
// click slots all form correctly). Bed contact is the four 24.8 mm snap
// faces. In this orientation the SNAP SIDE needs no support at all:
//
//   - snap nubs/wedges: self-supporting by design (sub-mm ledges,
//     >=45deg wedge cuts) — same as every other openGrid model here;
//   - plate underside between snaps: 3.2 mm bridges on the 28 mm pitch
//     (proven at these exact spans by the led_remote_holder twins);
//   - plate underside margin ring: 45deg rim chamfer, clamped so it
//     never crosses a snap footprint (full backing preserved, st-ocs).
//
// Slicer-generated support in the 3.2 mm x snap-depth channels between
// the snaps is near-impossible to dig out — that is exactly why NOTHING
// in this model ever needs (or models) support down there.
//
// The one real span in the print is the handle crossbar: its straight
// section is a ~22 mm bridge at defaults (bridgeable — the spraycan
// carrier OKs ~56 mm — but the sag lands on the grip surface). The
// optional built-in breakaway support (include_supports, DEFAULT TRUE)
// is a thin fin under the crossbar standing on the PLATE TOP — the
// handle side of the plate, nowhere near the snap gaps, open and
// reachable from both sides of the loop. Interfaces:
//
//   - fin -> crossbar: pure air gap (support_gap, default 0.25) — the
//     bridge sags onto the fin crest and tacks lightly, like slicer
//     support Z-distance; pulls free when the fin is removed;
//   - fin -> plate: single narrow neck line (support_neck wide, 0.4 mm
//     exposed height) — grab the fin tab and rock it sideways; the
//     neck peels off zipper-style and the stub line sands flat.
//
// Set include_supports=false for the clean part (print as-is and let
// the crossbar bridge, or use your own supports — with a support
// BLOCKER in the snap channels).
//
// === Structure ===
//
// Snaps (z=0 up to snap_h) weld 0.02 mm into the plate bottom (st-v7k:
// face-kissing unions leave detached shells / non-manifold tangent
// edges). Each snap carries the root-fillet shims from the
// led_remote_holder models: openGridSnap's four click nubs are
// face-touching solids whose root tangent line survives as a
// non-2-manifold edge; a 0.3 mm shim straddling each nub root fuses
// nub and core into one clean solid on both CGAL and Manifold.
//
// The handle is the spraycan-carrier toolbox pattern: two vertical
// posts + horizontal crossbar sharing one diameter, joined by true
// tangent-arc quarter-torus corner sweeps (2deg overlap past tangent at
// each end, st-7o3). All cylindrical surfaces — comfortable to grip,
// self-supporting at every point except the crossbar's straight
// section.
//
// NOTE on rounding style: nothing in this model uses hull-backed
// rounding (BOSL2 cuboid edges=/except=) — the wasm engine's CGAL
// applyHull() asserts on some swept dimensions (st-7x7/st-560 class).
// Vertical edges get 2D rounded-rect footprints extruded in Z; exposed
// rims get explicit 45deg chamfer prisms.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Snap array -----
grid_x = 2;        // @param number min=1 max=4 step=1 group=array label="Snap columns (X)"
grid_y = 2;        // @param number min=1 max=4 step=1 group=array label="Snap rows (Y)"
snap_lite = false; // @param boolean group=array label="Lite snaps (3.4mm instead of 6.8mm)"

// ----- Plate -----
plate_margin = 4;  // @param number min=1 max=10 step=0.5 unit=mm group=plate label="Plate margin beyond snap array"
plate_t      = 4;  // @param number min=3 max=6 step=0.5 unit=mm group=plate label="Plate thickness"

// ----- Handle -----
handle_span    = 40; // @param number min=30 max=90 step=1 unit=mm group=handle label="Handle width — post-centre to post-centre (X)"
handle_clear   = 30; // @param number min=20 max=50 step=1 unit=mm group=handle label="Finger clearance under the crossbar"
handle_bar_d   = 14; // @param number min=10 max=20 step=0.5 unit=mm group=handle label="Post / crossbar diameter"
corner_sweep_r = 10; // @param number min=0 max=16 step=0.5 unit=mm group=handle label="Corner sweep radius"

// ----- Built-in breakaway support (see header) -----
include_supports = true; // @param boolean group=printing label="Breakaway fin under the crossbar"
support_gap  = 0.25;     // @param number min=0.15 max=0.4 step=0.05 unit=mm group=printing label="Fin-to-crossbar air gap"
support_neck = 0.45;     // @param number min=0.3 max=0.6 step=0.05 unit=mm group=printing label="Fin-to-plate neck width"

// @preset id="default" label="Default (built-in breakaway fin)" grid_x=2 grid_y=2 snap_lite=false plate_margin=4 plate_t=4 handle_span=40 handle_clear=30 handle_bar_d=14 corner_sweep_r=10 include_supports=true support_gap=0.25 support_neck=0.45
// @preset id="clean" label="Clean part (no built-in supports)" include_supports=false

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed depth of snap tops into the plate (st-v7k)

span_x  = (grid_x - 1) * snap_pitch + snap_w;  // snap array outer extent
span_y  = (grid_y - 1) * snap_pitch + snap_w;
plate_w = span_x + 2 * plate_margin;
plate_d = span_y + 2 * plate_margin;

plate_z0  = snap_h - weld;          // plate bottom (welds into snap tops)
plate_top = plate_z0 + plate_t;

post_r          = handle_bar_d / 2;
crossbar_axis_z = plate_top + handle_clear + post_r;
apex_z          = crossbar_axis_z + post_r;
// The handle auto-shrinks to keep the posts >= 1mm inside the plate
// edge, and the corner sweep to fit the (possibly shrunk) span — so no
// param combination the sliders can reach produces a handle hanging
// off the plate or a sweep wider than the span (the param sweep test
// renders every single-param extreme).
hspan = min(handle_span, plate_w - 2 - handle_bar_d);
sweep = min(corner_sweep_r, hspan / 2);

plate_corner_r = 3;
top_chamfer    = 0.8;  // hand-feel chamfer on the plate top rim
// 45deg bottom-rim chamfer: sized to leave a 0.4 vertical rim between
// it and the top chamfer (their combined depth must stay under
// plate_t), and clamped so the cut never crosses a snap footprint —
// every snap stays fully backed by full-thickness plate (st-ocs).
plate_chamfer = min(plate_t - 0.4 - top_chamfer, plate_margin - 0.2);
// Walls/posts sink this far into the solid below them. Zero-overlap
// (face-kissing) unions leave the CGAL export with detached shells or
// tangent-line non-manifold edges (st-v7k class).
bury = 0.6;

// PRINT_ANCHOR_BBOX at defaults:
//   X = plate_w = 28 + 24.8 + 2*4                  = 60.8
//   Y = plate_d = 28 + 24.8 + 2*4                  = 60.8
//   Z = apex_z  = 6.8 - 0.02 + 4 + 30 + 14         = 54.78
PRINT_ANCHOR_BBOX = [60.8, 60.8, 54.78];

// === Snaps ===
// Frame: XY centered on the array, z = 0 on the bed at the snap faces.

// openGridSnap models its four click nubs as face-touching (zero
// overlap) solids, and the bottom-wedge undercut leaves each nub
// kissing the core along a bare tangent line at the nub root. Under
// the Manifold backend the nubs export as four detached shells; under
// CGAL they corefine into one body but the root line survives as a
// non-2-manifold edge, which fails the export gate's strict trimesh
// watertight check. The root-fillet shim below is a 0.3 x 11.6 x 0.62
// cuboid straddling each nub/core contact plane (local x=12.4) right
// at the nub root: it submerges the tangent line and volumetrically
// bridges nub to core, making the snap one clean solid on BOTH
// backends. It reads as a sub-0.3mm root fillet in the click
// undercut — smaller than the blob FDM leaves there anyway.
// Non-directional snaps: the tool is clicked in and pulled out
// constantly, in any rotation — symmetric engagement on all four sides.
module welded_snap() {
    root_z = snap_lite ? 0 : 3.39;  // clamp to the bed for lite snaps
    openGridSnap(lite = snap_lite, directional = false,
                 anchor = BOT, orient = UP);
    zrot_copies(n = 4)
        translate([12.4, 0, root_z])
            cuboid([0.3, 11.6, snap_lite ? 0.61 : 0.62], anchor = BOT);
}

module grid_snaps() {
    for (cx = [0 : grid_x - 1], ry = [0 : grid_y - 1])
        translate([(cx - (grid_x - 1) / 2) * snap_pitch,
                   (ry - (grid_y - 1) / 2) * snap_pitch,
                   0])
            welded_snap();
}

// === Plate ===

module plate_body() {
    translate([0, 0, plate_z0])
        linear_extrude(height = plate_t)
            rect([plate_w, plate_d], rounding = plate_corner_r);
}

// 45deg chamfer cuts along all four bottom edges of the plate. Four
// explicit triangular prisms (bounded below at the plate bottom plane
// so they cannot clip the snaps) rather than edge_profile(): the
// prisms overshoot the ends and overlap each other at the corners, so
// the cuts stay transversal through the rounded plate corners.
module plate_rim_chamfers() {
    c = plate_chamfer;
    // ±X edges: profile in XZ, extruded along Y.
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, (plate_d + 4) / 2, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = plate_d + 4)
                        polygon([[plate_w / 2 - c, plate_z0],
                                 [plate_w / 2 + 2, plate_z0],
                                 [plate_w / 2 + 2, plate_z0 + c + 2]]);
    // ±Y edges: profile in YZ, extruded along X.
    for (sy = [-1, 1])
        scale([1, sy, 1])
            translate([-(plate_w + 4) / 2, -plate_d / 2, 0])
                rotate([90, 0, 90])
                    linear_extrude(height = plate_w + 4)
                        polygon([[c, plate_z0],
                                 [-2, plate_z0],
                                 [-2, plate_z0 + c + 2]]);
}

// 45deg hand-feel chamfers along the plate's four top edges (the
// hull-free stand-in for top-edge rounding).
module plate_top_chamfers() {
    ch = top_chamfer;
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, (plate_d + 4) / 2, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = plate_d + 4)
                        polygon([[plate_w / 2 - ch, plate_top],
                                 [plate_w / 2 + 2, plate_top - ch - 2],
                                 [plate_w / 2 + 2, plate_top + 2],
                                 [plate_w / 2 - ch, plate_top + 2]]);
    for (sy = [-1, 1])
        scale([1, sy, 1])
            translate([-(plate_w + 4) / 2, -plate_d / 2, 0])
                rotate([90, 0, 90])
                    linear_extrude(height = plate_w + 4)
                        polygon([[ch, plate_top],
                                 [-2, plate_top - ch - 2],
                                 [-2, plate_top + 2],
                                 [ch, plate_top + 2]]);
}

module plate() {
    difference() {
        plate_body();
        plate_rim_chamfers();
        plate_top_chamfers();
    }
}

// === Handle ===
// Toolbox loop (spraycan-carrier pattern): two vertical posts + one
// horizontal crossbar sharing handle_bar_d, joined by tangent-arc
// quarter-torus corner sweeps. Post tops sit corner_sweep_r below the
// crossbar axis; crossbar endpoints sit corner_sweep_r inside the post
// X. 1mm overlap at every junction (st-v7k).

module _post_cyl(sx, post_total_h) {
    translate([sx * hspan / 2, 0, plate_top - bury])
        cylinder(h = post_total_h + bury, r = post_r);
}

module _crossbar_cyl(half_len) {
    translate([-half_len, 0, crossbar_axis_z])
        rotate([0, 90, 0])
            cylinder(h = 2 * half_len, r = post_r);
}

// Quarter-torus inside-corner blend, tangent-vertical at the post end
// and tangent-horizontal at the crossbar end. Extended 2deg past
// tangent at each end (st-7o3): stopping exactly at 0/90deg leaves
// non-manifold edges at the sweep-to-cylinder tangent junctions;
// sweeping into the cylinder volumes forces a clean CSG union.
module _handle_corner_sweep(sx) {
    sweep_eps = 2;
    scale([sx, 1, 1])
        translate([hspan / 2 - sweep, 0, crossbar_axis_z - sweep])
            rotate([90, 0, -sweep_eps])
                rotate_extrude(angle = 90 + 2 * sweep_eps, convexity = 4)
                    translate([sweep, 0])
                        circle(r = post_r);
}

module handle() {
    if (sweep > 0) {
        post_total_h    = handle_clear + post_r - sweep + 1;
        crossbar_half_x = hspan / 2 - sweep + 1;
        for (sx = [-1, 1]) {
            _post_cyl(sx, post_total_h);
            _handle_corner_sweep(sx);
        }
        _crossbar_cyl(crossbar_half_x);
    } else {
        for (sx = [-1, 1])
            _post_cyl(sx, handle_clear + post_r);
        _crossbar_cyl(hspan / 2 + post_r);
    }
}

// === Breakaway support fin (see header) ===
// Thin fin under the crossbar's straight section, standing on the
// plate top inside the loop. Top edge stops support_gap below the
// crossbar's underside (air-gap interface); bottom necks down to a
// support_neck-wide line that welds bury-deep into the plate (the
// snap-off point). The fin body is deliberately chunky (fin_th) so
// there's a real tab to grab; only the neck is thin.
fin_th     = 1.2;  // fin body thickness (Y)
fin_neck_h = 0.4;  // exposed neck height above the plate
fin_top    = crossbar_axis_z - post_r - support_gap;
// Cover the crossbar's straight span only: stop at the corner-sweep
// junction (the sweep's underside dips BELOW the bar underside toward
// the posts and would swallow a wider fin), and never closer than 1mm
// to a post's inner face (small sweep radii) — the fin must stay
// breakaway, touching nothing but its two designed interfaces.
fin_half_x = hspan / 2 - max(sweep, post_r + 1);

module support_fin() {
    // Neck line: fin-to-plate breakaway interface. Runs bury deep into
    // the plate and bury high into the fin body — and 0.3 short of the
    // body's X ends — so both junctions are real volumetric overlaps,
    // never face-kissing coplanar contacts (st-v7k).
    translate([-fin_half_x + 0.3, -support_neck / 2, plate_top - bury])
        cube([2 * fin_half_x - 0.6, support_neck,
              bury + fin_neck_h + bury]);
    // Fin body: from just above the plate (fin_neck_h exposed neck) up
    // to the air gap under the bar.
    translate([-fin_half_x, -fin_th / 2, plate_top + fin_neck_h])
        cube([2 * fin_half_x, fin_th, fin_top - plate_top - fin_neck_h]);
}

// === Assembly ===

grid_snaps();
plate();
handle();
// Skip the fin when the crossbar's straight span is too short to need
// support, or the fin would be degenerately squat — a sub-4mm bridge
// needs no help and a sliver fin is unprintable anyway.
if (include_supports && fin_half_x >= 2 && fin_top - plate_top > 5)
    support_fin();
