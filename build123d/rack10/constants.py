"""Rack10 dimensions (mm), original geometry; provenance: docs/rack10.md.

[C] E1 = task pst-go6df.1, CANONICAL rev 1, invariants 1/3/4 (2026-11-02).
[C] OR = dduxx/openRack scad/lib/rack_units.scad, named assignments below:
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
PANEL_SHORT = 0.8  # [C] E1, shared equally between the two U boundaries
SCREW_CLEAR = 6.4  # [C] initial E1, M6 nominal clearance; actual aperture uses EAR_HOLE_D
EAR_HOLE_D = 7.0  # [C] E1 rev 1
MAX_SLOT_MM = 8.0  # [C] E1 rev 1, overall vertical length; 0 means round
PANEL_THICKNESS = 3.0  # [C] E1
EAR_THICKNESS = 4.0  # [C] E1
HOLES_PER_UNIT = 3  # [C] E1; OR HOLES_PER_UNIT
TRAY_SIDE_MARGIN = 1.0  # [C] E1: (CLEAR_OPENING - 220.25) / 2
TRAY_OUTER_WIDTH_LIMIT = CLEAR_OPENING - 2 * TRAY_SIDE_MARGIN
KEYSTONE_WIDTH = 14.5  # [C] E1, front window
KEYSTONE_HEIGHT = 16.0  # [C] E1, front window
KEYSTONE_PITCH = 19.0  # [C] E1
MAX_KEYSTONES = int(USABLE_WIDTH // KEYSTONE_PITCH)
# Original design dimensions, not claims of a measured hardware fit.
MIN_WALL_MM = 0.9  # [C] docs/design-guidelines.md section 1
EDGE_CHAMFER = 0.3  # [C] section 1: 0.3–0.5 mm bed relief
PANEL_CORNER = 4.0  # [C] section 1: broad flat corner radius >= 4
RAIL_WALL = 2.4  # Original load-bearing rail dimension, >= 1.6 mm
FLOOR = 3.0  # Original load-bearing floor dimension
RAIL_HEIGHT = 8.0  # Original rear retaining rail height above floor
KEYSTONE_LATCH_WALL = 2.5  # [C] davidwkeith/rack-build README: 1U keystone panel
KEYSTONE_RELIEF = 1.6  # Rear clearance per end; 16 + 2*1.6 = 19.2 mm [C] Delock 67068 port height
TIE_WIDTH = 3.0  # Original zip-tie aperture (>= 2 mm)
TIE_LENGTH = 8.0  # Original zip-tie aperture, with 45-degree peaked ceiling

# [C] E2b = pst-go6df.4 rev 4, invariants 1–2 and round-3 PASS.
# [C] HR = HomeRacker 90556d1, models/core/lib/constants.scad:31,38,44;
# support.scad:62–71,103–129; connector.scad:33 (full paths in rack10-frame.md).
# [C] Harrison Silverdale Series 20103, row TH060H090 (hole / length / min wall):
# https://www.harrisonsilverdale.com/products/details/thermocert-heatstake-insert-for-thermoplastic72.html
INSERT_M6_HOLE_D = 8.0  # [C] E2b; Harrison Silverdale series 20103 TH060H090 hole column
INSERT_M6_LEN = 9.0  # [C] TH060H090 length H
INSERT_WALL_MIN = 2.0  # [C] TH060H090 minimum wall E
INSERT_POCKET_DEPTH = INSERT_M6_LEN + 0.5  # [C] E2b
RAIL_WIDTH = 31.0  # [C] E2b
RAIL_FLANGE = 16.0  # [C] E2b
RAIL_THICKNESS = 12.0  # [C] E2b
RAIL_MAX_UNITS = 27  # [C] E2b: (15*27+31)/sqrt(2)=308.3 on 325x320 bed; 28 leaves only 1 mm
PEG_SQUARE = 4.0  # [C] HR LOCKPIN_HOLE_SIDE_LENGTH (nominal throat)
PEG_PITCH = 15.0  # [C] HR BASE_UNIT
PEG_TOL = 0.2  # [C] HR TOLERANCE; E2b round-3 A4 applies to peg width
POST_INNER_SPAN = 255.0  # [C] E2b, 17 HomeRacker units
RAIL_HOLE_X = PEG_PITCH + (POST_INNER_SPAN-HOLE_SPAN)/2  # [C] E2b
SLEEVE_RELIEF_D = 2.1  # [C] HR: (19.2 mm sleeve - 15 mm post)/2
SLEEVE_RELIEF_W = PEG_PITCH + SLEEVE_RELIEF_D  # [C] E2b round-3 A1
CAGE_WEB = 2.0  # [C] E2b
PEG_LENGTH = PEG_PITCH - PEG_TOL  # Original straight peg, stays inside post
PEG_ROOT = 0.8  # Original overlap into the bar; 0.3 mm finish fits the flared mouth
