// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// OpenGrid wall holder for a 55 x 124 x 7.7 mm LED-strip controller remote.
//
// Portrait open-front cradle: side + bottom walls retain the remote,
// 45deg-underside retaining lips over the long edges keep it from
// falling forward, and a rounded thumb scoop through both side walls
// lets you pinch the remote's edges and slide it up and out. The back
// plate carries openGrid snaps on the standard 28 mm tile pitch.
//
// Twin model: led_remote_holder_51x84mm.scad is this same design with
// different remote dims / snap-grid defaults. The two files are kept
// textually identical apart from the parameter defaults and this
// header, because the browser render pipeline can only resolve
// includes from vendored libs/ — a shared project-side module file is
// not reachable there. Fix a bug here → apply it to the twin too.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived holder is for personal use only; do
// not sell prints or files.
//
// === Print orientation (native) ===
//
// Prints snaps-down: the snap faces are the first layers — that is the
// orientation the snap geometry was designed to print in (nubs and
// click slots all form correctly). The back plate spans the snap tops
// (3.2 mm bridges between snaps) and its bottom rim carries a 45deg
// chamfer sized plate_t - 0.4, so the rim overhang beyond the snap
// grid is self-supporting. The retaining lips' undersides rise inward
// at 45deg for the same reason. No supports needed at defaults.
//
// === Retention geometry ===
//
// The lip underside is a 45deg plane rising from the wall's inner face
// at the remote's face level up to the lip tip (lip_over higher). The
// plane converges at the walls, so although the lip tip sits lip_over
// above the remote face, the remote's face EDGE meets the chamfer
// plane after only ~side_clearance mm of forward float — retention
// play stays under ~1 mm at defaults.
//
// === Snap grid ===
//
// Snap count auto-fits from the plate size: as many 24.8 mm snap
// footprints as fit on the 28 mm openGrid pitch inside the plate,
// keeping >= 1 mm rim per side, always centered. At defaults that is
// 2 cols x 4 rows of full-depth (6.8 mm) snaps.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Remote -----
remote_w = 55;    // @param number min=40 max=70 step=0.5 unit=mm group=remote label="Remote width"
remote_h = 124;   // @param number min=70 max=160 step=0.5 unit=mm group=remote label="Remote height"
remote_d = 7.7;   // @param number min=4 max=12 step=0.1 unit=mm group=remote label="Remote depth"
side_clearance  = 0.45; // @param number min=0.2 max=1 step=0.05 unit=mm group=remote label="Pocket clearance per side"
depth_clearance = 0.3;  // @param number min=0 max=1 step=0.05 unit=mm group=remote label="Pocket depth clearance"

// ----- Cradle -----
wall    = 2.4;  // @param number min=1.6 max=4 step=0.1 unit=mm group=cradle label="Wall thickness"
plate_t = 3;    // @param number min=2 max=5 step=0.5 unit=mm group=cradle label="Back plate thickness"
lip_over = 3;   // @param number min=1.5 max=5 step=0.5 unit=mm group=cradle label="Retaining lip reach"
lip_t    = 2;   // @param number min=1 max=4 step=0.5 unit=mm group=cradle label="Retaining lip thickness"
scoop_r  = 13;  // @param number min=8 max=18 step=0.5 unit=mm group=cradle label="Thumb scoop radius"
// Cap on the back-plate length. Below the full cradle length the
// remote sticks out the top (easier to grab) and the snap-grid rim
// margins stay small enough to print support-free. 116 caps this
// model below its full 127.3: the 4-row snap span is 108.8, leaving
// 3.6 mm rim margins (within the 45deg chamfer budget), and the
// remote stands ~10 mm proud of the top edge for grip.
plate_len_max = 116; // @param number min=60 max=300 step=1 unit=mm group=cradle label="Back plate length cap"

// ----- OpenGrid mount -----
snap_lite = false; // @param boolean group=mount label="Lite snaps (3.4mm instead of 6.8mm)"

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed depth of snap tops into the plate (st-v7k)

pocket_w     = remote_w + 2 * side_clearance;
outer_w      = pocket_w + 2 * wall;
pocket_depth = remote_d + depth_clearance;
plate_len    = min(wall + remote_h + 2 * side_clearance, plate_len_max);

