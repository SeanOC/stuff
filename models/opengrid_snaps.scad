// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Standalone openGrid snap connectors — ready-to-print click-in
// fasteners for openGrid boards (pst-dhr). One snap per part; the
// snap_type enum fans the export grid into one STL per variant so all
// four kinds are kept ready-to-print in the repo instead of being
// regenerated from the library each time: lite/full depth crossed with
// directional/bidirectional. Print one, press it straight into a tile.
//
// LICENSING: the snap is QuackWorks' openGridSnap()
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived part is for personal use only; do not
// sell prints or files.
//
// === Print orientation (native): ZERO supports ===
//
// Prints snaps-down, exactly as the wall-mount siblings do (opengrid_bin,
// ego_lb6500_blower_mount): the snap sits on its own 24.8mm core
// underside (z=0) — that flat face IS the minimal print base, no added
// raft or pad. The click nubs are 45deg wedges rising off the sides,
// self-supporting in this orientation (the geometry was designed to
// print this way). Deliberately NOTHING is added under the snap: the
// four flex slots the click nubs need are cut through to z=0, so a
// solid base pad would foul them and kill the snap action. The part is
// a squat 24.8mm block with full bed contact — stable on its own.
//
// === Directional vs bidirectional ===
//
// Directional snaps have one strong front nub (non-flexing, 0.8mm deep
// vs 0.4) plus a rear click nub: mount them with the strong nub UP the
// wall so a cantilevered load levers out against the rigid hook while
// the flexy side faces down (st-0of, same rule the wall-mount siblings
// follow). Bidirectional snaps carry four identical click nubs — use
// them where the part clicks in and pulls straight out with no load
// direction (opengrid_panel_aligner style). The enum's four choices are
// the depth (lite 3.4mm / full 6.8mm) crossed with these two.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

// The four kinds of openGrid snap, one exported STL each (the
// 'filename' flag fans the export grid over the enum). Maps to
// openGridSnap's lite= (depth 3.4 vs 6.8mm) and directional= args.
snap_type = "full-directional"; // @param enum choices=lite-directional|lite-bidirectional|full-directional|full-bidirectional group=snap label="Snap type" filename

// @preset id="default" label="Full-depth directional" snap_type=full-directional
// @preset id="lite_bi" label="Lite bidirectional" snap_type=lite-bidirectional

// === Derived ===

// snap_type = "<depth>-<direction>"; the four choices are exact strings
// (note "bidirectional" also ends in "directional", so compare whole
// strings, never a suffix test).
snap_lite        = (snap_type == "lite-directional" ||
                    snap_type == "lite-bidirectional");
snap_directional = (snap_type == "lite-directional" ||
                    snap_type == "full-directional");

snap_w = 24.8;                    // openGrid snap footprint
snap_h = snap_lite ? 3.4 : 6.8;   // click depth (lite vs full)

// PRINT_ANCHOR_BBOX at defaults (snap_type = "full-directional"),
// measured from the export. The invariants gate fails on >1mm drift, so
// keep this current. The 24.8mm core footprint is widened by the click
// nubs standing proud of it: the side nubs push Y to 25.6, and the
// wider/deeper front nub pushes +X out to 26.0. Z = snap_h = 6.8.
PRINT_ANCHOR_BBOX = [26.0, 25.6, 6.8];

// === Snap ===

// One openGrid snap welded into a single watertight solid. openGridSnap
// models its click nubs as face-touching solids whose roots kiss the
// core along bare tangent lines — detached shells under Manifold,
// non-2-manifold edges under CGAL (the st-v7k class). Each nub root
// gets a 0.3mm shim straddling the nub/core contact plane (local
// x=12.4) that volumetrically fuses nub to core on both engines. This
// wrapper is kept textually identical to the wall-mount siblings
// (opengrid_bin, ego_lb6500_blower_mount, the led_remote_holder twins):
// the browser render pipeline can only resolve vendored libs/, so there
// is no shared project-side module — fix a bug here, apply it to them.
//
// Directional: two side (standard) nubs + a 14mm-wide strong front nub
// (shim widens to 14.6) + a rear click nub whose root rides 0.65 higher
// than the base band. Bidirectional: four identical standard nubs, all
// rooted on the base band.
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

welded_snap();
