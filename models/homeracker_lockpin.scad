// SPDX-License-Identifier: CC-BY-SA-4.0
// Copyright (c) 2026 Sean O'Connor; upstream (c) 2025 Patrick Pötz
//
// HomeRacker lock pins — single pin or twenty-pin print plate
//
// Derived from HomeRacker by Patrick Pötz, commit 90556d1.
// Models and presets: CC BY-SA 4.0; see homeracker-LICENSE.md.
// HomeRacker is the author's unregistered trademark; no endorsement implied.
//
// === Print orientation ===
// Pin broad side down, tension slit through Z. No supports.
// 16 x 36 mm plate spacing also clears extended grips and both necks.

include <homeracker/BOSL2/std.scad>
use <homeracker/models/core/lib/lockpin.scad>

$fn = 100;  // Match the pinned upstream parts and reference meshes.

// === User-tunable parameters ===

grip = "standard"; // @param enum choices=standard|extended|none group=pin label="Grip"
neck = "none"; // @param enum choices=none|neck|both|tail group=pin label="Neck extension"
strength = "regular"; // @param enum choices=regular|slim group=pin label="Tension strength"
quantity = 1; // @param integer min=1 max=20 step=1 group=plate label="Pin count"

// @preset id="standard" label="Standard pin" grip=standard neck=none strength=regular quantity=1
// @preset id="plate-20" label="Twenty standard pins" grip=standard neck=none strength=regular quantity=20

// === Geometry ===

// Upstream default pin: 8 mm grip x 22.1 mm length x 3.8 mm thickness.
PRINT_ANCHOR_BBOX = [8, 22.1, 3.8];
grip_code = grip == "standard" ? 0 : grip == "extended" ? 1 : 2;
neck_code = neck == "none" ? 0 : neck == "neck" ? 1 : neck == "both" ? 2 : 3;
// Upstream constants (regular 4 / slim 6) define the tension-slot width.
strength_multiplier = strength == "regular" ? 4 : 6;
for (i = [0:quantity-1])
    translate([16 * (i % 5), 36 * floor(i / 5), 1.9])
        lockpin(grip_type=grip_code, neck_extension=neck_code,
                strength=strength_multiplier);
