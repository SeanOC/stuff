# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Sacrificial cradle for the outside corner, in a bed-centred print frame.

The retained part is unchanged. Only its old bed strip bonds to the 0.2 mm
remnant; all other contacts have a concentric normal gap. Cable loads remain
on the original channel after the connected pad/cradle is peeled away.
"""
from dataclasses import dataclass
from math import ceil, sqrt

from build123d import (Align, Box, Cylinder, Edge, Face, Pos, RectangleRounded, Rot,
                      Wire, chamfer, extrude)

PAD_THICKNESS = 0.6
REMNANT = 0.2
MARGIN = 5.0
CORNER_RADIUS = 4.0
GROOVE_WIDTH = 0.4
FIN_THICKNESS = 0.95
FIN_PITCH_MAX = 8.0
ARM_BACKING = 3.0  # horizontal projection: 3*sqrt(2) mm along each 45-degree arm


@dataclass(frozen=True)
class DesignedSupport:
    """Exact material declarations, in the same coordinates as the part.

    ``pad`` includes the groove remnants; it is the only wall-floor exception.
    ``fins`` must exist in the part and retain the ordinary wall floor.
    ``bridge_axis`` is the direction between adjacent fins.
    """
    gap_mm: float
    pad: object
    fins: tuple
    bridge_axis: tuple = (1., 0., 0.)

    def moved(self, frame):
        from build123d import Matrix, Vector
        transform = Matrix(frame.wrapped.Transformation())
        origin = Vector(0, 0, 0).transform(transform)
        axis = Vector(self.bridge_axis).transform(transform) - origin
        return DesignedSupport(self.gap_mm, frame * self.pad,
                               tuple(frame * f for f in self.fins), tuple(axis))


def dimensions(width, radius, gap=.2):
    # At the bed-flat crown the 4 mm floor bevel extends 0.6 mm outward.
    footprint_width = width - 2 * (4.0 - 0.6)
    return footprint_width + 2 * MARGIN, sqrt(2) * (radius + gap) + 2 * (ARM_BACKING + MARGIN)


def cradle(width, radius, gap):
    """Return the exact pad and fins; old part bed is Z=0, cylinder axis Y=0.

    Curved fin tops are concentric offsets, not stairs. The layer-grid rule
    applies to flat tops only (plan-review N1); pad and groove heights use
    the default 0.2 mm layer. Gap remains tunable for material/layer settings.
    """
    pw, pl = dimensions(width, radius, gap)
    bottom, top = -REMNANT, PAD_THICKNESS - REMNANT
    pad = Pos(0, 0, bottom) * extrude(RectangleRounded(pw, pl, CORNER_RADIUS), PAD_THICKNESS)
    bottom_edges = [e for e in pad.edges() if abs(e.center().Z - bottom) < 1e-6]
    pad = chamfer(bottom_edges, length=0.3)
    # Keep the upper pad clear of the same concentric surface as the fins.
    clearance = Pos(0, 0, radius - 0.6) * Rot(0, 90, 0) * Cylinder(
        radius + gap, pw + 2, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    turn = (radius + gap) / sqrt(2)
    half_chord = turn + ARM_BACKING
    flat_width = width - 8.0
    n = max(2, ceil((flat_width - FIN_THICKNESS) / FIN_PITCH_MAX) + 1)
    xs = [-(flat_width - FIN_THICKNESS) / 2 + i * (flat_width - FIN_THICKNESS) / (n - 1)
          for i in range(n)]
    fins = []
    grooves = []
    for x in xs:
        # Continue 3 mm horizontally up each 45-degree arm. This avoids a
        # short, sub-0.9 mm wedge at the smallest (h10/r0) bend endpoint.
        root = sqrt((radius + gap)**2 - (radius - .6 - top)**2)
        def height(y):
            return radius - .6 - sqrt((radius + gap)**2 - y*y)
        for side in (-1, 1):
            def q(y, z):
                return (x - FIN_THICKNESS/2, side*y, z)
            start = q(root, top)
            tangent = q(turn, height(turn))
            end = q(half_chord, height(turn) + ARM_BACKING)
            foot = q(half_chord, top)
            mid = (root + turn)/2
            outline = Wire([Edge.make_three_point_arc(start, q(mid, height(mid)), tangent),
                            Edge.make_line(tangent, end), Edge.make_line(end, foot),
                            Edge.make_line(foot, start)])
            fins.append(extrude(Face(outline), amount=FIN_THICKNESS, dir=(1, 0, 0)))
        # 0.4 mm-wide outline grooves leave a 0.2 mm connected bottom skin.
        outer = Pos(x, 0, 0) * Box(FIN_THICKNESS + 2 * GROOVE_WIDTH,
                                   2 * half_chord + 2 * GROOVE_WIDTH, top,
                                   align=(Align.CENTER, Align.CENTER, Align.MIN))
        inner = Pos(x, 0, 0) * Box(FIN_THICKNESS, 2 * half_chord, top,
                                   align=(Align.CENTER, Align.CENTER, Align.MIN))
        grooves.append(outer - inner)
    # Lower the entire contact strip (plus >=0.4 mm on each side) to one
    # layer. The clearance cylinder also prevents unintended pad/part bonds
    # where the curved underside emerges from that strip.
    strip_half = sqrt(2 * radius * 0.6 - 0.6 ** 2)
    strip = Box(width - 6.8 + 2 * GROOVE_WIDTH, 2 * (strip_half + GROOVE_WIDTH), top,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    upper_pad = Pos(0, 0, 0) * Box(pw + 2, pl + 2, top,
                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    pad = pad - strip - (clearance & upper_pad)
    for groove in grooves:
        pad = pad - groove
    return DesignedSupport(gap, pad, tuple(fins))
