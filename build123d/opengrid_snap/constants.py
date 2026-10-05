# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# openGrid design: David D; OpenSCAD: metasyntactic (QuackWorks).
# Port of QuackWorks/openGrid/opengrid-snap.scad @6123129 + local patch 0001.
"""[C] constants from the patched, pinned source (line numbers preserved).

Source: https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad
Local patch: scripts/patches/QuackWorks/0001-opengrid-snap-linear-extrude-click-holes.patch.
Every dimensional literal below cites its defining source line. BOSL2's $fn=2
vertical rounding becomes an octagonal outline (one diagonal per corner).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    value: float
    status: str
    source: str
    locator: str


CORE_WIDTH = 24.8  # [C] opengrid-snap.scad:37
FULL_EXTRA = 3.4  # [C] opengrid-snap.scad:38
LITE_HEIGHT = 3.4  # [C] opengrid-snap.scad:39
CORE_HEIGHT = 3.0  # [C] opengrid-snap.scad:42
TOP_HEIGHT = 0.4  # [C] opengrid-snap.scad:43
TOP_NUB_HEIGHT = 1.1  # [C] opengrid-snap.scad:44
TOP_CORNER = 3.262743  # [C] opengrid-snap.scad:48
CORE_CORNER = 4.81837  # [C] opengrid-snap.scad:50
TOP_NUB_OFFSET = 2.02  # [C] opengrid-snap.scad:52
TOP_NUB_WIDTH = 6.817  # [C] opengrid-snap.scad:55
OVERLAP = 0.01  # [C] opengrid-snap.scad:26
NUB_TOP = 2.0  # [C] opengrid-snap.scad:26
NUB_HEIGHT = 0.2  # [C] opengrid-snap.scad:62
NUB_WIDTH = 11.0  # [C] opengrid-snap.scad:63
NUB_DEPTH = 0.4  # [C] opengrid-snap.scad:64
NUB_TOP_WEDGE = 0.6  # [C] opengrid-snap.scad:65
NUB_BOTTOM_WEDGE = 0.6  # [C] opengrid-snap.scad:66
NUB_ROUND_X = -12.36  # [C] opengrid-snap.scad:67
NUB_ROUND_SCALE = 1.36  # [C] opengrid-snap.scad:68
NUB_ROUND_RADIUS = 13.025  # [C] opengrid-snap.scad:69
BOTTOM_WEDGE_DEPTH = 0.4  # [C] opengrid-snap.scad:30
FRONT_HEIGHT = 0.0  # [C] opengrid-snap.scad:78
FRONT_WIDTH = 14.0  # [C] opengrid-snap.scad:79
FRONT_DEPTH = 0.8  # [C] opengrid-snap.scad:80
FRONT_TOP_WEDGE = 1.0  # [C] opengrid-snap.scad:81
FRONT_BOTTOM_WEDGE = 0.4  # [C] opengrid-snap.scad:82
FRONT_ROUND_X = -11.75  # [C] opengrid-snap.scad:83
FRONT_ROUND_SCALE = 1.26  # [C] opengrid-snap.scad:84
FRONT_ROUND_RADIUS = 13.025  # [C] opengrid-snap.scad:85
FRONT_BOTTOM_SHIFT = -0.4  # [C] opengrid-snap.scad:86
REAR_HEIGHT = 0.65  # [C] opengrid-snap.scad:92
REAR_WIDTH = 10.8  # [C] opengrid-snap.scad:93
REAR_DEPTH = 0.4  # [C] opengrid-snap.scad:94
REAR_TOP_WEDGE = 0.6  # [C] opengrid-snap.scad:95
REAR_BOTTOM_WEDGE = 0.6  # [C] opengrid-snap.scad:96
REAR_ROUND_X = -12.41  # [C] opengrid-snap.scad:97
REAR_ROUND_SCALE = 1.37  # [C] opengrid-snap.scad:98
REAR_ROUND_RADIUS = 13.025  # [C] opengrid-snap.scad:99
CLICK_OFFSET = 1.0  # [C] opengrid-snap.scad:105
CLICK_DEPTH = 0.6  # [C] opengrid-snap.scad:107
CLICK_WIDTH = 12.4  # [C] opengrid-snap.scad:107
CLICK_RADIUS = 0.3  # [C] opengrid-snap.scad:107
CLICK_ROOF = 2.8  # [C] opengrid-snap.scad:107
REAR_CLICK_START = 0.599  # [C] opengrid-snap.scad:110
REAR_CLICK_HEIGHT = 2.2  # [C] opengrid-snap.scad:110
REAR_CLICK_OFFSET = 1.2  # [C] opengrid-snap.scad:111
REAR_CLICK_RISE = 0.6  # [C] opengrid-snap.scad:111
REAR_CLICK_SHIFT = 0.2  # [C] opengrid-snap.scad:111
REAR_RELIEF_OFFSET = 0.1  # [C] opengrid-snap.scad:112
REAR_RELIEF_DEPTH = 0.2  # [C] opengrid-snap.scad:112
REAR_RELIEF_WIDTH = 20.0  # [C] opengrid-snap.scad:112
REAR_RELIEF_HEIGHT = 0.6  # [C] opengrid-snap.scad:112
WALL_CLICK_HEIGHT = 2.2  # [C] opengrid-snap.scad:117
WALL_CLICK_DEPTH = 1.4  # [C] opengrid-snap.scad:119
WALL_CLICK_WIDTH = 12.0  # [C] opengrid-snap.scad:119
WALL_CLICK_THICKNESS = 0.4  # [C] opengrid-snap.scad:119
INDICATOR_X = 9.5  # [C] opengrid-snap.scad:122
INDICATOR_BOTTOM_RADIUS = 2.0  # [C] opengrid-snap.scad:122
INDICATOR_TOP_RADIUS = 1.5  # [C] opengrid-snap.scad:122
INDICATOR_HEIGHT = 0.4  # [C] opengrid-snap.scad:122

PROVENANCE = {
    "CORE_WIDTH": Provenance(CORE_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L37"),
    "FULL_EXTRA": Provenance(FULL_EXTRA, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L38"),
    "LITE_HEIGHT": Provenance(LITE_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L39"),
    "CORE_HEIGHT": Provenance(CORE_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L42"),
    "TOP_HEIGHT": Provenance(TOP_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L43"),
    "TOP_NUB_HEIGHT": Provenance(TOP_NUB_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L44"),
    "TOP_CORNER": Provenance(TOP_CORNER, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L48"),
    "CORE_CORNER": Provenance(CORE_CORNER, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L50"),
    "TOP_NUB_OFFSET": Provenance(TOP_NUB_OFFSET, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L52"),
    "TOP_NUB_WIDTH": Provenance(TOP_NUB_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L55"),
    "OVERLAP": Provenance(OVERLAP, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L26"),
    "NUB_TOP": Provenance(NUB_TOP, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L26"),
    "NUB_HEIGHT": Provenance(NUB_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L62"),
    "NUB_WIDTH": Provenance(NUB_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L63"),
    "NUB_DEPTH": Provenance(NUB_DEPTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L64"),
    "NUB_TOP_WEDGE": Provenance(NUB_TOP_WEDGE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L65"),
    "NUB_BOTTOM_WEDGE": Provenance(NUB_BOTTOM_WEDGE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L66"),
    "NUB_ROUND_X": Provenance(NUB_ROUND_X, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L67"),
    "NUB_ROUND_SCALE": Provenance(NUB_ROUND_SCALE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L68"),
    "NUB_ROUND_RADIUS": Provenance(NUB_ROUND_RADIUS, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L69"),
    "BOTTOM_WEDGE_DEPTH": Provenance(BOTTOM_WEDGE_DEPTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L30"),
    "FRONT_HEIGHT": Provenance(FRONT_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L78"),
    "FRONT_WIDTH": Provenance(FRONT_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L79"),
    "FRONT_DEPTH": Provenance(FRONT_DEPTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L80"),
    "FRONT_TOP_WEDGE": Provenance(FRONT_TOP_WEDGE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L81"),
    "FRONT_BOTTOM_WEDGE": Provenance(FRONT_BOTTOM_WEDGE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L82"),
    "FRONT_ROUND_X": Provenance(FRONT_ROUND_X, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L83"),
    "FRONT_ROUND_SCALE": Provenance(FRONT_ROUND_SCALE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L84"),
    "FRONT_ROUND_RADIUS": Provenance(FRONT_ROUND_RADIUS, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L85"),
    "FRONT_BOTTOM_SHIFT": Provenance(FRONT_BOTTOM_SHIFT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L86"),
    "REAR_HEIGHT": Provenance(REAR_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L92"),
    "REAR_WIDTH": Provenance(REAR_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L93"),
    "REAR_DEPTH": Provenance(REAR_DEPTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L94"),
    "REAR_TOP_WEDGE": Provenance(REAR_TOP_WEDGE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L95"),
    "REAR_BOTTOM_WEDGE": Provenance(REAR_BOTTOM_WEDGE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L96"),
    "REAR_ROUND_X": Provenance(REAR_ROUND_X, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L97"),
    "REAR_ROUND_SCALE": Provenance(REAR_ROUND_SCALE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L98"),
    "REAR_ROUND_RADIUS": Provenance(REAR_ROUND_RADIUS, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L99"),
    "CLICK_OFFSET": Provenance(CLICK_OFFSET, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L105"),
    "CLICK_DEPTH": Provenance(CLICK_DEPTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L107"),
    "CLICK_WIDTH": Provenance(CLICK_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L107"),
    "CLICK_RADIUS": Provenance(CLICK_RADIUS, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L107"),
    "CLICK_ROOF": Provenance(CLICK_ROOF, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L107"),
    "REAR_CLICK_START": Provenance(REAR_CLICK_START, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L110"),
    "REAR_CLICK_HEIGHT": Provenance(REAR_CLICK_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L110"),
    "REAR_CLICK_OFFSET": Provenance(REAR_CLICK_OFFSET, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L111"),
    "REAR_CLICK_RISE": Provenance(REAR_CLICK_RISE, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L111"),
    "REAR_CLICK_SHIFT": Provenance(REAR_CLICK_SHIFT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L111"),
    "REAR_RELIEF_OFFSET": Provenance(REAR_RELIEF_OFFSET, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L112"),
    "REAR_RELIEF_DEPTH": Provenance(REAR_RELIEF_DEPTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L112"),
    "REAR_RELIEF_WIDTH": Provenance(REAR_RELIEF_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L112"),
    "REAR_RELIEF_HEIGHT": Provenance(REAR_RELIEF_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L112"),
    "WALL_CLICK_HEIGHT": Provenance(WALL_CLICK_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L117"),
    "WALL_CLICK_DEPTH": Provenance(WALL_CLICK_DEPTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L119"),
    "WALL_CLICK_WIDTH": Provenance(WALL_CLICK_WIDTH, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L119"),
    "WALL_CLICK_THICKNESS": Provenance(WALL_CLICK_THICKNESS, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L119"),
    "INDICATOR_X": Provenance(INDICATOR_X, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L122"),
    "INDICATOR_BOTTOM_RADIUS": Provenance(INDICATOR_BOTTOM_RADIUS, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L122"),
    "INDICATOR_TOP_RADIUS": Provenance(INDICATOR_TOP_RADIUS, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L122"),
    "INDICATOR_HEIGHT": Provenance(INDICATOR_HEIGHT, "C", "QuackWorks openGrid/opengrid-snap.scad + patch 0001",
        "https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L122"),
}
