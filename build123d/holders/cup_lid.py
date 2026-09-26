"""Planar circular-segment cup-lid holder for Multibuild (pst-5slt).

X joins the pins; +Y is forward from the board; +Z is up. Print STANDING
on the lower chord, Z=-mount_height/2, without supports. Worst-case forward
pull (+Y) loads the lips and their continuous R1 junction webs along layers.
The plate carries lid weight (-Z) in compression. Intended for PLA/PCTG on
an H2S; the round horizontal bolt shank is the sole approved audit exception.

The circle centre is at Z=top_chord_offset + mount_height/2; the chords
are at circle-relative heights -top_chord_offset and
-top_chord_offset-mount_height. Thus the channels widen continuously upward.
Pins (+/-25, 0) and bolt hole use the PLATE centre between the chords, not
the circle centre. Default offset 1.5 mm follows the reviewed parameter
domain; its bottom tangent leans 43.3 degrees from vertical. The lips stop
above the bed at the inner-radius 45-degree limit plus lip_end_margin.
Their 45-degree end ramps rise inward from that stop; full-height walls
support the lid below the lips.

The fixed 25 mm pitch is one Multibuild Multi Unit. Board dimensions cited
in docs/cup-lid-validation.md: 7.5 mm mouth tapering to a 6.0 mm throat over
1.5 mm, total depth 6.4 mm. The rear cones CLEAR that cavity; they provide
coarse anti-rotation at the mouth rim (default +/-0.2 mm lateral play), not
chamfer seating. Their bases and the plate back are coplanar. The bolt clamps.
The 8 mm shank / 12.5 mm head / 90 degree seat are operator-approved BEST
GUESSES, exposed for the physical fit validation tracked by pst-mvno.

Functional sharp edges: lip shoulder-contact arc and wall seating arc.
Cone pin surfaces and countersink are functional. All bed-contact edges
have 45 degree relief; exposed upper edges have 0.5 mm chamfers. The R1
junctions follow the near-vertical end arcs, never a downward rolled edge.
"""
from __future__ import annotations

import math

from build123d import Align, Axis, Box, BuildSketch, Cone, Cylinder, Plane, Polygon, Pos, Rot, extrude, revolve
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
from holders.registry import ModelSpec, Param, Preset, register

PITCH = 25.0
JOINT_RADIUS = 1.0

PARAMS = tuple(Param(name, 'number', default, min=lo, max=hi, step=step,
                     unit='deg' if 'angle' in name else 'mm', label=label)
    for name, lo, hi, step, default, label in (
        ('lid_diameter', 84, 130, 0.1, 85.3, 'Lid diameter'),
        ('shoulder_height', 6, 25, 0.5, 13, 'Shoulder height'),
        ('shoulder_depth', 2, 10, 0.1, 4.5, 'Shoulder radial depth'),
        ('mount_height', 20, 30, 0.5, 30, 'Mount height'),
        ('lip_end_margin', 1, 5, 0.5, 2, 'Lip end clearance'),
        ('top_chord_offset', 0.5, 2.0, 0.5, 1.5, 'Top chord below circle centre'),
        ('plate_thickness', 5, 8, 0.5, 5, 'Plate thickness'),
        ('tab_thickness', 2, 5, 0.5, 3, 'Tab thickness'),
        ('lip_thickness', 2, 5, 0.5, 3, 'Lip thickness'),
        ('lid_clearance', 0.1, 0.8, 0.05, 0.3, 'Lid clearance'),
        ('pin_base_diameter', 6.9, 7.3, 0.1, 7.1, 'Pin base diameter'),
        ('pin_tip_diameter', 0, 0.8, 0.1, 0, 'Pin tip diameter'),
        ('pin_cone_half_angle', 45, 49, 1, 45, 'Pin cone half-angle'),
        ('bolt_clearance_diameter', 7.5, 8.5, 0.1, 8, 'Bolt clearance diameter'),
        ('countersink_diameter', 10.5, 13, 0.5, 12.5, 'Countersink diameter'),
        ('countersink_angle', 90, 100, 1, 90, 'Countersink included angle'),
        ('bed_chamfer', 0.3, 0.5, 0.1, 0.4, 'Bed edge chamfer'),
    ))


def pin_length_mm(base_diameter, tip_diameter, half_angle_deg):
    """Pure cone-length guard, also testable outside the public Param domain."""
    length = (base_diameter-tip_diameter)/(2*math.tan(math.radians(half_angle_deg)))
    if length < 2.4 - 1e-9:
        raise ValueError('pin length below 2.4')
    if length > 6.0 + 1e-9:
        raise ValueError('pin length above 6.0')
    return length


