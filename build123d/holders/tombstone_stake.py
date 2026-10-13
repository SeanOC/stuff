"""Tombstone stake (epic pst-tl4ac, S2 pst-tl4ac.2): the ground stake for the sign.

One flat blade, printed flat (thickness along Z, Z = 0 the bed face). In
plan (X across, Y up the stake): a SHAFT `width` wide ending in a 45-degree
point at Y = 0 (45 degrees INCLUDED, 22.5 per flank), a HEAD `head_width` x
`head_height` joined to the shaft by 45-degree shoulders, and two TENONS
rising from the head's top edge at X = signs.POCKET_XS. `length` is the
whole printed length, tip to tenon ends, so length <= 320 is the bed bound.

The joint numbers come from holders/signs.py, which the sign imports too:
each tenon is signs.tenon_w() x signs.tenon_len() x signs.tenon_t(thickness)
(7.6 x 34.6 x 3.2 at thickness 6). `thickness` is the stake blade's and
must equal the sign's: the tenon height is the contract's formula of it.
The tenon is FLUSH WITH THE BED FACE (stake Z in [0, tenon_t]), never
centred in the blade, because a mid-thickness tenon printed flat would be a
7.6 x 34.6 mm flat ceiling. Assembled, sign Z = stake Z + SKIN +
JOINT_CLEARANCE (1.4): the tenon sits centred in its pocket, 0.2 clear of
every wall (0.4 at the pocket end), and the sign rides 1.4 mm off the
stake's mid-plane, a 1.4 mm step at each face of the joint. The stake's
head-top edge bears on the sign's bottom edge.

retention='pin' drills the sign's cross-hole axis (signs.PIN_AXIS, Y =
PIN_FROM_BOTTOM above the head top, the tenon's mid-height) through each
tenon with signs.pin_profile: the plate hole and the tenon hole are one
axis by construction. The teardrop's flat roof faces +Z in the print frame,
as in the sign. It needs thickness >= 7.8 (signs.check_pin_thickness).

cross_bar=True adds a second blade, `width` wide x `cross_length` long and
the same thickness, half-lapped across the shaft LAP_DROP below the
shoulders so the two interlock flush on both faces. Both blades print flat
in this one print frame (a two-solid compound, the bar beside the stake),
each with its lap notch facing UP, so neither notch is a ceiling; the bar
is turned over to assemble.

Edges: both rims carry a 0.4 chamfer (on the bed, elephant's foot); the
tenons' bed rims carry it too, so elephant's foot cannot eat the 0.2 joint
clearance. Plan corners are rounded: 3 mm at the shoulders and the bar,
min(3, head_width / 2 - 43.8) at the head top so the rounding never reaches
a tenon root (square at head_width 87.6, where the tenon's outer face
continues the head's side). The concave shoulder corners are filleted
SHOULDER_R in plan, a blend on the stress path. Tenon and lap faces are
mating edges and stay sharp; the tip is sharp to enter the ground.

Worst-case load: wind on the face of the default 240 x 300 sign, pushing
along Z. The sign's moment about X crosses the joint in the two tenons,
spreads through the head and the 45-degree shoulders into the shaft, and
is resisted by the soil along the buried shaft. The blade prints flat, so
that bending stress runs along the layers. At thickness 6 the tenons (7.6
x 3.2 each) are the weakest section; use 8 mm (tenons 5.2) for an exposed
site. PLA or PCTG; PCTG for a stake left outdoors.
"""
from __future__ import annotations

import math

from build123d import (Axis, Box, Compound, Part, Polygon, Pos, Rectangle, Rot, chamfer,
                       extrude, fillet)
from holders import signs
from holders.printer import BED_Y
from holders.registry import ModelSpec, Param, Preset, register
from scripts.thumbnail import PlaneSpec

EDGE_CHAMFER = 0.4          # both rims and the tenons' bed rims, as the sign
CORNER_R = signs.CORNER_R   # plan rounding of convex corners (3)
SHOULDER_R = 5.0            # plan fillet of the concave shoulder-to-shaft corners
POINT_DEG = 45.0            # included angle of the shaft's point
TENON_OVERLAP = 1.0         # tenon root reaches this far into the head
LAP_DROP = 50.0             # lap centre below the shoulders' bottom
LAP_CLEARANCE = signs.JOINT_CLEARANCE  # each side of each lap notch, in plan
BAR_GAP = 10.0              # bar beside the stake on the bed
MIN_STRAIGHT = CORNER_R + SHOULDER_R  # straight shaft between the point and shoulder fillets
MAX_LENGTH = BED_Y          # holders.printer; the blade prints along Y
TENON_OUTER = signs.POCKET_OFFSET + signs.tenon_w() / 2  # 43.8
MIN_HEAD_WIDTH = round(2 * TENON_OUTER, 6)                # 87.6


def taper_run(width: float) -> float:
    """Length of the point: half the width over tan(half the included angle)."""
    return width / 2 / math.tan(math.radians(POINT_DEG / 2))


