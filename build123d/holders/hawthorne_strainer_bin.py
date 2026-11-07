# SPDX-License-Identifier: MIT
"""OXO SteeL strainer stack bin; print Gridfinity feet down, +Z up, PLA/PCTG.

Worst load is lateral pressure from the stack into the continuous XY walls;
weight compresses the floor. No separate body joint, mount or stacking lip.
The Gridfinity foot profile (including its 0.8 mm bed chamfer) is functional.
[U] Strainer defaults are the mayor's photo estimates (2026-11-06), +/-3 mm:
93 mm coil, 67 mm centre-to-handle TIP, 55 mm centre-to-ear TIP. Physical
measurements/test print remain necessary; handle 67 is deliberately rounded down.
"""
from math import cos, radians, sin
import sys

from build123d import Face, Pos, RectangleRounded, Wire, chamfer, extrude, fillet
from shapely import affinity
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from gridfinity import bin as gf
from holders.gridfinity_capture_bin import POCKET_BREAK, outer_polygon
from holders.registry import ModelSpec, Param, Preset, register

RIM_RADIUS = 1.0
SCOOP_RADIUS = 5.0
# Finer than the capture bin's 0.1 mm ring: the scoop intersects this
# outline, and coarser facets can leave sub-0.01 mm edges at that crossing.
POCKET_SIMPLIFY_MM = .04
FIT_ERROR = 'strainer does not fit this bin depth'


def stadium(reach, width, angle):
    """Round-ended arm from C: reach is the tip, not the arc centre."""
    radius = width/2
    tip_centre = reach-radius
    return LineString([(0, 0), (tip_centre*sin(angle), tip_centre*cos(angle))]).buffer(
        radius, quad_segs=32)


def dimensions(values=None):
    v = SPEC.resolve_values(values)
    envelope = unary_union([
        Point(0, 0).buffer(v['coil_diameter']/2, quad_segs=64),
        stadium(v['handle_reach'], v['handle_width'], radians(180)),
        stadium(v['ear_reach'], v['ear_width'], radians(v['ear_angle'])),
        stadium(v['ear_reach'], v['ear_width'], -radians(v['ear_angle'])),
    ])
    offset = envelope.buffer(v['clearance'], quad_segs=8)
    # Round the re-entrant disc/tab junctions by removing stock. A closing
    # operation preserves the clearance envelope and its outer extents.
    rounded = offset.buffer(RIM_RADIUS, quad_segs=16).buffer(-RIM_RADIUS, quad_segs=16)
    tolerance = POCKET_SIMPLIFY_MM
    while True:
        # Mitre the tiny compensation offset: bevel joins would introduce
        # sub-0.02 mm edges that cannot accept the pocket-mouth break.
        pocket = rounded.simplify(tolerance, preserve_topology=True).buffer(tolerance, join_style=2)
        if len(pocket.exterior.coords) <= 257:
            break
        tolerance *= 2
    # Centre the front/back slack, keeping C on X=0. Check the full rounded
    # outer footprint too: long ears can violate X or a rounded bin corner.
    centre_y = -(pocket.bounds[1]+pocket.bounds[3])/2
    envelope, offset, pocket = [affinity.translate(p, yoff=centre_y)
                                for p in (envelope, offset, pocket)]
    outer = outer_polygon(3, v['depth_units'])
    if not outer.covers(pocket) or outer.boundary.distance(pocket) < v['wall_min']-1e-7:
        raise ValueError(FIT_ERROR)
    floor = gf.BASE_HEIGHT+v['floor_thickness']
    scoop_height = min(v['scoop_height'], v['height_mm']-floor-3)
    return v, floor, centre_y, envelope, offset, pocket, scoop_height


def audit_exclusions(values=None):
    v = SPEC.resolve_values(values)
    # Reuse only the library's exact inter-foot bridge family, as in the
    # capture bin; this does not exclude any pocket or scoop surface.
    return gf.underside_exclusions(3, v['depth_units'])


def _cut(polygon, bottom, top):
    face = Face(Wire.make_polygon([(x, y, bottom) for x, y in polygon.exterior.coords], close=True))
    return extrude(face, amount=top-bottom+1, dir=(0, 0, 1))


