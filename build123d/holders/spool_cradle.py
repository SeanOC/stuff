"""One spool, axis X parallel to the board; +Y faces the user, +Z is up.

Print standing on Z=0. Worst case: 30 N downward at the front contact,
putting longitudinal Y fibres in bending. PETG/PCTG only; PLA excluded by
operator approval (creep/heat). Only library slot pockets may need supports.
Two ribbed 2.4 mm webs carry the flange rims, with R1 vertical root blends.
The wider plate is slicer-filled; strength calculations count its shell only.

pst-ir0v approves fixed count=2, travel=25, snap=True and derived margins:
three seats cannot fit the 70 mm plate on the large-hole lattice. The plate
centre is on a small-hole column. See docs/spool-cradle-validation.md.
"""
from __future__ import annotations

import math
from build123d import Align, Axis, Box, BuildSketch, Cone, Face, Plane, Polygon, Pos, Rot, Solid, Vector, Wire, extrude
from holders.registry import ModelSpec, MountFixtures, Param, Preset, register
from multibuild.constants import PITCH
from multibuild.multiconnect import POCKET_DEPTH, slot_cutter

MOUNT = 'multibuild-multiconnect-slot'
WEB = 2.4
APEX_HEIGHT = 18.0
JOINT_RADIUS = 1.0
SEAT_Z = 24.0
BED_CHAMFER = 0.4
MOUNT_RIB_DEPTH = 15.0
MOUNT_RIB_HEIGHT = 60.0

