"""Spool cradle v2.1: axis X along the board, +Y outward, printed on Z=0.

Worst case: 30 N downward at the front flange rim. Closed triangular webs
return to the plate through a bed chord; a vertical front panel ties them.
PETG/PCTG only (operator-approved PLA exclusion for sustained load/heat).
The 2.4 mm webs/panel print as perimeters; the plate uses three walls and
15% infill. Only library channel pockets may need supports. Inboard rail
caps keep the analytic flange contact; 45-degree underside ramps carry
the caps and outboard lead-in guides in the standing pose.
Fixed two-channel mount and 25 mm board pitch are operator-approved.
mount_style='points' swaps the channels for four MultiBuild Fix Point slots
(2 columns x 2 rows 50 mm apart, lip end up, solid plate between) that hang
on Fix Points in the board; the body is the same.
mount_style='openconnect' carries four openConnect slots for an openGrid
wall (28 mm tiles, 84 mm holder cadence, 2 columns x 2 rows: one under the
plate top, one at the lowest tile that keeps the bottom floor);
the body is the same, only the grid and the plate floors change.
label_holder (default on, labels L3): two side rails and a bottom lip on the
front panel's outside face hold a label_card (labels/constants.py). The card
slides in from the top with the spool out (above the panel the spool is
proud of the face; the neighbouring cradle blocks a side slide). The holder
is omitted below spool_width HOLDER_MIN_PANEL_W (63.4 mm). Load: the card's
own weight on the lip; the rails retain it in +Y.
"""
from __future__ import annotations

import math
from dataclasses import replace
from build123d import (Align, Axis, Box, BuildSketch, Cone, Edge, Face, Kind, Plane, Polygon, Pos, Rot, Solid,
                       Vector, Wire, extrude)
from build123d import fillet as fillet_2d, offset as offset_2d
from holders.registry import ModelSpec, MountFixtures, PlaneSpec, Param, Preset, register
from labels.constants import (CARD_H, CARD_W, CORNER_R, HOLDER_JUNCTION, HOLDER_MIN_PANEL_W,
                              HOLDER_TOP_INSET, LIP_OVERLAP, RAIL_PROUD, RAIL_W, SLOT_CLEARANCE,
                              SLOT_DEPTH)
from multibuild.constants import PITCH
from multibuild import fixpoint as fp
from multibuild.multiconnect import POCKET_DEPTH, channel_cutter
from openconnect import constants as oc
from openconnect import grid as oc_grid
from openconnect.slot import POCKET_DEPTH as OC_POCKET_DEPTH

MOUNT = 'multibuild-multiconnect-channel'
OC_MOUNT = 'openconnect-slot'
FP_MOUNT = 'multibuild-fixpoint-slot'
WEB = 2.4
APEX_HEIGHT = 18.0
JOINT_RADIUS = 1.0
BED_CHAMFER = 0.4
CHORD = 6.0
# Per style: board pitch, holder cadence (three pitches), pocket depth and
# the gap a maximum-width plate leaves at that cadence. pitch and cadence are
# resolved into dimensions(); nothing below reads a module-level grid.
GRIDS = {
    'channel': (PITCH, 3*PITCH, POCKET_DEPTH, 5.0),
    'points': (PITCH, 3*PITCH, fp.POCKET_DEPTH, 5.0),
    'openconnect': (oc.TILE_SIZE, 3*oc.TILE_SIZE, OC_POCKET_DEPTH, 2.0),
}
# openConnect slot roof above its seat: the clearance-grown flange outline.
OC_SLOT_TOP = oc.HEAD_WIDTH/2+oc.BACK_POS_OFFSET+oc.SIDE_CLEARANCE  # 9.0
# The on-ramp's clearance floor, below the seat.
OC_SLOT_BOTTOM = oc.HEAD_HEIGHT+2*oc.SIDE_CLEARANCE+oc.MOVE_DISTANCE+oc.ONRAMP_CLEARANCE-OC_SLOT_TOP  # 13.2

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
        ('plate_width', 70, 68, 82, 0.5, 'Mount plate width'),
        ('plate_thickness', 7, 5.1, 9, 0.1, 'Mount plate thickness'),
        ('wall_clearance', 3, 3, 6, 0.5, 'Spool clearance from plate'),
        ('rail_width', 10, 6, 14, 0.5, 'Saddle rail width, inboard'),
        ('guide_height', 15, 12, 30, 1, 'Guide height above rail'),
        ('guide_gap', 0.5, 0.5, 2, 0.25, 'Half-gap to the neighbouring holder'),
    )) + (Param('mount_style', 'enum', 'channel',
                choices=('channel', 'points', 'openconnect'), label='Mount style',
                filename=True),
           Param('oc_lock_distribution', 'enum', 'corners',
                 choices=('corners', 'staggered', 'none'),
                 label='Lock nubs (openConnect only)'),
           Param('label_holder', 'boolean', True,
                 label=f'Label card holder (spool width >= {HOLDER_MIN_PANEL_W:g} mm; '
                       'swap the card with the spool out)'))
