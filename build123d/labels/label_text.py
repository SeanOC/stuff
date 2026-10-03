"""Label text: one vendored font, autoscaled and centred in a box (spike pst-0zfra).

The font is Inter Bold 4.001, static (OFL 1.1, assets/fonts/inter/). build123d's
Text silently substitutes a system font when font_path is missing or is not a
font, so load_font() registers the file itself and fails loudly unless OCCT
resolves the face to exactly that file. Only STATIC fonts are supported:
variable TTFs (Inter[opsz,wght], Roboto[wdth,wght]) build invalid solids.

fit_text() builds at NOMINAL_SIZE, scales uniformly to fit the box minus the
margin in both axes and centres the ink bounding box on the origin. It also
reports the thinnest stroke and the narrowest gap (counters and letter
spacing), both scaled, so a model can clamp before a feature goes below a
printable width. Glyphs read correctly from +Z; a face-down card mirrors them.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from build123d import FontStyle, Part, Pos, Sketch, Text, extrude, scale
from shapely.geometry import Polygon, box
from shapely.ops import polylabel, unary_union

FONT_PATH = (Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
             / 'inter' / 'Inter-Bold.ttf')
FONT_STYLE = FontStyle.BOLD
NOMINAL_SIZE = 10.0
# Feature-width scan at NOMINAL_SIZE: radius start and step (mm).
_SCAN_START, _SCAN_STEP = 0.1, 0.01


class FittedText(NamedTuple):
    part: Part
    scale: float
    min_stroke: float  # thinnest glyph feature, mm, after scaling
    min_gap: float     # narrowest counter / letter gap, mm, after scaling


def load_font(path: Path | str = FONT_PATH) -> str:
    """Register the font file with OCCT and return its face name; never substitute."""
    from build123d.text import FONT_ASPECT, FontManager
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'label font missing: {path}')
    manager = FontManager()
    names = manager.register_font(str(path), True, False)  # fontTools raises on a non-font
    if not names:
        raise ValueError(f'no font faces in {path}')
    found = manager.find_font(names[0], FONT_STYLE)
    resolved = found.FontPath(FONT_ASPECT[FONT_STYLE]).ToCString() if found else ''
    if not resolved or Path(resolved).resolve() != path.resolve():
        raise RuntimeError(f'OCCT resolved {names[0]!r} {FONT_STYLE.name} to '
                           f'{resolved or "nothing"}, not {path}')
    return names[0]


def text_sketch(text: str, size: float = NOMINAL_SIZE, path: Path | str = FONT_PATH) -> Sketch:
    if not text.strip():
        raise ValueError('label text is empty')
    return Text(text, font_size=size, font=load_font(path), font_path=str(path),
                font_style=FONT_STYLE)


def _polygons(sketch: Sketch, tol: float = 0.005):
    tris = []
    for face in sketch.faces():
        verts, faces = face.tessellate(tol, 0.1)
        pts = [(v.X, v.Y) for v in verts]
        tris += [Polygon([pts[i] for i in t]) for t in faces]
    return unary_union(tris).buffer(0)


def _thin_feature_lost(region, r: float) -> bool:
    """Does an opening by a disc of radius r remove a feature >= 0.75 r thick?

    Corner slivers of an opening are thinner than 0.75 r unless the corner
    is sharper than ~16 degrees; a vanished stroke of width < 2 r is not.
    """
    lost = region.difference(region.buffer(-r, join_style=1).buffer(r, join_style=1))
    for piece in getattr(lost, 'geoms', [lost]):
        if piece.is_empty or piece.area < 1e-9:
            continue
        c = polylabel(piece, tolerance=r / 50)
        if piece.contains(c) and piece.exterior.distance(c) >= 0.75 * r:
            return True
    return False


def min_feature_width(region, limit: float = 3.0) -> float:
    """Narrowest feature a disc must pass, by an upward scan (not monotonic)."""
    r = _SCAN_START
    while r < limit and not _thin_feature_lost(region, r):
        r += _SCAN_STEP
    return 2 * (r - _SCAN_STEP)


def stroke_and_gap(sketch: Sketch) -> tuple[float, float]:
    ink = _polygons(sketch)
    x0, y0, x1, y1 = ink.bounds
    pad = NOMINAL_SIZE / 5
    return (min_feature_width(ink),
            min_feature_width(box(x0 - pad, y0 - pad, x1 + pad, y1 + pad).difference(ink)))


def fit_text(text: str, box_w: float, box_h: float, margin: float,
             depth: float = 0.6, measure: bool = True) -> FittedText:
    """Text scaled to fit (box - 2 margin) in both axes, ink centred on the origin.

    The part spans Z 0..depth. measure=False skips the stroke/gap scan (NaN).
    """
    w_avail, h_avail = box_w - 2 * margin, box_h - 2 * margin
    if w_avail <= 0 or h_avail <= 0 or depth <= 0:
        raise ValueError(f'no room for text in {box_w} x {box_h} with margin {margin}')
    nominal = text_sketch(text)
    bb = nominal.bounding_box()
    s = min(w_avail / bb.size.X, h_avail / bb.size.Y)
    stroke, gap = stroke_and_gap(nominal) if measure else (float('nan'),) * 2
    fitted = scale(nominal, s)
    c = fitted.bounding_box().center()
    part = extrude(Pos(-c.X, -c.Y, 0) * fitted, depth)
    return FittedText(part, s, stroke * s, gap * s)
