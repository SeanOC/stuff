// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Aquor hose-bib drip deflector — bent-plate form factor (st-2ln).
// Two pieces welded at one edge: a small horizontal VHB tab that
// presses against the underside of the Aquor bib face plate, and a
// thin flap that hinges at the tab's outer-top edge and angles
// up-and-outward. Installed upside-down from the printed orientation:
// the tab's top-in-print face bonds to the bib with VHB tape, and the
// flap hangs down-and-outward past the wall plane, shedding drain
// water well clear of the drywall below.
//
// Install orientation (implied by inverting the printed part):
//   tab top (VHB zone) pressed UP against the bib face-plate
//   underside; flap hangs DOWN-AND-OUTWARD at flap_angle below
//   horizontal.
//
// Print orientation (how the file is modelled):
//   +Y = outward from wall (eventual install direction)
//   +Z = up
//   +X = along the bib width
//   Tab lies flat on the build plate, Z = [0, top_thickness]. Flap
//   hinges at the tab's front-top corner (Y = tab_depth,
//   Z = top_thickness) and rises up at flap_angle.
//
// Overhang note: the flap's bed-facing underside sits at flap_angle
// above horizontal. With the default 38°, each print layer overhangs
// its predecessor by ~1.28 × the layer height — above the classic
// 45°-from-vertical "safe" threshold but well within what modern
// printers handle unsupported for a thin, short plate. If a finer
// surface finish matters on the flap's underside, drop flap_angle
// to 45° (the borderline) or add tree supports at slice time.
//
// First-layer contact footprint at defaults: width × tab_depth =
// 68 × 10 = 680 mm². Plenty for adhesion.

$fn = 48;

// === User-tunable parameters ===

// ----- Bib reference (not printed; drives defaults only) -----
bib_plate_width  = 72;  // @param number min=60 max=90  step=0.5 unit=mm  group=bib label="Aquor face-plate width"

// ----- Part geometry -----
width          = 68;    // @param number min=40 max=90  step=0.5 unit=mm  group=geometry label="Part width (X, along bib width)"
tab_depth      = 10;    // @param number min=5  max=30  step=0.5 unit=mm  group=geometry label="VHB tab depth (Y, outward from wall)"
top_thickness  = 2.5;   // @param number min=1.5 max=5 step=0.25 unit=mm group=geometry label="Tab thickness"
flap_thickness = 2.5;   // @param number min=1.5 max=5 step=0.25 unit=mm group=geometry label="Flap thickness"
flap_length    = 32;    // @param number min=15 max=60  step=0.5 unit=mm  group=geometry label="Flap length (along the plate)"
flap_angle     = 38;    // @param number min=15 max=60  step=1   unit=deg group=geometry label="Flap angle above horizontal (print-orientation)"
corner_radius  = 0;     // @param number min=0  max=3   step=0.25 unit=mm group=finish label="Exposed-edge fillet (0 = sharp; minkowski cost rises quickly)"

// ----- Derived (for the PRINT_ANCHOR_BBOX comment + the preset) -----
flap_far_y    = tab_depth + flap_length * cos(flap_angle);
flap_far_z    = top_thickness + flap_length * sin(flap_angle) + flap_thickness * cos(flap_angle);

// PRINT_ANCHOR_BBOX at defaults. Measured from the rendered STL
// (OpenSCAD + trimesh): extents 68 × 35.22 × 24.17 mm before any
// corner_radius minkowski expansion. Kept sub-mm precise so the
// 1 mm invariant tolerance absorbs only real drift.
PRINT_ANCHOR_BBOX = [68, 35.22, 24.17];

// @preset id="aquor-72x100" label="Aquor 72×100mm (default)" bib_plate_width=72 width=68 tab_depth=10 top_thickness=2.5 flap_thickness=2.5 flap_length=32 flap_angle=38 corner_radius=0

// === Geometry ===

module aquor_bib_drip_deflector_body() {
    // Tab: horizontal plate, flat on the print bed.
    translate([-width / 2, 0, 0])
        cube([width, tab_depth, top_thickness]);

    // Flap: hinges at the tab's front-top corner. The rotate()
    // about +X by flap_angle lifts the flap's +Y end upward while
    // the back-bottom edge (pre-rotate origin) stays anchored. The
    // 0.5 mm pre-rotate overlap into the tab-side guarantees a
    // solid boolean union at the hinge; without it the two cubes
    // share only a line, which OpenSCAD's Manifold backend accepts
    // but trimesh's STL-based watertight check refuses.
    HINGE_OVERLAP = 0.5;
    translate([0, tab_depth, top_thickness])
        rotate([flap_angle, 0, 0])
            translate([-width / 2, -HINGE_OVERLAP, 0])
                cube([width, flap_length + HINGE_OVERLAP, flap_thickness]);
}

module aquor_bib_drip_deflector() {
    if (corner_radius > 0) {
        // Minkowski with a small sphere rounds every exposed edge
        // at once. Expensive — facets multiply — so keep the
        // radius small and $fn modest.
        minkowski() {
            aquor_bib_drip_deflector_body();
            sphere(r = corner_radius);
        }
    } else {
        aquor_bib_drip_deflector_body();
    }
}

aquor_bib_drip_deflector();
