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
    # Rev 6 reserves a WEB-wide guide before edge finishing. At the
    # threshold the lead-in is vertical; rim bevels leave a 1.8 mm land.
    p['guide_enabled'] = p['guide_reach']+1e-9 >= WEB+p['saddle_clearance']
    return p


def saddle_curtain(p, x0, x1, dz0=0, dz1=0, floor=-100, radial_depth=0,
                   end_extension=0, tail_drop=0):
    """Solid below the exact saddle, translated vertically across X.

    Oblique extrusion keeps XZ ramp sections at 45 degrees while retaining
    the circular YZ profile. A rotating pipe would change those sections.
    The tangent extension carries the aids to the front lip. tail_drop adds
    the inclined cap/panel junction within its last millimetre.
    """
    rear, front, end = p['rear_y'], p['front_y'], p['end_y']
    rs = p['saddle_radius']+radial_depth
    z = p['center_z']-math.sqrt(rs**2-(rear-p['center_y'])**2)+dz0
    tip = p['panel_height']+z-p['contact_z']
    a, b = (x0, rear, z), (x0, front, z)
    c = (x0, end, tip-tail_drop)
    lead = [(x0,end-1,tip-(tip-z)/(end-front))] if tail_drop else []
    tail = [(x0, end+end_extension, tip)] if end_extension else []
    points = [c, *tail, (x0, end+end_extension, floor), (x0, rear, floor), a]
    wire = Wire([Edge.make_three_point_arc(a, (x0, p['center_y'], APEX_HEIGHT-radial_depth+dz0), b),
                 *(Edge.make_line(u,v) for u,v in zip([b,*lead,c],[*lead,c])),
                 *(Edge.make_line(u, v) for u, v in zip(points, points[1:]))])
    return Solid.extrude(Face(wire), (x1-x0, 0, dz1-dz0))


