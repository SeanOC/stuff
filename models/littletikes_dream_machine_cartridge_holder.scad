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
// The DEFAULT/preview footprint is a compact 3x3-cell tile (84 x 84mm) —
// intentionally small so the wasm param-sweep stays inside CI's per-shard
// budget (every sweep case renders from these defaults; a dense one-per-
// cell default at the full 9x8 size blew a 45min shard, pst-93r). It is a
// real, printable tile that still exercises every feature (packs 3
// cartridge slots + 1 figure holder + 9 snaps). Scale grid_cols/grid_rows
// up to 9x8 for the full ~250 x 235mm reference holder.
// Two families of pockets AUTO-FILL the derived
// footprint — their counts are computed from the available space and the
// feature pitch, never hard-coded, so they follow the grid size:
//
//   * CARTRIDGE SLOTS open on the +Z top face: rounded rectangular
//     pockets (51 x 14mm interior) on a 60mm column / 22mm row pitch,
//     with a widened drop-in mouth. Rows pack into the depth left AFTER
//     the front figure strip is reserved, so they never overlap it at
//     any grid size. Default 3x3 footprint packs 1 x 3 = 3 (a full 9x8
//     packs 4 x 9 = 36).
//   * FIGURE HOLDERS open on the +Y front face: a rectangle capped by a
//     half-circle dome (43mm wide, 21.5mm radius), 10mm deep, on a
//     ~49mm pitch. Default 3x3 footprint packs 1 (a full 9x8 packs 5).
//     Each is a closed BLIND
//     pocket: the packer keeps a fig_floor (2mm) solid floor behind it,
//     so it never breaks through into the cartridge slot behind.
//
// All +Z (top) face edges — the outer perimeter and every cartridge slot
// mouth rim — get a top_round round-over (a hull-free stepped chamfer;
// up-facing so no overhang). See top_outer_roundover / slot_mouth_roundover.
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
// sell prints or files.
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

// ----- openGrid size (primary: whole 28mm cells) -----
grid_cols = 3;      // @param integer min=3 max=9 step=1 group=grid label="Width (28mm openGrid cells)"
grid_rows = 3;      // @param integer min=3 max=9 step=1 group=grid label="Height (28mm openGrid cells)"
snap_lite = true;   // @param boolean group=grid label="Lite snaps (3.4mm instead of 6.8mm)"
body_h    = 41;     // @param number min=38 max=55 step=1 unit=mm group=grid label="Body depth out from the wall (Z)"
body_corner_r = 3;  // @param number min=0.5 max=8 step=0.5 unit=mm group=grid label="Body vertical-corner radius"
// Default TRUE: one lite snap per cell (grid_cols x grid_rows), the
// original spec's max-hold layout. This makes the wasm/browser preview
// heavier and the desktop CGAL export slower the larger the grid gets
// (a full 9x8 is a 72-snap union), but preview perf is not a blocker
// (the wasm path is preview-only, not export) and the CGAL export still
// lands inside CI's budget (pst-93r). The default 3x3 tile is only 9
// snaps, so the preview and the whole param-sweep stay light.
// Set FALSE for a sparse, still-cell-aligned subset (snap_sparse_cols x
// snap_sparse_rows, evenly spread and corner-inclusive) that holds a
// tray firmly and exports far faster (~45s with the batched pocket cuts).
snap_every_cell = true; // @param boolean group=grid label="Snap in every cell (one per cell; default)"

// ----- Cartridge slots (open on +Z top; counts auto-fill) -----
slot_w         = 51;  // @param number min=30 max=56 step=0.5 unit=mm group=cartridge label="Cartridge slot width (X)"
slot_l         = 14;  // @param number min=8 max=19 step=0.5 unit=mm group=cartridge label="Cartridge slot length (Y)"
slot_depth     = 36;  // @param number min=10 max=40 step=1 unit=mm group=cartridge label="Cartridge slot depth"
floor_z        = 5;   // @param number min=2 max=8 step=0.5 unit=mm group=cartridge label="Pocket floor height above the back"
slot_col_pitch = 60;  // @param number min=54 max=90 step=0.5 unit=mm group=cartridge label="Slot column pitch (X)"
slot_row_pitch = 22;  // @param number min=18 max=40 step=0.5 unit=mm group=cartridge label="Slot row pitch (Y)"
slot_corner_r  = 2;   // @param number min=0.5 max=6 step=0.5 unit=mm group=cartridge label="Slot corner radius"
slot_mouth     = 2;   // @param number min=0 max=5 step=0.5 unit=mm group=cartridge label="Drop-in mouth widening (each dim)"
top_round      = 1.2; // @param number min=0 max=3 step=0.2 unit=mm group=cartridge label="Top-edge round-over (outer rim + slot mouths; 0=off)"

// ----- Figure holders (open on +Y front; count auto-fills) -----
fig_w      = 43;    // @param number min=24 max=46 step=0.5 unit=mm group=figures label="Figure pocket width (dome dia.)"
fig_rect_h = 9;     // @param number min=3 max=13 step=0.5 unit=mm group=figures label="Figure straight-wall height"
fig_depth  = 10;    // @param number min=5 max=18 step=0.5 unit=mm group=figures label="Figure pocket depth into front"
fig_pitch  = 49.25; // @param number min=47 max=90 step=0.25 unit=mm group=figures label="Figure pocket pitch (X)"

// @preset id="default" label="Default (3x3 tile, one snap per cell)" grid_cols=3 grid_rows=3 snap_lite=true snap_every_cell=true
// @preset id="full_holder" label="Full holder (9x8 cells)" grid_cols=9 grid_rows=8 snap_lite=true snap_every_cell=true
// @preset id="sparse_snaps" label="Sparse snaps (faster CGAL export)" snap_every_cell=false

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed of snap tops into the back face (st-v7k)
body_lift  = snap_h - weld;

