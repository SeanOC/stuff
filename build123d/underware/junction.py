# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Monokini junctions: L, T and X, composed from straight channels and the
corner body on the shared 28 mm cell grid.

[C] monokini_L_channel.scad:131-145 (actually_channel) and :474-500
(monokiniChannelCurve, the addedRadius form); monokini_T_channel.scad:135-282
and :555; monokini_X_channel.scad:131-191 and :457. Same frame as
underware.channel: X/Y in the bed plane, Z up, Z=0 the closed face; spin is
the author's (counter-clockwise about +Z), so a straight channel's +X wall
(the author's 'Left') is +Y after spin 90.

The source's 0.01 mm Nudge overlaps and half-space offsets are not
reproduced: every arm, stub and clip meets its neighbour exactly.
"""
from __future__ import annotations

from dataclasses import dataclass

from build123d import Axis, Box, Location, Part, Plane, Pos, Rot, extrude, mirror, revolve

from . import constants as c
from .channel import channel_section, cord_cutouts, present_grips, straight_channel

STUB = c.CHANNEL_SEPARATION   # corner path's straight lead-in/out (:476 channelWidthSeparation+Nudge)
CUTOUT_SIDES_X = ('Left Side', 'Right Side', 'Both Sides', 'None')  # [C] X:56 has no Top modes
FAR = 1e3                     # half-space extent for the clips


def split_fields(name: str, value: str, count: int) -> list[str]:
    """Per-arm comma fields ([C] L:117 str_split(upcase(...), ",")); a missing
    field is the author's undef, i.e. nothing suppressed."""
    fields = value.split(',') if value.strip() else []
    if len(fields) > count:
        raise ValueError(f'{name} {value!r} has {len(fields)} comma fields but the junction has only '
                         f'{count} channels')
    return [f.strip() for f in fields] + [''] * (count - len(fields))


@dataclass(frozen=True)
class Arm:
    """One straight monokiniChannel placed on the junction.

    keep: local-frame rectangles (xmin, xmax, ymin, ymax) whose union is kept
    (the source's left_half/front_half/back_half clips); None keeps it all.
    """
    length: float
    width: float
    x: float
    y: float
    spin: float
    suppress: str = ''
    separators: str = ''
    keep: tuple[tuple[float, float, float, float], ...] | None = None

    @property
    def location(self) -> Location:
        return Location((self.x, self.y, 0), (0, 0, self.spin))

    def kept(self, x: float, y: float) -> bool:
        return self.keep is None or any(a <= x <= b and lo <= y <= hi for a, b, lo, hi in self.keep)

    def grips(self, grip_flare: float = 0.) -> list[tuple[float, int, bool]]:
        """(y_cell, side, flared) in the arm frame, minus grips the clip drops."""
        return [g for g in present_grips(self.length, self.suppress, grip_flare)
                if self.kept(g[1]*(self.width/2 - c.SNAP_WALL/2), g[0])]

    def solid(self, height: float, grip_flare: float, cutters=()) -> Part:
        body = straight_channel(self.length, self.width, height, suppress=self.suppress,
                                separators=self.separators, grip_flare=grip_flare)
        for cutter in cutters:
            body -= cutter
        if self.keep is not None:
            boxes = [Pos((a+b)/2, (lo+hi)/2, height/2)*Box(b-a, hi-lo, height + 2)
                     for a, b, lo, hi in self.keep]
            clip = boxes[0]
            for box in boxes[1:]:
                clip += box
            body &= clip
        return self.location*body


def corner(width: float, height: float, added_radius: int = 0, separators: str = '') -> Part:
    """monokiniChannelCurve: the channel section swept along a lead-in STUB,
    a 90 degree arc about (w/2, -w/2) from -X round to +Y, and a lead-out STUB
    along +X ([C] L:476 path, moved by L:486).

    The arc's centreline radius is added_radius*GRID + w/2, so at 0 the
    section's +X outer face sits on the axis (a quarter post of wall at the
    inside corner). BOSL2 path_extrude2d mitres 89 straight segments; the
    port revolves the section (chord error 0.0005 mm at r=13.2).
    """
    cx, cy = width/2, -width/2
    r = added_radius*c.GRID + width/2
    section = Pos(cx - r, cy, 0)*channel_section(width, height, separators)
    lead_in = Pos(0, -STUB, 0)*extrude(section, STUB, dir=(0, 1, 0))
    arc = revolve(section, Axis((cx, cy, 0), (0, 0, -1)), 90)
    turned = Pos(cx, cy, 0)*Rot(0, 0, -90)*Pos(-cx, -cy, 0)*section
    lead_out = extrude(turned, STUB, dir=(1, 0, 0))
    return lead_in + arc + lead_out


def quadrant(part: Part, height: float, x_sign: int, y_sign: int) -> Part:
    """Keep the part's (x_sign, y_sign) quadrant ([C] front_half/right_half)."""
    return part & Pos(x_sign*FAR/2, y_sign*FAR/2, height/2)*Box(FAR, FAR, height + 2)


def assemble(arms, pieces, height, grip_flare, cutouts_on_first=()) -> Part:
    part = arms[0].solid(height, grip_flare, cutouts_on_first)
    for arm in arms[1:]:
        part += arm.solid(height, grip_flare)
    for piece in pieces:
        part += piece
    return part.clean()


# --- L ------------------------------------------------------------------------

def l_arms(units, ly, lx, added_radius, suppress, separators):
    """[C] L:133-141: Y arm (spin 0) below the corner, X arm (spin 270) to its
    right; added_radius moves the Y arm -X and the X arm +Y by whole cells."""
    w, cw = c.channel_width(units), units*c.GRID
    f = split_fields('suppress_connectors', suppress, 2)
    sep = separators.split(',')[0]
    ro = added_radius*c.GRID
    return [Arm(ly*c.GRID, w, -ro, -(ly*c.GRID/2 + cw/2), 0, f[0], sep),
            Arm(lx*c.GRID, w, lx*c.GRID/2 + cw/2, ro, 270, f[1], sep)]


def build_l(units, height, ly, lx, *, mirrored=False, added_radius=0, suppress='', separators='',
            grip_flare=0., cutters=()) -> Part:
    """[C] L:127-145. Mirror_Channel xflips the whole actually_channel, so the
    added_radius shift happens first and the mirror last (x -> -x)."""
    arms = l_arms(units, ly, lx, added_radius, suppress, separators)
    w = c.channel_width(units)
    part = assemble(arms, [corner(w, height, added_radius, separators.split(',')[0])],
                    height, grip_flare, cutters)
    return mirror(part, Plane.YZ) if mirrored else part


# --- T ------------------------------------------------------------------------

def t_arms(ub, ul, ur, ly, ll, lr, suppress):
    """[C] T:135-238. The stem runs up to the narrower arm; with unequal arm
    widths its two halves stop at their own arm (front_half :140/:144), the
    stem gains the width difference, and the crossbar (:236-238: a one-node
    channel of the wider arm's width, back_half y > -topChamfer) carries the
    node's grip on the top wall."""
    w, wl, wr = c.channel_width(ub), c.channel_width(ul), c.channel_width(ur)
    cw, cwl, cwr = ub*c.GRID, ul*c.GRID, ur*c.GRID
    m, d = min(cwl, cwr), abs(cwl - cwr)
    length = ly*c.GRID + d
    f = split_fields('suppress_connectors', suppress, 4)
    stem_keep = ((-FAR, 0., -FAR, length/2 - cwl + m), (0., FAR, -FAR, length/2 - cwr + m))
    return [
        Arm(length, w, 0., -(length/2 + m/2), 0, f[0], keep=stem_keep),
        Arm(lr*c.GRID, wr, lr*c.GRID/2 + cw/2, -d/2 if cwr > cwl else 0., 90, f[1]),
        Arm(ll*c.GRID, wl, -(ll*c.GRID/2 + cw/2), -d/2 if cwl > cwr else 0., -90, f[2]),
        # spin 90: world y = local x - d/2, so y > -topChamfer is local x > d/2 - 4.
        Arm(cw, max(wl, wr), 0., -d/2, 90, f[3], keep=((d/2 - c.TOP_CHAMFER, FAR, -FAR, FAR),)),
    ]


def t_corner_placements(ub, ul, ur) -> list[tuple[int, float, float, float]]:
    """(side, corner width, dx, dy) for T:239-281: one corner per side, width
    max(stem, arm), moved (dx, dy) after the side's xflip so it meets the
    wider of the two."""
    cw, cwl, cwr = ub*c.GRID, ul*c.GRID, ur*c.GRID
    w = c.channel_width(ub)
    out = []
    for side, ca, co in ((1, cwr, cwl), (-1, cwl, cwr)):
        fwd = (0. if cw > ca else ca/2 - co/2) if ca > co else (-abs(cw - ca)/2 if cw > ca else 0.)
        inward = 0. if cw > ca else abs(cw - ca)/2
        out.append((side, max(w, c.channel_width(round(ca/c.GRID))), -side*inward, -fwd))
    return out


def t_curves(ub, ul, ur, height) -> list[Part]:
    """[C] T:239-281: each corner clipped to its lower quadrant."""
    out = []
    for side, wc, dx, dy in t_corner_placements(ub, ul, ur):
        piece = corner(wc, height)
        if side < 0:
            piece = mirror(piece, Plane.YZ)
        out.append(quadrant(Pos(dx, dy, 0)*piece, height, side, -1))
    return out


def build_t(ub, ul, ur, height, ly, ll, lr, *, suppress='', grip_flare=0., cutters=()) -> Part:
    arms = t_arms(ub, ul, ur, ly, ll, lr, suppress)
    return assemble(arms, t_curves(ub, ul, ur, height), height, grip_flare, cutters)


# --- X ------------------------------------------------------------------------

def x_arms(units, lb, lr, ll, lt, suppress):
    """[C] X:131-183: four arms round a one-node centre (bottom, right, left,
    top = suppress fields 0-3); the top arm keeps spin 0."""
    w, cw = c.channel_width(units), units*c.GRID
    f = split_fields('suppress_connectors', suppress, 4)
    return [Arm(lb*c.GRID, w, 0., -(lb*c.GRID/2 + cw/2), 0, f[0]),
            Arm(lr*c.GRID, w, lr*c.GRID/2 + cw/2, 0., 90, f[1]),
            Arm(ll*c.GRID, w, -(ll*c.GRID/2 + cw/2), 0., -90, f[2]),
            Arm(lt*c.GRID, w, 0., lt*c.GRID/2 + cw/2, 0, f[3])]


def x_curves(units, height) -> list[Part]:
    """[C] X:184-190: zrot_copies(2) of a corner and its xflip, each clipped
    to x > 0, y < 0 first: floor and four corner posts, no centre grip."""
    q = quadrant(corner(c.channel_width(units), height), height, 1, -1)
    q2 = mirror(q, Plane.YZ)
    return [q, q2, Rot(0, 0, 180)*q, Rot(0, 0, 180)*q2]


def build_x(units, height, lb, lr, ll, lt, *, suppress='', grip_flare=0., cutters=()) -> Part:
    arms = x_arms(units, lb, lr, ll, lt, suppress)
    return assemble(arms, x_curves(units, height), height, grip_flare, cutters)


def footprint(arms) -> tuple[float, float, float, float]:
    """(xmin, xmax, ymin, ymax) of the arms' rectangles; the corner bodies lie
    inside them (an L corner's outer radius reaches the Y arm's outer wall)."""
    xs, ys = [], []
    for arm in arms:
        half = (arm.width/2, arm.length/2) if arm.spin % 180 == 0 else (arm.length/2, arm.width/2)
        xs += [arm.x - half[0], arm.x + half[0]]
        ys += [arm.y - half[1], arm.y + half[1]]
    return min(xs), max(xs), min(ys), max(ys)


def check_cutout_span(arm: Arm, number: int, spacing: float, shift: float, cutout_width: float) -> None:
    """Cutouts must stay on the first arm: the source cuts only that arm, so a
    slot running past its junction end would leave the corner's 0.8 mm lead-in
    wall standing as a fin, and one past its free end notches the mating face."""
    from .channel import cutout_centres
    if number <= 0:
        return
    top = arm.length/2
    if arm.keep is not None:
        top = min(top, *(hi for _, _, _, hi in arm.keep))
    r = cutout_width/2
    for y in cutout_centres(number, spacing, shift):
        if y - r < -arm.length/2 or y + r > top:
            raise ValueError(f'the cord cutout at y={y:g} mm runs past the first channel '
                             f'(y {-arm.length/2:g}..{top:g} mm); lengthen it or move the cutouts')


def first_arm_cutters(width, height, **cut_args) -> list[Part]:
    """Cord cutouts in the first arm's frame (the source's diff() wraps only
    that arm: L:123-128, T:137-212, X:132-176)."""
    return cord_cutouts(width, height, **cut_args)
