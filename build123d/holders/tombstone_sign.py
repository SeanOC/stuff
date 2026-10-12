"""Tombstone sign (epic pst-tl4ac, S1 pst-tl4ac.1): a flat song-request sign.

A plate in the classic tombstone outline (holders/signs.py outline: straight
sides, flat bottom, a 'round' full-width arch or a 'shoulder' arch a third
of the width) carrying four lines of text and a QR code for url, with two
tenon pockets in its bottom edge for the separately printed stake (S2).
The pocket / tenon / pin numbers live in holders/signs.py, which the stake
imports too.

Layout, top to bottom, inside a `margin` inset of the outline: title,
headline, QR block, scan_line, host. Nothing sits below INLAY_FLOOR (35 mm,
the pocket depth: a 0.6 inlay over a pocket would leave 0.6 mm of skin).
The content stops where the arch narrows to half the inset width; between
that top and the floor the QR takes qr_size, the gaps take margin each and
the four text bands share the rest 30 / 25 / 25 / 20 % (title, headline,
scan_line, host). Each line is autoscaled and centred in its band by
labels.label_text.layout_text (one line, else two; ValueError naming the
stroke and the longest fitting text below the stroke floor). The band must
be at least MIN_TEXT_BUDGET tall in total and the QR must fit under the
arch; otherwise a ValueError names the minimum height.

QR: segno at error level M, a 4-module quiet zone, qr_size square including
the quiet zone; pitch = qr_size / modules must be >= 2.0 mm (signs.py).

text_style:
  inlaid (default): printed FACE DOWN, every colour a flush INLAY_DEPTH
      inlay in the bed face, modelled in the print frame and mirrored about
      YZ like the label card (D3); the viewer opens on the bottom face.
      colours='four': base (stone, filament 1), bone (headline, scan_line,
      host and the QR light field), ink (QR dark modules), accent (title).
      'three': the title joins bone. 'two': no bone; text and QR dark
      modules are ink on the stone, the stone is the QR light field.
  raised: the single-colour fallback (label card D11), printed FACE UP with
      the text and the QR dark modules INLAY_DEPTH proud of the top face.

build() returns the assembled plate (what the print audit and the plain STL
see; inlays are flush, so it is the plate itself); colour_parts() the
filament bodies for the 3MF and the per-part STLs (tag "multi-colour");
preview_colour_parts() the viewer GLB's materials for inlaid presets.

Pockets print as flat 8 mm roofs over the void (bridges <= MAX_BRIDGE_MM;
audit_exclusions lists those planes, measured by the tests first). The
pin hole is a flat-topped teardrop (signs.pin_profile). Pocket mouths and
the pin hole are mating edges and stay sharp; the plate rims carry a 0.4
chamfer on both faces (bed: elephant's foot). Glyph and QR edges are the
feature and stay sharp, as on the label card.

Worst-case load: wind on the face, bending the plate about the X axis at
the pockets; the tenons carry it into the stake. The load path runs along
the printed layers (the plate prints flat), so the bending stress is in
the strong in-plane direction. PLA or PCTG; PCTG for a sign left outdoors.
"""
from __future__ import annotations

from build123d import (Axis, Box, Compound, Face, Part, Plane, Pos, Vector, Wire, chamfer,
                       extrude, mirror)
from holders import signs
from holders.label_card import _glyph_order
from holders.registry import ColourPart, ModelSpec, Param, Preset, register
from labels.constants import (INLAY_DEPTH, MAX_TEXT_LENGTH, STROKE_FLOOR_INLAID,
                              STROKE_FLOOR_RAISED, TEXT_CHARSET)
from labels.label_text import layout_text
from scripts.thumbnail import PlaneSpec
from shapely.geometry.polygon import orient

STROKE_FLOOR = {'inlaid': STROKE_FLOOR_INLAID, 'raised': STROKE_FLOOR_RAISED}
EDGE_CHAMFER = 0.4          # both rims, as the label card
URL_MAX_LENGTH = 64
LINES = ('title', 'headline', 'scan_line', 'host')
BAND_SHARE = {'title': 0.30, 'headline': 0.25, 'scan_line': 0.25, 'host': 0.20}
CONTENT_CHORD = 0.5         # content stops where the arch is this share of the inset width
MIN_TEXT_BUDGET = 40.0      # mm shared by the four text bands (host band >= 8)
RGBA = {'base': (0.55, 0.56, 0.58, 1.0),     # stone
        'bone': (0.93, 0.90, 0.82, 1.0),
        'ink': (0.08, 0.08, 0.08, 1.0),
        'accent': (0.93, 0.45, 0.10, 1.0)}   # pumpkin


