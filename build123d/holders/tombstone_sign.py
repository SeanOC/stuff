"""Tombstone sign (epic pst-tl4ac; S1 pst-tl4ac.1, S3 pst-tl4ac.3): the poster look.

A plate in the classic tombstone outline (holders/signs.py outline: straight
sides, flat bottom, a 'round' full-width arch or a 'shoulder' arch a third
of the width) carrying the song-request poster (poppystreetspooks.com/sign)
as RAISED multi-colour features, with two tenon pockets in its bottom edge
for the separately printed stake (S2). The pocket / tenon / pin numbers live
in holders/signs.py, which the stake imports too.

Printed FACE UP: every colour feature stands RAISE_H (0.6 mm = 3 layers)
proud of the top face, modelled unmirrored in the print frame. All raised
regions share the one Z t..t+RAISE_H slab and never overlap.

Layout, top to bottom, inside a `margin` inset of the outline (D4): eyebrow
(caps, Lexend Medium), title (Creepster, one line else two), ART ROW (the
ghost-with-poppy at left, the QR panel at right, centred as a pair with a
margin gap; ghost height 0.47 x qr_size, the poster ratio), scan_line
(Lexend Bold), detail_1 and detail_2 (Lexend Medium, one line else two),
host (Lexend Bold, its own band: the poster sets it inline after detail_2),
and the footer_1 line (Lexend Medium) under a thin raised rule. Blank lines
take no band and no gap.

Band rule: from the content top (where the inset arch is CONTENT_CHORD of
the inset width) down to a floor of margin, gaps margin / 2, the art row a
fixed qr_size block. B = top - margin - qr_size - gap x (blocks - 1) must be
>= MIN_TEXT_BUDGET (else the 'minimum height' ValueError). Each text band
needs need = (stroke floor + FLOOR_MARGIN) / nominal stroke x nominal ink
height, measured on its own face at its wrap (the fewest lines whose width
need fits the inset chord at the band's top); band height = need + the
slack (B - sum of needs) shared by the poster weights. A line wider than the
chord at its top pushes the band down to where the chord holds it (B
shrinks by the push): that is how the eyebrow leaves the arch on the small
plate. Pass 1 places the bands by the weights alone; the needs are
measured at those tops; pass 2 places need + slack. A line that cannot hold
the 0.9 raised stroke floor anywhere (or sum of needs > B: the hungriest
line) raises the label card's stroke ValueError naming the line.

Colours (D3), rank order = filament order: base (the plate, ground purple),
bone, pumpkin, poppy, leaf, dim, ink, ember. colours = N (2..8) activates
the first N; an inactive role folds (FOLD, repeated until active): ember ->
poppy, ink -> hole, dim -> bone, leaf -> pumpkin, poppy -> pumpkin,
pumpkin -> bone. A 'hole' is absent from the slab, so the plate shows
0.6 mm down: the ghost's eyes, mouth and poppy centre always, the QR dark
modules whenever ink is inactive. The ghost's overlaps are resolved by SVG
document order (holders/sign_ghost.py); the poster's 0.55-opacity ember
highlights print solid. Same-filament regions are fused, and QR dark
modules are shrunk 0.01 mm (signs.qr_regions) so no two bodies of one
filament meet only at an edge.

QR: segno at error level M encoding https://{host}, a 4-module quiet zone,
qr_size square including it, on a bone panel with QR_CORNER_R corners (the
corner arcs stay inside the quiet zone); pitch = qr_size / modules must be
>= 2.0 mm (signs.py).

build() returns the plate with every raised feature fused on (what the print
audit and the plain STL see); colour_parts() the filament bodies for the 3MF
and the per-part STLs (tag "multi-colour"); preview_colour_parts() the
viewer GLB's materials.

Pockets print as flat 8 mm roofs over the void (bridges <= MAX_BRIDGE_MM;
audit_exclusions lists those planes, measured by the tests first). The
pin hole is a flat-topped teardrop (signs.pin_profile). Pocket mouths and
the pin hole are mating edges and stay sharp; the plate rims carry a 0.4
chamfer on both faces (bed: elephant's foot). Glyph, art and QR edges are
the feature and stay sharp, as on the label card. Raised features add
material, so they may run down to the margin over the pockets.

Worst-case load: wind on the face, bending the plate about the X axis at
the pockets; the tenons carry it into the stake. The load path runs along
the printed layers (the plate prints flat), so the bending stress is in
the strong in-plane direction. PLA or PCTG; PCTG for a sign left outdoors.
"""
from __future__ import annotations