def build(values=None):
    v, floor, centre_y, _, _, pocket, scoop_height = dimensions(values)
    top = v['height_mm']
    part = gf.base(3, v['depth_units'])
    part += extrude(Pos(0, 0, gf.BASE_HEIGHT)*gf.outline(3, v['depth_units']),
                    amount=top-gf.BASE_HEIGHT)
    part = fillet([e for e in part.edges() if abs(e.bounding_box().min.Z-top) < 1e-6], RIM_RADIUS)
    part -= _cut(pocket, floor, top)
    if scoop_height:
        front = -(gf.PITCH*v['depth_units']-.5)/2
        # Carry the scoop into the disc opening: its rounded back end is
        # wholly inside the coil pocket, avoiding thin shoulder remnants.
        back = centre_y+v['scoop_width']/2
        scoop = Pos(0, (front-10+back)/2, floor+scoop_height)*RectangleRounded(
            v['scoop_width'], back-front+10, SCOOP_RADIUS)
        part -= extrude(scoop, amount=top-floor-scoop_height+1)
    # Round convex vertical junctions where the disc, tabs and scoop meet.
    # Doing this before the rim break avoids tiny three-way chamfer caps.
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    corners = []
    outer = outer_polygon(3, v['depth_units'])
    for edge, faces in adjacency.items():
        bb = edge.bounding_box()
        point = edge.position_at(.5)
        if outer.boundary.distance(Point(point.X, point.Y)) < .001:
            continue
        if bb.min.Z < floor-1e-6 or bb.size.Z < 1 or max(bb.size.X, bb.size.Y) > 1e-6:
            continue
        p = edge.position_at(.5)
        n1, n2 = [face.normal_at(p) for face in faces]
        if n1.dot(n2) < 2**-.5 and not part.is_inside(p+(n1-n2)*.01):
            corners.append(edge)
    if corners:
        try:
            part = fillet(corners, RIM_RADIUS)
        except ValueError:
            # Narrow scoops can intersect a short simplified pocket facet:
            # there is no room for R1, but a 45-degree break still removes
            # the exposed corner without changing the floor footprint.
            part = chamfer(corners, POCKET_BREAK)
    # Break upward-facing pocket and scoop rims; concave floor seams stay
    # sharp to preserve the full footprint down to the declared pocket floor.
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    edges = []
    for edge, faces in adjacency.items():
        if edge.bounding_box().max.Z <= floor+1e-6:
            continue
        p = edge.position_at(.5)
        n1, n2 = [face.normal_at(p) for face in faces]
        if n1.dot(n2) < 2**-.5-1e-6 and not part.is_inside(p+(n1-n2)*.01):
            edges.append(edge)
    for length in (POCKET_BREAK, POCKET_BREAK/2, .05):
        try:
            part = chamfer(edges, length)
            break
        except ValueError as error:
            last_error = error
    else:
        print(f'[hawthorne-strainer-bin] pocket break skipped: {last_error}', file=sys.stderr)
    return part


SPEC = register(ModelSpec(
    name='hawthorne_strainer_bin', title='Hawthorne strainer bin', category_id='storage',
    description='A 3-cell-wide Gridfinity bin for a flat stack of OXO SteeL cocktail strainers. '
                '68 mm total height for the bar drawer, with a front finger scoop. Print feet down.',
    build=build,
    params=(
        Param('depth_units', 'integer', 3, min=3, max=4, step=1, filename=True),
        Param('coil_diameter', 'number', 93, min=80, max=110, step=1, unit='mm'),
        Param('handle_width', 'number', 30, min=20, max=40, step=1, unit='mm'),
        Param('handle_reach', 'number', 67, min=50, max=85, step=1, unit='mm', description='Disc centre to rounded handle tip.'),
        Param('ear_reach', 'number', 55, min=45, max=65, step=1, unit='mm', description='Disc centre to rounded ear tip.'),
        Param('ear_width', 'number', 16, min=10, max=24, step=1, unit='mm'),
        Param('ear_angle', 'number', 55, min=30, max=80, step=1, unit='deg', description='Angle from +Y (back); handle points toward -Y (front).'),
        Param('clearance', 'number', 2, min=1, max=4, step=.1, unit='mm'),
        Param('height_mm', 'number', 68, min=35, max=90, step=1, unit='mm', description='Total height including the Gridfinity feet.'),
        Param('floor_thickness', 'number', 2, min=1.2, max=4, step=.1, unit='mm'),
        Param('wall_min', 'number', 1.6, min=1.2, max=3, step=.1, unit='mm'),
        Param('scoop_height', 'number', 22, min=0, max=50, step=1, unit='mm', description='Height above pocket floor; 0 disables scoop. Clamped 3 mm below the rim.'),
        Param('scoop_width', 'number', 40, min=20, max=70, step=1, unit='mm'),
    ),
    presets=(Preset('default', 'OXO SteeL — bar drawer', {}),),
))
