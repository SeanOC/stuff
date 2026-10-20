"""Tombstone sign (epic pst-tl4ac; S1 pst-tl4ac.1, S3 .3, S4 .4): the poster look.

A plate in the classic tombstone outline (holders/signs.py outline: straight
sides, flat bottom, a 'round' full-width arch or a 'shoulder' arch a third
of the width) carrying the song-request poster (poppystreetspooks.com/sign)
as RAISED multi-colour features, with two tenon pockets in its bottom edge
for the separately printed stake (S2). The pocket / tenon / pin numbers live
in holders/signs.py, which the stake imports too.

Printed FACE UP: every colour feature stands RAISE_H (0.6 mm = 3 layers)
proud of the top face, modelled unmirrored in the print frame. All raised
regions share the one Z t..t+RAISE_H slab and never overlap.

Layout, top to bottom, inside a `margin` inset of the outline (S4,
pst-tl4ac.4): eyebrow (caps, Lexend Medium), title (Creepster, one line else
two), ART ROW (the ghost-with-poppy at left, the QR panel at right, centred
as a pair with a 2 U gap; ghost height GHOST_SHARE x qr_size), scan_line and
host (Lexend Bold), and the footer_1 line (Lexend Medium) under a thin
raised rule. Blank lines take no band and no gap; the rule exists only with
a footer.

Type classes: every line is set at a class cap height (the face's 'H'),
TITLE_CAP 20 / LINE_CAP 11 (scan_line, host) / SMALL_CAP 8 (footer_1) /
EYEBROW_CAP 7, times one type scale s. Rhythm: the unit U = margin x RHYTHM
x s; groups [eyebrow, title] [art] [scan_line, host] [rule, footer_1], 1 U
within a group, 2 U between groups, RULE_CLEAR U either side of the rule
(replacing the gaps there). The stack runs from the content top (where the
inset arch is CONTENT_CHORD of the inset width) down. Per line, at its top
y: the wrap is the fewest lines whose width fits the inset chord there (else
the most); a line wider than the inset box shrinks alone to the box
(width-bound); a line still wider than the chord moves down to the highest y
whose chord holds it (the arch push: the eyebrow at the default). s is the
largest in (0, 1] whose stack bottoms out at or above the margin; s < 1
scales the text and U, never the art row or the margin. At s = 1 the
leftover is split equally into the two gaps flanking the art row, so the
footer sits on the margin. A line under the raised stroke floor makes the
plate too short (the 'minimum height' ValueError), unless it is width-bound:
then it raises the label card's stroke ValueError naming the line.

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
the pin hole are mating edges and stay sharp. Glyph, art and QR edges are
the feature and stay sharp, as on the label card. Raised features add
material, so they may run down to the margin over the pockets.

Rims (pst-aw7p3, after the first test print lifted an edge strip): the TOP
rim (printed last) is rounded over `edge_round` (2.5): a round-over on an
upper outer edge makes every layer smaller than the one below, so it never
overhangs. The BED rim takes a 45-degree `bed_chamfer` (1.0, never a
fillet on the bed side): it beats elephant's foot and gives a spatula a
clean entry under the plate; it is wider than the guideline's 0.3-0.5 on
purpose. The straight bottom edge (Y = 0, where the pockets enter, SKIN 1.2
from each face) keeps EDGE_CHAMFER's 0.4 on both rims: a 2.5 round-over
there would cut through the skin over each pocket mouth. The rim is one
tangent-continuous loop, which OCCT eases whole, so each rim changes size
INSIDE the two CORNER_R plan corners: the top is one evolving-radius
fillet (0.4 along Y = 0, ramping to edge_round round each corner), so on
that edge it is a 0.4 round, not a chamfer; the bed is cut by a swept 45-
degree cutter whose size ramps 0.4 -> bed_chamfer the same way.
edge_round = 0 is the former 0.4 chamfer on the whole top rim.

Worst-case load: wind on the face, bending the plate about the X axis at
the pockets; the tenons carry it into the stake. The load path runs along
the printed layers (the plate prints flat), so the bending stress is in
the strong in-plane direction. PLA or PCTG; PCTG for a sign left outdoors.
"""
from __future__ import annotations

from functools import lru_cache, reduce
from pathlib import Path

