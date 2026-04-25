// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Aquor hose-bib drip deflector — bent sheet-metal form (st-r38,
// revised st-if3 / st-hkn / st-vu1 / st-002 / st-hxy / st-c7x /
// st-6pc). One continuous plate of uniform thickness, smoothly bent
// from a VHB-bonded wall-panel section to a down-and-forward-angled
// flap. Two coplanar quarter-arc wedges at the back of the VHB
// section trace the bib's bottom-corner outline so they nest under
// the face-plate's lower corners during install, keying the
// deflector laterally.
//
// === INSTALL ORIENTATION ===
//
// The deflector mounts as a VERTICAL wall panel under the hose bib.
// The blue tab's VHB face is pressed against the wall; the green
// flap hangs forward-and-down at `flap_angle` below horizontal.
// Water runs down the wall, onto the blue panel's outward face, over
// the bend, down the green flap, and drips off the front edge clear
// of the drywall below. Install axes (independent of print pose):
//   install +X = along bib width    (unchanged from the part's +X)
//   install +Y = outward from wall  (normal to wall plane)
//   install +Z = up toward ceiling
//
// === PRINT ORIENTATIONS ===
//
// `print_orientation` selects the pose that goes to the slicer.
// Defaults to "side" (v13) — the user's v12 first-print landed a
// borderline 45° overhang on the bend's underside, right at the FDM
// no-support threshold. Side-printing rotates the part to stand on
// one of its X-end corner-tab faces; the bent-plate shape is uniform
// along its logical X axis (the linear_extrude of `_side_profile`),
// so every print Z layer is the same 2D side-profile silhouette
// stacked on the previous — no overhangs anywhere, including the
// bend.
//
// --- "side" (v13, st-97h, default) ---
//   Transform: rotate([0, -90, 0]) followed by a translate to put
//     the rotated part's min-Z on Z=0 and shift in X so the bbox
//     starts at X=0.
//   Bed face: the part's logical -X end face (one of the two
//     symmetric corner-tab end faces).
//   Print bbox at defaults (fa=45°, width=72): roughly
//     [28, 50, 72] mm — tall and narrow.
//   First-layer footprint: the X-end's 2D silhouette (the side
//     profile of the bent plate plus a corner wedge), about
//     2.5 × 50 mm. Slim — use a slicer brim, or set
//     `print_foot=true` to add a sacrificial slab.
//   Install→print axes (verified against the rotate output):
//     install +X (along bib width)  → print +Z
//     install +Y (outward from wall) → print +Y
//     install +Z (up toward ceiling) → print -X
//
// --- "flap_on_bed" (v12, st-me9, legacy) ---
//   Transform: rotate([-flap_angle, 0, 0]) then translate(+lift in Z),
//     where lift = tab_depth·sin(fa) + bend_radius·(1−cos(fa)). The
//     green flap lies flat on Z=0; the blue tab + red wedges rise at
//     flap_angle above horizontal.
//   Print bbox at defaults: [72, 52, 16.8] mm — wide and short.
//   First-layer footprint: the full flap underside (~32 × 72 mm).
//   Install→print axes:
//     install +X                     → print +X (unchanged)
//     install +Y (toward drip)       → print +Y·cos(fa) − Z·sin(fa)
//     install +Z (flap top)          → print +Y·sin(fa) + Z·cos(fa)
//   Trade-off (the v13 motivation): the flap-bottom and tab-bottom
//     faces both sit at fa from vertical overhang; at fa=45° that's
//     right at the support-free limit and slicer-dependent.
//
// Features that depend on the pose:
//   - V-groove on the flap top (logical +Z face): in flap_on_bed
//     it ends up up-facing near Z = plate_thickness; in side it
//     ends up at print -X (centered well inside the print bbox).
//   - Corner wedges (logical Y < 0): in flap_on_bed they tilt up
//     above the tab's top-rear edge; in side they sit at print Z
//     near 0 (one wedge) and print Z near `width` (the other),
//     both as flat-bed-coplanar slices.
//
// === GEOMETRY ===
//
// Three features on top of the raw L-shape:
//
//   1. **Large-radius bend.** Tab→flap junction is a filleted corner
//      (outer radius `bend_radius`, default 12 mm at the bib size).
//      Longer arc smooths the transition — it reads as a continuous
//      bend, not a fold line.
//
//   2. **Rear-extending corner wedges** at the VHB section's two
//      rear-outer corners (st-6pc — reshaped from v9's rectangular
//      tabs). Each wedge has a quarter-arc curved inner edge that
//      traces the bib's bottom-corner outline. Footprint: a
//      `bib_corner_radius` × `bib_corner_radius` box at the corner
//      position minus a cylinder of radius `bib_corner_radius +
//      corner_wedge_clearance` at the bib's corner centre. Coplanar
//      with the VHB section (Z ∈ [0, plate_thickness]); flush with
//      the build plate so they print without supports. In install
//      orientation the wedge nests under the bib's curving lower
//      corner — the curved edge on the wedge faces UP toward the
//      bib's outline.
//
//   3. **Tapered V-groove** on the flap top (print +Z face). Dish
//      depth grows linearly from ~0 at the bend to `contour_depth`
//      at the drip edge. Implemented as a truncated-cone subtract
//      whose radius grows along the flap, keeping the cone caps
//      perpendicular to +Y (not tilted) so they land cleanly outside
//      the plate bounds.
//
// Debug colour legend (when `debug_colors=true`):
//   tab                  → cornflowerblue
//   bend                 → gold
//   flap                 → mediumseagreen
//   corner wedges (−Y)   → tomato
//
// Construction — polygon side profile + linear_extrude (bent plate,
// as three tab/bend/flap sub-polygons for the colour palette),
// union'd with two simple rear-extending corner-tab cubes, then the
// contour-cone subtract.
//
// Print orientation (how this file models the part):
//   VHB section lies flat on the build plate, Z = [0, plate_thickness].
//   Flap rises at `flap_angle` above horizontal from the bend — this
//   is entirely a print-time convenience; in install orientation the
//   flap hangs forward-and-DOWN at `flap_angle` below horizontal,
//   since the whole part has been rotated 90° about X. The flap's
//   bed-facing underside has ~1.28× overhang per layer at 38° — above
//   the classic 45°-from-vertical threshold but manageable for a thin
//   plate. Drop flap_angle to 45°+ if a cleaner underside finish is
//   needed. The new rear-extending corner tabs are coplanar with the
//   VHB section's first layer so they print without supports.

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Bib reference (drives defaults + recess geometry) -----
bib_plate_width     = 72;  // @param number min=60 max=90  step=0.5 unit=mm  group=bib label="Aquor face-plate width"
bib_plate_height    = 100; // @param number min=80 max=120 step=0.5 unit=mm  group=bib label="Aquor face-plate height"
bib_plate_thickness = 6;   // @param number min=0  max=12  step=0.5 unit=mm  group=bib label="Aquor face-plate protrusion from wall"
bib_corner_radius   = 9;   // @param number min=0  max=20  step=0.5 unit=mm  group=bib label="Aquor face-plate corner radius"

