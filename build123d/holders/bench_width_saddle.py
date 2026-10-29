"""Bench width saddle, step 1b: the width fit-test coupon (pst-czxuk.3).

An inverted-U saddle that spans the cast faux-wood bench top across its
width (Sean's tape reading 2026-10-29: 310 mm between the two long edges;
docs/bench-width-saddle.md). A flat bar rests on the slab top and a short
cheek hangs down each long edge face, so the coupon locates on the width the
way the lip coupon (bench_lip_clip.py) locates on the thickness.

Model frame = print frame: the profile is the footprint in XY, extruded +Z
by coupon_length, so the part is a prism and prints on its side as modelled.
X runs across the bench width from one cheek's outer face (x=0) to the
other's; +Y is up IN USE: the cheek tips at y=0, the bar underside on the
slab top at y=cheek_depth. Z runs along the bench. No downward faces except
the debossed label's recess ceilings (audit_exclusions), no bridges.

Worst load: prying the cheeks apart (the slab's edge faces pushing either
cheek tip outward) bends the two cheek roots in the profile plane, i.e.
along the layers, in PLA or PCTG. Both roots carry an R >= 1 inside fillet;
outer vertical edges R 1, top edges R 1 fillet, bed edges a 45 degree
chamfer. Functional (sharp-by-spec) faces: the bar underside, the two inner
cheek faces and the lead-ins.
The label is the signed width_clearance by default, debossed INLAY_DEPTH
into the bar's outer face, baseline along X (the bench width): coupon_length
then only has to hold the glyph height, not the label's width.
"""
from __future__ import annotations

import math

from build123d import Axis, Box, BuildSketch, Plane, Polygon, Pos, Sketch, chamfer, extrude, fillet

from holders.bench_lip_clip import LABEL_END_MARGIN, OUTER_RADIUS, TOP_RADIUS
from holders.printer import BED_X, BED_Y, BED_Z
from holders.registry import ModelSpec, Param, Preset, register
from labels.constants import INLAY_DEPTH, MAX_TEXT_LENGTH, STROKE_FLOOR_INLAID, TEXT_CHARSET
from labels.label_text import FLOOR_MARGIN, text_measures, text_sketch
from scripts.thumbnail import PlaneSpec

