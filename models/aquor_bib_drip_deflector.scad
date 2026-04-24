// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Aquor hose-bib drip deflector — bent sheet-metal form (st-r38,
// revised st-if3, revised again st-hkn). One continuous plate of
// uniform thickness, smoothly bent from a horizontal VHB tab to a
// down-angled flap. In install orientation the tab's top face is
// VHB-taped to the Aquor face-plate underside; the flap hangs
// outward-and-downward past the wall plane so drain water sheds off
// its front edge clear of the drywall below.
//
// Four geometric features on top of the raw L-shape:
//
//   1. **Large-radius bend.** Tab→flap junction is a filleted corner
//      (outer radius `bend_radius`, default 12 mm at the bib size).
//      Longer arc smooths the transition — it reads as a continuous
//      bend, not a fold line.
//
//   2. **Rounded rear tab corners** matching the Aquor face-plate's
//      rounded-rectangle bottom edge (`bib_corner_radius`).
//
//   3. **Bib-bottom recess** in the tab's top-rear region (st-hkn).
//      A rounded-rectangle pocket sized to match the bib's bottom
//      footprint (`bib_plate_width` × `bib_plate_thickness` plus a
//      small `bib_recess_clearance` for slop). When installed, the
//      bib's bottom perimeter nestles into this recess — the VHB
//      bond is inside the pocket floor, and the lateral keying stops
//      the deflector from sliding sideways during the adhesive cure.
//
//   4. **Tapered V-groove** on the flap top. Dish depth grows
//      linearly from ~0 at the bend to `contour_depth` at the drip
//      edge so the contour "grows in" from the fold rather than
//      starting abruptly. Achieved by tilting the subtracted
//      cylinder's axis so it's tangent to the flap top at the
//      hinge-end and dips `contour_depth` below it at the front end.
//
// Construction — polygon side profile + linear_extrude + three
// boolean subtracts (tilted dish cylinder, bib recess, rear-corner
// anti-round prisms). All subtract cutters extend past the main
// body by an `eps` to kill coplanar-face artefacts.
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
//   rear-corner roundings. The flap's bed-facing underside has
//   ~1.28× overhang per layer at 38° — above the classic
//   45°-from-vertical threshold but manageable for a thin plate.
//   Drop flap_angle to 45°+ if a cleaner underside finish is needed.

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Bib reference (drives defaults + recess geometry) -----
bib_plate_width     = 72;  // @param number min=60 max=90  step=0.5 unit=mm  group=bib label="Aquor face-plate width"
bib_plate_height    = 100; // @param number min=80 max=120 step=0.5 unit=mm  group=bib label="Aquor face-plate height"
bib_plate_thickness = 6;   // @param number min=0  max=12  step=0.5 unit=mm  group=bib label="Aquor face-plate protrusion from wall"
bib_corner_radius   = 9;   // @param number min=0  max=20  step=0.5 unit=mm  group=bib label="Aquor face-plate corner radius"

// ----- Bib recess (pocket in the tab top that mates to the bib) -----
bib_recess_depth     = 1.5;  // @param number min=0   max=4   step=0.25 unit=mm group=fit label="Recess depth in the tab top"
bib_recess_clearance = 0.4;  // @param number min=0   max=1.5 step=0.05 unit=mm group=fit label="Clearance around bib in recess"

// ----- Part geometry -----
width           = 68;   // @param number min=40 max=90  step=0.5 unit=mm  group=geometry label="Part width (X)"
tab_depth       = 10;   // @param number min=5  max=30  step=0.5 unit=mm  group=geometry label="VHB tab depth (Y)"
flap_length     = 32;   // @param number min=15 max=60  step=0.5 unit=mm  group=geometry label="Flap length (along the plate)"
flap_angle      = 38;   // @param number min=15 max=60  step=1   unit=deg group=geometry label="Flap angle above horizontal"
plate_thickness = 2.5;  // @param number min=1.5 max=4   step=0.25 unit=mm group=geometry label="Plate thickness (uniform)"

// ----- Bend -----
bend_radius     = 12;   // @param number min=4  max=20  step=0.5 unit=mm  group=shape label="Outer bend radius"

// ----- Top contour (concave dish on the flap) -----
contour_depth          = 1.5; // @param number min=0   max=3   step=0.25 unit=mm group=shape label="Contour dish depth at the drip edge (tapers from 0 at the bend)"
contour_side_rim_width = 1.5; // @param number min=0.5 max=8   step=0.25 unit=mm group=shape label="Raised side-rim width on the flap top"

// === Derived ===

_fa = flap_angle;
_t  = plate_thickness;
_R  = bend_radius;                   // outer bend radius
_Ri = bend_radius - plate_thickness; // inner bend radius (must stay > 0)

// Dish cylinder radius. Solve chord geometry so the cylinder is
// tangent to the flap top at X = ±(width/2 − rim) and dishes
// `contour_depth` at the centerline (at full-depth end):
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

