"""Spool cradle v2.1: axis X along the board, +Y outward, printed on Z=0.

Worst case: 30 N downward at the front flange rim. Closed triangular webs
return to the plate through a bed chord; a vertical front panel ties them.
PETG/PCTG only (operator-approved PLA exclusion for sustained load/heat).
The 2.4 mm webs/panel print as perimeters; the plate uses three walls and
15% infill. Only library channel pockets may need supports. Inboard rail
caps keep the analytic flange contact; 45-degree underside ramps carry
the caps and outboard lead-in guides in the standing pose.
Fixed two-channel mount and 25 mm board pitch are operator-approved.
"""
from __future__ import annotations

import math
from build123d import Align, Axis, Box, BuildSketch, Cone, Edge, Face, Plane, Polygon, Pos, Rot, Solid, Vector, Wire, extrude
from holders.registry import ModelSpec, MountFixtures, Param, Preset, register
from multibuild.constants import PITCH
from multibuild.multiconnect import POCKET_DEPTH, channel_cutter

MOUNT = 'multibuild-multiconnect-channel'
WEB = 2.4
APEX_HEIGHT = 18.0
JOINT_RADIUS = 1.0
BED_CHAMFER = 0.4
CHORD = 6.0
CADENCE = 75.0

PARAMS = tuple(Param(name, 'number', default, min=lo, max=hi, step=step,
                    unit='deg' if name == 'cradle_angle' else 'mm', label=label)
    for name, default, lo, hi, step, label in (
        ('spool_diameter', 200, 190, 205, 0.5, 'Spool diameter'),
        ('spool_width', 66, 50, 70, 0.5, 'Spool width'),
        ('flange_height', 8, 4, 15, 0.5, 'Flange above winding'),
        ('flange_rim_width', 3, 1.5, 6, 0.5, 'Flange rim width'),
        ('cradle_angle', 40, 25, 45, 1, 'Contact tangent angle from vertical'),
        ('saddle_clearance', 0.5, 0.25, 1.5, 0.25, 'Saddle radial clearance'),
        ('lip_height', 5, 0, 15, 0.5, 'Front rise above contact'),
        ('plate_width', 70, 68, 70, 0.5, 'Mount plate width'),
        ('plate_thickness', 7, 6.6, 9, 0.1, 'Mount plate thickness'),
        ('wall_clearance', 3, 3, 6, 0.5, 'Spool clearance from plate'),
        ('rail_width', 10, 6, 14, 0.5, 'Saddle rail width, inboard'),
        ('guide_height', 15, 12, 30, 1, 'Guide height above rail'),
        ('guide_gap', 0.5, 0.5, 2, 0.25, 'Half-gap to the neighbouring holder'),
    ))


def dimensions(values=None):
    p = SPEC.resolve_values(values)
    if not all(math.isfinite(v) for v in p.values()):
        raise ValueError('parameters must be finite')
    r = p['spool_diameter']/2
    a = math.radians(p['cradle_angle'])
    cy = p['plate_thickness'] + p['wall_clearance'] + r
    rs = r+p['saddle_clearance']
    cz = APEX_HEIGHT+rs
    dy = rs*math.cos(a)
    contact_z = cz-rs*math.sin(a)
    rear, front = cy-dy, cy+dy
    # A short landing keeps the panel's R1 blend off the circular contact
    # when lip_height=0; the lip rise itself remains exactly the input.
    end = front+max(JOINT_RADIUS+0.5, p['lip_height']*math.tan(a))
    root_h = contact_z+(rear-p['plate_thickness'])/math.tan(a)
    length = math.ceil(root_h/PITCH)*PITCH
    backing = p['plate_thickness']-POCKET_DEPTH
    ramps = tuple(PITCH/2+i*PITCH for i in range(int(length/PITCH)-1))
    rows = tuple(z+PITCH/2 for z in ramps)
    p.update(radius=r, saddle_radius=rs, center_y=cy, center_z=cz,
             rear_y=rear, front_y=front, contact_z=contact_z, end_y=end,
             plate_height=length+backing, root_height=root_h,
             channel_length=length, onramps=ramps, seat_rows=rows,
             panel_height=contact_z+p['lip_height'],
             rail_inner=p['spool_width']/2-WEB,
             root_inner=min(p['spool_width'], p['plate_width']-4)/2-WEB,
             winding_radius=r-p['flange_height'])
    p.update(cap_inner=p['spool_width']/2-p['rail_width'],
             cap_reach=p['rail_width']-WEB,
             guide_outer=CADENCE/2-p['guide_gap'],
             guide_reach=CADENCE/2-p['guide_gap']-p['spool_width']/2,
             exposed_rim=2*r*math.sin(a)-p['lip_height']-p['guide_height'])
    p['guide_enabled'] = p['guide_reach'] >= 1.6
    return p