// Footprint derives from the cell count: an exact integer openGrid grid,
// so snaps land on cell centres and the back face is a clean N x M grid.
//   default 3x3: 3 * 28 = 84 (X) by 3 * 28 = 84 (Y) — a compact preview
//   tile. The full holder (9x8) is 252 x 224mm, the closest whole-cell
//   match to the measured ~250 x 235mm reference part.
body_w = grid_cols * snap_pitch;
body_d = grid_rows * snap_pitch;

// Cartridge slots auto-fill: as many 51x14 pockets as fit at the column/
// row pitch, then centred with even edge margins. The +Y front figure
// strip (fig_depth deep) plus a solid floor behind each figure pocket is
// RESERVED FIRST, so rows pack only into the remaining depth cart_depth
// and never break through into the figure pockets at any grid/param
// (pst-93r items 1+3). The reservation also subtracts the drop-in
// mouth's extra half-width, so even the WIDEST cartridge cut stays
// >= fig_floor clear of the figure pockets. Counts follow the footprint
// (default 3x3 = 1 x 3 = 3; a full 9x8 = 4 x 9 = 36).
fig_floor = 2;   // solid floor (mm) kept behind each figure pocket
cart_depth = body_d - fig_depth - fig_floor - slot_mouth / 2;
n_slot_cols = max(0, floor((body_w - slot_w) / slot_col_pitch) + 1);
n_slot_rows = max(0, floor((cart_depth - slot_l) / slot_row_pitch) + 1);
slot_x0 = (body_w - (n_slot_cols - 1) * slot_col_pitch) / 2;  // first col centre
slot_y0 = (cart_depth - (n_slot_rows - 1) * slot_row_pitch) / 2;  // first row centre
// Slot floor clamps up if the body is too shallow for the full depth, so
// the pocket never punches through the back (keeps param sweeps valid).
slot_bottom = max(floor_z, body_h - slot_depth);
slot_mouth_h = 3;   // flared mouth spans the top 3mm

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
// fails on >1mm drift from the exported STL). Default is the 3x3 tile:
//   X = body_w    = 3 * 28              = 84
//   Y = body_d    = 3 * 28              = 84
//   Z = body_lift + body_h = 3.4 - 0.02 + 41 = 44.38
PRINT_ANCHOR_BBOX = [84, 84, 44.38];

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

// 2D union of the widened mouths, cut over the top slot_mouth_h only:
// each slot gets a recessed drop-in lip (slot_mouth wider all round). A
// step, not a taper — a per-slot tapered frustum can't be batched into
// one 2D tool (linear_extrude scale pulls every footprint toward the
// origin), and 40 separate frusta are exactly what made CGAL choke.
module cartridge_mouths_2d() {
    for (i = [0 : n_slot_cols - 1], j = [0 : n_slot_rows - 1])
        translate([slot_x0 + i * slot_col_pitch,
                   slot_y0 + j * slot_row_pitch])
            rect([slot_w + slot_mouth, slot_l + slot_mouth],
                 rounding = slot_corner_r);
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

// Top-face (+Z) edge round-over — a hull-free STEPPED chamfer (the
// batchable stand-in; a true fillet needs hull, and a per-slot tapered
// frustum can't be batched — same reason the drop-in mouth is a step).
// It's the up-facing surface so there is no overhang. Both families are
// stacks of 2D-`offset` layers, added to body()'s single cut union so
// they stay ONE CGAL difference (pst-93r item 4). n_top_steps keeps the
// step ~0.4mm so a 1.2mm round-over is 3 barely-visible facets.
n_top_steps = max(1, round(top_round / 0.4));

// Outer top perimeter: remove a margin that widens toward the top face,
// so the sharp top-outer edge becomes a ~45deg bevel all round (rounded
// body corners included — `offset` insets them uniformly).
module top_outer_roundover() {
    if (top_round > 0)
        for (k = [0 : n_top_steps - 1]) {
            off = top_round * (k + 1) / n_top_steps;   // widest at the top
            translate([0, 0, body_h - top_round + k * top_round / n_top_steps])
                linear_extrude(top_round / n_top_steps + 0.02)
                    difference() {
                        translate([body_w / 2, body_d / 2])
                            square([body_w + 2, body_d + 2], center = true);
                        translate([body_w / 2, body_d / 2])
                            offset(-off) rect([body_w, body_d],
                                              rounding = body_corner_r);
                    }
        }
}

// Cartridge slot mouths: widen each opening toward the top face, so the
// slot rim gets the same bevel (offset of the batched 2D mouth union).
module slot_mouth_roundover() {
    if (top_round > 0)
        for (k = [0 : n_top_steps - 1]) {
            off = top_round * (k + 1) / n_top_steps;   // widest at the top
            translate([0, 0, body_h - top_round + k * top_round / n_top_steps])
                linear_extrude(top_round / n_top_steps + 0.02)
                    offset(off) cartridge_mouths_2d();
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
            if (slot_mouth > 0)
                translate([0, 0, body_h - slot_mouth_h])
                    linear_extrude(slot_mouth_h + eps)
                        cartridge_mouths_2d();
            translate([0, body_d + eps, 0])
                rotate([90, 0, 0])
                    linear_extrude(fig_depth + eps)
                        figure_profiles_2d();
            top_outer_roundover();
            slot_mouth_roundover();
        }
    }
}

translate([0, 0, body_lift]) body();
grid_snaps();
