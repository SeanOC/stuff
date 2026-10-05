# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# openGrid design: David D; OpenSCAD: metasyntactic (QuackWorks).
# Port of QuackWorks/openGrid/opengrid-snap.scad @6123129 + local patch 0001.
"""Analytic port of openGridSnap; dimensions and source locators in constants.

XY centred on the 24.8 mm core, +Z toward the mounted body. Build the body
from snap height minus 0.02 mm to embed the top. Nubs share their full root
face with the core and are fused as BReps; no SCAD consumer weld shims.
"""
from build123d import (
    Align,
    Box,
    Ellipse,
    Part,
    Plane,
    Polygon,
    Pos,
    RegularPolygon,
    Rot,
    SlotOverall,
    extrude,
    loft,
)

from . import constants as c


def _outline(corner):
    a = c.CORE_WIDTH / 2
    b = a - corner
    return Polygon((a, b), (b, a), (-b, a), (-a, b),
                   (-a, -b), (-b, -a), (b, -a), (a, -b), align=None)


def _wedge(width, depth, height):
    # BOSL2 wedge anchored CENTER+BOTTOM+BACK: -depth <= Y <= 0.
    triangle = Plane.YZ * Polygon((-depth, 0), (0, 0), (-depth, height), align=None)
    return extrude(triangle, amount=width / 2, both=True)


def _nub(height, width, depth, top, bottom, rx, radius, scale, shift=0):
    block = Pos(0, 0, height - c.OVERLAP) * Box(
        depth, width, c.NUB_TOP - height + c.OVERLAP,
        align=(Align.MIN, Align.CENTER, Align.MIN))
    upper = Pos(0, 0, c.NUB_TOP) * Rot(0, 0, 90) * Rot(0, 180, 0) * _wedge(width, depth, top)
    lower = Pos(0, 0, height) * Rot(0, 0, 90) * Pos(0, shift, 0) * _wedge(
        width, c.BOTTOM_WEDGE_DEPTH, bottom)
    rounding = Pos(rx, 0, 0) * extrude(Ellipse(radius, radius * scale),
                                      amount=c.NUB_TOP + c.OVERLAP)
    return Pos(c.CORE_WIDTH / 2, 0, 0) * ((block - upper - lower) & rounding)


def snap(lite: bool = True, directional: bool = False) -> Part:
    """Return one fused solid, snaps-down (+Z up), in millimetres.

    Lite/full heights are 3.4/6.8; overall XY is 25.6 square, or 26 x 25.6
    with directional nubs (+X is the front). Both flags may be combined.
    """
    extra = 0 if lite else c.FULL_EXTRA
    core = c.CORE_HEIGHT + extra
    height = c.LITE_HEIGHT + extra
    body = extrude(_outline(c.CORE_CORNER), amount=core)
    body += Pos(0, 0, height - c.TOP_HEIGHT - c.OVERLAP) * extrude(
        _outline(c.TOP_CORNER), amount=c.TOP_HEIGHT + c.OVERLAP)
    top_band = Pos(0, 0, core - c.TOP_NUB_HEIGHT - c.OVERLAP) * extrude(
        _outline(c.TOP_CORNER), amount=c.TOP_NUB_HEIGHT + c.OVERLAP)
    offset = c.CORE_WIDTH / 2 - c.TOP_NUB_OFFSET
    top_nub = (Pos(offset, offset, core) * Rot(0, 0, 135) * Rot(180, 0, 0)
               * Pos(0, c.TOP_NUB_HEIGHT / 2, 0)
               * _wedge(c.TOP_NUB_WIDTH, c.TOP_NUB_HEIGHT, c.TOP_NUB_HEIGHT))
    standard = _nub(c.NUB_HEIGHT, c.NUB_WIDTH, c.NUB_DEPTH,
                    c.NUB_TOP_WEDGE, c.NUB_BOTTOM_WEDGE, c.NUB_ROUND_X,
                    c.NUB_ROUND_RADIUS, c.NUB_ROUND_SCALE)
    for i in range(4):
        body += Rot(0, 0, 90 * i) * (top_nub & top_band)
        if not directional or i in (1, 3):
            body += Pos(0, 0, extra) * Rot(0, 0, 90 * i) * standard
    if directional:
        body += Pos(0, 0, extra) * _nub(
            c.FRONT_HEIGHT, c.FRONT_WIDTH, c.FRONT_DEPTH, c.FRONT_TOP_WEDGE,
            c.FRONT_BOTTOM_WEDGE, c.FRONT_ROUND_X, c.FRONT_ROUND_RADIUS,
            c.FRONT_ROUND_SCALE, c.FRONT_BOTTOM_SHIFT)
        body += Pos(0, 0, extra) * Rot(0, 0, 180) * _nub(
            c.REAR_HEIGHT, c.REAR_WIDTH, c.REAR_DEPTH, c.REAR_TOP_WEDGE,
            c.REAR_BOTTOM_WEDGE, c.REAR_ROUND_X, c.REAR_ROUND_RADIUS,
            c.REAR_ROUND_SCALE)
    click = SlotOverall(c.CLICK_WIDTH, c.CLICK_DEPTH, rotation=90)
    for i in range(4):
        rot = Rot(0, 0, 90 * i)
        if not directional or i in (1, 3):
            body -= rot * Pos(c.CORE_WIDTH / 2 - c.CLICK_OFFSET, 0, 0) * extrude(
                click, amount=c.CLICK_ROOF + extra)
        if not directional or i > 0:
            body -= rot * Pos(c.CORE_WIDTH / 2, 0, c.WALL_CLICK_HEIGHT + extra) * Box(
                c.WALL_CLICK_DEPTH, c.WALL_CLICK_WIDTH, c.WALL_CLICK_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    if directional:
        rear = Pos(c.CORE_WIDTH / 2 - c.CLICK_OFFSET, 0, c.REAR_CLICK_START) * extrude(
            click, amount=c.REAR_CLICK_HEIGHT + extra)
        rear += loft([
            Pos(c.CORE_WIDTH / 2 - c.REAR_CLICK_OFFSET, 0, 0) * click,
            Pos(c.CORE_WIDTH / 2 - c.REAR_CLICK_OFFSET + c.REAR_CLICK_SHIFT,
                0, c.REAR_CLICK_RISE) * click,
        ])
        relief = Plane.XZ * Polygon(
            (c.CORE_WIDTH / 2 - c.REAR_RELIEF_DEPTH, 0),
            (c.CORE_WIDTH / 2, 0), (c.CORE_WIDTH / 2, c.REAR_RELIEF_HEIGHT), align=None)
        rear += extrude(relief, amount=c.REAR_RELIEF_WIDTH / 2, both=True)
        body -= Rot(0, 0, 180) * rear
        # OpenSCAD cylinder($fn=2) clamps to a triangular frustum.
        body -= Pos(c.INDICATOR_X, 0, 0) * loft([
            RegularPolygon(c.INDICATOR_BOTTOM_RADIUS, 3),
            Pos(0, 0, c.INDICATOR_HEIGHT) * RegularPolygon(c.INDICATOR_TOP_RADIUS, 3),
        ])
    return Part(body.wrapped)
