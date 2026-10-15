"""Label text: one vendored font, autoscaled and centred in a box (spike pst-0zfra).

Moved from holders/ in L2 (pst-qznya) so text layout and labels/constants.py
share one home.

The default font is Inter Bold 4.001, static (OFL 1.1, assets/fonts/inter/);
every function takes a font path + FontStyle to use another vendored face
(the tombstone sign's Creepster and Lexend, pst-tl4ac.3). build123d's Text
silently substitutes a system font when font_path is missing or is not a
font, so load_font() registers the file itself and fails loudly unless OCCT
resolves the face at that style to exactly that file. Only STATIC fonts are
supported: variable TTFs (Inter[opsz,wght], Roboto[wdth,wght]) build invalid
solids.

fit_text() builds at NOMINAL_SIZE, scales uniformly to fit the box minus the
margin in both axes and centres the ink bounding box on the origin. It also
reports the thinnest stroke and the narrowest gap (counters and letter
spacing), both scaled, so a model can clamp before a feature goes below a
printable width, plus the glyph-to-glyph clearance (reported, never gated:
see docs/labels-spike.md, 'Raised: no inter-glyph floor'). Glyphs read correctly from +Z; a face-down card mirrors them.

layout_text() applies the D6 rule on top: one line if the stroke holds the
floor, else two lines split at the space nearest the middle with one common
scale, else ValueError. Two lines stack on their ink boxes LINE_GAP apart
(the font's own 1.2 em leading costs about 10 % of the scale, and height
binds a two-line label on a 20 mm card).
"""
from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from build123d import Compound, FontStyle, Part, Pos, Sketch, Text, extrude, scale
from shapely.geometry import Polygon, box
from shapely.ops import polylabel, unary_union

FONT_PATH = (Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
             / 'inter' / 'Inter-Bold.ttf')
FONT_STYLE = FontStyle.BOLD
NOMINAL_SIZE = 10.0
# Feature-width scan at NOMINAL_SIZE: radius start and step (mm).
_SCAN_START, _SCAN_STEP = 0.1, 0.01
# Ink gap between two stacked lines at NOMINAL_SIZE (about 0.9 mm once fitted).
LINE_GAP = 1.2
# A layout must clear its stroke floor by this much: the print audit's wall
# bisection under-reports by ~1e-5 mm, so a stroke exactly at the 0.9 raised
# floor could fail the 0.9 MIN_WALL_MM it was meant to meet.
FLOOR_MARGIN = 0.01
# Committed nominal strokes (font sha256[:16]:style:text -> mm), so a cold
# process does not rescan the tombstone sign's preset lines: ~65 s of its
# ~105 s cold build, paid once per pytest worker, export and live render
# (codex on #206). A miss scans live; scripts/nominal_strokes.py regenerates
# the file and test_tombstone_sign.py re-measures every entry (audit_full).
STROKE_CACHE = Path(__file__).with_name('nominal_strokes.json')


class FittedText(NamedTuple):
    part: Part
    scale: float
    min_stroke: float  # thinnest glyph feature, mm, after scaling
    min_gap: float     # narrowest counter / letter / line gap, mm, after scaling
    lines: tuple[str, ...] = ()
    min_clearance: float = float('nan')  # closest two separate ink pieces, mm, scaled


def load_font(path: Path | str = FONT_PATH, style: FontStyle = FONT_STYLE) -> str:
    """Register the font file with OCCT and return its face name; never substitute."""
    from build123d.text import FONT_ASPECT, FontManager
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'label font missing: {path}')
    manager = FontManager()
    names = manager.register_font(str(path), True, False)  # fontTools raises on a non-font
    if not names:
        raise RuntimeError(f'no font faces in {path}')  # a deployment fault, not bad input
    found = manager.find_font(names[0], style)
    resolved = found.FontPath(FONT_ASPECT[style]).ToCString() if found else ''
    if not resolved or Path(resolved).resolve() != path.resolve():
        raise RuntimeError(f'OCCT resolved {names[0]!r} {style.name} to '
                           f'{resolved or "nothing"}, not {path}')
    return names[0]


def text_sketch(text: str, size: float = NOMINAL_SIZE, path: Path | str = FONT_PATH,
                style: FontStyle = FONT_STYLE) -> Sketch:
    """One line, or lines split on '\\n', each centred in X, stacked LINE_GAP apart."""
    if not text.strip():
        raise ValueError('label text is empty')
    lines = text.split('\n')
    if len(lines) > 1 and not all(line.strip() for line in lines):
        raise ValueError(f'label text {text!r} has an empty line')
    font = load_font(path, style)
    stack = None
    for line in lines:
        sketch = Text(line.strip() if len(lines) > 1 else line, font_size=size,
                      font=font, font_path=str(path), font_style=style)
        if stack is None:
            stack = sketch
        else:
            # The lines never touch, so collect faces rather than 2D-fuse them:
            # the fuse re-approximates the B-spline glyph edges and the extruded
            # second line then disagrees with its own fuse onto a plate (0.4 mm^3
            # on the tombstone sign's two-line Lexend detail band).
            drop = stack.bounding_box().min.Y - LINE_GAP * size / NOMINAL_SIZE
            below = Pos(0, drop - sketch.bounding_box().max.Y) * sketch
            stack = Sketch(Compound(stack.faces() + below.faces()).wrapped)
    return stack


