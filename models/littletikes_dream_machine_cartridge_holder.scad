// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Little Tikes Dream Machine cartridge + figure holder (openGrid wall mount).
//
// A native parametric tray that hangs on an openGrid wall panel. The
// body is sized in whole 28mm openGrid cells (grid_cols x grid_rows); its
// mm footprint is derived from the cell count so the flat back face is
// always an exact integer cell grid and every snap lands dead-centre in
// a cell. Snaps default to ONE PER CELL (grid_cols x grid_rows, the
// original spec's max-hold layout); a sparse cell-aligned subset stays
// selectable via snap_every_cell=false for a much faster CGAL export.
//
// The DEFAULT/preview footprint is a compact 2x4-cell tile (56 x 112mm) —
// intentionally small so the wasm param-sweep stays inside CI's per-shard
// budget (every sweep case renders from these defaults; a dense one-per-
// cell default at the full 9x8 size blew a 45min shard, pst-93r). It is a
// real, printable tile that still exercises every feature (packs 4
// cartridge slots + 1 figure holder + 8 snaps). Scale grid_cols/grid_rows
// up to 9x8 for the full ~250 x 235mm reference holder.
// Two families of pockets AUTO-FILL the derived
// footprint — their counts are computed from the available space and the
// feature pitch, never hard-coded, so they follow the grid size:
//
//   * CARTRIDGE SLOTS open on the +Z top face: rectangular pockets with
//     SQUARE interior vertical corners (52 x 14mm interior) on a 56mm
//     column / 22mm row pitch. The interior corners are sharp
//     (slot_corner_r defaults 0) so a rectangular cartridge seats
//     without the corners pinching (pst-ge6); only the +Z slot-mouth rim
//     is rounded over (slot_rim_roundover, below).
//     Straight-walled to the top rim (only the top edge is rounded over;
//     no widened drop-in mouth). Each column is PHASE-LOCKED to a
//     2-cell openGrid module (56mm = 2 x 28mm): its centre sits over the
//     centre of a 2x(depth) block of cells (module centres at
//     snap_pitch*(2k+1) = 28, 84, 140... over the snap grid), so the 52mm
//     slot stays consistent relative to the back-face snaps (pst-62f).
//     Rows pack into the depth left AFTER
//     the front figure strip is reserved, so they never overlap it at
//     any grid size. Default 2x4 footprint packs 1 x 4 = 4 (a full 9x8
//     packs 4 x 9 = 36).
//   * FIGURE HOLDERS open on the +Y front face: a rectangle capped by a
//     half-circle dome (43.5mm wide, 21.75mm radius), 10mm deep, on a
//     ~49mm pitch. Default 2x4 footprint packs 1 (a full 9x8 packs 5).
//     Each is a closed BLIND
//     pocket: the packer keeps a fig_floor (2mm) solid floor behind it,
//     so it never breaks through into the cartridge slot behind.
//
// All +Z (top) face edges — the outer perimeter and every cartridge slot
// rim — get a top_round round-over: a hull-free quarter-round FILLET
// approximated by a stack of 2D-offset layers sampled at even ANGULAR
// steps around the arc (thin near the top face, where the curve turns
// horizontal), so the profile reads as a smooth curve, not a staircase
// (up-facing so no overhang). See top_outer_roundover / slot_rim_roundover.
//
// This model replaces an earlier import()-of-STL attempt (pst-rll): the
// operator-supplied mesh was 158k triangles of sliver geometry that hung
// the repo's CGAL export/invariants pipeline (>5.5min, no STL). Rebuilt
// natively from primitives per the imported-STL playbook's own guidance
// (docs/imported-model-opengrid-playbook.md is N/A for steps 1-2/5 here;
// steps 3 snaps + 8 verification still govern). Dimensions were measured
// off the reference part by the operator and are all @params.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived model is for personal use only; do not
// sell prints or files. The openConnect receiver geometry (mount_type=
// "openconnect") is modelled NATIVELY from the openConnect spec by
// mitufy (github.com/mitufy/opengrid-projects, openConnect connector
// system, CC-BY 4.0) — dimensions only, no source vendored; openConnect
// is designed for openGrid by David D.
//
// === Back-face MOUNTING OPTIONS (mount_type) ===
//
// The back face carries one of three selectable mounts (mount_type),
// all laid out on the SAME 28mm openGrid cell grid so the footprint
// stays an exact integer cell count whichever is chosen:
//
//   * "opengrid" (DEFAULT, unchanged): the openGrid snaps below. This
//     preserves the original behaviour exactly. snap_lite /
//     snap_every_cell only apply here.
//   * "blank": a flat solid z=0 back with NO connector features — mount
//     it however you like (screws, tape, your own bracket).
//   * "openconnect": one openConnect connector receiver per cell, cut
//     into the back. openConnect is openGrid's own 28mm-compatible
//     connector (17 x 10.6mm, so a slot fits inside a single tile) —
//     kept over Multiconnect, whose 25mm pitch clashes with the 28mm
//     cell sizing. The receiver is a native dovetail slot: a narrow
//     14.4mm mouth at the back face widening to a 17.2mm-wide pocket at
//     2.7mm depth (the openConnect undercut that captures a connector
//     head against straight pull-out), with a full-depth drop-in onramp
//     at one end so a connector can be dropped in and slid to seat.
//     Dimensions are the authoritative openConnect spec (see LICENSING).
//     Simplifications vs the reference generator (operator may request
//     more on review): no side nub click-detent and no 45-degree eased
//     onramp ramp — the dovetail alone gives pull-out capture, and a
//     straight drop-in pocket gives entry. Print NOTE: unlike the snap
//     variant (snaps-down), an openConnect back prints cleanest with the
//     back face UP (receivers opening upward) so the ~17mm pocket roofs
//     don't have to bridge; flip in the slicer.
//
// === Print orientation (native): ZERO supports on the snap side ===
//
// Prints snaps-down: the snap faces are the first layers — the
// orientation the snap geometry was designed to print in. The flat back
// (z=0) is the openGrid wall face; the body lifts snap_h - weld above
// the bed on the snap tops. Cartridge slots open straight up (+Z) so
// their walls are vertical and their floors face up — no overhang. The
// snaps sit one-per-cell with a 1.6mm rim inside each 28mm cell and a
// 3.2mm channel between neighbours (bridges cleanly, openGrid prints
// this way by design).
//
// One overhang is inherent to the spec and NOT auto-supported: each
// figure holder is a domed pocket cut into the vertical +Y wall, so the
// top of its half-circle arch is a shallow inward overhang (worst at the
// apex, a ~fig_depth-deep lip). At r=21.5 this bridges/slightly droops
// but is generally acceptable FDM; add a little support on the front
// face if your printer struggles. Left un-ribbed deliberately — the
// operator reviews renders and can call for a breakaway rib (playbook
// 6.3) if wanted.
//
// === Wall-hang orientation / load direction ===
//
// NON-directional lite snaps (led_remote_holder precedent): the operator
// gave no usage/load direction and the tray is loaded straight down into
// open-top slots, so there is no cantilever lever-out to orient a strong
// hook against. Non-directional snaps click in and pull straight off the
// panel. snap_lite defaults TRUE (3.4mm profile) per the bead.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Back-face mount (see the MOUNTING OPTIONS header) -----
// DEFAULT "opengrid" preserves the original behaviour exactly. `filename`
// expands one export STL per choice (opengrid / blank / openconnect).
mount_type = "opengrid"; // @param enum choices=opengrid|blank|openconnect group=mount label="Back-face mount" filename