def head_top(values: dict) -> float:
    """Y of the head's top edge, the bearing face under the sign."""
    return values['length'] - signs.tenon_len()


def shoulder_bottom(values: dict) -> float:
    """Y where the shoulders meet the shaft (the shaft's straight top)."""
    return (head_top(values) - values['head_height']
            - (values['head_width'] - values['width']) / 2)


def lap_centre(values: dict) -> float:
    return shoulder_bottom(values) - LAP_DROP


def lap_span(values: dict) -> float:
    """The shaft notch's length along Y: the bar's width plus clearance."""
    return values['width'] + 2 * LAP_CLEARANCE


def min_length(values: dict) -> float:
    """Shortest length (0.1 mm up) whose shaft holds the point, MIN_STRAIGHT of
    straight shaft for the plan fillets, and with cross_bar the lap clear of the
    point's fillet."""
    above = signs.tenon_len() + values['head_height'] + (values['head_width'] - values['width']) / 2
    need = taper_run(values['width']) + MIN_STRAIGHT
    if values['cross_bar']:
        need = max(need, taper_run(values['width']) + CORNER_R + LAP_DROP + lap_span(values) / 2)
    return round(above + need + 0.05, 1)


def validate(values: dict) -> None:
    """Cross-param guards; each ValueError names the bound."""
    hw = values['head_width']
    if hw < MIN_HEAD_WIDTH - 1e-9:
        raise ValueError(
            f'head_width {hw:g} mm < {MIN_HEAD_WIDTH:g} mm: the tenons at '
            f'+-{signs.POCKET_OFFSET:g} mm need head_width >= 2 x '
            f'({signs.POCKET_OFFSET:g} + {signs.tenon_w() / 2:g})')
    if values['retention'] == 'pin':
        signs.check_pin_thickness(values['thickness'])
    run, top = taper_run(values['width']), shoulder_bottom(values)
    if top - run < MIN_STRAIGHT - 1e-9:
        raise ValueError(
            f'length {values["length"]:g} mm leaves a {top:.1f} mm shaft below the shoulders, '
            f'under the {run:.1f} mm point + {MIN_STRAIGHT:g} mm straight: the taper would '
            f'reach the head; length must be >= {min_length(values):g} mm')
    if values['cross_bar'] and lap_centre(values) - lap_span(values) / 2 < run + CORNER_R - 1e-9:
        raise ValueError(
            f'length {values["length"]:g} mm puts the cross-bar lap ({LAP_DROP:g} mm below '
            f'the shoulders) into the {run:.1f} mm point; with cross_bar length must be '
            f'>= {min_length(values):g} mm')


def outline(values: dict):
    """The stake in plan: point at Y = 0, head top at head_top(values)."""
    w, hw, hh = values['width'], values['head_width'], values['head_height']
    run, ys, yh = taper_run(w), shoulder_bottom(values), head_top(values)
    yb = yh - hh  # head bottom = shoulders' top
    right = [(w / 2, run), (w / 2, ys), (hw / 2, yb), (hw / 2, yh)]
    pts = [(0, 0)] + right + [(-x, y) for x, y in reversed(right)]
    shape = Polygon(*pts, align=None)
    # Fillet one corner row at a time (Y picks the row; the tip is left sharp).
    for y, r in ((run, CORNER_R), (ys, SHOULDER_R), (yb, CORNER_R),
                 (yh, min(CORNER_R, hw / 2 - TENON_OUTER))):
        if r > 1e-6:
            shape = fillet([v for v in shape.vertices() if abs(v.Y - y) < 1e-6], r)
    return shape


def _rim_chamfered(sketch, t: float) -> Part:
    blank = extrude(sketch, t)
    rims = blank.faces().sort_by(Axis.Z)
    return chamfer(rims[0].edges() + rims[-1].edges(), EDGE_CHAMFER)


def tenon(x: float, values: dict) -> Part:
    """One tenon, flush with the bed face, its bed rim chamfered (not the root)."""
    tt, yh = signs.tenon_t(values['thickness']), head_top(values)
    y0, y1 = yh - TENON_OVERLAP, yh + signs.tenon_len()
    box = Pos(x, (y0 + y1) / 2, tt / 2) * Box(signs.tenon_w(), y1 - y0, tt)
    bed = box.faces().sort_by(Axis.Z)[0]
    return chamfer([e for e in bed.edges() if e.center().Y > y0 + 1e-6], EDGE_CHAMFER)


def stake(values: dict) -> Part:
    """The stake blade alone, in the print frame."""
    t = values['thickness']
    out = _rim_chamfered(outline(values), t)
    for x in signs.POCKET_XS:
        out += tenon(x, values)
    if values['retention'] == 'pin':
        section = signs.pin_profile(head_top(values) + signs.PIN_FROM_BOTTOM,
                                    signs.tenon_t(t) / 2)
        out -= extrude(section, values['head_width'] / 2 + 1, both=True)
    if values['cross_bar']:
        out -= _upper_half(values['width'] + 2, lap_span(values), t, lap_centre(values))
    return out


