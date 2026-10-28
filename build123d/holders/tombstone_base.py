"""Hard-ground tombstone base, printed flat on Z=0 (pst-iu0k1 rev 5).

Two drill-in screw stakes clamp a plate to the ground. The separately
flat-printed post sits in a THROUGH mortise, its bottom flush with the bed.
Free-standing +/-X cheeks retain it with a round cross-pin; +/-Y buttresses
take wind on the sign's wide face. Their rise/run is 24/25 (43.83 degrees).
Worst load: 20 N along Y at the top of the 240 x 300 sign, bending about X.
The pin is for lift-out only, not this moment. PLA/PCTG, PCTG outdoors.

Screw-stake dimensions are provisional [U], authorized by mayor rev 5:
12.7 mm shaft, ROUND 25 x 4 mm head, two at 160 mm spacing. Set Params to
the actual hardware. Mortise clearance is the existing signs.JOINT_CLEARANCE.
The counterbore bearing floor, mortise and pin surfaces are functional.
"""
from __future__ import annotations

from build123d import (Box, Circle, Plane, Polygon, Pos, Rectangle, RectangleRounded,
                       Rot, chamfer, extrude, fillet, loft)
from holders import signs
from holders.printer import BED_X, BED_Y
from holders.registry import ModelSpec, Param, Preset, register
from holders.tombstone_ground import (CHEEK_H, CHEEK_MARGIN, CHEEK_T,
                                      DEFAULT_PLATE_T, GUSSET_RUN)
from scripts.thumbnail import PlaneSpec

CORNER_R = 4.0
EDGE_CHAMFER = 0.4
STAKE_MARGIN = 8.0


def mortise_size(v):
    return v['width'] + 2 * signs.JOINT_CLEARANCE, v['thickness'] + 2 * signs.JOINT_CLEARANCE


def stake_xs(v):
    # One stake is offset, never in the central mortise. Two prevent pivoting.
    return (-v['stake_spacing'] / 2, v['stake_spacing'] / 2) if v['stake_count'] == '2' else (v['stake_spacing'] / 2,)


def validate(v):
    mw, md = mortise_size(v)
    if v['plate_t'] - v['stake_head_t'] < 2.0 - 1e-9:
        raise ValueError('counterbore floor needs plate_t - stake_head_t >= 2 mm')
    if v['stake_head_d'] + 1 - (v['stake_d'] + 0.8) < 4:
        raise ValueError('stake head must leave >= 2 mm radial bearing around the shaft bore')
    r = (v['stake_head_d'] + 1) / 2
    if v['stake_spacing'] / 2 - r - (mw / 2 + CHEEK_T) < STAKE_MARGIN:
        raise ValueError('stake holes must clear the mortise, cheeks and gussets by >= 8 mm')
    if v['plate_w'] / 2 - v['stake_spacing'] / 2 - r < STAKE_MARGIN:
        raise ValueError('stake counterbores need >= 8 mm to the plate edge')
    if v['plate_d'] / 2 - (md / 2 + GUSSET_RUN) < STAKE_MARGIN:
        raise ValueError('gusset toes need >= 8 mm to the plate edge')
    if v['plate_w'] > BED_X or v['plate_d'] > BED_Y:
        raise ValueError('plate exceeds the single-nozzle bed')