// ----- openGrid size (primary: whole 28mm cells) -----
grid_cols = 2;      // @param integer min=2 max=9 step=1 group=grid label="Width (28mm openGrid cells)"
grid_rows = 4;      // @param integer min=3 max=9 step=1 group=grid label="Height (28mm openGrid cells)"
// snap_lite / snap_every_cell apply to the openGrid mount only (no-ops for
// blank / openconnect).
snap_lite = true;   // @param boolean group=grid label="Lite snaps (3.4mm not 6.8mm; openGrid mount)"
body_h    = 41;     // @param number min=38 max=55 step=1 unit=mm group=grid label="Body depth out from the wall (Z)"
body_corner_r = 3;  // @param number min=0.5 max=8 step=0.5 unit=mm group=grid label="Body vertical-corner radius"
// Default TRUE: one lite snap per cell (grid_cols x grid_rows), the
// original spec's max-hold layout. This makes the wasm/browser preview
// heavier and the desktop CGAL export slower the larger the grid gets
// (a full 9x8 is a 72-snap union), but preview perf is not a blocker
// (the wasm path is preview-only, not export) and the CGAL export still
// lands inside CI's budget (pst-93r). The default 2x4 tile is only 8
// snaps, so the preview and the whole param-sweep stay light.
// Set FALSE for a sparse, still-cell-aligned subset (snap_sparse_cols x
// snap_sparse_rows, evenly spread and corner-inclusive) that holds a
// tray firmly and exports far faster (~45s with the batched pocket cuts).
snap_every_cell = true; // @param boolean group=grid label="Snap in every cell (one per cell; openGrid mount)"

