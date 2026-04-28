// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Sean O'Connor
//
// Parametric Gridfinity bin for the standard 42mm grid (st-7hq).
//
// Thin wrapper around kennetek/gridfinity-rebuilt-openscad v2.0.0 that
// exposes the ~95% set of knobs real users care about, named so that
// stuff's left-rail param editor reads naturally. The library has
// dozens more internal toggles; keeping this small is intentional —
// adding one more is a one-line follow-up bead, removing one we
// shipped is not.
//
// Drops onto any standard 42mm Gridfinity baseplate. Footprint is
// grid_x × grid_y × 42mm; height is height_units × 7mm + a stacking
// lip the library adds (~3.55mm, no impact on stack pitch).
//
// Wrapper-to-library parameter mapping:
//   grid_x          -> gridx
//   grid_y          -> gridy
//   height_units    -> gridz             (gridz_define=0: 7mm increments,
//                                          excludes stacking lip)
//   divisions_x     -> divx              (compartments along X)
//   divisions_y     -> divy              (compartments along Y)
//   enable_scoop    -> scoop             (1.0 if true, 0 if false)
//   enable_label_tab -> style_tab        (1=Auto if true, 5=None if false)
//   magnet_holes    -> magnet_holes      (refined_holes auto-disabled when on
//                                          — the library asserts they're
//                                          mutually exclusive)
//   screw_holes     -> screw_holes
//   wall_thickness  -> d_wall            (override the spec constant from
//                                          standard.scad — last-write-wins)

include <gridfinity-rebuilt-openscad/src/core/standard.scad>
use <gridfinity-rebuilt-openscad/src/core/gridfinity-rebuilt-utility.scad>
use <gridfinity-rebuilt-openscad/src/core/gridfinity-rebuilt-holes.scad>
use <gridfinity-rebuilt-openscad/src/core/bin.scad>
use <gridfinity-rebuilt-openscad/src/core/cutouts.scad>

$fa = 4;
$fs = 0.25;

// === User-tunable parameters ===
grid_x           = 1;     // @param integer min=1 max=6 group=footprint label="Grid X (cells)"
grid_y           = 1;     // @param integer min=1 max=6 group=footprint label="Grid Y (cells)"
height_units     = 3;     // @param integer min=2 max=8 group=footprint label="Height (7mm units)"

divisions_x      = 1;     // @param integer min=1 max=6 group=compartments label="Divisions X"
divisions_y      = 1;     // @param integer min=1 max=6 group=compartments label="Divisions Y"

enable_scoop     = true;  // @param boolean group=compartments label="Front scoop"
enable_label_tab = true;  // @param boolean group=compartments label="Label tab"

magnet_holes     = false; // @param boolean group=base label="6mm magnet sockets"
screw_holes      = false; // @param boolean group=base label="M3 screw holes (needs magnets)"

// d_wall = 0.95 is the gridfinity-rebuilt stock; reassigning here
// overrides the value pulled in from standard.scad above.
wall_thickness   = 0.95;  // @param number min=0.6 max=3 step=0.05 unit=mm group=walls label="Wall thickness"

// === Library overrides ===
// d_wall comes from standard.scad; redeclaring after the include
// makes wall_thickness the effective value everywhere downstream.
d_wall = wall_thickness;

// === Implementation ===
// Refined-hole pattern conflicts with magnet_holes (the library
// asserts !(refined && magnet)). Drop refined when magnets are on.
hole_options = bundle_hole_options(
    refined_holes = !magnet_holes,
    magnet_holes  = magnet_holes,
    screw_holes   = screw_holes
);

bin = new_bin(
    grid_size     = [grid_x, grid_y],
    height_mm     = height(height_units, 0, false),
    include_lip   = true,
    hole_options  = hole_options
);

bin_render(bin) {
    bin_subdivide(bin, [divisions_x, divisions_y]) {
        cut_compartment_auto(
            cgs(),
            enable_label_tab ? 1 : 5,
            false,
            enable_scoop ? 1 : 0
        );
    }
}

// PRINT_ANCHOR_BBOX at defaults (1×1×3U).
// X/Y: 41.5mm — Gridfinity's spec'd 0.5mm slip clearance below the
// 42mm grid pitch (so bins drop into baseplates without binding).
// Z: 7mm * 3 (gridz_define=0) + library stacking-lip height
// (~3.55mm per the gridfinity-rebuilt-bins.scad header note).
PRINT_ANCHOR_BBOX = [41.5, 41.5, 24.55];