def build(v):
    validate(v)
    mw, md = mortise_size(v)
    pt, top = v['plate_t'], v['plate_t'] + CHEEK_H
    plate = extrude(RectangleRounded(v['plate_w'], v['plate_d'], CORNER_R), pt)
    # Keep a continuous overlapping cradle before cutting the through mortise.
    # Cheeks extend 3.2 beyond the narrow faces; buttresses span both cheeks
    # (5 mm overlap along X) and sink 2 mm into the plate. Their outer X
    # faces are continuous, permitting a robust root fillet.
    out = plate + Pos(0, 0, (pt - 2 + top) / 2) * Box(mw + 2 * CHEEK_T, md + 2 * CHEEK_MARGIN, CHEEK_H + 2)
    for side in (-1, 1):
        section = Plane.YZ * Polygon((md / 2, pt - 2),
                                     (md / 2 + GUSSET_RUN, pt - 2),
                                     (md / 2 + GUSSET_RUN, pt),
                                     (md / 2, top), align=None)
        wedge = extrude(section, mw / 2 + CHEEK_T, both=True)
        out += wedge if side == 1 else Rot(0, 0, 180) * wedge
    # A 1 mm upward-facing concave root fillet blends the fused bodies.
    roots = [e for e in out.edges() if all(abs(v.Z - pt) < 1e-6 for v in e.vertices())
             and abs(e.center().X) < mw / 2 + CHEEK_T + 2
             and abs(e.center().Y) < md / 2 + GUSSET_RUN + 2]
    out = fillet(roots, 1.0)
    # Functional mortise surfaces are cut after easing the outside edges.
    # Ease the exposed rims including the plate bed. The slope edges receive
    # the same 0.4 mm relief; no downward-facing round is introduced.
    edges = []
    for edge in out.edges():
        faces = [f for f in out.faces() if any(e.is_same(edge) for e in f.edges())]
        if len(faces) == 2 and faces[0].normal_at(edge.center()).dot(faces[1].normal_at(edge.center())) < 0.999:
            edges.append(edge)
    out = chamfer(edges, EDGE_CHAMFER)
    mortise = extrude(Pos(0, 0, -1) * Rectangle(mw, md), top + 2)
    out -= mortise
    # Explicit 45-degree lead-ins are robust where the upper rim meets the
    # buttresses (a BREP edge chamfer at that multi-edge vertex is ambiguous).
    for z0, z1, d0, d1 in ((0, EDGE_CHAMFER, 2 * EDGE_CHAMFER, 0),
                           (top - EDGE_CHAMFER, top, 0, 2 * EDGE_CHAMFER)):
        out -= loft([Pos(0, 0, z0) * Rectangle(mw + d0, md + d0),
                     Pos(0, 0, z1) * Rectangle(mw + d1, md + d1)])
    for x in stake_xs(v):
        bore = extrude(Pos(x, 0, -1) * Circle((v['stake_d'] + 0.8) / 2), pt + 2)
        counter = extrude(Pos(x, 0, pt - v['stake_head_t']) * Circle((v['stake_head_d'] + 1) / 2), v['stake_head_t'] + 1)
        out -= bore + counter
    # Bore bed rims, counterbore mouths and shaft entry rims are 45 degrees.
    rings = [e for e in out.edges() if e.geom_type.name == 'CIRCLE'
             and any(abs(e.center().X - x) < (v['stake_head_d'] + 1) / 2 + 0.01 for x in stake_xs(v))
             and any(abs(e.radius - radius) < 1e-6 for radius in
                     ((v['stake_d'] + 0.8) / 2, (v['stake_head_d'] + 1) / 2))]
    # The counterbore floor's outer corner is the head-bearing datum.
    rings = [e for e in rings if not (abs(e.radius - (v['stake_head_d'] + 1) / 2) < 1e-6
                                     and abs(e.center().Z - (pt - v['stake_head_t'])) < 1e-6)]
    out = chamfer(rings, EDGE_CHAMFER)
    out -= extrude(signs.pin_profile(0, pt + CHEEK_H / 2), mw / 2 + CHEEK_T + 1, both=True)
    return out


def audit_exclusions(v):
    mw, _ = mortise_size(v)
    z = v['plate_t'] + CHEEK_H / 2 + signs.PIN_D / 2
    return [(a - 0.001, -signs.PIN_D / 2, z - 0.001,
             b + 0.001, signs.PIN_D / 2, z + 0.001)
            for a, b in ((-mw / 2 - CHEEK_T, -mw / 2), (mw / 2, mw / 2 + CHEEK_T))]


PARAMS = (
    Param('plate_w', 'number', 240.0, label='Plate width', group='Plate', unit='mm', min=180.0, max=BED_X, step=1.0),
    Param('plate_d', 'number', 120.0, label='Plate depth', group='Plate', unit='mm', min=80.0, max=200.0, step=1.0),
    Param('plate_t', 'number', DEFAULT_PLATE_T, label='Plate thickness', group='Plate', unit='mm', min=6.0, max=12.0, step=1.0),
    Param('stake_count', 'enum', '2', label='Screw stakes', group='Hardware', choices=('1', '2'), description='Two stakes prevent pivoting. One uses the right-hand hole.'),
    Param('stake_spacing', 'number', 160.0, label='Stake spacing', group='Hardware', unit='mm', min=100.0, max=240.0, step=1.0),
    Param('stake_d', 'number', 12.7, label='Shaft diameter', group='Hardware', unit='mm', min=6.0, max=25.0, step=0.1),
    Param('stake_head_d', 'number', 25.0, label='Round head diameter', group='Hardware', unit='mm', min=16.0, max=45.0, step=0.1),
    Param('stake_head_t', 'number', 4.0, label='Head thickness', group='Hardware', unit='mm', min=2.0, max=10.0, step=0.1),
    Param('width', 'number', 40.0, label='Post width', group='Post', unit='mm', min=25.0, max=60.0, step=1.0),
    Param('thickness', 'number', 8.0, label='Post thickness', group='Post', unit='mm', min=6.0, max=10.0, step=0.2),
)
DEFAULTS = {p.name: p.default for p in PARAMS}
SPEC = register(ModelSpec(
    name='holder_tombstone_base', build=build, title='Tombstone hard-ground base',
    description='Base plate for two drill-in screw stakes and the flat-printed tombstone post. Set the round screw-stake head and shaft dimensions to your hardware.',
    category_id='household', tags=('sign',), print_orientation=(0, 0, 1),
    params=PARAMS, presets=(Preset('default', 'Two screw stakes (8 mm post)', {}),),
    review_sections=(PlaneSpec((0, 0, DEFAULT_PLATE_T + CHEEK_H / 2), (0, 1, 0), 'retaining pin through both cheeks'),
                     PlaneSpec((0, 0, DEFAULT_PLATE_T), (1, 0, 0), 'wide-face buttresses and through mortise')),
))
