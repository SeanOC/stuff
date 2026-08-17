// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// openGrid-to-Multiconnect wall adapter — clicks into an openGrid tile
// on the back and presents a Multiconnect (Multiboard) receiver slot on
// the front, so any Multiconnect-tabbed accessory hangs on an openGrid
// wall (pst-9xgx). Direction is fixed: the ITEMS are Multiconnect, the
// SUBSTRATE is openGrid — this is NOT an openGrid accessory on a
// Multiboard wall (that reverse part is the mount_type=multiconnect
// backer on opengrid_bin / the led_remote_holder twins). The `size`
// enum fans the export grid into one STL per width: a single-tile part
// with one slot, and a two-tile part with two slots.
//
// LICENSING: the back snap is QuackWorks' openGridSnap()
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic); the front receiver is QuackWorks'
// multiconnectBack() (libs/QuackWorks/Modules/multiconnectSlotDesign.scad,
// Multiconnect by Andy Levesque, credit David D; Multiboard by Keep
// Making). Both are CC BY-NC-SA 4.0 AND the Multiboard License —
// NON-COMMERCIAL, attribution, share-alike. This derived part is for
// personal use only; do not sell prints or files.
//
// === Pitch mismatch: openGrid 28mm vs Multiconnect 25mm ===
//
// The two ecosystems are on different pitches and the adapter does NOT
// try to reconcile them — it carries each face on its own native grid,
// independently centered on the shared plate:
//
//  - Back: one openGridSnap per 28mm tile (single = 1 tile / 28mm wide,
//    double = 2 tiles / 56mm wide), so the snaps land dead-center in
//    real openGrid holes.
//  - Front: multiconnectBack() lays its slots on the standard 25mm
//    Multiconnect pitch (single = 1 slot, double = 2 slots at 25mm),
//    centered on the same plate.
//
// The snaps (28mm apart) and slots (25mm apart) therefore do NOT line
// up in X — they don't need to, they engage opposite faces. The plate
// is sized in whole openGrid tiles so the mounted part aligns to the
// wall; the slots ride wherever multiconnectBack centers them.
//
// === Print orientation (native): ZERO supports ===
//
// Prints snaps-down: the 24.8mm openGridSnap faces are the first layers
// at z=0, exactly as the wall-mount siblings print (opengrid_bin,
// ego_lb6500_blower_mount). The four flex slots the click nubs need are
// cut through to the bed, so nothing is added under the snaps.
//
// The Multiconnect receiver sits on top (front face, +Z up on the bed)
// with its slot mouths opening UPWARD. That is printable support-free:
// the dovetail slot is widest at the mouth and tapers in at 45deg going
// down toward the plate (a valley, not an undercut), and the slot's long
// axis runs horizontally across the bed (world +Y, up the wall as
// mounted). The retention dome caps the top (+Y) end. Every body
// overhang is <=45deg; the 3.2mm channels between double-variant snaps
// stay clear.
//
// === Wall-hang orientation / load direction ===
//
// Mounted, +Y points UP the wall. The openGridSnap's strong front nub
// (non-flexing, 0.8mm vs 0.4) faces +Y so the accessory's cantilever
// lever-out bears on the rigid hook while the flexy click side faces
// down (st-0of, same rule as ego_lb6500_blower_mount / opengrid_bin).
//
// The Multiconnect receiver's retention dome points DOWN (-Y) — the
// OPPOSITE of the sibling parts, and deliberately so. Those parts are
// accessories: their slotted back slides DOWN onto fixed wall connectors,
// so their dome is UP and the accessory's own weight rides its slot up
// onto the connector, seating into the top dome. This adapter is the
// wall-FIXED half instead, and it carries the slot, not the connector.
// A hung accessory's male tab drops into the slot from the top mouth
// (+Y) and gravity pulls it DOWN to a hard stop at the closed dome at
// the bottom (-Y) — weight seats the tab, exactly as a load-bearing
// hang should. A dome-up receiver here would let the tab slide straight
// back out the bottom under load (only the v2 detent resisting), so the
// role inversion forces the dome flip. One tile tall carries one snap
// row; the pull-out moment is taken by the rigid front nub (st-0of).
//
// === Mesh-robustness notes ===
//
// The openGridSnap click nubs are face-touching solids whose roots kiss
// the core along bare tangent lines — detached shells under Manifold,
// non-2-manifold edges under CGAL (the st-v7k class). Each nub root
// carries a 0.3mm shim that volumetrically fuses it to the core. The
// snap wrapper is kept textually identical to the siblings
// (opengrid_snaps, opengrid_bin) — the browser render pipeline only
// resolves vendored libs/, so there is no shared project-side module:
// fix a bug here, apply it to them. The receiver is QuackWorks'
// BOSL2-free master slot back (a plain difference(), no BOSL2 diff()
// tags), so it is safe as a root-level sibling — unlike the BOSL2
// generator that silently loses its slot cuts inside an outer union().
// The receiver welds bury=0.6mm into the plate; snaps weld 0.02mm — no
// face-kissing unions anywhere.

