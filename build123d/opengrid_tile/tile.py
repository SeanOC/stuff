"""openGrid Full/Lite tiles, in print coordinates (back down, front up).

All snap and connector geometry comes from the pinned vendor Base. Coordinates
in omit_cells run from the lower-left cell (0,0), independently of orientation.
"""
from functools import lru_cache
import math
import re

from build123d import Align, Box, Plane, Polygon, Pos, chamfer, extrude
from opengrid.base import Base
from opengrid.constants import OPEN_GRID_UNIT_SIZE, OPEN_GRID_BASE_HEIGHT
from shapely.geometry import Polygon as Outline, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

PITCH = OPEN_GRID_UNIT_SIZE  # [C] vendor/opengrid/opengrid/constants.py
FULL = OPEN_GRID_BASE_HEIGHT
LITE = 4.0  # [C] assets/openConnect/lib/opengrid_base.scad:6 OG_LITE_THICKNESS
CORNER = 4.2  # [C] vendor Base.corner_chamfer_length
RELIEF = 0.3
MIN_BACKING = 1.0  # nonzero minimum; endpoint audit includes the bed relief
# [C] scripts/export.py::max_footprint, H2C printing nozzle + prime tower.
BAKE_ENVELOPE = (323, 244)  # mm, either orientation
MAX_COUNT = int(max(BAKE_ENVELOPE) // PITCH)
MAX_SHORT_COUNT = int(min(BAKE_ENVELOPE) // PITCH)


def cells(x_count, y_count, omit_cells=''):
    """Require bake fit and edge connection; parse whitespace/semicolon x,y pairs.

    The bake accepts either orientation: long <= 323 mm and short <= 244 mm
    is equivalent to long <= 11 cells and short <= 8 at the fixed 28 mm pitch.
    Apply this to the requested grid, before omissions.
    """
    for name, value in (('x_count', x_count), ('y_count', y_count)):
        if type(value) is not int or not 1 <= value <= MAX_COUNT:
            raise ValueError(f'{name} must be an integer from 1 to {MAX_COUNT}')
    if min(x_count, y_count) > MAX_SHORT_COUNT:
        raise ValueError('tile exceeds the 323 x 244 mm bake envelope: '
                         f'longer side must be <= {MAX_COUNT} cells and shorter '
                         f'side <= {MAX_SHORT_COUNT}, either orientation')
    if not isinstance(omit_cells, str) or len(omit_cells) > 256:
        raise ValueError('omit_cells must be a string of at most 256 characters')
    omitted = set()
    for token in re.split(r'[;\s]+', omit_cells.strip()):
        if not token:
            continue
        if not re.fullmatch(r'\d+,\d+', token):
            raise ValueError('omit_cells needs x,y pairs separated by spaces or semicolons')
        x, y = map(int, token.split(','))
        if not (0 <= x < x_count and 0 <= y < y_count):
            raise ValueError('omit_cells contains a cell outside x_count/y_count')
        omitted.add((x, y))
    kept = {(x, y) for x in range(x_count) for y in range(y_count)} - omitted
    if not kept:
        raise ValueError('omit_cells must leave at least one cell')
    reached = {next(iter(kept))}
    queue = list(reached)
    while queue:
        x, y = queue.pop()
        for neighbour in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            if neighbour in kept and neighbour not in reached:
                reached.add(neighbour)
                queue.append(neighbour)
    if reached != kept:
        raise ValueError('omit_cells must leave an edge-connected tile')
    return kept


def _bevel_ring(ring):
    coords = list(ring.coords)[:-1]
    # Remove collinear lattice vertices before applying each convex bevel.
    coords = [p for i, p in enumerate(coords)
              if abs((p[0]-coords[i-1][0])*(coords[(i+1)%len(coords)][1]-p[1])
                     - (p[1]-coords[i-1][1])*(coords[(i+1)%len(coords)][0]-p[0])) > 1e-7]
    result = []
    for i, p in enumerate(coords):
        a, b = coords[i-1], coords[(i+1)%len(coords)]
        cross = (p[0]-a[0])*(b[1]-p[1]) - (p[1]-a[1])*(b[0]-p[0])
        if cross > 0:  # material-convex, including any corners on hole rings
            for q in (a, b):
                length = math.dist(p, q)
                result.append(tuple(p[j] + CORNER*(q[j]-p[j])/length for j in (0,1)))
        else:
            result.append(p)
    return result


@lru_cache(maxsize=64)
def outline(x_count, y_count, omit_cells=''):
    kept = cells(x_count, y_count, omit_cells)
    w, d = x_count*PITCH, y_count*PITCH
    raw = unary_union([box(x*PITCH-w/2, y*PITCH-d/2,
                           (x+1)*PITCH-w/2, (y+1)*PITCH-d/2)
                       for x, y in sorted(kept)])
    if raw.geom_type != 'Polygon' or not raw.is_valid:
        raise ValueError('omit_cells must leave a valid edge-connected outline')
    raw = orient(raw, sign=1)
    return Outline(_bevel_ring(raw.exterior), [_bevel_ring(r) for r in raw.interiors])


def outline_solid(profile, height):
    part = extrude(Polygon(*list(profile.exterior.coords)[:-1], align=None), amount=height)
    for ring in profile.interiors:
        # Hole rings are clockwise; force +Z rather than their face normal.
        part -= extrude(Polygon(*list(ring.coords)[:-1], align=None), amount=height, dir=(0,0,1))
    return part


def tile(x_count=1, y_count=1, style='full', backing_mm=0.0, omit_cells='',
         connector_neg_x=True, connector_pos_x=True,
         connector_neg_y=True, connector_pos_y=True):
    if style not in ('full', 'lite'):
        raise ValueError('style must be full or lite')
    if (isinstance(backing_mm, bool) or not isinstance(backing_mm, (int, float))
            or not math.isfinite(backing_mm)
            or not (backing_mm == 0 or MIN_BACKING <= backing_mm <= 3)):
        raise ValueError(f'backing_mm must be 0 (none) or between {MIN_BACKING:g} and 3 mm')
    profile = outline(x_count, y_count, omit_cells)
    masked = len(cells(x_count, y_count, omit_cells)) != x_count*y_count
    kwargs = dict(x_count=x_count, y_count=y_count,
                  connector_cut_neg_x=connector_neg_x, connector_cut_pos_x=connector_pos_x,
                  connector_cut_neg_y=connector_neg_y, connector_cut_pos_y=connector_pos_y)
    if masked:
        kwargs.update(connector_cutter=None, corner_chamfer=False)
    part = Base(**kwargs)
    height = LITE if style == 'lite' else FULL
    if masked:
        part = part & outline_solid(profile, height)
    elif style == 'lite':
        part = part & Box(x_count*PITCH, y_count*PITCH, height,
                          align=(Align.CENTER, Align.CENTER, Align.MIN))
    if backing_mm:
        part += Pos(0, 0, height) * outline_solid(profile, backing_mm)
    total = height + backing_mm
    # Reflect Z only: preserve the user's x,y mask coordinates, with rear on bed.
    part = part.mirror(Plane.XY.offset(total/2))
    # Apply the finished outline's relief as a final intersection. Chamfering
    # the already-pocketed part fails at connector mouths on bare Lite grids;
    # this identical outline envelope leaves all library cutter edges intact.
    envelope = outline_solid(profile, total)
    bed_edges = [e for e in envelope.edges()
                 if abs(e.bounding_box().min.Z) < 1e-6
                 and abs(e.bounding_box().max.Z) < 1e-6]
    return part & chamfer(bed_edges, length=RELIEF)