// Recess footprint. Radius clamp so the rounded-rectangle stays
// manifold even when bib_corner_radius exceeds the recess's narrow
// dimension (a 9 mm radius can't actually fit inside a 6 mm-deep
// rectangle — the real geometry is an approximation of the bib's
// bottom projection where the face plate's rounded corners meet
// its bottom edge).
_recess_w = bib_plate_width + 2 * bib_recess_clearance;
_recess_d = bib_plate_thickness + 2 * bib_recess_clearance;
_recess_r = min(
    bib_corner_radius,
    _recess_d / 2 - 0.01,
    _recess_w / 2 - 0.01
);

// PRINT_ANCHOR_BBOX at defaults. Measured from the rendered STL;
// recomputed whenever the bend or flap params shift materially.
PRINT_ANCHOR_BBOX = [68, 42.6, 24.22];

// @preset id="aquor-72x100" label="Aquor 72×100mm (default)" bib_plate_width=72 bib_plate_height=100 bib_plate_thickness=6 bib_corner_radius=9 bib_recess_depth=1.5 bib_recess_clearance=0.4 width=68 tab_depth=10 flap_length=32 flap_angle=38 plate_thickness=2.5 bend_radius=12 contour_depth=1.5 contour_side_rim_width=1.5

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

// Tapered V-groove cutter. A truncated cone whose axis lies in the
// flap-local X=0, Z=(_t+_Rd-contour_depth) line, pointing along the
// flap's +Y. The cone's radius grows linearly from `_Rd -
// contour_depth` at the bend-end to `_Rd` at the drip-end — which
// makes the dish depth on the flap top grow linearly from 0 to
// `contour_depth`, and the dish width grow from 0 to its full chord.
// Unlike a tilted cylinder, the cap faces are perpendicular to +Y
// (not tilted), so they don't slice the plate at a shallow angle —
// which was producing tiny orphan fragments (previous revision).
// `slack_back` pushes the back cap behind `groove_inset` so the cap
// lands in a region where the cone cross-section is already too
// small to reach the plate top; `slack_front` pushes the front cap
// past the drip edge.
module _contour_cutter() {
    slack_front  = 6;
    slack_back   = 3;
    groove_inset = 3;
    taper_len    = flap_length - groove_inset;
    cutter_len   = slack_back + taper_len + slack_front;
    // Cone radii: linear in local Y. At Y=groove_inset, r = _Rd -
    // contour_depth (cross-section's lowest Z = axis_Z + _Rd -
    // (_Rd - contour_depth) ... no wait, the axis is at fixed Z,
    // and the cross-section's LOWEST Z at radius r is axis_Z - r.
    // With axis_Z = _t + _Rd - contour_depth, lowest Z at r is
    // _t - contour_depth + (_Rd - r). Dish depth below plate top
    // is (_t) - lowest_Z = contour_depth - (_Rd - r) = r - (_Rd - contour_depth).
    // So: r = (_Rd - contour_depth)  → depth = 0 (tangent)
    //     r = _Rd                     → depth = contour_depth
    r_back_cap  = (_Rd - contour_depth) - contour_depth * slack_back  / taper_len;
    r_front_cap = _Rd                   + contour_depth * slack_front / taper_len;
    axis_Z = _t + _Rd - contour_depth;
    translate([0, _midline_hinge_y, _midline_hinge_z])
        rotate([_fa, 0, 0])
            translate([0, groove_inset - slack_back, axis_Z])
                // rotate([-90,0,0]) sends local +Z (extrude axis) to
                // flap-local +Y, so the cone grows along +Y.
                rotate([-90, 0, 0])
                    cylinder(h = cutter_len, r1 = r_back_cap, r2 = r_front_cap);
}

// Bib-bottom recess. A rounded-rectangle pocket on the tab's top
// surface, centered in X with the rear edge at Y = 0. The
// subtraction starts at Z = t − recess_depth and extends upward
// past the tab top by `eps` so no coplanar-face artefact remains
// at the tab surface.
module _bib_recess_cutter() {
    if (bib_recess_depth <= 0) {
        // no-op
    } else {
        eps = 0.05;
        h = bib_recess_depth + eps;
        translate([0, _recess_d / 2, _t - bib_recess_depth])
            linear_extrude(h)
                rect([_recess_w, _recess_d],
                     rounding = _recess_r,
                     anchor = CENTER);
    }
}

// Anti-round corner cutters for the tab's two rear corners (Y=0
// side). Each cutter = a corner cube minus a vertical quarter-
// cylinder at the inset corner; the difference leaves a rounded-
// rectangle rear corner of radius `bib_corner_radius`. Only acts on
// the tab portion (Y < bib_corner_radius); the flap is untouched.
// Cutter extents bump out of the main body by `eps` on every
// would-be-coplanar face so Manifold doesn't leave zero-thickness
// artefacts at the edges.
module _rear_corner_cutters() {
    if (bib_corner_radius <= 0) {
        // no-op
    } else {
        R = bib_corner_radius;
        eps = 0.1;
        h = _t + 2 * eps;
        for (sign = [-1, 1]) {
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
        _bib_recess_cutter();
        _rear_corner_cutters();
    }
}

aquor_bib_drip_deflector();