include <BOSL2/std.scad>
// `use` not `include`: both vendored files end with top-level demo
// geometry (a stray snap / a full slot back) that would otherwise inject
// solids into every render. `use` pulls in the module definitions only.
use <QuackWorks/openGrid/opengrid-snap.scad>
use <QuackWorks/Modules/multiconnectSlotDesign.scad>

$fn = 64;

// === User-tunable parameters ===

// The two shipped widths, one exported STL each (the 'filename' flag
// fans the export grid over the enum). single = 1 openGrid tile / 1
// Multiconnect slot; double = 2 tiles / 2 slots. Start with single;
// double only earns its place because both grids stay clean at 2-wide.
size = "single"; // @param enum choices=single|double group=size label="Adapter width" filename

// Back-snap flavor. directional (default) is the load-bearing choice —
// one rigid front hook takes the cantilever lever-out (strong nub up the
// wall). bidirectional carries four identical click nubs; use it where
// the adapter clicks in and pulls straight out with no hung load.
snap_type = "directional"; // @param enum choices=directional|bidirectional group=mount label="Snap type"
// Lite snaps engage a 3.4mm-deep tile instead of the full 6.8mm. Full
// depth is the default for a load-bearing adapter.
snap_lite = false; // @param boolean group=mount label="Lite snaps (3.4mm instead of 6.8mm)"

// ----- Plate -----
plate_t = 4; // @param number min=3 max=6 step=0.5 unit=mm group=plate label="Back plate thickness"

// ----- Multiconnect slot tuning (front receiver) -----
// Defaults reproduce the standard Multiconnect fit. Same canonical
// @param set the sibling mounts expose (see scripts/patches/QuackWorks/
// 0003 for the pass-through). backThickness and the 25mm pitch stay
// fixed by choice (board compatibility).
slot_tolerance = 1.0;  // @param number min=0.925 max=1.075 step=0.005 group=slot label="Slot fit tolerance"
slot_retention = true; // @param boolean group=slot label="Slot retention (v2 snap)"
dimple_scale   = 1.0;  // @param number min=0.5 max=1.5 step=0.05 group=slot label="Dimple scale (v1 only)"
on_ramp        = true; // @param boolean group=slot label="Slot on-ramp lead-in"

// @preset id="default" label="Single tile, directional full snap" size=single snap_type=directional snap_lite=false plate_t=4
// @preset id="double" label="Two tiles, two slots" size=double snap_type=directional snap_lite=false plate_t=4

// === Derived ===

is_double        = (size == "double");
width_units      = is_double ? 2 : 1;   // openGrid tiles across
snap_directional = (snap_type == "directional");

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed depth of snap tops into the plate (st-v7k)
bury       = 0.6;   // receiver sink into the plate (real weld, not a kiss)

// Plate: whole openGrid tiles wide, one tile tall. Frame: X centered on
// the snap array, Y = 0 at the bottom edge (up the wall = +Y), Z = 0 on
// the bed at the snap faces.
W = width_units * snap_pitch;   // plate width  (28 or 56)
H = snap_pitch;                 // plate height (28, one tile tall)

plate_z0  = snap_h - weld;
plate_top = plate_z0 + plate_t;

// Multiconnect receiver constants.
slot_spacing = 25;   // Multiconnect standard pitch (1 MU)
mc_thickness = 6.5;  // receiver slab depth (the module's fixed backThickness)