from functools import lru_cache, reduce
from pathlib import Path

from build123d import Axis, Box, Compound, Face, FontStyle, Part, Pos, Vector, Wire, chamfer, \
    extrude
from holders import sign_ghost, signs
from holders.label_card import _glyph_order
from holders.printer import BED_X, BED_Y
from holders.registry import ColourPart, ModelSpec, Param, Preset, register
from labels.constants import INLAY_DEPTH, MAX_TEXT_LENGTH, STROKE_FLOOR_RAISED, TEXT_CHARSET
from labels.label_text import FLOOR_MARGIN, layout_text, nominal_stroke, text_sketch, two_lines
from scripts.thumbnail import PlaneSpec
from shapely.geometry import box
from shapely.geometry.polygon import orient

RAISE_H = INLAY_DEPTH       # 0.6 mm = 3 layers proud of the top face
FLOOR = STROKE_FLOOR_RAISED
THRESHOLD = FLOOR + FLOOR_MARGIN  # what every raised stroke must clear
RULE_W = THRESHOLD          # the footer rule is one stroke-floor line
EDGE_CHAMFER = 0.4          # both rims, as the label card
DETAIL_MAX_LENGTH = 72
QR_CORNER_R = 8.0           # bone panel rounding, inside the 4-module quiet zone
GHOST_SHARE = 0.47          # ghost height / panel height (the poster's 172 / 368 px)
GAP_SHARE = 0.5             # inter-band gap = margin x this
CONTENT_CHORD = 0.5         # content stops where the arch is this share of the inset width
MIN_TEXT_BUDGET = 40.0      # mm: the floor on B (the text bands' total), never per line

_FONTS = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
FONTS = {'lexend-medium': (_FONTS / 'lexend' / 'Lexend-Medium.ttf', FontStyle.REGULAR),
         'lexend-bold': (_FONTS / 'lexend' / 'Lexend-Bold.ttf', FontStyle.BOLD),
         'creepster': (_FONTS / 'creepster' / 'Creepster-Regular.ttf', FontStyle.REGULAR)}

# Text bands, top to bottom; 'art' is the fixed ghost + QR row between them.
LINES = ('eyebrow', 'title', 'scan_line', 'detail_1', 'detail_2', 'host', 'footer_1')
ORDER = ('eyebrow', 'title', 'art', 'scan_line', 'detail_1', 'detail_2', 'host', 'footer_1')
WEIGHT = {'eyebrow': 6, 'title': 22, 'scan_line': 8, 'detail_1': 10, 'detail_2': 6,
          'host': 6, 'footer_1': 8}
FACE = {'eyebrow': 'lexend-medium', 'title': 'creepster', 'scan_line': 'lexend-bold',
        'detail_1': 'lexend-medium', 'detail_2': 'lexend-medium', 'host': 'lexend-bold',
        'footer_1': 'lexend-medium'}
MAX_LINES = {'eyebrow': 1, 'title': 2, 'scan_line': 1, 'detail_1': 2, 'detail_2': 2,
             'host': 1, 'footer_1': 1}
LINE_ROLE = {'eyebrow': 'dim', 'title': 'pumpkin', 'scan_line': 'bone', 'detail_1': 'dim',
             'detail_2': 'dim', 'host': 'pumpkin', 'footer_1': 'dim'}

# D3: filament order; the preview colours are the poster's tokens (ink and
# ember are ours: ember is the poster's inline highlight, ink is not on it).
HOLE = sign_ghost.HOLE
ROLES = ('base', 'bone', 'pumpkin', 'poppy', 'leaf', 'dim', 'ink', 'ember')
FOLD = {'ember': 'poppy', 'ink': HOLE, 'dim': 'bone', 'leaf': 'pumpkin',
        'poppy': 'pumpkin', 'pumpkin': 'bone'}
HEX = {'base': '#120a1e', 'bone': '#f4ecdc', 'pumpkin': '#ff7a1a', 'poppy': '#e5322d',
       'leaf': '#5b8f3a', 'dim': '#b7a9c9', 'ink': '#0a0a0a', 'ember': '#ff5a4e'}
