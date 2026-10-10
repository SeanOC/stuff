# SPDX-License-Identifier: MIT
"""Captured-footprint Gridfinity bin; print feet-down (+Z up), PLA/PCTG.

Worst load: lateral item force against the pocket wall; the continuous stock
carries it along XY layers. Downward item weight is compression into the floor.
The GR 0.8 mm 45° foot chamfer is already the mating bed relief; foot/profile
edges remain functional. No stacking lip and no mount contract.
"""
from math import ceil
import sys

from build123d import Face, Pos, Wire, chamfer, extrude, fillet
from shapely import affinity
from shapely.geometry import Point, Polygon, box

from capture.encoding import MAX_BYTES, encode, parse, validate
from gridfinity import bin as gf
from holders.registry import ModelSpec, Param, Preset, register

RIM_RADIUS = 1.0
POCKET_BREAK = .15
POCKET_SIMPLIFY_MM = .1
# Canned 140 x 18 mm rounded rectangle; the capture panel replaces this string.
DEFAULT_FOOTPRINT = encode(box(-65.5, -4.5, 65.5, 4.5).buffer(4.5, quad_segs=8).exterior.coords)


def outer_polygon(w, d):
    half_w, half_d = (42*w-.5)/2, (42*d-.5)/2
    return box(-half_w+gf.TOP_RADIUS, -half_d+gf.TOP_RADIUS,
               half_w-gf.TOP_RADIUS, half_d-gf.TOP_RADIUS).buffer(gf.TOP_RADIUS, quad_segs=64)


def dimensions(values=None):
    # Encoding owns all wire errors, including byte/character/geometry errors.
    raw = (values or {}).get('footprint', DEFAULT_FOOTPRINT)
    polygon = Polygon(validate(parse(raw)))
    v = SPEC.resolve_values(values)
    x0, y0, x1, y1 = polygon.bounds
    polygon = affinity.translate(polygon, -(x0+x1)/2, -(y0+y1)/2)
    offset = polygon.buffer(v['clearance'], quad_segs=8)
    tolerance = POCKET_SIMPLIFY_MM
    while True:
        # Real 0.2 mm-quantised rings produce sub-0.1 mm clearance-offset
        # edges that OCP cannot chamfer, even below the vertex-count limit.
        # Expand after simplification so the true clearance outline is contained.
        pocket = offset.simplify(tolerance, preserve_topology=True).buffer(tolerance, quad_segs=1)
        if len(pocket.exterior.coords) <= 257:
            break
        tolerance = tolerance*2 or .001
    candidates = [(w, d) for w in range(1, 7) for d in range(1, 7)]
    candidates.sort(key=lambda wh: (wh[0]*wh[1], sum(wh), wh))
    if v['size_mode'] == 'manual':
        candidates = [(v['width_units'], v['depth_units'])]
    for w, d in candidates:
        outer = outer_polygon(w, d)
        if outer.covers(pocket) and outer.boundary.distance(pocket) >= v['wall_min']-1e-7:
            break
    else:
        raise ValueError('footprint + wall exceeds 6×6 cells')
    height_units = ceil((v['pocket_depth']+v['floor_thickness']+gf.BASE_HEIGHT)/gf.BASE_HEIGHT)
    height = height_units*gf.BASE_HEIGHT
    floor = height-v['pocket_depth']
    if floor < gf.BASE_HEIGHT+v['floor_thickness']-1e-7:
        raise ValueError('pocket deeper than the bin')
    return v, w, d, height_units, floor, pocket, offset


def before_treatment(values=None):
    _, w, d, h, *_ = dimensions(values)
    return gf.blank(w, d, h)


def audit_exclusions(values=None):
    _, w, d, *_ = dimensions(values)
    return gf.underside_exclusions(w, d)


def build(values=None):
    v, w, d, h, floor, pocket, _ = dimensions(values)
    part = gf.blank(w, d, h)
    top = h*gf.BASE_HEIGHT
    rim = [e for e in part.edges() if abs(e.bounding_box().min.Z-top) < 1e-6]
    part = fillet(rim, RIM_RADIUS)
    face = Face(Wire.make_polygon([(x, y, 0) for x, y in pocket.exterior.coords], close=True))
    part -= extrude(Pos(0, 0, floor)*face, amount=v['pocket_depth']+1, dir=(0, 0, 1))
    pocket_edges = [e for e in part.edges()
                    if abs(e.bounding_box().min.Z-top) < 1e-6
                    and pocket.boundary.distance(Point(e.center().X, e.center().Y)) < .001]
    for length in (POCKET_BREAK, POCKET_BREAK/2, .05):
        try:
            return chamfer(pocket_edges, length)
        except ValueError as error:
            last_error = error
    # Deviation from docs/design-guidelines.md §2: retain the pocket's hard
    # top edge only if every break fails. It adds no downward face/overhang
    # (§1), so this cosmetic failure need not prevent a printable render.
    print(f'[capture-bin] pocket break skipped: {last_error}', file=sys.stderr)
    return part


SPEC = register(ModelSpec(
    name='gridfinity_capture_bin', title='Gridfinity capture bin', category_id='storage',
    description='A no-lip Gridfinity bin with a pocket fitted to a captured item footprint. Print feet-down without supports.',
    build=build,
    tags=('capture',),
    params=(
        Param('footprint', 'string', DEFAULT_FOOTPRINT, max_length=MAX_BYTES,
              label='Item footprint (from the capture panel)',
              description='The capture panel fills this encoded outline in millimetres.'),
        Param('pocket_depth', 'number', 20, min=3, max=90, step=1, unit='mm'),
        Param('clearance', 'number', 1.6, min=1.0, max=3.0, step=.1, unit='mm',
              description='Capture accuracy is not established below 1 mm clearance. The 1.6 mm default covers the measured mean (0.790 mm), not the 1.612 mm worst case.'),
        Param('floor_thickness', 'number', 2.0, min=1.2, max=4.0, step=.1, unit='mm'),
        Param('wall_min', 'number', 1.6, min=1.2, max=3.0, step=.1, unit='mm'),
        Param('size_mode', 'enum', 'auto', choices=('auto', 'manual')),
        Param('width_units', 'integer', 4, min=1, max=6, step=1, filename=True),
        Param('depth_units', 'integer', 1, min=1, max=6, step=1, filename=True),
    ),
    presets=(Preset('default', 'Marker pen', {}),
             Preset('deep', 'Deep pocket', {'pocket_depth': 45}),
             Preset('wide', '4 × 2 cells', {'size_mode': 'manual', 'width_units': 4, 'depth_units': 2})),
))
