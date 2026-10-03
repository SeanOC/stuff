"""Label card (labels L2, pst-qznya): user text on a card for the spool cradle's label holder.

A 60 x 20 x 1.6 mm card (labels/constants.py, D7) that slides into the
holder on the cradle's front panel (L3). One fixed font (Inter Bold, D1/D2),
autoscaled and centred inside a 2.0 mm margin (D4); one line, else two, else
a ValueError naming the stroke (or, raised, the gap) and the longest text
that fits (D5/D6).

text_style:
  inlaid (default): two colours, printed FACE DOWN. The text fills the
      bottom INLAY_DEPTH of the card (filament 2) and the base is the rest
      (filament 1), so the visible face is the flat bed face. The card is
      modelled in the print frame and the text mirrored about YZ (D3);
      turned face up, it reads left to right.
  raised: the single-colour fallback (D11), printed FACE UP with the text
      INLAY_DEPTH proud of the top face, unmirrored.

build() returns the assembled card (what the print audit and the plain
STL see); colour_parts() returns the two filament bodies for the 3MF and
the -base / -text STLs (tag "multi-colour"). Glyph edges are left sharp:
they are the feature, and strokes down to 0.7 mm leave no room to chamfer.

Worst-case load: none (a label). The holder's rails and lip retain it.
"""
from __future__ import annotations

from build123d import Axis, Part, Plane, Pos, RectangleRounded, chamfer, extrude, mirror
from holders.registry import ColourPart, ModelSpec, Param, Preset, register
from labels.constants import (CARD_SIZES, CARD_T, CORNER_R, EDGE_CHAMFER, INLAY_DEPTH,
                              MAX_TEXT_LENGTH, MIN_GAP_RAISED, STROKE_FLOOR_INLAID,
                              STROKE_FLOOR_RAISED, TEXT_CHARSET, TEXT_MARGIN)
from labels.label_text import FittedText, layout_text

STROKE_FLOOR = {'inlaid': STROKE_FLOOR_INLAID, 'raised': STROKE_FLOOR_RAISED}
# Inlaid gaps are card material, held by the print audit's wall floor instead.
GAP_FLOOR = {'inlaid': 0.0, 'raised': MIN_GAP_RAISED}
BASE_RGBA = (0.10, 0.10, 0.10, 1.0)
TEXT_RGBA = (0.96, 0.96, 0.96, 1.0)


def card(size: str = 'spool-cradle') -> Part:
    w, h = CARD_SIZES[size]
    blank = extrude(RectangleRounded(w, h, CORNER_R), CARD_T)
    rims = blank.faces().sort_by(Axis.Z)
    return chamfer(rims[0].edges() + rims[-1].edges(), EDGE_CHAMFER)


def fitted_text(values: dict) -> FittedText | None:
    """The laid-out text (Z 0..INLAY_DEPTH, unmirrored), or None for blank text."""
    if not values['text'].strip():
        return None
    w, h = CARD_SIZES[values['size']]
    style = values['text_style']
    return layout_text(values['text'], w, h, TEXT_MARGIN, INLAY_DEPTH,
                       STROKE_FLOOR[style], GAP_FLOOR[style])


def _glyph_order(shape: Part) -> Part:
    """The same solids in a fixed order (left to right, then down the lines).

    OCCT booleans return the glyph solids in an address-dependent order, so
    the -text STL and the 3MF would differ between processes without this.
    """
    def key(solid):
        c = solid.center()
        return (round(c.X, 3), round(-c.Y, 3), round(c.Z, 3), round(solid.volume, 3))
    return Part(sorted(shape.solids(), key=key))


def colour_parts(values: dict) -> list[ColourPart]:
    """[(base, filament 1), (text, filament 2)] in the print frame; base only if blank."""
    whole = card(values['size'])
    fitted = fitted_text(values)
    if fitted is None:
        return [('base', whole, BASE_RGBA)]
    if values['text_style'] == 'inlaid':
        inlay = _glyph_order(whole & mirror(fitted.part, Plane.YZ))
        return [('base', whole - inlay, BASE_RGBA), ('inlay', inlay, TEXT_RGBA)]
    return [('base', whole, BASE_RGBA),
            ('text', _glyph_order(Pos(0, 0, CARD_T) * fitted.part), TEXT_RGBA)]


def build(values: dict) -> Part:
    parts = [shape for _, shape, _ in colour_parts(values)]
    out = parts[0]
    for shape in parts[1:]:
        out = out + shape
    return out


SPEC = register(ModelSpec(
    name='holder_label_card',
    build=build,
    title='Label card',
    description=('Slide-in label card for the spool cradle label holder: your text in '
                 'a fixed font, autoscaled and centred. Inlaid two-colour (face down, '
                 'flush) or raised single-colour.'),
    category_id='label',
    tags=('label', 'multi-colour'),
    params=(
        Param('text', 'string', 'Filament', label='Label text',
              max_length=MAX_TEXT_LENGTH, charset=TEXT_CHARSET),
        Param('size', 'enum', 'spool-cradle', label='Card size',
              choices=tuple(CARD_SIZES)),
        Param('text_style', 'enum', 'inlaid', label='Text style',
              choices=('inlaid', 'raised')),
    ),
    presets=(
        Preset('inlaid', 'Inlaid (two colours, face down)',
               {'text': 'Filament', 'text_style': 'inlaid'}),
        Preset('raised', 'Raised (one colour, face up)',
               {'text': 'Filament', 'text_style': 'raised'}),
    ),
))