RGBA = {k: (*(int(v[i:i + 2], 16) / 255 for i in (1, 3, 5)), 1.0) for k, v in HEX.items()}


def filament(role: str, colours: int) -> str:
    """The active role (or HOLE) a feature of `role` prints in, given N colours."""
    active = ROLES[:colours]
    while role not in active and role != HOLE:
        role = FOLD[role]
    return role


def qr_data(values: dict) -> str:
    """What the QR encodes: the host's site (the poster encodes site.url)."""
    return f'https://{values["host"].strip()}'


def _line(values: dict, name: str) -> str:
    text = values[name].strip()
    return text.upper() if name == 'eyebrow' else text


@lru_cache(maxsize=None)
def _ink(text: str, face: str) -> tuple[float, float, float]:
    """(width, height, stroke) of text's ink at NOMINAL_SIZE in face."""
    path, style = FONTS[face]
    bb = text_sketch(text, path=path, style=style).bounding_box()
    return bb.size.X, bb.size.Y, nominal_stroke(text, path, style)


def line_need(name: str, candidate: str) -> tuple[float, float]:
    """(width, height) the candidate needs for its stroke to clear THRESHOLD."""
    w, h, stroke = _ink(candidate, FACE[name])
    k = THRESHOLD / stroke
    return k * w, k * h


def _candidates(name: str, text: str) -> list[str]:
    split = two_lines(text) if MAX_LINES[name] > 1 else None
    return [text] + ([split] if split else [])


def _top(region, width: float, height: float, margin: float) -> float:
    """Highest Y whose inset chord is >= CONTENT_CHORD of the inset width."""
    need = CONTENT_CHORD * (width - 2 * margin)
    lo, hi = margin, height
    for _ in range(60):  # inner width only shrinks going up
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if signs.inner_width(region, mid) >= need else (lo, mid)
    return lo


def _chord_cap(region, top: float, width: float, floor: float) -> float | None:
    """Highest Y <= top whose inset chord is >= width; None if not even at floor."""
    if signs.inner_width(region, top) >= width:
        return top
    if signs.inner_width(region, floor) < width:
        return None
    lo, hi = floor, top
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if signs.inner_width(region, mid) >= width else (lo, mid)
    return lo


def _place(order, heights: dict, top: float, gap: float, caps: dict) -> tuple[dict, float]:
    """Stack the blocks down from top; a capped band starts no higher than its cap.
    Returns ({name: (y_lo, y_hi)}, total push)."""
    out, y, push = {}, top, 0.0
    for name in order:
        cap = caps.get(name, y)
        if cap < y:
            push += y - cap
            y = cap
        out[name] = (y - heights[name], y)
        y -= heights[name] + gap
    return out, push


def art_width(qr: float, margin: float) -> float:
    """Ghost box + margin + QR panel: the art row's width at its top."""
    return sign_ghost.width(GHOST_SHARE * qr) + margin + qr


