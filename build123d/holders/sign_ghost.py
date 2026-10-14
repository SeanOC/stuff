"""The ghost-with-poppy motif for the tombstone sign (pst-tl4ac.3 D7).

Sean's own design from the Poppy Street Spooks show site, vendored as
assets/art/ghost-with-poppy.svg (see assets/art/NOTICE): one element per
colour ROLE, its role in the data-role attribute, in a 52 x 60 viewBox.

build123d's import_svg composes a group's translate with an element's
rotate in the wrong order (petal-180 lands at x ~9 instead of ~39), so the
twelve primitives are rebuilt here from the SVG itself: ellipse / circle
attributes and path data (import_svg on the bare path, which it reads
correctly) under the element's full transform chain, read with xml.etree.

regions() partitions the motif by DOCUMENT ORDER (D2): a later element wins
where it overlaps an earlier one, which trims the earlier role; 'hole'
elements (eyes, mouth, poppy centre) are then dropped, so the plate shows
through. The result is Y-up, the 52 x 60 box scaled to `height` with its
lower-left corner on the origin.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

from build123d import Compound, Ellipse, Face, Pos, Rot, Sketch, import_svg, scale

SVG_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'art' / 'ghost-with-poppy.svg'
VIEW_W, VIEW_H = 52.0, 60.0
HOLE = 'hole'
_SVG = '{http://www.w3.org/2000/svg}'
_OP = re.compile(r'(translate|rotate|scale)\(([^)]*)\)')


def _ops(attr: str | None) -> list[tuple[str, list[float]]]:
    return [(name, [float(v) for v in re.split(r'[\s,]+', args.strip())])
            for name, args in _OP.findall(attr or '')]


def _place(face: Face, ops: list[tuple[str, list[float]]]) -> Face:
    """Apply an SVG transform chain to a face built in the Y-NEGATED frame.

    SVG maps a point by the chain right to left. With N(x, y) = (x, -y),
    N . rotate(a) = rotate(-a) . N and N . translate(x, y) = translate(x, -y) . N,
    so the chain is applied right to left with those conjugates.
    """
    for name, args in reversed(ops):
        if name == 'translate':
            face = Pos(args[0], -(args[1] if len(args) > 1 else 0.0)) * face
        elif name == 'rotate':
            face = Rot(0, 0, -args[0]) * face
        else:
            sx, sy = args[0], args[-1]  # uniform keeps the ellipse exact
            face = scale(face, sx if sx == sy else (sx, sy, 1))
    return face


def _primitive(el: ET.Element) -> Face:
    """The element's own shape, untransformed, in the Y-negated frame."""
    tag = el.tag.removeprefix(_SVG)
    num = lambda key: float(el.get(key, 0.0))  # noqa: E731
    if tag == 'path':
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W:g} {VIEW_H:g}">'
               f'<path d="{el.get("d")}"/></svg>')
        faces = [s for s in import_svg(io.StringIO(svg), flip_y=True, align=None)
                 if isinstance(s, Face)]
        assert len(faces) == 1, el.get('id')
        return faces[0]
    if tag in ('ellipse', 'circle'):
        rx, ry = (num('rx'), num('ry')) if tag == 'ellipse' else (num('r'),) * 2
        return Pos(num('cx'), -num('cy')) * Ellipse(rx, ry).faces()[0]
    raise ValueError(f'unsupported SVG element <{tag}> {el.get("id")!r}')


@cache
def elements() -> tuple[tuple[str, str, Face], ...]:
    """(id, role, face) per data-role element in document order, Y-up in the
    52 x 60 box (y = 0 at the box bottom)."""
    root = ET.parse(SVG_PATH).getroot()
    out = []

    def walk(node: ET.Element, chain: list) -> None:
        chain = chain + _ops(node.get('transform'))
        role = node.get('data-role')
        if role:
            out.append((node.get('id'), role, Pos(0, VIEW_H) * _place(_primitive(node), chain)))
        for child in node:
            walk(child, chain)

    walk(root, [])
    return tuple(out)


def _sketch(faces) -> Sketch:
    return Sketch(Compound(list(faces)).wrapped)


@cache
def _partition() -> tuple[tuple[str, Sketch], ...]:
    """role -> region in the 52 x 60 box, overlaps resolved by document order."""
    regions: dict[str, Sketch] = {}
    for _, role, face in elements():
        for name, region in regions.items():
            regions[name] = region - face
        regions[role] = regions[role] + face if role in regions else _sketch([face])
    return tuple((role, region) for role, region in regions.items()
                 if role != HOLE and region.faces())


def regions(height: float) -> dict[str, Sketch]:
    """role -> region, the 52 x 60 box scaled to height, lower-left on the origin."""
    k = height / VIEW_H
    return {role: scale(region, k) for role, region in _partition()}


def width(height: float) -> float:
    """The scaled box width (the art row reserves the whole box, as the poster)."""
    return VIEW_W * height / VIEW_H
