// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Aquor hose-bib drip deflector. Mounts under the face plate of a
// flush-mount Aquor hose bib (face plate 2-7/8" × 4" = 72×100 mm) with
// VHB tape and catches the freeze-drain water that exits the bib's
// lower drain port on hose disconnect, redirecting it outward past the
// wall plane so it drops clear of the drywall below.
//
// Install orientation:
//   +Y = outward from the wall
//   +Z = up
//   +X = along the bib width
//   The back face (Y=0) sits flush against the wall. The top-rear strip
//   (Y < vhb_contact_depth, Z = deflector_thickness) is a flat zone
//   for VHB tape — bonded to the smooth Aquor face plate underside, NOT
//   to drywall (paint/paper tears). Beyond the VHB zone, the top slopes
//   down-and-out at ramp_angle and a recessed channel funnels water
//   off the open front edge.
//
// Print orientation:
//   Place the back face (Y=0) on the build plate. Every outward- or
//   upward-facing surface sits at ≤ ramp_angle from horizontal or
//   vertical, so no supports are needed. The channel pocket opens UP
//   (toward the would-be-wall on the printer, which is +Y), i.e. the
//   cavity has no ceiling to span. First-layer adhesion is the full
//   deflector_width × deflector_thickness back face.

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Aquor face-plate reference (for fit; not printed) -----
bib_plate_width  = 72;   // @param number min=60 max=90 step=0.5 unit=mm group=bib label="Aquor face-plate width"
bib_plate_height = 100;  // @param number min=80 max=120 step=0.5 unit=mm group=bib label="Aquor face-plate height"

// ----- Deflector geometry -----
deflector_width     = 70;  // @param number min=40 max=90 step=0.5 unit=mm group=geometry label="Deflector width (X)"
deflector_depth     = 40;  // @param number min=25 max=80 step=0.5 unit=mm group=geometry label="Deflector depth — outward from wall (Y)"
deflector_thickness = 18;  // @param number min=10 max=35 step=0.5 unit=mm group=geometry label="Deflector max thickness (Z)"
vhb_contact_depth   = 22;  // @param number min=8  max=60 step=0.5 unit=mm group=geometry label="VHB flat zone depth from wall"
ramp_angle          = 15;  // @param number min=5  max=30 step=1   unit=deg group=shape label="Top downslope past the VHB zone"
corner_radius       = 3;   // @param number min=0  max=8  step=0.5 unit=mm group=shape label="Outer vertical corner fillet"

// ----- Channel (gutter) -----
channel_depth   = 4;    // @param number min=0   max=10 step=0.5 unit=mm group=channel label="Channel pocket depth below the ramp"
wall_thickness  = 2.5;  // @param number min=1.5 max=6  step=0.5 unit=mm group=channel label="Channel side-wall thickness"

// === Derived ===

// Vertical drop from VHB-zone top to the front-top edge along the ramp.
ramp_drop       = (deflector_depth - vhb_contact_depth) * tan(ramp_angle);
// Material thickness at the front edge (load-bearing cue — keep
// > ~5 mm so the front lip doesn't feel flimsy). Not parametric;
// tune deflector_thickness / ramp_angle to shift it.
front_thickness = deflector_thickness - ramp_drop;
channel_width   = max(deflector_width - 2 * wall_thickness, 0.1);

// PRINT_ANCHOR_BBOX — outermost printed bbox (X, Y, Z) in mm at defaults.
// Raw prism extents. The ramp and channel cuts remove material from
// inside these bounds; they don't add to them.
PRINT_ANCHOR_BBOX = [deflector_width, deflector_depth, deflector_thickness];

// @preset id="aquor-72x100" label="Aquor 72×100mm (default)" bib_plate_width=72 bib_plate_height=100 deflector_width=70 deflector_depth=40 deflector_thickness=18 vhb_contact_depth=22 ramp_angle=15 corner_radius=3 channel_depth=4 wall_thickness=2.5

// === Geometry ===

// The base prism sits anchored with its back face at Y=0, build-plate
// side at Z=0, centered in X. BOSL2 `cuboid` defaults to CENTER anchor
// so we translate half-extents into place.
module main_prism() {
    translate([0, deflector_depth / 2, deflector_thickness / 2])
        cuboid(
            [deflector_width, deflector_depth, deflector_thickness],
            rounding = corner_radius,
            edges    = "Z"   // fillet only the four vertical corners
        );
}

// Diagonal cutter that shaves the top-forward material above the ramp
// plane. The cutter's bottom face passes through the pivot line at
// (Y=vhb_contact_depth, Z=deflector_thickness) and tilts down by
// ramp_angle, so the subtraction leaves a flat VHB zone at the rear
// and a clean ramp from there to the front.
module ramp_cutter() {
    big = 3 * max(deflector_width, deflector_depth, deflector_thickness);
    translate([0, vhb_contact_depth, deflector_thickness])
        rotate([-ramp_angle, 0, 0])
            translate([-big / 2, 0, 0])
                cube([big, big, big]);
}

// Channel pocket. Same tilt as the ramp cutter but shifted along the
// rotated normal by -channel_depth so the cutter's bottom face is
// channel_depth below the ramp surface. Narrower than the deflector
// in X (leaves wall_thickness sidewalls) and shorter in Y by
// wall_thickness at the back (keeps a tiny lip between the VHB zone
// and the channel floor — avoids a knife-edge where they meet).
module channel_cutter() {
    big = 3 * max(deflector_width, deflector_depth, deflector_thickness);
    translate([0, vhb_contact_depth + wall_thickness, deflector_thickness])
        rotate([-ramp_angle, 0, 0])
            translate([-channel_width / 2, 0, -channel_depth])
                cube([channel_width, big, big]);
}

module deflector() {
    difference() {
        main_prism();
        ramp_cutter();
        if (channel_depth > 0) channel_cutter();
    }
}

deflector();
