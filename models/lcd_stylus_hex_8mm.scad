// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Hex-profile stylus for a child's pressure-sensitive LCD drawing pad —
// sibling of lcd_stylus_75mm (the round tapered bullet). Same job, same
// kid-safe ethos: no electronics, just a firm, smooth ~2 mm rounded dome
// tip that presses a clean line without scratching or puncturing the film,
// and no hard edges anywhere. The difference is the body: a constant
// pencil-like hexagon cross-section (8 mm across flats) instead of a round
// taper, so it feels like a pencil and doesn't roll off the table.
//
// Geometry: ONE convex hull of thirteen spheres. Twelve edge_fillet-radius
// spheres sit at the corners of two hexagonal rings — a rear ring at the
// base and a front ring where the taper starts. Their hull is a hex prism
// whose six faces stay flat but whose every edge is tangent-rounded at
// edge_fillet: the six long edges become cylindrical fillets, the base end
// becomes a flat hex face with a rolled rim. The thirteenth sphere is the
// tip dome; hulling it in produces the smooth hex-to-dome taper, and every
// taper edge blends tangentially from the corner spheres to the dome. No
// hard corners anywhere on the stylus proper.
//
// Print orientation: lies flat on the bed on one hex face — that IS the
// model's native orientation (bottom flat on z=0, no slicer rotation
// needed). Lying flat, only the tapered tip zone floats above the bed
// (the tip axis sits at hex_width/2 but the dome radius is smaller), so
// the model ships with a designed-in breakaway support: a thin sacrificial
// fin under the tip zone, connected to the underside through three ~0.5 mm
// contact ribs. After printing, snap the fin off sideways and sand the
// three tiny stubs. The rib contact points are the one deliberate
// exception to the no-hard-edges rule (they must snap clean); the fin's
// own outer profile is rounded too. The first ~0.7 mm of tip-zone rise
// (before the fin can start) is close enough to the bed that any sag is
// cosmetic and sands out.

$fn = 128;

// === User-tunable parameters ===
hex_width       = 8;    // @param number min=6 max=12 step=0.5 unit=mm group=geometry label="Body width (across flats)"
total_length    = 90;   // @param number min=70 max=140 step=1 unit=mm group=geometry label="Total length"
tip_radius      = 2;    // @param number min=1 max=2.75 step=0.25 unit=mm group=geometry label="Tip dome radius"
edge_fillet     = 1;    // @param number min=0.4 max=2 step=0.1 unit=mm group=geometry label="Edge fillet radius"
taper_length    = 14;   // @param number min=8 max=25 step=1 unit=mm group=geometry label="Tip taper length"
include_support = true; // @param boolean group=printing label="Breakaway tip support"

// @preset id="default" label="Default" hex_width=8 total_length=90 tip_radius=2 edge_fillet=1 taper_length=14 include_support=true

// === PRINT_ANCHOR_BBOX ===
// Lying flat: X spans the full stylus, base face tangent plane at x=0 to
// the tip dome at x=total_length. Y spans the rounded hex across corners:
// corner circumradius (hex_width/2 - edge_fillet)/cos(30) plus edge_fillet
// each side = 2*((4-1)/cos(30) + 1) = 8.93. Z is the hex across flats
// (bottom face on z=0, top face at hex_width). The support fin stays
// inside all three extents.
//   X 90,  Y 8.93,  Z 8
PRINT_ANCHOR_BBOX = [90, 8.93, 8];

axis_z  = hex_width / 2;                // stylus axis height above the bed
apothem = hex_width / 2 - edge_fillet;  // core hexagon flat distance
hex_rc  = apothem / cos(30);            // core hexagon corner radius

