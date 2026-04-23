// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Cartoonish popped popcorn kernel — replacement piece for a Disney
// toddler-toy popcorn stand. Union of overlapping spheres so each sphere
// reads as a visible popcorn "lobe"; sphere-sphere intersections are smooth
// concave creases (no sharp edges, toddler-safe). Solid interior.

$fn = 96;

// === User-tunable parameters ===
base_cut = 4;  // @param number min=2 max=10 step=0.5 unit=mm group=geometry label="Base flat-cut"

// === PRINT_ANCHOR_BBOX ===
// Raw union bbox (from sphere extents listed below):
//   X [-25, 23] = 48,  Y [-22, 20] = 42,  Z [-14, 34] = 48
// After translate +Z 14 and chop at z = base_cut = 4:
//   X 48,  Y 42,  Z 48 - 4 = 44
PRINT_ANCHOR_BBOX = [48, 42, 44];

// === Lobe spheres ===
// Hand-picked centers + radii (no OpenSCAD rands, so the bbox above stays a
// literal value). One wide base sphere + 6 jittered upper lobes/bumps.
lobes = [
    [[  0,   0,  4], 18],  // wide base (stability + fattest middle)
    [[ 11,   8, 14], 12],  // back-right lobe
    [[-12,  -2, 13], 13],  // left lobe
    [[  4, -11, 12], 11],  // front lobe
    [[ -4,  10, 22], 10],  // top-back bump
    [[  8,  -2, 23],  9],  // top-right bump
    [[ -2,   0, 28],  6],  // crown
];

module kernel_lobes() {
    union() {
        for (s = lobes)
            translate(s[0]) sphere(r = s[1]);
    }
}

module popped_kernel() {
    // Lift so lowest sphere point sits at z = 0, then chop the bottom
    // base_cut mm with a half-space so the print rests on a flat circle.
    translate([0, 0, -base_cut])
    intersection() {
        translate([0, 0, 14]) kernel_lobes();
        translate([0, 0, base_cut + 100])
            cube([300, 300, 200], center = true);
    }
}

popped_kernel();
