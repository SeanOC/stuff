"""Spool cradle v2: axis X along the board, +Y outward, printed on Z=0.

Worst case: 30 N downward at the front flange rim. Closed triangular webs
return to the plate through a bed chord; a vertical front panel ties them.
PETG/PCTG only (operator-approved PLA exclusion for sustained load/heat).
The 2.4 mm webs/panel print as perimeters; the plate uses three walls and
15% infill. Only library channel pockets may need supports. Arc saddles
are upward-facing contact surfaces on standing walls, not hanging shelves.
Fixed two-channel mount and 25 mm board pitch are operator-approved.
"""
from __future__ import annotations

import math
from build123d import Align, Axis, Box, BuildSketch, Cone, Face, Plane, Polygon, Pos, Rot, Solid, Vector, Wire, extrude
from holders.registry import ModelSpec, MountFixtures, Param, Preset, register
from multibuild.constants import PITCH
from multibuild.multiconnect import POCKET_DEPTH, channel_cutter

MOUNT = 'multibuild-multiconnect-channel'
WEB = 2.4
APEX_HEIGHT = 18.0
JOINT_RADIUS = 1.0
BED_CHAMFER = 0.4
CHORD = 6.0

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
    return p


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
    part = plate.fuse(rail, rail.mirror(Plane.YZ), panel).clean()
    joints = [e for e in part.edges().filter_by(Axis.Z)
              if (abs(e.center().Y-t) < 1e-6 and abs(abs(e.center().X)-ri) < 1e-6)
              or (abs(e.center().Y-end) < 1e-6 and abs(abs(e.center().X)-xi) < 1e-6)]
    part = part.fillet(JOINT_RADIUS, joints)
    # Ease exposed vertical edges. Functional circular rim-contact edges and
    # library mount geometry remain exact. No downward-facing fillets.
    verticals = list(part.edges().filter_by(Axis.Z))
    part = part.chamfer(0.4, None, verticals)
    # The triangular openings retain sharp internal 45-degree roof ridges
    # (a ceiling chamfer would introduce a flat overhang). Ease their rims.
    hole_rims = [e for e in part.edges() if e.geom_type.name == 'LINE'
                 and e.bounding_box().size.X < 1e-6
                 and any(abs(abs(e.center().X)-x) < 1e-6 for x in (xi, xi+WEB))
                 and CHORD-1e-6 <= e.center().Z < APEX_HEIGHT+CHORD
                 and t+12 < e.center().Y < end-1]
    part = part.chamfer(0.4, None, hole_rims)
    top = part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1]
    part = part.chamfer(0.4, None, top.edges())
    panel_rims = [e for e in part.edges() if e.bounding_box().size.Z < 1e-6
                  and abs(e.center().Z-p['panel_height']) < 1e-6
                  and (e.center().Y > end+1e-6 or e.length > 10)]
    part = part.chamfer(0.4, None, panel_rims)
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
    description='Single spool bookshelf cradle with arc saddles, closed truss webs and two full-height Multiconnect channels. Flange-rim support; standing PETG/PCTG print with support allowed only in the mount pockets.',
    tags=('holder', 'multiboard', 'spool'), params=PARAMS,
    mounts=(MOUNT,), print_orientation=(0, 0, 1),
    presets=(
        Preset('bambu_reusable_200', 'Bambu reusable 200 mm',
               {'spool_width': 67, 'flange_height': 8, 'flange_rim_width': 3}),
        Preset('ams_generic_200', 'AMS generic 200 mm',
               {'spool_width': 66, 'flange_height': 8, 'flange_rim_width': 3}),
    ),
))
