// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Ego LB6500 leaf-blower wall mount, converted from screw-mount to a
// wall-grid system. Imports an operator-supplied STL (two triangular
// bracket arms on a 138.5 x 93.5 mm base plate), fills its six
// countersunk screw holes with plugs, and fuses wall-mount geometry
// onto the original build-plate face: a Multiconnect slot backer
// (default) or a grid of openGrid snaps, selected by mount_type.
//
// First import()-based model in this repo. The mesh is referenced
// relative to this file (models/ego_lb6500_blower_mount.stl, committed
// alongside); the browser pipeline mounts it at the FS root next to
// the entry file, so the bare filename resolves in both native and
// WASM renders.
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
// The imported mesh's back plate was its build-plate face (Z=0); the
// whole mesh is lifted by the back-mount thickness so the finished
// part still prints flat: first layers are the slot face (or the
// openGrid snap faces — the orientation the snap was designed to
// print in), then the filled plate, then the arms.
//
// === Wall-hang orientation / load direction (st-0of) ===
//
// Operator-verified physics: the Y+ face is the BEARING face — the
// blower rests on the arm surfaces facing +Y — so the live load
// points -Y and the y=0 edge points DOWN on the wall. (The original
// st-f43 backer inferred the opposite from the saddle-hook shape and
// was 180 deg off.) Consequences:
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
// === Screw-hole fill (measured from the mesh) ===
//
// Six countersunk holes, mirror-symmetric about X=69.25, in the
// 15 mm-thick back plate (mesh frame): bore d=5.10 tilted 12° outward
// in X, entries at Z=0 (11.19,12) (11.19,77) (19.19,44.5) + mirrored;
// countersink cone from Z≈11.3 into a d=9.52 counterbore exiting the
// plate top flush at Z=15.0. Each hole is filled by two oversized
// plugs (union, not re-cut): a tilted bore plug that also welds the
// backer to the plate through the hole, and a vertical countersink
// plug capped exactly flush with the plate top so no rim or bump
// remains. The big 68.5 x 29 mm central obround is a functional
// cutout, not a screw hole — it stays.

include <BOSL2/std.scad>
// `use` not `include`: keeps the libraries' top-level demo/customizer
// statements out of the render.
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

mount_type = "multiconnect"; // @param enum choices=multiconnect|opengrid group=mount label="Wall mount type" filename
fill_screw_holes = true; // @param boolean group=plate label="Fill original screw holes"
backer_thickness = 6.5;  // @param number min=5.5 max=8 step=0.5 unit=mm group=mount label="Multiconnect backer thickness"
slot_dimples     = true; // @param boolean group=mount label="Multiconnect slot dimples (click retention)"
snap_lite        = false; // @param boolean group=mount label="Lite openGrid snaps (3.4mm instead of 6.8mm)"

// === Fixed geometry (matches the imported mesh — not tunable) ===

plate_w      = 138.5; // mesh X extent
plate_face_d = 89;    // Y extent of the flat build face — the arm
                      // saddle hooks overhang to y=93.5 higher up, but
                      // the plate itself (and so the backer) ends at 89
mesh_h       = 160;   // mesh Z extent
plate_t      = 15;    // back plate thickness in the mesh

// Multiconnect
slot_spacing    = 25;   // Multiconnect standard pitch
top_band        = 5;    // solid band capping the slot dome ends (y=84..89)
weld            = 0.45; // backer sink into the plate. 0.45 (not a hair)
                        // because the build face has two ~0.4 mm-deep
                        // logo recesses at (14..19, 53..61) + mirror; a
                        // shallower weld seals them into enclosed voids
                        // that break the single-solid topology claim

// openGrid (mount_type = "opengrid")
snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
og_weld    = 0.02;  // embed of snap tops into the plate face (st-vmn).
                    // Deliberately shallow — sinking deeper would offset
                    // the click nubs from the grid's groove plane. The
                    // logo recesses stay VENTED here (snap pads only
                    // partially cover them; recess slivers at x<14.85
                    // and y 56.9..60.1 open to air), so the shallow
                    // weld cannot create enclosed voids.