corner_r = 1;   // vertical-edge rounding on the plate

// PRINT_ANCHOR_BBOX at defaults (size = "single"):
//   X = W                          = 1 * 28              = 28
//   Y = H                          =                       28
//   Z = plate_top + mc_thickness   = (6.8 - 0.02 + 4) + 6.5 = 17.28
// (the receiver slab stacks 6.5mm on the plate top, minus the 0.6mm
// weld overlap it sinks in — but its front face still lands at
// plate_top - bury + 6.5 = 16.68... the 17.28 above counts from the
// plate top without the weld sink; measured value pinned from export.)
PRINT_ANCHOR_BBOX = [28, 28, 16.68];

// === Back snaps ===

// One openGridSnap in its own frame (front/strong nub toward +X),
// welded into a single watertight solid — kept textually identical to
// opengrid_snaps / opengrid_bin (st-v7k / st-0of). Directional: two side
// nubs + a 14mm-wide strong front nub + a rear click nub riding 0.65
// higher. Bidirectional: four identical standard nubs on the base band.
module welded_snap() {
    base   = snap_lite ? 0 : 3.4;
    root_z = max(0, base - 0.01);
    root_h = snap_lite ? 0.61 : 0.62;
    openGridSnap(lite = snap_lite, directional = snap_directional,
                 anchor = BOT, orient = UP, spin = 0);
    if (snap_directional) {
        for (a = [90, 270])                          // side (standard) nubs
            zrot(a) translate([12.4, 0, root_z])
                cuboid([0.3, 11.6, root_h], anchor = BOT);
        translate([12.4, 0, root_z])                 // front (strong) nub
            cuboid([0.3, 14.6, root_h], anchor = BOT);
        zrot(180) translate([12.4, 0, base + 0.64])  // rear (click) nub
            cuboid([0.3, 11.6, 0.62], anchor = BOT);
    } else {
        for (a = [0, 90, 180, 270])                  // four standard nubs
            zrot(a) translate([12.4, 0, root_z])
                cuboid([0.3, 11.6, root_h], anchor = BOT);
    }
}

// One snap per tile, centered in X on the plate, centered in Y on the
// single tile row. zrot(90) turns each directional snap's strong front
// nub toward +Y — up the wall.
module grid_snaps() {
    for (cx = [0 : width_units - 1])
        translate([(cx - (width_units - 1) / 2) * snap_pitch, H / 2, 0])
            zrot(90) welded_snap();
}

// === Back plate ===

module plate() {
    translate([0, 0, plate_z0])
        linear_extrude(height = plate_t)
            rect([W, H], rounding = corner_r, anchor = FRONT);
}

// === Front Multiconnect receiver ===
//
// QuackWorks' BOSL2-free master slot back. multiconnectBack's local
// frame L: a cube x[0,W] y[-6.5,0] z[0,H], slots recessed from the
// y=-6.5 face, retention dome at high z, entry mouth + on-ramp at low z.
// Two stacked transforms put the mouths at the front and the dome at the
// bottom (load direction, see the header):
//   1. rotate([-90,0,0]) maps (lx,ly,lz) -> (lx, lz, -ly): the y=-6.5
//      face (slot mouths) turns to +Z (front, away from the wall) and
//      the dome/insertion axis L.z turns to +Y.
//   2. zrot(180) then flips +Y->-Y so the dome points DOWN while the
//      mouths stay on +Z; the two translates re-center X and lift the
//      slab so its solid back overlaps bury=0.6mm into the plate top and
//      its mouths open at the front face (z = plate_top - bury + 6.5).
module receiver() {
    translate([0, H, 0])
        zrot(180)
            translate([-W / 2, 0, plate_top - bury])
                rotate([-90, 0, 0])
                    multiconnectBack(backWidth = W, backHeight = H,
                                     distanceBetweenSlots = slot_spacing,
                                     quickRelease = !slot_retention,
                                     tolerance = slot_tolerance,
                                     dimple = dimple_scale,
                                     onRamp = on_ramp);
}

// === Assembly (root-level siblings; receiver never union()'d away) ===

grid_snaps();
plate();
receiver();