def dimensions(values: dict) -> dict:
    p = {q.name: q.default for q in PARAMS}
    unknown = values.keys() - p.keys()
    if unknown:
        raise ValueError(f'unknown parameters: {sorted(unknown)}')
    p.update(values)
    for q in PARAMS:
        v = p[q.name]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not q.min <= v <= q.max:
            raise ValueError(f'{q.name} must be in [{q.min}, {q.max}]')
    reach = p['shoulder_depth']-p['lid_clearance']
    if reach < 1.6 - 1e-9:
        raise ValueError('shoulder_depth - lid_clearance must be >= 1.6')
    if p['countersink_diameter'] <= p['bolt_clearance_diameter'] + 2:
        raise ValueError('countersink_diameter must exceed bolt_clearance_diameter + 2')
    seat = (p['countersink_diameter']-p['bolt_clearance_diameter'])/(2*math.tan(math.radians(p['countersink_angle']/2)))
    if p['plate_thickness']-seat < 2.4 - 1e-9:
        raise ValueError('plate_thickness must leave 2.4 mm behind the countersink')
    if p['pin_tip_diameter'] >= p['pin_base_diameter']:
        raise ValueError('pin_tip_diameter must be below pin_base_diameter')
    length = pin_length_mm(p['pin_base_diameter'], p['pin_tip_diameter'], p['pin_cone_half_angle'])
    # Difference from the linear board cavity is linear on each interval,
    # so checking its breakpoints proves clearance over the entire depth.
    for z in (0, 1.5, length):
        pin_d = p['pin_base_diameter']-2*z*math.tan(math.radians(p['pin_cone_half_angle']))
        cavity_d = 7.5-z if z <= 1.5 else 6.0
        if pin_d > cavity_d-0.2 + 1e-9:
            raise ValueError('pin must clear board cavity by 0.1 mm per side')
    inner = p['lid_diameter']/2+p['lid_clearance']
    p.update(radius=inner+p['tab_thickness'], wall_radius=inner,
             lip_radius=inner-reach, reach=reach, seat_depth=seat,
             pin_length=length, lip_bottom=p['plate_thickness']+p['shoulder_height']+p['lid_clearance'])
    b = p['top_chord_offset'] + p['mount_height']
    r = p['radius']
    if b > r - 2*p['tab_thickness'] - 1:
        raise ValueError('bottom chord must leave room: b <= R - 2*tab_thickness - 1')
    if b > r/math.sqrt(2):
        raise ValueError('wall outward lean must be <= 45 degrees: b <= R/sqrt(2)')
    # atan(b / sqrt(R²-b²)) is maximal at the bottom chord.
    p['wall_lean_deg'] = math.degrees(math.atan(b/math.sqrt(r*r-b*b)))
    p['circle_center_z'] = p['top_chord_offset'] + p['mount_height']/2
    lip_depth = min(b, p['lip_radius']/math.sqrt(2)) - p['lip_end_margin']
    p['lip_stop_z'] = p['circle_center_z'] - lip_depth
    p['lip_lean_deg'] = math.degrees(math.asin(lip_depth/p['lip_radius']))
    if p['lip_lean_deg'] > 45:
        raise ValueError('lip inner-arc lean must be <= 45 degrees')
    p['lip_top'] = p['lip_bottom']+p['lip_thickness']
    return p


def pin_centers(values: dict) -> tuple[tuple[float, float, float], ...]:
    dimensions(values)
    return ((-PITCH, 0.0, 0.0), (PITCH, 0.0, 0.0))


def _pin(p):
    return Rot(90, 0, 0) * Cone(p['pin_base_diameter']/2, p['pin_tip_diameter']/2,
                               p['pin_length'], align=(Align.CENTER, Align.CENTER, Align.MIN))


