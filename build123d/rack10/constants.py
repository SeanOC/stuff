"""Rack10 interface dimensions, mm; provenance and pending decision in docs/rack10.md.

[C] E1 = task pst-go6df.1, description invariants 1, 3 and 4 (2026-11-02).
These are the requested interface, not a claim of measured hardware fit.
[C] OR = dduxx/openRack scad/lib/rack_units.scad, named assignments below;
https://github.com/dduxx/openRack/blob/main/scad/lib/rack_units.scad
No upstream geometry or source is copied into this package.
"""

RACK_UNIT = 44.45  # [C] E1; OR RACK_UNIT = 7/4 inch
HOLE_PITCH = 15.875  # [C] E1; OR RACK_UNIT_HOLE_SPACING = 5/8 inch
HOLE_EDGE = 6.35  # [C] E1; OR RACK_UNIT_HOLE_BOTTOM_EDGE_OFFSET = 1/4 inch
EAR_WIDTH = 254.0  # [C] E1; OR TEN_INCH_STANDARD_WIDTH = 10 inch
HOLE_SPAN = 236.525  # [C] E1, explicitly required (not rounded 9.3125 inch)
CLEAR_OPENING = 222.25  # [C] E1
USABLE_WIDTH = 210.0  # [C] E1
CAGE_SQUARE = 9.525  # [C] E1; OR RACK_SQUARE_HOLE_XY = 3/8 inch
PANEL_SHORT = 0.8  # [C] E1
SCREW_CLEAR = 6.4  # [C] E1, M6 clearance
EAR_SLOT_WIDTH = 7.0  # [C] E1
EAR_SLOT_HEIGHT = 10.0  # [C] E1, total vertical slot length
PANEL_THICKNESS = 3.0  # [C] E1 invariant 3
EAR_THICKNESS = 4.0  # [C] E1 invariant 3
HOLES_PER_UNIT = 3  # [C] E1; OR HOLES_PER_UNIT
TRAY_SIDE_MARGIN = 1.0  # [C] E1: (CLEAR_OPENING - 220.25) / 2
TRAY_OUTER_WIDTH_LIMIT = CLEAR_OPENING - 2 * TRAY_SIDE_MARGIN
KEYSTONE_WIDTH = 14.5  # [C] E1, window width; latch profile remains unspecified
KEYSTONE_HEIGHT = 16.0  # [C] E1, window height
KEYSTONE_PITCH = 19.0  # [C] E1
MAX_KEYSTONES = int(USABLE_WIDTH // KEYSTONE_PITCH)
