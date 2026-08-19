// SPDX-License-Identifier: CC-BY-NC-SA-4.0
//
// Disney ear hanger — saddle hook for Disney-style ear headbands
// (Mickey/Minnie ears). Drapes over a wall ledge, shelf lip, or door
// top; the vertical tab faces out and the headbands hang on the arch.
//
// REMIX / ATTRIBUTION (this is a derivative work, not original):
//   Original: "Disney Ear Hanger" by the MakerWorld author at
//     https://makerworld.com/en/@profileId-469918
//   Source:  https://makerworld.com/en/models/551375-disney-ear-hanger
//   License: CC BY-NC-SA 4.0 (operator-verified — pst-15du). This is a
//     NON-COMMERCIAL license: do not sell prints or files, and share
//     any derivatives alike. Credit the original author on reshare.
//
// Our contribution over the upstream .scad is house-style integration
// only — @param exposure, a print-orientation anchor, and catalog +
// invariant wiring. The geometry is IDENTICAL to the upstream model at
// default parameters (pst-15du: an add, not a redesign); hangerLength
// only scales the saddle's span across the edge it hooks over.
//
// Print orientation (as delivered): arch up, tab up, saddle opening
// down — the natural upstream orientation. The inner arch is a bridge,
// so enable slicer support/bridging under the saddle if your printer
// struggles with the unsupported span. Reorienting the assembly would
// change the exported geometry and is deliberately out of scope for
// this vendoring bead — flag it as a follow-up if a flatter print
// orientation is wanted.

$fn = 50;

// === User-tunable parameters ===

hangerLength = 28;  // @param number min=15 max=60 step=1 unit=mm group=hanger label="Edge span (saddle width)"

// @preset id="standard" label="Standard (28mm edge)" hangerLength=28
// @preset id="wide"     label="Wide ledge (45mm)"    hangerLength=45

// === Derived ===

padding = 0.1;  // internal epsilon for clean CSG cuts; not user-tunable

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at defaults.
// X: hangerLength(28) + the two end flares (each reaches x = L/2 + 5) = 38.1
// Y: elliptical saddle (d35, y-scaled x2 -> Ø70) clipped by the ±55 side
//    cubes to ±32.5 = 65.0
// Z: saddle floor (min-Z 3.4 after the inner bore) up to the tab top
//    (z=25 + 9.5) = 34.5 -> 31.1 tall
PRINT_ANCHOR_BBOX = [38.1, 65, 31.1];

earHanger();

module earHanger()
{

    difference()
    {

        union()
        {

            // main shape
            translate([ 0, 0, 0 ]) baseShape(hangerLength);

            // hanging tab
            translate([ -hangerLength / 2 - 5, 0, 25 ]) rotate([ 0, 90, 0 ]) linear_extrude(height = 3)
            {
                offset(2) square(15, center = true);
            }

            // front end
            hull()
            {
                translate([ hangerLength / 2, 0, 0 ]) scale([ 1, 1, 1 ]) baseShape(0.1);

                translate([ hangerLength / 2 + 5, 0, 1 ]) scale([ 1, 1, 1.2 ]) baseShape(0.1);
            }

            // wall end
            hull()
            {
                translate([ -hangerLength / 2, 0, 0 ]) scale([ 1, 1, 1 ]) baseShape(0.1);

                translate([ -hangerLength / 2 - 5, 0, 1 ]) scale([ 1, 1, 1.2 ]) baseShape(0.1);
            }
        }

        translate([ 0, 0, -3 ]) rotate([ 0, 90, 0 ]) scale([ 1, 2, 2 ])
            cylinder(d = 35, h = hangerLength - 2, center = true);
    }
}

// this creates the main shape
module baseShape(height)
{

    difference()
    {

        translate([ 0, 0, 0 ]) rotate([ 0, 90, 0 ]) scale([ 1, 2, 1 ]) cylinder(d = 35, h = height, center = true);

        translate([ 0, 0, -20 ]) cube([ height + padding, 60, 30 ], center = true);

        translate([ 0, 55, 0 ]) cube([ height + padding, 45, 60 ], center = true);

        translate([ 0, -55, 0 ]) cube([ height + padding, 45, 60 ], center = true);
    }
}
