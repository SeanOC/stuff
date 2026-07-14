// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Ego Power+ powerhead wall holder — openGrid remount of the operator's
// screw-mount bracket (pst-3m2). The operator-supplied mesh
// (models/ego_powerhead_mount_source.stl, 7,676 triangles) is
// import()ed as-is, its four countersunk screw holes are plugged
// solid, and a 2x4 grid of directional openGrid snaps is fused onto
// the wall face. import()-based modeling is deliberate here: the wasm
// render-path performance problem that forced the native remodel of
// ego_lb6500_blower_mount (st-82o) is fixed per the operator
// (pst-3m2), and the st-zph silently-missing-mesh failure mode is now
// fatal in the pipeline (lib/wasm/closure.ts missingAssets). The
// invariants sidecar still raycast-compares the export against the
// source mesh so a broken import can't ship.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived model is for personal use only; do not
// sell prints or files.
//
// === Source-mesh anatomy (measured off the STL; frame: z=0 is the
//     wall/back face, x spans the 56mm width, y is height on the wall) ===
//
// Back plate z=0..15, full 56 x 110 footprint, with four countersunk
// screw holes (Ø5.1 shafts at x≈12/44, y=40/97, tilted ~8° outward,
// countersinks flaring to Ø9.5 at the z=15 front face). A bottom
// shelf (y=0..29 tapering to 22) and an upper fork rail (y=58..68)
// run out to z=135, joined by a diagonal strut from the plate top;
// the outer end carries a ~27mm-wide central slot through both
// levels where the powerhead shaft drops in.
//
// === Print orientation: ZERO supports (pst-efb) ===
//
// Prints snaps-down: the snap faces are the first layers, then the
// plugged plate, then the shelf/strut/fork rising 135mm. The plugs
// and snaps keep the wall face a single flat plane; the 3.2mm
// channels between snaps stay clear. Two regions of the as-imported
// bracket needed work to print supportless in this orientation
// (slicer-style face scan of the export; overhang measured as angle
// from vertical, threshold 50°):
//
//  1. WALL-FACE RIMS (was ~1620mm² of 90° face floating 6.78mm above
//     the bed): the plate underside rides on the snap tops, and
//     beyond the outer rows of the old 2x3 snap grid a 14.6mm-deep
//     rim at each Y end started mid-air. FIX (bead option A): the
//     back plate is extended +Y from the mesh's 110mm to back_d =
//     112mm — exactly 4 openGrid cells at the 28mm pitch — so the
//     snap auto-fit places a 2x4 grid and the worst rim shrinks to
//     the same 1.6mm lip the X sides always had (X is already exactly
//     2 cells: 56 = 2*28). Side benefit: 8 snaps instead of 6.
//
//  2. SHELF-LIP NOTCH CEILINGS: each shelf rail's outer end carries a
//     retention lip whose notch (print z≈98.2 floor / 111.2 shoulder
//     step up to a 9.2 x 6.8mm ceiling at z≈138.2) is functional
//     clearance for the powerhead — it cannot be filled or chamfered.
//     FIX (bead option B): two breakaway ribs per notch (one from the
//     floor, one from the shoulder), welded at the bottom through a
//     thin snap-off neck and stopping 0.2mm short of the ceiling so
//     the cap's first layer bridges onto the rib tops. SNAP THE FOUR
//     RIBS OUT of the notches before first use.
//
// Worst remaining unsupported overhang: the 1.6mm plate-rim lips and
// the <=3.6mm ceiling bridge spans between rib tops. Every other
// downward face steeper than 50° from vertical is on the bed, bridges
// the 3.2mm inter-snap channels, or is the vendored snap's own sub-mm
// click-nub relief, which openGrid prints in exactly this orientation
// by design. The invariants sidecar pins rib presence, the breakaway
// gap, and the <=1.8mm rim reach.
//
// === Wall-hang orientation / load direction ===
//
// OPERATOR CORRECTION (pst-ozs): in real usage 'up' on the wall is
// this model's -Y vector — the earlier +Y-up inference from the
// bearing faces (pst-3m2) was inverted. Directional snaps therefore
// hang zrot(-90): the strong front nub (non-flexing, 0.8mm deep vs
// 0.4, indicator-marked) points -Y — up the wall in usage — so the
// lever-out moment the cantilevered powerhead puts on the top snap
// row bears on the rigid hook, and the flexy click-in side faces +Y
// (down in usage) where the moment presses the plate into the wall.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

snap_lite = false; // @param boolean group=mount label="Lite openGrid snaps (3.4mm instead of 6.8mm)"

// @preset id="default" label="Default (full-depth snaps)" snap_lite=false

// === Fixed geometry (matches the source mesh — not tunable) ===

plate_w  = 56;   // bracket X extent
plate_d  = 110;  // bracket Y extent (height on the wall)
mesh_h   = 135;  // bracket Z extent (depth out from the wall)
plate_t  = 15;   // back plate thickness

// Screw-hole plugs: one Ø16 cylinder per hole, spanning the full
// plate thickness. Each hole's swept envelope (tilted Ø5.1 shaft +
// countersink, measured by slicing the mesh) stays within 4.8mm of
// the envelope center, so a Ø16 plug welds ≥3.2mm of real overlap
// into the surrounding plate on every side while staying ≥2mm inside
// the plate edges. Plug faces are flush with the wall face (z=0) and
// the plate front (z=15) — flush, not proud, so the wall face stays a
// grid-seatable plane and the front face stays true to the source.
plug_d = 16;
plug_centers = [[10, 40], [10, 97], [46, 40], [46, 97]];