// ----- Cartridge slots (open on +Z top; counts auto-fill) -----
slot_w         = 52;  // @param number min=30 max=56 step=0.5 unit=mm group=cartridge label="Cartridge slot width (X)"
slot_l         = 14;  // @param number min=8 max=19 step=0.5 unit=mm group=cartridge label="Cartridge slot length (Y)"
slot_depth     = 36;  // @param number min=10 max=40 step=1 unit=mm group=cartridge label="Cartridge slot depth"
floor_z        = 5;   // @param number min=2 max=8 step=0.5 unit=mm group=cartridge label="Pocket floor height above the back"
slot_col_pitch = 56;  // @param number min=54 max=90 step=0.5 unit=mm group=cartridge label="Slot column pitch (X; default 56 = 2 openGrid cells)"
slot_row_pitch = 22;  // @param number min=18 max=40 step=0.5 unit=mm group=cartridge label="Slot row pitch (Y)"
slot_corner_r  = 0;   // @param number min=0 max=6 step=0.5 unit=mm group=cartridge label="Slot interior corner radius (0 = square)"
top_round      = 1.2; // @param number min=0 max=3 step=0.2 unit=mm group=cartridge label="Top-edge round-over (outer rim + slot rims; 0=off)"

// ----- Figure holders (open on +Y front; count auto-fills) -----
fig_w      = 43.5;  // @param number min=24 max=46 step=0.5 unit=mm group=figures label="Figure pocket width (dome dia.)"
fig_rect_h = 9;     // @param number min=3 max=13 step=0.5 unit=mm group=figures label="Figure straight-wall height"
fig_depth  = 10;    // @param number min=5 max=18 step=0.5 unit=mm group=figures label="Figure pocket depth into front"
fig_pitch  = 49.25; // @param number min=47 max=90 step=0.25 unit=mm group=figures label="Figure pocket pitch (X)"

// @preset id="default" label="Default (2x4 tile, openGrid snaps)" mount_type=opengrid grid_cols=2 grid_rows=4 snap_lite=true snap_every_cell=true
// @preset id="full_holder" label="Full holder (9x8 cells)" mount_type=opengrid grid_cols=9 grid_rows=8 snap_lite=true snap_every_cell=true
// @preset id="sparse_snaps" label="Sparse snaps (faster CGAL export)" snap_every_cell=false
// @preset id="blank_back" label="Blank back (no connector features)" mount_type=blank
// @preset id="openconnect" label="openConnect receivers (2x4 tile)" mount_type=openconnect grid_cols=2 grid_rows=4

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed of snap tops into the back face (st-v7k)
// Lift the body onto the snap tops for the openGrid mount; the blank and
// openConnect mounts have no snaps, so the back face sits flat on the bed.
body_lift  = mount_type == "opengrid" ? snap_h - weld : 0;