POINT_ROW_SPACING = 2*PITCH  # Two board rows: the pockets stay discrete.


def mount_for_values(values):
    """The one declared mount present under these resolved values."""
    return {'openconnect': OC_MOUNT, 'points': FP_MOUNT}.get(values['mount_style'], MOUNT)


def check_plate(p):
    """Style floors: the plate fits the style's cadence and backs its pocket.

    The shared plate_width / plate_thickness ranges cover every style, so a
    style-invalid combination is rejected here with the floor it violates.
    """
    _, cadence, depth, gap = GRIDS[p['mount_style']]
    if p['plate_width'] > cadence-gap+1e-9:
        raise ValueError(f"mount_style={p['mount_style']!r} needs plate_width <= "
                         f'{cadence-gap:g} mm (cadence {cadence:g} - {gap:g} mm gap)')
    if p['plate_thickness']-depth < WEB-1e-9:
        raise ValueError(f"mount_style={p['mount_style']!r} needs plate_thickness >= "
                         f'{depth+WEB:g} mm ({depth:g} mm pocket + {WEB:g} mm backing)')


def dimensions(values=None):
    p = SPEC.resolve_values(values)
    if not all(math.isfinite(v) for v in p.values() if not isinstance(v, str)):
        raise ValueError('parameters must be finite')
    check_plate(p)
    pitch, cadence, depth, _ = GRIDS[p['mount_style']]
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
    length = math.ceil(root_h/pitch)*pitch
    backing = p['plate_thickness']-depth
    if p['mount_style'] == 'openconnect':
        rows = oc_seats(length, backing)
        ramps = tuple(z-oc.MOVE_DISTANCE for z in rows)
    else:
        ramps = tuple(pitch/2+i*pitch for i in range(int(length/pitch)-1))
        rows = tuple(z+pitch/2 for z in ramps)
    p.update(pitch=pitch, cadence=cadence, pocket_depth=depth, radius=r, saddle_radius=rs, center_y=cy, center_z=cz,
             rear_y=rear, front_y=front, contact_z=contact_z, end_y=end,
             plate_height=length+backing, root_height=root_h,
             channel_length=length, onramps=ramps, seat_rows=rows,
             panel_height=contact_z+p['lip_height'],
             rail_inner=p['spool_width']/2-WEB,
             root_inner=min(p['spool_width'], p['plate_width']-4)/2-WEB,
             winding_radius=r-p['flange_height'])
    if p['mount_style'] == 'points':
        p['point_seats'] = point_seats(length)
    p.update(cap_inner=p['spool_width']/2-p['rail_width'],
             cap_reach=p['rail_width']-WEB,
             guide_outer=cadence/2-p['guide_gap'],
             guide_reach=cadence/2-p['guide_gap']-p['spool_width']/2,
             exposed_rim=2*r*math.sin(a)-p['lip_height']-p['guide_height'])
    # Rev 6 reserves a WEB-wide guide before edge finishing. At the
    # threshold the lead-in is vertical; rim bevels leave a 1.8 mm land.
    p['guide_enabled'] = p['guide_reach']+1e-9 >= WEB+p['saddle_clearance']
    # A wide reach (84 mm openGrid cadence, narrow spool) sinks the root's
    # 45-degree underside below the bed at the saddle apex.
    p['root_to_bed'] = p['guide_enabled'] and p['guide_reach']+WEB > APEX_HEIGHT
    # The card holder needs the slot, two outer walls and the side inset;
    # a narrower panel omits it (label_holder is then a no-op).
    p['label_holder_enabled'] = p['label_holder'] and p['spool_width']+1e-9 >= HOLDER_MIN_PANEL_W
    # The cap underside's last millimetre must fall toward the panel, else
    # a steep lip (shallow cradle_angle) leaves an acute groove at the
    # panel face. sqrt(2) is the original drop; 0.2 mm is the minimum fall.
    lip_slope = (p['panel_height']-contact_z)/(end-front)
    p['tail_drop'] = max(math.sqrt(2), lip_slope+.2)
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


