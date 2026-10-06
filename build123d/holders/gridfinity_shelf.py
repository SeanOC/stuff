# SPDX-License-Identifier: CC-BY-SA-4.0
"""mitufy's openConnect Gridfinity shelf, ported from the published generator.

[C] assets/openConnect-gridfinity-shelf/openconnect_gridfinity_shelf_online.scad
:329-371,1213-1340. Model frame: back Y=0, shelf extends +Y, deck normal +Z.
Print wedge-down in PLA/PCTG using print_frame(values). Worst-case load is
bins pulling the shelf away from the wall; the continuous wedge is the web.
The author's default backing is 0.85 mm; sturdy-back provides 2.4 mm.
"""
from dataclasses import replace
from math import atan, cos, degrees, floor, radians

from build123d import Align, Axis, Box, Cylinder, Face, Part, Pos, Rot, Solid, Vector, Wire, fillet
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
from gridfinity import baseplate as gf
from holders.registry import ModelSpec, Param, Preset, register
from openconnect.constants import EPS, TILE_SIZE
from openconnect.grid import fixtures, layout, row_strip

MOUNT = 'openconnect-slot-shallow'
LOCKS = {'All': 'all', 'Staggered': 'staggered', 'Corners': 'corners',
         'Top Corners': 'top-corners', 'None': 'none'}


def dimensions(values=None):
    v = SPEC.resolve_values(values)
    magnets = (v['baseplate_style'] != 'Default' and v['magnet_diameter'] > 0
               and v['magnet_thickness'] > 0)
    extra = max(2.4, v['magnet_thickness']) if magnets else 2.4
    deck = extra+gf.PROFILE_HEIGHT+(gf.CLEARANCE if magnets else 0)
    tilt = max(0, TILE_SIZE-deck)
    width = v['gridfinity_width_grids']*gf.PITCH+2*v['shelf_side_rim']
    depth = v['shelf_back_offset']+0.7+v['gridfinity_depth_grids']*gf.PITCH+v['shelf_front_rim']
    nh = floor(width/TILE_SIZE)
    dx = {'Center': 0, 'Left': 1, 'Right': -1}[v['slot_horizontal_alignment']]*(width-nh*TILE_SIZE)/2
    dx += v['slot_horizontal_offset']
    dz = v['slot_vertical_offset']
    if abs(dx) > (width-nh*TILE_SIZE)/2+1e-7:
        raise ValueError('slot_horizontal offset leaves the back face')
    if abs(dz) > 1e-7:
        raise ValueError('slot_vertical offset leaves the back face')
    return v, width, depth, extra, deck, tilt, magnets, nh, dx, dz


def print_bottom_angle(values=None):
    _, _, depth, _, _, tilt, *_ = dimensions(values)
    return degrees(atan(tilt/depth))


def print_frame(values):
    # The wedge back-bottom is the origin: rotating about X puts its entire
    # underside at Z=0. This is the author's xrot(-angle) up(tilt), with the
    # translation already included in our model frame.
    return Rot(-print_bottom_angle(values), 0, 0)


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    v, _, _, _, _, _, _, nh, dx, dz = dimensions(values)
    points = [replace(p, x=p.x+dx, z=p.z+TILE_SIZE/2+dz) for p in layout(
        nh, 1, lock=LOCKS[v['slot_lock_distribution']], slide='up',
        entryramp_flip=v['slot_entryramp_flip'])]
    fx = fixtures(points, edge_feature='top', excess_thickness=EPS, excess_length=4)
    fx.backing_envelope = backing_envelope(values)
    return fx


def _footprint(width, depth, bottom, height):
    body = Pos(0, 0, bottom)*Box(width, depth, height,
                               align=(Align.CENTER, Align.MIN, Align.MIN))
    return fillet([e for e in body.edges().filter_by(Axis.Z)
                   if e.center().Y > depth/2], gf.TOP_CORNER_RADIUS)


def screw_positions(values):
    v, width, depth, extra, _, tilt, *_ = dimensions(values)
    if not v['enable_screw_connections']:
        return []
    radius = v['connection_screw_diameter']/2
    z = tilt+extra-radius-0.8
    positions = []
    for j in range(v['gridfinity_depth_grids']):
        y = v['shelf_back_offset']+0.7+(j+0.5)*gf.PITCH
        wall = (z-tilt*y/depth)*cos(radians(print_bottom_angle(v)))-radius
        if wall >= 0.8:
            positions.extend([(x, y, z) for x in (-width/2, width/2)])
    return positions


def uncut_wedge(values=None):
    """Uncut body: the underside is z = tilt*y/depth in model coordinates."""
    _, width, depth, _, deck, tilt, *_ = dimensions(values)
    section = Face(Wire.make_polygon([(-width/2, 0, 0), (-width/2, depth, tilt),
                                      (-width/2, depth, tilt+deck),
                                      (-width/2, 0, tilt+deck)], close=True))
    return Solid.extrude(section, (width, 0, 0)) & _footprint(width, depth, 0, tilt+deck)