PARAMS = tuple(Param(name, 'number', default, min=lo, max=hi, step=step,
                    unit='deg' if name == 'cradle_angle' else 'mm', label=label)
    for name, default, lo, hi, step, label in (
        ('spool_diameter', 200, 190, 205, 0.5, 'Spool diameter'),
        ('spool_width', 66, 50, 70, 0.5, 'Spool width'),
        ('flange_height', 8, 4, 15, 0.5, 'Flange above winding'),
        ('flange_rim_width', 3, 1.5, 6, 0.5, 'Flange rim width'),
        ('cradle_angle', 40, 25, 45, 1, 'V half angle from vertical'),
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
    cz = APEX_HEIGHT + r/math.sin(a)
    dy = r*math.cos(a)
    contact_z = cz-r*math.sin(a)
    end = cy+dy+p['lip_height']*math.tan(a)
    root_h = APEX_HEIGHT+(cy-p['plate_thickness'])/math.tan(a)
    p.update(radius=r, center_y=cy, center_z=cz, rear_y=cy-dy,
             front_y=cy+dy, contact_z=contact_z, end_y=end,
             plate_height=root_h+1, root_height=root_h,
             rail_inner=p['spool_width']/2-WEB,
             root_inner=min(p['spool_width'], p['plate_width']-4)/2-WEB,
             winding_radius=r-p['flange_height'])
    return p


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    dimensions(values)
    return MountFixtures(
        cutters=[Pos(x, 0, SEAT_Z)*slot_cutter(snap=True) for x in (-PITCH/2, PITCH/2)],
        seat_locs=[Pos(x, POCKET_DEPTH, SEAT_Z)*Rot(90, 0, 0) for x in (-PITCH/2, PITCH/2)],
        entry_axis=(0, 0, 1), face_normal=(0, -1, 0),
    )


def holder(**values):
    p = dimensions(values)
    t, cy, end = p['plate_thickness'], p['center_y'], p['end_y']
    slope = 1/math.tan(math.radians(p['cradle_angle']))
    start = t-WEB
    with BuildSketch(Plane.YZ) as profile:
        Polygon((start, 0), (end, 0),
                (end, APEX_HEIGHT+(end-cy)*slope), (cy, APEX_HEIGHT),
                (t, p['root_height']), (start, p['root_height']), align=None)
    blank = extrude(profile.sketch, amount=p['spool_width'], both=True)
    ri, xi = p['root_inner'], p['rail_inner']
    with BuildSketch(Plane.XY) as footprint:
        Polygon((ri, start), (ri+WEB, start), (ri+WEB, t),
                (xi+WEB, t+12), (xi+WEB, end), (xi, end),
                (xi, t+12), (ri, t), align=None)
    rail = blank & extrude(footprint.sketch, amount=p['plate_height']+100)
    plate = Box(p['plate_width'], t, p['plate_height'],
                align=(Align.CENTER, Align.MIN, Align.MIN))
    part = plate.fuse(rail, rail.mirror(Plane.YZ)).clean()
    # Short transverse ribs stiffen the webs against lateral handling. They
    # extend INWARD below the tangent surface by 12 mm, clear of winding.
    rib_positions = (cy-35, cy+35)
    for y in rib_positions:
        height = APEX_HEIGHT+abs(y-cy)*slope-12
        if height <= WEB:
            continue
        rib = Pos(xi-3, y-WEB/2, 0)*Box(3+WEB, WEB, height,
                align=(Align.MIN, Align.MIN, Align.MIN))
        part = part.fuse(rib, rib.mirror(Plane.YZ)).clean()
    # Solid perimeter ribs stiffen the pocketed plate section. The 45-degree
    # upper ramps remain below the spool envelope, with no underside bridge.
    with BuildSketch(Plane.YZ) as mount_profile:
        Polygon((t-WEB, 0), (t+MOUNT_RIB_DEPTH, 0),
                (t+MOUNT_RIB_DEPTH, MOUNT_RIB_HEIGHT-MOUNT_RIB_DEPTH),
                (t, MOUNT_RIB_HEIGHT), (t-WEB, MOUNT_RIB_HEIGHT), align=None)
    mount_rib = extrude(mount_profile.sketch, amount=WEB)
    for x in (-PITCH/2, PITCH/2):
        part = part.fuse(Pos(x-WEB/2, 0, 0)*mount_rib).clean()
    # R1 on the vertical re-entrant root junctions, after fusion.
    joints = [e for e in part.edges().filter_by(Axis.Z)
              if abs(e.center().Y-t) < 1e-6 and
              (abs(abs(e.center().X)-ri) < 1e-6 or
               abs(abs(e.center().X)-(PITCH/2-WEB/2)) < 1e-6 or
               abs(abs(e.center().X)-(PITCH/2+WEB/2)) < 1e-6)]
    part = part.fillet(JOINT_RADIUS, joints)
    # Exposed vertical edges and plate top are eased; contact-plane edges
    # remain functional. Bed relief follows the actual remaining outline.
    top = part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1]
    part = part.chamfer(0.5, None, top.edges())
    rib_tops = [e for e in part.edges() if e.bounding_box().size.Z < 1e-6
                and 1 < e.center().Z < p['plate_height']-1
                and abs(e.center().X) < xi-1e-6 and e.center().Y > t+12]
    part = part.chamfer(0.5, None, rib_tops)
    if p['lip_height'] >= 1:
        lip_tops = [e for e in part.edges() if e.bounding_box().size.Z < 1e-6
                    and abs(e.center().Y-end) < 1e-6 and e.center().Z > 1]
        part = part.chamfer(0.5, None, lip_tops)
    ramps = [e for e in part.edges() if e.geom_type.name == 'LINE'
             and e.bounding_box().size.Z > 1 and e.bounding_box().size.Y > 1
             and abs(e.center().X) < PITCH/2+WEB and e.center().Y > t]
    part = part.chamfer(0.5, None, ramps)
    def rib_joint(e):
        return (abs(abs(e.center().X)-xi) < 1e-6
                and any(abs(abs(e.center().Y-y)-WEB/2) < 1e-6 for y in rib_positions))
    verticals = [e for e in part.edges().filter_by(Axis.Z)
                 if (abs(e.center().Y-t) > 1e-6 or
                     abs(abs(e.center().X)-(ri+WEB)) < 1e-6 or
                     abs(abs(e.center().X)-p['plate_width']/2) < 1e-6) and not rib_joint(e)]
    part = part.chamfer(0.5, None, verticals)
    part = part.fillet(JOINT_RADIUS, [e for e in part.edges().filter_by(Axis.Z) if rib_joint(e)])
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
    description='Single spool bookshelf cradle on two flush snap-in Multiconnect slots. Flange-rim support; standing PETG/PCTG print with support allowed only in the mount pockets.',
    tags=('holder', 'multiboard', 'spool'), params=PARAMS,
    mounts=(MOUNT,), print_orientation=(0, 0, 1),
    presets=(
        Preset('bambu_reusable_200', 'Bambu reusable 200 mm',
               {'spool_width': 67, 'flange_height': 8, 'flange_rim_width': 3}),
        Preset('ams_generic_200', 'AMS generic 200 mm',
               {'spool_width': 66, 'flange_height': 8, 'flange_rim_width': 3}),
    ),
))