def _top(region, width: float, height: float, margin: float) -> float:
    """Highest Y whose inset chord is >= CONTENT_CHORD of the inset width."""
    need = CONTENT_CHORD * (width - 2 * margin)
    lo, hi = signs.INLAY_FLOOR, height
    for _ in range(60):  # inner width only shrinks going up
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if signs.inner_width(region, mid) >= need else (lo, mid)
    return lo


def _frame(values: dict, height: float | None = None) -> dict | None:
    """Band and QR placement (pure 2D), or None when height cannot hold them.

    Returns {line or 'qr': (y_lo, y_hi, inset width at y_hi)} and 'region',
    the margin-inset outline (shapely).
    """
    w, m, qr = values['width'], values['margin'], values['qr_size']
    h = values['height'] if height is None else height
    region = signs.outline_region(w, h, values['arch']).buffer(-m)
    top = _top(region, w, h, m)
    budget = top - signs.INLAY_FLOOR - qr - 4 * m
    if budget < MIN_TEXT_BUDGET:
        return None
    frame, y = {'region': region}, top
    for name in ('title', 'headline', 'qr', 'scan_line', 'host'):
        size = qr if name == 'qr' else BAND_SHARE[name] * budget
        frame[name] = (y - size, y, signs.inner_width(region, y))
        y -= size + m
    if frame['qr'][2] < qr:
        return None
    return frame


def min_height(values: dict) -> float:
    """Smallest plate height (0.1 mm up) whose layout holds the text and QR."""
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
    if qr > w - 2 * m:
        raise ValueError(f'qr_size {qr:g} mm > width - 2 x margin = {w - 2 * m:g} mm')
    signs.qr_regions(values['url'], qr)  # the pitch guard
    if values['retention'] == 'pin':
        signs.check_pin_thickness(values['thickness'])
    if _frame(values) is None:
        raise ValueError(
            f'height {h:g} mm cannot hold the {qr:g} mm QR and the four text bands '
            f'({MIN_TEXT_BUDGET:g} mm) between the {signs.INLAY_FLOOR:g} mm inlay floor and '
            f'the arch; height must be >= {min_height(values):g} mm for these values')


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


def _fit_line(name: str, text: str, frame: dict, floor: float) -> Part:
    """One line laid out in its band, as wide as the arch allows at the ink's top.

    A band under the arch narrows upward, but a width-bound line is shorter
    than its band, so its ink top sits below the band top where the arch is
    wider. Bisect the box width between the band-top chord (always clear)
    and the band-centre chord for the widest box whose ink top still clears;
    a stroke-floor ValueError at a width means "wider", and is raised (with
    the line's name) only if it holds at the widest clear width.
    """
    region = frame['region']
    y_lo, y_hi, w_lo = frame[name]
    yc, band_h = (y_lo + y_hi) / 2, y_hi - y_lo
    w_hi = signs.inner_width(region, yc)

    def attempt(w):
        try:
            fitted = layout_text(text, w, band_h, 0.0, INLAY_DEPTH, floor)
        except ValueError as err:
            return None, err
        size = fitted.part.bounding_box().size
        clear = signs.inner_width(region, yc + size.Y / 2) >= size.X - 1e-6
        return (fitted if clear else False), None

    best, error = attempt(w_lo)
    for _ in range(12):
        if w_hi - w_lo < 0.1:
            break
        w = (w_lo + w_hi) / 2
        fitted, err = attempt(w)
        if fitted is False:
            w_hi = w
        else:
            w_lo = w
            if fitted is not None:
                best = fitted
            elif best is None:
                error = err
    if best is None:
        raise ValueError(f'{name}: {error}') from None
    return Pos(0, yc) * best.part


