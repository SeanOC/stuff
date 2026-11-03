// SPDX-License-Identifier: CC-BY-SA-4.0
// Copyright (c) 2026 Sean O'Connor; upstream (c) 2025 Patrick Pötz
//
// HomeRacker foot — broad contact plate with connector insert
//
// Derived from HomeRacker by Patrick Pötz, commit 90556d1.
// Models and presets: CC BY-SA 4.0; see homeracker-LICENSE.md.
// HomeRacker is the author's unregistered trademark; no endorsement implied.
//
// === Print orientation ===
// Broad 19.2 mm plate down, insert upwards. Chamfered rim and short
// square pin-hole bridges print without supports.

include <homeracker/BOSL2/std.scad>
use <homeracker/models/foot/lib/foot.scad>

$fn = 100;  // Match the pinned upstream parts and reference meshes.

// === User-tunable parameters ===

// Fixed mating dimensions: 15 mm insert, 0.2 mm upstream tolerance.
// @preset id="standard" label="Standard foot"

// === Geometry ===

// Upstream plate = 15 + 2*2 + 0.2; height = 15 + 2 + 0.1 mm.
PRINT_ANCHOR_BBOX = [19.2, 19.2, 17.1];
foot(anchor=BOT);