// ----- Fit (rear-extending corner wedges) -----
// Two coplanar rear-extending wedges at the VHB section's two rear-
// outer corners (st-6pc). Each wedge's footprint is a
// `bib_corner_radius`-square box at X ∈ [±bib_plate_width/2,
// ±(bib_plate_width/2 − bib_corner_radius)], Y ∈ [−bib_corner_radius,
// 0], with a cylinder (radius `bib_corner_radius + corner_wedge_
// clearance`, axis along +Z) at the bib's lower-corner centre
// subtracted. The remaining material is a quarter-pie wedge whose
// curved inner edge traces the bib's bottom-corner arc — in install
// orientation the wedge fills the void between the blue panel's top
// edge and the bib's curving bottom. `corner_wedge_clearance` is the
// radial slop so the printed wedge clears the bib's actual corner
// without grinding.
corner_tabs            = true; // @param boolean group=fit label="Rear-extending corner wedges (trace bib's corner arc)"
corner_wedge_clearance = 0.4;  // @param number min=0 max=1.5 step=0.05 unit=mm group=fit label="Radial clearance between wedge arc and bib corner"

// ----- Part geometry -----
width           = 72;   // @param number min=50 max=100 step=0.5 unit=mm  group=geometry label="Part width (X) — matches bib_plate_width by default to remove the shoulder at the wedge seam"
tab_depth       = 10;   // @param number min=5  max=30  step=0.5 unit=mm  group=geometry label="VHB tab depth (Y)"
flap_length     = 32;   // @param number min=15 max=60  step=0.5 unit=mm  group=geometry label="Flap length (along the plate)"
flap_angle      = 45;   // @param number min=15 max=60  step=1   unit=deg group=geometry label="Flap angle from horizontal (drives print-orientation rotation too)"
plate_thickness = 2.5;  // @param number min=1.5 max=4   step=0.25 unit=mm group=geometry label="Plate thickness (uniform)"