def _frame(values: dict, height: float | None = None) -> dict | None:
    """Band placement (pure 2D), or None when height cannot hold it.

    Returns region (the margin-inset outline, shapely), top, gap, B, the
    pass-1 placement, needs / width needs / chosen wrap per present line,
    'bands' {name: (y_lo, y_hi)} for every present line and 'art', and
    'overflow' (sum of needs > B: features() raises for the hungriest line).
    A line that cannot hold the stroke floor at any width raises here.
    """
    w, m, qr = values['width'], values['margin'], values['qr_size']
    h = values['height'] if height is None else height
    region = signs.outline_region(w, h, values['arch']).buffer(-m)
    top = _top(region, w, h, m)
    gap = GAP_SHARE * m
    order = [n for n in ORDER if n == 'art' or values[n].strip()]
    texts = [n for n in order if n != 'art']
    base = top - m - qr - gap * (len(order) - 1)
    if base < MIN_TEXT_BUDGET:
        return None
    weights = sum(WEIGHT[n] for n in texts)
    pass1, _ = _place(order, {'art': qr, **{n: base * WEIGHT[n] / weights for n in texts}},
                      top, gap, {})
    lines, need, wneed, caps = {}, {}, {}, {}
    for n in texts:
        text = _line(values, n)
        chord = signs.inner_width(region, pass1[n][1])
        sizes = [(c, *line_need(n, c)) for c in _candidates(n, text)]
        fit = next((s for s in sizes if s[1] <= chord + 1e-9), None)
        lines[n], wneed[n], need[n] = fit or min(sizes, key=lambda s: s[1])
        if wneed[n] > w - 2 * m:
            raise _line_error(n, text, w - 2 * m, pass1[n][1] - pass1[n][0])
        caps[n] = _chord_cap(region, top, wneed[n], m)
        if caps[n] is None:
            return None
    total = sum(need.values())
    push = 0.0
    for _ in range(8):  # pushes only move bands that stay below their cap: settles fast
        b = base - push
        if b < MIN_TEXT_BUDGET:
            return None
        slack = b - total
        heights = {n: (need[n] + slack * WEIGHT[n] / weights if slack >= 0
                       else need[n] * b / total) for n in texts}
        bands, pushed = _place(order, {'art': qr, **heights}, top, gap, caps)
        if abs(pushed - push) < 1e-9:
            break
        push = pushed
    if bands[order[-1]][0] < m - 1e-6:
        return None
    if signs.inner_width(region, bands['art'][1]) < art_width(qr, m):
        return None
    return {'region': region, 'top': top, 'gap': gap, 'B': base - push, 'pass1': pass1,
            'need': need, 'width_need': wneed, 'lines': lines, 'bands': bands,
            'overflow': total > base - push + 1e-9}


def _line_error(name: str, text: str, box_w: float, box_h: float) -> ValueError:
    """The label card's stroke-floor ValueError for this line, prefixed with its name."""
    path, style = FONTS[FACE[name]]
    try:
        layout_text(text, box_w, box_h, 0.0, RAISE_H, FLOOR, path, style, MAX_LINES[name])
    except ValueError as err:
        return ValueError(f'{name}: {err}')
    return ValueError(f'{name}: {text!r} does not hold the {THRESHOLD:g} mm stroke in its band')


# The printable bed (holders.printer); the sign prints flat, width along X.
MAX_WIDTH = BED_X
MAX_HEIGHT = BED_Y


def min_height(values: dict) -> float:
    """Smallest plate height (0.1 mm up) whose layout holds the bands and the art row."""
    lo, hi = 0.0, 2000.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if _frame(values, mid) else (mid, hi)
    return round(hi + 0.05, 1)


def validate(values: dict) -> None:
    """Cross-param guards; each ValueError names the bound and the minimum."""
    w, h, m, qr = values['width'], values['height'], values['margin'], values['qr_size']
    min_w = 2 * (signs.POCKET_OFFSET + signs.POCKET_W / 2) + 2 * m
    if w < min_w:
        raise ValueError(f'width {w:g} mm < {min_w:g} mm: the pockets at '
                         f'+-{signs.POCKET_OFFSET:g} mm need width >= 2 x '
                         f'({signs.POCKET_OFFSET:g} + {signs.POCKET_W / 2:g}) + 2 x margin')
    floor = signs.min_outline_height(w, values['arch'])
    if h < floor:
        raise ValueError(f'height {h:g} mm leaves no straight side under the '
                         f'{signs.arch_radius(w, values["arch"]):g} mm arch: height must be '
                         f'>= {floor:g} mm for width {w:g} mm ({values["arch"]} arch)')
    if not values['host'].strip():
        raise ValueError('host is blank: the QR encodes https://{host}')
    if art_width(qr, m) > w - 2 * m:
        raise ValueError(f'qr_size {qr:g} mm: the art row (ghost + margin + QR) is '
                         f'{art_width(qr, m):.1f} mm, wider than width - 2 x margin = '
                         f'{w - 2 * m:g} mm')
    signs.qr_regions(qr_data(values), qr)  # the pitch guard
    if values['retention'] == 'pin':
        signs.check_pin_thickness(values['thickness'])
    if _frame(values) is None:
        need = min_height(values)
        advice = (f'height must be >= {need:g} mm for these values' if need <= MAX_HEIGHT else
                  f'that needs height >= {need:g} mm, above the {MAX_HEIGHT:g} mm maximum: '
                  f'reduce qr_size or margin')
        raise ValueError(
            f'height {h:g} mm cannot hold the {qr:g} mm art row and the text bands '
            f'({MIN_TEXT_BUDGET:g} mm) between the {m:g} mm margin floor and the arch; '
            f'{advice}')


