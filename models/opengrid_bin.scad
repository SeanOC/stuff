// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Parametric open-topped wall bin for vertically-mounted openGrid
// panels (st-3mk). Sized in openGrid units (28 mm pitch): the back
// plate is exactly width_units x height_units tiles, so the mounted
// bin visually aligns with the grid, and it carries one directional
// snap per tile — click it straight into the wall and it works as a
// parts bin. Full-height side walls, open top for drop-in access, and
// a 45deg ramped front lip (scoop) so contents are retained but easy
// to grab.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived bin is for personal use only; do not
// sell prints or files.
//
// === Print orientation (native): ZERO supports ===
//
// Prints snaps-down: the snap faces are the first layers — the
// orientation the snap geometry was designed to print in. Every
// overhang in the body is a 45deg chamfer, never a flat span:
//
//  - plate underside between snaps: 3.2 mm bridges on the 28 mm pitch
//    (proven at these exact spans by the led_remote_holder twins);
//  - plate underside rim: 45deg chamfer, clamped so it never crosses a
//    snap footprint (st-ocs) nor climbs into the wall bases;
//  - floor, side walls: vertical fins rising in Z — trivially printable;
//  - front lip: there is deliberately NO vertical front wall (its
//    underside would be a flat overhang bridging the whole cavity —
//    unprintable without supports at multi-unit widths). Instead the
//    floor ramps up at 45deg to the lip crest, and the matching outer
//    chamfer trims the body's front-bottom corner, so both lip faces
//    are self-supporting 45deg planes;
//  - rear interior fillet: a 45deg wedge standing on the plate,
//    narrowing as it rises — supported at every layer.
//
// === Wall-hang orientation / load direction ===
//
// Mounted, +Y points UP the wall and the bin cantilevers its load off
// the panel. Two consequences:
//
//  - Directional snaps with the strong front nub (non-flexing, 0.8 mm
//    deep vs 0.4) pointing +Y, same rationale as
//    ego_lb6500_blower_mount (st-0of): the lever-out moment on the top
//    snap row bears on the rigid hook; the flexy click-in side faces
//    down where the moment presses the plate into the wall.
//  - The floor-to-plate joint takes the peel moment, so a full-width
//    45deg interior fillet (rear_fillet) thickens that corner and
//    shortens the lever arm — the "rear gusset" of the bead spec.
//
// === Structure / mesh-robustness notes ===
//
// Snaps weld 0.02 mm into the plate underside and each snap carries
// the root-fillet shims from the sibling models (st-v7k: openGridSnap's
// click nubs are face-touching solids; the shims fuse them into one
// clean solid on both CGAL and Manifold). The body is ONE extruded
// block minus three cuts (cavity, front chamfer, top-edge chamfers),
// buried 0.6 mm into the plate — no face-kissing unions anywhere.
// Rim-chamfer prisms overshoot 2 mm below the plate bottom plane
// (st-n4v: a coplanar cut bottom is a degenerate boolean) and are
// differenced from the plate only, so they cannot clip the snaps.
// Nothing uses hull-backed rounding (BOSL2 cuboid edges=) — the wasm
// engine's CGAL applyHull() asserts on some swept dimensions
// (st-7x7/st-560 class). Vertical edges get 2D rounded-rect footprints
// extruded in Z; exposed top edges get explicit 45deg chamfer prisms.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Size (openGrid units are 28mm) -----
width_units  = 2;  // @param integer min=1 max=6 group=size label="Width (openGrid units)"
height_units = 2;  // @param integer min=1 max=4 group=size label="Height (openGrid units)"
depth        = 60; // @param number min=25 max=120 step=1 unit=mm group=size label="Depth from panel face"

// ----- Shell -----
wall    = 2.4; // @param number min=1.6 max=4 step=0.1 unit=mm group=shell label="Wall thickness"
floor_t = 3;   // @param number min=2 max=5 step=0.5 unit=mm group=shell label="Floor thickness"
plate_t = 4;   // @param number min=3 max=6 step=0.5 unit=mm group=shell label="Back plate thickness"

// ----- Front / strength -----
// Both auto-clamp against shallow depths (see Derived) so no slider
// combination produces invalid geometry.
lip_rise    = 14; // @param number min=4 max=30 step=1 unit=mm group=shape label="Front lip rise (scoop)"
rear_fillet = 8;  // @param number min=0 max=15 step=1 unit=mm group=shape label="Rear floor fillet"

// ----- OpenGrid mount -----
snap_lite = false; // @param boolean group=mount label="Lite snaps (3.4mm instead of 6.8mm)"

// @preset id="default" label="2x2 units, 60mm deep" width_units=2 height_units=2 depth=60 wall=2.4 floor_t=3 plate_t=4 lip_rise=14 rear_fillet=8 snap_lite=false
// @preset id="wide_tray" label="4x1 units, 28mm (1u) deep tray" width_units=4 height_units=1 depth=28 wall=2.4 floor_t=3 plate_t=4 lip_rise=14 rear_fillet=8 snap_lite=false

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed depth of snap tops into the plate (st-v7k)