// openGrid snaps
snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
og_weld    = 0.02;  // embed of snap tops into the wall face (st-vmn).
                    // Deliberately shallow — sinking deeper would offset
                    // the click nubs from the grid's groove plane.

// Grid-aligned back plate (pst-efb): the wall plate is extended +Y
// from the mesh's 110mm to exactly 4 openGrid cells so a 4th snap row
// fits with >=1mm rim and the plate underside never overhangs more
// than a 1.6mm lip (print-orientation rationale in the header).
back_d = 4 * snap_pitch;  // 112

// Snap grid auto-fit over the plugged 56 x 112 wall face: as many
// snaps as fit at 28mm pitch keeping >= 1mm rim, always centered.
// Net at these dimensions: 2 cols x 4 rows = 8 snaps, every footprint
// fully backed by the (now hole-free, +Y-extended) plate.
snap_cols = max(1, floor((plate_w - 2 - snap_w) / snap_pitch) + 1);
snap_rows = max(1, floor((back_d - 2 - snap_w) / snap_pitch) + 1);

// Lift of the bracket above the bed = snap depth minus the weld embed.
body_lift = snap_h - og_weld;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at
// defaults (snap_lite = false).
// X: plate_w = 56   Y: back_d = 112
// Z: snap_h (6.8) - og_weld (0.02) + mesh_h (135) = 141.78
// (snap_lite variant: Z = 3.4 - 0.02 + 135 = 138.38)
PRINT_ANCHOR_BBOX = [56, 112, 141.78];

// === Breakaway notch supports (pst-efb) ===
//
// The retention-lip notch on each shelf rail leaves a 9.2 x 6.8mm
// ceiling 27-40mm mid-air in the print orientation (all measured off
// the source mesh, source frame = print frame minus body_lift):
// ceiling at z=131.4, deep notch floor at z=91.4 (x 9.6..14.65),
// shoulder step at z≈104.3 (x 5.5..9.2), notch open y≈1.1..7.9;
// mirrored about the slot centerline x=28. One rib rises from each
// floor level, stopping 0.2mm short of the ceiling (the cap's first
// layer bridges onto the rib tops; the gap keeps them breakaway and
// the body 2-manifold), welded to the floor through a thin neck that
// twists off leaving a <=0.5mm witness mark. The rib body overlaps
// its neck 0.3mm — volumetric weld, no tangent faces (wasm CGAL trap).
rib_t    = 1.0;   // rib thickness (x)
rib_neck = 0.5;   // snap-off neck thickness (x)
rib_y0   = 1.4;   // clear of the lip inner face (y≈1.1)...
rib_y1   = 7.6;   // ...and of the rail wall (y≈7.9)
rib_top  = 131.2; // 0.2mm breakaway gap below the notch ceiling (131.4)
rib_sites = [[11.9, 91.4], [7.4, 104.3]];  // [x center, floor z], left notch

module breakaway_ribs() {
    for (s = rib_sites, xc = [s[0], plate_w - s[0]]) {
        translate([xc - rib_neck / 2, rib_y0, s[1] - 0.5])   // neck: 0.5 sunk
            cube([rib_neck, rib_y1 - rib_y0, 1.1]);
        translate([xc - rib_t / 2, rib_y0, s[1] + 0.3])      // rib body
            cube([rib_t, rib_y1 - rib_y0, rib_top - s[1] - 0.3]);
    }
}

// === Bracket body: imported mesh + screw-hole plugs ===

module holder_body() {
    // Path is models/-relative in both render paths: desktop openscad
    // resolves siblings of the .scad, the wasm closure walker mounts
    // the asset at the FS root next to the entry (lib/wasm/closure.ts).
    import("ego_powerhead_mount_source.stl", convexity = 4);
    for (c = plug_centers)
        translate([c.x, c.y, 0])
            cylinder(d = plug_d, h = plate_t);
    // +Y back-plate extension to the 4-cell grid line (pst-efb):
    // y 109..112, 1mm volumetric weld overlap into the mesh plate.
    translate([0, plate_d - 1, 0])
        cube([plate_w, back_d - plate_d + 1, plate_t]);
    breakaway_ribs();
}

// === openGrid snaps ===

// One openGrid snap in its own frame (front/strong nub toward +X),
// welded into a single solid — verbatim from ego_lb6500_blower_mount
// (st-0of), where it's verified watertight + single-component for both
// snap depths. openGridSnap models its click nubs as face-touching
// solids whose root tangent line survives as a non-2-manifold edge;
// each 0.3mm shim straddles a nub/core contact plane (local x=12.4)
// and volumetrically fuses nub to core on both CGAL and Manifold. The
// 14mm-wide front nub's shim widens to 14.6; the rear nub's sits 0.65
// higher (its root rides above the base band in the directional
// variant). NEVER re-derive snap geometry — the browser pipeline can
// only resolve vendored libs/, so this wrapper is kept textually
// identical across models: fix a bug here, apply it to the siblings.
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

// Snap grid centered on the (extended) wall face, zrot(-90) turning
// each snap's strong front nub toward -Y (up on the wall in usage —
// load direction rationale in the header).
module grid_snaps() {
    for (cx = [0 : snap_cols - 1], ry = [0 : snap_rows - 1])
        translate([plate_w / 2 + (cx - (snap_cols - 1) / 2) * snap_pitch,
                   back_d / 2 + (ry - (snap_rows - 1) / 2) * snap_pitch,
                   0])
            zrot(-90) welded_directional_snap();
}

translate([0, 0, body_lift]) holder_body();
grid_snaps();