// Snap grid auto-fit over the flat plate face (138.5 x 89): as many
// snaps as fit at 28 mm pitch keeping >= 1 mm rim, always centered —
// minus any snap whose footprint intersects the central 68.5 x 29
// obround (the original bracket's functional pass-through): the two
// middle snaps float entirely inside the cutout with nothing to weld
// to, and the flanking pair would seal two ~0.5 mm-deep recesses in
// the build face at (19.3..21.8, 42..47) + mirror into enclosed void
// shells. Net: a 4 x 3 grid minus the middle row = 8 full-depth snaps
// at defaults, on the top and bottom rows where the load actually
// goes (pull-out up top, compression at the bottom).
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

// Lift of the imported mesh above the bed = thickness of whichever
// back-mount is selected (its top welds into the plate build face).
body_lift = mount_type == "opengrid" ? snap_h - og_weld
                                     : backer_thickness;

// Screw holes (mesh frame, Z from the plate's original build face)
hole_tilt       = 12;     // bore lean, degrees outward in X
bore_d          = 5.1;    // measured bore diameter
cbore_d         = 9.52;   // measured counterbore diameter
cs_top_z        = 15.0;   // counterbore exits flush at the plate top
cs_bottom_z     = 11.0;   // vertical plug starts below the cone start (11.3)
plug_margin     = 0.75;   // radial oversize so plugs swallow the hole rims
// Bore entries at Z=0 and measured counterbore centers; x mirrors as
// plate_w - x for the right-hand trio.
bore_entries    = [[11.19, 12], [11.19, 77], [19.19, 44.5]];
cbore_centers   = [[7.95, 12], [7.95, 77], [15.95, 44.5]];

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at defaults
// (mount_type = "multiconnect").
// X: plate_w = 138.5 (backer matches the plate footprint)
// Y: plate_d = 93.5
// Z: backer_thickness (6.5) + mesh_h (160) = 166.5
// (opengrid variant: Z = snap_h - og_weld + 160 = 166.78 at full depth)
PRINT_ANCHOR_BBOX = [138.5, 93.5, 166.5];

// === Geometry ===

// Everything below is a root-level sibling: multiconnectGenerator uses
// BOSL2 diff() tags internally and is known to break inside an outer
// explicit union() (see models/cylindrical_holder_slot.scad). Root
// siblings implicitly union into one solid at render time. The
// mount_type if() blocks are plain group nodes, not explicit union()
// calls — the generator's slot cuts survive them (verified by the
// slot-channel probes in the invariants sidecar).

// The import path must stay a literal string: the browser pipeline's
// closure walker regex-scans the entry source for import("...") to
// know which binary assets to mount (lib/wasm/closure.ts).
module blower_body() {
    translate([0, 0, body_lift])
        import("ego_lb6500_blower_mount.stl", convexity = 10);
}

// One screw-hole fill: a tilted bore plug reaching from the plate's
// back face up through the bore, plus a vertical plug swallowing the
// countersink cone + counterbore, its top exactly flush with the
// plate top so the filled surface is clean.
// For multiconnect the bore plug starts 2 mm inside the backer,
// welding backer to plate through the hole; for opengrid there is no
// panel behind the holes, so it starts flush with the back face (the
// same proven-manifold coplanar-cap trick as the plug tops).
plug_sink = mount_type == "multiconnect" ? 2 : 0;

module screw_plug(entry, cbore, lean) {
    translate([entry.x, entry.y, body_lift])
        rotate([0, lean, 0])
            translate([0, 0, -plug_sink])
                cylinder(d = bore_d + 2 * plug_margin, h = 12.5 + plug_sink);
    // Countersink + counterbore: vertical, flush top.
    translate([cbore.x, cbore.y, body_lift + cs_bottom_z])
        cylinder(d = cbore_d + 2 * plug_margin, h = cs_top_z - cs_bottom_z);
}

module screw_plugs() {
    for (i = [0 : len(bore_entries) - 1]) {
        e = bore_entries[i];
        c = cbore_centers[i];
        screw_plug(e, c, -hole_tilt);                                // left trio leans -X
        screw_plug([plate_w - e.x, e.y], [plate_w - c.x, c.y], hole_tilt); // right trio mirrored
    }
}

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

blower_body();
if (fill_screw_holes) screw_plugs();
if (mount_type == "multiconnect") {
    backer_panel();
    dome_band();
} else {
    grid_snaps();
}
