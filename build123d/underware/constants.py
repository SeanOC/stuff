# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""[C] monokini_I_channel.scad (Underware for openGrid upload, SHA256 in
assets/underware-opengrid/NOTICE); locators are that file's lines.

The upload is not committed (CC BY-NC-SA, epic pst-fsk8s D0 outcome (b)).
Twelve of the thirteen files share this hidden block; the cross-file module
hashes are pinned in tests/underware_module_hashes.json.
"""
from math import sqrt

GRID = 28.0                    # [C] :102 Grid_Size
CHANNEL_SEPARATION = 0.8       # [C] :103 channelWidthSeparation
BASE_HEIGHT = 3.40             # [C] :106 grip height above the wall top
TOP_HEIGHT = 18.60             # [C] :107 (attachable box only; no geometry)
TOP_CHAMFER = 4.0              # [C] :112 45 degree exterior chamfer
SNAP_WALL = 2.0                # [C] :114 wall, floor and grip thickness
GRIP_SIZE = 15.0               # [C] :115 grip length along the channel
MIN_WALL = 0.4                 # [C] :116 minWall with Decorative=false
NUDGE = 0.01                   # [C] :113 (only the flare slits keep it)

# monokiniGrip locals [C] :208-211 (baseChamfer :209 is unused upstream).
SNAP_CAPTURE = 0.7             # nub undercut depth
TOP_LITTLE_CHAMFER = 0.4       # nub top chamfer height
SPACING_FROM_CHANNEL = 6.5     # grip start from the cell start

# Grip-end top ramp: the :233-252 triangles leave a 45 degree cut that starts
# SNAP_WALL below the grip top (reference i-1x5-h22.stl, y 63.495 at z 20,
# 61.495 at z 22).
GRIP_RAMP = SNAP_WALL
# monokiniGripFlaredCut [C] :426-441: relief slits beside each flared grip.
FLARE_SLIT = TOP_LITTLE_CHAMFER
FLARE_SLIT_DEPTH = 2*SNAP_WALL + 0.01

# Cord cutouts [C] :143-190.
CUTOUT_DEPTH = 2*TOP_CHAMFER   # side cutout cylinder/box length across the wall
TOP_CUTOUT_Z = SNAP_WALL + TOP_HEIGHT/2 - BASE_HEIGHT + SNAP_WALL  # 9.9: :151 centre
# OpenSCAD text(size=s) sets the em to s/0.72 (FreeType 72 dpi points):
# [V] i-1x5-h22-label.stl ink 10.39 mm across = Inter Bold caps at em 13.89.
OPENSCAD_TEXT_SCALE = 1/0.72

INNER_CHAMFER = SNAP_WALL + SNAP_WALL*sqrt(2)  # 4.828: inset chamfer corner


def channel_width(units: int) -> float:
    """[C] :104 channelWidth = Grid_Size - 2*separation + (units-1)*Grid_Size."""
    return GRID - 2*CHANNEL_SEPARATION + (units-1)*GRID