W = width_units * snap_pitch;   // plate/body footprint = whole tiles
H = height_units * snap_pitch;

plate_z0  = snap_h - weld;      // plate bottom (welds into snap tops)
plate_top = plate_z0 + plate_t;
z_front   = plate_z0 + depth;   // bin front face (depth counts from the
                                // panel face the plate back sits on)
body_depth = z_front - plate_top;
assert(body_depth >= 15,
       "depth leaves under 15mm of bin in front of the back plate");

// Auto-clamps: the fillet backs off first on shallow bins (keeping
// >= 12mm of body in front of it), then the lip shrinks to keep a
// >= 4mm flat floor run between fillet and ramp. lip_e also stays
// below the side-wall height so the scoop crest never outgrows the
// bin. Given body_depth >= 15 both always land in valid range.
rf    = min(rear_fillet, max(0, body_depth - 12));
lip_e = min(lip_rise, body_depth - rf - 4, H - floor_t - 4);
z_bend = z_front - lip_e;       // where the 45deg front ramp starts

// Walls sink this far into the solid below them. Zero-overlap
// (face-kissing) unions leave the CGAL export with detached shells or
// tangent-line non-manifold edges (st-v7k class).
bury = 0.6;
ov   = 2;    // cut-tool overshoot past the faces it cuts through

corner_r = 1;   // vertical-edge rounding, plate and body alike
top_ch   = 0.8; // hand-feel chamfer on the body's front-face rim
// 45deg plate bottom-rim chamfer. The snap grid leaves a 1.6mm rim
// ((28 - 24.8)/2) per side; clamp keeps the cut off the snap
// footprints (st-ocs) and below the body wall bases.
snap_margin   = (snap_pitch - snap_w) / 2;
plate_chamfer = min(plate_t - bury - 0.2, snap_margin - 0.2);

// PRINT_ANCHOR_BBOX at defaults:
//   X = W = 2 * 28                = 56
//   Y = H = 2 * 28                = 56
//   Z = z_front = 6.8 - 0.02 + 60 = 66.78
PRINT_ANCHOR_BBOX = [56, 56, 66.78];

// === Snaps ===
// Frame: X centered, Y = 0 at the bin's bottom edge (bottom on the
// wall as mounted), Z = 0 on the bed at the snap faces.

// One openGrid snap in its own frame (front/strong nub toward +X),
// welded into a single solid — verbatim from ego_lb6500_blower_mount
// (st-0of), where it's verified watertight + single-component for both
// snap depths. Each click-nub root gets a 0.3mm shim straddling the
// nub/core contact plane (local x=12.4); the 14mm-wide front nub's
// shim widens to 14.6, and the rear nub's sits 0.65 higher (its root
// rides above the base band in the directional variant).
module welded_directional_snap() {
    base   = snap_lite ? 0 : 3.4;
    root_z = max(0, base - 0.01);
    root_h = snap_lite ? 0.61 : 0.62;
    openGridSnap(lite = snap_lite, directional = true,
                 anchor = BOT, orient = UP, spin = 0);
    for (a = [90, 270])                       // side nubs
        zrot(a) translate([12.4, 0, root_z])
            cuboid([0.3, 11.6, root_h], anchor = BOT);
    translate([12.4, 0, root_z])              // front (strong) nub
        cuboid([0.3, 14.6, root_h], anchor = BOT);
    zrot(180) translate([12.4, 0, base + 0.64])  // rear (click) nub
        cuboid([0.3, 11.6, 0.62], anchor = BOT);
}

// One snap per tile: width_units cols x height_units rows on the 28mm
// pitch, centered per tile (1.6mm rim to the plate edge on every
// side). zrot(90) turns each snap's strong front nub toward +Y — up
// the wall (load rationale in the header).
module grid_snaps() {
    for (cx = [0 : width_units - 1], ry = [0 : height_units - 1])
        translate([(cx - (width_units - 1) / 2) * snap_pitch,
                   (ry + 0.5) * snap_pitch,
                   0])
            zrot(90) welded_directional_snap();
}

// === Back plate ===