def saddle_curtain(p, x0, x1, dz0=0, dz1=0, floor=-100, radial_depth=0,
                   end_extension=0):
    """Solid below the exact saddle, translated vertically across X.

    Oblique extrusion keeps XZ ramp sections at 45 degrees while retaining
    the circular YZ profile. A rotating pipe would change those sections.
    The tangent extension carries the aids all the way to the front lip.
    """
    rear, front, end = p['rear_y'], p['front_y'], p['end_y']
    rs = p['saddle_radius']+radial_depth
    z = p['center_z']-math.sqrt(rs**2-(rear-p['center_y'])**2)+dz0
    tip = p['panel_height']+z-p['contact_z']
    a, b = (x0, rear, z), (x0, front, z)
    c = (x0, end, tip)
    tail = [(x0, end+end_extension, tip)] if end_extension else []
    points = [c, *tail, (x0, end+end_extension, floor), (x0, rear, floor), a]
    wire = Wire([Edge.make_three_point_arc(a, (x0, p['center_y'], APEX_HEIGHT-radial_depth+dz0), b),
                 Edge.make_line(b, c),
                 *(Edge.make_line(u, v) for u, v in zip(points, points[1:]))])
    return Solid.extrude(Face(wire), (x1-x0, 0, dz1-dz0))


def vertical_gusset(x, y, sx, sy):
    """R1 concave vertical blend, bounded by two tangent straight faces."""
    r = JOINT_RADIUS
    corner = (x, y, 0)
    a, b = (x+sx*r, y, 0), (x, y+sy*r, 0)
    mid = (x+sx*r*(1-1/math.sqrt(2)), y+sy*r*(1-1/math.sqrt(2)), 0)
    return Solid.extrude(Face(Wire([Edge.make_line(corner, a),
        Edge.make_three_point_arc(a, mid, b), Edge.make_line(b, corner)])), (0, 0, 400))


