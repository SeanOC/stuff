// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Ego MultiHead EA0820 edger tool wall mount — openGrid remount of the
// operator's screw-mount bracket V2 (pst-bly). The operator-supplied
// mesh (models/ego_ea0820_edger_mount_source.stl, 9,160 triangles) is
// import()ed as-is per the imported-STL playbook
// (docs/imported-model-opengrid-playbook.md): its four countersunk
// screw holes are plugged solid, the back plate is extended +Y to the
// 5-cell openGrid line, and a 2x5 grid of directional openGrid snaps
// is fused onto the wall face. The invariants sidecar raycast-compares
// the export against the source mesh so a broken import can't ship.
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
// Back plate z=0..16, full 56 x 123.2 footprint, with four countersunk
// screw holes (Ø5.16 shafts at x≈11/45, y=50.2/107.2, tilted ~7°
// outward, countersinks flaring to ~Ø8.8 at the z=16 front face; each
// hole's swept envelope stays within 4.8mm of its center). Above the
// plate, two hook towers (x 6.75..14.65 and its mirror about x=28,
// y 0..22) rise to z=152.4, joined by a central web below z~140 and
// braced by body walls running out to y=85 plus a ~42° buttress wedge
// from the plate front (y 86..123) up into the body. Each tower
// carries a tool slot — void inward of the x≈10.3 wall, y 0..9, floor
// at z=102.45 — where the EA0820 edger head's mounting bar drops in
// from above (usage-up = -Y, so the slot mouths at y=0 open upward in
// use); the slot is capped by a flat ceiling at z=148.85.
//
// === Print orientation: ZERO supports (operator: keep the STL's own
//     orientation) ===
//
// Prints snaps-down: the snap faces are the first layers, then the
// plugged plate, then the towers rising to 152.4mm. The plugs and
// snaps keep the wall face a single flat plane; the 3.2mm channels
// between snaps stay clear. Two regions needed work to print
// supportless in this orientation (slicer-style face scan of the
// export; overhang measured as angle from vertical, threshold 50°):
//
//  1. WALL-FACE RIMS: the plate underside rides on the snap tops, and
//     the source's 123.2mm Y extent is not a whole number of 28mm
//     openGrid cells — a centered snap grid left a 7.2mm-deep rim at
//     each Y end starting mid-air. FIX (playbook §6.2): the back
//     plate is extended +Y from the mesh's 123.2mm to back_d = 140mm —
//     exactly 5 openGrid cells — so the snap auto-fit places a 2x5
//     grid and the worst rim shrinks to the same 1.6mm lip the X
//     sides always had (X is already exactly 2 cells: 56 = 2*28).
//     Side benefit: 10 snaps instead of 8. Blended into the molded
//     shape (playbook §7): the extension's edges carry the source's
//     measured r2 roundover, and the slab's inner top edge starts at
//     ext_y0 = 121.2 exactly where the source's own front-edge r2
//     roundover ends, so old and new surfaces continue tangentially.
//     The buttress wedge's ~42° face crosses the z=16 plate front
//     right at y≈123.2, so it lands on the slab top in a concave
//     crease exactly like the source's own wedge-foot crease at y=86.
//     +Y is DOWN the wall in usage, so the extension hangs below the
//     bracket where nothing docks.
//
//  2. TOOL-SLOT CEILINGS: each tower's slot is capped at z=148.85 by
//     a flat ceiling (x 11.3..14.65 mirrored about x=28, y 1..7)
//     floating 46mm above the slot floor — functional clearance for
//     the edger's mounting bar, so it cannot be filled or chamfered.
//     FIX (playbook §6.3): one breakaway rib per slot rising from the
//     slot floor (z=102.45), welded at the bottom through a thin
//     snap-off neck and stopping 0.2mm short of the ceiling so the
//     cap's first layer bridges <=1.7mm onto the rib top. SNAP THE
//     TWO RIBS OUT of the slots before first use.
//
// Worst remaining unsupported overhang: the 1.6mm plate-rim lips and
// the <=1.7mm ceiling bridge spans beside the rib tops. Every other
// downward face steeper than 50° from vertical is on the bed, bridges
// the 3.2mm inter-snap channels, or is the vendored snap's own sub-mm
// click-nub relief, which openGrid prints in exactly this orientation
// by design. The invariants sidecar pins rib presence, the breakaway
// gap, and the <=1.8mm rim reach.
//
// === Wall-hang orientation / load direction ===
//
// OPERATOR-STATED (pst-bly, not inferred): in real usage 'up' on the
// wall is this model's -Y vector. Directional snaps therefore hang
// zrot(-90): the strong front nub (non-flexing, 0.8mm deep vs 0.4,
// indicator-marked) points -Y — up the wall in usage — so the
// lever-out moment the cantilevered edger head puts on the top snap
// row bears on the rigid hook, and the flexy click-in side faces +Y
// (down in usage) where the moment presses the plate into the wall.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

