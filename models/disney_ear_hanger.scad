// SPDX-License-Identifier: LicenseRef-MakerWorld-unverified
// Vendored model — original by an upstream MakerWorld author (st-w2g).
// Source:    https://makerworld.com/en/models/551375-disney-ear-hanger
// Profile:   https://makerworld.com/en/@profileId-469918
// Imported:  2026-05-01
//
// We did not author this model. The MakerWorld page was Cloudflare-
// gated when this file was vendored, so the upstream author's display
// name and the model's specific license badge could not be captured
// programmatically. The SPDX line above is a placeholder — replace
// `LicenseRef-MakerWorld-unverified` with the correct license tag
// (e.g. CC-BY-4.0, CC-BY-NC-4.0, CC-BY-SA-4.0, CC-BY-NC-SA-4.0, or
// LicenseRef-MakerWorld-<short-tag>) once the page can be opened in
// a browser. Do not relicense without checking the upstream listing.
//
// Contributions to this file should be minimal and respect the
// upstream author's design intent. If the model needs structural
// changes, prefer reaching out to the upstream author or forking
// with explicit derivative attribution. Don't claim copyright.
//
// Print orientation: see upstream listing — the MakerWorld page hosts
// the canonical print profile and orientation guidance.
// Install context: ear hanger — most likely a wall-mount or shelf-edge
// clip that hooks Disney-style ear headbands (Mickey/Minnie ears).
// Polecat: confirm with user before adding install-side fillets,
// keying, or surface treatments.
//   (See mayor memory feedback_confirm_install_orientation_for_wallmount_parts.md.)

$fn = 50;

hangerLength = 28;
padding = 0.1;

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
