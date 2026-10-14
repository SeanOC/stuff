# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Monokini transitions: width change, height change and bridge.

[W] monokini_I_width_change_channel.scad (monokiniWidthChangeChannel :216-375),
[H] monokini_I_height_change_channel.scad (monokiniHeightChangeChannel
:223-366), [B] monokini_I_bridge_channel.scad (top level :131-178, its
monokiniHeightChangeChannel :239-404); Pedro Leite after Hands on Katie and
BlackjackDuck. Source and reference pins in assets/underware-opengrid/NOTICE.

Model frame = the author's render frame (channel.py): X across, Y along, Z up,
the closed face toward Z=0 and the grips on top. Each transition skins two
monokini profiles: B over the front (-Y) end, ruled to A across the middle
`rise`, A to the back (+Y) end ([W]/[H] skin(..., z=[0, L/2-R/2, L/2+R/2, L],
slices=0) under xrot(90), so z=0 lands at +Y).

- Width change: the narrower profile shifts +X so the +X walls stay in line
  and the -X wall jogs ([W] :222-226 off3/off4).
- Height change: the lower profile's closed face rises so every wall top
  stays at max(height) - BASE_HEIGHT, the plane the grips snap into ([H]
  :225-228 off1/off2); the floor steps, the grips do not.
- Bridge: two one-cell height changes (rise = one cell, [B] :118) up to
  max(bridge, from) + to, joined by a straight run whose upper part a hull of
  the crossing channel removes ([B] :131-178).

