// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Aquor hose-bib drip deflector — bent sheet-metal form (st-r38,
// revised st-if3 / st-hkn / st-vu1 / st-002). One continuous plate of
// uniform thickness, smoothly bent from a horizontal VHB tab to a
// down-angled flap, with two quarter-arc corner fillers on the tab's
// rear that nest into the voids under the bib's rounded-corner bottom
// arc. In install orientation the tab's top face is VHB-taped to the
// Aquor face-plate underside; the fillers ride inside the bib's own
// plate volume at each lower corner, where the bib's flat bottom edge
// curves upward into the left/right sides. The flap hangs outward-
// and-downward past the wall plane so drain water sheds off its
// front edge clear of the drywall below.
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
//   3. **Quarter-arc corner fillers** at the tab's top-rear at each
//      bib-corner footprint (st-002, replacing st-vu1's mislocated
//      upright ears). Each filler is a `bib_corner_radius`-wide block
//      rising `bib_corner_radius` above the tab top, carved out by a
//      cylinder at the bib's lower-corner centre (radius
//      `bib_corner_radius + bib_clearance`, axis along +Y). The result
//      is a pie-slice wedge whose concave top surface matches the
//      bib's corner arc — it hides INSIDE the bib's plate volume when
//      installed (not outside wrapping the corner — that was v6's
//      mistake). Depth in Y equals `bib_plate_thickness` so the
//      filler spans the full face-plate thickness at the corner.
//      Print caveat: the concave top arc faces upward in print
//      orientation, giving a ceiling-bridge overhang of up to 90° at
//      the arc's sides; the 9 mm span is short enough for routine
//      slicer bridging.
//
//   4. **Tapered V-groove** on the flap top. Dish depth grows
//      linearly from ~0 at the bend to `contour_depth` at the drip
//      edge so the contour "grows in" from the fold rather than
//      starting abruptly. Implemented as a truncated-cone subtract
//      whose radius grows along the flap, keeping the cone caps
//      perpendicular to +Y (not tilted) so they land cleanly outside
//      the plate bounds.
//
// Construction — polygon side profile + linear_extrude (bent plate),
// union'd with two corner-filler blocks (each = rectangular prism
// minus a cylinder at the bib's corner centre), then boolean subtracts
// (contour cone, rear-corner anti-round prisms). Subtract cutters
// extend past the main body by an `eps` to kill coplanar-face
// artefacts.
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

// ----- Fit (clearance against the bib) -----
// Both the corner-filler subtract and the rear-corner anti-round cutter
// derive their radii from `bib_corner_radius`. `bib_clearance` pads the
// filler's arc-subtract so the bib's actual corner slides in without
// grinding; the filler's X-width and Z-height are fixed at
// `bib_corner_radius`, its Y-depth at `bib_plate_thickness`. (st-002)
bib_clearance  = 0.4;  // @param number min=0   max=1.5 step=0.05 unit=mm group=fit label="Clearance around bib corner arc"

// ----- Part geometry -----
width           = 78;   // @param number min=50 max=100 step=0.5 unit=mm  group=geometry label="Part width (X)"
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

// Corner-filler geometry. Each filler sits at a bib lower-corner
// footprint: a block of X-width × Z-height = bib_corner_radius each,
// Y-depth = bib_plate_thickness, with the bib's corner-arc cylinder
// subtracted so the filler's concave top surface matches the bib's
// rounded-rectangle bottom arc (plus bib_clearance slop).
_corner_cx         = bib_plate_width / 2 - bib_corner_radius;  // |X| of each bib lower-corner centre
_corner_cz         = _t + bib_corner_radius;                   // Z of the corner arc centre (above tab top)
_corner_arc_radius = bib_corner_radius + bib_clearance;        // subtracted cylinder radius

// PRINT_ANCHOR_BBOX at defaults. Z is dominated by the flap's inner
// tip (~24.22 mm at flap_length=32, flap_angle=38°). The new corner
// fillers rise to _t + bib_corner_radius = 11.5 mm — well under the
// flap tip, so bbox Z is unchanged from v4/v6. (st-002)
PRINT_ANCHOR_BBOX = [78, 42.6, 24.22];

// @preset id="aquor-72x100" label="Aquor 72×100mm (default)" bib_plate_width=72 bib_plate_height=100 bib_plate_thickness=6 bib_corner_radius=9 bib_clearance=0.4 width=78 tab_depth=10 flap_length=32 flap_angle=38 plate_thickness=2.5 bend_radius=12 contour_depth=1.5 contour_side_rim_width=1.5

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

// Corner-fillers (st-002). Two pie-slice wedges, one under each of
// the bib's rounded-rectangle bottom corners. In the install pose the
// bib's flat bottom edge is at the tab's top face; at each lower
// corner the bib's bottom edge curves upward along a quarter-arc of
// radius `bib_corner_radius`, leaving a curved void between tab top
// and bib underside. This module fills that void.
//
// For the left corner (sign = -1): a cube spanning X ∈ [-bib_plate
// _width/2, -bib_plate_width/2 + bib_corner_radius], Y ∈ [0, bib_plate
// _thickness], Z ∈ [_t, _t + bib_corner_radius], minus a cylinder
// (axis along +Y) at the bib's corner centre (X = -_corner_cx,
// Z = _corner_cz) with radius `_corner_arc_radius`. Subtraction keeps
// the region OUTSIDE the arc — the pie slice under the bib's
// curve. Mirror for the right corner.
//
// Unioned with the bent plate before the rear-corner cutters subtract.
// The rear-corner cutter's Z-range extends up to `_t + eps`, nicking a
// ~0.1 mm sliver off the filler's rear-outer bottom edge; the sliver
// is well under slicer resolution and keeps the tab-filler seam
// manifold where the tab's rear-outer corner rounds off.
module _corner_fillers() {
    for (sign = [-1, 1]) {
        corner_x = sign * _corner_cx;
        block_x_min = sign < 0
            ? -bib_plate_width / 2
            :  _corner_cx;
        difference() {
            translate([block_x_min, 0, _t])
                cube([bib_corner_radius, bib_plate_thickness, bib_corner_radius]);
            // Cylinder passes fully through the block along +Y; pad
            // each end by `eps` so the caps don't coincide with the
            // block's Y faces (coplanar-face jitter territory).
            translate([corner_x, -0.02, _corner_cz])
                rotate([-90, 0, 0])
                    cylinder(h = bib_plate_thickness + 0.04,
                             r = _corner_arc_radius);
        }
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
        union() {
            _bent_plate_solid();
            _corner_fillers();
        }
        if (contour_depth > 0 && _Rd > 0) _contour_cutter();
        _rear_corner_cutters();
    }
}

aquor_bib_drip_deflector();