// ----- Bend -----
bend_radius     = 12;   // @param number min=4  max=20  step=0.5 unit=mm  group=shape label="Outer bend radius"

// ----- Top contour (concave dish on the flap) -----
contour_depth          = 1.5; // @param number min=0   max=3   step=0.25 unit=mm group=shape label="Contour dish depth at the drip edge (tapers from 0 at the bend)"
contour_side_rim_width = 1.5; // @param number min=0.5 max=8   step=0.25 unit=mm group=shape label="Raised side-rim width on the flap top"

// ----- Print orientation (st-97h) -----
// "side" (default) stands the part on one X-end corner-tab face so
// every print Z layer is the same 2D side-profile slice (no overhangs
// anywhere, including the bend). "flap_on_bed" preserves v12's pose
// for anyone reprinting the original or with a saved slicer profile.
print_orientation   = "side";  // @param enum choices=side|flap_on_bed group=print label="Print orientation"

// Optional sacrificial print-foot for the side orientation. The first-
// layer footprint of side is slim (~2.5 × 50 mm); a slicer brim is the
// preferred adhesion aid, but a print-foot offers a dimensional spec
// for cases where the brim isn't enough. Default OFF.
print_foot          = false; // @param boolean group=print label="Sacrificial print-foot (side orientation only)"
print_foot_height   = 0.4;   // @param number min=0.2 max=1.0 step=0.1 unit=mm group=print label="Print-foot Z height"
print_foot_overhang = 1.5;   // @param number min=0 max=4 step=0.25 unit=mm group=print label="Print-foot overhang past part footprint"

// ----- Debug / visualization -----
// Preview-only tint; does NOT affect the exported STL (colours aren't
// carried in binary STL). Default on while the corner-filler geometry
// is still being dialled in (st-57r) — flip off once shape is final.
debug_colors = true; // @param boolean group=debug label="Color regions (preview only; not exported)"

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

// Print-pose transforms.
//
// flap_on_bed (v12 / st-me9). The logical frame has the tab flat on
// Z=0 and the flap rising at flap_angle above horizontal (the "old"
// print frame); the new print frame is produced by a final
// `translate([0, 0, _print_lift]) rotate([-flap_angle, 0, 0])`
// wrapper. `_print_lift` pushes the flap's underside onto Z=0 — it's
// the absolute value of the flap-bend outer-arc endpoint's Z
// coordinate after the rotation.
_print_lift = tab_depth * sin(_fa) + _R * (1 - cos(_fa));

// side (v13 / st-97h). rotate([0, -90, 0]) maps logical (X, Y, Z) to
// world (-Z, Y, X), so logical +X — the linear_extrude axis of the
// bent plate — becomes print +Z. Translate in Z by `width/2` so the
// rotated part's min-Z (logical X = -width/2) lands on the bed.
// Translate in X by `_side_print_x_shift` so the part's bbox starts
// at print X = 0; the X extent is dominated by the flap's inner-tip
// logical Z (it's the part's max-Z corner — the flap rises into +Z
// in the logical frame, which becomes -X in the side print frame).
_side_print_z_lift  = width / 2;
_side_print_x_shift = _flap_inner_tip[1] + 0.05;  // tiny pad so X-min lands at +0.05

