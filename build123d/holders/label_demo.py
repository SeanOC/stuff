"""Labels spike demo card (pst-0zfra): smoke-tagged, never in the app catalog.

The spike's own envelope, kept as measured: the production card and its
numbers are holders/label_card.py + labels/constants.py (L2).

A 60 x 14 x 1.6 mm card printed FACE DOWN: the visible face is the bed face
(Z = 0) and the text is a flush two-colour inlay in the bottom INLAY_DEPTH.
print_orientation is metadata only (export writes the part unrotated), so
the card is modelled in the print frame and the text is mirrored about the
YZ plane here; flipped face-up, it reads left to right.

Parts: inlay = text ∩ card (Z 0..INLAY_DEPTH); base = card − inlay. The
single-colour fallback is the base alone (debossed, face down) or the
mirror-free raised card (text on top, face up). Worst-case load: none (a
label); it is held by the holder's rails, not by its own strength.

Run as a script from build123d/ to write the 3MF and STLs to docs/exports:
    uv run python -m holders.label_demo
"""
from __future__ import annotations

import sys
from pathlib import Path

from build123d import Axis, Part, Plane, Pos, RectangleRounded, chamfer, extrude, mirror
from labels.label_text import fit_text
from holders.registry import ModelSpec, Param, register

CARD_W, CARD_H, CARD_T = 60.0, 14.0, 1.6
CORNER_R = 1.5
EDGE_CHAMFER = 0.4      # bed-face edge (elephant's foot) and top edge
INLAY_DEPTH = 0.6       # 3 layers at 0.2 mm
TEXT_MARGIN = 1.5       # ink to card edge, > EDGE_CHAMFER
BASE_RGBA = (0.10, 0.10, 0.10, 1.0)
INLAY_RGBA = (0.96, 0.96, 0.96, 1.0)
EXPORTS = Path(__file__).resolve().parent.parent / 'docs' / 'exports'


def card() -> Part:
    blank = extrude(RectangleRounded(CARD_W, CARD_H, CORNER_R), CARD_T)
    rims = blank.faces().sort_by(Axis.Z)
    return chamfer(rims[0].edges() + rims[-1].edges(), EDGE_CHAMFER)


def parts(text: str) -> tuple[Part, Part]:
    """(base, inlay) in the face-down print frame; text mirrored about YZ."""
    ink = fit_text(text, CARD_W, CARD_H, TEXT_MARGIN, INLAY_DEPTH, measure=False).part
    whole = card()
    inlay = whole & mirror(ink, Plane.YZ)
    return whole - inlay, inlay


def raised(text: str) -> Part:
    """Single-colour alternative: face up, text raised INLAY_DEPTH on top, unmirrored."""
    ink = fit_text(text, CARD_W, CARD_H, TEXT_MARGIN, INLAY_DEPTH, measure=False).part
    plain = extrude(RectangleRounded(CARD_W, CARD_H, CORNER_R), CARD_T)
    plain = chamfer(plain.faces().sort_by(Axis.Z)[0].edges(), EDGE_CHAMFER)
    return plain + Pos(0, 0, CARD_T) * ink


def build(values: dict) -> Part:
    base, inlay = parts(values['text'])
    return base + inlay


SPEC = register(ModelSpec(
    name='label_demo',
    build=build,
    description='Labels spike demo card: flush two-colour text inlay, face down',
    tags=('smoke',),
    params=(Param('text', 'string', 'PLA Black', label='Label text'),),
))


def export_all(text: str = 'PLA Black', out: Path = EXPORTS) -> list[Path]:
    from scripts.export import export_3mf_one_object, export_stl
    base, inlay = parts(text)
    files = {name: out / f'label_demo_{name}.stl' for name in
             ('base', 'inlay', 'debossed', 'raised')}
    export_stl(base, files['base'])
    export_stl(inlay, files['inlay'])
    export_stl(base, files['debossed'])  # single colour = the base alone
    export_stl(raised(text), files['raised'])
    one = out / 'label_demo.3mf'
    export_3mf_one_object([('base', base, BASE_RGBA), ('inlay', inlay, INLAY_RGBA)],
                          one, 'label_demo')
    return [*files.values(), one]


if __name__ == '__main__':
    for p in export_all(*sys.argv[1:2]):
        print(p.relative_to(EXPORTS.parent.parent), p.stat().st_size)
