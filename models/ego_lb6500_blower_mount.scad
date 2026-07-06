// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Ego LB6500 leaf-blower wall mount, converted from screw-mount to
// Multiconnect. Imports an operator-supplied STL (two triangular
// bracket arms on a 138.5 x 93.5 mm base plate), fills its six
// countersunk screw holes with plugs, and fuses a Multiconnect backer
// onto the original build-plate face so the mount clips to a
// Multiboard wall instead of being screwed to a stud.
//
// First import()-based model in this repo. The mesh is referenced
// relative to this file (models/ego_lb6500_blower_mount.stl, committed
// alongside); the browser pipeline mounts it at the FS root next to
// the entry file, so the bare filename resolves in both native and
// WASM renders.
//
// LICENSING: the Multiconnect backer comes from QuackWorks
// (libs/QuackWorks/Modules/multiconnectSlotDesignBOSL.scad), licensed
// CC BY-NC-SA 4.0 — NON-COMMERCIAL. This derived mount is for
// personal use only; do not sell prints or files.
//
// === Coordinate frame / print orientation ===
//
// The imported mesh's back plate was its build-plate face (Z=0); the
// whole mesh is lifted by backer_thickness so the finished part still
// prints flat: first layers are the backer's slot face, then the
// filled plate, then the arms. Slot channels print face-down (the
// standard orientation for a backer fused to an object's back).
//
// Wall-hang orientation: the bracket arms' saddle hooks open toward
// -Y+Z, so the y=0 edge points UP on the wall. The slots' closed dome
// ends (where connectors rest under load) therefore point toward y=0,
// a 5 mm solid band above them caps the dome openings, and the slot
// entry mouths open through the y=93.5 edge — the part slides DOWN
// onto wall connectors.
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
// `use` not `include`: keeps the library's top-level demo/customizer
// statements out of the render.
use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>

$fn = 64;

// === User-tunable parameters ===

fill_screw_holes = true; // @param boolean group=plate label="Fill original screw holes"
backer_thickness = 6.5;  // @param number min=5.5 max=8 step=0.5 unit=mm group=mount label="Backer thickness"
slot_dimples     = true; // @param boolean group=mount label="Slot dimples (click retention)"

// === Fixed geometry (matches the imported mesh — not tunable) ===

plate_w      = 138.5; // mesh X extent
plate_face_d = 89;    // Y extent of the flat build face — the arm
                      // saddle hooks overhang to y=93.5 higher up, but
                      // the plate itself (and so the backer) ends at 89
mesh_h       = 160;   // mesh Z extent
plate_t      = 15;    // back plate thickness in the mesh

// Multiconnect
slot_spacing    = 25;   // Multiconnect standard pitch
top_band        = 5;    // solid band capping the slot dome ends (y=0..5)
weld            = 0.45; // backer sink into the plate. 0.45 (not a hair)
                        // because the build face has two ~0.4 mm-deep
                        // logo recesses at (14..19, 53..61) + mirror; a
                        // shallower weld seals them into enclosed voids
                        // that break the single-solid topology claim

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

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at defaults.
// X: plate_w = 138.5 (backer matches the plate footprint)
// Y: plate_d = 93.5
// Z: backer_thickness (6.5) + mesh_h (160) = 166.5
PRINT_ANCHOR_BBOX = [138.5, 93.5, 166.5];

// === Geometry ===

// Everything below is a root-level sibling: multiconnectGenerator uses
// BOSL2 diff() tags internally and is known to break inside an outer
// explicit union() (see models/cylindrical_holder_slot.scad). Root
// siblings implicitly union into one solid at render time.

// The import path must stay a literal string: the browser pipeline's
// closure walker regex-scans the entry source for import("...") to
// know which binary assets to mount (lib/wasm/closure.ts).
module blower_body() {
    translate([0, 0, backer_thickness])
        import("ego_lb6500_blower_mount.stl", convexity = 10);
}

// One screw-hole fill: a tilted bore plug reaching from inside the
// backer up through the bore, plus a vertical plug swallowing the
// countersink cone + counterbore, its top exactly flush with the
// plate top so the filled surface is clean.
module screw_plug(entry, cbore, lean) {
    // Bore: tilted cylinder along the measured hole axis. Starts 2 mm
    // inside the backer (welding backer to plate through the hole) and
    // ends inside the countersink plug's region.
    translate([entry.x, entry.y, backer_thickness])
        rotate([0, lean, 0])
            translate([0, 0, -2])
                cylinder(d = bore_d + 2 * plug_margin, h = 14.5);
    // Countersink + counterbore: vertical, flush top.
    translate([cbore.x, cbore.y, backer_thickness + cs_bottom_z])
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
// recessed into the -Y face. rotate([90,0,0]) lays it flat: dome ends
// toward -Y (the up-when-hung edge), slot openings facing -Z (the
// build plate / wall face). Panel is thickened by `weld` so its top
// sinks into the plate instead of merely touching it.
backer_h = plate_face_d - top_band; // slot region height (dome edge at y=top_band)

module backer_panel() {
    translate([plate_w / 2, top_band + backer_h / 2, (backer_thickness + weld) / 2])
        rotate([90, 0, 0])
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
// edge — same fix as cylindrical_holder_slot's top_band).
module dome_band() {
    cube([plate_w, top_band + 0.01, backer_thickness + weld]);
}

blower_body();
if (fill_screw_holes) screw_plugs();
backer_panel();
dome_band();