def _center_hole(p):
    shank = Pos(0, -1, 0) * Rot(-90, 0, 0) * Cylinder(
        p['bolt_clearance_diameter']/2, p['plate_thickness']+2,
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    seat = Pos(0, p['plate_thickness']-p['seat_depth'], 0) * Rot(-90, 0, 0) * Cone(
        p['bolt_clearance_diameter']/2, p['countersink_diameter']/2,
        p['seat_depth'], align=(Align.CENTER, Align.CENTER, Align.MIN))
    return shank.fuse(seat)


def holder(**values):
    p = dimensions(values)
    r, ri, rl = p['radius'], p['wall_radius'], p['lip_radius']
    t, h, bottom, top = p['plate_thickness'], p['mount_height'], p['lip_bottom'], p['lip_top']
    # A single revolved section is equivalent to overlapping the wall into
    # the plate by tab_thickness and the lip into the wall by lip_thickness
    # along Y. No coincident-only fusions. R1 inside blends spread the load.
    with BuildSketch(Plane.XY) as section:
        Polygon((0, 0), (r, 0), (r, top), (rl, top), (rl, bottom),
                (ri, bottom), (ri, t), (0, t), align=None)
    part = revolve(section.sketch, axis=Axis.Y)
    part = Pos(0, 0, p['circle_center_z']) * part
    part = (part & Box(2*r+2, 2*top+2, h)).clean()
    # End each lip with a 45-degree ramp into its full-height wall.
    # The ramp starts at lip_stop_z on the wall and rises inward, keeping
    # the entire inner lip arc above its own 45-degree tangent limit.
    stop = p['lip_stop_z']
    ramp_x = math.sqrt(ri*ri - (stop-p['circle_center_z'])**2)
    for sign in (-1, 1):
        with BuildSketch(Plane.XZ) as end_cut:
            Polygon((0, -h), (sign*(r+1), -h),
                    (sign*(r+1), stop+ramp_x-(r+1)),
                    (0, stop+ramp_x), align=None)
        cutter = extrude(end_cut.sketch, amount=2*top, both=True)
        # Preserve the full wall and plate. The extra JOINT_RADIUS behind
        # the lip leaves room for the final junction blend above the ramp.
        cavity = Pos(0, bottom-JOINT_RADIUS, p['circle_center_z']) * Rot(-90, 0, 0) * Cylinder(
            ri, top, align=(Align.CENTER, Align.CENTER, Align.MIN))
        part = (part - (cutter & cavity)).clean()
    # Treat every edge of both chord faces, including the ends of the walls
    # and lips. The bottom takes the configurable bed relief instead of 0.5.
    for z, amount in ((h/2, 0.5), (-h/2, p['bed_chamfer'])):
        face = next(f for f in part.faces() if f.geom_type.name == 'PLANE'
                    and abs(f.center().Z-z) < 1e-6 and abs(f.normal_at().Z) > 0.99)
        # Equal-distance chamfers are NOT 45 degrees where a curved wall
        # meets the chord obliquely. OCP's distance/angle form pins the
        # angle to the planar contact face along the entire curved loop.
        if z > 0:
            part = part.chamfer(amount, None, face.edges())
            continue
        builder = BRepFilletAPI_MakeChamfer(part.wrapped)
        for edge in face.edges():
            builder.AddDA(amount, math.pi/4, edge.wrapped, face.wrapped)
        part = part._make_3d_result(builder.Shape()).clean().fix()
        if not part.is_valid:
            raise ValueError('invalid chord chamfer')
    # Arcs exposed to handling: rear perimeter and both front lip rims.
    arcs = [e for e in part.edges() if e.geom_type.name == 'CIRCLE'
            and (abs(e.center().Y) < 1e-6 or abs(e.center().Y-top) < 1e-6)]
    part = part.chamfer(0.5, None, arcs)
    # Blend after the chord relief: chamfering a pre-existing torus at the
    # 0.5 mm top-offset boundary creates an invalid OCP face.
    joints = [e for e in part.edges() if e.geom_type.name == 'CIRCLE'
              and abs(e.radius-ri) < 1e-6 and
              (abs(e.center().Y-t) < 1e-6 or abs(e.center().Y-bottom) < 1e-6)]
    part = part.fillet(JOINT_RADIUS, joints)
    # Construct one finished half and mirror it: independent spline fits
    # at opposite ends otherwise differ by measurable boolean slivers.
    half = part & Box(r+1, 2*top+2, h+2, align=(Align.MIN, Align.CENTER, Align.CENTER))
    part = half.fuse(half.mirror(Plane.YZ)).clean()
    for x, y, z in pin_centers(values):
        part = part.fuse(Pos(x, y, z) * _pin(p))
    return (part-_center_hole(p)).clean()


SPEC = register(ModelSpec(
    name='holder_cup_lid', build=lambda values: holder(**values),
    title='Cup lid holder (Multibuild)', category_id='multiboard',
    description='Planar circular-segment cradle with mirrored arc tabs, inward lips and loose cone locating pins. Standing print; parametric countersink uses best-guess bolt dimensions pending physical validation.',
    tags=('holder', 'multiboard', 'cup-lid'), params=PARAMS,
    presets=(Preset(id='sippy_cup_85mm', label='Sippy cup (85.3 mm)', values={}),),
    print_orientation=(0.0, 0.0, 1.0),
))