def _polygons(sketch: Sketch, tol: float = 0.005):
    tris = []
    for face in sketch.faces():
        verts, faces = face.tessellate(tol, 0.1)
        pts = [(v.X, v.Y) for v in verts]
        tris += [Polygon([pts[i] for i in t]) for t in faces]
    ink = unary_union(tris).buffer(0)
    # Overlapping glyph faces (Creepster kerns 'x' into 't') union with
    # hairline cracks (~1e-16 mm^2) the exact fuse does not have; the sliver
    # they cut off read as a 0.18 mm stroke. Real counters are >= 0.3 mm^2.
    return unary_union([Polygon(p.exterior, [r for r in p.interiors if Polygon(r).area > 1e-9])
                        for p in getattr(ink, 'geoms', [ink])])


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


def glyph_clearance(sketch: Sketch) -> float:
    """Closest distance between two separate pieces of ink (glyphs, i-dots, lines).

    Unlike min_gap this ignores notches inside one glyph: min_gap reads
    Inter's 'M' crotch as 0.18 mm at NOMINAL_SIZE. inf for a single piece.
    """
    ink = _polygons(sketch)
    pieces = list(getattr(ink, 'geoms', [ink]))
    return min((a.distance(b) for i, a in enumerate(pieces) for b in pieces[i + 1:]),
               default=float('inf'))


def measure_stroke(text: str, path: Path | str = FONT_PATH,
                   style: FontStyle = FONT_STYLE) -> float:
    """Thinnest stroke at NOMINAL_SIZE, scanned live: stroke_and_gap's first
    scan alone (about half of _nominal_measures' cost)."""
    return min_feature_width(_polygons(text_sketch(text, path=path, style=style)))


@lru_cache(maxsize=None)
def _font_sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def stroke_key(text: str, path: Path | str, style: FontStyle) -> str:
    """STROKE_CACHE key: the font's content, not its path (worktrees differ)."""
    return f'{_font_sha(str(path))}:{style.name}:{text}'


@lru_cache(maxsize=1)
def stroke_cache() -> dict[str, float]:
    return json.loads(STROKE_CACHE.read_text(encoding='utf-8'))


@lru_cache(maxsize=256)
def _nominal_stroke(text: str, path: str = str(FONT_PATH),
                    style: FontStyle = FONT_STYLE) -> float:
    """measure_stroke, from STROKE_CACHE when the line is there.

    The tombstone sign gates on the stroke only, so its bands skip the gap
    and clearance scans.
    """
    cached = stroke_cache().get(stroke_key(text, path, style))
    return cached if cached is not None else measure_stroke(text, path, style)


@lru_cache(maxsize=256)
def _nominal_measures(text: str, path: str = str(FONT_PATH),
                      style: FontStyle = FONT_STYLE) -> tuple[float, float, float]:
    """(stroke, gap, clearance) at NOMINAL_SIZE: a pure function of the text and face.

    The scan costs ~14 s for a 20-character line and fit_text's result only
    scales it, so a model that fits the same line into several boxes (the
    tombstone sign's presets) measures it once per process. The face is part
    of the key: the same text is thinner in Lexend Medium than in Inter Bold.
    """
    nominal = text_sketch(text, path=path, style=style)
    return (*stroke_and_gap(nominal), glyph_clearance(nominal))


def nominal_stroke(text: str, path: Path | str = FONT_PATH,
                   style: FontStyle = FONT_STYLE) -> float:
    """Thinnest stroke of text at NOMINAL_SIZE in this face (cached)."""
    return _nominal_stroke(text, str(path), style)


def text_measures(text: str, size: float) -> tuple[float, float, float]:
    """(stroke, gap, clearance) of text_sketch(text, size), mm, for a caller
    that sets the size itself instead of fitting a box (scaled from the cached
    NOMINAL_SIZE scan; text size scales every glyph feature linearly)."""
    k = size / NOMINAL_SIZE
    return tuple(v * k for v in _nominal_measures(text))