def _upper_half(dx: float, dy: float, t: float, y: float = 0.0) -> Part:
    """A notch cutter: dx x dy in plan at (0, y), from Z = t / 2 up past the top face."""
    return Pos(0, y, 3 * t / 4 + 0.5) * Box(dx, dy, t / 2 + 1)


def cross_bar(values: dict) -> Part:
    """The cross-bar laid along X centred on the origin, its lap notch on top (+Z)."""
    w, t, cl = values['width'], values['thickness'], values['cross_length']
    bar = _rim_chamfered(fillet(Rectangle(cl, w).vertices(), CORNER_R), t)
    return bar - _upper_half(w + 2 * LAP_CLEARANCE, w + 2, t)


def bar_placement(values: dict):
    """Where the bar lies on the bed: along Y, beside the stake's +X side."""
    x = values['head_width'] / 2 + BAR_GAP + values['width'] / 2
    return Pos(x, values['length'] / 2, 0) * Rot(0, 0, 90)


def build(values: dict) -> Part:
    validate(values)
    blade = stake(values)
    if not values['cross_bar']:
        return blade
    bar = bar_placement(values) * cross_bar(values)
    return Part(Compound(blade.solids() + bar.solids()).wrapped)


def audit_exclusions(values: dict) -> list[tuple[float, ...]]:
    """Approved regions, as thin exact boxes: with a pin, each tenon's pin-hole
    roof (signs.pin_profile's 1.33 mm flat, the sign's own exclusion). No
    other preset needs one. The tests measure the span before excluding it.
    Approved by the mayor (pst-tl4ac.2, 2026-10-13): option A, mirror S1."""
    if values['retention'] != 'pin':
        return []
    z = signs.tenon_t(values['thickness']) / 2 + signs.PIN_D / 2
    y, half = head_top(values) + signs.PIN_FROM_BOTTOM, signs.PIN_D / 2
    return [(x - signs.tenon_w() / 2 - 0.001, y - half, z - 0.001,
             x + signs.tenon_w() / 2 + 0.001, y + half, z + 0.001) for x in signs.POCKET_XS]


PARAMS = (
    Param('width', 'number', 40.0, label='Shaft width', group='Stake', unit='mm',
          min=25.0, max=60.0, step=1.0),
    Param('length', 'number', 300.0, label='Length', group='Stake', unit='mm',
          min=150.0, max=MAX_LENGTH, step=1.0,
          description='Tip to tenon ends: the whole printed length.'),
    Param('thickness', 'number', 6.0, label='Thickness', group='Stake', unit='mm',
          min=5.0, max=10.0, step=0.2,
          description="Match the sign's thickness: the tenons are sized from it."),
    Param('head_width', 'number', 90.0, label='Head width', group='Head', unit='mm',
          min=MIN_HEAD_WIDTH, max=140.0, step=0.5),
    Param('head_height', 'number', 30.0, label='Head height', group='Head', unit='mm',
          min=20.0, max=60.0, step=1.0),
    Param('retention', 'enum', 'none', label='Retention', group='Joint',
          choices=('none', 'pin'),
          description="'pin' drills the sign's 3.2 mm cross-hole through each tenon; "
                      'needs thickness >= 7.8 mm.'),
    Param('cross_bar', 'boolean', False, label='Cross-bar', group='Cross-bar'),
    Param('cross_length', 'number', 200.0, label='Cross-bar length', group='Cross-bar',
          unit='mm', min=100.0, max=MAX_LENGTH, step=1.0),
)

DEFAULTS = {p.name: p.default for p in PARAMS}

SPEC = register(ModelSpec(
    name='holder_tombstone_stake',
    build=build,
    title='Tombstone stake',
    description=('Ground stake for the tombstone sign: a flat blade with a 45-degree '
                 'point and a flared head whose two tenons fit the sign\'s pockets; '
                 'optional cross-pin and half-lapped cross-bar.'),
    category_id='household',
    tags=('sign',),
    print_orientation=(0, 0, 1),  # flat, the tenon face on the bed
    params=PARAMS,
    presets=(
        Preset('default', 'Stake (6 mm)', {}),
        Preset('long', 'Long (320 mm)', {'length': 320.0}),
        Preset('cross-bar', 'With cross-bar', {'cross_bar': True}),
        Preset('pinned', 'Pinned (8 mm)', {'thickness': 8.0, 'retention': 'pin'}),
    ),
    # Joint plane first: the review sheet goldens sections[0] (the tenon cut).
    review_sections=(
        PlaneSpec((signs.POCKET_OFFSET, head_top(DEFAULTS) + signs.tenon_len() / 2,
                   DEFAULTS['thickness'] / 2), (1, 0, 0), 'tenon at X = +40'),
        PlaneSpec((0, (taper_run(DEFAULTS['width']) + shoulder_bottom(DEFAULTS)) / 2,
                   DEFAULTS['thickness'] / 2), (0, 1, 0), 'shaft'),
    ),
))