// Snap grid auto-fit: as many snaps as fit at 28mm pitch, keeping a
// 1mm rim per side.
snap_cols = max(1, floor((outer_w   - 2 - snap_w) / snap_pitch) + 1);
snap_rows = max(1, floor((plate_len - 2 - snap_w) / snap_pitch) + 1);
assert(snap_cols * snap_rows >= 2,
       "fewer than 2 snaps fit this plate; grow the remote dims or plate_len_max");

plate_z0  = snap_h - weld;          // plate bottom (welds into snap tops)
plate_top = plate_z0 + plate_t;
face_z    = plate_top + pocket_depth;      // remote face plane
wall_h    = pocket_depth + lip_over + lip_t;
rail_top  = plate_top + wall_h;

// Corner rounding is 1 everywhere so the wall corner arcs sit exactly
// on the plate corner arcs (mismatched radii would leave micro-ledges).
plate_corner_r = 1;
plate_chamfer  = plate_t - 0.4;  // 45deg bottom-rim chamfer, keeps a 0.4 vertical rim
edge_r         = 1;              // hand-feel rounding on walls/lips
// Walls/rails sink this far into the solid below them. Zero-overlap
// (face-kissing) unions leave the CGAL export with detached shells or
// tangent-line non-manifold edges (st-v7k class); every junction in
// this model overlaps by a real volume instead.
bury = 0.6;

// PRINT_ANCHOR_BBOX at defaults:
//   X = outer_w  = 55 + 2*0.45 + 2*2.4          = 60.7
//   Y = plate_len = min(2.4 + 124 + 2*0.45, 116) = 116
//   Z = snap_h - weld + plate_t + pocket_depth + lip_over + lip_t
//     = 6.78 + 3 + 8.0 + 3 + 2                   = 22.78
PRINT_ANCHOR_BBOX = [60.7, 116, 22.78];

// === Geometry ===
// Frame: X centered, Y = 0 at the plate's bottom edge (bottom of the
// cradle as mounted), Z = 0 on the bed at the snap faces.

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
module welded_snap() {
    root_z = snap_lite ? 0 : 3.39;  // clamp to the bed for lite snaps
    openGridSnap(lite = snap_lite, directional = false,
                 anchor = BOT, orient = UP);
    zrot_copies(n = 4)
        translate([12.4, 0, root_z])
            cuboid([0.3, 11.6, snap_lite ? 0.61 : 0.62], anchor = BOT);
}

module grid_snaps() {
    for (cx = [0 : snap_cols - 1], ry = [0 : snap_rows - 1])
        translate([(cx - (snap_cols - 1) / 2) * snap_pitch,
                   plate_len / 2 + (ry - (snap_rows - 1) / 2) * snap_pitch,
                   0])
            welded_snap();
}

// NOTE on rounding style: BOSL2 cuboid() implements partial edge
// rounding (edges=/except=) as hull() of eight corner pieces. The
// wasm engine's CGAL applyHull() asserts on some swept dimensions
// (convex_hull_3.h:684 — the st-7x7/st-560 bug class), which shatters
// the param sweep. So nothing in this model uses hull-backed
// rounding: vertical edges get 2D rounded-rect footprints extruded in
// Z, and exposed top edges get explicit 45deg chamfer prisms.

module back_plate() {
    translate([0, 0, plate_z0])
        linear_extrude(height = plate_t)
            rect([outer_w, plate_len], rounding = plate_corner_r,
                 anchor = FRONT);
}

