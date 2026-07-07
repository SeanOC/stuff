// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Ego LB6500 leaf-blower wall mount — NATIVE parametric remodel of the
// operator-supplied bracket (st-82o). The original import()-based
// version unioned a 13,596-triangle mesh through Manifold on every
// render (~23s in the wasm export path — enough to blow the serverless
// gateway timeout on cold starts) and was the sole consumer of the
// binary-asset pipeline. This file rebuilds the bracket from
// primitives measured off that mesh; the mesh itself stays in-repo
// (models/ego_lb6500_blower_mount.stl) purely as the fidelity
// reference for the invariants sidecar — it is never import()ed.
//
// What is preserved EXACTLY (operator constraint, 2026-07-06): the
// BEARING SURFACES — every +Y-facing face the blower can touch from
// above. The sidecar raycasts both models on a 1.5mm grid and fails
// if any bearing height deviates >1mm from the reference. What is
// approximated: the organic bulk (the arms' triangular windows are
// filled solid, fillets and logo recesses dropped, stair-stepped rib
// edges straightened). The six countersunk screw holes of the
// original are simply not modeled — the plate is solid, which retires
// the old fill_screw_holes plug machinery.
//
// LICENSING: both back-mount systems come from QuackWorks — the
// Multiconnect backer (Modules/multiconnectSlotDesignBOSL.scad) and
// the openGrid snap (openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic) — licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived mount is for personal use only; do not
// sell prints or files.
//
// === Coordinate frame / print orientation ===
//
// Bracket frame (matches the reference mesh): z=0 is the wall/back
// face, x spans the 138.5mm width, y is height on the wall. The whole
// bracket is lifted by the back-mount thickness so the finished part
// prints flat: first layers are the slot face (or the openGrid snap
// faces), then the plate, then the arms rising 160mm.
//
// === Wall-hang orientation / load direction (st-0of) ===
//
// Operator-verified physics: the Y+ face is the BEARING face — the
// blower rests on the arm surfaces facing +Y — so the live load
// points -Y and the y=0 edge points DOWN on the wall. Consequences:
//
//  - Multiconnect: the slots' closed dome ends (where connectors rest
//    under load) point toward high y (UP on the wall), a 5 mm solid
//    band above them caps the dome openings at the y=89 plate edge,
//    and the entry mouths open through the y=0 edge — the part slides
//    DOWN onto wall connectors and the load seats it into the domes.
//  - openGrid: directional snaps, strong front nub (the one marked by
//    the indicator, non-flexing, 0.8 mm deep vs 0.4) pointing +Y (UP),
//    so the lever-out moment the cantilevered blower puts on the top
//    snap row bears on the rigid hook; the flexy click-in side faces
//    DOWN where the moment presses the plate into the wall.
//
// === Bracket anatomy (all coords: left arm; right arm mirrors
//     about x=69.25) ===
//
// Plate: 138.5 x 89 x 15, edge-notched top and bottom between
// x=35..103.5 (15 deep) with the original's central 68.5 x 29 obround
// pass-through — both kept because the blower shell may nest into
// them and the openGrid snap layout logic depends on them.
//
// Each arm, measured off the reference mesh:
//  - WEB: solid gusset x=24..35. Top beam edge at y=89.0 runs the
//    full z=15..160 depth — the primary bearing line. The original's
//    triangular lightening window is filled (bulk, not bearing).
//  - HORN: retention bump at the far end, plateau z=110..160. Ridge
//    peaks at y=93.50, x=25.36 (exact mesh vertices), tapering
//    linearly to a thin blade at x~15.2 (y=81.2, slope 1.437/mm —
//    matches the mesh raycast within 0.1mm) and to y=89.0 at x=35.
//    Built as pairwise hull()s of thin convex Y-Z profile plates at
//    measured x stations; interp error vs the mesh is <=0.6mm.
//  - SHELF: second bearing rib, top at y=64.80, y-extent 56.4..64.8,
//    from x=10.9 to the web. Far edge is a straight chord standing in
//    for the mesh's 8mm stair-stepped edge (z = 5.61x - 46.6).
//  - LOWER BAR: guide rib, top at y=30.8, y-extent 23.2..30.8. Only
//    x<11 is exposed (the rest sits under the shelf).
//  - FLARE: small beam-root wedge where the web front face blends
//    into the plate (x 19.4..24 at z<20.4, top at y=89).

include <BOSL2/std.scad>
// `use` not `include`: keeps the libraries' top-level demo/customizer
// statements out of the render.
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