// Footprint derives from the cell count: an exact integer openGrid grid,
// so snaps land on cell centres and the back face is a clean N x M grid.
//   default 2x4: 2 * 28 = 56 (X) by 4 * 28 = 112 (Y) — a compact preview
//   tile. The full holder (9x8) is 252 x 224mm, the closest whole-cell
//   match to the measured ~250 x 235mm reference part.
body_w = grid_cols * snap_pitch;
body_d = grid_rows * snap_pitch;

// Cartridge slots auto-fill: as many slot_w x 14 pockets as fit at the
// column/ row pitch, then centred with even edge margins. The +Y front
// figure strip (fig_depth deep) plus a solid floor behind each figure
// pocket is RESERVED FIRST, so rows pack only into the remaining depth
// cart_depth and never break through into the figure pockets at any
// grid/param (pst-93r items 1+3). The straight-walled slot cut is at most
// slot_l deep in Y, so this reserve keeps even the front row >= fig_floor
// clear of the figure pockets. Counts follow the footprint
// (default 2x4 = 1 x 4 = 4; a full 9x8 = 4 x 9 = 36).
fig_floor = 2;   // solid floor (mm) kept behind each figure pocket
cart_depth = body_d - fig_depth - fig_floor;
n_slot_cols = max(0, floor((body_w - slot_w) / slot_col_pitch) + 1);
n_slot_rows = max(0, floor((cart_depth - slot_l) / slot_row_pitch) + 1);
// Column X is PHASE-LOCKED, not just pitched: centre the array, then snap
// its first column onto the nearest 2-cell openGrid module centre. Module
// centres sit at snap_pitch*(2k+1) = 28, 84, 140... (the mid-line between
// each pair of cells, over the same grid origin the snaps use), so every
// 52mm slot lands centred over a 2x(depth) block of cells and stays fixed
// relative to the back-face snaps regardless of how the packing margin
// shifts. With the default 56mm pitch every column then lands on a module
// centre; a user-tuned pitch keeps only the first column locked (pst-62f).
slot_module = 2 * snap_pitch;   // 56mm = one 2-cell openGrid module
slot_x_centered = (body_w - (n_slot_cols - 1) * slot_col_pitch) / 2;
slot_x0 = snap_pitch + slot_module * round((slot_x_centered - snap_pitch) / slot_module);  // first col centre (module-locked)
slot_y0 = (cart_depth - (n_slot_rows - 1) * slot_row_pitch) / 2;  // first row centre
// Slot floor clamps up if the body is too shallow for the full depth, so
// the pocket never punches through the back (keeps param sweeps valid).
slot_bottom = max(floor_z, body_h - slot_depth);

// Figure holders auto-fill along the width; the dome radius is half the
// pocket width so the arch always caps the straight walls cleanly.
fig_r  = fig_w / 2;
n_figs = max(0, floor((body_w - fig_w) / fig_pitch) + 1);
fig_x0 = (body_w - (n_figs - 1) * fig_pitch) / 2;  // first pocket centre

// Snap placement (cell indices). Dense = one per cell. Sparse = an
// evenly-spread, corner-inclusive subset sized snap_sparse_cols x
// snap_sparse_rows (clamped to the grid) — enough to hold a loaded tray
// while keeping the default CGAL export fast (see snap_every_cell above).
snap_sparse_cols = 4;
snap_sparse_rows = 3;
// Evenly spread n corner-inclusive picks across c cells (all cells if
// n >= c; the centre cell if n <= 1).
function _spread(c, n) =
    n >= c ? [for (i = [0 : c - 1]) i] :
    n <= 1 ? [floor((c - 1) / 2)] :
             [for (k = [0 : n - 1]) round(k * (c - 1) / (n - 1))];
snap_col_idx = snap_every_cell ? [for (i = [0 : grid_cols - 1]) i]
                               : _spread(grid_cols, snap_sparse_cols);
