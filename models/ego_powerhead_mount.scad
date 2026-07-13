// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Ego Power+ powerhead wall holder — openGrid remount of the operator's
// screw-mount bracket (pst-3m2). The operator-supplied mesh
// (models/ego_powerhead_mount_source.stl, 7,676 triangles) is
// import()ed as-is, its four countersunk screw holes are plugged
// solid, and a 2x3 grid of directional openGrid snaps is fused onto
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
// === Print orientation: ZERO supports ===
//
// Prints snaps-down: the snap faces are the first layers, then the
// plugged plate, then the shelf/strut/fork rising 135mm — the same
// orientation the source bracket was designed to print in (its only
// underside reliefs are 45° chamfers and a ~52° strut). The plugs and
// snaps keep the wall face a single flat plane; the 3.2mm channels
// between snaps stay clear.
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

// Snap grid auto-fit over the plugged 56 x 110 wall face: as many
// snaps as fit at 28mm pitch keeping >= 1mm rim, always centered.
// Net at these dimensions: 2 cols x 3 rows = 6 snaps, every footprint
// fully backed by the (now hole-free) plate.
snap_cols = max(1, floor((plate_w - 2 - snap_w) / snap_pitch) + 1);
snap_rows = max(1, floor((plate_d - 2 - snap_w) / snap_pitch) + 1);

// Lift of the bracket above the bed = snap depth minus the weld embed.
body_lift = snap_h - og_weld;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at
// defaults (snap_lite = false).
// X: plate_w = 56   Y: plate_d = 110
// Z: snap_h (6.8) - og_weld (0.02) + mesh_h (135) = 141.78
// (snap_lite variant: Z = 3.4 - 0.02 + 135 = 138.38)
PRINT_ANCHOR_BBOX = [56, 110, 141.78];

// === Bracket body: imported mesh + screw-hole plugs ===

module holder_body() {
    // Path is models/-relative in both render paths: desktop openscad
    // resolves siblings of the .scad, the wasm closure walker mounts
    // the asset at the FS root next to the entry (lib/wasm/closure.ts).
    import("ego_powerhead_mount_source.stl", convexity = 4);
    for (c = plug_centers)
        translate([c.x, c.y, 0])
            cylinder(d = plug_d, h = plate_t);
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

// Snap grid centered on the wall face, zrot(-90) turning each snap's
// strong front nub toward -Y (up on the wall in usage — load
// direction rationale in the header).
module grid_snaps() {
    for (cx = [0 : snap_cols - 1], ry = [0 : snap_rows - 1])
        translate([plate_w / 2 + (cx - (snap_cols - 1) / 2) * snap_pitch,
                   plate_d / 2 + (ry - (snap_rows - 1) / 2) * snap_pitch,
                   0])
            zrot(-90) welded_directional_snap();
}

translate([0, 0, body_lift]) holder_body();
grid_snaps();
