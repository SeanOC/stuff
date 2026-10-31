# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Monokini path channels: S, diagonal, mitre and outside corner.

[C] monokini_S_channel.scad:135-219 and :664-726, monokini_diagonal_channel.scad:
135-221 and :666-726, monokini_mitre_channel.scad:127-220 and :479-540. Same
frame as underware.channel: X/Y in the bed plane, Z up, Z=0 the closed face.

S and diagonal: two gripped straight runs whose walls the connector supplies
(monokiniChannel with suppressWalls, S:155/:189) and one gripless swept
connector over the whole path (monokiniChannelPath, S:205): the bottom run
along +Y ends at (0, -GRID), the top run starts at (dx, dy). The S path is a
cubic Bezier between them (S:139-146); the diagonal is the polyline (D:148).

Mitre: a 90 degree bend about the width axis (X), floor inside. The first
channel runs along Y as in underware.channel; the second hangs down -Z with
its closed face toward -Y and its grips toward +Y (mitre:139-217).
build_mitre is the author's solid and keeps the source's two arm lengths (the
parity references include an unequal pair); the registered underware_mitre
(holders/underware_path_channels.py) drives both from one length and cuts a
bed flat across the arm tips in its 45 degree print frame.

Outside corner (original design derived from the ported mitre, pst-38hu7;
no author source): the mitre's first arm, then a 90 degree bend UP about the
width axis with the floor OUTSIDE and the open (grip) faces inside, into a
second channel along +Z with its grips toward -Y. It wraps the convex edge
of two openGrid panels: the open faces meet at the edge line (outside_edge),
on the bend axis at added_radius 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot, tan, radians

from build123d import (Axis, Bezier, Line, Location, Part, Plane, Pos, Wire, extrude, mirror,
                       revolve)

from . import constants as c
from .channel import channel_section, grip_parts, path_channel, straight_channel
from .junction import Arm, split_fields

PARTS = ('S', 'diagonal')
STUB = c.CHANNEL_SEPARATION   # mitre bend's lead-out (:501 channelWidthSeparation+Nudge)
BEZIER_SAMPLES = 2000
# The end grip of a run stops SPACING_FROM_CHANNEL short of the vertex; past
# the corner of the inside wall's inner face (on the mitre plane) the grip's
# foot overhangs the channel (probes: 6.50 mm setback clean, 6.53 a 0.0005
# mm2 sliver, 6.92 a 0.42 mm one, at z = height - BASE_HEIGHT).
MAX_SETBACK = c.SPACING_FROM_CHANNEL


@dataclass(frozen=True)
class Run:
    """One gripped straight run of an S or diagonal part (no walls of its own)."""
    length: float
    width: float
    x: float
    y: float
    suppress: str = ''

    @property
    def location(self) -> Location:
        return Location((self.x, self.y, 0))

    @property
    def start(self) -> float:
        return self.y - self.length/2

    @property
    def end(self) -> float:
        return self.y + self.length/2


def offsets(over: int, up: int) -> tuple[float, float]:
    """(dx, dy): [C] S:135-136 dx = Units_Over*GRID, dy = (Units_Up-1)*GRID."""
    return over*c.GRID, (up - 1)*c.GRID


def runs(units: int, bottom: int, top: int, over: int, up: int, suppress: str = '') -> tuple[Run, Run]:
    """[C] S:153 fwd(lengthMM/2+Grid_Size) and S:186-187 left(-dx) back(lengthMM2/2+dy)."""
    w = c.channel_width(units)
    dx, dy = offsets(over, up)
    f = split_fields('suppress_connectors', suppress, 2)
    l1, l2 = bottom*c.GRID, top*c.GRID
    return (Run(l1, w, 0., -(l1/2 + c.GRID), f[0]), Run(l2, w, dx, dy + l2/2, f[1]))


def bezier_controls(dx: float, dy: float) -> tuple[tuple[float, float], ...]:
    """[C] S:139-144: bez_tang([0,-G], BACK, G) to bez_tang([dx,dy], BACK, G);
    the source's first and last Bezier pieces are collinear with the runs."""
    g = c.GRID
    return ((0., -g), (0., 0.), (dx, dy - g), (dx, dy))