def guide_top(p, x0, x1, h0, h1):
    """Flat end lands keep the rising guide from feathering at its ends.

    Continue the front land across the panel so both share one end face.
    The central contact-length arc remains analytic.
    """
    rear, front, end = p['rear_y'], p['front_y'], p['end_y']
    start, stop = rear+WEB, end-WEB
    arc_end = min(front, stop)
    def z(y):
        if y <= front:
            return p['center_z']-math.sqrt(p['saddle_radius']**2-(y-p['center_y'])**2)+h0
        return p['contact_z']+(y-front)*(p['panel_height']-p['contact_z'])/(end-front)+h0
    a, b = (x0,rear,z(start)), (x0,start,z(start))
    c = (x0,arc_end,z(arc_end))
    edges = [Edge.make_line(a,b), Edge.make_three_point_arc(b,
        (x0,p['center_y'],z(p['center_y'])),c)]
    if stop > front:
        d=(x0,stop,z(stop))
        edges.append(Edge.make_line(c,d))
        c=d
    tail=[c,(x0,end+WEB,z(stop)),(x0,end+WEB,-100),(x0,rear,-100),a]
    edges.extend(Edge.make_line(u,v) for u,v in zip(tail,tail[1:]))
    return Solid.extrude(Face(Wire(edges)),(x1-x0,0,h1-h0))


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

    Both underside chamfers retain full-WEB overlap with the standing web.
    Cut the block below each void roof before fusion, so a deep cap cannot
    leave a thin tail beneath an opening floor. The baseline web supplies
    the unchanged bed chord and 1.6 mm core.
    """
    xi, xw = p['rail_inner'], p['spool_width']/2
    cap = saddle_curtain(p, p['cap_inner'], xw, .01, .01)
    cap -= saddle_curtain(p, p['cap_inner'], xw, 0, -p['rail_width'],
                          floor=-1000, radial_depth=WEB, tail_drop=math.sqrt(2))
    # An explicit vertical R1 gusset avoids OCCT's failed rolling fillet at
    # the short cap/panel junction. Its underside continues the 45° ramp.
    inner = p['cap_inner']
    blend = vertical_gusset(inner, p['end_y'], -1, -1)
    blend &= saddle_curtain(p, inner-JOINT_RADIUS, inner, .01, .01)
    blend -= saddle_curtain(p, inner-JOINT_RADIUS, inner, JOINT_RADIUS, 0,
                            floor=-1000, radial_depth=WEB, tail_drop=math.sqrt(2))
    cap = cap.fuse(blend)
    if p['guide_enabled']:
        xo, reach = p['guide_outer'], p['guide_reach']
        foot = xw+p['saddle_clearance']
        # The below-saddle root joins the ramp to a full wall of the web;
        # the lead-in starts outboard of the flange by saddle_clearance.
        root = saddle_curtain(p, xi, xo, end_extension=WEB)
        root -= saddle_curtain(p, xi, xo, -reach-WEB, 0,
                               floor=-1000, end_extension=WEB)
        # Preserve the 2.4 mm finished crest wherever it fits. Rev 6 keeps
        # narrower guides down to a 2.4 mm blank (1.8 mm after rim bevels).
        crest = max(foot, xo-WEB-.4)
        guide = guide_top(p, crest, xo, p['guide_height'], p['guide_height'])
        if crest-foot > 1e-8:
            guide = guide.fuse(guide_top(p, foot, crest, 0, p['guide_height']))
        guide -= saddle_curtain(p, foot, xo, foot-xw-reach, 0, floor=-1000, end_extension=WEB)
        guide = guide.fuse(root).clean()
        upper_ends = [e for e in guide.edges()
                      if e.geom_type.name == 'LINE' and e.bounding_box().size.X > 1e-6
                      and abs(e.center().Y-p['rear_y']) < 1e-6
                      and e.center().Z > p['contact_z']]
        guide = guide.chamfer(.4, None, upper_ends)
        crest_edges = []
        for e in guide.edges():
            c=e.center()
            if abs(e.bounding_box().min.X-xo)>1e-6 or abs(e.bounding_box().max.X-xo)>1e-6:
                continue
            base=(p['center_z']-math.sqrt(p['saddle_radius']**2-(c.Y-p['center_y'])**2)
                  if c.Y <= p['front_y'] else p['contact_z']+
                  (c.Y-p['front_y'])*(p['panel_height']-p['contact_z'])/(p['end_y']-p['front_y']))
            if c.Z > base+p['guide_height']/2:
                crest_edges.append(e)
        guide = guide.chamfer(.4,None,crest_edges)
        if crest-foot <= 1e-8:
            inner_edges = []
            for e in guide.edges():
                c = e.center()
                if abs(e.bounding_box().min.X-foot)>1e-6 or abs(e.bounding_box().max.X-foot)>1e-6:
                    continue
                base = (p['center_z']-math.sqrt(p['saddle_radius']**2-(c.Y-p['center_y'])**2)
                        if c.Y <= p['front_y'] else p['contact_z']+
                        (c.Y-p['front_y'])*(p['panel_height']-p['contact_z'])/(p['end_y']-p['front_y']))
                if c.Z > base+p['guide_height']/2:
                    inner_edges.append(e)
            guide = guide.chamfer(.2, None, inner_edges)
        cap = cap.fuse(guide).clean()
    for triangle in truss_openings(p):
        cap -= truss_relief(p, triangle, deep=True)
    return cap.clean()


def truss_relief(p, triangle, deep=False):
    """Mitred rim relief; the original apex continues outside the web.

    The 1.6 mm outer runouts avoid a sharp crease where the relief meets
    the cap underside. Deep cutters remove only the added cap/guide tails;
    the final shallow cutter preserves the original chord through the web.
    """
    y,z=triangle[2]
    xi=p['rail_inner']
    wires=[]
    for x,offset in ((p['cap_inner']-2,0),(xi-1.6,0),(xi,.4),
                     (xi+.4,0),(xi+WEB-.4,0),(xi+WEB,.4),
                     (xi+WEB+1.6,0),(CADENCE/2+1,0)):
        roof=z+offset*math.sqrt(2)
        floor=-100 if deep else CHORD-offset
        half=roof-floor
        vertices=[(x,y-half,floor),(x,y+half,floor),(x,y,roof)]
        wires.append(Wire.make_polygon([*vertices,vertices[0]]))
    return Solid.make_loft(wires,ruled=True)


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
    base_verticals = [e for e in verticals if e.length > 1 and abs(e.center().Y-p['rear_y']) > 1e-6]
    rear_datums = [e.center() for e in verticals if abs(e.center().Y-p['rear_y']) <= 1e-6]
    part = part.chamfer(0.4, None, base_verticals)
    rear_edges = [e for e in part.edges().filter_by(Axis.Z)
                  if any(abs(e.center().X-c.X) < 1e-6 and abs(e.center().Y-c.Y) < 1e-6
                         for c in rear_datums)]
    narrow_guide = p['guide_enabled'] and p['guide_reach']-p['saddle_clearance'] < WEB+.4
    # The rear contact tangent falls by cot(angle) per millimetre of Y.
    # Bound the bevel's vertical reach to the nominal 0.4 mm edge relief,
    # so shallow-angle cap corners retain their full section below it.
    rear_bevel = min(0.4, p['saddle_clearance']/(4 if narrow_guide else 2),
                     BED_CHAMFER*math.tan(math.radians(p['cradle_angle'])))
    guide_inner = [e for e in rear_edges if narrow_guide and
                   abs(abs(e.center().X)-foot) < 1e-6]
    if guide_inner:
        # The inner guide's pre-finished rim leaves a short land at each
        # endpoint. Clearance does not measure that land: at 45 degrees a
        # 1.5 mm clearance still leaves only a 0.2 mm horizontal rim land.
        # Limit its bevel to half the actual adjacent horizontal edge runs.
        runs = []
        all_edges = part.edges()
        for edge in guide_inner:
            for vertex in edge.vertices():
                point = vertex.center()
                for adjacent in all_edges:
                    if adjacent == edge or not any(
                            (v.center()-point).length < 1e-6 for v in adjacent.vertices()):
                        continue
                    run = max(math.hypot(v.X-point.X, v.Y-point.Y)
                              for v in adjacent.vertices())
                    if run > 1e-6:
                        runs.append(run)
        guide_bevel = min(rear_bevel, min(runs)/2)
        other_rear = [e for e in rear_edges if e not in guide_inner]
        # Use the same land bound on the cap/web rear edges: a larger
        # clearance-scaled bevel also thins the cap at the 25-degree corner.
        part = part.chamfer(guide_bevel, None, other_rear)
        guide_inner = [e for e in part.edges().filter_by(Axis.Z)
                       if abs(abs(e.center().X)-foot) < 1e-6
                       and abs(e.center().Y-p['rear_y']) < 1e-6]
        part = part.chamfer(guide_bevel, None, guide_inner)
        # Finish the short sloping intersections at the feet of those rear
        # bevels, where the guide and web meet the relieved contact surface.
        feet = [e for e in part.edges() if e.geom_type.name == 'LINE'
                and e.bounding_box().size.X < 1e-6
                and e.bounding_box().size.Y > 1e-6
                and abs(e.center().Y-p['rear_y']) < rear_bevel+.2
                and p['contact_z']-1 < e.center().Z < p['contact_z']
                and any(abs(abs(e.center().X)-x) < 1e-6
                        for x in (foot, p['spool_width']/2))]
        if feet:
            part = part.chamfer(min(guide_bevel, min(e.length for e in feet)/4), None, feet)
    else:
        part = part.chamfer(rear_bevel, None, rear_edges)
    # Finish each void with the same mitred profile used by the added block.
    # The original void and chord remain through the 1.6 mm web core.
    rim_cuts = []
    for triangle in truss_openings(p):
        cutter = truss_relief(p, triangle)
        rim_cuts.extend((cutter, cutter.mirror(Plane.YZ)))
    part = part.cut(*rim_cuts).clean()
    top = part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1]
    part = part.chamfer(0.4, None, top.edges())
    z = p['panel_height']
    back_edges = [e for e in part.edges() if abs(e.center().Y-end-WEB)<1e-6
                  and e.bounding_box().size.Y<1e-6 and e.center().Z>=z-1e-6]
    # The vertical threshold guide meets the panel across a short clearance
    # land; a smaller end bevel avoids crossing that land.
    if narrow_guide:
        adjacency = {}
        for face in part.faces():
            for edge in face.edges():
                adjacency.setdefault(edge, []).append(face)
        back_edges = [e for e in back_edges if len(adjacency[e]) == 2 and
                      adjacency[e][0].normal_at(e.center()).dot(
                          adjacency[e][1].normal_at(e.center())) < .01]
    part = part.chamfer(.2 if narrow_guide else .4, None, back_edges)
    front_edges = [e for e in part.edges() if e.geom_type.name == 'LINE'
                   and abs(e.center().Y-end)<1e-6 and abs(e.center().Z-z)<1e-6
                   and abs(e.center().X)<p['cap_inner']-1 and e.length>10]
    part = part.chamfer(.4, None, front_edges)
    if not p['guide_enabled']:
        panel_rims = [e for e in part.edges()
                      if abs(abs(e.center().X)-p['spool_width']/2) < 1e-6
                      and abs(e.center().Z-z) < 1e-6
                      and e.bounding_box().size.Y > 1
                      and e.center().Y > end]
        part = part.chamfer(.4, None, panel_rims)
    ramp_ends = [e for e in part.edges() if abs(e.center().Y-end-WEB)<1e-6
                 and e.bounding_box().size.Y<1e-6
                 and e.bounding_box().size.X>1 and e.bounding_box().size.Z>1
                 and e.center().Z<z]
    if ramp_ends:
        part = part.chamfer(.4,None,ramp_ends)
    if narrow_guide:
        adjacency = {}
        for face in part.faces():
            for edge in face.edges():
                adjacency.setdefault(edge, []).append(face)
        ends = [e for e in part.edges()
                if abs(e.center().X) >= foot-1e-6 and e.center().Y >= end
                and len(adjacency[e]) == 2
                and adjacency[e][0].normal_at(e.center()).dot(
                    adjacency[e][1].normal_at(e.center())) < .01]
        if ends:
            part = part.chamfer(.1, None, ends)
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
    bed_cuts = []
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
        bed_cuts.append(Solid.extrude(triangle, tangent*edge.length))
    vertices = {(v.X, v.Y) for edge in edges for v in edge.vertices()}
    for x, y in sorted(vertices):
        bed_cuts.append(Pos(x, y, 0)*Cone(BED_CHAMFER, 0, BED_CHAMFER,
                    align=(Align.CENTER, Align.CENTER, Align.MIN)))
    part = part.cut(*bed_cuts)
    return part.clean()


SPEC = register(ModelSpec(
    name='holder_spool_cradle', build=lambda values: holder(**values),
    title='Spool cradle (Multibuild)', category_id='multiboard',
    description='Single spool bookshelf cradle with wide inboard saddle rails, outboard placement guides (omitted when reach is less than 2.4 mm plus saddle clearance), closed truss webs and two full-height Multiconnect channels. Flange-rim support; standing PETG/PCTG print with support allowed only in the mount pockets.',
    tags=('holder', 'multiboard', 'spool'), params=PARAMS,
    mounts=(MOUNT,), print_orientation=(0, 0, 1),
    presets=(
        Preset('bambu_reusable_200', 'Bambu reusable 200 mm',
               {'spool_width': 67, 'flange_height': 8, 'flange_rim_width': 3}),
        Preset('ams_generic_200', 'AMS generic 200 mm',
               {'spool_width': 66, 'flange_height': 8, 'flange_rim_width': 3}),
    ),
))
