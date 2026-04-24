// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Aquor hose-bib drip deflector — bent sheet-metal form (st-r38,
// revised st-if3). One continuous plate of uniform thickness,
// smoothly bent from a horizontal VHB tab to a down-angled flap. In
// install orientation the tab's top face is VHB-taped to the Aquor
// face-plate underside; the flap hangs outward-and-downward past
// the wall plane so drain water sheds off its front edge clear of
// the drywall below.
//
// Three geometric features on top of the raw L-shape:
//
//   1. **Large-radius bend.** The tab→flap junction is a filleted
//      corner with outer radius `bend_radius` (default 12 mm at the
//      bib size). Larger radius stretches the transition arc long
//      enough that the preview reads as a smooth bend, not a visible
//      fold line.
//
//   2. **Rounded rear tab corners** matching the Aquor face-plate's
//      rounded-rectangle bottom edge. `bib_corner_radius` is measured
//      against the 72×100 mm face plate (≈ 9 mm). When installed
//      against the bib's curves, the tab's corners don't protrude
//      past the plate outline.
//
//   3. **Concave top contour.** The flap's top surface is dished
//      across its width with `contour_depth` of concavity at the
//      centerline and `contour_side_rim_width`-wide raised rims on
//      the long edges. Water landing anywhere on the flap rolls
//      toward the centerline and sheds from the front edge at a
//      single drip point.
//
// Construction — polygon side profile + linear_extrude + two
// boolean subtracts:
//
//   * A 2D polygon in Y-Z describes the bent plate's side view.
//     Concentric arcs (outer radius `bend_radius`, inner radius
//     `bend_radius - plate_thickness`) share a center directly above
//     the tab's front edge and sweep `flap_angle`. Tab + flap
//     straights close the profile.
//   * `linear_extrude` + `rotate([90,0,90])` extends that profile by
//     `width` along global X.
//   * A long cylinder aligned with the flap's length axis is
//     subtracted from the flap top to create the V-groove. Radius
//     is chosen so the intersection spans exactly
//     `width - 2·contour_side_rim_width` and dishes `contour_depth`
//     at the centerline.
//   * Two "anti-round" prisms are subtracted at the tab's rear
//     corners to carve the `bib_corner_radius` fillets. The corner
//     cutter = a corner-cube minus a vertical quarter-cylinder at
//     each rear corner.
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
//   layer contact area depends on `width × tab_depth` minus the
//   rear-corner roundings (≈ 660 mm² at defaults), plenty for
//   adhesion. The flap's bed-facing underside has ~1.28× overhang
//   per layer at 38° — above the classic 45°-from-vertical threshold
//   but manageable for a thin, short plate. Drop flap_angle to 45°+
//   if a cleaner underside finish is needed.

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Bib reference (drives defaults; not printed) -----
bib_plate_width   = 72;  // @param number min=60 max=90  step=0.5 unit=mm  group=bib label="Aquor face-plate width"
bib_plate_height  = 100; // @param number min=80 max=120 step=0.5 unit=mm  group=bib label="Aquor face-plate height"
bib_corner_radius = 9;   // @param number min=0  max=20  step=0.5 unit=mm  group=bib label="Aquor face-plate corner radius"

// ----- Part geometry -----
width           = 68;   // @param number min=40 max=90  step=0.5 unit=mm  group=geometry label="Part width (X)"
tab_depth       = 10;   // @param number min=5  max=30  step=0.5 unit=mm  group=geometry label="VHB tab depth (Y)"
flap_length     = 32;   // @param number min=15 max=60  step=0.5 unit=mm  group=geometry label="Flap length (along the plate)"
flap_angle      = 38;   // @param number min=15 max=60  step=1   unit=deg group=geometry label="Flap angle above horizontal"
plate_thickness = 2.5;  // @param number min=1.5 max=4   step=0.25 unit=mm group=geometry label="Plate thickness (uniform)"

// ----- Bend -----
bend_radius     = 12;   // @param number min=4  max=20  step=0.5 unit=mm  group=shape label="Outer bend radius"

// ----- Top contour (concave dish on the flap) -----
contour_depth          = 1.5; // @param number min=0   max=3   step=0.25 unit=mm group=shape label="Contour dish depth at centerline"
contour_side_rim_width = 1.5; // @param number min=0.5 max=8   step=0.25 unit=mm group=shape label="Raised side-rim width on the flap top"

// === Derived ===

_fa = flap_angle;
_t  = plate_thickness;
_R  = bend_radius;                   // outer bend radius
_Ri = bend_radius - plate_thickness; // inner bend radius (must stay > 0)

