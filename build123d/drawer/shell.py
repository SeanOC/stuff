# SPDX-License-Identifier: CC-BY-SA-4.0
"""openConnect drawer shell with selectable walls, fittings and bed treatment.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:384-394,
1354-1357,1372-1483. Published magnet and stopper pockets are preserved;
openConnect library cutters supply the mating profiles. The only exterior
geometry changes are the mandatory 0.3 mm bed-edge bevel, the selected
inward roofs on honeycomb ceilings longer than 10 mm, and the Left/Right
slot orientation recorded under "Deviations from the source" in
docs/openconnect-drawer.md.

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
DIVIDER_MODES = ('None', 'Width', 'Height', 'Both')


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


def validate_clearances(values=None):
    """REV 3e: keep the unchanged shallow contract's pull-off retention."""
    v = values or {}
    value = v.get('slot_side_clearance', .1)
    # Depth clearance retains the full library domain. The registry/library
    # diagnose its out-of-domain values; only side clearance loses retention.
    if isinstance(value, (int, float)) and value > c.SLOT_SIDE_CLEARANCE_MAX:
        raise ValueError(f'slot_side_clearance above {c.SLOT_SIDE_CLEARANCE_MAX:g} mm '
                         'leaves no openConnect head retention '
                         '(openconnect-slot-shallow contract)')


