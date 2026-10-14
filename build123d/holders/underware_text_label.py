# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Underware for openGrid text label plate, adapted under CC BY-NC-SA 4.0.

[C] monokini_text_label.scad:38-62 (parameters), :125-137 (top level),
:146-196 monokiniGrip, :198-283 monokiniPlate — Pedro Leite, after Underware
2.0 by Hands on Katie and BlackjackDuck; source and reference pins in
assets/underware-opengrid/NOTICE (meshes + NOTICE only, no author SCAD is
committed). Geometry: build123d/underware/ — the plate is U1's straight
channel at top_chamfer 0 (the file's topChamfer, :109) and height
SNAP_WALL + BASE_HEIGHT, i.e. the 2 mm floor alone with the same openGrid
grips per 28 mm cell.

Model frame = print frame: X across, Y along (centred), Z up; the text face
lies on the bed and the grips point up (+Z). Worst load: the plate pulled
off the board along +Z on the grip nubs; each grip is one continuous rail
along the layers on the 2 mm floor. PLA or PCTG, no supports.

text_style (the author's Text_Emboss, :59-60):
  inlaid (author default, Text_Emboss=false): the glyphs fill the bed face
      to text_depth in filament 2, flush with the plate (filament 1); read
      from below. Same two-colour seam as holders/label_card.py.
  debossed (Text_Emboss=true): the glyph recess alone, one colour.
Glyphs come from the labels seam (Inter Bold, labels/label_text.py) at
OpenSCAD's text size (1/0.72 em), not the author's Raleway; strokes are
held to the labels inlay floor (labels/constants.py STROKE_FLOOR_INLAID).

Deviations: a BED_CHAMFER on every bed-face edge (design-guidelines §1/§8:
bed-contact chamfers never yield; the author's plate is square-edged).
Not ported: Text_x_coordinate, Font / Font_Style / colours, Grip_Flare,
Grip_Increase_Clearance, Suppress_Connectors and the hidden Decorative block.
label_length_units stops at 11, not 12: 12 cells are 336 mm, past the H2S
bed (holders/printer.py), as for underware_i_channel.
"""
from build123d import Axis, Box, Pos, chamfer

from holders.label_card import BASE_RGBA, TEXT_RGBA, _glyph_order
from holders.printer import BED_X
from holders.registry import ColourPart, ModelSpec, Param, Preset, register
from labels.constants import INLAY_DEPTH, MAX_TEXT_LENGTH, STROKE_FLOOR_INLAID, TEXT_CHARSET
from labels.label_text import FLOOR_MARGIN, text_measures
from underware import constants as c
from underware.channel import label_cutter, present_grips, straight_channel
from underware.grip import end_ramp_regions

PLATE_TOP_CHAMFER = 0.                       # [C] :109 topChamfer
PLATE_HEIGHT = c.SNAP_WALL + c.BASE_HEIGHT    # 5.4: floor + grips ([C] :129, :171)
BED_CHAMFER = 0.4                            # design-guidelines §1, 0.3-0.5 mm
MAX_LENGTH_UNITS = int(BED_X // c.GRID)
TEXT_STYLES = ('inlaid', 'debossed')


def dimensions(v):
    return c.channel_width(v['label_width_units']), v['label_length_units']*c.GRID


def plate(width: float, length: float):
    """monokiniPlate (:198-283) before the bed chamfer: floor + grips per cell."""
    return straight_channel(length, width, PLATE_HEIGHT, top_chamfer=PLATE_TOP_CHAMFER)


def glyphs(v):
    """The ink, z 0..text_depth, read from below; None for blank text.

    Named errors: depth 0, ink past the flat bed face, a stroke under the
    labels inlay floor.
    """
    if not v['text'].strip():
        return None
    if v['text_depth'] <= 0:
        raise ValueError('text_depth 0 makes no label in the bed face; use 0.2 or more')
    width, length = dimensions(v)
    size = v['text_size']*c.OPENSCAD_TEXT_SCALE
    stroke = text_measures(v['text'], size)[0]
    floor = STROKE_FLOOR_INLAID + FLOOR_MARGIN
    if stroke < floor:
        raise ValueError(f'label {v["text"]!r} at size {v["text_size"]:g} has a {stroke:.3f} mm '
                         f'stroke, under the {floor:g} mm floor; use a larger text_size')
    return label_cutter(v['text'], v['text_size'], v['text_depth'], width, length,
                        face=(width - 2*BED_CHAMFER, length - 2*BED_CHAMFER))


def blank(v):
    width, length = dimensions(v)
    body = plate(width, length)
    return chamfer(body.faces().sort_by(Axis.Z)[0].edges(), BED_CHAMFER)


def colour_parts(values: dict) -> list[ColourPart]:
    """[(base, filament 1), (inlay, filament 2)] for inlaid text; base only otherwise."""
    v = SPEC.resolve_values(values)
    whole, ink = blank(v), glyphs(v)
    if ink is None:
        return [('base', whole, BASE_RGBA)]
    if v['text_style'] == 'debossed':
        return [('base', whole - ink, BASE_RGBA)]
    inlay = _glyph_order(whole & ink)
    return [('base', whole - inlay, BASE_RGBA), ('inlay', inlay, TEXT_RGBA)]


def preview_colour_parts(values: dict) -> list[ColourPart] | None:
    """Two-material viewer GLB for inlaid text; None (one material) otherwise."""
    parts = colour_parts(values)
    return parts if len(parts) > 1 else None


def build(values=None):
    parts = [shape for _, shape, _ in colour_parts(values or {})]
    out = parts[0]
    for shape in parts[1:]:
        out = out + shape
    return out


def audit_exclusions(values=None) -> dict:
    """Published-exception envelopes by family (exact solids, no bbox growth).

    grip-end-wedge: every grip's two 45 degree end-ramp faces ([C] :174-191,
      U1's family; the ramp meets the nub undercut in the author's wedge).
    label-recess: debossed text only, the 0..text_depth slab over the ink:
      glyph recess ceilings are flat bridges no wider than a stroke (U1's
      family). Inlaid text prints flush: build() has no recess.
    """
    v = SPEC.resolve_values(values or {})
    width, length = dimensions(v)
    out = {'grip-end-wedge': [], 'label-recess': []}
    for y, side, _ in present_grips(length, ''):
        out['grip-end-wedge'] += end_ramp_regions(width, PLATE_HEIGHT, y, side)
    ink = glyphs(v) if v['text_style'] == 'debossed' else None
    if ink is not None:
        bb, d = ink.bounding_box(), v['text_depth']
        out['label-recess'].append(Pos(bb.center().X, bb.center().Y, d/2)
                                   * Box(bb.size.X + 0.02, bb.size.Y + 0.02, d + 0.002))
    return out


SPEC = register(ModelSpec(
    name='underware_text_label',
    title='Underware text label plate (openGrid)',
    description=('Underware 2.0 "monokini" label plate that snaps into openGrid beside your '
                 'cable channels: set width and length in 28 mm cells and your text, inlaid '
                 'in a second colour or debossed. By Pedro Leite after Hands on Katie and '
                 'BlackjackDuck, CC BY-NC-SA 4.0 (non-commercial, share-alike). Prints text '
                 'face down, no supports.'),
    category_id='multiboard',
    tags=('multi-colour',),
    build=build,
    params=(
        Param('label_width_units', 'integer', 1, min=1, max=4, step=1, filename=True,
              group='Label Size', label='Width (28 mm units)'),
        Param('label_length_units', 'integer', 5, min=1, max=MAX_LENGTH_UNITS, step=1, filename=True,
              group='Label Size', label='Length (28 mm units)'),
        Param('text', 'string', 'CABLES', group='Text Label', label='Label text',
              max_length=MAX_TEXT_LENGTH, charset=TEXT_CHARSET),
        # 6..16 step 1 (as underware_i_channel): OpenSCAD text sizes.
        Param('text_size', 'number', 10, min=6, max=16, step=1,
              group='Text Label', unit='mm', label='Font size'),
        Param('text_style', 'enum', 'inlaid', choices=TEXT_STYLES, filename=True,
              group='Text Label', label='Text style'),
        # 0..1 step 0.2 (layer heights, [C] :54); 0 is a named error.
        Param('text_depth', 'number', INLAY_DEPTH, min=0, max=1, step=0.2,
              group='Text Label', unit='mm', label='Text depth'),
    ),
    presets=(
        Preset('label-1x5', '1 × 5 cells, inlaid text', {}, default_view='bottom'),
        Preset('label-2x3', '2 × 3 cells, inlaid text',
               {'label_width_units': 2, 'label_length_units': 3}, default_view='bottom'),
    ),
))