def features(values: dict) -> dict[str, list[Part]]:
    """Unmirrored colour features, Z 0..INLAY_DEPTH: each line's text and the
    QR 'dark' / 'light' regions, keyed by name (blank lines are absent)."""
    validate(values)
    frame = _frame(values)
    floor = STROKE_FLOOR[values['text_style']]
    out = {}
    for name in LINES:
        if values[name].strip():
            out[name] = _fit_line(name, values[name], frame, floor)
    dark, light = signs.qr_regions(values['url'], values['qr_size'])
    y_lo, y_hi, _ = frame['qr']
    out['dark'] = Pos(0, (y_lo + y_hi) / 2) * _region_part(dark, INLAY_DEPTH)
    out['light'] = Pos(0, (y_lo + y_hi) / 2) * _region_part(light, INLAY_DEPTH)
    return out


def _roles(values: dict) -> dict[str, tuple[str, ...]]:
    """Filament part name -> the features it carries, in filament order."""
    if values['text_style'] == 'raised':
        return {'bone': ('title', 'headline', 'scan_line', 'host', 'dark')}
    return {'four': {'bone': ('headline', 'scan_line', 'host', 'light'), 'ink': ('dark',),
                     'accent': ('title',)},
            'three': {'bone': ('title', 'headline', 'scan_line', 'host', 'light'),
                      'ink': ('dark',)},
            'two': {'ink': ('title', 'headline', 'scan_line', 'host', 'dark')},
            }[values['colours']]


def _union(parts: list[Part]) -> Part:
    return _glyph_order(Part(Compound([s for p in parts for s in p.solids()]).wrapped))


def colour_parts(values: dict) -> list[ColourPart]:
    """[(name, part, rgba)] in the print frame; part 0 is the base (filament 1)."""
    whole = plate(values)
    feats = features(values)
    named = []
    for name, keys in _roles(values).items():
        found = [feats[k] for k in keys if k in feats]
        if found:
            named.append((name, _union(found)))
    if values['text_style'] == 'raised':
        t = values['thickness']
        return [('base', whole, RGBA['base'])] + [
            (name, Pos(0, 0, t) * part, RGBA[name]) for name, part in named]
    inlays = [(name, mirror(part, Plane.YZ)) for name, part in named]
    # One cutter per pocket in the stone. Light and dark share faces, and
    # OCCT silently drops a cut whose tools touch, so a two-tone QR block
    # leaves the base as its whole square.
    used = {k for keys in _roles(values).values() for k in keys if k in feats}
    cut = [feats[k] for k in LINES if k in used]
    if 'light' in used:
        half = values['qr_size'] / 2
        y = (feats['light'].bounding_box().min.Y + feats['light'].bounding_box().max.Y) / 2
        cut.append(Pos(0, y, INLAY_DEPTH / 2) * Box(2 * half, 2 * half, INLAY_DEPTH))
    elif 'dark' in used:
        cut.append(feats['dark'])
    base = whole - mirror(_union(cut), Plane.YZ)
    return [('base', base, RGBA['base'])] + [(n, p, RGBA[n]) for n, p in inlays]


def preview_colour_parts(values: dict) -> list[ColourPart] | None:
    """The viewer GLB's materials for inlaid presets; None (one material) for raised."""
    if values['text_style'] != 'inlaid':
        return None
    return colour_parts(values)


def build(values: dict) -> Part:
    """The assembled plate. Inlays are flush, so inlaid is the plate itself."""
    if values['text_style'] == 'inlaid':
        validate(values)
        return plate(values)
    parts = [shape for _, shape, _ in colour_parts(values)]
    out = parts[0]
    for shape in parts[1:]:
        out = out + shape
    return out


def audit_exclusions(values: dict) -> list[tuple[float, ...]]:
    """Approved regions, as thin exact boxes: each pocket roof (an 8 mm
    bridge), with a pin the hole's 1.33 mm flat roof, and with raised text
    the slab the raised text and QR modules stand in (the label card's
    exclusion: tapered glyph terminals read thin by the wall march). The
    tests measure every span before excluding its plane and check the slab
    holds nothing but the raised features."""
    t, w, h = values['thickness'], values['width'], values['height']
    roof = t - signs.SKIN
    out = [(x - signs.POCKET_W / 2, -0.001, roof - 0.001,
            x + signs.POCKET_W / 2, signs.POCKET_DEPTH + 0.001, roof + 0.001)
           for x in signs.POCKET_XS]
    if values['retention'] == 'pin':
        z = t / 2 + signs.PIN_D / 2
        y, half = signs.PIN_FROM_BOTTOM, signs.PIN_D / 2
        out.append((-w / 2 - 0.001, y - half, z - 0.001, w / 2 + 0.001, y + half, z + 0.001))
    if values['text_style'] == 'raised':
        out.append((-w / 2, signs.INLAY_FLOOR, t + 1e-4, w / 2, h, t + INLAY_DEPTH + 0.001))
    return out


