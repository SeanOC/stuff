# SPDX-License-Identifier: CC-BY-SA-4.0
"""Solid-wall drawer body, before mount/magnet/stopper cuts and bed treatment.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:384-394,
1354-1357,1372-1483. This module is the geometric foundation of the port;
it is not yet a registered, finished printable model.

Model frame: back at Y=0, open front at +Y, height along Z. A proper rotation
maps the author frame (x,y,z) to (-x,z,y); the author's Left is consequently
model +X. Source Top/Bottom retain their +Z/-Z meaning. Worst-case load is
a filled drawer pulling the back away from its mounts; the continuous box
walls carry that load. The requested slot-face-down print transform is
provided explicitly for printability assessment in PLA/PCTG.
"""
from dataclasses import dataclass
from math import sqrt

from build123d import Face, Pos, Rot, Solid, Wire

from openconnect.constants import TILE_SIZE
from openconnect.slot import pocket_depth


AUTHOR_TO_MODEL = Rot(90, 0, 180)
SLOT_FACES = ('Back', 'Top', 'Bottom', 'Left', 'Right')


@dataclass(frozen=True)
class Dimensions:
    width: float
    height: float
    depth: float
    inner_width: float
    inner_height: float
    inner_depth: float
    slot_thickness: float
    wall: float
    outer_chamfer: float
    inner_chamfer: float
    slot_face: str
    source_x: float
    source_y: float


def dimensions(values=None):
    """Author tile-based sizes; extra slot thickness extends only its face."""
    v = values or {}
    nh, nv, nd = (v.get(k, default) for k, default in (
        ('horizontal_grids', 5), ('vertical_grids', 2), ('depth_grids', 5)))
    if any(isinstance(n, bool) or not isinstance(n, int) or n <= 0
           for n in (nh, nv, nd)):
        raise ValueError('drawer grid counts must be greater than 0')
    wall = v.get('shell_thickness', 2.4)
    if wall <= 0:
        raise ValueError('shell_thickness must be greater than 0')
    backing = v.get('shell_to_slot_wall_thickness', 0.9)
    if backing < 0.8:
        raise ValueError('shell_to_slot_wall_thickness below 0.8 mm leaves less '
                         'slot backing than the openconnect-slot-shallow contract')
    slot = pocket_depth((v.get('slot_side_clearance', 0.1),
                         v.get('slot_depth_clearance', 0.1))) + backing
    w, h, depth = nh*TILE_SIZE, nv*TILE_SIZE, nd*TILE_SIZE
    iw, ih, idepth = w-2*wall, h-2*wall, depth-slot
    if min(iw, ih, idepth) <= 0:
        raise ValueError('shell inner dimensions must be greater than 0; increase '
                         'grid counts or reduce shell_thickness/shell_to_slot_wall_thickness')
    face = v.get('shell_slot_position', 'Back')
    if face not in SLOT_FACES:
        raise ValueError('shell_slot_position must be Back, Top, Bottom, Left or Right')
    extra = slot-wall
    x = extra/2 * ({'Left': -1, 'Right': 1}.get(face, 0))
    y = extra/2 * ({'Top': 1, 'Bottom': -1}.get(face, 0))
    chamfer = v.get('shell_outer_chamfer', 2.0)
    return Dimensions(w + (extra if face in ('Left', 'Right') else 0),
                      h + (extra if face in ('Top', 'Bottom') else 0), depth,
                      iw, ih, idepth, slot, wall, chamfer,
                      max(0, chamfer + wall*sqrt(2)-2*wall), face, x, y)


def _section(width, height, chamfer, except_face=None):
    """Convex XY section with the source's long-edge chamfer exceptions."""
    points = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = sx*width/2, sy*height/2
        omit = ((except_face == 'Top' and sy == 1)
                or (except_face == 'Bottom' and sy == -1)
                or (except_face == 'Left' and sx == -1)
                or (except_face == 'Right' and sx == 1))
        c = 0 if omit else chamfer
        if c:
            if sx == sy:
                points.extend(((x, y-sy*c, 0), (x-sx*c, y, 0)))
            else:
                points.extend(((x-sx*c, y, 0), (x, y-sy*c, 0)))
        else:
            points.append((x, y, 0))
    return Face(Wire.make_polygon(points, close=True))


def source_body(values=None):
    """SCAD-frame box and chamfered open-front cavity, before feature cuts.

The cavity centre stays on the tile grid after the source's top-level
placement (:1354-1357); the extra slot thickness belongs outside that grid.
Its depth is tile depth minus slot thickness on every slot-face choice.
"""
    d = dimensions(values)
    outer = Pos(d.source_x, d.source_y, 0) * Solid.extrude(
        _section(d.width, d.height, d.outer_chamfer, d.slot_face), (0, 0, d.depth))
    cavity = Pos(0, 0, d.slot_thickness) * Solid.extrude(
        _section(d.inner_width, d.inner_height, d.inner_chamfer),
        (0, 0, d.inner_depth))
    return outer - cavity


def body(values=None):
    """Model-frame body before feature cuts (not a finished print)."""
    return AUTHOR_TO_MODEL * source_body(values)


def print_frame(values=None):
    """Requested slot-face-down orientation, with its face exactly at Z=0."""
    d = dimensions(values)
    rotation, height = {
        'Back': (Rot(0, 0, 0), 0),
        'Top': (Rot(-90, 0, 0), d.source_y+d.height/2),
        'Bottom': (Rot(90, 0, 0), d.height/2-d.source_y),
        'Left': (Rot(0, -90, 0), d.width/2-d.source_x),
        'Right': (Rot(0, 90, 0), d.width/2+d.source_x),
    }[d.slot_face]
    return Pos(0, 0, height) * rotation * AUTHOR_TO_MODEL.inverse()