snap_lite = false; // @param boolean group=mount label="Lite openGrid snaps (3.4mm instead of 6.8mm)"

// Every convex edge on the source bracket measures r=2.0 (plate
// front-face side edges: (0,14)->(2,16) arc at y=60; plan corners:
// (0,2)->(2,0) arcs) — the extension's edges default to the same.
ext_fillet = 2; // @param number min=1 max=3 step=0.25 unit=mm group=mount label="Extension edge roundover radius (source edges measure 2.0)"

// @preset id="default" label="Default (full-depth snaps)" snap_lite=false

// === Fixed geometry (matches the source mesh — not tunable) ===

plate_w  = 56;    // bracket X extent
plate_d  = 123.2; // bracket Y extent (height on the wall)
mesh_h   = 152.4; // bracket Z extent (depth out from the wall)
plate_t  = 16;    // back plate thickness

// Screw-hole plugs: one Ø16 cylinder per hole, spanning the full
// plate thickness. Each hole's swept envelope (tilted Ø5.16 shaft +
// countersink, measured by slicing the mesh) stays within 4.8mm of
// the envelope center, so a Ø16 plug welds >=3.2mm of real overlap
// into the surrounding plate on every side while staying >=2mm inside
// the plate edges. Plug faces are flush with the wall face (z=0) and
// the plate front (z=16) — flush, not proud, so the wall face stays a
// grid-seatable plane and the front face stays true to the source.
plug_d = 16;
plug_centers = [[10, 50.2], [10, 107.2], [46, 50.2], [46, 107.2]];

// openGrid snaps
snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
og_weld    = 0.02;  // embed of snap tops into the wall face (st-vmn).
                    // Deliberately shallow — sinking deeper would offset
                    // the click nubs from the grid's groove plane.

// Grid-aligned back plate (playbook §6.2): the wall plate is extended
// +Y from the mesh's 123.2mm to exactly 5 openGrid cells so a 5th
// snap row fits with >=1mm rim and the plate underside never
// overhangs more than a 1.6mm lip (print-orientation rationale in the
// header).
back_d = 5 * snap_pitch;  // 140

// Blended extension (playbook §7): the slab starts at ext_y0 = 121.2,
// exactly where the source's own r2 front-edge roundover ends, so old
// and new rounded surfaces continue tangentially, and carries
// ext_fillet roundovers on every new convex edge. Unlike the
// powerhead there is no strut-landing cut: the buttress wedge's 42°
// face meets the slab top at a concave crease matching the source's
// own wedge-foot crease at y=86.
ext_y0 = 121.2;  // slab inner edge: end of the source's own roundovers

// Snap grid auto-fit over the plugged 56 x 140 wall face: as many
// snaps as fit at 28mm pitch keeping >= 1mm rim, always centered.
// Net at these dimensions: 2 cols x 5 rows = 10 snaps, every
// footprint fully backed by the (now hole-free, +Y-extended) plate.
snap_cols = max(1, floor((plate_w - 2 - snap_w) / snap_pitch) + 1);
snap_rows = max(1, floor((back_d - 2 - snap_w) / snap_pitch) + 1);

// Lift of the bracket above the bed = snap depth minus the weld embed.
body_lift = snap_h - og_weld;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at
// defaults (snap_lite = false).
// X: plate_w = 56   Y: back_d = 140
// Z: snap_h (6.8) - og_weld (0.02) + mesh_h (152.4) = 159.18
// (snap_lite variant: Z = 3.4 - 0.02 + 152.4 = 155.78)
PRINT_ANCHOR_BBOX = [56, 140, 159.18];

