# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Straight monokini channel with grips, separators, cord cutouts, label and
filament grooves.

[C] monokini_I_channel.scad:130-204 (top level) and :257-371
monokiniChannel. Model frame = the author's render frame: X across the
channel, Y along it (centred), Z up; Z=0 is the closed, chamfered face and
the openGrid grips stand on the wall tops at Z = height - BASE_HEIGHT. The
part prints as modelled (closed face on the bed, grips up).

The source's 0.01 mm Nudge overlaps are not reproduced: the port spans
exactly +/-length/2 (reference meshes span -L/2-0.015 .. L/2-0.005).
"""
from __future__ import annotations

from math import atan2, degrees, radians, sqrt, tan

from build123d import (Box, Cylinder, Face, Part, Plane, Pos, Rot, ThreePointArc, Transition, Vector,
                       Wire, extrude, mirror, sweep)

from . import constants as c
from .grip import grip, grip_flared, grip_flared_cut
from .profile import midline_positions, monokini_profile, separator_rect

CUTOUT_SIDES = ('Left Side', 'Right Side', 'Both Sides', 'None', 'Left Side Top', 'Right Side Top')
SUPPRESS_CODES = 'NLRBS'   # [C] :89 key: None, Left, Right, Both, Static
SEPARATOR_CODES = 'NS'     # [C] :92 key: None, Separator
# Above this the flared rail's base (u = SNAP_CAPTURE at z = TOP_CHAMFER)
# leaves the wall's outer face: TOP_CHAMFER*tan(f) > SNAP_CAPTURE.
MAX_FLARE_DEG = 9.9


def cell_centres(length_mm: float) -> list[float]:
    """Grip cell centres, index 0 at -Y ([C] :303 path_copies over the length;
    author render 'LNNNB' drops the +X grip at y=-56 and both at y=+56)."""
    n = round(length_mm/c.GRID)
    return [(k - (n-1)/2)*c.GRID for k in range(n)]


def parse_codes(name: str, value: str, codes: str, count: int) -> str:
    """First comma field, upper-cased ([C] :119-120 str_split(upcase(...))[0]).

    Each character applies to one index. The author silently ignores extra
    characters; the port names them.
    """
    field = value.upper().split(',')[0].strip()
    bad = sorted(set(field) - set(codes))
    if bad:
        raise ValueError(f'{name} {value!r}: unknown code(s) {"".join(bad)}; use {", ".join(codes)}')
    if len(field) > count:
        raise ValueError(f'{name} {value!r} has {len(field)} codes but the channel has only {count}')
    return field


def present_grips(length_mm: float, suppress: str, grip_flare: float = 0.):
    """(y_cell, side, flared) for every grip the suppress codes keep (:303-321)."""
    cells = cell_centres(length_mm)
    if length_mm <= c.GRIP_SIZE:
        return []
    codes = parse_codes('suppress_connectors', suppress, SUPPRESS_CODES, len(cells))
    out = []
    for y, code in zip(cells, codes.ljust(len(cells), 'N')):
        for side, gone in ((1, 'BL'), (-1, 'BR')):
            if code not in gone:
                out.append((y, side, grip_flare > 0 and code != 'S'))
    return out


def channel_section(width_mm: float, height_mm: float, separators: str = '',
                    top_chamfer: float = c.TOP_CHAMFER) -> Face:
    """The U profile plus the separator walls the codes select (:304-310)."""
    xs = midline_positions(width_mm)
    sep = parse_codes('channel_separators', separators, SEPARATOR_CODES, len(xs))
    section = monokini_profile(width_mm, height_mm, top_chamfer)
    for x, code in zip(xs, sep):
        if code == 'S':
            section = section.fuse(separator_rect(x, height_mm)).clean()
    return section


def straight_channel(length_mm: float, width_mm: float, height_mm: float, *,
                     suppress: str = '', separators: str = '', grip_flare: float = 0.,
                     top_chamfer: float = c.TOP_CHAMFER) -> Part:
    """monokiniChannel (:257-371): profile along Y, one grip per wall per cell.

    top_chamfer=0 with height_mm = SNAP_WALL + BASE_HEIGHT is the text label
    plate (monokini_text_label.scad:198-280 monokiniPlate): the floor alone,
    the same grips per cell standing on its top face.
    """
    section = channel_section(width_mm, height_mm, separators, top_chamfer)
    body = Pos(0, -length_mm/2, 0)*extrude(section, length_mm, dir=(0, 1, 0))
    grips, slits = grip_parts(length_mm, width_mm, height_mm, suppress, grip_flare)
    for g in grips:
        body += g
    for slit in slits:
        body -= slit
    return body


def grip_parts(length_mm: float, width_mm: float, height_mm: float, suppress: str = '',
               grip_flare: float = 0.) -> tuple[list[Part], list[Part]]:
    """(grips, flare slits) of one straight run in its own frame: what
    monokiniChannel adds with suppressWalls=true ([C] monokini_S_channel.scad:
    361 skips only the walls) and its flare-slit difference set."""
    if grip_flare > MAX_FLARE_DEG:
        raise ValueError(
            f'grip_flare above {MAX_FLARE_DEG:g} degrees leaves the flared grip base '
            f'overhanging the wall chamfer (a flat, unsupported ledge)')
    grips, slits = [], []
    for y, side, flared in present_grips(length_mm, suppress, grip_flare):
        if flared:
            grips.append(grip_flared(width_mm, height_mm, y, side, grip_flare))
            slits.append(grip_flared_cut(width_mm, height_mm, y, side))
        else:
            grips.append(grip(width_mm, height_mm, y, side))
    return grips, slits


def path_channel(path: Wire, width_mm: float, height_mm: float, separators: str = '') -> Part:
    """monokiniChannelPath ([C] monokini_S_channel.scad:664-726): the section
    (and the separator walls the codes select) swept along a path in the XY
    plane, gripless. The source path_extrude2d chains straight segments,
    mitred on the inside of each joint and filled round (a faceted
    rotate_extrude) on the outside; the port sweeps the path itself with
    Transition.ROUND, the same joint with a true arc, and a smooth (Bezier)
    path stays smooth where the source samples it into chords.

    The section stays the channel section only while the path's radius of
    curvature is at least width_mm/2; callers check that before sweeping.
    """
    start, tangent = path.position_at(0), path.tangent_at(0)
    spin = degrees(atan2(-tangent.X, tangent.Y))
    section = Pos(start.X, start.Y, 0)*Rot(0, 0, spin)*channel_section(width_mm, height_mm, separators)
    return sweep(section, path, transition=Transition.ROUND)


def cutout_centres(number: int, spacing: float, shift: float) -> list[float]:
    """[C] :143-144 ycopies(n, spacing) centred, then fwd(shift)."""
    return [(j - (number-1)/2)*spacing - shift for j in range(number)]


def cord_cutouts(width_mm: float, height_mm: float, *, number: int, side: str,
                 cutout_width: float, spacing: float, shift: float) -> list[Part]:
    """[C] :131-190 cord cutouts, one cutter per opening.

    Side modes: a U-slot through the wall, round bottom at z = 2*SNAP_WALL,
    CUTOUT_DEPTH long across the wall face ('Right Side' cuts the -X wall,
    'Left Side' the +X wall, :167-182). Top modes: a slot through the closed
    face from a round end at x = +/-(w/2 - 2r) through the far wall, over
    z = TOP_CUTOUT_Z +/- height/2 (:145-166).
    """
    if side == 'None' or number <= 0:
        return []
    if side not in CUTOUT_SIDES:
        raise ValueError(f'cord_side_cutouts {side!r} not in {CUTOUT_SIDES}')
    r, w = cutout_width/2, width_mm/2
    cuts = []
    for y in cutout_centres(number, spacing, shift):
        if side in ('Left Side', 'Right Side', 'Both Sides'):
            walls = {'Left Side': (1,), 'Right Side': (-1,), 'Both Sides': (1, -1)}[side]
            zc, top = 2*c.SNAP_WALL + r, height_mm + c.SNAP_WALL
            for s in walls:
                cyl = Pos(s*w, y, zc)*Rot(0, 90, 0)*Cylinder(r, c.CUTOUT_DEPTH)
                box = Pos(s*w, y, (zc+top)/2)*Box(c.CUTOUT_DEPTH, 2*r, top-zc)
                cuts.append(cyl + box)
        else:
            s = 1 if side == 'Left Side Top' else -1
            ax, length = s*(w - 2*r), 2*w - r + 0.01
            z0, z1 = c.TOP_CUTOUT_Z - height_mm/2, c.TOP_CUTOUT_Z + height_mm/2
            cyl = Pos(ax, y, (z0+z1)/2)*Cylinder(r, z1-z0)
            box = Pos(ax - s*length/2, y, (z0+z1)/2)*Box(length, 2*r, z1-z0)
            cuts.append(cyl + box)
    return cuts


def side_cut_walls(side: str) -> tuple[int, ...]:
    return {'Left Side': (1,), 'Right Side': (-1,), 'Both Sides': (1, -1)}.get(side, ())


def cutout_sill_regions(width_mm: float, *, number: int, side: str, cutout_width: float,
                        spacing: float, shift: float, grow: float = 0.02) -> list[Part]:
    """Exact envelopes of each side cutout's sill: its round floor across the
    wall and the exterior chamfer under that floor.

    The slot floor bottoms out at z = 2*SNAP_WALL = TOP_CHAMFER (:170, :178),
    the height where the exterior chamfer starts, so the wall under the sill
    thins to an edge at the outer face (the author's cord-exit sill).
    """
    r, w = cutout_width/2, width_mm/2
    out = []
    for y in cutout_centres(number, spacing, shift) if number > 0 else ():
        for s in side_cut_walls(side):
            cyl = Pos(s*w, y, 2*c.SNAP_WALL + r)*Rot(0, 90, 0)*Cylinder(r + grow, c.CUTOUT_DEPTH)
            wall = Pos(s*(w - c.SNAP_WALL/2 + grow/2), y, 2*c.SNAP_WALL + r)*Box(
                c.SNAP_WALL + grow, 2*r + 2*grow, 2*r + 2*grow)
            under = Pos(s*(w - c.SNAP_WALL/2 + grow/2), y, (c.SNAP_WALL + c.TOP_CHAMFER)/2)*Box(
                c.SNAP_WALL + grow, 2*r + 2*grow, c.TOP_CHAMFER - c.SNAP_WALL + 2*grow)
            out.append((cyl & wall) + under)
    return out


def check_cutouts(width_mm: float, height_mm: float, cells: list[float], suppress: str, *,
                  number: int, side: str, cutout_width: float, spacing: float, shift: float,
                  grip_flare: float = 0.) -> None:
    """Named errors for cutouts that leave unprintable geometry.

    A cutout may not cross a grip on a wall it cuts: it would leave a grip
    stub thinner than the wall floor (author render, 1 cutout at y=0: a
    0.09 mm sliver), or a 0.1 mm fin beside a flare slit. A Top-mode slot
    spans TOP_CUTOUT_Z +/- height/2 (:151): its floor must clear the bed face
    or sit 0.9 mm above the chamfer (height 16 leaves a 0.1 mm skin), and a
    wall left above it inside the slot is a flat unsupported ceiling.
    """
    inner = width_mm - 2*c.SNAP_WALL
    if cutout_width >= inner:
        raise ValueError(f'cord_cutout_width {cutout_width:g} mm is not narrower than the '
                         f'{inner:g} mm channel interior')
    if side == 'None' or number <= 0:
        return
    if side in ('Left Side Top', 'Right Side Top'):
        top, wall_top = c.TOP_CUTOUT_Z + height_mm/2, height_mm - c.BASE_HEIGHT
        floor = c.TOP_CUTOUT_Z - height_mm/2
        if 0 < floor < c.TOP_CHAMFER + 0.9:
            raise ValueError(f'a {side} cord cutout at {height_mm:g} mm height bottoms out at '
                             f'z={floor:g} mm, inside the closed face, leaving a skin under 0.9 mm')
        if top < wall_top:
            raise ValueError(f'a {side} cord cutout stops at z={top:g} mm, below the {wall_top:g} mm '
                             f'wall top, leaving an unsupported wall span over the opening')
        walls = (-1,) if side == 'Left Side Top' else (1,)
    else:
        walls = side_cut_walls(side)
    r = cutout_width/2
    codes = suppress.upper().split(',')[0].ljust(len(cells), 'N')
    for y in cutout_centres(number, spacing, shift):
        for yc, code in zip(cells, codes):
            flared = grip_flare > 0 and code != 'S'
            reach = c.GRIP_SIZE/2 + (c.FLARE_SLIT + 0.9 if flared else 0.)
            for wall in walls:
                if code in ('B', 'L' if wall > 0 else 'R'):
                    continue
                if abs(y - yc) < r + reach:
                    raise ValueError(
                        f'the {side} cord cutout at y={y:g} mm crosses the grip at y={yc:g} mm on the '
                        f'{"+" if wall > 0 else "-"}X wall; move it between grips or suppress that grip')


def label_cutter(text: str, text_size: float, depth: float, width_mm: float,
                 length_mm: float, face: tuple[float, float] | None = None) -> Part:
    """[C] :191-196: text debossed into the closed (bed) face, read from below
    along +Y, centred. Glyphs come from the repo's labels seam (Inter Bold,
    labels/label_text.py), not the author's Raleway.

    face: the (across, along) flat the ink must fit; default the channel's
    closed face inside its TOP_CHAMFER."""
    from labels.label_text import text_sketch
    sketch = text_sketch(text, size=text_size*c.OPENSCAD_TEXT_SCALE)
    bb = sketch.bounding_box()
    sketch = Pos(-bb.center().X, -bb.center().Y)*sketch
    # spin=-90 then orient=BOT: (x, y) -> (y, x), a mirror read from -Z.
    sketch = mirror(sketch, Plane(origin=(0, 0, 0), z_dir=(1, -1, 0)))
    bb = sketch.bounding_box()
    flat, along = face or (width_mm - 2*c.TOP_CHAMFER, length_mm)
    if bb.size.X > flat or bb.size.Y > along:
        raise ValueError(f'label {text!r} at size {text_size:g} is {bb.size.Y:.1f} x '
                         f'{bb.size.X:.1f} mm; the closed face is {along:g} x {flat:g} mm')
    return extrude(sketch, depth)


def filament_grooves(width_mm: float, length_mm: float, *, diameter: float, depth: float,
                     offset: float, repeat: int, spacing: float) -> list[Part]:
    """[C] :327-333: teardrop grooves along Y, tip up, centre at z=-depth.

    The source hard-codes teardrop2d(d=1.75) and ignores Filament_Diameter;
    the port honours it (identical at the 1.75 default). Named errors keep
    every groove inside the flat floor with the 0.9 mm wall floor above it.
    """
    r, zc = diameter/2, -depth
    tip = zc + r*sqrt(2)
    if diameter <= 0 or repeat < 1:
        raise ValueError('filament_diameter and filament_repeat must be positive')
    if zc <= -r:
        raise ValueError(f'filament_depth {depth:g} mm puts the groove below the part')
    if tip > c.SNAP_WALL - 0.9:
        raise ValueError(f'filament groove tip at z={tip:.2f} mm leaves less than 0.9 mm of '
                         f'floor (floor top z={c.SNAP_WALL:g}); increase filament_depth')
    if repeat > 1 and spacing - 2*r < 0.9:
        raise ValueError(f'filament_spacing {spacing:g} mm leaves less than 0.9 mm between grooves')
    xs = [(repeat-1)*spacing/2 - i*spacing - offset for i in range(repeat)]
    limit = width_mm/2 - c.INNER_CHAMFER
    if max(abs(x) for x in xs) + r > limit:
        raise ValueError(f'filament grooves reach |x|={max(abs(x) for x in xs)+r:.2f} mm, '
                         f'past the {limit:.2f} mm flat floor')
    d = r*sqrt(2)/2  # tangent points of the 45 degree teardrop
    grooves = []
    for x in xs:
        pts = [Vector(x, -length_mm/2, zc + r*sqrt(2))]
        arc = ThreePointArc((x - d, -length_mm/2, zc + d), (x, -length_mm/2, zc - r),
                            (x + d, -length_mm/2, zc + d))
        wire = Wire([arc, *Wire.make_polygon([arc @ 1, pts[0], arc @ 0], close=False).edges()])
        grooves.append(extrude(Face(wire), length_mm, dir=(0, 1, 0)))
    return grooves