// Dish cylinder radius. Solve chord geometry so the cylinder is
// tangent to the flap top at X = ±(width/2 − rim) and dishes
// `contour_depth` at the centerline:
//   2·Rd·d = (w/2 − rim)² + d²  ⇒  Rd = [(w/2 − rim)² + d²] / (2d).
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
PRINT_ANCHOR_BBOX = [68, 42.6, 24.22];

// @preset id="aquor-72x100" label="Aquor 72×100mm (default)" bib_plate_width=72 bib_plate_height=100 bib_corner_radius=9 width=68 tab_depth=10 flap_length=32 flap_angle=38 plate_thickness=2.5 bend_radius=12 contour_depth=1.5 contour_side_rim_width=1.5

// === Geometry ===

function _arc_samples(cx, cy, r, a0, a1, n) = [
    for (i = [0:n]) let(t = a0 + (a1 - a0) * i / n)
        [cx + r * cos(t), cy + r * sin(t)]
];

// 2D side profile in polygon's (x,y) — mapped to the part's (Y,Z)
// via the outer rotate([90,0,90]). Walks CCW starting from the
// tab-back-bottom corner.
module _side_profile() {
    cx = tab_depth;
    cy = _R;
    a_start = 270;            // outer arc starts at (tab_depth, 0)
    a_end   = 270 + _fa;      // sweep by flap_angle CCW
    n       = 20;
    outer_arc = _arc_samples(cx, cy, _R,  a_start, a_end,   n);
    inner_arc = _arc_samples(cx, cy, _Ri, a_end,   a_start, n);
    polygon(concat(
        [[0, 0], [tab_depth, 0]],
        outer_arc,
        [_flap_outer_tip, _flap_inner_tip, _inner_arc_exit],
        inner_arc,
        [[tab_depth, _t], [0, _t]]
    ));
}

module _bent_plate_solid() {
    translate([-width / 2, 0, 0])
        rotate([90, 0, 90])
            linear_extrude(width)
                _side_profile();
}

// V-groove cutter — a cylinder whose axis lies along the flap's
// length direction, centred side-to-side (X=0). Its intersection
// with the flap top plane produces a circular-segment groove
// spanning (width − 2·rim) wide × contour_depth deep.
module _contour_cutter() {
    // `groove_inset` pushes the cutter's back (hinge-end) cap into
    // the flap so the cap plane never lands inside the bend arc.
    // Without this, a large bend_radius makes the cap face cross
    // the curved bend region and splits the plate into orphan
    // components (the cap's X-Z cross-section and the bend's
    // curving cross-section meet at a knife edge). `slack_front`
    // pushes the cutter past the tip so the groove exits off the
    // front edge cleanly.
    groove_inset = 3;
    slack_front  = 6;
    cutter_len   = flap_length + slack_front - groove_inset;
    axis_local_z = _t / 2 + _Rd - contour_depth;
    translate([0, _midline_hinge_y, _midline_hinge_z])
        rotate([_fa, 0, 0])
            translate([0, groove_inset + cutter_len / 2, axis_local_z])
                rotate([-90, 0, 0])
                    cylinder(h = cutter_len, r = _Rd, center = true);
}

// Anti-round corner cutters for the tab's two rear corners (Y=0
// side). Each cutter removes a corner square MINUS a
// quarter-cylinder, so the subtraction leaves a rounded-rectangle
// rear corner of radius `bib_corner_radius`. Only acts on the tab
// portion (Y < bib_corner_radius); the flap is untouched.
module _rear_corner_cutters() {
    if (bib_corner_radius <= 0) {
        // no-op: let the tab stay sharp-rectangular
    } else {
        R = bib_corner_radius;
        // All cutter extents bump out of the main body by `eps` on
        // every surface that would otherwise be coplanar. Without
        // these offsets OpenSCAD's Manifold backend leaves a
        // zero-thickness artefact at each coplanar face: orphan
        // fragments appear and trimesh fails the watertight check.
        eps = 0.1;
        h = _t + 2 * eps;
        for (sign = [-1, 1]) {
            // Corner cube extended by eps past the part's side face
            // (X = ±width/2) and past the part's back face (Y=0) so
            // the difference() cleaves cleanly rather than sharing a
            // face with the main body.
            x_lo = sign < 0 ? -width / 2 - eps : width / 2 - R;
            cx_cyl = sign * (width / 2 - R);
            difference() {
                translate([x_lo, -eps, -eps])
                    cube([R + eps, R + eps, h]);
                translate([cx_cyl, R, -eps])
                    cylinder(h = h, r = R);
            }
        }
    }
}

module aquor_bib_drip_deflector() {
    difference() {
        _bent_plate_solid();
        if (contour_depth > 0 && _Rd > 0) _contour_cutter();
        _rear_corner_cutters();
    }
}

aquor_bib_drip_deflector();