def bezier_min_radius(dx: float, dy: float) -> float:
    """Smallest radius of curvature of the S Bezier (sampled)."""
    p = bezier_controls(dx, dy)
    best = float('inf')
    for i in range(BEZIER_SAMPLES + 1):
        t = i/BEZIER_SAMPLES
        d1 = [3*(1-t)**2*(p[1][k]-p[0][k]) + 6*(1-t)*t*(p[2][k]-p[1][k]) + 3*t**2*(p[3][k]-p[2][k])
              for k in (0, 1)]
        d2 = [6*(1-t)*(p[2][k]-2*p[1][k]+p[0][k]) + 6*t*(p[3][k]-2*p[2][k]+p[1][k]) for k in (0, 1)]
        cross = abs(d1[0]*d2[1] - d1[1]*d2[0])
        if cross > 1e-12:
            best = min(best, hypot(*d1)**3/cross)
    return best


def corner_turn(dx: float, dy: float) -> float:
    """Turn (degrees) at each diagonal vertex: +Y to the (dx, dy + GRID) leg."""
    return degrees(atan2(abs(dx), dy + c.GRID))


def mitre_setback(width: float, turn_deg: float) -> float:
    """How far the inside wall's inner face (width/2 - SNAP_WALL off the
    centreline) meets the mitre plane short of the vertex."""
    return (width/2 - c.SNAP_WALL)*tan(radians(turn_deg/2))


def centre_path(part: str, first: Run, second: Run) -> Wire:
    """The connector path from the bottom run's start to the top run's end."""
    a, b = (0., first.start), (0., first.end)
    q, z = (second.x, second.start), (second.x, second.end)
    if part == 'S':
        return Wire([Line(a, b), Bezier(*bezier_controls(second.x, second.start)), Line(q, z)])
    return Wire.make_polygon([a, b, q, z], close=False)


def build_path(part: str, first: Run, second: Run, height: float, *, separators: str = '',
               grip_flare: float = 0., cutters=()) -> Part:
    """[C] S:150-219: (connector + both runs' grips) minus the flare slits
    (monokiniChannelCuts, S:210/:215) minus the cord cutouts on the first run."""
    w = first.width
    body = path_channel(centre_path(part, first, second), w, height, separators)
    slits = []
    for run in (first, second):
        grips, cuts = grip_parts(run.length, w, height, run.suppress, grip_flare)
        for g in grips:
            body += run.location*g
        slits += [run.location*s for s in cuts]
    for cut in slits + [first.location*cutter for cutter in cutters]:
        body -= cut
    return body.clean()


# --- mitre ---------------------------------------------------------------------

def mitre_radius(height: float, added_radius: int) -> float:
    """[C] mitre:501 arc r = addedRadius*GRID + heightMM/2: the floor's radius."""
    return added_radius*c.GRID + height/2


def mitre_first(units: int, length_y: int, added_radius: int, suppress: str, separators: str) -> Arm:
    """[C] mitre:139-144 left(aR*G) fwd(lengthMM/2+curveWidth/2), spin 0."""
    w, cw = c.channel_width(units), units*c.GRID
    f = split_fields('suppress_connectors', suppress, 2)
    return Arm(length_y*c.GRID, w, -added_radius*c.GRID, -(length_y*c.GRID/2 + cw/2), 0,
               f[0], separators.split(',')[0])


def mitre_second_location(units: int, height: float, length_z: int, added_radius: int) -> Location:
    """[C] mitre:212-217: left(aR*G) down(aR*G) down(lengthMM2/2+h/2)
    fwd(cw/2-h/2-sep-aR*G) zrot(-90) yrot(-90) of a spin-270 channel, i.e.
    local (x, y, z) -> (-x, z, y): along -Z, closed face at y = r - w/2."""
    w, r = c.channel_width(units), mitre_radius(height, added_radius)
    lz = length_z*c.GRID
    origin = (-added_radius*c.GRID, r - w/2, -(r + lz/2))
    return Location(Plane(origin=origin, x_dir=(-1, 0, 0), z_dir=(0, 1, 0)))


def mitre_bend(width: float, height: float, added_radius: int = 0, separators: str = '') -> Part:
    """monokiniChannelCurve of the mitre file ([C] mitre:479-540): the section
    revolved 90 degrees about the X-parallel axis through (y = -w/2, z = -r),
    from the first channel's end (lead-out STUB at y = -w/2 .. -w/2-STUB) down
    to z = -r, where the second channel starts. The source's 0.81 mm lead-in
    lies inside the second channel and is not built. path_extrude2d chains 90
    straight segments; the port revolves (as junction.corner, but about the
    width axis and with the floor, not the outer wall, on the radius)."""
    r = mitre_radius(height, added_radius)
    section = Pos(-added_radius*c.GRID, -width/2, 0)*channel_section(width, height, separators)
    arc = revolve(section, Axis((0, -width/2, -r), (-1, 0, 0)), 90)
    lead_out = extrude(Pos(0, -STUB, 0)*section, STUB, dir=(0, 1, 0))
    return arc + lead_out


