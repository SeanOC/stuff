// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Tapered-bullet stylus for a child's pressure-sensitive LCD drawing pad
// (Boogie-Board-style film tablet, where pressing darkens the line). No
// electronics — pure geometry. The tip just needs to be firm, smooth, and
// rounded enough to press a clean line without scratching or puncturing the
// film. Smooth round body (7.5 mm max) tapering to a ~2 mm rounded dome tip,
// ~90 mm long for a small hand, no hard edges anywhere. Prints tip-up,
// vertical, support-free: the taper only narrows going up (self-supporting),
// the base rim rolls over into a flat circle, and the only rough spot is the
// very tip pole (minor, sandable).
//
// Geometry: hull of two spheres along the axis — a fat bottom bulb (radius =
// body_diameter/2) and a small tip sphere (radius = tip_radius). The hull is
// the smooth tangent envelope between them, so the whole surface is C1 round
// with no hard edges. A flat base-cut (intersection with a half-space, like
// popcorn_kernel) shaves base_flat off the bottom so the part rests on a flat
// circle; the shallow cut leaves the rim softly rounded.

$fn = 128;

// === User-tunable parameters ===
body_diameter = 7.5;  // @param number min=5 max=10 step=0.5 unit=mm group=geometry label="Body max diameter"
total_length  = 90;   // @param number min=70 max=140 step=1 unit=mm group=geometry label="Total length"
tip_radius    = 2;    // @param number min=1 max=3.75 step=0.25 unit=mm group=geometry label="Tip dome radius"
base_flat     = 1.5;  // @param number min=0.5 max=4 step=0.5 unit=mm group=geometry label="Base flat-cut depth"

// @preset id="default" label="Default" body_diameter=7.5 total_length=90 tip_radius=2 base_flat=1.5

// === PRINT_ANCHOR_BBOX ===
// Full hull spans z [0, total_length]; max radius is the bottom bulb radius
// body_diameter/2, so X = Y = body_diameter. The base-cut shaves base_flat
// off the bottom, so Z = total_length - base_flat.
//   X 7.5,  Y 7.5,  Z 90 - 1.5 = 88.5
PRINT_ANCHOR_BBOX = [7.5, 7.5, 88.5];

module stylus_solid() {
    R  = body_diameter / 2;  // bottom bulb radius (== max body radius)
    rt = tip_radius;         // tip dome radius
    // Bottom bulb sits tangent to z=0; tip sphere sits tangent to z=total_length.
    hull() {
        translate([0, 0, R])                sphere(r = R);
        translate([0, 0, total_length - rt]) sphere(r = rt);
    }
}

module stylus() {
    // Shave base_flat off the bottom with a half-space, then drop the cut
    // face onto z=0 so the model stands tip-up on its flat base.
    translate([0, 0, -base_flat])
    intersection() {
        stylus_solid();
        translate([0, 0, base_flat + 150])
            cube([300, 300, 300], center = true);
    }
}

stylus();