def placement_aids(p):
    """Right-hand cap and guide; the left side is its mirror.

    Both ramps overlap the existing web by WEB. Preserve the truss voids
    when a ramp reaches below an opening roof at an extreme parameter set.
    """
    xi, xw = p['rail_inner'], p['spool_width']/2
    cap = saddle_curtain(p, p['cap_inner'], xw, .01, .01)
    cap -= saddle_curtain(p, p['cap_inner'], xw, 0, -p['rail_width'], floor=-1000, radial_depth=WEB)
    # An explicit vertical R1 gusset avoids OCCT's failed rolling fillet at
    # the short cap/panel junction. Its underside continues the 45° ramp.
    inner = p['cap_inner']
    blend = vertical_gusset(inner, p['end_y'], -1, -1)
    blend &= saddle_curtain(p, inner-JOINT_RADIUS, inner, .01, .01)
    blend -= saddle_curtain(p, inner-JOINT_RADIUS, inner, JOINT_RADIUS, 0,
                            floor=-1000, radial_depth=WEB)
    cap = cap.fuse(blend)
    if p['guide_enabled']:
        xo, reach = p['guide_outer'], p['guide_reach']
        foot = xw+p['saddle_clearance']
        # The below-saddle root joins the ramp to a full wall of the web;
        # the lead-in starts outboard of the flange by saddle_clearance.
        root = saddle_curtain(p, xi, foot, .01, .01)
        root -= saddle_curtain(p, xi, foot, -reach-WEB, foot-xw-reach, floor=-1000)
        guide = saddle_curtain(p, foot, xo, 0, p['guide_height'])
        guide -= saddle_curtain(p, foot, xo, foot-xw-reach, 0, floor=-1000)
        # Trim the sharp crest by 0.4 mm along its upright outer edge.
        guide &= saddle_curtain(p, foot, xo, p['guide_height']-0.4,
                                p['guide_height']-0.4)
        blend = vertical_gusset(xw, p['end_y'], 1, 1)
        blend &= saddle_curtain(p, xw, xw+JOINT_RADIUS,
                                end_extension=JOINT_RADIUS)
        blend -= saddle_curtain(p, xw, xw+JOINT_RADIUS, -reach, -reach+JOINT_RADIUS,
                                floor=-1000, end_extension=JOINT_RADIUS)
        cap = cap.fuse(root, guide, blend).clean()
    for triangle in truss_openings(p):
        with BuildSketch(Plane.YZ) as opening:
            Polygon(*triangle, align=None)
        cap -= extrude(opening.sketch, amount=CADENCE, both=True)
    return cap.clean()


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    p = dimensions(values)
    channel = channel_cutter(p['channel_length'], onramps=p['onramps'],
                             seats=(p['seat_rows'][0], p['seat_rows'][-1]))
    return MountFixtures(
        cutters=[Pos(x, 0, 0)*channel for x in (-PITCH/2, PITCH/2)],
        seat_locs=[Pos(x, POCKET_DEPTH, z)*Rot(90, 0, 0)
                   for x in (-PITCH/2, PITCH/2) for z in p['seat_rows']],
        onramp_locs=[Pos(x, POCKET_DEPTH, z)*Rot(90, 0, 0)
                     for x in (-PITCH/2, PITCH/2) for z in p['onramps']],
        entry_axis=(0, 0, 1), face_normal=(0, -1, 0),
    )


def truss_openings(p):
    """45-degree triangular voids leave a continuous bottom return chord.

    Each apex stays CHORD below the saddle; the inclined upper members
    close into the bed chord. All opening ceilings rise at 45 degrees.
    """
    result = []
    for fraction in (.25, .5, .75):
        y = p['plate_thickness']+(p['end_y']-p['plate_thickness'])*fraction
        surface = p['center_z']-math.sqrt(p['saddle_radius']**2-(y-p['center_y'])**2)
        height = min(surface-2*CHORD, (p['end_y']-p['plate_thickness'])/8-CHORD)
        result.append(((y-height, CHORD), (y+height, CHORD), (y, CHORD+height)))
    return result