PARAMS = (
    Param('bench_width', 'number', 310, min=250, max=315, step=0.5, unit='mm',
          group='Bench', label='Bench top width'),
    Param('width_clearance', 'number', 1.0, min=-2.0, max=4.0, step=0.1, unit='mm',
          group='Fit', label='Width clearance', filename=True),
    Param('cheek_depth', 'number', 11.5, min=6, max=20, step=0.5, unit='mm',
          group='Bench', label='Cheek depth down the edge'),
    Param('wall', 'number', 4, min=3, max=6, step=0.5, unit='mm',
          group='Shape', label='Wall thickness'),
    Param('coupon_length', 'number', 15, min=15, max=60, step=1, unit='mm',
          group='Shape', label='Coupon length'),
    Param('lead_in', 'number', 1.5, min=0, max=3, step=0.5, unit='mm',
          group='Fit', label='Cheek-tip lead-in'),
    Param('jaw_root_radius', 'number', 1.0, min=1.0, max=2.0, step=0.5, unit='mm',
          group='Shape', label='Cheek root fillet'),
    Param('bed_chamfer', 'number', 0.4, min=0.3, max=0.5, step=0.1, unit='mm',
          group='Shape', label='Bed chamfer'),
    Param('label_text', 'string', '', group='Label', label='Label text',
          max_length=MAX_TEXT_LENGTH, charset=TEXT_CHARSET,
          description='Blank = the signed width clearance, e.g. +1.0'),
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
    if p['cheek_depth'] - p['lead_in'] - p['jaw_root_radius'] < 3 - 1e-9:
        raise ValueError('cheek_depth - lead_in - jaw_root_radius must be >= 3 '
                         '(flat bearing on the edge face)')
    if p['wall'] - p['lead_in'] < 1.6 - 1e-9:
        raise ValueError('wall - lead_in must be >= 1.6 (the cheek tip stays load-bearing)')
    w = p['wall']
    inner = p['bench_width'] + p['width_clearance']
    p.update(inner_width=inner, width=inner + 2*w, height=p['cheek_depth'] + w)
    footprint = (p['width'], p['height'])
    if footprint[0] > BED_X or footprint[1] > BED_Y:
        raise ValueError(f'footprint {footprint[0]:g} x {footprint[1]:g} mm exceeds the '
                         f'{BED_X:g} x {BED_Y:g} mm bed; reduce bench_width, width_clearance or wall')
    if p['coupon_length'] > BED_Z:
        raise ValueError(f'coupon_length exceeds the {BED_Z:g} mm build height')
    p['footprint'] = footprint
    label = p['label_text'] if p['label_text'].strip() else f'{p["width_clearance"]:+.1f}'
    stroke = text_measures(label, p['text_size'])[0]
    floor = STROKE_FLOOR_INLAID + FLOOR_MARGIN
    if stroke < floor:
        raise ValueError(f'label_text {label!r} at text_size {p["text_size"]:g} has a {stroke:.3f} mm '
                         f'stroke, under the {floor:g} mm floor; use a larger text_size')
    size = text_sketch(label, p['text_size']).bounding_box().size
    room = p['coupon_length'] - 2*LABEL_END_MARGIN
    if size.Y > room + 1e-9:
        raise ValueError(f'label_text {label!r} at text_size {p["text_size"]:g} is {size.Y:.2f} mm tall; '
                         f'coupon_length {p["coupon_length"]:g} leaves {room:g} mm')
    span = inner - 2*LABEL_END_MARGIN
    if size.X > span + 1e-9:
        raise ValueError(f'label_text {label!r} at text_size {p["text_size"]:g} is {size.X:.2f} mm wide; '
                         f'bench_width leaves {span:g} mm')
    p.update(label=label, label_stroke=stroke, label_width=size.X, label_height=size.Y)
    return p


def saddle_profile(p: dict) -> Sketch:
    """The inverted-U footprint (XY) with its in-plane edge treatment.

    Inside root fillets jaw_root_radius, 45 degree lead_in on both cheek
    tips' inner corners, OUTER_RADIUS on the four outer corners.
    """
    w, W, h, cd = p['wall'], p['width'], p['height'], p['cheek_depth']
    pts = ((0, 0), (w, 0), (w, cd), (W - w, cd), (W - w, 0), (W, 0), (W, h), (0, h))
    with BuildSketch() as s:
        Polygon(*pts, align=None)

        def at(*corners):
            return [v for v in s.vertices() for x, y in corners
                    if abs(v.X - x) < 1e-6 and abs(v.Y - y) < 1e-6]
        fillet(at((w, cd), (W - w, cd)), p['jaw_root_radius'])
        if p['lead_in'] > 0:
            chamfer(at((w, 0), (W - w, 0)), p['lead_in'])
        fillet(at((0, 0), (W, 0), (W, h), (0, h)), OUTER_RADIUS)
    return s.sketch


def _blank(p: dict):
    part = extrude(saddle_profile(p), p['coupon_length'])
    top = part.faces().sort_by(Axis.Z)[-1]
    part = part.fillet(TOP_RADIUS, top.edges())
    bed = part.faces().sort_by(Axis.Z)[0]
    return part.chamfer(p['bed_chamfer'], None, bed.edges())


def label_cutter(p: dict):
    """The glyph recess: y height-INLAY_DEPTH..height, centred on the bar's outer face.

    Read from +Y with +Z (print up) up: the sketch's X (reading direction)
    maps to -X, its Y to +Z.
    """
    sketch = text_sketch(p['label'], p['text_size'])
    bb = sketch.bounding_box()
    sketch = Pos(-bb.center().X, -bb.center().Y) * sketch
    face = Plane(origin=(p['width']/2, p['height'], p['coupon_length']/2), x_dir=(-1, 0, 0), z_dir=(0, 1, 0))
    return extrude(face * sketch, -INLAY_DEPTH)


def holder(**values):
    p = dimensions(values)
    return (_blank(p) - label_cutter(p)).clean()


def audit_exclusions(values: dict) -> list:
    """label-recess: the INLAY_DEPTH slab under the ink on the bar's outer face.

    The glyph recess ceilings face down in the print pose; each is a flat
    bridge no wider than a stroke (the underware_text_label family).
    """
    p = dimensions(values)
    bb = label_cutter(p).bounding_box()
    return [Pos(bb.center().X, p['height'] - INLAY_DEPTH/2, bb.center().Z)
            * Box(bb.size.X + 0.02, INLAY_DEPTH + 0.002, bb.size.Z + 0.02)]


FIT_KIT = (-1.0, 0.0, 1.0, 2.0, 3.0)


def _preset_id(c: float) -> str:
    return f'fit-{"minus" if c < 0 else "plus"}-{abs(c):.1f}'.replace('.', '-')


SPEC = register(ModelSpec(
    name='holder_bench_width_saddle', build=lambda values: holder(**values),
    title='Bench width saddle (fit coupon)', category_id='household',
    description=('Fit-test coupon for a saddle that spans a bench top across its width: a flat '
                 'bar on the slab top with a short cheek down each long edge. The five-coupon fit '
                 'kit varies the width clearance and debosses it on the bar; print them, drop '
                 'each over the top and keep the snug one. Prints on its side, no supports.'),
    tags=('holder', 'fit-test'), params=PARAMS,
    presets=tuple(Preset(id=_preset_id(c), label=f'Fit kit {c:+.1f} mm',
                         values={'width_clearance': c}) for c in FIT_KIT),
    # The profile plane below the label (it reads the bar's outer face at mid-length).
    review_sections=(PlaneSpec((0, 0, 1.5), (0, 0, 1), 'profile at Z = 1.5, below the label'),),
))