snap_row_idx = snap_every_cell ? [for (j = [0 : grid_rows - 1]) j]
                               : _spread(grid_rows, snap_sparse_rows);
snap_count = len(snap_col_idx) * len(snap_row_idx);

// PRINT_ANCHOR_BBOX at defaults (literal numbers — the invariants gate
// fails on >1mm drift from the exported STL). Default is the 2x4 tile:
//   X = body_w    = 2 * 28              = 56
//   Y = body_d    = 4 * 28              = 112
//   Z = body_lift + body_h = 3.4 - 0.02 + 41 = 44.38
PRINT_ANCHOR_BBOX = [56, 112, 44.38];

// === Snaps ===

// One openGrid snap in its own frame, welded into a single solid — the
// non-directional lite variant, verbatim from led_remote_holder_51x84mm
// (st-v7k / st-0of): openGridSnap models its four click nubs as
// face-touching solids whose root tangent line survives as a
// non-2-manifold edge; each 0.3mm shim straddles a nub/core contact
// plane (local x=12.4) and volumetrically fuses nub to core on both CGAL
// and Manifold. NEVER re-derive snap geometry — the browser pipeline can
// only resolve vendored libs/, so this wrapper is kept textually
// identical across the sibling models (led_remote_holder twins,
// opengrid_panel_aligner): fix a bug here, apply it to the siblings.
module welded_snap() {
    root_z = snap_lite ? 0 : 3.39;  // clamp to the bed for lite snaps
    openGridSnap(lite = snap_lite, directional = false,
                 anchor = BOT, orient = UP);
    zrot_copies(n = 4)
        translate([12.4, 0, root_z])
            cuboid([0.3, 11.6, snap_lite ? 0.61 : 0.62], anchor = BOT);
}

// Snaps at the chosen cell centres (sparse subset or every cell).
module grid_snaps() {
    for (i = snap_col_idx, j = snap_row_idx)
        translate([(i + 0.5) * snap_pitch, (j + 0.5) * snap_pitch, 0])
            welded_snap();
}

// === openConnect receivers (mount_type = "openconnect") ===
//
// A native openConnect connector receiver, one per cell, cut into the
// back (z=0) face. Dimensions are the authoritative openConnect spec
// (mitufy, CC-BY 4.0 — see LICENSING); modelled NATIVELY rather than
// vendoring the reference generator, which needs BOSL2 struct/newer-trig
// features our pinned BOSL2 lacks and leans on hull()/diff() that trip
// the wasm CGAL path this model is built to avoid (st-7x7/st-560).
//
// Geometry: a dovetail T-slot running along Y. Its X-Z cross-section is a
// narrow mouth (oc_mouth_w) at the back face widening at 45 degrees to a
// wide pocket (oc_deep_w) at oc_depth — the openConnect undercut that
// captures a connector head against straight (-Z) pull-out. A full-depth
// rectangular drop-in onramp at the +Y end breaches the face so a
// connector can be dropped in and slid to seat. Built from a single
// polygon linear_extrude plus one cube — no hull, wasm-safe — so all
// per-cell receivers batch into body()'s one cut union (one CGAL diff).
oc_side_cl  = 0.10;   // openConnect slot side clearance (spec)
oc_depth_cl = 0.10;   // openConnect slot depth clearance (spec)
oc_ang      = tan(22.5);           // chamfer-plane trig adjust (spec)
oc_neck_h   = 1.4;                 // OCHEAD middle (neck) height
oc_mouth_h  = 0.6 - oc_ang * oc_side_cl;                // flat at the mouth
oc_deep_h   = 0.6 + oc_ang * oc_side_cl + oc_depth_cl;  // flat at the pocket
oc_depth    = oc_mouth_h + oc_neck_h + oc_deep_h;       // total = 2.70mm
oc_mouth_w  = 14.2 + 2 * oc_side_cl;   // narrow mouth width (X) = 14.4
oc_deep_w   = 17.0 + 2 * oc_side_cl;   // wide pocket width (X)  = 17.2
oc_foot_y   = 10.6 + 2 * oc_side_cl;   // connector footprint depth (Y) = 10.8
oc_move     = 10.6;                    // slide distance to seat (spec)
oc_slot_len = oc_foot_y + oc_move;     // dovetail slot length (Y) = 21.4
oc_ramp_len = oc_foot_y;               // drop-in onramp length (Y)
oc_breach   = 0.6;                     // extend below z=0 for a clean cut