def plate(values: dict) -> Part:
    """The uncoloured plate in the print frame: outline, rim chamfers, pockets, pin hole."""
    w, h, t = values['width'], values['height'], values['thickness']
    blank = extrude(signs.outline(w, h, values['arch']), t)
    rims = blank.faces().sort_by(Axis.Z)
    out = chamfer(rims[0].edges() + rims[-1].edges(), EDGE_CHAMFER)
    for x in signs.POCKET_XS:
        out -= Pos(x, signs.POCKET_DEPTH / 2 - 0.5, t / 2) * Box(
            signs.POCKET_W, signs.POCKET_DEPTH + 1, signs.pocket_height(t))
    if values['retention'] == 'pin':
        out -= signs.pin_hole(w, t)
    return out


def _region_part(geom, depth: float) -> Part:
    """A shapely (multi)polygon extruded Z 0..depth, one solid per polygon."""
    def wire(ring):
        return Wire.make_polygon([Vector(x, y, 0) for x, y in ring.coords[:-1]], close=True)
    solids = []
    for poly in getattr(geom, 'geoms', [geom]):
        poly = orient(poly, 1.0)  # CCW outside: a CW face extrudes an inside-out solid
        face = Face(wire(poly.exterior), [wire(r) for r in poly.interiors])
        solids += extrude(face, depth).solids()
    return Part(Compound(solids).wrapped)


def qr_panel(values: dict):
    """(dark, light) shapely regions of the QR panel centred on the origin: the
    bone panel is the qr_size square with QR_CORNER_R corners, minus dark."""
    qr = values['qr_size']
    dark, _ = signs.qr_regions(qr_data(values), qr)
    half = qr / 2 - QR_CORNER_R
    panel = box(-half, -half, half, half).buffer(QR_CORNER_R, quad_segs=32)
    return dark, panel.difference(dark).simplify(0)


def _fit_line(name: str, values: dict, frame: dict) -> Part:
    """One line in its band at its chosen wrap, inside the chord at the band top."""
    y_lo, y_hi = frame['bands'][name]
    chord = signs.inner_width(frame['region'], y_hi)
    path, style = FONTS[FACE[name]]
    try:
        fitted = layout_text(frame['lines'][name], chord, y_hi - y_lo, 0.0, RAISE_H, FLOOR,
                             path, style, max_lines=1)
    except ValueError:
        raise _line_error(name, _line(values, name), chord, y_hi - y_lo) from None
    return Pos(0, (y_lo + y_hi) / 2) * _merge_overlaps(fitted.part)


def _merge_overlaps(part: Part) -> Part:
    """Fuse glyph solids whose boxes overlap: Creepster kerns some pairs into
    each other ('x' into 't' by 0.015 mm^3), and two interpenetrating solids
    in one compound make the plate fuse invalid. Disjoint glyphs pass through."""
    groups: list[list] = []
    for solid in part.solids():
        bb = solid.bounding_box()
        hits = [g for g in groups if any(bb.overlaps(o.bounding_box()) for o in g)]
        merged = [solid] + [o for g in hits for o in g]
        groups = [g for g in groups if g not in hits] + [merged]
    out = []
    for g in groups:
        out += g if len(g) == 1 else reduce(lambda a, b: a.fuse(b), g).solids()
    return Part(Compound(out).wrapped)


def features(values: dict) -> dict[str, tuple[str, Part]]:
    """Unfolded raised features, Z 0..RAISE_H in the plate frame: name -> (role, part).

    Text lines by their Param name, 'rule' (over footer_1), 'ghost:<role>'
    per motif role, 'qr_light' (bone) and 'qr_dark' (ink). Blank lines are absent.
    """
    validate(values)
    frame = _frame(values)
    if frame['overflow']:
        name = max(frame['need'], key=frame['need'].get)
        y_lo, y_hi = frame['bands'][name]
        raise _line_error(name, _line(values, name),
                          signs.inner_width(frame['region'], y_hi), y_hi - y_lo)
    out = {n: (LINE_ROLE[n], _fit_line(n, values, frame)) for n in frame['lines']}
    if 'footer_1' in frame['bands']:
        y = frame['bands']['footer_1'][1] + frame['gap'] / 2
        chord = signs.inner_width(frame['region'], y + RULE_W / 2)
        out['rule'] = ('dim', Pos(0, y, RAISE_H / 2) * Box(chord, RULE_W, RAISE_H))
    ghost_at, qr_at = art_layout(values, frame)
    for role, region in sign_ghost.regions(GHOST_SHARE * values['qr_size']).items():
        out[f'ghost:{role}'] = (role, Pos(*ghost_at) * extrude(region, RAISE_H))
    dark, light = qr_panel(values)
    out['qr_light'] = ('bone', Pos(*qr_at) * _region_part(light, RAISE_H))
    out['qr_dark'] = ('ink', Pos(*qr_at) * _region_part(dark, RAISE_H))
    return out