// 45deg chamfer cuts along all four bottom edges of the plate. Four
// explicit triangular prisms (bounded below at the plate bottom plane
// so they cannot clip the snaps) rather than edge_profile(): the
// prisms overshoot the ends and overlap each other at the corners, so
// the cuts stay transversal through the rounded plate corners —
// edge_profile's per-edge masks stop at the corners and leave
// tangent-line non-manifold edges there. Each cut plane rises from
// the plate bottom at (edge - plate_chamfer) to a 0.4mm vertical rim
// at the edge.
module plate_rim_chamfers() {
    c = plate_chamfer;
    // ±X edges: profile in XZ, extruded along Y.
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, plate_len + 2, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = plate_len + 4)
                        polygon([[outer_w / 2 - c, plate_z0],
                                 [outer_w / 2 + 2, plate_z0],
                                 [outer_w / 2 + 2, plate_z0 + c + 2]]);
    // ±Y ends: profile in YZ, extruded along X; the -Y prism is built
    // directly and mirrored across y = plate_len/2 for the +Y end.
    for (sy = [0, 1])
        translate([0, sy * plate_len, 0])
            mirror([0, sy, 0])
                translate([-(outer_w + 4) / 2, 0, 0])
                    rotate([90, 0, 90])
                        linear_extrude(height = outer_w + 4)
                            polygon([[c, plate_z0],
                                     [-2, plate_z0],
                                     [-2, plate_z0 + c + 2]]);
}

// One vertical side wall + its retaining lip, on the +X side; the
// caller mirrors it. The lip profile is a quad whose underside rises
// inward at 45deg from the remote face plane (see header).
module side_wall_right() {
    // Footprint with the two OUTER corners rounded; the inner corners
    // stay square so the rail's buried overlap never pokes through a
    // rounded inner corner. rect() rounding order: [X+Y+,X-Y+,X-Y-,X+Y-].
    translate([pocket_w / 2 + wall / 2, 0, plate_top - bury])
        linear_extrude(height = wall_h + bury)
            rect([wall, plate_len], rounding = [edge_r, 0, 0, edge_r],
                 anchor = FRONT);
    // The profile's first two points extend `bury` past the wall's
    // inner face (u < 0), continuing the 45deg underside into the
    // wall's interior so rail and wall genuinely overlap.
    rail_profile = [
        [-bury,    pocket_depth - bury],
        [lip_over, pocket_depth + lip_over],
        [lip_over, wall_h],
        [-bury,    wall_h],
    ];
    translate([pocket_w / 2, plate_len, plate_top])
        xflip()
            rotate([90, 0, 0])
                linear_extrude(height = plate_len)
                    polygon(rail_profile);
}

// Bottom wall: full cradle height, closing the bottom end into a cup
// rim so the remote cannot squeeze out forward at the bottom.
module bottom_wall() {
    translate([0, 0, plate_top - bury])
        linear_extrude(height = wall_h + bury)
            rect([outer_w, wall], rounding = [0, 0, edge_r, edge_r],
                 anchor = FRONT);
}

// 45deg chamfers along the cradle's exposed top edges (the hull-free
// stand-in for cuboid top-edge rounding): both long outer edges, plus
// both ends — the top-end cut doubles as a lead-in for sliding the
// remote under the rails.
module top_edge_chamfers() {
    ch = 0.8;
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, plate_len + 2, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = plate_len + 4)
                        polygon([[outer_w / 2 - ch, rail_top],
                                 [outer_w / 2 + 2, rail_top - ch - 2],
                                 [outer_w / 2 + 2, rail_top + 2],
                                 [outer_w / 2 - ch, rail_top + 2]]);
    for (sy = [0, 1])
        translate([0, sy * plate_len, 0])
            mirror([0, sy, 0])
                translate([-(outer_w + 4) / 2, 0, 0])
                    rotate([90, 0, 90])
                        linear_extrude(height = outer_w + 4)
                            polygon([[ch, rail_top],
                                     [-2, rail_top - ch - 2],
                                     [-2, rail_top + 2],
                                     [ch, rail_top + 2]]);
}

// Thumb scoop: a horizontal cylinder (axis along X) carves a rounded
// valley through both walls and lips at mid-height. The cut floor
// stays 1.2mm above the plate, so the walls stay connected and the
// remote's side edges become pinchable.
module scoop_cut() {
    translate([0, plate_len / 2, plate_top + 1.2 + scoop_r])
        xcyl(r = scoop_r, l = outer_w + 4, $fn = 96);
}

module holder() {
    difference() {
        union() {
            back_plate();
            side_wall_right();
            xflip() side_wall_right();
            bottom_wall();
        }
        plate_rim_chamfers();
        top_edge_chamfers();
        scoop_cut();
    }
}

grid_snaps();
holder();