Every edge of the ruled skin joins parallel profile edges, so each ruled face
is a planar quad and BOSL2's triangulated skin is the same surface.
"""
from __future__ import annotations

from build123d import (Box, Cylinder, Face, Part, Plane, Pos, Rot, Shell, Solid, Vector, Wire,
                       extrude, mirror)

from . import constants as c
from .channel import SUPPRESS_CODES, cell_centres, parse_codes
from .grip import grip, grip_flared, grip_flared_cut
from .profile import monokini_profile, monokini_profile_points

SIDE_CUTOUTS = ('Left Side', 'Right Side', 'Both Sides', 'None')   # [W]/[H]/[B] :54


def _points(width, height, y, dx=0., dz=0.) -> list[Vector]:
    return [Vector(x + dx, y, z + dz) for x, z in monokini_profile_points(width, height)]


def _ruled_segment(pa: list[Vector], pb: list[Vector]) -> Solid:
    """Closed solid between two matching profiles: both caps plus one planar
    quad per profile edge (each pair of matching edges is parallel)."""
    faces = [Face(Wire.make_polygon(pa, close=True)), Face(Wire.make_polygon(pb, close=True))]
    for i in range(len(pa)):
        j = (i + 1) % len(pa)
        faces.append(Face(Wire.make_polygon([pa[i], pa[j], pb[j], pb[i]], close=True)))
    solid = Solid(Shell(faces))
    return solid if solid.volume > 0 else Solid(solid.wrapped.Reversed())


def skinned_channel(length: float, rise: float, a: tuple, b: tuple) -> Part:
    """Profile b = (width, height, dx, dz) from -L/2 to -rise/2, ruled to
    profile a across the rise, a from +rise/2 to +L/2 (slices=0: straight
    rulings between matching profile points)."""
    if not 0 < rise <= length:
        raise ValueError(f'a {rise:g} mm transition does not fit a {length:g} mm channel')
    stations = [(-length/2, b), (-rise/2, b), (rise/2, a), (length/2, a)]
    profiles, last = [], None
    for y, section in stations:
        if last is None or y - last > 1e-9:
            profiles.append(_points(section[0], section[1], y, *section[2:]))
        last = y
    body = Part()
    for pa, pb in zip(profiles, profiles[1:]):
        body += _ruled_segment(pa, pb)
    return body.clean()


def cell_regions(length: float, rise: float) -> list[tuple[float, str]]:
    """(y_cell, 'front' | 'back' | 'middle') per grip cell ([W]/[H] :287/:309).

    A cell is front when it ends before the rise starts, back when it starts
    after the rise ends, else middle (cell index 0 at -Y, as channel.py).
    """
    start, end = length/2 - rise/2, length/2 + rise/2
    out = []
    for k, y in enumerate(cell_centres(length)):
        if (k + 1)*c.GRID <= start + 1e-9:
            out.append((y, 'front'))
        elif k*c.GRID >= end - 1e-9:
            out.append((y, 'back'))
        else:
            out.append((y, 'middle'))
    return out


def _codes(suppress: str, count: int) -> str:
    return parse_codes('suppress_connectors', suppress, SUPPRESS_CODES, count).ljust(count, 'N')


def _sides(code: str):
    return [side for side, gone in ((1, 'BL'), (-1, 'BR')) if code not in gone]


def width_change_grips(length, rise, from_width, to_width, height, suppress='', grip_flare=0.):
    """(y, side, flared, width, dx) per grip [W] :283-374: front cells carry
    the to (B) profile's grips, back cells the from (A) profile's, the cells
    the rise crosses carry none."""
    wide = max(from_width, to_width)
    cells = cell_regions(length, rise)
    if length <= c.GRIP_SIZE:
        return []
    out = []
    for (y, region), code in zip(cells, _codes(suppress, len(cells))):
        if region == 'middle':
            continue
        width = to_width if region == 'front' else from_width
        for side in _sides(code):
            out.append((y, side, grip_flare > 0 and code != 'S', width, (wide - width)/2))
    return out


def width_change_channel(length: float, rise: float, from_width: float, to_width: float,
                         height: float, *, suppress: str = '', grip_flare: float = 0.) -> Part:
    """monokiniWidthChangeChannel [W] :216-375 (from = Channel_Width_1, +Y)."""
    wide = max(from_width, to_width)
    body = skinned_channel(length, rise, (from_width, height, (wide - from_width)/2, 0.),
                           (to_width, height, (wide - to_width)/2, 0.))
    slits = []
    for y, side, flared, width, dx in width_change_grips(length, rise, from_width, to_width, height,
                                                         suppress, grip_flare):
        if flared:
            body += Pos(dx, 0, 0)*grip_flared(width, height, y, side, grip_flare)
            slits.append(Pos(dx, 0, 0)*grip_flared_cut(width, height, y, side))
        else:
            body += Pos(dx, 0, 0)*grip(width, height, y, side)
    for slit in slits:
        body -= slit
    return body


def height_change_grips(length, rise, width, from_height, to_height, suppress='', grip_flare=0.):
    """(y, side, kind, height, dz) per grip [H] :282-334.

    kind 'plain': a monokiniGrip at the common top (every unflared grip, and
    every grip on a cell the rise crosses); 'flared': monokiniGripFlared of
    that end's height lifted onto its raised floor.
    """
    top = max(from_height, to_height)
    cells = cell_regions(length, rise)
    if length <= c.GRIP_SIZE:
        return []
    out = []
    for (y, region), code in zip(cells, _codes(suppress, len(cells))):
        h = {'front': to_height, 'back': from_height}.get(region, top)
        for side in _sides(code):
            if region != 'middle' and grip_flare > 0 and code != 'S':
                out.append((y, side, 'flared', h, top - h))
            else:
                out.append((y, side, 'plain', top, 0.))
    return out


def height_change_slits(length, rise, width, from_height, to_height, suppress='', grip_flare=0.):
    """[H] :337-361: flare slits at full height on every cell the rise does not
    touch (the author's test is (k+1)G >= start and kG <= end, inclusive, so a
    flared grip on a cell ending exactly where the rise starts gets none)."""
    if grip_flare <= 0 or length <= c.GRIP_SIZE:
        return []
    start, end = length/2 - rise/2, length/2 + rise/2
    cells = cell_centres(length)
    out = []
    for k, (y, code) in enumerate(zip(cells, _codes(suppress, len(cells)))):
        if (k + 1)*c.GRID >= start and k*c.GRID <= end or code == 'S':
            continue
        out += [(y, side) for side in _sides(code)]
    return out


def height_change_channel(length: float, rise: float, width: float, from_height: float,
                          to_height: float, *, suppress: str = '', grip_flare: float = 0.) -> Part:
    """monokiniHeightChangeChannel [H] :223-366 (from = Channel_Internal_Height_1, +Y)."""
    top = max(from_height, to_height)
    body = skinned_channel(length, rise, (width, from_height, 0., top - from_height),
                           (width, to_height, 0., top - to_height))
    for y, side, kind, h, dz in height_change_grips(length, rise, width, from_height, to_height,
                                                    suppress, grip_flare):
        if kind == 'flared':
            body += Pos(0, 0, dz)*grip_flared(width, h, y, side, grip_flare)
        else:
            body += grip(width, top, y, side)
    for y, side in height_change_slits(length, rise, width, from_height, to_height, suppress, grip_flare):
        body -= grip_flared_cut(width, top, y, side)
    return body


# --- bridge -------------------------------------------------------------------

def over_bridge_height(from_height: float, to_height: float, bridge_height: float) -> float:
    """[B] :120 Over_Bridge_Height = max(bridge, from) + to."""
    return max(bridge_height, from_height) + to_height


def bridge_run_length(length_units: int, half: bool) -> float:
    """[B] :105 lengthMM (doubled for a half bridge, which keeps +Y only)."""
    return length_units*c.GRID*(2 if half else 1)


def _bridge_end(width, from_height, over, suppress, grip_flare) -> Part:
    """One [B] monokiniHeightChangeChannel(lengthMM=Grid_Size): a one-cell
    rise from `over` (front, toward the run) to `from_height` (back), centred
    at y=0. Its single cell is a rise cell; [B] :342-360 give it a plain grip
    at `over`, or a flared one of from_height on the raised floor."""
    off = over - from_height
    body = skinned_channel(c.GRID, c.GRID, (width, from_height, 0., off), (width, over, 0., 0.))
    code = _codes(suppress, 1)[0]
    flared = grip_flare > 0 and code != 'S'
    slits = []
    for side in _sides(code):
        if flared:
            body += Pos(0, 0, off)*grip_flared(width, from_height, 0., side, grip_flare)
            slits.append(Pos(0, 0, off)*grip_flared_cut(width, from_height, 0., side))
        else:
            body += grip(width, over, 0., side)
    for slit in slits:
        body -= slit
    return body


def bridge_tunnel(width: float, run: float, bridge_height: float, over: float) -> Part:
    """[B] :175-177 hull() of the crossing monokiniChannel (length 2G + width,
    width = run, height = bridge_height, spin 90) lifted to the grip plane.

    Its section across Y is the hull of the U profile and the grips' nub and
    top corners: (u=0, h-0.4) and (u=0.7, h) (grip.py _profile). Its grips
    span past both walls of this channel at every width (cells at 28 mm over
    2G + width), so the hull is one prism here.
    """
    r, h, z0 = run/2, bridge_height, over - bridge_height
    k, cap, lc = c.TOP_CHAMFER, c.SNAP_CAPTURE, c.TOP_LITTLE_CHAMFER
    half = [(r - k, 0.), (r, k), (r, h - lc), (r - cap, h)]
    pts = half + [(-y, z) for y, z in reversed(half)]
    span = 2*c.GRID + width
    face = Face(Wire.make_polygon([Vector(-span/2, y, z + z0) for y, z in pts], close=True))
    return extrude(face, span, dir=(1, 0, 0))


def bridge_channel(width: float, from_height: float, to_height: float, bridge_height: float,
                   length_units: int, *, half: bool = False, suppress: str = '',
                   grip_flare: float = 0., run_cutters=()) -> Part:
    """[B] :131-178. `run_cutters` (cord cutouts, label) cut the straight run
    only, as the source's inner diff() does. A half bridge keeps y >= 0
    ([B] :131 back_half at y=0) and is not re-centred."""
    over = over_bridge_height(from_height, to_height, bridge_height)
    run = bridge_run_length(length_units, half)
    fields = (suppress.split(',') + ['', ''])[:2]
    middle = Pos(0, -run/2, 0)*extrude(monokini_profile(width, over), run, dir=(0, 1, 0))
    for cutter in run_cutters:
        middle -= cutter
    end = Pos(0, run/2 + c.GRID/2, 0)*_bridge_end(width, from_height, over, fields[0], grip_flare)
    part = middle + end
    if not half:
        other = Pos(0, run/2 + c.GRID/2, 0)*_bridge_end(width, from_height, over, fields[1], grip_flare)
        part += mirror(other, Plane.XZ)
    part -= bridge_tunnel(width, run, bridge_height, over)
    if half:
        top = run/2 + c.GRID + 1
        part &= Pos(0, top/2, over/2)*Box(width + 2*c.GRID, top, over + 2)
    return part


# --- cord cutouts ([W] :145-154, [H] :143-152, [B] :154-163) --------------------

def cutout_centres(number: int, spacing: float, shift: float) -> list[float]:
    """ycopies(n, spacing) centred, then fwd(shift)."""
    return [(j - (number-1)/2)*spacing - shift for j in range(number)]


def side_cutouts(span_width: float, height: float, *, number: int, side: str, cutout_width: float,
                 spacing: float, shift: float) -> list[Part]:
    """The transitions' older cord cutout: one $fn=50 cylinder of radius
    cutout_width/2 along X, round bottom at z = 2*SNAP_WALL, under a box up to
    height + SNAP_WALL. Both Sides spans the whole channel (width + 5), Left
    Side (+X wall) and Right Side (-X wall) half of it centred on that wall
    (left(+/-channelWidth/2), cylinder anchor=LEFT orient=LEFT is centred on
    its axis). span_width is the source's channelWidth (the wider end)."""
    if side == 'None' or number <= 0:
        return []
    if side not in SIDE_CUTOUTS:
        raise ValueError(f'cord_side_cutouts {side!r} not in {SIDE_CUTOUTS}')
    r = cutout_width/2
    length = span_width + 5 if side == 'Both Sides' else span_width/2
    x = {'Both Sides': 0., 'Left Side': span_width/2, 'Right Side': -span_width/2}[side]
    zc, top = 2*c.SNAP_WALL + r, height + c.SNAP_WALL
    cuts = []
    for y in cutout_centres(number, spacing, shift):
        cyl = Pos(x, y, zc)*Rot(0, 90, 0)*Cylinder(r, length)
        box = Pos(x, y, (zc + top)/2)*Box(length, 2*r, top - zc)
        cuts.append(cyl + box)
    return cuts
