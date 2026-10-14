# SPDX-License-Identifier: CC-BY-SA-4.0
"""[C] assets/openConnect-drawer/openconnect_drawer_online.scad.

Each locator below refers to that unmodified, SHA256-pinned source.
Mount dimensions remain in the existing openconnect library.
"""

MAGNET_HOLE_SIDE_CLEARANCE = 0.2  # [C] :380
MAGNET_HOLE_DEPTH_CLEARANCE = 0.15  # [C] :381
STOPPER_WIDTH = 4.8  # [C] :453
STOPPER_HEIGHT = 2.4  # [C] :454
STOPPER_ROUNDING = 0.4  # [C] :455
STOPPER_FLANK_WIDTH = 2.0  # [C] :456
STOPPER_FLANK_DEPTH = 0.8  # [C] :457
STOPPER_TO_EDGE_OFFSET = 0.0  # [C] :458-459: centre 14 mm from the edge
STOPPER_WIDTH_CLEARANCE = 0.2  # [C] :114
STOPPER_HEIGHT_CLEARANCE = 0.2  # [C] :115
BACK_MAGNET_OCSLOT_OFFSET = 4.6  # [C] :467; shell rule :1450-1462
HANDLE_CHAMFER = 0.4  # [C] :461
HONEYCOMB_UNIT = 14.0  # [C] :435; used by the later honeycomb port
HONEYCOMB_STRUT_HYP = 5.0  # [C] :118
# [C] docs/design-guidelines.md §1/§8; pst-t0ob3.2 REV 3 D2-R2.
MAX_BRIDGE_MM = 10.0
# docs/design-guidelines.md:46 minimum modelled hole; production closes every
# shell and container lattice opening whose largest inscribed circle is smaller
# (pst-t0ob3.3 DECISION C rev (b), pst-t0ob3.5). Source mode keeps the author's cells.
MIN_LATTICE_OPENING_MM = 2.0

# Local retention-domain decision (pst-t0ob3.1 REV 3e); measured with the
# mandatory bevel and unchanged openconnect-slot-shallow contract.
SLOT_SIDE_CLEARANCE_MAX = 0.3
SLOT_DEPTH_CLEARANCE_MAX = 0.5