from build123d import Axis, Box, Compound, Edge, Face, FontStyle, Part, Pos, Solid, Vector, \
    Wire, chamfer, extrude
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCP.gp import gp_Dir
from OCP.TopoDS import TopoDS
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
EDGE_CHAMFER = 0.4          # both rims of the Y = 0 pocket edge; the whole top rim at edge_round 0
QR_CORNER_R = 6.0           # bone panel rounding, inside the 4-module quiet zone
GHOST_SHARE = 0.65          # ghost height / panel height (the poster's is 0.47)
CONTENT_CHORD = 0.5         # content stops where the arch is this share of the inset width
RHYTHM = 1 / 3              # rhythm unit U = margin x this x s
RULE_CLEAR = 1.5            # U clear above and below the rule, replacing the gaps there

_FONTS = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
FONTS = {'lexend-medium': (_FONTS / 'lexend' / 'Lexend-Medium.ttf', FontStyle.REGULAR),
         'lexend-bold': (_FONTS / 'lexend' / 'Lexend-Bold.ttf', FontStyle.BOLD),
         'creepster': (_FONTS / 'creepster' / 'Creepster-Regular.ttf', FontStyle.REGULAR)}

# Text bands, top to bottom; 'art' is the ghost + QR row, 'rule' the line
# over the footer (present only with a footer).
LINES = ('eyebrow', 'title', 'scan_line', 'host', 'footer_1')
ORDER = ('eyebrow', 'title', 'art', 'scan_line', 'host', 'rule', 'footer_1')
GROUP = {'eyebrow': 0, 'title': 0, 'art': 1, 'scan_line': 2, 'host': 2, 'rule': 3,
         'footer_1': 3}
# Type classes: cap height (mm, the face's 'H') at type scale s = 1.
TITLE_CAP, LINE_CAP, SMALL_CAP, EYEBROW_CAP = 20.0, 11.0, 8.0, 7.0
CAP = {'eyebrow': EYEBROW_CAP, 'title': TITLE_CAP, 'scan_line': LINE_CAP, 'host': LINE_CAP,
       'footer_1': SMALL_CAP}
FACE = {'eyebrow': 'lexend-medium', 'title': 'creepster', 'scan_line': 'lexend-bold',
        'host': 'lexend-bold', 'footer_1': 'lexend-medium'}
MAX_LINES = {'eyebrow': 1, 'title': 2, 'scan_line': 1, 'host': 1, 'footer_1': 1}
LINE_ROLE = {'eyebrow': 'dim', 'title': 'pumpkin', 'scan_line': 'bone', 'host': 'pumpkin',
             'footer_1': 'dim'}

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


@lru_cache(maxsize=None)
def cap_height(face: str) -> float:
    """The face's 'H' ink height at NOMINAL_SIZE: a band's cap is set in these units."""
    path, style = FONTS[face]
    return text_sketch('H', path=path, style=style).bounding_box().size.Y


def line_ink(name: str, candidate: str, cap: float) -> tuple[float, float, float]:
    """(width, height, stroke) of the candidate set at this cap height."""
    face = FACE[name]
    w, h, stroke = _ink(candidate, face)
    k = cap / cap_height(face)
    return k * w, k * h, k * stroke


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


def art_width(qr: float, gap: float) -> float:
    """Ghost box + the pair gap + QR panel: the art row's width at its top."""
    return sign_ghost.width(GHOST_SHARE * qr) + gap + qr


def _gap(above: str, below: str, unit: float) -> float:
    """1 U within a group, 2 U between groups; RULE_CLEAR U either side of the rule."""
    if 'rule' in (above, below):
        return RULE_CLEAR * unit
    return unit if GROUP[above] == GROUP[below] else 2 * unit


def _stack(values: dict, region, top: float, s: float, leftover: float) -> dict | None:
    """The bands stacked down from top at type scale s, with leftover split
    equally into the gaps flanking the art row. None if a line cannot fit
    the inset chord even at the margin floor."""
    w, m, qr = values['width'], values['margin'], values['qr_size']
    unit, box_w = m * RHYTHM * s, w - 2 * m
    order = [n for n in ORDER if n == 'art' or values['footer_1' if n == 'rule' else n].strip()]
    i = order.index('art')
    flanks = [p for p in (i, i + 1) if 0 < p < len(order)]  # gaps above order[p]
    bands, lines, caps, bound = {}, {}, {}, {}
    y = top
    for p, n in enumerate(order):
        if p:
            y -= _gap(order[p - 1], n, unit) + (leftover / len(flanks) if p in flanks else 0.0)
        if n in ('art', 'rule'):
            h = qr if n == 'art' else RULE_W
        else:
            cap, chord = CAP[n] * s, signs.inner_width(region, y)
            cands = [(c, line_ink(n, c, cap)[0]) for c in _candidates(n, _line(values, n))]
            text, width = next((c for c in cands if c[1] <= chord + 1e-9), cands[-1])
            bound[n] = width > box_w
            if bound[n]:  # width-bound: this line alone shrinks to the inset box
                cap, width = cap * box_w / width, box_w
            pushed = _chord_cap(region, y, width, m)
            if pushed is None:
                return None
            y, lines[n], caps[n] = pushed, text, cap
            h = line_ink(n, text, cap)[1]
        bands[n] = (y - h, y)
        y -= h
    return {'bands': bands, 'lines': lines, 'caps': caps, 'bound': bound, 'unit': unit,
            'bottom': y}


