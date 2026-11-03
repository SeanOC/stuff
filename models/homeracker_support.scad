// SPDX-License-Identifier: CC-BY-SA-4.0
// Copyright (c) 2026 Sean O'Connor; upstream (c) 2025 Patrick Pötz
//
// HomeRacker support beams — 15 mm modular frame members
//
// Derived from HomeRacker by Patrick Pötz, commit 90556d1.
// Models and presets: CC BY-SA 4.0; see homeracker-LICENSE.md.
// HomeRacker is the author's unregistered trademark; no endorsement implied.
//
// === Print orientation ===
// Long side on the bed; 1 mm chamfers and 4 mm pin-hole bridges.
// units > 23 intentionally supports future large-bed frames (up to 750 mm);
// all supplied presets fit H2S/H2C. x_holes adds the second pinning axis.

include <homeracker/BOSL2/std.scad>
use <homeracker/models/core/lib/support.scad>

$fn = 100;  // Match the pinned upstream parts and reference meshes.

// === User-tunable parameters ===

units = 18; // @param integer min=1 max=50 step=1 group=beam label="Length (15 mm units)"
x_holes = false; // @param boolean group=beam label="Second pin-hole axis"

// @preset id="15u" label="15u / 225 mm (10U alternative posts)" units=15 x_holes=false
// @preset id="16u" label="16u / 240 mm (depth)" units=16 x_holes=false
// @preset id="17u" label="17u / 255 mm (width)" units=17 x_holes=false
// @preset id="18u" label="18u / 270 mm (12U posts)" units=18 x_holes=false

// === Geometry ===

// 15 mm square cross section; default length = 18 * 15 = 270 mm.
PRINT_ANCHOR_BBOX = [15, 270, 15];
support(units=units, x_holes=x_holes, anchor=BOT);