// One receiver at the origin: mouth centred on z=0, cavity into +Z.
module openconnect_receiver() {
    m2 = oc_mouth_w / 2;
    d2 = oc_deep_w / 2;
    z1 = oc_mouth_h;                 // end of the vertical mouth flat
    z2 = oc_mouth_h + oc_neck_h;     // end of the 45-degree neck
    z3 = oc_depth;                   // pocket roof
    // X-Z dovetail cross-section, extruded along Y.
    pts = [[-m2, -oc_breach], [-m2, z1], [-d2, z2], [-d2, z3],
           [ d2, z3], [ d2, z2], [ m2, z1], [ m2, -oc_breach]];
    translate([0, -oc_slot_len / 2, 0])
        rotate([-90, 0, 0]) linear_extrude(oc_slot_len) polygon(pts);
    // Full-depth drop-in onramp at the +Y end.
    translate([-d2, oc_slot_len / 2 - oc_ramp_len, -oc_breach])
        cube([oc_deep_w, oc_ramp_len, z3 + oc_breach]);
}

// One receiver in every cell centre (mirrors the dense snap layout).
module openconnect_receivers() {
    for (i = [0 : grid_cols - 1], j = [0 : grid_rows - 1])
        translate([(i + 0.5) * snap_pitch, (j + 0.5) * snap_pitch, 0])
            openconnect_receiver();
}

// === Body ===
// Frame: x in [0, body_w], y in [0, body_d], z = 0 at the back face.
// Built here in the body's own frame, then lifted onto the snap tops.
//
// Each pocket FAMILY is cut as ONE solid — a single 2D union of all its
// footprints, extruded once and subtracted once — not one CSG operation
// per pocket. As ~77 sequential 3D differences the 36 slots + 5 figures
// push the CGAL export (the invariants/CI engine) past 5 min; batched
// into three 2D-union tools it lands in the peer-model envelope (the
// Manifold preview/download path is fast either way). No hull-backed
// rounding (BOSL2 cuboid rounding=/edges= trips the wasm CGAL
// applyHull() assertion, st-7x7/st-560): every footprint is a 2D
// rect(rounding=) / circle.

// 2D union of every cartridge footprint — the through-pocket bores.
module cartridge_pockets_2d() {
    for (i = [0 : n_slot_cols - 1], j = [0 : n_slot_rows - 1])
        translate([slot_x0 + i * slot_col_pitch,
                   slot_y0 + j * slot_row_pitch])
            rect([slot_w, slot_l], rounding = slot_corner_r);
}

// One figure silhouette in the (x, z) plane at column xc: a straight-
// walled rectangle capped by a half-circle dome, flat side down at
// floor_z, clipped at floor_z so the dome's lower half never eats the
// floor.
module figure_profile(xc) {
    intersection() {
        union() {
            translate([xc, floor_z + fig_rect_h / 2])
                square([fig_w, fig_rect_h], center = true);
            translate([xc, floor_z + fig_rect_h])
                circle(r = fig_r);
        }
        translate([xc, floor_z + 500])
            square([1000, 1000], center = true);   // keep z >= floor_z
    }
}

// 2D union of every figure silhouette (bored into the +Y face together).
module figure_profiles_2d() {
    for (k = [0 : n_figs - 1])
        figure_profile(fig_x0 + k * fig_pitch);
}