def build(values=None):
    v, width, depth, extra, deck, tilt, magnets, nh, dx, dz = dimensions(values)
    part = uncut_wedge(v)
    lip = v['shelf_rim_lip_height']
    side = v['shelf_side_rim'] if lip else 0
    front = v['shelf_front_rim'] if lip else 0
    if lip and (side or front):
        rim = _footprint(width, depth, tilt+deck, lip)
        inner_width, inner_depth = width-2*side, depth-front-v['shelf_back_offset']-0.7
        pocket = (Pos(0, v['shelf_back_offset']+0.7, tilt+deck-EPS)*
                  Box(inner_width, inner_depth, lip+2*EPS, align=(Align.CENTER, Align.MIN, Align.MIN)))
        if front:
            edges = pocket.edges().filter_by(Axis.Z)
            pocket = fillet([e for e in edges if side or e.center().Y > depth/2], gf.TOP_CORNER_RADIUS)
        part += rim-pocket
    origin = Pos(0, v['shelf_back_offset']+0.7+v['gridfinity_depth_grids']*gf.PITCH/2, tilt+extra)
    socket = gf.socket_cutout(v['gridfinity_socket_clearance'], magnets)
    for x, y in gf.cell_positions(v['gridfinity_width_grids'], v['gridfinity_depth_grids']):
        part -= origin*Pos(x, y)*socket
    mode = {'Default': 'None', 'Magnet - All': 'All', 'Magnet - Corners Only': 'Corners Only'}[v['baseplate_style']]
    part -= origin*gf.window_cutouts(v['gridfinity_width_grids'], v['gridfinity_depth_grids'],
                                    extra+tilt, magnets=magnets, diameter=v['magnet_diameter'], mode=mode)
    if magnets:
        for x, y in gf.magnet_positions(v['gridfinity_width_grids'], v['gridfinity_depth_grids'], mode, v['magnet_diameter']):
            part -= origin*Pos(x, y)*Cylinder(v['magnet_diameter']/2, v['magnet_thickness'],
                                             align=(Align.CENTER, Align.CENTER, Align.MAX))
    for x, y, z in screw_positions(v):
        part -= Pos(x, y, z)*Rot(0, 90, 0)*Cylinder(v['connection_screw_diameter']/2, gf.PITCH/2)
    for cutter in mount_fixtures(MOUNT, v).cutters:
        part -= cutter
    part -= Pos(dx, 0, TILE_SIZE/2+dz)*row_strip(nh, 4)
    return chamfer_bed(part, v)


def backing_envelope(values=None):
    """Rev 10 E1b: uncut wedge with only its underside perimeter chamfered."""
    return chamfer_bed(uncut_wedge(values), values)


def chamfer_bed(part, values):
    _, _, depth, _, _, tilt, *_ = dimensions(values)
    # Rev 9 E1: finish every loop of the actual underside, including window
    # and on-ramp edges, only after all cuts. Other author edges stay intact.
    bed_normal = Vector(0, tilt/depth, -1).normalized()
    bed_faces = [f for f in part.faces() if f.normal_at().dot(bed_normal) > 1-1e-7]
    if len(bed_faces) != 1:
        raise ValueError("shelf underside must be one connected bed face")
    bed = bed_faces[0]
    # Use OCCT's angle-based operation: build123d's angle argument converts
    # to two linear distances, which is not 45 degrees on tilted side faces.
    bevel = BRepFilletAPI_MakeChamfer(part.wrapped)
    for edge in bed.edges():
        # OCCT's fitted curved bevels overshoot the nominal slope by ~0.0012
        # degrees. A 0.01-degree inward margin keeps the actual surface below
        # 45 degrees from vertical without weakening the production audit.
        bevel.AddDA(0.3, radians(45.01), edge.wrapped, bed.wrapped)
    finished = Part(bevel.Shape())
    if not finished.is_valid:
        raise ValueError("shelf underside chamfer produced invalid geometry")
    return finished


SPEC = register(ModelSpec(
    name='openconnect_gridfinity_shelf', title='openConnect Gridfinity shelf',
    category_id='multiboard', build=build, mounts=(MOUNT,), print_frame=print_frame,
    description="mitufy's Gridfinity shelf (CC BY-SA 4.0). Wedge-down print; sturdy-back provides 2.4 mm slot backing.",
    params=(
        Param('baseplate_style', 'enum', 'Default', choices=('Default', 'Magnet - All', 'Magnet - Corners Only'), filename=True),
        Param('gridfinity_width_grids', 'integer', 2, min=1, max=6, step=1, filename=True),
        Param('gridfinity_depth_grids', 'integer', 2, min=1, max=4, step=1, filename=True),
        Param('enable_screw_connections', 'boolean', False),
        Param('connection_screw_diameter', 'number', 3.3, min=2, max=5, step=0.1),
        Param('magnet_diameter', 'number', 6.4, min=0, max=8, step=0.1),
        Param('magnet_thickness', 'number', 2.4, min=0, max=3, step=0.1),
        Param('shelf_back_offset', 'number', 0, min=0, max=20, step=0.1),
        Param('shelf_side_rim', 'number', 0, min=0, max=10, step=0.1),
        Param('shelf_front_rim', 'number', 0, min=0, max=10, step=0.1),
        Param('shelf_rim_lip_height', 'number', 0, min=0, max=5, step=0.1),
        Param('slot_lock_distribution', 'enum', 'Top Corners', choices=tuple(LOCKS)),
        Param('slot_entryramp_flip', 'boolean', False),
        Param('slot_horizontal_alignment', 'enum', 'Center', choices=('Center', 'Left', 'Right')),
        Param('gridfinity_socket_clearance', 'number', 0, min=0, max=0.2, step=0.01),
        Param('slot_horizontal_offset', 'number', 0, min=-14, max=14, step=0.1),
        Param('slot_vertical_offset', 'number', 0, min=-10, max=10, step=0.1),
    ),
    presets=(Preset('default', '2 × 2 shelf', {}),
             Preset('magnets', '2 × 2 with magnets', {'baseplate_style': 'Magnet - All'}),
             Preset('wide', '4 × 2 shelf', {'gridfinity_width_grids': 4}),
             Preset('sturdy-back', '2.4 mm slot backing', {'shelf_back_offset': 1.55})),
))