// === Breakaway slot supports (playbook §6.3) ===
//
// Each tower's tool slot leaves a flat ceiling (z=148.85, y 1..7,
// x 11.3..14.65 and mirror) 46mm above the slot floor (z=102.45) in
// the print orientation (all measured off the source mesh, source
// frame = print frame minus body_lift). One rib rises mid-slot from
// each floor, stopping 0.2mm short of the ceiling (the cap's first
// layer bridges <=1.7mm onto the rib top; the gap keeps it breakaway
// and the body 2-manifold), welded to the floor through a thin neck
// that twists off leaving a <=0.5mm witness mark. The rib body
// overlaps its neck 0.3mm — volumetric weld, no tangent faces (wasm
// CGAL trap). Rib y stops at 6.8, inside the flat ceiling span: past
// y=7 the ceiling rounds down toward the y=9 slot wall and a
// full-length rib would fuse into that roundover.
rib_t    = 1.0;    // rib thickness (x)
rib_neck = 0.5;    // snap-off neck thickness (x)
rib_y0   = 1.4;    // clear of the slot mouth roundover (y<1)...
rib_y1   = 6.8;    // ...and of the ceiling's y>7 roundover
rib_top  = 148.65; // 0.2mm breakaway gap below the slot ceiling (148.85)
rib_sites = [[12.5, 102.45]];  // [x center, floor z], left slot

module breakaway_ribs() {
    for (s = rib_sites, xc = [s[0], plate_w - s[0]]) {
        translate([xc - rib_neck / 2, rib_y0, s[1] - 0.5])   // neck: 0.5 sunk
            cube([rib_neck, rib_y1 - rib_y0, 1.1]);
        translate([xc - rib_t / 2, rib_y0, s[1] + 0.3])      // rib body
            cube([rib_t, rib_y1 - rib_y0, rib_top - s[1] - 0.3]);
    }
}

// === Blended back-plate extension (playbook §6.2 + §7) ===

// +Y back-plate extension to the 5-cell grid line: y ext_y0..140,
// welded 2mm volumetrically into the mesh plate (y 121.2..123.2 is
// solid plate below the front-edge roundover), with the source's edge
// roundover on every new convex edge — outer top edge, top side
// edges, vertical outer corners. The FRONT/BOT edges stay sharp: they
// are buried in the weld or on the z=0 wall plane, which must remain
// flat for grid seating.
//
// Built as the intersection of three rounded-rect extrusions rather
// than BOSL2 cuboid(rounding=, edges=): the subset-edges rounding
// path in cuboid() hulls eight corner shapes, and degenerate corner
// pieces deterministically trip the wasm build's CGAL convex_hull_3
// assertion (pst-5kz / lib/wasm/render.ts). rect() emits plain
// polygons, no hull anywhere. Where three rounded edges meet, the
// intersected corner bulges <=0.23*r (~0.45mm) proud of a true
// sphere — invisible at r=2.
module plate_extension() {
    intersection() {
        // plan: vertical outer-corner roundings (along z)
        linear_extrude(plate_t)
            translate([plate_w / 2, (ext_y0 + back_d) / 2])
                rect([plate_w, back_d - ext_y0],
                     rounding = [ext_fillet, ext_fillet, 0, 0]);
        // yz: outer top-edge roundover (along x)
        rotate([90, 0, 90])
            linear_extrude(plate_w)
                translate([(ext_y0 + back_d) / 2, plate_t / 2])
                    rect([back_d - ext_y0, plate_t],
                         rounding = [ext_fillet, 0, 0, 0]);
        // xz: top side-edge roundovers (along y)
        translate([0, back_d, 0])
            rotate([90, 0, 0])
                linear_extrude(back_d - ext_y0)
                    translate([plate_w / 2, plate_t / 2])
                        rect([plate_w, plate_t],
                             rounding = [ext_fillet, ext_fillet, 0, 0]);
    }
}

// === Bracket body: imported mesh + screw-hole plugs ===

module holder_body() {
    // Path is models/-relative in both render paths: desktop openscad
    // resolves siblings of the .scad, the wasm closure walker mounts
    // the asset at the FS root next to the entry (lib/wasm/closure.ts).
    import("ego_ea0820_edger_mount_source.stl", convexity = 4);
    for (c = plug_centers)
        translate([c.x, c.y, 0])
            cylinder(d = plug_d, h = plate_t);
    plate_extension();
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