def _frame(values: dict, height: float | None = None) -> dict | None:
    """Band placement (pure 2D), or None when height cannot hold it.

    Returns region (the margin-inset outline, shapely), top, the type scale
    s, leftover, unit (the rhythm unit U), and per present line its wrap
    ('lines'), cap height ('caps') and whether it is width-bound ('bound');
    'bands' {name: (y_lo, y_hi)} covers every present line, 'art' and 'rule'.
    s is the largest in (0, 1] whose stack bottoms out at or above the
    margin; leftover (s = 1 only) goes to the art row's flanking gaps. A line
    under its stroke floor makes the height too small (None), unless it is
    width-bound, where no height helps: that raises the line's stroke error.
    """
    w, m, qr = values['width'], values['margin'], values['qr_size']
    h = values['height'] if height is None else height
    region = signs.outline_region(w, h, values['arch']).buffer(-m)
    top = _top(region, w, h, m)

    def stack(s: float, leftover: float = 0.0) -> dict | None:
        st = _stack(values, region, top, s, leftover)
        return st if st is not None and st['bottom'] >= m - 1e-9 else None

    s, leftover, st = 1.0, 0.0, stack(1.0)
    if st is None:
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if stack(mid) else (lo, mid)
        s, st = lo, stack(lo) if lo > 0 else None
        if st is None:
            return None
    else:
        for _ in range(8):  # a band moved lower may need less push: settles fast
            leftover += st['bottom'] - m
            st = _stack(values, region, top, 1.0, leftover)
            if st is None or abs(st['bottom'] - m) < 1e-9:
                break
        if st is None or st['bottom'] < m - 1e-6:
            return None
    for n, cap in st['caps'].items():
        width, height_, stroke = line_ink(n, st['lines'][n], cap)
        if stroke < THRESHOLD:
            if st['bound'][n]:
                raise _line_error(n, _line(values, n), w - 2 * m, height_)
            return None
    if signs.inner_width(region, st['bands']['art'][1]) < art_width(qr, 2 * st['unit']):
        return None
    return {'region': region, 'top': top, 's': s, 'leftover': leftover, **st}


def _line_error(name: str, text: str, box_w: float, box_h: float) -> ValueError:
    """The label card's stroke-floor ValueError for this line, prefixed with its name."""
    path, style = FONTS[FACE[name]]
    try:
        layout_text(text, box_w, box_h, 0.0, RAISE_H, FLOOR, path, style, MAX_LINES[name],
                    stroke_only=True)
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
    art = art_width(qr, 2 * m * RHYTHM)
    if art > w - 2 * m:
        raise ValueError(f'qr_size {qr:g} mm: the art row (ghost + 2/3 margin + QR) is '
                         f'{art:.1f} mm, wider than width - 2 x margin = {w - 2 * m:g} mm')
    signs.qr_regions(qr_data(values), qr)  # the pitch guard
    if values['retention'] == 'pin':
        signs.check_pin_thickness(values['thickness'])
    r, d, t = values['edge_round'], values['bed_chamfer'], values['thickness']
    if r + FLOOR >= m:
        raise ValueError(f'edge_round {r:g} mm + the {FLOOR:g} mm stroke floor must stay '
                         f'< margin {m:g} mm: the round-over would eat the raised features '
                         f'at the margin; edge_round must be < {m - FLOOR:g} mm')
    if max(r, EDGE_CHAMFER) + d >= t:
        raise ValueError(f'edge_round {r:g} mm + bed_chamfer {d:g} mm must stay < thickness '
                         f'{t:g} mm: the two rims would meet')
    if _frame(values) is None:
        need = min_height(values)
        advice = (f'height must be >= {need:g} mm for these values' if need <= MAX_HEIGHT else
                  f'that needs height >= {need:g} mm, above the {MAX_HEIGHT:g} mm maximum: '
                  f'reduce qr_size or margin')
        raise ValueError(
            f'height {h:g} mm cannot hold the {qr:g} mm art row and the text above its '
            f'stroke floor between the {m:g} mm margin floor and the arch; {advice}')


def _on_pocket_edge(point) -> bool:
    return abs(point.Y) < 1e-6


