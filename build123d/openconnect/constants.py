"""openConnect dimensions with provenance (docs/provenance.md, design-guidelines §7).

Every value is [C]: read from the author's own CC BY 4.0 OpenSCAD source,
mitufy/opengrid-projects at commit 04e2277a71c5 (vendored verbatim under
assets/openConnect/). ``source`` names the file and ``locator`` is the
GitHub URL of the defining line at that commit. Derived values (mouth width,
head depth, the clearance-adjusted pocket levels) inherit [C] and cite the
line that defines the arithmetic; they are computed here, never typed.

Only the numbers this adapter uses are recorded. The connector-printing
constants (tile thicknesses, thread profile, fold gaps) do not shape the slot.
"""
from dataclasses import dataclass
from math import radians, tan


@dataclass(frozen=True)
class Provenance:
    value: float
    status: str
    source: str
    locator: str


UPSTREAM_REPO = 'https://github.com/mitufy/opengrid-projects'
UPSTREAM_COMMIT = '04e2277a71c5'
_BASE = 'lib/opengrid_base.scad'
_LIB = 'lib/openconnect_lib.scad'


def _cite(value: float, path: str, line: int) -> Provenance:
    return Provenance(value, 'C', f'mitufy/opengrid-projects {path}',
                      f'{UPSTREAM_REPO}/blob/{UPSTREAM_COMMIT}/{path}#L{line}')


# Roots (opengrid_base.scad).
EPS = 0.005
TILE_SIZE = 28.0                 # openGrid pitch; the only grid constant
HEAD_BOTTOM_HEIGHT = 0.6         # head flange band
HEAD_MIDDLE_HEIGHT = 1.4         # 45° dovetail taper
HEAD_TOP_HEIGHT = 0.6            # neck band at the mouth
HEAD_WIDTH = 17.0                # flange across X
HEAD_HEIGHT = 10.6               # flange along the slide axis
HEAD_CHAMFER = 4.0               # leading (seat-end) corner chamfers
NUB_TO_TOP_DISTANCE = 7.2
NUB_DEPTH = 0.6
NUB_TIP_HEIGHT = 1.2
NUB_FILLET = 0.8
BACK_POS_OFFSET = 0.4
MOVE_DISTANCE = 10.6             # on-ramp to seat travel
ONRAMP_CLEARANCE = 0.8

# Slot defaults and fixed shape numbers (openconnect_lib.scad).
EDGE_BRIDGE_MIN_W = 0.8
EDGE_WALL_MIN_W = 0.6
SIDE_CLEARANCE = 0.10
DEPTH_CLEARANCE = 0.10
NUB_FLANK_ANGLE = 45.0
ONRAMP_ROOF_HEIGHT = 4.0

# Derived.
HEAD_DEPTH = HEAD_BOTTOM_HEIGHT + HEAD_MIDDLE_HEIGHT + HEAD_TOP_HEIGHT   # 2.6
MOUTH_WIDTH = HEAD_WIDTH - 2 * HEAD_MIDDLE_HEIGHT                      # 14.2
# Default pocket: the flange band grows by the 22.5° chamfer share of the side
# clearance plus the depth clearance; the neck band shrinks by the same share.
POCKET_DEPTH = HEAD_DEPTH + DEPTH_CLEARANCE                             # 2.7
NUB_TAPER_SHIFT = HEAD_MIDDLE_HEIGHT - NUB_DEPTH                        # 0.8
# The on-ramp sits this far to -X of the slot axis at the flange band.
ONRAMP_SHIFT = ONRAMP_CLEARANCE + HEAD_MIDDLE_HEIGHT                    # 2.2


def half_angle_share(clearance: float) -> float:
    """BOSL2 ``ang_adj_to_opp(45 / 2, clearance)``: offset of a 45° chamfer edge."""
    return clearance * tan(radians(45 / 2))


PROVENANCE = {
    'EPS': _cite(EPS, _BASE, 3),
    'TILE_SIZE': _cite(TILE_SIZE, _BASE, 4),
    'HEAD_BOTTOM_HEIGHT': _cite(HEAD_BOTTOM_HEIGHT, _BASE, 43),
    'HEAD_TOP_HEIGHT': _cite(HEAD_TOP_HEIGHT, _BASE, 44),
    'HEAD_MIDDLE_HEIGHT': _cite(HEAD_MIDDLE_HEIGHT, _BASE, 45),
    'HEAD_WIDTH': _cite(HEAD_WIDTH, _BASE, 46),
    'HEAD_HEIGHT': _cite(HEAD_HEIGHT, _BASE, 47),
    'HEAD_CHAMFER': _cite(HEAD_CHAMFER, _BASE, 48),
    'NUB_TO_TOP_DISTANCE': _cite(NUB_TO_TOP_DISTANCE, _BASE, 50),
    'NUB_DEPTH': _cite(NUB_DEPTH, _BASE, 51),
    'NUB_TIP_HEIGHT': _cite(NUB_TIP_HEIGHT, _BASE, 52),
    'NUB_FILLET': _cite(NUB_FILLET, _BASE, 53),
    'BACK_POS_OFFSET': _cite(BACK_POS_OFFSET, _BASE, 55),
    'HEAD_DEPTH': _cite(HEAD_DEPTH, _BASE, 56),
    'MOVE_DISTANCE': _cite(MOVE_DISTANCE, _BASE, 59),
    'ONRAMP_CLEARANCE': _cite(ONRAMP_CLEARANCE, _BASE, 60),
    'MOUTH_WIDTH': _cite(MOUTH_WIDTH, _LIB, 27),
    'EDGE_BRIDGE_MIN_W': _cite(EDGE_BRIDGE_MIN_W, _LIB, 77),
    'EDGE_WALL_MIN_W': _cite(EDGE_WALL_MIN_W, _LIB, 78),
    'SIDE_CLEARANCE': _cite(SIDE_CLEARANCE, _LIB, 79),
    'DEPTH_CLEARANCE': _cite(DEPTH_CLEARANCE, _LIB, 80),
    'POCKET_DEPTH': _cite(POCKET_DEPTH, _LIB, 99),
    'NUB_TAPER_SHIFT': _cite(NUB_TAPER_SHIFT, _LIB, 274),
    'ONRAMP_SHIFT': _cite(ONRAMP_SHIFT, _LIB, 415),
    'NUB_FLANK_ANGLE': _cite(NUB_FLANK_ANGLE, _LIB, 307),
    'ONRAMP_ROOF_HEIGHT': _cite(ONRAMP_ROOF_HEIGHT, _LIB, 417),
}