def land_stage(p, x0, length, x_at, slope, bevel=.4):
    """Solid above a rear land floor z + (x - x_at) * slope over X.

    The land lies at the saddle height WEB/2 in front of rear_y, with a
    bevel x 45-degree chamfer at rear_y. Intersected stages take the
    highest floor, so each one adds a ramp to the land.
    """
    rear, land_y = p['rear_y'], p['rear_y']+WEB/2
    z = p['center_z']-math.sqrt(p['saddle_radius']**2-(land_y-p['center_y'])**2)
    top = p['contact_z']+20
    offset = (x0-x_at)*slope
    face = Face(Wire.make_polygon([
        (x0, rear-1, z-bevel-1+offset), (x0, rear+bevel, z+offset),
        (x0, land_y+1, z+offset), (x0, land_y+1, top+offset),
        (x0, rear-1, top+offset)], close=True))
    return Solid.extrude(face, (length, 0, length*slope))


def rear_land_cutter(p):
    """Flat land on the outboard root's rear end (right-hand side).

    Unbacked, the root's rear end is a cradle_angle knife where the saddle
    meets its vertical end face. The rail behind its own rear contact
    continues the tangent plane, so it needs no land. A WEB/2 land with a
    0.4 mm rear chamfer replaces the knife beside the rail. Cut before the
    guide fuses, so the guide refills wherever it stands above the land.
    Mirrored 30-degree ramps rise 0.4 mm to the rail's outer face and to the
    guide's lead-in, so neither junction closes to a square groove. A
    narrow gap becomes a 60-degree V with its root midway between them.
    """
    rear, xw, foot = p['rear_y'], p['spool_width']/2, p['spool_width']/2+p['saddle_clearance']
    land_y = rear+WEB/2
    def saddle(y):
        return p['center_z']-math.sqrt(p['saddle_radius']**2-(y-p['center_y'])**2)
    z, bevel = saddle(land_y), .4
    # The lead-in rises from the guide's rear land to the crest; find where
    # it crosses the land; the guide ramp reaches 0.4 mm above it there.
    # guide_height is bounded to 12-30 mm by its Param, so never zero.
    crest = max(foot, p['guide_outer']-WEB-.4)
    wall = foot+(z-saddle(rear+WEB))*(crest-foot)/p['guide_height']
    x0, length = xw-5, p['guide_outer']-xw+10
    def stage(x_at, slope):
        return land_stage(p, x0, length, x_at, slope, bevel)
    ramp = math.tan(math.radians(30))
    # At y=rear_y the guide underside is contact_z-(xo-x); the 45-degree
    # stage keeps the bevelled floor 0.1 mm above it, so no notch opens
    # below the guide where the shallower ramp would fall beneath it.
    rise_x = p['guide_outer']-(p['contact_z']-z)-bevel-.1
    return (stage(x0, 0) & stage(xw+.4/ramp, -ramp)
            & stage(wall-.4/ramp, ramp) & stage(rise_x, 1))


