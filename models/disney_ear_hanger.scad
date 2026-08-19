// SPDX-License-Identifier: CC-BY-NC-SA-4.0
//
// Disney ear hanger — saddle hanger for Disney-style ear headbands
// (Mickey/Minnie ears). Wall-mounts with double-sided tape or 3M
// Command strips: stick the flat mounting face to the wall, and the
// headbands drape over the saddle arch that projects out from it.
//
// REMIX / ATTRIBUTION (this is a derivative work, not original):
//   Original: "Disney Ear Hanger" by SpruceWayne
//     Creator: https://makerworld.com/en/@user_2791005939
//     Model:   https://makerworld.com/en/models/551375-disney-ear-hanger
//   (The MakerWorld id 469918 is the default print-profile/instance,
//    not an author profile.)
//   License: CC BY-NC-SA 4.0 (operator-verified — pst-15du). This is a
//     NON-COMMERCIAL license: do not sell prints or files, and share
//     any derivatives alike. Credit SpruceWayne on reshare.
//
// Our contribution over the upstream .scad is house-style integration
// only — @param exposure, a print-orientation anchor, and catalog +
// invariant wiring. The geometry is IDENTICAL to the upstream model at
// default parameters (pst-15du: an add, not a redesign); hangerLength
// only scales how far the saddle projects out from the wall.
//
// Print orientation: the top-level call is rigidly rotated so the flat
// mounting face (the tab and the saddle end) lies on the bed and the
// arch extrudes straight up. This is the upstream orientation — no
// special settings are needed (the vertical cross-section is constant,
// so no supports), and the broad mounting face prints against the
// plate. Keep that face smooth — print it against a smooth plate so the
// tape / 3M Command strip bonds to a smooth, clean, dry surface (their
// adhesive is rated for smooth surfaces; plate texture weakens the bond).
// The rotate/translate wraps only the top-level call; the earHanger()
// body geometry is unchanged (pst-yfml finding #1).

$fn = 50;

// === User-tunable parameters ===

hangerLength = 28;  // @param number min=15 max=60 step=1 unit=mm group=hanger label="Projection (saddle depth off wall)"

// Hanging tab — the rounded-square fin on the flat mounting face at the
// wall end that the whole hanger hooks / mounts by. It is square by
// nature (the upstream source is `square(15)`), so a single size drives
// both width and height. `tabRounding` is the corner radius, which also
// grows the plate outward by that radius (offset semantics); `tabThickness`
// is how far the fin stands off the wall face. Defaults reproduce the
// upstream geometry byte-for-byte.
tabSize      = 15;  // @param number min=8 max=30 step=1   unit=mm group=tab label="Tab size (square side)"
tabThickness = 3;   // @param number min=2 max=6  step=0.5 unit=mm group=tab label="Tab thickness (stand-off)"
tabRounding  = 2;   // @param number min=0 max=5  step=0.5 unit=mm group=tab label="Tab corner rounding"

// @preset id="standard"   label="Standard (28mm projection)" hangerLength=28
// @preset id="deep"       label="Deep (45mm projection)"     hangerLength=45
// @preset id="chunky-tab" label="Chunky mounting tab"        tabSize=22 tabThickness=4 tabRounding=3

// === Derived ===

padding = 0.1;  // internal epsilon for clean CSG cuts; not user-tunable

// Tab seat: the fin is anchored by its BOTTOM edge at tabSeatZ and grows
// UPWARD as tabSize/tabRounding increase, rather than being centred on a
// fixed z. tabSeatZ (15.5) sits ~2-6mm inside the arch's wall-end
// shoulder, whose cross-section here is independent of every @param — so
// a fixed seat keeps the fin fused to the body across the whole size
// range: a smaller tab can't lift off the arch, a larger one just stands
// taller. Deriving the centre from the seat (not hardcoding z=25) is
// PR #65 round-2's no-default-only-seating rule applied to the tab
// (pst-wjte). tabCenterZ evaluates to 25 at defaults, so default geometry
// is unchanged.
tabSeatZ   = 15.5;
tabCenterZ = tabSeatZ + tabSize / 2 + tabRounding;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at defaults,
// measured in the print orientation below (flat mounting face on the bed,
// arch pointing up). Verified against the exported STL, not hand-derived.
// X (31.1): TAB-DEPENDENT. The print rotate maps the body-Z axis to
//    build-X, so this spans from the arch's lowest interior point
//    (body z ~= 3.4) up to the tab's top edge (body z = tabCenterZ +
//    tabSize/2 + tabRounding = 34.5 at defaults). Raising tabSize or
//    tabRounding raises the tab top and therefore this extent — 31.1
//    holds only at default tab params.
// Y (65.0): saddle width across the two ±32.5 side clips — arch-only and
//    param-independent (the tab half-width tabSize/2+tabRounding stays
//    well inside ±32.5 over its whole range, so it never drives Y).
// Z (38.1): vertical print height = hangerLength(28) + the two end flares
//    (each +5), i.e. the body-X span mapped to build-Z. hangerLength-
//    dependent; independent of the tab.
PRINT_ANCHOR_BBOX = [31.1, 65, 38.1];

// Print-orientation transform (pst-yfml finding #1): rigidly rotate the
// top-level model so the flat mounting face lies on the bed (arch up),
// then centre in X/Y and seat min-Z at 0. Body geometry is unchanged.
// The Z seat is parameter-derived: after rotate([0,-90,0]) the body's
// X-extent [-(hangerLength/2+5.05), +(hangerLength/2+5.05)] becomes the
// build-Z span, so the offset must track hangerLength (pst-t9ri finding
// #1). At the 28mm default this evaluates to 19.05, matching the prior
// constant; short/deep/max presets now also seat min-Z at 0.
translate([ 18.95, 0, hangerLength / 2 + 5.05 ]) rotate([ 0, -90, 0 ]) earHanger();

module earHanger()
{

    difference()
    {

        union()
        {

            // main shape
            translate([ 0, 0, 0 ]) baseShape(hangerLength);

            // hanging tab
            translate([ -hangerLength / 2 - 5, 0, tabCenterZ ]) rotate([ 0, 90, 0 ]) linear_extrude(height = tabThickness)
            {
                offset(tabRounding) square(tabSize, center = true);
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
