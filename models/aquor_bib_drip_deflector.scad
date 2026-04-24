// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Aquor hose-bib drip deflector — bent sheet-metal form (st-r38).
//
// One continuous plate of uniform thickness, smoothly bent from a
// horizontal VHB tab to a down-angled flap. In install orientation
// the tab's top face is VHB-taped to the Aquor face-plate underside;
// the flap hangs outward-and-downward past the wall plane so drain
// water sheds off its front edge clear of the drywall below.
//
// Two geometric features beyond the raw L-shape:
//
//   1. **Smooth bend.** The tab→flap junction is a filleted corner
//      with outer radius `bend_radius`. The plate reads as a single
//      bent shape, not two rectangles butted together — sheet-metal
//      language, not layered-cake language.
//
//   2. **Concave top contour.** The flap's top surface is dished
//      across its width with `contour_depth` of concavity at the
//      centerline and `contour_side_rim_width`-wide rims at the
//      edges. Water landing anywhere on the flap rolls toward the
//      centerline and sheds from the front edge at a single drip
//      point rather than a line.
//
// Construction — polygon side profile + linear_extrude + cylinder
// subtract:
//
//   * A 2D polygon in Y-Z describes the bent plate's side view. Two
//     concentric arcs (outer radius `bend_radius`, inner radius
//     `bend_radius - plate_thickness`) share a center directly above
//     the tab's front edge and sweep `flap_angle`. Tab + flap
//     straights complete the closed profile.
//   * `linear_extrude` extends that profile by `width` along X
//     (transformed via rotate([90,0,90]) so the polygon's local X/Y
//     map to global Y/Z and the extrude axis becomes global X).
//   * A long cylinder oriented along the flap's length axis is
//     subtracted from the top of the flap. Its radius is chosen so
//     the cylinder's intersection with the flap's top plane spans
//     exactly `width - 2*contour_side_rim_width`, dishing the
//     centerline by `contour_depth`.
//
// Install orientation:
//   +Y = outward from wall; +Z = up; +X = along bib width.
//   Flip the printed part top-to-bottom for install: the printed-
//   bed-facing tab surface becomes the VHB zone pressed UP against
//   the bib underside; the flap hangs DOWN-and-outward at
//   `flap_angle` below horizontal.
//
// Print orientation (how this file models the part):
//   Tab lies flat on the build plate, Z = [0, plate_thickness].
//   Flap rises at `flap_angle` above horizontal from the bend. First-
//   layer contact = width × tab_depth = 680 mm² at defaults, plenty
//   for adhesion. The flap's bed-facing underside has ~1.28× overhang
//   per layer at 38° — above the classic 45°-from-vertical threshold
//   but manageable for a thin, short plate. Drop flap_angle to 45°+
//   if a cleaner underside finish is needed.

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Bib reference (drives defaults; not printed) -----
bib_plate_width  = 72;   // @param number min=60 max=90  step=0.5 unit=mm  group=bib label="Aquor face-plate width"
bib_plate_height = 100;  // @param number min=80 max=120 step=0.5 unit=mm  group=bib label="Aquor face-plate height"

// ----- Part geometry -----
width           = 68;   // @param number min=40 max=90  step=0.5 unit=mm  group=geometry label="Part width (X)"
tab_depth       = 10;   // @param number min=5  max=30  step=0.5 unit=mm  group=geometry label="VHB tab depth (Y)"
flap_length     = 32;   // @param number min=15 max=60  step=0.5 unit=mm  group=geometry label="Flap length (along the plate)"
flap_angle      = 38;   // @param number min=15 max=60  step=1   unit=deg group=geometry label="Flap angle above horizontal"
plate_thickness = 2.5;  // @param number min=1.5 max=4   step=0.25 unit=mm group=geometry label="Plate thickness (uniform)"

// ----- Bend -----
bend_radius     = 6;    // @param number min=3  max=12  step=0.5 unit=mm  group=shape label="Outer bend radius"

// ----- Top contour (concave dish on the flap) -----
contour_depth         = 1.5; // @param number min=0   max=3   step=0.25 unit=mm group=shape label="Contour dish depth at centerline"
contour_side_rim_width = 1.5; // @param number min=0.5 max=8   step=0.25 unit=mm group=shape label="Raised side-rim width on the flap top"

// === Derived ===

_fa = flap_angle;
_t  = plate_thickness;
_R  = bend_radius;                 // outer bend radius
_Ri = bend_radius - plate_thickness; // inner bend radius

// Dish cylinder radius. The cylinder is tangent to the flap top at
// the rim edges (X = ±(width/2 - rim)) and sinks `contour_depth` at
// the centerline. From chord geometry:
//   2·Rd·d = ((w/2 − rim)² + d²)  ⇒  Rd = [(w/2 − rim)² + d²] / (2d).
_dish_half_chord = max(width / 2 - contour_side_rim_width, 0.1);
_Rd = contour_depth > 0
    ? (_dish_half_chord * _dish_half_chord + contour_depth * contour_depth) / (2 * contour_depth)
    : 0;