def art_layout(values: dict, frame: dict) -> tuple[tuple[float, float], tuple[float, float]]:
    """(ghost box lower-left, QR centre): the pair centred on X = 0 with a
    margin gap, both centred on the art row (the poster's align-items: center)."""
    m, qr = values['margin'], values['qr_size']
    y_lo, y_hi = frame['bands']['art']
    yc, left, gh = (y_lo + y_hi) / 2, -art_width(qr, m) / 2, GHOST_SHARE * qr
    return (left, yc - gh / 2), (left + sign_ghost.width(gh) + m + qr / 2, yc)


def _union(parts: list[Part]) -> Part:
    return _glyph_order(Part(Compound([s for p in parts for s in p.solids()]).wrapped))


def assemble(values: dict, feats: dict[str, tuple[str, Part]]) -> list[ColourPart]:
    """Fold the features into filaments: [(name, part, rgba)], part 0 the base.

    Ghost regions that fold into one filament share faces, so they are fused
    into one body; everything else in a filament is disjoint and compounds.
    """
    n, t = values['colours'], values['thickness']
    groups: dict[str, list[Part]] = {}
    ghosts: dict[str, list[Part]] = {}
    for name, (role, part) in feats.items():
        fil = filament(role, n)
        if fil != HOLE:
            (ghosts if name.startswith('ghost:') else groups).setdefault(fil, []).append(part)
    for fil, parts in ghosts.items():
        groups.setdefault(fil, []).append(reduce(lambda a, b: a + b, parts))
    out = [('base', plate(values), RGBA['base'])]
    return out + [(r, Pos(0, 0, t) * _union(groups[r]), RGBA[r]) for r in ROLES[1:] if r in groups]


def colour_parts(values: dict) -> list[ColourPart]:
    """[(name, part, rgba)] in the print frame; part 0 is the base (filament 1)."""
    return assemble(values, features(values))


def preview_colour_parts(values: dict) -> list[ColourPart]:
    """The viewer GLB's materials: one per filament."""
    return colour_parts(values)


def build(values: dict) -> Part:
    """The plate with every raised feature fused on: one solid."""
    parts = [shape for _, shape, _ in colour_parts(values)]
    return parts[0].fuse(*parts[1:]).clean()


def audit_exclusions(values: dict) -> list[tuple[float, ...]]:
    """Approved regions, as thin exact boxes: each pocket roof (an 8 mm
    bridge), with a pin the hole's 1.33 mm flat roof, and the slab the raised
    features stand in (the label card's exclusion: tapered glyph terminals
    read thin by the wall march), from the margin floor up. The tests measure
    every span before excluding its plane, and check the slab holds every
    raised feature and nothing else."""
    t, w, h, m = values['thickness'], values['width'], values['height'], values['margin']
    roof = t - signs.SKIN
    out = [(x - signs.POCKET_W / 2, -0.001, roof - 0.001,
            x + signs.POCKET_W / 2, signs.POCKET_DEPTH + 0.001, roof + 0.001)
           for x in signs.POCKET_XS]
    if values['retention'] == 'pin':
        z = t / 2 + signs.PIN_D / 2
        y, half = signs.PIN_FROM_BOTTOM, signs.PIN_D / 2
        out.append((-w / 2 - 0.001, y - half, z - 0.001, w / 2 + 0.001, y + half, z + 0.001))
    # Z floor 1e-6 under the top face, so every raised wall's box sits wholly
    # inside and the audit skips it without sampling (t + 1e-4 sampled all
    # ~4000 glyph walls: > 17 min CPU vs 52 s at the default preset).
    out.append((-w / 2, m - 0.001, t - 1e-6, w / 2, h, t + RAISE_H + 0.001))
    return out