def build_mitre(units: int, height: float, length_y: int, length_z: int, *, mirrored: bool = False,
                added_radius: int = 0, suppress: str = '', separators: str = '',
                grip_flare: float = 0., cutters=()) -> Part:
    """[C] mitre:127-220. Mirror_Channel xflips the whole actually_channel."""
    first = mitre_first(units, length_y, added_radius, suppress, separators)
    f = split_fields('suppress_connectors', suppress, 2)
    second = mitre_second_location(units, height, length_z, added_radius)*straight_channel(
        length_z*c.GRID, first.width, height, suppress=f[1], separators=first.separators,
        grip_flare=grip_flare)
    part = first.solid(height, grip_flare, cutters) + second
    part += mitre_bend(first.width, height, added_radius, first.separators)
    part = part.clean()
    return mirror(part, Plane.YZ) if mirrored else part


# --- outside corner (convex twin of the mitre; original design, pst-38hu7) ------

def outside_axis(units: int, height: float, added_radius: int) -> tuple[float, float]:
    """(y, z) of the outside corner's bend axis (X-parallel): the mitre's
    tangent plane y = -w/2, ABOVE the first arm by the open (wall-top) face
    radius added_radius*GRID, so the floor (radius that + the wall top) lies
    outside the bend and the open faces inside it."""
    w = c.channel_width(units)
    return -w/2, height - c.BASE_HEIGHT + added_radius*c.GRID


def outside_edge(units: int, height: float, added_radius: int) -> tuple[float, float]:
    """(y, z) of the corner edge line: where the two arms' open faces (wall
    tops, the openGrid tile faces) meet; on the bend axis at added_radius 0."""
    ya, za = outside_axis(units, height, added_radius)
    return ya + added_radius*c.GRID, za - added_radius*c.GRID


def outside_floor_radius(height: float, added_radius: int) -> float:
    """Radius of the bend's closed (floor) face about the axis."""
    return added_radius*c.GRID + height - c.BASE_HEIGHT


def outside_second_location(units: int, height: float, length_z: int, added_radius: int) -> Location:
    """The second arm rises +Z from the axis height, its open face (grips)
    toward -Y on the plane y = edge: local (x, y, z) -> (-x, -z, -y), the
    mitre's second-arm frame turned 180 degrees about X (index 0 at the free
    tip, the +X wall still the author's 'Right')."""
    ya, za = outside_axis(units, height, added_radius)
    lz = length_z*c.GRID
    origin = (-added_radius*c.GRID, ya + outside_floor_radius(height, added_radius), za + lz/2)
    return Location(Plane(origin=origin, x_dir=(-1, 0, 0), z_dir=(0, -1, 0)))


def outside_bend(width: float, height: float, added_radius: int = 0, separators: str = '') -> Part:
    """mitre_bend turned the other way: the section revolved 90 degrees about
    the axis ABOVE it (outside_axis), from the first channel's end up to the
    second channel's start, with the mitre's lead-out STUB. At added_radius 0
    the wall tops lie on the axis and the bend's walls are quarter discs."""
    ya, za = -width/2, outside_floor_radius(height, added_radius)   # = outside_axis
    section = Pos(-added_radius*c.GRID, -width/2, 0)*channel_section(width, height, separators)
    arc = revolve(section, Axis((0, ya, za), (1, 0, 0)), 90)
    lead_out = extrude(Pos(0, -STUB, 0)*section, STUB, dir=(0, 1, 0))
    return arc + lead_out


def build_outside_corner(units: int, height: float, length_y: int, length_z: int, *,
                         mirrored: bool = False, added_radius: int = 0, suppress: str = '',
                         separators: str = '', grip_flare: float = 0., cutters=()) -> Part:
    """The mitre's first arm (mitre_first, cutters on it), outside_bend and a
    second arm rising +Z (outside_second_location). Mirror xflips the whole."""
    first = mitre_first(units, length_y, added_radius, suppress, separators)
    f = split_fields('suppress_connectors', suppress, 2)
    second = outside_second_location(units, height, length_z, added_radius)*straight_channel(
        length_z*c.GRID, first.width, height, suppress=f[1], separators=first.separators,
        grip_flare=grip_flare)
    part = first.solid(height, grip_flare, cutters) + second
    part += outside_bend(first.width, height, added_radius, first.separators)
    part = part.clean()
    return mirror(part, Plane.YZ) if mirrored else part