// --- breakaway support math (2D, in the y=0 plane) ---
// Lying flat, the underside leaves the bed at the taper start and climbs
// to the tip dome along the lower tangent line from (sup_px, 0) to the
// tip sphere. The fin's top edge parallels that line fin_gap below it;
// ribs bridge the gap and root ~1.2 mm into the body.
fin_gap = 0.7;  // vertical air gap between fin top edge and the underside
fin_th  = 1.0;  // fin thickness (Y)
rib_w   = 0.5;  // contact rib width (X) — the snap point
sup_px  = total_length - taper_length;  // underside lifts off the bed here
sup_bx  = total_length - tip_radius;    // tip sphere center (x)
sup_d   = sqrt((sup_bx - sup_px)^2 + axis_z^2);
sup_theta = atan2(axis_z, sup_bx - sup_px) - asin(tip_radius / sup_d);
sup_m   = tan(sup_theta);               // underside ramp slope
fin_x0  = sup_px + fin_gap / sup_m;     // fin starts where it has any height
fin_x1  = sup_px + sqrt(sup_d^2 - tip_radius^2) * cos(sup_theta); // tangent touch point

function underside_z(x) = (x - sup_px) * sup_m;

// Every hull sphere gets a distinct mesh phase (a small z-rotation,
// per-sphere). A sphere is rotation-invariant, so the SHAPE is
// untouched — but without this, all twelve corner spheres are exact
// translated copies of one tessellated mesh, and the hull faces that
// bridge corresponding vertices of two copies are exactly-coplanar
// quads by construction. CGAL's convex_hull_3 in the site's
// openscad-wasm build (2025.01.19, the newest published) has a
// robustness bug on such degenerate inputs: at some widths
// (hex_width 9/10/12) it fails its border walk ("it != border.end()"
// assertion), applyHull() emits nothing, and the preview showed only
// the fin + ribs (st-7x7). Distinct phases (all distinct modulo the
// 360/$fn fragment angle) put the hull's input points in generic
// position, which renders intact across the whole param range —
// verified by the wasm param-sweep test (tests/sweep/). Desktop
// OpenSCAD renders identically either way (within tessellation).
module corner_ring(x, phase) {
    // Six fillet spheres at the corners of the core hexagon, oriented so
    // the hull's flats land top/bottom (corners at 0/60/.../300 put edge
    // normals at 90 and 270 — a flat face down on the bed).
    for (k = [0:5])
        translate([x, hex_rc * cos(60 * k), axis_z + hex_rc * sin(60 * k)])
            rotate([0, 0, phase + 1.3 * k])
                sphere(r = edge_fillet);
}

module stylus_body() {
    hull() {
        corner_ring(edge_fillet, 0.4);                  // base ring; face plane at x=0
        corner_ring(total_length - taper_length, 8.1);  // ring where the taper starts
        translate([total_length - tip_radius, 0, axis_z])
            rotate([0, 0, 16.7])
                sphere(r = tip_radius);                 // tip dome
    }
}

module support_fin() {
    // Sacrificial fin: a rounded triangular profile on the bed, its top
    // edge tracking the underside ramp fin_gap below the model. The
    // offset shrink/grow pass rounds the profile's outer corners and
    // drops any unprintable sliver at the thin end.
    rotate([90, 0, 0])
        linear_extrude(height = fin_th, center = true)
            offset(r = 0.3) offset(delta = -0.3)
                polygon([
                    [fin_x0, 0],
                    [fin_x1, 0],
                    [fin_x1, underside_z(fin_x1) - fin_gap],
                ]);
    // Three thin ribs bridge the gap: rooted in the fin, buried ~1.2 mm
    // into the body. The exposed ~0.5 x 1.0 mm necks are the snap points.
    for (f = [0.2, 0.55, 0.9]) {
        x  = fin_x0 + f * (fin_x1 - fin_x0);
        z0 = max(0.05, underside_z(x) - fin_gap - 0.6);
        z1 = underside_z(x) + 1.2;
        translate([x - rib_w / 2, -fin_th / 2, z0])
            cube([rib_w, fin_th, z1 - z0]);
    }
}

module stylus() {
    stylus_body();
    // Skip the fin when the tip barely floats (sub-millimetre gap prints
    // fine without support) — also guards degenerate fin geometry.
    if (include_support && axis_z - tip_radius > fin_gap + 0.3)
        support_fin();
}

stylus();