def _text(name: str, default: str, label: str, max_length: int = MAX_TEXT_LENGTH) -> Param:
    return Param(name, 'string', default, label=label, group='Text',
                 max_length=max_length, charset=TEXT_CHARSET)


PARAMS = (
    Param('width', 'number', 240.0, label='Width', group='Plate', unit='mm',
          min=100.0, max=MAX_WIDTH, step=1.0),
    Param('height', 'number', 300.0, label='Height', group='Plate', unit='mm',
          min=150.0, max=MAX_HEIGHT, step=1.0),
    Param('thickness', 'number', 6.0, label='Thickness', group='Plate', unit='mm',
          min=5.0, max=12.0, step=0.2),
    Param('arch', 'enum', 'round', label='Arch', group='Plate', choices=('round', 'shoulder')),
    Param('margin', 'number', 8.0, label='Margin', group='Plate', unit='mm',
          min=3.0, max=20.0, step=0.5),
    _text('eyebrow', 'Poppy Street Spooks', 'Eyebrow (printed in capitals)'),
    _text('title', 'Pick the next song!', 'Title'),
    _text('scan_line', 'Scan to request a song', 'Scan line'),
    _text('detail_1', 'The spooks sing whatever the street picks. Three requests per phone.',
          'Detail 1', DETAIL_MAX_LENGTH),
    _text('detail_2', 'No app needed. Or visit', 'Detail 2', DETAIL_MAX_LENGTH),
    _text('host', 'poppystreetspooks.com', 'Host (the QR encodes https://host)'),
    _text('footer_1', 'Show runs dusk to 9 pm', 'Footer'),
    Param('qr_size', 'number', 100.0, label='QR size', group='QR', unit='mm',
          min=50.0, max=300.0, step=1.0,
          description='Includes the 4-module quiet zone; modules must be >= 2 mm.'),
    Param('colours', 'integer', 8, label='Colours (filaments)', group='Style',
          min=2, max=8, step=1,
          description='Filaments including the plate; fewer colours fold the extra roles.'),
    Param('retention', 'enum', 'friction', label='Stake retention', group='Stake',
          choices=('friction', 'pin'),
          description="'pin' adds a 3.2 mm cross-hole; needs thickness >= 7.8 mm."),
)

DEFAULTS = {p.name: p.default for p in PARAMS}
# Through the default art row (ghost + QR); a constant because the layout
# measures the text (about a minute) and registration must stay cheap. A test
# pins it inside the default layout's art row.
ART_SECTION_Y = 178.0

SPEC = register(ModelSpec(
    name='holder_tombstone_sign',
    build=build,
    title='Tombstone sign',
    description=('Song-request tombstone sign in the poster look: eyebrow, Creepster title, '
                 'the ghost-with-poppy, a QR code and the show details raised in up to '
                 'eight colours, printed face up; two pockets in the bottom edge take the '
                 'separately printed stake.'),
    category_id='household',
    tags=('sign', 'multi-colour'),
    print_orientation=(0, 0, 1),  # flat, face up
    params=PARAMS,
    presets=(
        Preset('default', 'Eight colours', {}),
        Preset('one-ams', 'One AMS (four colours)', {'colours': 4}),
        Preset('two-colour', 'Two colours (bone on ground)', {'colours': 2}),
        Preset('pinned', 'Pinned stake (8 mm plate)', {'thickness': 8.0, 'retention': 'pin'}),
        Preset('small', 'Small (160 x 200, no detail lines)',
               {'width': 160.0, 'height': 200.0, 'qr_size': 74.0,
                'detail_1': '', 'detail_2': ''}),
    ),
    # Pocket plane first: the review sheet goldens sections[0] (the joint cut).
    review_sections=(
        PlaneSpec((signs.POCKET_OFFSET, signs.POCKET_DEPTH / 2, DEFAULTS['thickness'] / 2),
                  (1, 0, 0), 'pocket at X = +40'),
        PlaneSpec((0, ART_SECTION_Y, DEFAULTS['thickness'] / 2), (0, 1, 0), 'art row'),
    ),
))
