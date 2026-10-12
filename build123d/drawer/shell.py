# SPDX-License-Identifier: CC-BY-SA-4.0
"""Solid-wall openConnect drawer shell with mounts, fittings and bed treatment.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:384-394,
1354-1357,1372-1483. Published magnet and stopper pockets are preserved;
openConnect library cutters supply the mating profiles. The only exterior
geometry change is the mandatory 0.3 mm bed-edge bevel.

Model frame: back at Y=0, open front at +Y, height along Z. A proper rotation
maps the author frame (x,y,z) to (-x,z,y); the author's Left is consequently
model +X. Source Top/Bottom retain their +Z/-Z meaning. Worst-case load is
a filled drawer pulling the back away from its mounts; the continuous box
walls carry that load. Print back-wall-down in PLA/PCTG for every mounting
face (source placement :1354-1357 and the REV 3d orientation correction).
"""
from dataclasses import dataclass, replace
from math import radians, sqrt

from build123d import Align, Box, Cone, Cylinder, Face, Line, Part, Plane, Pos, Rot, Solid, ThreePointArc, Wire, section
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
from OCP.StdFail import StdFail_NotDone

from openconnect.constants import TILE_SIZE, EPS, EDGE_WALL_MIN_W, HEAD_MIDDLE_HEIGHT
from openconnect.grid import fixtures, layout
from openconnect.slot import pocket_depth
from . import constants as c


AUTHOR_TO_MODEL = Rot(0, 0, 180) * Rot(90, 0, 0)
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
    """Back-wall-down for every mount face (SCAD :1354-1357; REV 3d)."""
    return AUTHOR_TO_MODEL.inverse()


def slot_layout(values=None):
    v = values or {}
    d = dimensions(v)
    nh, nv, nd = (v.get(k, default) for k, default in (
        ('horizontal_grids', 5), ('vertical_grids', 2), ('depth_grids', 5)))
    h = nv if d.slot_face in ('Left', 'Right') else nh
    rows = nv if d.slot_face == 'Back' else nd
    excluded = ((0, 0), (h-1, 0)) if (
        (d.slot_face == 'Top' and v.get('add_stopper_holes', True))
        or (d.slot_face in ('Left', 'Right') and v.get('add_side_magnet_holes', True))) else ()
    dx, dz = v.get('slot_horizontal_offset', 0), v.get('slot_vertical_offset', 0)
    # The author fills the entire face with whole tiles, as on the shelf.
    if abs(dx) > 1e-7:
        raise ValueError('slot_horizontal offset leaves the slot face')
    if abs(dz) > 1e-7:
        raise ValueError('slot_vertical offset leaves the slot face')
    points = layout(h, rows,
                    position=v.get('slot_position', 'All').lower().replace(' ', '-'),
                    lock=v.get('slot_lock_distribution', 'Top Corners').lower().replace(' ', '-'),
                    slide='left' if d.slot_face in ('Top', 'Bottom') else 'up',
                    entryramp_flip=v.get('slot_entryramp_flip', False),
                    except_positions=excluded)
    return h, rows, [replace(p, x=p.x+dx, z=p.z+dz) for p in points]


def source_slot_frame(values=None):
    """Place the library's -Y mounting face on the chosen source box face."""
    d = dimensions(values)
    return {
        'Back': AUTHOR_TO_MODEL,
        'Top': Pos(d.source_x, d.source_y+d.height/2, d.depth/2)*Rot(0, 0, 180),
        'Bottom': Pos(d.source_x, d.source_y-d.height/2, d.depth/2),
        'Left': Pos(d.source_x-d.width/2, d.source_y, d.depth/2)*Rot(0, 0, -90),
        'Right': Pos(d.source_x+d.width/2, d.source_y, d.depth/2)*Rot(0, 0, 90),
    }[d.slot_face]


def slot_fixtures(values=None):
    v = values or {}
    d = dimensions(v)
    h, rows, points = slot_layout(v)
    clearance = (v.get('slot_side_clearance', .1), v.get('slot_depth_clearance', .1))
    fx = fixtures(points, clearance=clearance,
                  edge_feature='none' if d.slot_face == 'Back' else 'side')
    # [C] :1428 and :1264: the source clips the whole Back grid's corners.
    ch = min(4, max(.8, EDGE_WALL_MIN_W)+HEAD_MIDDLE_HEIGHT+1) if d.slot_face == 'Back' else 0
    # _section XY -> local XZ; translate mouth-plane excess outwards.
    clip = Pos(0, pocket_depth(clearance), 0)*Rot(90, 0, 0)*Solid.extrude(
        _section(h*TILE_SIZE, rows*TILE_SIZE, ch), (0, 0, pocket_depth(clearance)+EPS))
    frame = AUTHOR_TO_MODEL * source_slot_frame(v)
    fx.cutters = [frame*(cut & clip) for cut in fx.cutters]
    fx.seat_locs = [frame*loc for loc in fx.seat_locs]
    fx.onramp_locs = [frame*loc for loc in fx.onramp_locs]
    def direction(xyz):
        return tuple((frame*Pos(*xyz)).position-frame.position)
    fx.entry_axis = direction(fx.entry_axis)
    fx.face_normal = direction(fx.face_normal)
    return fx