// 45deg chamfer cuts along all four bottom edges of the plate. Four
// explicit triangular prisms rather than edge_profile(): they
// overshoot the ends and overlap at the corners, so the cuts stay
// transversal through the rounded plate corners, and they overshoot
// 2mm BELOW the plate bottom plane (st-n4v: a coplanar cut bottom is
// a degenerate boolean). Differenced from the plate body only —
// grid_snaps() is a sibling union — so the snaps cannot be clipped.
module plate_rim_chamfers() {
    c = plate_chamfer;
    // ±X edges: profile in XZ, extruded along Y.
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, H + ov, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = H + 2 * ov)
                        polygon([[W / 2 - c - ov, plate_z0 - ov],
                                 [W / 2 + ov, plate_z0 - ov],
                                 [W / 2 + ov, plate_z0 + c + ov]]);
    // ±Y ends: profile in YZ, extruded along X; the y=0 prism is built
    // directly and mirrored across y = H/2 for the top end.
    for (sy = [0, 1])
        translate([0, sy * H, 0])
            mirror([0, sy, 0])
                translate([-(W + 2 * ov) / 2, 0, 0])
                    rotate([90, 0, 90])
                        linear_extrude(height = W + 2 * ov)
                            polygon([[c + ov, plate_z0 - ov],
                                     [-ov, plate_z0 - ov],
                                     [-ov, plate_z0 + c + ov]]);
}

module plate() {
    difference() {
        translate([0, 0, plate_z0])
            linear_extrude(height = plate_t)
                rect([W, H], rounding = corner_r, anchor = FRONT);
        plate_rim_chamfers();
    }
}

// === Bin body ===
// One solid block (rounded vertical edges, buried into the plate)
// minus three cuts. The cavity cut alone carves the interior floor,
// the 45deg inner ramp face, the rear fillet diagonal, both side-wall
// inner faces, the open top, and the open front above the lip crest.

// Cavity profile in (Y, Z), extruded along X across the interior
// width. Overshoots (ov) past every face it opens: +Y past the top,
// +Z past the front, and BELOW the body's bottom plane at the back —
// the cut punches clear through the body web so the bin's interior
// back face is the plate's own top face. Stopping the cut exactly at
// plate_top would instead leave the web's top face coincident with
// the plate top (two coplanar boundary faces in the union, st-v7k
// class); overshooting past the body bottom is safe because the cut
// is differenced from the body only and the plate is a sibling.
module cavity() {
    zc = plate_top - bury - ov;  // below everything the body owns
    // At rear_fillet = 0 the fillet diagonal vanishes; emit the bare
    // corner drop instead — duplicate vertices would make a
    // degenerate polygon edge (opengrid_panel_aligner's axis_top
    // guard). The material left under the fillet toe (z between the
    // body bottom and plate_top) sits wholly inside the plate solid,
    // so it merges invisibly.
    fillet_pts = rf < 0.01
        ? [[floor_t, zc]]
        : [[floor_t, plate_top + rf], [floor_t + rf, plate_top],
           [floor_t + rf, zc]];
    pts = concat([
        [H + ov, zc],                       // up the plate face
        [H + ov, z_front + ov],             // over the top, out the front
        [floor_t + lip_e, z_front + ov],    // down the open front...
        [floor_t + lip_e, z_front],         // ...to the lip crest
        [floor_t, z_bend],                  // 45deg inner ramp face
    ], fillet_pts);                         // flat floor, then fillet
    translate([-(W / 2 - wall), 0, 0])
        rotate([90, 0, 90])
            linear_extrude(height = W - 2 * wall)
                polygon(pts);
}

// Front-bottom 45deg chamfer across the full width: the outer face of
// the lip ramp, and the matching trim on the side walls' front-bottom
// corners. The hypotenuse passes through (y=0, z=z_bend) and
// (y=lip_e, z=z_front).
module front_chamfer_cut() {
    translate([-(W / 2 + ov), 0, 0])
        rotate([90, 0, 90])
            linear_extrude(height = W + 2 * ov)
                polygon([[-ov, z_bend - ov],
                         [lip_e + ov, z_front + ov],
                         [-ov, z_front + ov]]);
}

// 45deg hand-feel chamfers along the front face's exposed outer rim:
// both side-wall edges (running the full Y extent) and the top edge
// (y=H). The y=0 edge needs none — front_chamfer_cut() already
// removed that corner. Prisms overshoot and overlap at corners so the
// cuts stay transversal through the rounded body corners.
module top_edge_chamfers() {
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, H + ov, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = H + 2 * ov)
                        polygon([[W / 2 - top_ch, z_front],
                                 [W / 2 + ov, z_front - top_ch - ov],
                                 [W / 2 + ov, z_front + ov],
                                 [W / 2 - top_ch, z_front + ov]]);
    translate([-(W + 2 * ov) / 2, H, 0])
        rotate([90, 0, 90])
            linear_extrude(height = W + 2 * ov)
                polygon([[-top_ch, z_front],
                         [ov, z_front - top_ch - ov],
                         [ov, z_front + ov],
                         [-top_ch, z_front + ov]]);
}

module body() {
    difference() {
        translate([0, 0, plate_top - bury])
            linear_extrude(height = z_front - (plate_top - bury))
                rect([W, H], rounding = corner_r, anchor = FRONT);
        cavity();
        front_chamfer_cut();
        top_edge_chamfers();
    }
}

// === Assembly ===

grid_snaps();
plate();
body();
