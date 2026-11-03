// SPDX-License-Identifier: CC-BY-SA-4.0
// Copyright (c) 2026 Sean O'Connor; upstream (c) 2025 Patrick Pötz
//
// HomeRacker rack panels — blank 10-inch or 19-inch panels
//
// Derived from HomeRacker by Patrick Pötz, commit 90556d1.
// Models and presets: CC BY-SA 4.0; see homeracker-LICENSE.md.
// HomeRacker is the author's unregistered trademark; no endorsement implied.
//
// === Print orientation ===
// Broad face down (rotate upstream XZ panel onto XY). Bores rise
// vertically and edges are chamfered; no supports. 19-inch panels and
// the 8U endpoint need a larger bed; the supplied 10-inch 1U/2U presets fit.

include <homeracker/BOSL2/std.scad>
use <homeracker/models/panel/lib/rackpanel.scad>

$fn = 100;  // Match the pinned upstream parts and reference meshes.

// === User-tunable parameters ===

width = "10in"; // @param enum choices=10in|19in group=panel label="Rack width"
height_units = 1; // @param integer min=1 max=8 step=1 unit=U group=panel label="Rack height"
bore_mode = "default"; // @param enum choices=default|all|minimal group=panel label="Mounting bores"

// @preset id="10in-1u" label="10-inch / 1U" width=10in height_units=1 bore_mode=default
// @preset id="10in-2u" label="10-inch / 2U" width=10in height_units=2 bore_mode=default

// === Geometry ===

// Upstream 254 x 2 x 44.45 mm panel, rotated 90 degrees about X.
PRINT_ANCHOR_BBOX = [254, 44.45, 2];
translate([0, 0, 1]) rotate([90, 0, 0])
    rackpanel(panel_width=width == "10in" ? 254 : 482.6,
              panel_height_units=height_units,
              bore_mode=bore_mode == "default" ? 0 : bore_mode == "all" ? 1 : 2);