// Wedge Y-min: the cylinder cut leaves the wedge material starting
// at Y = -R + sqrt(2Rc + c²) at the X-end faces (X = ±bib_plate
// _width/2). At defaults (R=9, c=0.4) that's about Y = -6.29 mm,
// not -9 mm — the cylinder eats most of the cube's bottom corner.
_wedge_y_min = -bib_corner_radius
    + sqrt(2 * bib_corner_radius * corner_wedge_clearance
           + corner_wedge_clearance * corner_wedge_clearance);

// PRINT_ANCHOR_BBOX at defaults — depends on print_orientation.
//   flap_on_bed: with flap_angle = 45° the flap lies flat at Z =
//     0..plate_thickness across Y ≈ 15.56..47.56; blue tab + wedges
//     tilt up at 45° from the bend, reaching Z ≈ 16.8 at the wedge
//     tips. X unchanged at `width` (72 mm default). Y extends from
//     wedge tips (~ −4.45 mm) to the flap drip tip (~ 47.56 mm),
//     total ≈ 52 mm.
//   side: rotated to stand on the X-end. X bbox = max logical Z
//     (≈ flap inner-tip Z); Y bbox = logical Y span from the wedge's
//     surviving inner edge (_wedge_y_min) to the flap outer tip;
//     Z bbox = `width`.
PRINT_ANCHOR_BBOX = print_orientation == "side"
    ? [_side_print_x_shift + 0.05,
       _flap_outer_tip[0] - _wedge_y_min,
       width]
    : [72, 52.01, 16.79];

// @preset id="aquor-72x100" label="Aquor 72×100mm (default, side)" bib_plate_width=72 bib_plate_height=100 bib_plate_thickness=6 bib_corner_radius=9 corner_tabs=true corner_wedge_clearance=0.4 width=72 tab_depth=10 flap_length=32 flap_angle=45 plate_thickness=2.5 bend_radius=12 contour_depth=1.5 contour_side_rim_width=1.5 print_orientation="side" print_foot=false print_foot_height=0.4 print_foot_overhang=1.5 debug_colors=true
// @preset id="aquor-72x100-flap-on-bed" label="Aquor 72×100mm (legacy flap_on_bed)" bib_plate_width=72 bib_plate_height=100 bib_plate_thickness=6 bib_corner_radius=9 corner_tabs=true corner_wedge_clearance=0.4 width=72 tab_depth=10 flap_length=32 flap_angle=45 plate_thickness=2.5 bend_radius=12 contour_depth=1.5 contour_side_rim_width=1.5 print_orientation="flap_on_bed" print_foot=false print_foot_height=0.4 print_foot_overhang=1.5 debug_colors=true

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

// --- Region-specific sub-profiles (for the debug colour palette) -------
//
// Splitting `_side_profile` into three sub-polygons lets each region
// live in its own extrude + `color()` call, which the Manifold preview
// renderer then carries through the downstream union/difference without
// collapsing to a single tint (intersect-and-slice didn't — the backend
// merged the touching faces back into one colour). The sub-polygons
// share their seam edges exactly so the union reproduces the original
// bent-plate solid.
//
// Bend–flap seam is a vertical polygon-space line at X = _outer_end_y.
// The inner flap surface at that X is `_inner_z_at_outer_end_y` — linear
// interpolation between (_inner_end_y, _inner_end_z) and
// (_inner_arc_exit).
_inner_flap_dX = _inner_arc_exit[0] - _inner_end_y;
_inner_flap_dY = _inner_arc_exit[1] - _inner_end_z;
_inner_z_at_outer_end_y =
    _inner_end_z + (_outer_end_y - _inner_end_y) * _inner_flap_dY / _inner_flap_dX;

module _tab_profile() {
    polygon([
        [0, 0],
        [tab_depth, 0],
        [tab_depth, _t],
        [0, _t],
    ]);
}

module _bend_profile() {
    n = 20;
    outer_arc = _arc_samples(tab_depth, _R, _R,  270, 270 + _fa, n);
    inner_arc = _arc_samples(tab_depth, _R, _Ri, 270 + _fa, 270, n);
    polygon(concat(
        [[tab_depth, 0]],
        outer_arc,
        [[_outer_end_y, _inner_z_at_outer_end_y]],
        inner_arc,
        [[tab_depth, _t]]
    ));
}

