// SPDX-License-Identifier: CC-BY-SA-4.0
// Copyright (c) 2026 Sean O'Connor; upstream (c) 2025 Patrick Pötz
//
// HomeRacker connectors — frame corners and through joints
//
// Derived from HomeRacker by Patrick Pötz, commit 90556d1.
// Models and presets: CC BY-SA 4.0; see homeracker-LICENSE.md.
// HomeRacker is the author's unregistered trademark; no endorsement implied.
//
// === Print orientation ===
// Upstream optimal_orientation=true rests the connector on its chamfered
// print interface. Slicer auto-drop places it on the bed; do not stand a
// socket upright. The 3D3W and 3D4W presets need no supports.
// Upstream clamps directions to dimensions..2*dimensions (1..2 in 1D).

include <homeracker/BOSL2/std.scad>
use <homeracker/models/core/lib/connector.scad>

$fn = 100;  // Match the pinned upstream parts and reference meshes.

// === User-tunable parameters ===

dimensions = 3; // @param integer min=1 max=3 step=1 group=joint label="Dimensions"
directions = 3; // @param integer min=1 max=6 step=1 group=joint label="Directions (clamped by dimensions)"
pull_through_axis = "none"; // @param enum choices=none|x|y|z group=joint label="Pull-through axis"

// @preset id="3d3w" label="3D3W / top corners" dimensions=3 directions=3 pull_through_axis=none
// @preset id="3d4w" label="3D4W / bottom and middle" dimensions=3 directions=4 pull_through_axis=none
// @preset id="3d4w-pull-through-z" label="3D4W / continuous Z post" dimensions=3 directions=4 pull_through_axis=z

// === Geometry ===

// Measured upstream optimal orientation; unchanged geometry and coordinates.
PRINT_ANCHOR_BBOX = [43.98204, 32.1, 33.44615];
connector(dimensions=dimensions, directions=directions,
          pull_through_axis=pull_through_axis, optimal_orientation=true);
