"""Bench lip clip, step 1: the fit-test coupon (pst-czxuk.1).

A C-clip that hooks the lip of a cast faux-wood bench top (slab 38 mm thick,
re-measured 2026-10-29 after the 2026-10-28 tape read 2 in = 50.8 mm; lip
1/2 in = 12.7 mm beyond the end block; docs/bench-lip-clip.md). The coupon
only dials in the grip; step 2 extrudes the same lip_clip_profile() longer
and adds the 1/4"-20 insert boss.

Model frame = print frame: the profile is the footprint in XY, extruded +Z
by coupon_length, so the part is a prism and prints as modelled. X runs
from the spine's outer face (x=0) toward the slab; +Y is up IN USE: the
bottom hook (y 0..wall) reaches under the overhang, the spine climbs the
slab's edge face, the top jaw (y wall+inner height..) rests on the slab top.
Z runs along the lip. No downward faces except the debossed label's recess
ceilings (audit_exclusions), no bridges.

Worst load: prying the jaws apart (slab pushed against either jaw tip)
bends the two jaw roots in the profile plane, i.e. along the layers, in PLA
or PCTG. Both roots carry an R >= 1 inside fillet; outer vertical edges
R 1, top edges R 1 fillet, bed edges a 45 degree chamfer. Functional
(sharp-by-spec) faces: the three inner bearing faces and the lead-ins.
The label is the signed height_clearance by default, debossed INLAY_DEPTH
into the spine's outer face, baseline along Z (horizontal in use).
"""
from __future__ import annotations

import math

from build123d import Axis, Box, BuildSketch, Plane, Polygon, Pos, Sketch, chamfer, extrude, fillet

from holders.printer import BED_X, BED_Y, BED_Z
from holders.registry import ModelSpec, Param, Preset, register
from labels.constants import INLAY_DEPTH, MAX_TEXT_LENGTH, STROKE_FLOOR_INLAID, TEXT_CHARSET
from labels.label_text import FLOOR_MARGIN, text_measures, text_sketch
from scripts.thumbnail import PlaneSpec

OUTER_RADIUS = 1.0    # vertical outer edges, design-guidelines §2 (R 1-2)
TOP_RADIUS = 1.0      # top (upward) edges, §2 (R >= 1)
LABEL_END_MARGIN = 2.0  # ink to each coupon end: width <= coupon_length - 4

PARAMS = (
    Param('slab_thickness', 'number', 38.0, min=31, max=70, step=0.1, unit='mm',
          group='Bench', label='Slab thickness'),
    Param('height_clearance', 'number', 0.8, min=-0.5, max=4.0, step=0.1, unit='mm',
          group='Fit', label='Height clearance', filename=True),
    Param('hook_depth', 'number', 11.5, min=6, max=20, step=0.5, unit='mm',
          group='Bench', label='Hook depth under the lip'),
    Param('top_reach', 'number', 30, min=15, max=60, step=1, unit='mm',
          group='Shape', label='Top jaw reach'),
    Param('wall', 'number', 5, min=3, max=8, step=0.5, unit='mm',
          group='Shape', label='Wall thickness'),
    Param('edge_gap', 'number', 0.5, min=0, max=2, step=0.1, unit='mm',
          group='Fit', label='Edge-face clearance'),
    Param('coupon_length', 'number', 25, min=15, max=60, step=1, unit='mm',
          group='Shape', label='Coupon length'),
    Param('lead_in', 'number', 1.5, min=0, max=3, step=0.5, unit='mm',
          group='Fit', label='Jaw-tip lead-in'),
    Param('jaw_root_radius', 'number', 1.0, min=1.0, max=2.0, step=0.5, unit='mm',
          group='Shape', label='Jaw root fillet'),
    Param('bed_chamfer', 'number', 0.4, min=0.3, max=0.5, step=0.1, unit='mm',
          group='Shape', label='Bed chamfer'),
    Param('label_text', 'string', '', group='Label', label='Label text',
          max_length=MAX_TEXT_LENGTH, charset=TEXT_CHARSET,
          description='Blank = the signed height clearance, e.g. +0.8'),
    Param('text_size', 'number', 9.0, min=8.1, max=12, step=0.1, unit='mm',
          group='Label', label='Text size'),
)