// Top-face (+Z) edge round-over — a hull-free quarter-round FILLET. A true
// BOSL2 rounding=/edges= fillet needs hull, which trips the wasm CGAL
// applyHull() assertion (st-7x7/st-560), and a per-slot tapered frustum
// can't be batched — so we approximate the arc with a stack of 2D-`offset`
// layers whose inset follows a quarter circle. It's the up-facing surface
// so there is no overhang. Both families are stacks of 2D-offset layers,
// added to body()'s single cut union so they stay ONE CGAL difference
// (pst-93r item 4). The small default footprint keeps the step count cheap
// in the wasm sweep.
//
// The layers are sampled at even ANGULAR steps around the arc, NOT at even
// heights (pst-d3x). Equal-height slabs of a fillet that meets the top face
// tangentially leave a wide flat SHELF at the very top — where the curve is
// near-horizontal a tiny height change is a large inset change — which
// reads as a stepped/chamfered top. Equal-angle steps stay thin in height
// near the top (where the inset moves fast) and thin in inset near the foot
// (where the height moves fast), so the polygonal error is spread evenly
// and the profile reads as a genuine smooth curve at preview + in renders.
n_top_steps = max(24, ceil(top_round / 0.05));   // even-angle layers; >=24
// Layer boundary k (0-based) maps to arc angle theta in [0, 90]:
//   theta = 90 * k / n         (0 at the fillet foot, 90 at the top face)
//   z(k)  = body_h - R + R*sin(theta)     boundary height on the arc
//   off(k)= R * (1 - cos(theta_of_layer_top))   inset at the slab's top
// Using the inset at the slab TOP keeps every layer inside the ideal arc.
function _round_theta(k) = 90 * k / n_top_steps;
function _round_z(k)     = body_h - top_round + top_round * sin(_round_theta(k));
function _round_off(k)    = top_round * (1 - cos(_round_theta(k + 1)));

// Outer top perimeter: remove a margin that widens toward the top face
// along the quarter-round arc, so the sharp top-outer edge becomes a
// smooth rounded fillet all round (rounded body corners included —
// `offset` insets them uniformly).
module top_outer_roundover() {
    if (top_round > 0)
        for (k = [0 : n_top_steps - 1]) {
            off = _round_off(k);            // arc inset, widest at the top
            z0  = _round_z(k);
            th  = _round_z(k + 1) - z0 + 0.02;
            translate([0, 0, z0])
                linear_extrude(th)
                    difference() {
                        translate([body_w / 2, body_d / 2])
                            square([body_w + 2, body_d + 2], center = true);
                        translate([body_w / 2, body_d / 2])
                            offset(-off) rect([body_w, body_d],
                                              rounding = body_corner_r);
                    }
        }
}

// Cartridge slot rims: widen each straight-walled opening toward the top
// face along the same quarter-round arc, so the slot rim gets the matching
// rounded fillet (outward `offset` of the batched 2D slot union).
module slot_rim_roundover() {
    if (top_round > 0)
        for (k = [0 : n_top_steps - 1]) {
            off = _round_off(k);            // arc inset, widest at the top
            z0  = _round_z(k);
            th  = _round_z(k + 1) - z0 + 0.02;
            translate([0, 0, z0])
                linear_extrude(th)
                    offset(off) cartridge_pockets_2d();
        }
}

module body() {
    eps = 0.1;
    difference() {
        linear_extrude(body_h)
            translate([body_w / 2, body_d / 2])
                rect([body_w, body_d], rounding = body_corner_r);
        union() {
            translate([0, 0, slot_bottom - eps])
                linear_extrude(body_h - slot_bottom + 2 * eps)
                    cartridge_pockets_2d();
            translate([0, body_d + eps, 0])
                rotate([90, 0, 0])
                    linear_extrude(fig_depth + eps)
                        figure_profiles_2d();
            top_outer_roundover();
            slot_rim_roundover();
            // openConnect receivers cut into the back (z=0..2.7), well
            // clear of the cartridge floors (z>=floor_z=5). Batched into
            // this same cut union so they stay one CGAL difference.
            if (mount_type == "openconnect") openconnect_receivers();
        }
    }
}

translate([0, 0, body_lift]) body();
if (mount_type == "opengrid") grid_snaps();