def source_back_magnet_positions(values=None):
    v = values or {}
    if not v.get('add_back_magnet_holes', True):
        return []
    d = dimensions(v)
    nh, nv = v.get('horizontal_grids', 5), v.get('vertical_grids', 2)
    return [(d.source_x-(nh-2)*TILE_SIZE/2+i*TILE_SIZE*max(nh-2, 0),
             d.source_y-(nv-1)*TILE_SIZE/2+c.BACK_MAGNET_OCSLOT_OFFSET, 0)
            for i in range(min(nh-1, 2))]


def source_side_magnet_positions(values=None):
    v = values or {}
    if not v.get('add_side_magnet_holes', True):
        return []
    d = dimensions(v)
    radius = v.get('side_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
    nv = v.get('vertical_grids', 2)
    # BOSL2 teardrop TOP anchor is at r, not at cap_h (r+0.2).
    z = d.depth-v.get('shell_side_magnet_edge_distance', 6)-radius
    return [(side, (side*d.inner_width/2, d.source_y+(j-(nv-1)/2)*TILE_SIZE, z))
            for side in (-1, 1) for j in range(nv)]


def _teardrop(radius):
    """45-degree teardrop with the source's horizontal cap at r+0.2."""
    t, cap = radius/sqrt(2), radius+.2
    end = radius*sqrt(2)-cap
    return Face(Wire([
        ThreePointArc((-t, t, 0), (0, -radius, 0), (t, t, 0)),
        Line((t, t, 0), (end, cap, 0)),
        Line((end, cap, 0), (-end, cap, 0)),
        Line((-end, cap, 0), (-t, t, 0)),
    ]))


def source_magnet_cutters(values=None):
    v = values or {}
    cuts = []
    positions = source_back_magnet_positions(v)
    if positions:
        radius = v.get('back_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
        depth = v.get('shell_back_magnet_thickness', 2)+c.MAGNET_HOLE_DEPTH_CLEARANCE
        # cyl(chamfer1=-0.2) flares the entrance, not the blind end.
        cutter = (Cylinder(radius, depth, align=(Align.CENTER, Align.CENTER, Align.MIN))
                  + Cone(radius+.2, radius, .2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        cuts.extend(Pos(*p)*cutter for p in positions)
    positions = source_side_magnet_positions(v)
    if positions:
        radius = v.get('side_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
        depth = v.get('shell_side_magnet_thickness', 1)+c.MAGNET_HOLE_DEPTH_CLEARANCE
        cutter = Solid.extrude(_teardrop(radius), (0, 0, depth))
        # Local XY -> source YZ, extrusion -> +X. Top of drop points +Z.
        orient = Rot(0, 0, 90) * Rot(90, 0, 0)
        for side, (x, y, z) in positions:
            start = x-depth+2*EPS if side == -1 else x-2*EPS
            cuts.append(Pos(start, y, z)*orient*cutter)
    return cuts


def source_stopper_positions(values=None):
    v = values or {}
    if not v.get('add_stopper_holes', True):
        return []
    d = dimensions(v)
    nh = v.get('horizontal_grids', 5)
    return [(d.source_x-d.width/2+TILE_SIZE/2+j*(nh-1)*TILE_SIZE,
             d.source_y+d.height/2,
             d.depth-v.get('stopper_edge_distance', 3)-c.STOPPER_HEIGHT)
            for j in range(1 if nh == 1 else 2)]


def source_stopper_cutters(values=None):
    d = dimensions(values)
    cuts = []
    w, r, flange = c.STOPPER_WIDTH/2, c.STOPPER_ROUNDING, c.STOPPER_FLANK_DEPTH
    depth = d.wall+2*EPS
    # Shaft cross-section (X,inward depth), with the author's two concave
    # quarter-rounds at its entrance. No printed clip geometry is ported here.
    section = Face(Wire([
        Line((-w-r, flange, 0), (w+r, flange, 0)),
        ThreePointArc((w+r, flange, 0),
                      (w+r-r/sqrt(2), flange+r-r/sqrt(2), 0), (w, flange+r, 0)),
        Line((w, flange+r, 0), (w, depth, 0)),
        Line((w, depth, 0), (-w, depth, 0)),
        Line((-w, depth, 0), (-w, flange+r, 0)),
        ThreePointArc((-w, flange+r, 0),
                      (-w-r+r/sqrt(2), flange+r-r/sqrt(2), 0), (-w-r, flange, 0)),
    ]))
    shaft = Solid.extrude(section, (0, 0, c.STOPPER_HEIGHT))
    cutter = shaft + Box(c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH, flange, c.STOPPER_HEIGHT,
                         align=(Align.CENTER, Align.MIN, Align.MIN))
    if d.slot_face == 'Top' and d.slot_thickness > d.wall:
        cutter += Pos(0, depth, 0)*Box(c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH,
                                     d.slot_thickness-d.wall, c.STOPPER_HEIGHT,
                                     align=(Align.CENTER, Align.MIN, Align.MIN))
    # Reflect local inward-depth +Y to the source's inward -Y.
    from build123d import Plane
    cutter = cutter.mirror(Plane.XZ)
    for p in source_stopper_positions(values):
        cuts.append(Pos(*p)*cutter)
    return cuts


def before_bed_chamfer(values=None):
    part = source_body(values)
    for cut in source_magnet_cutters(values)+source_stopper_cutters(values):
        part -= cut
    part = AUTHOR_TO_MODEL*part
    for cut in slot_fixtures(values).cutters:
        part -= cut
    return part


def chamfer_bed(part, values=None):
    """Mandatory 0.3 mm bevel on every loop of the back-wall bed face."""
    source = AUTHOR_TO_MODEL.inverse()*part
    v = values or {}
    magnets = source_back_magnet_positions(v)
    radius = v.get('back_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
    beds = [f for f in source.faces()
            if abs(f.bounding_box().max.Z) < 1e-6 and f.normal_at().Z < -.999]
    bevel = BRepFilletAPI_MakeChamfer(source.wrapped)
    for face in beds:
        for edge in face.edges():
            # The author already flares magnet mouths by .2 mm at 45°.
            # Re-chamfering a cone at its own angle is degenerate in OCCT;
            # extend these existing cones to .3 mm with exact CSG below.
            if (edge.geom_type.name == 'CIRCLE' and abs(edge.radius-radius-.2) < 1e-5
                    and any((edge.arc_center-Pos(*p).position).length < 1e-5 for p in magnets)):
                continue
            bevel.AddDA(.3, radians(45.01), edge.wrapped, face.wrapped)
    try:
        result = Part(bevel.Shape())
    except StdFail_NotDone:
        # At maximum side clearance, opposing .3 mm bevels meet at the
        # bottom of a .6 mm strip. OCCT's edge operation cannot collapse that
        # face. Intersect the bottom .3 mm with independently tapered section
        # wires instead; the upper body and all library dimensions stay exact.
        return AUTHOR_TO_MODEL*_bevel_from_sections(source)
    for point in magnets:
        result -= Pos(*point)*Cone(radius+.3, radius, .3,
                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    if not result.is_valid:
        raise ValueError('drawer bed chamfer produced invalid geometry')
    return AUTHOR_TO_MODEL*result


def _bevel_from_sections(source):
    layers = []
    for face in section(source, section_by=Plane.XY.offset(.3)).faces():
        layer = Solid.extrude_taper(Face(face.outer_wire()), (0, 0, -.3), 45)
        for wire in face.inner_wires():
            layer -= Solid.extrude_taper(Face(wire), (0, 0, -.3), -45)
        layers.append(source & layer)
    bb = source.bounding_box()
    centre = (bb.min+bb.max)*.5
    upper = Pos(centre.X, centre.Y, .3)*Box(bb.size.X+2, bb.size.Y+2, bb.size.Z,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    result = source & upper
    for layer in layers:
        result += layer
    if not result.is_valid or len(result.solids()) != 1:
        raise ValueError('drawer section bevel produced invalid geometry')
    return result


def build(values=None):
    return chamfer_bed(before_bed_chamfer(values), values)


def published_ceiling_regions(values=None):
    """Exact thin regions for the author's short magnet/stopper ceilings.

    [C] :1438/:1444 (teardrop cap_h=r+.2) and :1468/:1816-1821
    (stopper-hole roofs). Tests independently pin their reference heights,
    bridge spans and membership. These regions exclude no vertical walls.
    """
    v = values or {}
    d = dimensions(v)
    regions = []
    back_radius = v.get('back_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
    if 2*back_radius <= 10:
        for x, y, _ in source_back_magnet_positions(v):
            regions.append(Pos(x, y, v.get('shell_back_magnet_thickness', 2)+c.MAGNET_HOLE_DEPTH_CLEARANCE)
                           * Cylinder(back_radius, .001))
    radius = v.get('side_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
    depth = v.get('shell_side_magnet_thickness', 1)+c.MAGNET_HOLE_DEPTH_CLEARANCE
    cap = radius+.2
    for side, (x, y, z) in source_side_magnet_positions(v):
        start = x-depth+2*EPS if side == -1 else x-2*EPS
        regions.append(Pos(start, y, z+cap)*Box(depth, 2*(radius*sqrt(2)-cap), .001,
                                              align=(Align.MIN, Align.CENTER, Align.CENTER)))
    for x, y, z in source_stopper_positions(v):
        depth = max(d.wall, d.slot_thickness if d.slot_face == 'Top' else 0)+2*EPS
        regions.append(Pos(x, y-depth, z+c.STOPPER_HEIGHT)*Box(
            c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH, depth, .001,
            align=(Align.CENTER, Align.MIN, Align.CENTER)))
    return [AUTHOR_TO_MODEL*r for r in regions]