def _text(name: str, default: str, label: str) -> Param:
    return Param(name, 'string', default, label=label, group='Text',
                 max_length=MAX_TEXT_LENGTH, charset=TEXT_CHARSET)


PARAMS = (
    Param('width', 'number', 240.0, label='Width', group='Plate', unit='mm',
          min=100.0, max=350.0, step=1.0),
    Param('height', 'number', 300.0, label='Height', group='Plate', unit='mm',
          min=150.0, max=320.0, step=1.0),
    Param('thickness', 'number', 6.0, label='Thickness', group='Plate', unit='mm',
          min=5.0, max=12.0, step=0.2),
    Param('arch', 'enum', 'round', label='Arch', group='Plate', choices=('round', 'shoulder')),
    Param('margin', 'number', 6.0, label='Margin', group='Plate', unit='mm',
          min=3.0, max=20.0, step=0.5),
    _text('title', 'Poppy Street Spooks', 'Title'),
    _text('headline', 'Pick the next song!', 'Headline'),
    _text('scan_line', 'Scan to request a song', 'Scan line'),
    _text('host', 'poppystreetspooks.com', 'Host'),
    Param('url', 'string', 'https://poppystreetspooks.com', label='QR link', group='QR',
          max_length=URL_MAX_LENGTH, charset=TEXT_CHARSET),
    Param('qr_size', 'number', 100.0, label='QR size', group='QR', unit='mm',
          min=50.0, max=300.0, step=1.0,
          description='Includes the 4-module quiet zone; modules must be >= 2 mm.'),
    Param('colours', 'enum', 'four', label='Colours', group='Style',
          choices=('four', 'three', 'two')),
    Param('text_style', 'enum', 'inlaid', label='Text style', group='Style',
          choices=('inlaid', 'raised')),
    Param('retention', 'enum', 'friction', label='Stake retention', group='Stake',
          choices=('friction', 'pin'),
          description="'pin' adds a 3.2 mm cross-hole; needs thickness >= 7.8 mm."),
)

DEFAULTS = {p.name: p.default for p in PARAMS}
_QR = _frame(DEFAULTS)['qr']

SPEC = register(ModelSpec(
    name='holder_tombstone_sign',
    build=build,
    title='Tombstone sign',
    description=('Song-request tombstone sign: title, headline, a QR code and two text '
                 'lines as flush inlays in up to four colours, printed face down; two '
                 'pockets in the bottom edge take the separately printed stake.'),
    category_id='household',
    tags=('sign', 'multi-colour'),
    params=PARAMS,
    presets=(
        Preset('default', 'Four colours (face down)', {}, default_view='bottom'),
        Preset('three-colour', 'Three colours (title in bone)', {'colours': 'three'},
               default_view='bottom'),
        Preset('raised', 'Raised (one colour, face up)', {'text_style': 'raised'}),
        Preset('pinned', 'Pinned stake (8 mm plate)',
               {'thickness': 8.0, 'retention': 'pin'}, default_view='bottom'),
        Preset('small', 'Small (160 x 200)',
               {'width': 160.0, 'height': 200.0, 'qr_size': 74.0}, default_view='bottom'),
    ),
    # Pocket plane first: the review sheet goldens sections[0] (the joint cut).
    review_sections=(
        PlaneSpec((signs.POCKET_OFFSET, signs.POCKET_DEPTH / 2, DEFAULTS['thickness'] / 2),
                  (1, 0, 0), 'pocket at X = +40'),
        PlaneSpec((0, (_QR[0] + _QR[1]) / 2, DEFAULTS['thickness'] / 2), (0, 1, 0),
                  'QR centre'),
    ),
))