module _flap_profile() {
    polygon([
        [_outer_end_y, _outer_end_z],
        _flap_outer_tip,
        _flap_inner_tip,
        _inner_arc_exit,
        [_outer_end_y, _inner_z_at_outer_end_y],
    ]);
}

module _extruded_profile(prof) {
    translate([-width / 2, 0, 0])
        rotate([90, 0, 90])
            linear_extrude(width) children();
}

module _tab_slice()  { _extruded_profile() _tab_profile();  }
module _bend_slice() { _extruded_profile() _bend_profile(); }
module _flap_slice() { _extruded_profile() _flap_profile(); }

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

// Rear-extending corner wedges (st-6pc). Quarter-pie wedges whose
// curved inner edge traces the bib's bottom-corner arc. Built as a
// `bib_corner_radius`-square box at the corner footprint minus a
// cylinder of radius `bib_corner_radius + corner_wedge_clearance`
// at the bib's corner centre. In install orientation the wedge
// fills the void between the blue panel's top edge and the bib's
// curving lower outline.
module _corner_wedges_geom() {
    if (!corner_tabs || bib_corner_radius <= 0) {
        // no-op
    } else {
        R   = bib_corner_radius;
        c   = corner_wedge_clearance;
        eps = 0.02;
        for (sign = [-1, 1]) {
            cx_box = sign < 0 ? -bib_plate_width / 2 : bib_plate_width / 2 - R;
            cx_cyl = sign * (bib_plate_width / 2 - R);
            difference() {
                translate([cx_box, -R, 0])
                    cube([R, R, _t]);
                // Cylinder at the bib's corner centre; pad in Z so
                // the cap planes don't sit on the wedge's Z faces.
                translate([cx_cyl, -R, -eps])
                    cylinder(h = _t + 2 * eps, r = R + c);
            }
        }
    }
}

// Debug-palette helper. Wraps children in `color()` only when the
// `debug_colors` flag is on; no-ops otherwise. STL export has no
// colour channel so this only affects the preview/thumbnail.
module color_if(cond, c) {
    if (cond) color(c) children();
    else children();
}

// Core assembly in the logical / old-print frame (blue tab flat on
// Z=0, flap rising at flap_angle). The public `aquor_bib_drip_
// deflector()` wraps this in the new print-pose transform.
module _assembled() {
    difference() {
        union() {
            color_if(debug_colors, "cornflowerblue")  _tab_slice();
            color_if(debug_colors, "gold")            _bend_slice();
            color_if(debug_colors, "mediumseagreen")  _flap_slice();
            color_if(debug_colors, "tomato")          _corner_wedges_geom();
        }
        if (contour_depth > 0 && _Rd > 0) _contour_cutter();
    }
}

// Sacrificial print-foot for the side orientation. A thin slab at
// print Z ∈ [0, print_foot_height] under the bed-contact area, padded
// outward by `print_foot_overhang` mm. The bed contact at print Z = 0
// in the side pose is the part's logical X-min slice — a thin band
// roughly (max logical Z) × (logical Y span) shaped like the side
// profile + the wedge quarter-pie at Y < 0. Approximate the footprint
// by the bbox rectangle for adhesion purposes — it's a sacrificial
// foot, not load-bearing. (st-97h)
module _print_foot_side() {
    if (print_foot && print_foot_height > 0) {
        oh = print_foot_overhang;
        // Bbox rectangle in print X-Y at Z=0:
        x0 = -oh;
        x1 = _side_print_x_shift + 0.05 + oh;
        y0 = -bib_corner_radius - oh;
        y1 = _flap_outer_tip[0] + oh;
        translate([x0, y0, 0])
            cube([x1 - x0, y1 - y0, print_foot_height]);
    }
}

module aquor_bib_drip_deflector() {
    if (print_orientation == "side") {
        union() {
            translate([_side_print_x_shift, 0, _side_print_z_lift])
                rotate([0, -90, 0])
                    _assembled();
            _print_foot_side();
        }
    } else {
        translate([0, 0, _print_lift])
            rotate([-_fa, 0, 0])
                _assembled();
    }
}

aquor_bib_drip_deflector();