def _top_rim(blank: Part, r: float) -> Part:
    """The top rim eased: a round-over r ramping to EDGE_CHAMFER on the Y = 0
    edge across each plan corner (one evolving-radius fillet, since OCCT
    eases the whole tangent loop), or at r = 0 a plain EDGE_CHAMFER."""
    top = blank.faces().sort_by(Axis.Z)[-1]
    if r == 0:
        return chamfer(top.edges(), EDGE_CHAMFER)
    mk = BRepFilletAPI_MakeFillet(blank.wrapped)
    mk.Add(EDGE_CHAMFER, top.edges()[0].wrapped)  # the whole loop is one contour
    for i in range(1, mk.NbEdges(1) + 1):
        edge = Edge(mk.Edge(1, i))
        r0, r1 = (EDGE_CHAMFER if _on_pocket_edge(edge.position_at(u)) else r for u in (0, 1))
        mk.SetRadius(r0, r1, 1, i)
    mk.Build()
    if not mk.IsDone():
        raise ValueError(f'edge_round {r:g} mm: the top rim round-over failed')
    return Part(mk.Shape())


def _bed_rim_cutter(outline: Face, d: float) -> Part:
    """The bed rim's 45-degree chamfer as a cutter: per outline edge, a
    swept triangle whose chamfer leg runs from (d inward, Z 0) to (the wall,
    Z d), d being EDGE_CHAMFER at a Y = 0 vertex and `d` elsewhere, so it
    ramps across each plan corner. The other two legs stand outside the
    plate, so every cut crosses the bed and the wall transversally."""
    up = Vector(0, 0, 1)
    def section(point, tangent):
        size = EDGE_CHAMFER if _on_pocket_edge(point) else d
        inward = up.cross(tangent).normalized()
        if not outline.is_inside(point + inward * 0.05):
            inward = -inward
        return Wire.make_polygon([point + inward * (2 * size) - up * size,
                                  point - inward * size + up * (2 * size),
                                  point - inward * size - up * size], close=True)
    cutters = []
    for edge in outline.outer_wire().edges():
        spine = Wire([edge])
        pipe = BRepOffsetAPI_MakePipeShell(spine.wrapped)
        pipe.SetMode(gp_Dir(0, 0, 1))  # sections stay vertical
        for u in (0, 1):
            point = edge.position_at(u)
            vertex = min(spine.vertices(), key=lambda v: (Vector(v) - point).length)
            pipe.Add(section(point, edge.tangent_at(u)).wrapped,
                     TopoDS.Vertex(vertex.wrapped), False, False)
        pipe.Build()
        pipe.MakeSolid()
        cutters.append(Solid(pipe.Shape()))
    return cutters[0].fuse(*cutters[1:]).clean()


def plate(values: dict) -> Part:
    """The uncoloured plate in the print frame: outline, eased rims, pockets, pin hole."""
    w, h, t = values['width'], values['height'], values['thickness']
    outline = signs.outline(w, h, values['arch'])
    out = _top_rim(extrude(outline, t), values['edge_round'])
    out -= _bed_rim_cutter(outline.faces()[0], values['bed_chamfer'])
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
                             path, style, max_lines=1, stroke_only=True)
    except ValueError:
        raise _line_error(name, _line(values, name), chord, y_hi - y_lo) from None
    return Pos(0, (y_lo + y_hi) / 2) * _merge_overlaps(fitted.part)


def _merge_overlaps(part: Part) -> Part:
    """Fuse glyph solids whose boxes overlap: Creepster kerns some pairs into
    each other ('x' into 't' by 0.015 mm^3), and two interpenetrating solids
    in one compound make the plate fuse invalid. Disjoint glyphs pass through."""
    groups: list[list] = []  # [(solid, its box)]: each box computed once
    for solid in part.solids():
        bb = solid.bounding_box()
        hits = [g for g in groups if any(bb.overlaps(o) for _, o in g)]
        merged = [(solid, bb)] + [o for g in hits for o in g]
        groups = [g for g in groups if g not in hits] + [merged]
    out = []
    for g in groups:
        solids = [s for s, _ in g]
        out += solids if len(solids) == 1 else reduce(lambda a, b: a.fuse(b), solids).solids()
    return Part(Compound(out).wrapped)