def rear_corner_wedge(p, bevel):
    """Explicit bevel for the right concave rail/guide-root rear corner.

    OCCT's chamfer of this corner fails non-monotonically with root depth,
    so the 45-degree fill is built directly. The hypotenuse joins the
    rail's outer face to the root's rear face; the land cutter trims its
    top to the root's land. The underside rises at 45 degrees in X like
    the root's underside, and also rises toward the plate. A small overlap
    goes into the rail and root.
    """
    xw, rear, top = p['spool_width']/2, p['rear_y'], p['contact_z']
    z0, overlap = top-p['guide_reach'], .1
    outline = [(xw-overlap, rear-bevel), (xw, rear-bevel), (xw+bevel, rear),
               (xw+bevel, rear+overlap), (xw-overlap, rear+overlap)]
    def ring(z):
        points = [(x, y, z(x, y)) for x, y in outline]
        return Wire.make_polygon([*points, points[0]])
    wedge = Solid.make_loft([ring(lambda x, y: z0+(x-xw)+(rear-y)/2),
                             ring(lambda x, y: top+1)], ruled=True)
    return wedge-rear_land_cutter(p)


def cap_land_cutter(p):
    """The outboard land, carried across the inboard cap's rear end.

    Nothing backs the cap behind its rear contact between cap_inner and
    the rail, so its rear end is the same cradle_angle knife. The land and
    its 0.4 mm rear chamfer match the outboard ones. A 30-degree ramp rises
    0.4 mm to the rail's inner face, where the cutter stops: the rail backs
    the cap outboard of it. 45-degree 0.4 mm bevels finish the land's edge
    at cap_inner and the cap's vertical rear corner there. Built, not
    chamfered: OCCT's rear chamfers on the knife failed at some parameter
    corners. holder() cuts it after the top clip.
    """
    ci, xi, rear, bevel = p['cap_inner'], p['rail_inner'], p['rear_y'], .4
    x0, length = ci-1, xi-(ci-1)
    ramp = math.tan(math.radians(30))
    land = land_stage(p, x0, length, x0, 0) & land_stage(p, x0, length, xi-bevel/ramp, ramp)
    # Union, not intersection: a 45-degree stage lowers the floor to the edge.
    edge = land_stage(p, x0, xi-x0, ci+bevel, 1)
    lo, hi = p['contact_z']-50, p['contact_z']+20
    corner = Pos(0, 0, lo)*Solid.extrude(Face(Wire.make_polygon([
        (ci+bevel+1, rear-1, 0), (ci-1, rear+bevel+1, 0), (ci-1, rear-1, 0)],
        close=True)), (0, 0, hi-lo))
    return land.fuse(edge, corner)


