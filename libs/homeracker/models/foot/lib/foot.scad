// HomeRacker - Foot Insert
//
// This file is part of HomeRacker implementation by KellerLab.
// It contains the foot module — a connector insert that provides a contact surface
// for connectors at the bottom of a rack.
// The foot plugs into any connector arm from the outside
// and adds a wider base plate for load distribution and grip.
//
// MIT License
// Copyright (c) 2026 Patrick Pötz
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

include <homeracker/BOSL2/std.scad>
include <../../core/lib/constants.scad>
include <../../core/lib/support.scad>

HR_FOOT_PRIMARY_COLOR = HR_YELLOW;

/**
 * 📐 foot module
 *
 * Creates a foot insert for HomeRacker connectors.
 * The foot consists of three stacked parts (top to bottom):
 *   1. Support section: 1-unit support() with x_holes, oriented downward — plugs into a connector arm
 *   2. Spacer: inset shim (TOLERANCE/2 shift-out + BASE_CHAMFER inset) for flush transition at arm entry
 *   3. Base plate: wider platform (BASE_UNIT + BASE_STRENGTH*2 + TOLERANCE) for load distribution
 *
 * Parameters:
 *   debug_colors (bool, default=false): Use distinct HR_ colors per section for visualization.
 *   disable_chamfer (bool, default=false): Remove chamfers from all sections.
 *   anchor (vector, default=CENTER): BOSL2 anchor point.
 *   spin (number, default=0): BOSL2 spin rotation.
 *   orient (vector, default=UP): BOSL2 orientation vector.
 *
 * Usage:
 *   foot();
 *   foot(debug_colors=true);
 *   foot(disable_chamfer=true);
 */
module foot(debug_colors = false, disable_chamfer = false,
  anchor = CENTER, spin = 0, orient = UP) {

  attachable_side_length = BASE_UNIT + BASE_STRENGTH * 2 + TOLERANCE;
  spacer_height = TOLERANCE / 2;
  spacer_inset_addition = BASE_CHAMFER;
  attachable_height = BASE_UNIT + spacer_height + BASE_STRENGTH;

  attachable(anchor = anchor, spin = spin, orient = orient, size = [attachable_side_length, attachable_side_length, attachable_height]) {
    union() {
      // Equivalent explicit placement avoids deeply nested attach() evaluation
      // in OpenSCAD wasm. Sink the spacer 0.001 mm into the plate so CGAL's
      // float rounding cannot split the face-touching original into two solids.
      up(BASE_STRENGTH / 2 + spacer_height / 2)
        support(units = 1, x_holes = true, debug_colors = debug_colors,
                disable_chamfer = disable_chamfer, orient = FRONT);
      down(attachable_height / 2 - BASE_STRENGTH / 2)
        cuboid([attachable_side_length, attachable_side_length, BASE_STRENGTH],
               chamfer = disable_chamfer ? 0 : BASE_CHAMFER, except = TOP);
      down(attachable_height / 2 - BASE_STRENGTH - (spacer_height + spacer_inset_addition) / 2 + 0.0005)
        cuboid([BASE_UNIT, BASE_UNIT, spacer_height + spacer_inset_addition + 0.001],
               chamfer = disable_chamfer ? 0 : BASE_CHAMFER, except = [TOP, BOTTOM]);
    }
    children();
  }

}