// Outer-arc endpoint (where the flap's bed-facing surface starts).
_outer_end_y = tab_depth + _R * sin(_fa);
_outer_end_z = _R * (1 - cos(_fa));

// Inner-arc endpoint (where the flap's top surface starts).
_inner_end_y = tab_depth + _Ri * sin(_fa);
_inner_end_z = _R - _Ri * cos(_fa);

// Flap midline-at-hinge (for transforming the dish cutter).
_midline_hinge_y = (_outer_end_y + _inner_end_y) / 2;
_midline_hinge_z = (_outer_end_z + _inner_end_z) / 2;

// Flap far corners along its length direction.
_flap_outer_tip = [_outer_end_y + flap_length * cos(_fa),
                   _outer_end_z + flap_length * sin(_fa)];
_flap_inner_tip = [_flap_outer_tip[0] - _t * sin(_fa),
                   _flap_outer_tip[1] + _t * cos(_fa)];
_inner_arc_exit = [_inner_end_y + flap_length * cos(_fa),
                   _inner_end_z + flap_length * sin(_fa)];

// PRINT_ANCHOR_BBOX at defaults. Measured from the rendered STL;
// recomputed whenever the bend or flap params shift materially.
PRINT_ANCHOR_BBOX = [68, 38.91, 22.94];

// @preset id="aquor-72x100" label="Aquor 72×100mm (default)" bib_plate_width=72 bib_plate_height=100 width=68 tab_depth=10 flap_length=32 flap_angle=38 plate_thickness=2.5 bend_radius=6 contour_depth=1.5 contour_side_rim_width=1.5

// === Geometry ===

// 2D side profile in the polygon's (x,y) — which we map to the part's
// (Y,Z) via the outer rotate([90,0,90]). Walks CCW starting from the
// tab-back-bottom corner.
function _arc_samples(cx, cy, r, a0, a1, n) = [
    for (i = [0:n]) let(t = a0 + (a1 - a0) * i / n)
        [cx + r * cos(t), cy + r * sin(t)]
];

module _side_profile() {
    // Arc center sits directly above tab's front edge at Z = R
    // (perpendicular distance from the tab bottom).
    cx = tab_depth;
    cy = _R;
    a_start = 270;               // outer arc starts at (cx, cy - R) = (tab_depth, 0)
    a_end   = 270 + _fa;         // sweep by flap_angle CCW
    n       = 16;
    outer_arc = _arc_samples(cx, cy, _R, a_start, a_end, n);
    // Inner arc traversed in reverse so the closed polygon stays CCW.
    inner_arc = _arc_samples(cx, cy, _Ri, a_end, a_start, n);
    polygon(concat(
        [[0, 0], [tab_depth, 0]],
        outer_arc,
        [_flap_outer_tip, _flap_inner_tip, _inner_arc_exit],
        inner_arc,
        [[tab_depth, _t], [0, _t]]
    ));
}

module _bent_plate_solid() {
    // polygon's x/y → global Y/Z via rotate([90,0,90]); linear_extrude
    // Z-axis becomes global X after the same rotation. Centre in X.
    translate([-width / 2, 0, 0])
        rotate([90, 0, 90])
            linear_extrude(width)
                _side_profile();
}

// Dish cutter — a cylinder whose axis lies along the flap's length
// direction, centred side-to-side (X=0). Its intersection with the
// flap's top surface produces a circular-segment groove spanning
// (width - 2·rim) wide × contour_depth deep at centerline. The
// cylinder extends past both ends of the flap so the groove runs the
// full flap length without end caps.
module _contour_cutter() {
    // Forward slack pushes the cutter past the flap tip so the
    // groove exits cleanly off the front edge. No slack on the
    // hinge end — extending the cutter into the bend arc would
    // split the bent plate into two components (the cylinder's
    // straight axis doesn't follow the curve).
    slack_front = 6;
    cutter_len  = flap_length + slack_front;
    // Axis offset from the flap midline in flap-local +Z: t/2
    // brings the axis to the top surface, then +(Rd − depth)
    // lifts it so the cylinder's underside dips contour_depth
    // into the plate at the centerline.
    axis_local_z = _t / 2 + _Rd - contour_depth;
    translate([0, _midline_hinge_y, _midline_hinge_z])
        rotate([_fa, 0, 0])
            translate([0, cutter_len / 2, axis_local_z])
                // Default cylinder is along +Z; rotate −90° around X
                // to align its axis with local +Y (the flap's length).
                rotate([-90, 0, 0])
                    cylinder(h = cutter_len, r = _Rd, center = true);
}

module aquor_bib_drip_deflector() {
    if (contour_depth > 0 && _Rd > 0) {
        difference() {
            _bent_plate_solid();
            _contour_cutter();
        }
    } else {
        _bent_plate_solid();
    }
}

aquor_bib_drip_deflector();