def cap_corner_wedge(p, bevel=.4):
    """Explicit bevel for the concave cap/rail-inner-face rear corner.

    Mirrors rear_corner_wedge() inboard of the rail. Its underside is flush
    with the cap's 45-degree underside at rear_y and rises toward the plate,
    and the cap land cutter trims its top. It is fused after the top clip,
    so its top stops just above the land's ramp at the rail's inner face:
    the overlap into the rail then stays below the saddle.
    """
    xi, rear, overlap = p['rail_inner'], p['rear_y'], .1
    def saddle(y, depth=0):
        return p['center_z']-math.sqrt((p['saddle_radius']+depth)**2-(y-p['center_y'])**2)
    deep, top = saddle(rear, WEB), saddle(rear+WEB/2)+bevel+.05
    z0 = deep-(xi-p['cap_inner'])
    outline = [(xi+overlap, rear-bevel), (xi, rear-bevel), (xi-bevel, rear),
               (xi-bevel, rear+overlap), (xi+overlap, rear+overlap)]
    def ring(z):
        points = [(x, y, z(x, y)) for x, y in outline]
        return Wire.make_polygon([*points, points[0]])
    wedge = Solid.make_loft([ring(lambda x, y: z0+(xi-x)+(rear-y)/2),
                             ring(lambda x, y: top)], ruled=True)
    return wedge-cap_land_cutter(p)


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
                          floor=-1000, radial_depth=WEB, tail_drop=p['tail_drop'])
    # An explicit vertical R1 gusset avoids OCCT's failed rolling fillet at
    # the short cap/panel junction. Its underside continues the 45° ramp.
    inner = p['cap_inner']
    blend = vertical_gusset(inner, p['end_y'], -1, -1)
    blend &= saddle_curtain(p, inner-JOINT_RADIUS, inner, .01, .01)
    blend -= saddle_curtain(p, inner-JOINT_RADIUS, inner, JOINT_RADIUS, 0,
                            floor=-1000, radial_depth=WEB, tail_drop=p['tail_drop'])
    cap = cap.fuse(blend)
    if p['guide_enabled']:
        xo, reach = p['guide_outer'], p['guide_reach']
        foot = xw+p['saddle_clearance']
        # The below-saddle root joins the ramp to a full wall of the web;
        # the lead-in starts outboard of the flange by saddle_clearance.
        root = saddle_curtain(p, xi, xo, end_extension=WEB)
        root -= saddle_curtain(p, xi, xo, -reach-WEB, 0,
                               floor=-1000, end_extension=WEB)
        root -= rear_land_cutter(p)
        if p['root_to_bed']:
            # The below-bed tail lies inside the rail: trimming it adds nothing.
            root -= Box(400, 400, 200, align=(Align.CENTER, Align.CENTER, Align.MAX))
        # Preserve the 2.4 mm finished crest wherever it fits. Rev 6 keeps
        # narrower guides down to a 2.4 mm blank (1.8 mm after rim bevels).
        crest = max(foot, xo-WEB-.4)
        guide = guide_top(p, crest, xo, p['guide_height'], p['guide_height'])
        if crest-foot > 1e-8:
            guide = guide.fuse(guide_top(p, foot, crest, 0, p['guide_height']))
        # Finish the guide's rear end while it is still a full-depth block:
        # the land exposes the lead-in's rear edge down into the root, and
        # OCCT cannot reliably close that chamfer on the thin foot or after
        # the fuse. The root buries the chamfer's lower end below the land.
        upper_ends = [e for e in guide.edges()
                      if e.geom_type.name == 'LINE' and e.bounding_box().size.X > 1e-6
                      and abs(e.center().Y-p['rear_y']) < 1e-6
                      and e.center().Z > p['contact_z']]
        guide = guide.chamfer(.4, None, upper_ends)
        guide -= saddle_curtain(p, foot, xo, foot-xw-reach, 0, floor=-1000, end_extension=WEB)
        guide = guide.fuse(root).clean()
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

    Runouts taper across the whole cap and guide root: a short steep taper
    turns the relief roof against the 45-degree cap/root undersides and
    leaves a sharp crease. The deep cutter, which removes only the added
    cap/guide tails, grows inboard so a deep cap tail meets the web face
    at an open corner. The final shallow cutter preserves the original
    chord through the web.
    """
    y,z=triangle[2]
    xi=p['rail_inner']
    # A root reaching the bed is cut down to the bed chord, so the deep
    # cutter's flanks meet the web's outer face: widen them outboard there
    # to keep that concave corner below 90 degrees.
    outboard=.6 if deep and p['root_to_bed'] else 0
    wires=[]
    for x,offset in ((p['cap_inner']-2,.8 if deep else 0),(xi,.4),
                     (xi+.4,0),(xi+WEB-.4,0),(xi+WEB,.4),
                     (p['cadence']/2+1,outboard)):
        roof=z+offset*math.sqrt(2)
        floor=-100 if deep else CHORD-offset
        half=roof-floor
        vertices=[(x,y-half,floor),(x,y+half,floor),(x,y,roof)]
        wires.append(Wire.make_polygon([*vertices,vertices[0]]))
    return Solid.make_loft(wires,ruled=True)


def point_seats(channel_length):
    """Seat heights of the two Fix Point slots in each column.

    The upper slot's lip end stops where the channel spine would, under the
    same closed cap, which keeps the upper heads as high as the plate allows
    for pull-out leverage. The lower slot is one POINT_ROW_SPACING below and
    its well keeps a WEB + 0.5 mm floor above the bed relief: no bottom opening.
    """
    upper = channel_length-fp.DEEP_INRADIUS
    lower = upper-POINT_ROW_SPACING
    if lower-(fp.SLOT_LENGTH-fp.DEEP_INRADIUS) < WEB+.5-1e-9:
        # dimensions() rounds root_height up to the 25 mm channel length.
        span = WEB+.5+POINT_ROW_SPACING+fp.SLOT_LENGTH
        root = (math.ceil(span/PITCH)-1)*PITCH
        raise ValueError(f"mount_style='points' needs root_height > {root:.0f} mm "
                         f'({span:.2f} mm pocket span); channel length is {channel_length:.0f} mm')
    return (lower, upper)


def oc_seats(channel_length, backing):
    """Seat heights of the two openConnect rows in each column.

    The upper slot roof sits WEB below the plate top, which keeps the upper
    heads as high as the plate allows. The lower row is the lowest whole tile
    below it whose on-ramp keeps a WEB + 0.5 mm floor above the bed relief,
    so the rows stand as far apart as the board grid allows.
    """
    upper = channel_length+backing-WEB-OC_SLOT_TOP
    tiles = math.floor((upper-OC_SLOT_BOTTOM-(WEB+.5)+1e-9)/oc.TILE_SIZE)
    if tiles < 1:
        # dimensions() rounds root_height up to the 28 mm grid length.
        span = 2*WEB+.5+OC_SLOT_TOP+oc.TILE_SIZE+OC_SLOT_BOTTOM-backing
        root = (math.ceil(span/oc.TILE_SIZE-1e-9)-1)*oc.TILE_SIZE
        raise ValueError(f"mount_style='openconnect' needs root_height > {root:.0f} mm "
                         f'({span:.2f} mm slot span); grid length is {channel_length:.0f} mm')
    return (upper-tiles*oc.TILE_SIZE, upper)


def mount_fixtures(mount_type, values):
    """Fixtures for the selected style's mount; None for the other mount."""
    if mount_type not in (MOUNT, OC_MOUNT, FP_MOUNT):
        raise ValueError(f'unsupported mount: {mount_type}')
    p = dimensions(values)
    if mount_type != mount_for_values(p):
        return None
    if p['mount_style'] == 'openconnect':
        # Both columns on adjacent tile centres; every slot has the same
        # on-ramp offset, so one push-in, shift and downward slide seats all.
        lower, upper = p['seat_rows']
        tiles = round((upper-lower)/oc.TILE_SIZE)
        lock = p['oc_lock_distribution']
        slots = oc_grid.layout(2, tiles+1, position='corners',
                               lock='none' if lock == 'none' else 'corners', slide='up')
        if lock == 'staggered':
            # Diagonal of the populated rows, independent of lattice parity:
            # left/lower and right/upper keep their nubs.
            slots = [replace(s, nubs='none') if s.x*s.z < 0 else s for s in slots]
        slots.sort(key=lambda s: (s.z, s.x))  # Preserve the original fixture order.
        fx = oc_grid.fixtures(slots)
        shift = Pos(0, 0, (upper+lower)/2)
        return replace(fx, cutters=[shift*c for c in fx.cutters],
                       seat_locs=[shift*s for s in fx.seat_locs],
                       onramp_locs=[shift*r for r in fx.onramp_locs])
    if p['mount_style'] == 'points':
        # Lip end up: lowering the holder onto the board's Fix Points carries
        # each head from its well up under its lip.
        slots = [(x, z) for x in (-p['pitch']/2, p['pitch']/2) for z in p['point_seats']]
        cutter = fp.slot_cutter()
        return MountFixtures(
            cutters=[Pos(x, 0, z)*cutter for x, z in slots],
            seat_locs=[fp.seat_location(x, z) for x, z in slots],
            onramp_locs=[fp.entry_location(x, z) for x, z in slots],
            entry_axis=(0, 0, 1), face_normal=(0, -1, 0),
        )
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


