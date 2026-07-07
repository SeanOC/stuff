// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// OpenGrid panel alignment tool: a stiff plate with a grid_x x grid_y
// (default 2x2) array of openGrid snaps on one face and a domed grip
// knob on the other. While installing openGrid panels on a wall you
// grip the knob, click the snap array into the already-mounted grid,
// and use the tool to register/hold the next panel's position and
// spacing as you seat it.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived tool is for personal use only; do not
// sell prints or files.
//
// === Print orientation (native): ZERO supports ===
//
// Prints snaps-down: the snap faces are the first layers — the
// orientation the snap geometry was designed to print in (nubs and
// click slots all form correctly). Bed contact is the four 24.8 mm snap
// faces. NOTHING in this model needs support — no built-in breakaway
// geometry, no slicer supports. Slice as-is with supports OFF:
//
//   - snap nubs/wedges: self-supporting by design (sub-mm ledges,
//     >=45deg wedge cuts) — same as every other openGrid model here;
//   - plate underside between snaps: 3.2 mm bridges on the 28 mm pitch
//     (proven at these exact spans by the led_remote_holder twins);
//   - plate underside margin ring: 45deg rim chamfer, clamped so it
//     never crosses a snap footprint (full backing preserved, st-ocs);
//   - knob: prints knob-up as stacked circles — straight cylinder wall,
//     domed top that steepens toward the apex (a dome's overhang angle
//     is worst at its base, where it's tangent-vertical) — and NO
//     flare/undercut/mushroom lip anywhere in the profile. An earlier
//     revision used an arched loop handle whose horizontal crossbar was
//     the ONE span needing (built-in breakaway) support; the knob
//     replaced it in st-7lc precisely to make the whole part
//     support-free.
//
// Slicer-generated support in the 3.2 mm x snap-depth channels between
// the snaps is near-impossible to dig out — that is exactly why NOTHING
// in this model may ever put geometry (or need support) down there.
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
// The knob is one rotate_extrude of a single closed 2D profile —
// straight cylinder wall capped by a tangent arc (dome when
// knob_top_r = knob_d/2, rounded rim chamfer when smaller) — so the
// whole grip is one revolved solid with no internal unions to leak
// (st-v7k class); its base buries `bury` deep into the plate top.
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

// ----- Knob -----
knob_d     = 25;   // @param number min=18 max=32 step=0.5 unit=mm group=knob label="Knob diameter"
knob_h     = 34;   // @param number min=24 max=44 step=1 unit=mm group=knob label="Knob height above the plate"
knob_top_r = 12.5; // @param number min=2 max=16 step=0.5 unit=mm group=knob label="Top dome / rim-round radius"

// @preset id="default" label="Default (domed knob, zero supports)" grid_x=2 grid_y=2 snap_lite=false plate_margin=4 plate_t=4 knob_d=25 knob_h=34 knob_top_r=12.5

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

// The knob auto-shrinks to stay >= 1mm inside the plate edge on the
// short axis (a 1x1 array at margin 1 makes a 26.8mm plate — smaller
// than the 32mm the knob_d slider reaches), same policy as the old
// handle: no slider combination produces a grip hanging off the plate.
knob_r = min(knob_d, min(plate_w, plate_d) - 2) / 2;
// Top-arc radius clamped so the revolved profile can't invert: never
// wider than the knob radius (at the clamp the cap is a full
// hemispherical dome) and never taller than the knob leaves room for.
dome_r = min(knob_top_r, knob_r, knob_h - 2);
apex_z = plate_top + knob_h;

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
//   Z = apex_z  = 6.8 - 0.02 + 4 + 34              = 44.78
PRINT_ANCHOR_BBOX = [60.8, 60.8, 44.78];

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
// explicit triangular prisms rather than edge_profile(): the prisms
// overshoot the ends and overlap each other at the corners, so the
// cuts stay transversal through the rounded plate corners. The prisms
// also overshoot 2mm BELOW the plate bottom plane — a cut bottom
// coplanar with the plate bottom face is a degenerate boolean that
// renders as a scalloped z-fighting artifact (st-n4v). Overshooting
// down cannot clip the snaps: this is differenced from plate_body()
// only; grid_snaps() is a sibling union at top level. The hypotenuse
// still passes through (edge - plate_chamfer, plate_z0), so the
// visible chamfer is unchanged.
module plate_rim_chamfers() {
    c = plate_chamfer;
    // ±X edges: profile in XZ, extruded along Y.
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, (plate_d + 4) / 2, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = plate_d + 4)
                        polygon([[plate_w / 2 - c - 2, plate_z0 - 2],
                                 [plate_w / 2 + 2, plate_z0 - 2],
                                 [plate_w / 2 + 2, plate_z0 + c + 2]]);
    // ±Y edges: profile in YZ, extruded along X.
    for (sy = [-1, 1])
        scale([1, sy, 1])
            translate([-(plate_w + 4) / 2, -plate_d / 2, 0])
                rotate([90, 0, 90])
                    linear_extrude(height = plate_w + 4)
                        polygon([[c + 2, plate_z0 - 2],
                                 [-2, plate_z0 - 2],
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

// === Knob ===
// One revolved solid: rotate_extrude of a closed 2D profile — flat
// base (buried bury-deep into the plate, st-v7k), straight cylinder
// wall, then a tangent arc into the top. At dome_r = knob_r the cap is
// a full hemispherical dome; smaller dome_r leaves a flat top circle
// with a rounded rim. Every point of the revolved surface is at or
// steeper than the arc's base tangent (vertical), so the knob is
// self-supporting printing knob-up — and there is deliberately no
// flare/undercut/mushroom lip, which would reintroduce the need for
// support this knob exists to remove (see header).

module knob() {
    z0 = plate_top - bury;          // buried base plane
    z1 = apex_z - dome_r;           // where the wall meets the top arc
    // Quarter arc from (knob_r, z1) up to (knob_r - dome_r, apex_z),
    // centered on (knob_r - dome_r, z1) — tangent-vertical where it
    // leaves the wall, tangent-horizontal at the top.
    arc_pts = [for (a = [0 : 90 / 24 : 90])
                   [knob_r - dome_r + dome_r * cos(a),
                    z1 + dome_r * sin(a)]];
    // Close along the axis only when the arc doesn't already end
    // there (dome_r < knob_r): a duplicate vertex at the apex would
    // make a degenerate polygon edge.
    axis_top = (dome_r < knob_r - 0.01) ? [[0, apex_z]] : [];
    rotate_extrude(convexity = 2)
        polygon(concat([[0, z0], [knob_r, z0]], arc_pts, axis_top));
}

// === Assembly ===

grid_snaps();
plate();
knob();