def features(values: dict) -> dict[str, tuple[str, Part]]:
    """Unfolded raised features, Z 0..RAISE_H in the plate frame: name -> (role, part).

    Text lines by their Param name, 'rule' (over footer_1), 'ghost:<role>'
    per motif role, 'qr_light' (bone) and 'qr_dark' (ink). Blank lines are absent.
    """
    validate(values)
    frame = _frame(values)
    out = {n: (LINE_ROLE[n], _fit_line(n, values, frame)) for n in frame['lines']}
    if 'rule' in frame['bands']:
        y_lo, y_hi = frame['bands']['rule']
        chord = signs.inner_width(frame['region'], y_hi)
        out['rule'] = ('dim', Pos(0, (y_lo + y_hi) / 2, RAISE_H / 2) * Box(chord, RULE_W, RAISE_H))
    ghost_at, qr_at = art_layout(values, frame)
    for role, region in sign_ghost.regions(GHOST_SHARE * values['qr_size']).items():
        out[f'ghost:{role}'] = (role, Pos(*ghost_at) * extrude(region, RAISE_H))
    dark, light = qr_panel(values)
    out['qr_light'] = ('bone', Pos(*qr_at) * _region_part(light, RAISE_H))
    out['qr_dark'] = ('ink', Pos(*qr_at) * _region_part(dark, RAISE_H))
    return out


def art_layout(values: dict, frame: dict) -> tuple[tuple[float, float], tuple[float, float]]:
    """(ghost box lower-left, QR centre): the pair centred on X = 0 with a
    2 U gap, both centred on the art row (the poster's align-items: center)."""
    qr, gap = values['qr_size'], 2 * frame['unit']
    y_lo, y_hi = frame['bands']['art']
    yc, left, gh = (y_lo + y_hi) / 2, -art_width(qr, gap) / 2, GHOST_SHARE * qr
    return (left, yc - gh / 2), (left + sign_ghost.width(gh) + gap + qr / 2, yc)


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
    Param('thickness', 'number', 8.0, label='Thickness', group='Plate', unit='mm',
          min=5.0, max=12.0, step=0.2),
    Param('arch', 'enum', 'round', label='Arch', group='Plate', choices=('round', 'shoulder')),
    Param('margin', 'number', 12.0, label='Margin', group='Plate', unit='mm',
          min=3.0, max=20.0, step=0.5),
    Param('edge_round', 'number', 2.5, label='Top edge round-over', group='Plate', unit='mm',
          min=0.0, max=4.0, step=0.5,
          description='Front-face rim; the pocket edge keeps 0.4. 0 = a 0.4 chamfer.'),
    Param('bed_chamfer', 'number', 1.0, label='Bed edge chamfer', group='Plate', unit='mm',
          min=0.4, max=1.5, step=0.1,
          description='45-degree, bed-face rim; the pocket edge keeps 0.4.'),
    _text('eyebrow', 'Poppy Street Spooks', 'Eyebrow (printed in capitals)'),
    _text('title', 'Pick the next song!', 'Title'),
    _text('scan_line', 'Scan to request a song', 'Scan line'),
    _text('host', 'poppystreetspooks.com', 'Host (the QR encodes https://host)'),
    _text('footer_1', 'Show runs dusk to 9 pm', 'Footer'),
    Param('qr_size', 'number', 120.0, label='QR size', group='QR', unit='mm',
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
ART_SECTION_Y = 142.4

SPEC = register(ModelSpec(
    name='holder_tombstone_sign',
    build=build,
    title='Tombstone sign',
    description=('Song-request tombstone sign in the poster look: eyebrow, Creepster title, '
                 'the ghost-with-poppy, a QR code, the scan line, the site and the show '
                 'times raised in up to eight colours, printed face up; two pockets in the '
                 'bottom edge take the separately printed stake.'),
    category_id='household',
    tags=('sign', 'multi-colour'),
    print_orientation=(0, 0, 1),  # flat, face up
    params=PARAMS,
    presets=(
        Preset('default', 'Eight colours', {}),
        Preset('one-ams', 'One AMS (four colours)', {'colours': 4}),
        Preset('two-colour', 'Two colours (bone on ground)', {'colours': 2}),
        Preset('pinned', 'Pinned stake (8 mm plate)', {'thickness': 8.0, 'retention': 'pin'}),
        Preset('small', 'Small (160 x 240)',
               {'width': 160.0, 'height': 240.0, 'qr_size': 74.0}),
    ),
    # Pocket plane first: the review sheet goldens sections[0] (the joint cut).
    review_sections=(
        PlaneSpec((signs.POCKET_OFFSET, signs.POCKET_DEPTH / 2, DEFAULTS['thickness'] / 2),
                  (1, 0, 0), 'pocket at X = +40'),
        PlaneSpec((0, ART_SECTION_Y, DEFAULTS['thickness'] / 2), (0, 1, 0), 'art row'),
    ),
))