def holder(**values):
    p = dimensions(values)
    t, cy, end = p['plate_thickness'], p['center_y'], p['end_y']
    start = t-WEB
    with BuildSketch(Plane.YZ) as profile:
        Polygon((start, 0), (end+WEB, 0),
                (end+WEB, p['panel_height']), (end, p['panel_height']),
                (p['front_y'], p['contact_z']), (p['rear_y'], p['contact_z']),
                (t, p['root_height']), (start, p['root_height']), align=None)
    blank = extrude(profile.sketch, amount=p['spool_width'], both=True)
    # Exact cylinder subtraction produces an analytic circular saddle.
    from build123d import Cylinder
    saddle = Pos(0, cy, p['center_z'])*Rot(0, 90, 0)*Cylinder(
        p['saddle_radius'], 2*p['spool_width']+10)
    blank -= saddle
    for triangle in truss_openings(p):
        with BuildSketch(Plane.YZ) as opening:
            Polygon(*triangle, align=None)
        blank -= extrude(opening.sketch, amount=p['spool_width']+1, both=True)
    ri, xi = p['root_inner'], p['rail_inner']
    # Keep the lateral root flare at <=1:2 and at least one wall long.
    # A fixed 12 mm run leaves a thin tip where the diagonal transition
    # meets the saddle at wide-spool/narrow-plate parameter corners.
    transition_length = max(WEB, 2*abs(xi-ri))
    with BuildSketch(Plane.XY) as footprint:
        Polygon((ri, start), (ri+WEB, start), (ri+WEB, t),
                (xi+WEB, t+transition_length), (xi+WEB, end+WEB), (xi, end+WEB),
                (xi, t+transition_length), (ri, t), align=None)
    rail = blank & extrude(footprint.sketch, amount=p['plate_height']+100)
    plate = Box(p['plate_width'], t, p['plate_height'],
                align=(Align.CENTER, Align.MIN, Align.MIN))
    panel = Pos(0, end, 0)*Box(p['spool_width'], WEB, p['panel_height'],
                align=(Align.CENTER, Align.MIN, Align.MIN))
    aids = placement_aids(p)
    part = plate.fuse(rail, rail.mirror(Plane.YZ), panel,
                      aids, aids.mirror(Plane.YZ), tol=1e-6).clean()
    foot = p['spool_width']/2+p['saddle_clearance']
    top_clip = Pos(0, p['rear_y'], 0)*Box(2*foot, end-p['rear_y'], 400,
        align=(Align.CENTER, Align.MIN, Align.MIN))
    top_clip -= saddle_curtain(p, -foot, foot)
    part = (part-top_clip).clean()
    joints = [e for e in part.edges().filter_by(Axis.Z)
              if (abs(e.center().Y-t) < 1e-6 and abs(abs(e.center().X)-ri) < 1e-6)
              or (abs(e.center().Y-end) < 1e-6 and abs(abs(e.center().X)-xi) < 1e-6)]
    part = part.fillet(JOINT_RADIUS, joints)
    if p['guide_enabled']:
        guide_ends = [e for e in part.edges().filter_by(Axis.Z)
                      if abs(abs(e.center().X)-p['guide_outer']) < 1e-6]
        try:
            part = part.fillet(JOINT_RADIUS, guide_ends)
        except ValueError:
            # Narrow endpoint guides cannot accommodate the R1 rolling
            # blend through the crest; retain a chamfered vertical corner.
            part = part.chamfer(0.4, None, guide_ends)
    # Ease exposed vertical edges. Functional circular rim-contact edges and
    # library mount geometry remain exact. No downward-facing fillets.
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    verticals = [e for e in part.edges().filter_by(Axis.Z)
                 if not (abs(e.center().Y-end) < 1e-6 and any(
                     abs(abs(e.center().X)-x) < 1e-6
                     for x in (p['cap_inner'], p['spool_width']/2)))
                 if len(adjacency[e]) == 2 and
                 adjacency[e][0].normal_at(e.center()).dot(
                     adjacency[e][1].normal_at(e.center())) < (
                         .01 if abs(e.center().X) > p['spool_width']/2+1e-6 else .99)]
    base_verticals = [e for e in verticals if abs(e.center().Y-p['rear_y']) > 1e-6]
    rear_datums = [e.center() for e in verticals if abs(e.center().Y-p['rear_y']) <= 1e-6]
    part = part.chamfer(0.4, None, base_verticals)
    rear_edges = [e for e in part.edges().filter_by(Axis.Z)
                  if any(abs(e.center().X-c.X) < 1e-6 and abs(e.center().Y-c.Y) < 1e-6
                         for c in rear_datums)]
    part = part.chamfer(min(0.4, p['saddle_clearance']/2), None, rear_edges)
    # Loft the rim relief as one mitred triangular cutter. This preserves
    # the original void through the 1.6 mm web core and carries its 0.4 mm
    # relief through any cap/ramp material outside the web faces.
    rim_cuts = []
    for triangle in truss_openings(p):
        y, z = triangle[2]
        half = (triangle[1][0]-triangle[0][0])/2
        expanded = ((y-half-0.4*(1+math.sqrt(2)), CHORD-0.4),
                    (y+half+0.4*(1+math.sqrt(2)), CHORD-0.4),
                    (y, z+0.4*math.sqrt(2)))
        wires = []
        for x, points in ((p['cap_inner']-2, expanded), (xi, expanded),
                          (xi+0.4, triangle), (xi+WEB-0.4, triangle),
                          (xi+WEB, expanded), (CADENCE/2+1, expanded)):
            vertices = [(x, yy, zz) for yy, zz in points]
            wires.append(Wire.make_polygon([*vertices, vertices[0]]))
        cutter = Solid.make_loft(wires, ruled=True)
        rim_cuts.extend((cutter, cutter.mirror(Plane.YZ)))
    part = part.cut(*rim_cuts).clean()
    top = part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1]
    part = part.chamfer(0.4, None, top.edges())
    panel_rims = [e for e in part.edges() if e.bounding_box().size.Z < 1e-6
                  and abs(e.center().Z-p['panel_height']) < 1e-6
                  and ((e.center().Y > end+1e-6 and e.geom_type.name == 'LINE') or
                       (e.length > 10 and abs(e.center().X) < p['cap_inner']-1))]
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    panel_cuts = []
    for edge in panel_rims:
        f1, f2 = adjacency[edge]
        n1, n2 = f1.normal_at(edge.center()), f2.normal_at(edge.center())
        cosine = n1.dot(n2)
        if abs(cosine) > .999:
            continue
        d1, d2 = (-n2+n1*cosine).normalized(), (-n1+n2*cosine).normalized()
        a, b = (Vector(v) for v in edge.vertices())
        bevel = Face(Wire.make_polygon([a, a+d1*0.4, a+d2*0.4, a]))
        panel_cuts.append(Solid.extrude(bevel, b-a))
    part = part.cut(*panel_cuts).clean()
    bottom = part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[0]
    part = part.chamfer(BED_CHAMFER, None, bottom.edges())
    cutters = mount_fixtures(MOUNT, values).cutters
    for cutter in cutters:
        part -= cutter
    # The library profile is left intact above the 0.4 mm bed relief.
    # Its short bottom aperture edges cannot use OCCT's chamfer builder;
    # finite 45-degree wedges follow the demo-plate construction.
    bottom = part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[0]
    unrelieved = part
    bounds = [c.bounding_box() for c in cutters]
    edges = [e for e in bottom.edges() if BED_CHAMFER+1e-6 < e.center().Y <= POCKET_DEPTH+1e-6
             and any(b.min.X-1e-6 <= e.center().X <= b.max.X+1e-6 for b in bounds)]
    for edge in edges:
        a, b = edge.vertices()
        start, end = Vector(a), Vector(b)
        tangent = (end-start).normalized()
        inward = Vector(-tangent.Y, tangent.X, 0)
        if not unrelieved.is_inside(edge.center()+inward*0.01+Vector(0, 0, 0.01)):
            inward = -inward
        triangle = Face(Wire.make_polygon([
            start, start+inward*BED_CHAMFER,
            start+Vector(0, 0, BED_CHAMFER), start,
        ]))
        part -= Solid.extrude(triangle, tangent*edge.length)
    for edge in edges:
        for vertex in edge.vertices():
            part -= Pos(vertex.X, vertex.Y, 0)*Cone(BED_CHAMFER, 0, BED_CHAMFER,
                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    return part.clean()


SPEC = register(ModelSpec(
    name='holder_spool_cradle', build=lambda values: holder(**values),
    title='Spool cradle (Multibuild)', category_id='multiboard',
    description='Single spool bookshelf cradle with wide inboard saddle rails, outboard placement guides, closed truss webs and two full-height Multiconnect channels. Flange-rim support; standing PETG/PCTG print with support allowed only in the mount pockets.',
    tags=('holder', 'multiboard', 'spool'), params=PARAMS,
    mounts=(MOUNT,), print_orientation=(0, 0, 1),
    presets=(
        Preset('bambu_reusable_200', 'Bambu reusable 200 mm',
               {'spool_width': 67, 'flange_height': 8, 'flange_rim_width': 3}),
        Preset('ams_generic_200', 'AMS generic 200 mm',
               {'spool_width': 66, 'flange_height': 8, 'flange_rim_width': 3}),
    ),
))