def dimensions(values=None):
    """Author tile-based sizes; extra slot thickness extends only its face."""
    v = values or {}
    validate_clearances(v)
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
        d.slot_face in ('Left', 'Right') and v.get('add_side_magnet_holes', True)) else ()
    if d.slot_face == 'Top' and v.get('add_stopper_holes', True):
        # [C] :1425-1426 frees the two corner tiles for the stopper holes. Width
        # compartments add stopper holes at their own end tiles; the port
        # frees those tiles too (the author's slots would collide). The Top
        # frame turns source -X into slot column h-1 (source_slot_frame).
        excluded = tuple((h-1-col, 0) for col in stopper_columns(v))
    dx, dz = v.get('slot_horizontal_offset', 0), v.get('slot_vertical_offset', 0)
    # The author fills the entire face with whole tiles, as on the shelf.
    if abs(dx) > 1e-7:
        raise ValueError('slot_horizontal offset leaves the slot face')
    if abs(dz) > 1e-7:
        raise ValueError('slot_vertical offset leaves the slot face')
    # Deliberate deviation from source :1427; see "Deviations from the source"
    # in docs/openconnect-drawer.md.
    slide = {'Back': 'up', 'Top': 'left', 'Bottom': 'left',
             'Left': 'left', 'Right': 'right'}[d.slot_face]
    points = layout(h, rows,
                    position=v.get('slot_position', 'All').lower().replace(' ', '-'),
                    lock=v.get('slot_lock_distribution', 'Top Corners').lower().replace(' ', '-'),
                    slide=slide,
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


def compartments(values=None):
    """Width and height compartments in tiles ([C] :399-417).

    Width runs from source -X (the author's Left). Height runs from the top
    (+Y), as the author's dividers do (:1597, align=BACK).
    """
    from .dividers import Compartments, parse
    v = values or {}
    mode = v.get('add_shell_divider', 'None')
    if mode not in DIVIDER_MODES:
        raise ValueError('add_shell_divider must be None, Width, Height or Both')
    nh, nv = v.get('horizontal_grids', 5), v.get('vertical_grids', 2)
    width = (parse(v.get('shell_width_compartment_list', '3,2'), nh, 'shell_width_compartment_list')
             if mode in ('Width', 'Both') else Compartments(nh, (), (nh,)))
    height = (parse(v.get('shell_height_compartment_list', '1,1'), nv, 'shell_height_compartment_list')
              if mode in ('Height', 'Both') else Compartments(nv, (), (nv,)))
    return width, height


def _starts(parts):
    return (0,)+parts.positions


def source_back_magnet_positions(values=None):
    """[C] :1450-1462 per compartment: tiles 1 and n-2 of each compartment.

    Rows sit 4.6 mm above each compartment's bottom tile centre. The author
    offsets rows from the BOTTOM with the top-first divider sums, which
    misses compartments of an asymmetric height list; the port uses each
    compartment's own bottom tile (equal for symmetric lists).
    """
    v = values or {}
    if not v.get('add_back_magnet_holes', True):
        return []
    d = dimensions(v)
    nh, nv = v.get('horizontal_grids', 5), v.get('vertical_grids', 2)
    width, height = compartments(v)
    rows = [nv-start-size for start, size in zip(_starts(height), height.sizes)]
    return [(d.source_x-(nh-2)*TILE_SIZE/2+(start+i*max(size-2, 0))*TILE_SIZE,
             d.source_y-(nv-1)*TILE_SIZE/2+row*TILE_SIZE+c.BACK_MAGNET_OCSLOT_OFFSET, 0)
            for row in rows
            for start, size in zip(_starts(width), width.sizes)
            for i in range(min(size-1, 2))]


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


def stopper_columns(values=None):
    """Tile columns of the stopper holes: each width compartment's end tiles."""
    width, _ = compartments(values)
    return [start+j*(size-1) for start, size in zip(_starts(width), width.sizes)
            for j in range(1 if size == 1 else 2)]


def source_stopper_positions(values=None):
    """Top-wall stopper holes [C] :1463-1469, per width compartment."""
    v = values or {}
    if not v.get('add_stopper_holes', True):
        return []
    d = dimensions(v)
    return [(d.source_x-d.width/2+TILE_SIZE/2+col*TILE_SIZE,
             d.source_y+d.height/2,
             d.depth-v.get('stopper_edge_distance', 3)-c.STOPPER_HEIGHT)
            for col in stopper_columns(v)]


def _stopper_hole(wall, excess=0):
    """drawer_stopper(hole=true) [C] :1807-1837 entering -Y from Y=0.

    Flange, then the shaft with the author's two concave quarter-rounds at
    its entrance, then ``excess`` mm of flange-width hole (hole_excess).
    """
    w, r, flange = c.STOPPER_WIDTH/2, c.STOPPER_ROUNDING, c.STOPPER_FLANK_DEPTH
    depth = wall+2*EPS
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
    cutter = Solid.extrude(section, (0, 0, c.STOPPER_HEIGHT))
    cutter += Box(c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH, flange, c.STOPPER_HEIGHT,
                  align=(Align.CENTER, Align.MIN, Align.MIN))
    if excess > 0:
        cutter += Pos(0, depth, 0)*Box(c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH,
                                       excess, c.STOPPER_HEIGHT,
                                       align=(Align.CENTER, Align.MIN, Align.MIN))
    # Reflect local inward-depth +Y to the source's inward -Y.
    return cutter.mirror(Plane.XZ)


def source_stopper_cutters(values=None):
    d = dimensions(values)
    # Shaft cross-section (X,inward depth). No printed clip geometry here.
    cutter = _stopper_hole(d.wall, d.slot_thickness-d.wall if d.slot_face == 'Top' else 0)
    return [Pos(*p)*cutter for p in source_stopper_positions(values)]


def honeycomb_layouts(values=None, *, close_openings=True):
    """Through-openings, preserving :1390-1415 frames and fitting infills.

    All four wall planes are vertical in the back-wall-down print frame.
    The openings have horizontal ceiling facets between their struts,
    including clipped cells at the frame. The slot-bearing wall stays solid.
    Production (any ceiling but 'source') closes each opening whose roofed
    profile has an inscribed circle under MIN_LATTICE_OPENING_MM, as the
    container does; close_openings=False keeps them for the closure test.
    """
    from .honeycomb import HoneycombLayout, HoneycombPanelTooSmall, close_small_openings, hole_polygons
    from shapely.geometry import Polygon, box
    v = values or {}
    d = dimensions(v)
    depth = d.depth+d.wall-d.slot_thickness
    ceiling = v.get('honeycomb_ceiling', 'roofed')
    layouts = []
    for name, setting, default in (
        ('Top', 'shell_top_wall_type', 'Solid'),
        ('Bottom', 'shell_bottom_wall_type', 'Honeycomb'),
        ('Left', 'shell_side_wall_type', 'Solid'),
        ('Right', 'shell_side_wall_type', 'Solid'),
    ):
        if v.get(setting, default) != 'Honeycomb' or d.slot_face == name:
            continue
        side = name in ('Left', 'Right')
        size = (d.height if side else d.width)-2*d.inner_chamfer
        sign = -1 if name in ('Left', 'Bottom') else 1
        origin = ((d.source_x+sign*(d.width-d.wall)/2, d.source_y, d.depth-depth/2)
                  if side else
                  (d.source_x, d.source_y+sign*(d.height-d.wall)/2, d.depth-depth/2))
        plane = Plane(origin=origin, x_dir=(0, 0, 1),
                      z_dir=(-1, 0, 0) if side else (0, 1, 0))
        polygons = hole_polygons(depth, size,
                                 strut_hyp=v.get('honeycomb_strut_hyp', c.HONEYCOMB_STRUT_HYP))
        # The source clears only the straight wall interior. Fitting infills
        # extend down from the front rim before the pockets are cut.
        front_fill = (v.get('shell_side_magnet_edge_distance', 6)
                      +v.get('side_magnet_diameter', 6)+2*c.MAGNET_HOLE_SIDE_CLEARANCE+3
                      if side and v.get('add_side_magnet_holes', True) else
                      v.get('stopper_edge_distance', 3)+c.STOPPER_HEIGHT+3
                      if name == 'Top' and v.get('add_stopper_holes', True) else 0)
        length = d.inner_depth-front_fill
        if length <= 0:
            continue
        # Local X is source +Z (print up); local Y is source +X/+Y.
        # Clip in 2D BEFORE roofing, including the fitting reinforcement.
        half_width = ((d.inner_height if side else d.inner_width)/2-d.inner_chamfer)
        window = box(d.slot_thickness-origin[2], -half_width,
                     d.slot_thickness+length-origin[2], half_width)
        openings = [Polygon(p).intersection(window) for p in polygons]
        openings = [p for p in openings if not p.is_empty and p.area > 1e-10]
        if close_openings and ceiling != 'source':
            kept = close_small_openings(openings, (1, 0), ceiling=ceiling)
            # Never substitute a Solid wall for a requested Honeycomb one.
            if openings and not kept:
                raise HoneycombPanelTooSmall(
                    f'honeycomb {name.lower()} wall: every opening clips under '
                    f'{c.MIN_LATTICE_OPENING_MM:g} mm; lower honeycomb_strut_hyp '
                    'or use the Solid wall type')
            openings = kept
        if openings:
            layouts.append((plane, HoneycombLayout(openings, ceiling, name)))
    return layouts


def divider_walls(values=None):
    """Shell divider planes [C] :1576-1674 (is_shell) as (axis, source coordinate).

    Walls are 2*shell_thickness thick (:1577) and centred on tile
    boundaries: 'x' walls at the width sums from the grid's -X edge, 'y'
    walls at the height sums down from the grid top. The author's Top and
    Bottom slot faces shift 'y' walls off the boundary by the extra slot
    thickness (:1620-1624); the port keeps them on it.
    """
    v = values or {}
    width, height = compartments(v)
    nh, nv = width.count, height.count
    return ([('x', (p-nh/2)*TILE_SIZE) for p in width.positions]
            + [('y', (nv/2-p)*TILE_SIZE) for p in height.positions])


def _polygons(shape):
    if shape.is_empty:
        return []
    if shape.geom_type == 'Polygon':
        return [shape] if shape.area > 1e-10 else []
    return [p for g in shape.geoms for p in _polygons(g)]


def divider_honeycomb_layouts(values=None):
    """Per divider wall: (plane, layout) of its through-openings, or None.

    [C] :1655-1670: hex_panel(frame=shell_thickness) over the full outer
    length and the wall depth, with the front fill for the wall's own
    stopper holes ('y') or side magnets ('x'). Same plane convention as
    honeycomb_layouts (local X = print up). Openings are clipped to the
    cavity and to crossing divider walls, where the union refills them.
    """
    from .honeycomb import HoneycombLayout, HoneycombPanelTooSmall, close_small_openings, hole_polygons
    from shapely.geometry import Polygon, box
    v = values or {}
    walls = divider_walls(v)
    if v.get('shell_divider_wall_type', 'Honeycomb') != 'Honeycomb':
        return [None]*len(walls)
    d = dimensions(v)
    depth = d.depth+d.wall-d.slot_thickness
    result = []
    for index, (axis, at) in enumerate(walls):
        x_wall = axis == 'x'
        front_fill = (v.get('side_magnet_diameter', 6)+2*c.MAGNET_HOLE_SIDE_CLEARANCE+3
                      if x_wall and v.get('add_side_magnet_holes', True) else
                      v.get('stopper_edge_distance', 3)+c.STOPPER_HEIGHT+3
                      if not x_wall and v.get('add_stopper_holes', True) else 0)
        centre = d.source_y if x_wall else d.source_x
        origin = (at, centre, d.depth-depth/2) if x_wall else (centre, at, d.depth-depth/2)
        plane = Plane(origin=origin, x_dir=(0, 0, 1),
                      z_dir=(-1, 0, 0) if x_wall else (0, 1, 0))
        half = (d.inner_height if x_wall else d.inner_width)/2
        window = box(d.slot_thickness-origin[2], -half-centre,
                     d.depth-front_fill-origin[2], half-centre)
        for other, cross in walls:
            if other != axis:
                window = window.difference(box(-depth, cross-d.wall-centre,
                                               depth, cross+d.wall-centre))
        polygons = hole_polygons(depth, d.height if x_wall else d.width,
                                 strut_hyp=v.get('honeycomb_strut_hyp', c.HONEYCOMB_STRUT_HYP),
                                 frame=d.wall)
        openings = [o for p in polygons for o in _polygons(Polygon(p).intersection(window))]
        ceiling = v.get('honeycomb_ceiling', 'roofed')
        if ceiling != 'source':
            # The same sub-Ø2 closure as the shell walls (pst-t0ob3.5).
            kept = close_small_openings(openings, (1, 0), ceiling=ceiling)
            if openings and not kept:
                raise HoneycombPanelTooSmall(
                    f'honeycomb divider wall {axis}{index}: every opening clips under '
                    f'{c.MIN_LATTICE_OPENING_MM:g} mm; lower honeycomb_strut_hyp '
                    'or use the Solid divider wall type')
            openings = kept
        result.append((plane, HoneycombLayout(openings, ceiling, f'Divider {axis}{index}'))
                      if openings else None)
    return result


def source_divider_walls(values=None):
    """Divider walls with their own cuts, before the shell's feature cuts.

    [C] :1599-1673. 'x' walls carry side-magnet teardrops on both faces
    (:1646-1653); 'y' walls carry a through stopper hole per width
    compartment end tile (hole_excess=shell_thickness, :1634-1644). A
    honeycomb wall is the hex panel's depth only (back frame in the back
    wall); a solid wall spans the full depth like the author's cuboid.
    """
    v = values or {}
    d = dimensions(v)
    walls = divider_walls(v)
    if not walls:
        return []
    layouts = divider_honeycomb_layouts(v)
    honey = v.get('shell_divider_wall_type', 'Honeycomb') == 'Honeycomb'
    z0 = d.slot_thickness-d.wall if honey else 0
    outer = Pos(d.source_x, d.source_y, 0)*Solid.extrude(
        _section(d.width, d.height, d.outer_chamfer, d.slot_face), (0, 0, d.depth))
    result = []
    for (axis, at), layout in zip(walls, layouts):
        size = (2*d.wall, d.height, d.depth-z0) if axis == 'x' else (d.width, 2*d.wall, d.depth-z0)
        centre = (at, d.source_y) if axis == 'x' else (d.source_x, at)
        wall = Pos(*centre, z0)*Box(*size, align=(Align.CENTER, Align.CENTER, Align.MIN)) & outer
        if layout is not None:
            plane, hexes = layout
            wall = wall.cut(plane.location*hexes.cutter(2*d.wall+2*EPS, (1, 0)))
        for cut in _divider_feature_cutters(v, axis, at):
            wall -= cut
        result.append(wall)
    return result


def _divider_feature_cutters(v, axis, at):
    d = dimensions(v)
    if axis == 'y':
        if not v.get('add_stopper_holes', True):
            return []
        cutter = _stopper_hole(d.wall, d.wall)
        z = d.depth-v.get('stopper_edge_distance', 3)-c.STOPPER_HEIGHT
        return [Pos(x, at+d.wall, z)*cutter for x, _, _ in source_stopper_positions(v)]
    cuts = []
    for start, y, z, depth, radius in _divider_magnets(v, at):
        cutter = Solid.extrude(_teardrop(radius), (0, 0, depth))
        cuts.append(Pos(start, y, z)*Rot(0, 0, 90)*Rot(90, 0, 0)*cutter)
    return cuts


def source_divider_feature_cutters(values=None):
    """Every divider wall's stopper-hole and teardrop cutters (source frame)."""
    v = values or {}
    return [cut for axis, at in divider_walls(v) for cut in _divider_feature_cutters(v, axis, at)]


def _divider_magnets(v, at):
    """Teardrops on both faces of an 'x' wall ([C] :1646-1653), extended 2*EPS out."""
    if not v.get('add_side_magnet_holes', True):
        return []
    d = dimensions(v)
    radius = v.get('side_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
    depth = v.get('shell_side_magnet_thickness', 1)+c.MAGNET_HOLE_DEPTH_CLEARANCE+2*EPS
    z = d.depth-v.get('shell_side_magnet_edge_distance', 6)-radius
    nv = v.get('vertical_grids', 2)
    return [(start, d.source_y+(j-(nv-1)/2)*TILE_SIZE, z, depth, radius)
            for start in (at-d.wall-2*EPS, at+d.wall+2*EPS-depth) for j in range(nv)]


def honeycomb_ceiling_chords(values=None):
    """Analytic through-wall spans, independent of the 3D local-width scan."""
    return ([row for _, layout in honeycomb_layouts(values)
             for row in layout.ceiling_chords((1, 0))]
            + [row for entry in divider_honeycomb_layouts(values) if entry
               for row in entry[1].ceiling_chords((1, 0))])


def source_honeycomb_wall_cutters(values=None):
    d = dimensions(values)
    return [plane.location * layout.cutter(d.wall+2*EPS, (1, 0))
            for plane, layout in honeycomb_layouts(values)]


def source_divider_honeycomb_cutters(values=None):
    d = dimensions(values)
    return [plane.location*layout.cutter(2*d.wall+2*EPS, (1, 0))
            for plane, layout in filter(None, divider_honeycomb_layouts(values))]


def source_honeycomb_cutters(values=None):
    """Individual openings for face inventories and reference measurements."""
    return [hole for wall in source_honeycomb_wall_cutters(values)
            + source_divider_honeycomb_cutters(values) for hole in wall.solids()]


def before_bed_chamfer(values=None):
    part = source_body(values)
    holes = source_honeycomb_wall_cutters(values)
    if holes:
        part = part.cut(*holes)
    # Divider walls are the author's 'keep' children: after the wall
    # openings, before every rm_outer feature cut (:1373-1374).
    for wall in source_divider_walls(values):
        part = (part+wall).clean()
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


def honeycomb_ceiling_regions(values):
    """Only flat positive-Z opening facets in the source/print frame.

    Source mode preserves source hex ceilings; roofed mode shortens only
    over-limit flat chords. The 11.835681 mm flat-to-flat
    dimension at strut_hyp=5 is vertical, not a horizontal bridge span.
    The family includes clipped frame cells as well as full hexes. Only
    chords at most MAX_BRIDGE_MM are eligible; the production local-width
    scan alone cannot bound unsupported through-wall ceiling chords.
    Production has no sub-Ø2 openings to register: honeycomb_layouts closes
    them (pst-t0ob3.5, test_shell_lattice_openings_under_2mm_are_closed).
    """
    regions = []
    for hole in source_honeycomb_cutters(values):
        for face in hole.faces():
            normal = face.normal_at()
            size = face.bounding_box().size
            # New 45-degree roofs are audited, never put in this waiver.
            if normal.Z > .999 and max(size.X, size.Y) <= c.MAX_BRIDGE_MM:
                regions.append(AUTHOR_TO_MODEL *
                               (Pos(*tuple(-normal*.0005))*Solid.extrude(face, normal*.001)))
    return regions


def published_ceiling_regions(values=None):
    """Exact thin regions for source magnet, stopper and honeycomb ceilings.

    [C] :1438/:1444 (teardrop cap_h=r+.2) and :1468/:1816-1821
    (stopper-hole roofs). Tests independently pin their reference heights,
    bridge spans and membership. Honeycomb regions are the positive-Z
    opening facets returned by honeycomb_ceiling_regions; their vertical
    strut walls are not excluded.
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
    for axis, at in divider_walls(v):
        if axis == 'y' and v.get('add_stopper_holes', True):
            z = d.depth-v.get('stopper_edge_distance', 3)-c.STOPPER_HEIGHT
            for x, _, _ in source_stopper_positions(v):
                regions.append(Pos(x, at-d.wall-EPS, z+c.STOPPER_HEIGHT)*Box(
                    c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH, 2*d.wall+2*EPS, .001,
                    align=(Align.CENTER, Align.MIN, Align.CENTER)))
        for start, y, z, depth, radius in (_divider_magnets(v, at) if axis == 'x' else ()):
            cap = radius+.2
            regions.append(Pos(start, y, z+cap)*Box(depth, 2*(radius*sqrt(2)-cap), .001,
                                                  align=(Align.MIN, Align.CENTER, Align.CENTER)))
    return [AUTHOR_TO_MODEL*r for r in regions]+honeycomb_ceiling_regions(v)