mount_type = "multiconnect"; // @param enum choices=multiconnect|opengrid group=mount label="Wall mount type" filename
backer_thickness = 6.5;  // @param number min=5.5 max=8 step=0.5 unit=mm group=mount label="Multiconnect backer thickness"
slot_dimples     = true; // @param boolean group=mount label="Multiconnect slot dimples (click retention)"
snap_lite        = false; // @param boolean group=mount label="Lite openGrid snaps (3.4mm instead of 6.8mm)"

// === Fixed geometry (matches the reference mesh — not tunable) ===

plate_w      = 138.5; // bracket X extent
plate_face_d = 89;    // Y extent of the flat build face — the arm
                      // horns overhang to y=93.5 higher up, but the
                      // plate itself (and so the backer) ends at 89
mesh_h       = 160;   // bracket Z extent (depth out from the wall)
plate_t      = 15;    // back plate thickness

// Multiconnect
slot_spacing    = 25;   // Multiconnect standard pitch
top_band        = 5;    // solid band capping the slot dome ends (y=84..89)
weld            = 0.45; // backer sink into the plate (proven-manifold
                        // overlap; the plate face is flat now, but a
                        // real overlap keeps the union robust)

// openGrid (mount_type = "opengrid")
snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
og_weld    = 0.02;  // embed of snap tops into the plate face (st-vmn).
                    // Deliberately shallow — sinking deeper would offset
                    // the click nubs from the grid's groove plane.

// The plate build face is NOT a full 138.5 x 89 rectangle: its bottom
// and top edges are notched between x=35..103.5 (y 0..15 and y 74..89
// are open through the edges), leaving two horizontal stringers
// (y 15..30 and 59..74, bounded by the central obround) plus
// full-height side columns. The snap rows sit half on the stringers
// and half over the notches, so without extra material ~11 mm of each
// snap's footprint hangs in air (st-ocs). A backing band per snap row
// fills the notch behind the snaps: bottom face flush with the plate
// build face (same 0.02 snap-top weld as the plate), overlapping
// og_overlap into the stringer and side columns for weld, extending
// og_lip past the snap edge so no snap edge overhangs. Prints
// snaps-down support-free: the band sits on the snap tops (3.2 mm
// bridges across the inter-snap gaps, a 0.4 mm lip at the free edge).
notch_x0    = 35;    // notch x extent (measured off the mesh)
notch_x1    = 103.5;
notch_d     = 15;    // notch depth in y from each plate edge
og_backer_t = 6;     // backing band thickness behind the snaps
og_overlap  = 2;     // band weld overlap into stringer/columns
og_lip      = 0.4;   // band margin past the snap edge (free edge)

// Snap grid auto-fit over the flat plate face (138.5 x 89): as many
// snaps as fit at 28 mm pitch keeping >= 1 mm rim, always centered —
// minus any snap whose footprint intersects the central 68.5 x 29
// obround (the original bracket's functional pass-through): the two
// middle snaps would float entirely inside the cutout with nothing to
// weld to. Net: a 4 x 3 grid minus the middle row = 8 full-depth
// snaps at defaults, on the top and bottom rows where the load
// actually goes (pull-out up top, compression at the bottom).
snap_cols = max(1, floor((plate_w - 2 - snap_w) / snap_pitch) + 1);
snap_rows = max(1, floor((plate_face_d - 2 - snap_w) / snap_pitch) + 1);
obround_w = 68.5;  // central obround cutout, centered on the plate face
obround_h = 29;
snap_centers = [
    for (cx = [0 : snap_cols - 1], ry = [0 : snap_rows - 1])
        let (px = plate_w / 2 + (cx - (snap_cols - 1) / 2) * snap_pitch,
             py = plate_face_d / 2 + (ry - (snap_rows - 1) / 2) * snap_pitch)
        if (abs(px - plate_w / 2) >= (obround_w + snap_w) / 2 ||
            abs(py - plate_face_d / 2) >= (obround_h + snap_w) / 2)
            [px, py]
];
assert(mount_type != "opengrid" || len(snap_centers) >= 2,
       "fewer than 2 openGrid snaps fit the plate face");

// Row centers that actually carry snaps (the middle row is skipped by
// the obround filter above) — each gets a backing band where its snap
// footprints reach into an edge notch.
snap_row_ys = [
    for (ry = [0 : snap_rows - 1])
        let (py = plate_face_d / 2 + (ry - (snap_rows - 1) / 2) * snap_pitch)
        if (len([for (c = snap_centers) if (abs(c.y - py) < 0.01) 1]) > 0)
            py
];

// Lift of the bracket above the bed = thickness of whichever
// back-mount is selected (its top welds into the plate build face).
body_lift = mount_type == "opengrid" ? snap_h - og_weld
                                     : backer_thickness;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at defaults