def dimensions(values: dict) -> dict:
    """Resolved values plus derived sizes; ValueError names the parameter."""
    p = {q.name: q.default for q in PARAMS}
    unknown = values.keys() - p.keys()
    if unknown:
        raise ValueError(f'unknown parameters: {sorted(unknown)}')
    p.update(values)
    for q in PARAMS:
        v = p[q.name]
        if q.kind == 'string':
            if not isinstance(v, str) or len(v) > q.max_length:
                raise ValueError(f'{q.name} must be a string of at most {q.max_length} characters')
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not q.min <= v <= q.max:
            raise ValueError(f'{q.name} must be in [{q.min}, {q.max}]')
    if p['hook_depth'] - p['lead_in'] < 3 - 1e-9:
        raise ValueError('hook_depth - lead_in must be >= 3 (flat bearing under the lip)')
    if p['wall'] - p['lead_in'] < 1.6 - 1e-9:
        raise ValueError('wall - lead_in must be >= 1.6 (the jaw tip stays load-bearing)')
    if p['top_reach'] < p['hook_depth']:
        raise ValueError('top_reach must be >= hook_depth')
    inner = p['slab_thickness'] + p['height_clearance']
    if inner < 30 - 1e-9:
        raise ValueError('slab_thickness + height_clearance must be >= 30')
    w = p['wall']
    p.update(inner_height=inner, height=inner + 2*w, edge_x=w + p['edge_gap'])
    p.update(hook_x=p['edge_x'] + p['hook_depth'], top_x=p['edge_x'] + p['top_reach'])
    footprint = (w + max(p['top_reach'], p['hook_depth']) + p['edge_gap'], p['height'])
    if footprint[0] > BED_X or footprint[1] > BED_Y:
        raise ValueError(f'footprint {footprint[0]:g} x {footprint[1]:g} mm exceeds the '
                         f'{BED_X:g} x {BED_Y:g} mm bed; reduce top_reach or slab_thickness')
    if p['coupon_length'] > BED_Z:
        raise ValueError(f'coupon_length exceeds the {BED_Z:g} mm build height')
    p['footprint'] = footprint
    label = p['label_text'] if p['label_text'].strip() else f'{p["height_clearance"]:+.1f}'
    stroke = text_measures(label, p['text_size'])[0]
    floor = STROKE_FLOOR_INLAID + FLOOR_MARGIN
    if stroke < floor:
        raise ValueError(f'label_text {label!r} at text_size {p["text_size"]:g} has a {stroke:.3f} mm '
                         f'stroke, under the {floor:g} mm floor; use a larger text_size')
    width = text_sketch(label, p['text_size']).bounding_box().size.X
    room = p['coupon_length'] - 2*LABEL_END_MARGIN
    if width > room + 1e-9:
        raise ValueError(f'label_text {label!r} at text_size {p["text_size"]:g} is {width:.2f} mm wide; '
                         f'coupon_length {p["coupon_length"]:g} leaves {room:g} mm')
    p.update(label=label, label_stroke=stroke, label_width=width)
    return p


def lip_clip_profile(p: dict) -> Sketch:
    """The C footprint (XY) with its in-plane edge treatment.

    Inside root fillets jaw_root_radius, 45 degree lead_in on both jaw tips'
    inner corners, OUTER_RADIUS on the four outer corners. Step 2 reuses it.
    """
    w, h, ih = p['wall'], p['height'], p['inner_height']
    hx, tx = p['hook_x'], p['top_x']
    pts = ((0, 0), (hx, 0), (hx, w), (w, w), (w, w + ih), (tx, w + ih), (tx, h), (0, h))
    with BuildSketch() as s:
        Polygon(*pts, align=None)

        def at(*corners):
            return [v for v in s.vertices() for x, y in corners
                    if abs(v.X - x) < 1e-6 and abs(v.Y - y) < 1e-6]
        fillet(at((w, w), (w, w + ih)), p['jaw_root_radius'])
        if p['lead_in'] > 0:
            chamfer(at((hx, w), (tx, w + ih)), p['lead_in'])
        fillet(at((0, 0), (0, h), (hx, 0), (tx, h)), OUTER_RADIUS)
    return s.sketch


def _blank(p: dict):
    part = extrude(lip_clip_profile(p), p['coupon_length'])
    top = part.faces().sort_by(Axis.Z)[-1]
    part = part.fillet(TOP_RADIUS, top.edges())
    bed = part.faces().sort_by(Axis.Z)[0]
    return part.chamfer(p['bed_chamfer'], None, bed.edges())


def label_cutter(p: dict):
    """The glyph recess: x 0..INLAY_DEPTH into the spine, centred on its outer face.

    Read from -X with +Y up: the sketch's X (reading direction) maps to +Z.
    """
    sketch = text_sketch(p['label'], p['text_size'])
    bb = sketch.bounding_box()
    sketch = Pos(-bb.center().X, -bb.center().Y) * sketch
    face = Plane(origin=(0, p['height']/2, p['coupon_length']/2), x_dir=(0, 0, 1), z_dir=(-1, 0, 0))
    return extrude(face * sketch, -INLAY_DEPTH)


def holder(**values):
    p = dimensions(values)
    return (_blank(p) - label_cutter(p)).clean()


def audit_exclusions(values: dict) -> list:
    """label-recess: the 0..INLAY_DEPTH slab over the ink on the spine face.

    The glyph recess ceilings face down in the print pose; each is a flat
    bridge no wider than a stroke (the underware_text_label family).
    """
    p = dimensions(values)
    bb = label_cutter(p).bounding_box()
    return [Pos(INLAY_DEPTH/2, bb.center().Y, bb.center().Z)
            * Box(INLAY_DEPTH + 0.002, bb.size.Y + 0.02, bb.size.Z + 0.02)]


FIT_KIT = (0.3, 0.8, 1.3, 1.8, 2.3)

SPEC = register(ModelSpec(
    name='holder_bench_lip_clip', build=lambda values: holder(**values),
    title='Bench lip clip (fit coupon)', category_id='household',
    description=('Fit-test coupon for a clip that hooks a bench top\'s lip: top jaw on the slab, '
                 'spine down its edge, hook under the overhang. The five-coupon fit kit varies the '
                 'vertical clearance and debosses it on the spine; print them, seat each on the '
                 'lip and keep the snug one. Prints on its side, no supports.'),
    tags=('holder', 'fit-test'), params=PARAMS,
    presets=tuple(Preset(id=f'fit-plus-{c:.1f}'.replace('.', '-'), label=f'Fit kit +{c:.1f} mm',
                         values={'height_clearance': c}) for c in FIT_KIT),
    # The profile plane: the C itself, clear of the label (it reads the spine face).
    review_sections=(PlaneSpec((0, 0, 12.5), (0, 0, 1), 'profile at Z = coupon_length / 2'),),
))