def fit_text(text: str, box_w: float, box_h: float, margin: float,
             depth: float = 0.6, measure: bool = True, path: Path | str = FONT_PATH,
             style: FontStyle = FONT_STYLE, stroke_only: bool = False) -> FittedText:
    """Text scaled to fit (box - 2 margin) in both axes, ink centred on the origin.

    The part spans Z 0..depth. measure=False skips the stroke/gap/clearance
    measures (NaN); stroke_only=True measures the stroke alone (gap and
    clearance NaN).
    """
    w_avail, h_avail = box_w - 2 * margin, box_h - 2 * margin
    if w_avail <= 0 or h_avail <= 0 or depth <= 0:
        raise ValueError(f'no room for text in {box_w} x {box_h} with margin {margin}')
    nominal = text_sketch(text, path=path, style=style)
    bb = nominal.bounding_box()
    s = min(w_avail / bb.size.X, h_avail / bb.size.Y)
    if not measure:
        stroke = gap = clearance = float('nan')
    elif stroke_only:
        stroke, gap, clearance = _nominal_stroke(text, str(path), style), float('nan'), float('nan')
    else:
        stroke, gap, clearance = _nominal_measures(text, str(path), style)
    fitted = scale(nominal, s)
    c = fitted.bounding_box().center()
    part = extrude(Pos(-c.X, -c.Y, 0) * fitted, depth)
    lines = tuple(line.strip() for line in text.split('\n'))
    return FittedText(part, s, stroke * s, gap * s, lines, clearance * s)


def two_lines(text: str) -> str | None:
    """text split at the space nearest its middle (earlier on a tie), or None."""
    text = text.strip()
    spaces = [i for i, ch in enumerate(text) if ch == ' ']
    if not spaces:
        return None
    mid = (len(text) - 1) / 2
    cut = min(spaces, key=lambda i: (abs(i - mid), i))
    return f'{text[:cut].rstrip()}\n{text[cut + 1:].lstrip()}'


def _fit_scale(text: str, box_w: float, box_h: float, margin: float,
               path: Path | str = FONT_PATH, style: FontStyle = FONT_STYLE) -> float:
    bb = text_sketch(text, path=path, style=style).bounding_box()
    return min((box_w - 2 * margin) / bb.size.X, (box_h - 2 * margin) / bb.size.Y)


def _longest_fitting(text: str, box_w: float, box_h: float, margin: float,
                     floor: float, nominal_stroke: float, path: Path | str = FONT_PATH,
                     style: FontStyle = FONT_STYLE, max_lines: int = 2) -> str:
    """Longest prefix of text that lays out above floor.

    Uses bounding boxes only, with the whole text's nominal stroke: a prefix
    has a subset of the glyphs, so its own stroke is at least as thick and
    the answer is conservative.
    """
    for n in range(len(text.rstrip()) - 1, 0, -1):
        prefix = text[:n].rstrip()
        if not prefix.strip():
            continue
        layouts = [prefix] + [t for t in (two_lines(prefix),) if t and max_lines > 1]
        if max(nominal_stroke * _fit_scale(t, box_w, box_h, margin, path, style)
               for t in layouts) >= floor + FLOOR_MARGIN:
            return prefix
    return ''


def layout_text(text: str, box_w: float, box_h: float, margin: float,
                depth: float, floor: float, path: Path | str = FONT_PATH,
                style: FontStyle = FONT_STYLE, max_lines: int = 2,
                stroke_only: bool = False) -> FittedText:
    """fit_text on one line, else two (D6); ValueError if neither holds floor.

    max_lines=1 never wraps (the tombstone sign's single-line bands);
    stroke_only is fit_text's (the floor gates the stroke alone).

    The error names the measured stroke, the threshold it missed (floor +
    FLOOR_MARGIN) and the longest prefix of text that would fit. The stroke is
    truncated, not rounded, to 0.001 mm: a rejected stroke is below the
    threshold, and rounding could print it as equal to it.
    """
    tried = []
    for candidate in (text, two_lines(text))[:max_lines]:
        if candidate is None:
            continue
        fitted = fit_text(candidate, box_w, box_h, margin, depth, path=path, style=style,
                          stroke_only=stroke_only)
        if fitted.min_stroke >= floor + FLOOR_MARGIN:
            return fitted
        tried.append(fitted)
    best = max(tried, key=lambda f: f.min_stroke)
    longest = _longest_fitting(text, box_w, box_h, margin, floor,
                               best.min_stroke / best.scale, path, style, max_lines)
    stroke = math.floor(best.min_stroke * 1000) / 1000
    raise ValueError(
        f'label text {text!r} is too long for a {box_w:g} x {box_h:g} mm card: '
        f'its thinnest stroke would be {stroke:.3f} mm on '
        f'{len(best.lines)} line(s), below the {floor + FLOOR_MARGIN:g} mm '
        f'minimum ({floor:g} mm floor + {FLOOR_MARGIN:g} mm margin); '
        f'the longest that fits is {longest!r} ({len(longest)} characters)')