// (mount_type = "multiconnect").
// X: plate_w = 138.5 (backer matches the plate footprint)
// Y: horn ridge = 93.5
// Z: backer_thickness (6.5) + mesh_h (160) = 166.5
// (opengrid variant: Z = snap_h - og_weld + 160 = 166.78 at full depth)
PRINT_ANCHOR_BBOX = [138.5, 93.5, 166.5];

// === Native bracket geometry (st-82o) ===

// Prism from a Y-Z profile polygon (points as [y, z]) extruded across
// x0..x1. rotate([90,0,90]) maps the polygon's local x to model y,
// local y to model z, and the extrusion to model +x.
module yz_prism(x0, x1, pts) {
    translate([x0, 0, 0])
        rotate([90, 0, 90])
            linear_extrude(x1 - x0)
                polygon(pts);
}

// Prism from a plan-view polygon (points as [x, z]) extruded across
// y0..y1 — a vertical-in-y slab. rotate([90,0,0]) maps local y to
// model z and the extrusion to model -y (hence the y1 translate).
module xz_prism(y0, y1, pts) {
    translate([0, y1, 0])
        rotate([90, 0, 0])
            linear_extrude(y1 - y0)
                polygon(pts);
}

// Back plate: 138.5 x 89 x 15 with the original's edge notches and
// central obround pass-through. Solid otherwise — no screw holes.
module bracket_plate() {
    linear_extrude(plate_t)
        difference() {
            square([plate_w, plate_face_d]);
            translate([notch_x0, -0.1])
                square([notch_x1 - notch_x0, notch_d + 0.1]);
            translate([notch_x0, plate_face_d - notch_d])
                square([notch_x1 - notch_x0, notch_d + 0.1]);
            // obround: rectangle + end semicircles, centered on the face
            translate([plate_w / 2, plate_face_d / 2])
                hull() {
                    translate([-(obround_w - obround_h) / 2, 0]) circle(d = obround_h);
                    translate([(obround_w - obround_h) / 2, 0]) circle(d = obround_h);
                }
        }
}

// Horn stations: [x, convex Y-Z profile] measured off the reference
// mesh (see header). Adjacent stations are hull()ed pairwise, giving
// a linear loft; profiles must stay CONVEX or hull() would bridge
// their concavities.
horn_stations = [
    [15.2,  [[80.9, 109],   [81.2, 160],   [79.4, 160], [79.4, 111]]],
    [17.5,  [[82.9, 102],   [84.8, 112],   [84.8, 160], [78.2, 160]]],
    [19.5,  [[84.5, 98],    [87.7, 112],   [87.7, 160], [77.2, 160]]],
    [21.5,  [[86.4, 93],    [90.6, 112],   [90.6, 160], [76.2, 160]]],
    [23.5,  [[88.6, 91.5],  [93.0, 110],   [93.0, 160], [74.8, 160]]],
    [25.36, [[87.5, 92],    [93.13, 106.11], [93.5, 110], [93.5, 160], [74.0, 160]]],
    [29.5,  [[87.8, 92.5],  [91.15, 112],  [91.15, 160], [74.0, 160]]],
    [35.0,  [[87.9, 92.5],  [89.0, 110],   [89.0, 160],  [74.0, 160]]],
];

module horn() {
    for (i = [0 : len(horn_stations) - 2])
        hull() {
            yz_prism(horn_stations[i][0], horn_stations[i][0] + 0.1,
                     horn_stations[i][1]);
            yz_prism(horn_stations[i + 1][0], horn_stations[i + 1][0] + 0.1,
                     horn_stations[i + 1][1]);
        }
}

// One arm (left-side coordinates). All members start at z=14.5 —
// 0.5mm inside the plate — so every union overlap is a real volume.
module arm() {
    // Web: solid gusset, beam top at y=89 the full depth, underside
    // diagonal from the plate root to the beam bottom at the tip.
    yz_prism(24, 35, [[9, 14.5], [89, 14.5], [89, 160], [75, 160]]);
    horn();
    // Shelf rib, bearing top at y=64.8. Plan: tip, front edge, flare
    // clip, then the far-edge chord back to the tip.
    xz_prism(56.4, 64.8,
             [[10.9, 14.5], [21.4, 14.5], [22.4, 24.5],
              [24.6, 26.5], [24.6, 91.4]]);
    // Lower guide rib, top at y=30.8.
    xz_prism(23.2, 30.8,
             [[6.8, 14.5], [18, 14.5], [24.6, 31.5], [24.6, 39.9]]);
    // Beam-root flare wedge (web front face blending into the plate).
    xz_prism(56.4, 89, [[19.4, 14.5], [24.5, 14.5], [24.5, 20.4]]);
}