def label_slot(p):
    """The card slot (labels L3) as (x, y0, y1, z0, z1), or None when omitted.

    X is the half-width at the side walls; Y runs off the panel face.
    """
    if not p['label_holder_enabled']:
        return None
    face, top = p['end_y']+WEB, p['panel_height']-HOLDER_TOP_INSET
    return (CARD_W/2+SLOT_CLEARANCE, face, face+SLOT_DEPTH,
            top-CARD_H-2*SLOT_CLEARANCE, top)


def seated_card(p, shape):
    """A label_card body (print frame, face down) centred in the slot, face out."""
    _, face, _, floor, _ = label_slot(p)
    return Pos(0, face+SLOT_DEPTH-SLOT_CLEARANCE, floor+SLOT_CLEARANCE+CARD_H/2)*Rot(90, 0, 0)*shape


def label_holder(p):
    """Rails and bottom lip on the panel's outside face (labels L3, D8).

    Built finished, then fused last so no panel edge selection changes.
    The underside is one 45-degree ramp from the panel face; a 45-degree
    junction blend runs round the outer footprint, shrunk only where the
    panel's 0.4 mm side chamfer leaves less room. The slot's walls, floor
    and the shelves' backs are mating faces and stay sharp.
    """
    x_s, face, _, floor, top = label_slot(p)
    x_o = x_s+RAIL_W-LIP_OVERLAP
    x_in = CARD_W/2-LIP_OVERLAP
    shelf_top = floor+SLOT_CLEARANCE+LIP_OVERLAP
    tip = floor-(RAIL_W-LIP_OVERLAP)-RAIL_PROUD
    blend = min(HOLDER_JUNCTION, p['spool_width']/2-x_o-.45)
    corner = (RAIL_W-LIP_OVERLAP)/2
    outline = Face(Wire.make_polygon([
        (-x_o+RAIL_PROUD+1, face, tip-1), (x_o-RAIL_PROUD-1, face, tip-1),
        (x_o, face, tip+RAIL_PROUD), (x_o, face, top), (-x_o, face, top),
        (-x_o, face, tip+RAIL_PROUD)], close=True))
    outline = fillet_2d(outline.vertices().filter_by_position(Axis.Z, top-1e-6, top+1e-6),
                     corner).face()
    body = extrude(outline, amount=RAIL_PROUD, dir=(0, 1, 0)).fuse(extrude(
        offset_2d(outline, blend, kind=Kind.INTERSECTION), amount=blend, dir=(0, 1, 0), taper=45))
    with BuildSketch(Plane.YZ) as ramp:
        Polygon((face-1, tip-1), (face+RAIL_PROUD+1, tip+RAIL_PROUD+1),
                (face+RAIL_PROUD+1, top+10), (face-1, top+10), align=None)
    window = Face(Wire.make_polygon([(-x_in, 0, shelf_top), (x_in, 0, shelf_top),
                                     (x_in, 0, top+10), (-x_in, 0, top+10)], close=True))
    window = fillet_2d(window.vertices().filter_by_position(Axis.Z, shelf_top-1e-6,
                                                         shelf_top+1e-6), CORNER_R).face()
    body = (body & extrude(ramp.sketch, amount=x_o+10, both=True)) - Pos(0, face-1, 0)*extrude(
        window, amount=RAIL_PROUD+2, dir=(0, 1, 0)) - Pos(0, face-1, floor)*Box(
        2*x_s, SLOT_DEPTH+1, top, align=(Align.CENTER, Align.MIN, Align.MIN))
    body = body.fillet(corner, [e for e in body.edges().filter_by(Axis.Y)
                                if abs(abs(e.center().X)-x_in) < 1e-6
                                and abs(e.center().Z-top) < 1e-6])
    front = body.faces().filter_by(Axis.Y).sort_by(Axis.Y)[-1]
    return body.chamfer(.4, None, front.edges())


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
    # Cut the cap's rear land on the clipped part: on the aids, the cap's
    # 0.01 mm curtain lift left a sliver on the rear knife line that the
    # clip fused into an unorientable saddle face at cradle_angle=45.
    land, wedge = cap_land_cutter(p), cap_corner_wedge(p)
    part = (part-land-land.mirror(Plane.YZ)).fuse(
        wedge, wedge.mirror(Plane.YZ)).clean()
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
    # The cap's rear corners are built finished (cap_land_cutter/wedge).
    verticals = [e for e in part.edges().filter_by(Axis.Z)
                 if not (abs(e.center().Y-end) < 1e-6 and any(
                     abs(abs(e.center().X)-x) < 1e-6
                     for x in (p['cap_inner'], p['spool_width']/2)))
                 if not (abs(e.center().Y-p['rear_y']) < .4+1e-6 and
                         p['cap_inner']-1e-6 < abs(e.center().X) < p['rail_inner']+1e-6)
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
    # The concave rail/guide-root corner gets an explicit wedge instead.
    concave = [e for e in rear_edges if p['guide_enabled']
               and abs(abs(e.center().X)-p['spool_width']/2) < 1e-6]
    rear_edges = [e for e in rear_edges if e not in concave]
    narrow_guide = p['guide_enabled'] and p['guide_reach']-p['saddle_clearance'] < WEB+.4
    # The rear contact tangent falls by cot(angle) per millimetre of Y.
    # Bound the bevel's vertical reach to the nominal 0.4 mm edge relief,
    # so shallow-angle corners retain their full section below it.
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
        # Use the same land bound on any other rear edges. The cap's rear
        # corners are built (cap_land_cutter), so this is usually empty.
        if other_rear:
            part = part.chamfer(guide_bevel, None, other_rear)
        guide_inner = [e for e in part.edges().filter_by(Axis.Z)
                       if abs(abs(e.center().X)-foot) < 1e-6
                       and abs(e.center().Y-p['rear_y']) < 1e-6]
        part = part.chamfer(guide_bevel, None, guide_inner)
    else:
        if rear_edges:
            part = part.chamfer(rear_bevel, None, rear_edges)
        guide_bevel = rear_bevel
    if concave:
        wedge = rear_corner_wedge(p, guide_bevel)
        part = part.fuse(wedge, wedge.mirror(Plane.YZ)).clean()
    if p['guide_enabled']:
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
    cutters = mount_fixtures(mount_for_values(p), values).cutters
    for cutter in cutters:
        part -= cutter
    # The library profile is left intact above the 0.4 mm bed relief.
    # Its short bottom aperture edges cannot use OCCT's chamfer builder;
    # finite 45-degree wedges follow the demo-plate construction.
    bottom = part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[0]
    unrelieved = part
    bounds = [c.bounding_box() for c in cutters]
    edges = [e for e in bottom.edges() if BED_CHAMFER+1e-6 < e.center().Y <= p['pocket_depth']+1e-6
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
    if p['label_holder_enabled']:
        part = part.fuse(label_holder(p))
    return part.clean()


# Static review plane uses the default plate + clearance + spool radius.
_DEFAULT_SECTION_Y = 7 + 3 + 200 / 2

SPEC = register(ModelSpec(
    name='holder_spool_cradle', build=lambda values: holder(**values),
    title='Spool cradle (Multibuild)', category_id='multiboard',
    description='Single spool bookshelf cradle with wide inboard saddle rails, outboard placement guides (omitted when reach is less than 2.4 mm plus saddle clearance) and closed truss webs, in three mount styles: two full-height Multiconnect channels (channel), four MultiBuild Fix Point slots in two rows 50 mm apart, lip end up (points), or four openConnect slots for an openGrid wall on the 28 mm tile pitch and 84 mm cadence, two under the plate top and two at the lowest tile that keeps the bottom floor (openconnect). A slide-in label card holder on the front panel (spool width 63.4 mm and up; swap the card with the spool out). Flange-rim support; standing PETG/PCTG print with support allowed only in the mount pockets.',
    tags=('holder', 'multiboard', 'opengrid', 'spool', 'multiconnect-channel',
          'fixpoint-slots', 'openconnect'), params=PARAMS,
    mounts=(MOUNT, OC_MOUNT, FP_MOUNT), mount_for_values=mount_for_values, print_orientation=(0, 0, 1),
    review_sections=(PlaneSpec((0, _DEFAULT_SECTION_Y, 0), (1, 0, 0),
                              'mid-plane through saddle + truss'),),
    presets=(
        Preset('channel', '200 mm spool, Multiconnect channels',
               {'spool_width': 67, 'flange_height': 8, 'flange_rim_width': 3}),
        Preset('points', '200 mm spool, Fix Point slots',
               {'spool_width': 67, 'flange_height': 8, 'flange_rim_width': 3,
                'mount_style': 'points'}),
        Preset('openconnect', '200 mm spool, openConnect',
               {'spool_width': 67, 'flange_height': 8, 'flange_rim_width': 3,
                'mount_style': 'openconnect', 'plate_width': 82, 'plate_thickness': 5.5}),
    ),
))