module blower_body() {
    translate([0, 0, body_lift]) {
        bracket_plate();
        arm();
        translate([plate_w, 0, 0]) mirror([1, 0, 0]) arm();
    }
}

// === Back-mount geometry ===
//
// Everything below is a root-level sibling: multiconnectGenerator uses
// BOSL2 diff() tags internally and is known to break inside an outer
// explicit union() (see models/cylindrical_holder_slot.scad). Root
// siblings implicitly union into one solid at render time. The
// mount_type if() blocks are plain group nodes, not explicit union()
// calls — the generator's slot cuts survive them (verified by the
// slot-channel probes in the invariants sidecar).

// Multiconnect backer under the plate face. Generator native frame:
// width along X, height along Z (dome ends at +Z), slot channels
// recessed into the -Y face. rotate([90,0,180]) lays it flat with the
// dome ends toward +Y (the up-when-hung edge — see the load-direction
// header) and the slot openings still facing -Z (the build plate /
// wall face); the entry mouths open through the y=0 down edge. Panel
// is thickened by `weld` so its top sinks into the plate instead of
// merely touching it.
backer_h = plate_face_d - top_band; // slot region height (dome edge at y=backer_h)

module backer_panel() {
    translate([plate_w / 2, backer_h / 2, (backer_thickness + weld) / 2])
        rotate([90, 0, 180])
            multiconnectGenerator(
                width = plate_w,
                height = backer_h,
                multiconnectPartType = "Backer",
                distanceBetweenSlots = slot_spacing,
                backerThickness = backer_thickness + weld,
                slotOrientation = "Vertical",
                slotDimple = slot_dimples
            );
}

// Solid strip over the slot dome ends (they breach the panel's dome
// edge — same fix as cylindrical_holder_slot's top_band). Sits at the
// TOP edge of the plate face (y=84..89) now that the domes point up.
module dome_band() {
    translate([0, backer_h - 0.01, 0])
        cube([plate_w, top_band + 0.01, backer_thickness + weld]);
}

// One openGrid snap in its own frame (front/strong nub toward +X),
// welded into a single solid. openGridSnap models its click nubs as
// face-touching (zero overlap) solids whose roots kiss the core along
// bare tangent lines — detached shells under Manifold, non-2-manifold
// edges under CGAL (the st-v7k class; see led_remote_holder_51x84mm
// for the full story). Each nub root gets a 0.3 mm shim straddling the
// nub/core contact plane (local x=12.4): sides and front at the base
// band, the rear nub 0.65 higher (its root sits at base+0.65 in the
// directional variant). The front nub is 14 mm wide (vs 11/10.8), so
// its shim widens to 14.6; shim widths overshoot each nub by 0.3 so
// the root seam is swallowed across the nub's full width. Verified
// watertight + single-component for both snap depths (st-0of).
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

// Snap grid centered on the flat plate face (obround-clearing centers
// precomputed above), zrot(90) turning each snap's strong front nub
// toward +Y (up on the wall — load direction rationale in the header).
module grid_snaps() {
    for (c = snap_centers)
        translate([c.x, c.y, 0])
            zrot(90) welded_directional_snap();
}

// Backing bands filling the edge notches behind the snap rows so every
// snap is fully backed (st-ocs — see the notch constants above). One
// cuboid per row/notch pair: x spans the notch plus og_overlap into
// the side columns; y from og_lip past the snap's free edge to
// og_overlap past the notch's inner wall (into the stringer); z from
// the plate build face plane up og_backer_t (snap tops keep their
// 0.02 weld embed, now into band as well as plate).
module snap_backer_bands() {
    bx = notch_x0 - og_overlap;
    bw = notch_x1 - notch_x0 + 2 * og_overlap;
    for (py = snap_row_ys) {
        y_lo = py - snap_w / 2;  // snap footprint edges at this row
        y_hi = py + snap_w / 2;
        if (y_lo < notch_d)      // row reaches into the bottom-edge notch
            translate([bx, y_lo - og_lip, body_lift])
                cube([bw, notch_d + og_overlap - y_lo + og_lip, og_backer_t]);
        if (y_hi > plate_face_d - notch_d)  // ... the top-edge notch
            translate([bx, plate_face_d - notch_d - og_overlap, body_lift])
                cube([bw, y_hi + og_lip - (plate_face_d - notch_d - og_overlap),
                      og_backer_t]);
    }
}

blower_body();
if (mount_type == "multiconnect") {
    backer_panel();
    dome_band();
} else {
    grid_snaps();
    snap_backer_bands();
}
