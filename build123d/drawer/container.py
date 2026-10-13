# SPDX-License-Identifier: CC-BY-SA-4.0
"""openConnect drawer container (the sliding drawer), adapted under CC BY-SA 4.0.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:421-431 (sizes),
:1346-1351 (asserts), :1358-1362 (export), :1484-1575 (drawer_container),
:1675-1773 (container_handle), :1774-1806 (container_label_holder).

Frames. Shell and container share ONE author frame (both SCAD cuboids are
[width, height, depth] on X/Y/Z, :1388 and :1487): X width, Y height (-Y is
the drawer bottom), Z depth (Z=0 back wall, Z=depth front wall; the handle
protrudes past it). shell.AUTHOR_TO_MODEL maps it to the model frame for
both parts. Only the container's export is spun (:1358-1362):
CONTAINER_AUTHOR_TO_MESH = Pos(0, 0, container_height/2) * Rot(90, 0, 0)
(see author_to_mesh) maps the author frame onto the reference meshes: X
width, Y depth toward -Y (handle at Y = -(depth + handle_depth)), Z height
0..container_height. The print frame IS that mesh frame: bottom on the bed,
handle toward -Y. print_frame() strips the author-to-model rotation, then
applies that spin.

Print bottom-down in PLA/PCTG. Worst-case load is a filled drawer pulled out
by its handle: the pull runs along the bed-supported handle bar and stems
into the full-height front wall, and the side walls carry the contents.
"""
from dataclasses import dataclass
from math import atan2, ceil, cos, degrees, floor, pi, radians, sin, sqrt, tan

from build123d import (Align, Axis, Box, Face, GeomType, Plane, Pos, Rot, Solid, Wire,
                       loft, revolve, section)
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from openconnect.constants import EPS, TILE_SIZE
from . import constants as c
from . import shell
from .honeycomb import HoneycombLayout, hole_polygons

AUTHOR_TO_MODEL = shell.AUTHOR_TO_MODEL
WALL_TYPES = ('Honeycomb', 'Solid')
# [C] :1708-1709: the third ("middle truss") handle stem is added only when
# each swept half of the handle bar is longer than this.
MIDDLE_TRUSS_MIN_HANDLE_WIDTH = 50
LABEL_SIDE_CLEARANCE = 0.2  # [C] :1777
LABEL_DEPTH_CLEARANCE = 0.3  # [C] :1778
LABEL_WALL = 0.8  # [C] :1779
HANDLE_TURTLE_START = 0.2  # [C] :1684
HANDLE_STEPS = 90  # [C] :1749
BED_BEVEL = 0.3  # design-guidelines bed-contact bevel (shell.chamfer_bed)


@dataclass(frozen=True)
class Dimensions:
    width: float
    height: float
    depth: float
    front: float
    back: float
    side: float
    bottom: float
    front_type: str
    back_type: str
    side_type: str
    bottom_type: str
    back_height: float
    side_height: float
    outer_chamfer: float
    fillet: float
    strut_hyp: float
    strut: float
    shell: shell.Dimensions


def _wall_types(v):
    types = tuple(v.get(f'container_{name}_wall_type', default) for name, default in (
        ('front', 'Honeycomb'), ('back', 'Solid'), ('side', 'Honeycomb'), ('bottom', 'Solid')))
    if any(t not in WALL_TYPES for t in types):
        raise ValueError('container wall types must be Honeycomb or Solid')
    return types


def dimensions(values=None):
    """[C] :421-431. The container is sized by the shell's inner box."""
    v = values or {}
    sd = shell.dimensions(v)
    width = sd.inner_width - 2*v.get('container_width_clearance', .3)
    height = sd.inner_height - 2*v.get('container_height_clearance', .4)
    depth = sd.inner_depth - v.get('container_depth_clearance', .4)
    if min(width, height, depth) <= 0:
        raise ValueError('container dimensions must be greater than 0; '
                         'reduce clearances or increase drawer size')
    types = _wall_types(v)
    solid = v.get('container_solid_wall_thickness', 1.6)
    honey = v.get('container_honeycomb_wall_thickness', 2.0)
    front, back, side, bottom = (solid if t == 'Solid' else honey for t in types)
    if (width - 2*side <= 0 or height - bottom <= 0 or depth - back - front <= 0):
        raise ValueError('container inner dimensions must be greater than 0; '
                         'reduce wall thicknesses or increase drawer size')
    back_height = height - v.get('container_back_side_height_offset', 3)
    strut_hyp = v.get('honeycomb_strut_hyp', c.HONEYCOMB_STRUT_HYP)
    return Dimensions(width, height, depth, front, back, side, bottom, *types,
                      back_height, back_height - sd.inner_chamfer, sd.inner_chamfer,
                      v.get('container_inner_fillet', 2), strut_hyp,
                      strut_hyp*cos(pi/6), sd)


def author_to_mesh(values=None):
    """CONTAINER_AUTHOR_TO_MESH = Pos(0, 0, container_height/2) * Rot(90, 0, 0).

    [C] :1358-1362 (xrot(90) after up(container_height/2)); the shell's
    export at :1353-1357 is unspun. Maps the author frame to the reference
    meshes and to the print frame.
    """
    return Pos(0, 0, dimensions(values).height/2) * Rot(90, 0, 0)


def print_frame(values=None):
    """Model -> print: undo AUTHOR_TO_MODEL, then the container's export spin."""
    return author_to_mesh(values) * AUTHOR_TO_MODEL.inverse()


def validate_label(values=None):
    """Our guard (no source assert): the label holder must fit the front.

    The author's mask clips an over-wide holder into a lipless ledge (the
    1x1x1 reference). The registry rejects that; library callers keep the
    source behaviour for reference parity.
    """
    v = values or {}
    if not v.get('add_label_holder', True):
        return
    d = dimensions(v)
    width = _label(v)[0]
    if width > d.width:
        raise ValueError(f'label holder ({width:g} mm) is wider than the container front '
                         f'({d.width:g} mm); reduce label_width or disable add_label_holder')


# ---------------------------------------------------------------- front hex

def _front_hex(d):
    """[C] :441-448 fronthex_* values that place the handle and label plates."""
    unit = c.HONEYCOMB_UNIT
    spacing = unit/cos(pi/6)
    nx = floor(d.width/unit)
    ny = floor(d.height/spacing*2)/2
    offset = (d.height - ny*spacing)/2
    bottom_strut = spacing/2 + d.strut/2 + offset - d.strut
    return nx, nx*unit, ny, offset, bottom_strut, spacing


def _hex_outer_radius(d):
    spacing = c.HONEYCOMB_UNIT/cos(pi/6)
    return (spacing - d.strut)/2*2/sqrt(3)


# ---------------------------------------------------------------- handle

@dataclass(frozen=True)
class Handle:
    thickness: float
    strut_height: float
    transition_depth: float
    stems: tuple  # (x, trans_offset, flip, add_front)
    sweeps: tuple  # (x, turn) turn=+1 toward +X, -1 toward -X
    bar_length: float


def handle_layout(values=None):
    """[C] :1675-1734, ported formula for formula (names follow the source)."""
    v = values or {}
    d = dimensions(v)
    nx, fw, ny, offset, H, spacing = _front_hex(d)
    T = v.get('handle_thickness', 2.4)
    depth = v.get('handle_depth', 12)
    hyp, chamfer = d.strut_hyp, c.HANDLE_CHAMFER
    unit = c.HONEYCOMB_UNIT
    number = 0 if fw < 100 else ((nx - 1)/2) % 2
    edge_to_strut = _hex_outer_radius(d)*2 + hyp/2 - tan(radians(30))*abs(offset)
    l1r2 = unit*(number - 1) + edge_to_strut
    l2r1 = unit*(-number + nx - 2) + edge_to_strut
    left_strut = l1r2 if number % 2 == 0 else l2r1
    right_strut = l2r1 if number % 2 == 0 else l1r2
    transition_depth = depth - T - T/2 - HANDLE_TURTLE_START
    left_transition = fw/2 - left_strut
    right_transition = fw/2 - right_strut
    left_target = tan(radians(30))*(H - chamfer)/2 - (T - hyp)
    right_target = fw - (right_strut + hyp) - (left_strut + left_target) - (T - hyp)
    left_turtle = fw/2 - left_strut - T/2 - left_target
    right_turtle = fw/2 - right_strut - T/2 - right_target
    width = (fw/2 - left_strut - left_target - T - T/2 if number % 2 == 0
             else fw/2 - right_strut - right_target - T - T/2)
    sign = -1 if number % 2 == 0 else 1  # left(a) moves -X; odd numbers negate a.
    flip = number % 2 != 0
    stems = [(sign*left_transition, left_target, flip, 0),
             (sign*right_transition, right_target, flip, 0)]
    if width > MIDDLE_TRUSS_MIN_HANDLE_WIDTH:
        stems.append((sign*left_transition + (nx - number*2 - 1)/2*unit,
                      (left_target + right_target)/2, ((nx - 1)/2) % 2 != 0,
                      T - chamfer))
    sweeps = ((sign*left_turtle, 1), (sign*right_turtle, -1))
    return Handle(T, H, transition_depth, tuple(stems), sweeps, width)


def _handle_profile(first, second, thickness, H, chamfer=c.HANDLE_CHAMFER):
    """[C] :1735-1745 handle_profile_func (x across, y up from the bed)."""
    t = lambda ang, adj: adj*tan(radians(ang))
    return [
        (t(first, chamfer), chamfer),
        (t(first, H - chamfer), H - chamfer),
        (t(first, H - chamfer) + chamfer, H),
        (thickness + t(first, H) - chamfer - t(first, chamfer), H),
        (thickness + t(first, H - chamfer), H - chamfer),
        (thickness + t(first, chamfer) + t(30 - second, H - 2*chamfer), chamfer),
        (thickness + t(first, chamfer) + t(30 - second, H - 2*chamfer) - t(45, chamfer), 0),
        (t(first, chamfer) + chamfer, 0),
    ]


def _stem(h, d, x, trans_offset, flip, add_front, step=6):
    """One handle_transition in the author frame (front face at Z=depth)."""
    hyp = d.strut_hyp
    steps = HANDLE_STEPS
    ang_unit = 30/steps
    up_unit = h.transition_depth/steps
    th_unit = (h.thickness - hyp)/steps
    x_unit = trans_offset/steps
    y0, z0 = -d.height/2, d.depth - EPS
    mirror = -1 if flip else 1

    def face(i, z):
        pts = _handle_profile(30 - ang_unit*i, ang_unit*i, hyp + th_unit*i, h.strut_height)
        pts = [(x + mirror*(px + x_unit*i), y0 + py, z) for px, py in pts]
        if flip:
            pts.reverse()
        return Face(Wire.make_polygon(pts, close=True))

    indices = list(range(0, steps + 1, step))
    if indices[-1] != steps:
        indices.append(steps)
    body = loft([face(i, z0 + up_unit*i) for i in indices], ruled=False)
    if add_front > 0:
        end = face(steps, z0 + up_unit*steps)
        body = body + Solid.extrude(end, (0, 0, add_front))
    return body


def _rect_face(width, height, chamfer):
    """BOSL2 rect([width, height], chamfer=chamfer) in local XY."""
    w, hh, k = width/2, height/2, chamfer
    pts = [(-w + k, -hh), (w - k, -hh), (w, -hh + k), (w, hh - k),
           (w - k, hh), (-w + k, hh), (-w, hh - k), (-w, -hh + k)]
    return Face(Wire.make_polygon([(x, y, 0) for x, y in pts], close=True))


def _segs(r):
    """OpenSCAD fragment count at the source's $fa=1, $fs=0.4 (:356-357)."""
    return ceil(max(5, min(360/1, abs(r)*2*pi/.4)))


def _start_tangent_angle(T, turn):
    """Angle (deg, toward the turn) of BOSL2's start tangent for the sweep.

    turtle() splits the 90 deg arc into segs(T) vertices; path_sweep's
    uniform deriv() then estimates the first tangent one-sidedly as
    3(P1-P0) - (P2-P1). attach(TOP, "start-centroid") aligns THAT tangent
    with the face normal, so the whole sweep turns by this angle about its
    start (about 0.25 deg at T=2.4: the bar ends 0.24 mm nearer the wall).
    """
    step = radians(90/(_segs(T) - 1))
    du = 3*HANDLE_TURTLE_START - T*sin(step)
    dv = -T*(1 - cos(step))
    return turn*degrees(atan2(dv, du))


def _sweep(h, d, x, turn):
    """path_sweep of the chamfered T x H rect along ["move", .2,
    "arc(left|right)", T, 90, "move", width] [C] :1702-1707.

    Built in the sweep frame (u out of the wall, v toward the handle centre
    for turn=+1) as extrusion + exact 90 deg revolve + extrusion, then turned
    by _start_tangent_angle about the start point. A non-positive bar length
    makes the source path fold back on itself; the reference render drops
    both sweeps there (CGAL applyUnion3D assertion), and so does the port.

    The two sweeps are mirror images about X=0 (right_turtle = -left_turtle)
    and each bar nominally ends there, but the start-tangent turn tilts the
    end faces so they cross: overlap on one side, a ~0.01 mm V-notch on the
    other. Each bar runs .1 past the centre and is clipped at X=0, so the
    mirror-identical sections meet flush.
    """
    T, H = h.thickness, h.strut_height
    if h.bar_length <= 0:
        return None
    profile = _rect_face(T, H, c.HANDLE_CHAMFER)  # local X across, Y = author Y
    # Sweep frame: author X = v, author Z = u, author Y = w. The first
    # "move" is a ruled loft from the transition's end face (untilted, so
    # it is that face exactly) to the tilted section at u=.2: the joint
    # shares a face instead of an overlapping lead, whose tilted start
    # left micrometre strips beside the stem's taper.
    tilt = _start_tangent_angle(T, turn)
    start = Pos(0, 0, HANDLE_TURTLE_START) * profile
    first = loft([Rot(0, tilt, 0) * profile, start], ruled=True)
    arc = revolve(start, Axis((turn*T, 0, HANDLE_TURTLE_START), (0, turn, 0)), 90)
    end = Plane(origin=(turn*T, 0, HANDLE_TURTLE_START + T), x_dir=(0, 0, -turn), z_dir=(turn, 0, 0))
    bar = end.location * Solid.extrude(_rect_face(T, H, c.HANDLE_CHAMFER), (0, 0, h.bar_length + .1))
    body = first + arc + bar
    y = -d.height/2 + H/2
    z = d.depth + h.transition_depth - EPS
    body = Pos(x, y, z) * Rot(0, -tilt, 0) * body
    big = 4*(d.width + d.height + d.depth)
    return body & Pos(big/2 if x > 0 else -big/2, 0, 0) * Box(big, big, big)


def _clip(d, values):
    """Mask (a) [C] :1529-1531: the full-height front, chamfered on Z edges,
    extended by handle_depth. Clips the handle and label holder."""
    hd = values.get('handle_depth', 12)
    return Pos(0, 0, d.depth - d.front) * Solid.extrude(
        shell._section(d.width, d.height, d.outer_chamfer), (0, 0, d.front + hd))


def source_handle(values=None):
    v = values or {}
    d = dimensions(v)
    h = handle_layout(v)
    parts = [_stem(h, d, *stem) for stem in h.stems]
    parts += [p for p in (_sweep(h, d, *sweep) for sweep in h.sweeps) if p is not None]
    body = parts[0]
    for part in parts[1:]:
        body = body + part
    return body & _clip(d, v)


def handle_fills(values=None):
    """In-wall wide_bottom of every stem [C] :1756-1758, as 2D (x, y)."""
    v = values or {}
    d = dimensions(v)
    h = handle_layout(v)
    fills = []
    for x, _, flip, _ in h.stems:
        mirror = -1 if flip else 1
        pts = _handle_profile(30, 0, d.strut_hyp, h.strut_height)
        fills.append(Polygon([(x + mirror*px, -d.height/2 + py) for px, py in pts]))
    return fills


# ---------------------------------------------------------------- label holder

def _label(v):
    """[C] :1775-1782 label holder width, depth and height."""
    width = v.get('label_width', 48) + 2*LABEL_WALL + 2*LABEL_SIDE_CLEARANCE
    depth = v.get('label_thickness', 1) + LABEL_DEPTH_CLEARANCE + LABEL_WALL
    height = v.get('label_height', 10) + depth + LABEL_SIDE_CLEARANCE
    return width, depth, height


def _label_box(d, v):
    width, depth, height = _label(v)
    top = d.height/2 - d.strut/2
    return width, depth, height, top - height, top


def label_fills(values=None):
    """Honeycomb front only [C] :1783-1793: two strut-aligned plates and the
    plate behind the label, as 2D (x, y) polygons through the front wall."""
    v = values or {}
    d = dimensions(v)
    if not v.get('add_label_holder', True) or d.front_type != 'Honeycomb':
        return []
    nx, _, ny, offset, _, spacing = _front_hex(d)
    radius = _hex_outer_radius(d)
    unit = c.HONEYCOMB_UNIT
    mode = ((nx - 1)/2) % 2 == (ny % 1)*2
    shift = -(unit/2 - d.strut*cos(pi/6)/2)
    plate = unit*4

    def prismoid(x, bottom, height, angles):
        x1, x2 = (height/tan(radians(a)) for a in angles)
        y0, y1 = -d.height/2 + bottom, -d.height/2 + bottom + height
        return Polygon([(x - plate/2, y0), (x + plate/2, y0),
                        (x + plate/2 - x2, y1), (x - plate/2 + x1, y1)])

    width, _, _, y0, y1 = _label_box(d, v)
    return [
        prismoid(shift + (radius if mode else radius/2), offset + (ny - .5)*spacing,
                 spacing/2 + offset, (120, 60) if mode else (60, 120)),
        prismoid(shift + (radius/2 if mode else radius), offset + (ny - 1)*spacing,
                 spacing/2, (60, 120) if mode else (120, 60)),
        box(-width/2, y0, width/2, y1),
    ]


def _rounded_rect(x0, x1, y0, y1, z, r, n=16):
    """Rectangle with r-rounded -Y corners (BOSL2 rounding [0,0,r,r])."""
    pts = [(x1, y1), (x0, y1)]
    for cx, a0 in ((x0 + r, 180), (x1 - r, 270)):
        for k in range(n + 1):
            a = radians(a0 + 90*k/n)
            pts.append((cx + r*cos(a), y0 + r + r*sin(a)))
    return Face(Wire.make_polygon([(x, y, z) for x, y in pts], close=True))


def source_label_holder(values=None):
    """[C] :1794-1805 prismoid (45 deg underside, 0.8 rounded lower corners),
    0.4 top-edge roundovers and the label pocket/window, clipped by mask (a)."""
    v = values or {}
    d = dimensions(v)
    if not v.get('add_label_holder', True):
        return None
    width, depth, height, y0, y1 = _label_box(d, v)
    z = d.depth
    body = loft([_rounded_rect(-width/2, width/2, y0, y1, z, LABEL_WALL),
                 _rounded_rect(-width/2, width/2, y0 + depth, y1, z + depth, LABEL_WALL)],
                ruled=True)
    r, extra = .4, .01
    for side in (-1, 1):
        # rounding_edge_mask(r=0.4) on the TOP+LEFT/RIGHT edges, l=edge+5.
        cx, cz = side*(width/2 - r), z + depth - r
        mask = Pos(cx + side*(r + extra)/2, (y0 + y1)/2, cz + (r + extra)/2) * Box(
            r + extra, height + 10, r + extra)
        mask -= Pos(cx, (y0 + y1)/2, cz) * Rot(90, 0, 0) * Solid.make_cylinder(
            r, height + 12, Plane.XY.offset(-(height + 12)/2))
        body -= mask
    pocket = v.get('label_height', 10) + LABEL_SIDE_CLEARANCE
    body -= Pos(0, y1 + EPS - pocket/2, z + (depth - LABEL_WALL)/2) * Box(
        width - 2*LABEL_WALL, pocket, depth - LABEL_WALL)
    body -= Pos(0, y1 + EPS - pocket/2, z + depth - (depth - LABEL_WALL)/2) * Box(
        width - 6*LABEL_WALL, pocket, depth - LABEL_WALL)
    return body & _clip(d, v)


# ---------------------------------------------------------------- walls

def _hex_holes(size0, size1, d, frame):
    return [Polygon(p) for p in hole_polygons(size0, size1, strut_hyp=d.strut_hyp, frame=frame)]


def _side_fill(d, v):
    if not v.get('add_side_magnet_holes', True):
        return []
    diameter = v.get('side_magnet_diameter', 6) + 2*c.MAGNET_HOLE_SIDE_CLEARANCE
    # [C] :1547-1549, hex_hole_fill_edge = 3 (:451).
    return [box(0, -d.height/2,
                v.get('container_side_magnet_edge_distance', 6) + diameter + 3,
                -d.height/2 + d.height - v.get('container_back_side_height_offset', 3)
                - d.outer_chamfer)]


def back_magnet_columns(values=None):
    """[C] :469-475 'Bottom Corners' (container_back_magnet_hole_position, :365)."""
    v = values or {}
    nh = v.get('horizontal_grids', 5)
    count = min(nh - 1, 2)
    spacing = TILE_SIZE*(nh - 2)
    return [(i - (count - 1)/2)*spacing for i in range(count)]


def _back_fill(d, v):
    if not v.get('add_back_magnet_holes', True):
        return []
    width = v.get('back_magnet_diameter', 6) + 2*c.MAGNET_HOLE_SIDE_CLEARANCE + 4.2
    top = -d.height/2 + d.height - v.get('container_back_side_height_offset', 3)
    return [box(x - width/2, -d.height/2, x + width/2, top) for x in back_magnet_columns(v)]


def wall_layouts(values=None):
    """Honeycomb walls as (name, plane, layout, thickness).

    [C] :1501-1527. Each source wall is: solid wall, minus a window cuboid,
    plus a full hex_panel (frame = min of the adjoining wall thicknesses),
    plus 'keep' fills. Through the wall that is exactly the 2D openings
    (panel holes & window) - fills, which this returns before roofing.
    Plane local X/Y are the wall's horizontal/print-up axes (front, back,
    sides) and its normal crosses the wall; the bottom lies on the bed.
    """
    v = values or {}
    d = dimensions(v)
    f, s, b = d.fillet, d.side, d.bottom
    ceiling = v.get('honeycomb_ceiling', 'roofed')
    frame = min(s, b)
    walls = []

    def add(name, plane, polygons, window, fills, thickness, wall_ceiling):
        if window.is_empty or window.area <= 0:
            return
        openings = unary_union(polygons).intersection(window)
        if fills:
            openings = openings.difference(unary_union(fills))
        # A window edge can clip a hex row into a strip thinner than 0.1 mm
        # (0.028 mm at back_side_height_offset 10): unprintable, and the
        # audit cannot orient its faces. The slicer would close it; drop it.
        parts = [p for p in getattr(openings, 'geoms', [openings])
                 if not p.is_empty and p.area > 1e-10 and not p.buffer(-.05).is_empty]
        for p in parts:
            if p.interiors:
                raise ValueError(f'container {name.lower()} wall honeycomb opening encloses an '
                                 'island; this parameter combination is unsupported')
        if parts:
            layout = HoneycombLayout(parts, wall_ceiling, name)
            # Kept for the frame-clipped opening register (frame_clipped_openings).
            layout.window, layout.fills = window, unary_union(fills) if fills else Polygon()
            walls.append((name, plane, layout, thickness))

    def window(x0, y0, x1, y1):
        return box(x0, y0, x1, y1) if x1 > x0 and y1 > y0 else Polygon()

    # (x, y) = (-py, px): hex_panel([height, width]) attach(FRONT, LEFT).
    def front_back(size1):
        return [Polygon([(-y, x) for x, y in p.exterior.coords])
                for p in _hex_holes(d.height, size1, d, frame)]

    if d.front_type == 'Honeycomb':
        add('Front', Plane(origin=(0, 0, d.depth - d.front/2 + EPS/2), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            front_back(d.width),
            window(-(d.width/2 - s - f), -d.height/2 + b + f, d.width/2 - s - f, d.height/2 - d.strut),
            label_fills(v) + handle_fills(v), d.front + EPS, ceiling)
    if d.back_type == 'Honeycomb':
        add('Back', Plane(origin=(0, 0, d.back/2 - EPS/2), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            front_back(d.width),
            window(-(d.width/2 - s - f), -d.height/2 + b + f, d.width/2 - s - f,
                   -d.height/2 + d.back_height - d.strut),
            _back_fill(d, v), d.back + EPS, ceiling)
    if d.side_type == 'Honeycomb':
        # (z, y) = (py + depth/2, px): attach(FRONT, LEFT, spin=90).
        holes = [Polygon([(y + d.depth/2, x) for x, y in p.exterior.coords])
                 for p in _hex_holes(d.height, d.depth, d, frame)]
        # [C] :1520-1522 anchors the window at the front wall and takes both
        # fillet margins off its back end, so it overlaps the front inner
        # fillet and leaves a 0.09 mm feather over it. Production stops at
        # the fillet tangent; 'source' keeps the author's window for parity.
        front_end = d.depth - d.front - (0 if ceiling == 'source' else f)
        side_window = window(d.back + 2*f, -d.height/2 + b + f, front_end,
                             -d.height/2 + d.side_height - d.strut)
        for name, sign in (('Left', -1), ('Right', 1)):
            add(name, _side_plane(d, sign), holes, side_window, _side_fill(d, v), s + EPS, ceiling)
    if d.bottom_type == 'Honeycomb':
        # hex_panel([depth, width]) attach(TOP, LEFT): (x, z) = (py, depth/2 - px).
        holes = [Polygon([(y, d.depth/2 - x) for x, y in p.exterior.coords])
                 for p in _hex_holes(d.depth, d.width, d, min(s, d.back, d.front))]
        # [C] :1526-1527 mirrors the side window: anchored at the back wall
        # with both fillet margins off the front end, so it runs under the
        # back inner fillet (a 0.09 mm feather with flat ceilings over the
        # cells). Production starts at the fillet tangent; 'source' keeps it.
        back_end = d.back + (0 if ceiling == 'source' else f)
        add('Bottom', Plane(origin=(0, -d.height/2 + b/2 - EPS/2, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)),
            holes, window(-(d.width/2 - s - f), back_end, d.width/2 - s - f, d.depth - d.front - 2*f),
            [], b + EPS, 'source')
    return walls


def _side_plane(d, sign):
    """Local X = author Z, local Y = author +Y, normal across the side wall."""
    x = sign*(d.width/2 - d.side/2 + EPS/2)
    return Plane(origin=(x, 0, 0), x_dir=(0, 0, 1), z_dir=(-1, 0, 0))


def honeycomb_ceiling_chords(values=None):
    """Analytic through-wall ceiling spans of the vertical walls."""
    return [row for name, _, layout, _ in wall_layouts(values) if name != 'Bottom'
            for row in layout.ceiling_chords((0, 1))]


def source_honeycomb_wall_cutters(values=None):
    return [plane.location * layout.cutter(thickness, (0, 1))
            for _, plane, layout, thickness in wall_layouts(values)]


def source_honeycomb_cutters(values=None):
    return [hole for wall in source_honeycomb_wall_cutters(values) for hole in wall.solids()]


# ---------------------------------------------------------------- body

def _envelope(d):
    """Cuboid & mask union [C] :1528-1535, without the handle extension."""
    front = Pos(0, 0, d.depth - d.front) * Solid.extrude(
        shell._section(d.width, d.height, d.outer_chamfer), (0, 0, d.front))
    middle = _bottom_chamfered(d.width, d.side_height, d.outer_chamfer, -d.height/2)
    middle = Pos(0, 0, d.back) * Solid.extrude(middle, (0, 0, d.depth - d.front - d.back))
    back = Pos(0, -d.height/2 + d.back_height/2, 0) * Solid.extrude(
        shell._section(d.width, d.back_height, d.outer_chamfer), (0, 0, d.back))
    return front + middle + back


def _bottom_chamfered(width, height, chamfer, y0):
    w, k = width/2, chamfer
    pts = [(-w + k, y0), (w - k, y0), (w, y0 + k), (w, y0 + height), (-w, y0 + height), (-w, y0 + k)]
    if not k:
        pts = [(-w, y0), (w, y0), (w, y0 + height), (-w, y0 + height)]
    return Face(Wire.make_polygon([(x, y, 0) for x, y in pts], close=True))


def _cavity(d):
    """[C] :1492-1500: cavity with bottom and vertical inner fillets."""
    top = d.height/2 + 1
    y0 = -d.height/2 + d.bottom
    cavity = Pos(0, (y0 + top)/2, (d.back + d.depth - d.front)/2) * Box(
        d.width - 2*d.side, top - y0, d.depth - d.front - d.back)
    if d.fillet > 0:
        edges = [e for e in cavity.edges()
                 if (abs(e.center().Y - y0) < 1e-6)  # bottom loop
                 or (e.bounding_box().size.Y > 1e-6)]  # vertical edges
        cavity = cavity.fillet(d.fillet, edges)
    return cavity


def _teardrop_cutter(radius, cap, length, origin, inward, flare=0):
    """BOSL2 teardrop (tip +Y) from `origin` along `inward` (+-X or +Z)."""
    if inward[0]:
        plane = Plane(origin=origin, x_dir=(0, 0, -inward[0]), z_dir=inward)
    else:
        plane = Plane(origin=origin, x_dir=(1, 0, 0), z_dir=inward)
    if flare:
        # chamfer1=-length: 45 deg draft from (r+L, cap+L) at the wall to r.
        face = plane.location * _teardrop_face(radius + flare, cap + flare)
        return Solid.extrude_taper(face, length, 45)
    return Solid.extrude(plane.location * _teardrop_face(radius, cap), plane.z_dir*length)


def _teardrop_face(radius, cap):
    from build123d import Line, ThreePointArc
    t = radius/sqrt(2)
    end = radius*sqrt(2) - cap
    return Face(Wire([
        ThreePointArc((-t, t, 0), (0, -radius, 0), (t, t, 0)),
        Line((t, t, 0), (end, cap, 0)),
        Line((end, cap, 0), (-end, cap, 0)),
        Line((-end, cap, 0), (-t, t, 0)),
    ]))


def source_magnet_positions(values=None):
    """Hole centres in the author frame: ('back'|'side', side, (x, y, z))."""
    v = values or {}
    d = dimensions(v)
    out = []
    if v.get('add_back_magnet_holes', True):
        y = -((v.get('vertical_grids', 2) - 1)/2*TILE_SIZE - c.BACK_MAGNET_OCSLOT_OFFSET)
        out += [('back', 0, (x, y, 0)) for x in back_magnet_columns(v)]
    if v.get('add_side_magnet_holes', True):
        radius = v.get('side_magnet_diameter', 6)/2 + c.MAGNET_HOLE_SIDE_CLEARANCE
        nv = v.get('vertical_grids', 2)
        z = v.get('container_side_magnet_edge_distance', 6) + radius
        out += [('side', side, (side*d.width/2, (j - (nv - 1)/2)*TILE_SIZE, z))
                for side in (-1, 1) for j in range(nv)]
    return out


def _bulge_length(hole, wall):
    # [C] :1547/:1561: hole thickness - wall + 0.45 + EPS, kept iff > EPS.
    length = hole - wall + 0.45 + EPS
    return length if length > EPS else 0


def source_magnet_cutters(values=None):
    v = values or {}
    d = dimensions(v)
    cuts, bulges = [], []
    for kind, side, (x, y, z) in source_magnet_positions(v):
        if kind == 'back':
            radius = v.get('back_magnet_diameter', 6)/2 + c.MAGNET_HOLE_SIDE_CLEARANCE
            hole = v.get('container_back_magnet_thickness', 1) + c.MAGNET_HOLE_DEPTH_CLEARANCE
            cuts.append(_teardrop_cutter(radius, radius + .2, hole, (x, y, 0), (0, 0, 1)))
            bulge = _bulge_length(hole, d.back)
            if bulge:
                bulges.append(_teardrop_cutter(radius + .1, radius + .2, bulge,
                                               (x, y, d.back), (0, 0, 1), flare=bulge))
        else:
            radius = v.get('side_magnet_diameter', 6)/2 + c.MAGNET_HOLE_SIDE_CLEARANCE
            hole = v.get('container_side_magnet_thickness', 1) + c.MAGNET_HOLE_DEPTH_CLEARANCE
            cuts.append(_teardrop_cutter(radius, radius + .2, hole, (x, y, z), (-side, 0, 0)))
            bulge = _bulge_length(hole, d.side)
            if bulge:
                bulges.append(_teardrop_cutter(radius + .1, radius + .2, bulge,
                                               (x - side*d.side, y, z + .1), (-side, 0, 0), flare=bulge))
    return cuts, bulges


def source_body(values=None):
    """Author-frame container before the bed bevel (source CSG order)."""
    v = values or {}
    d = dimensions(v)
    body = _envelope(d) - _cavity(d)
    holes = source_honeycomb_wall_cutters(v)
    if holes:
        body = body.cut(*holes)
    for extra in (source_handle(v), source_label_holder(v)):
        if extra is not None:
            body = body + extra
    cuts, bulges = source_magnet_cutters(v)
    for cut in cuts:
        body -= cut
    for bulge in bulges:
        body += bulge
    return body


def published_ceiling_regions(values=None):
    """Exact thin regions over flat print-up ceilings of source openings.

    Print up is author +Y. Honeycomb cells of the vertical walls (roofed
    chords above MAX_BRIDGE_MM are 45-degree roofs and stay audited) and the
    magnet teardrop caps ([C] :1547/:1561, cap_h=r+.2). Only flat facets with
    a horizontal extent of at most MAX_BRIDGE_MM are eligible.
    """
    cutters = [plane.location * layout.cutter(thickness, (0, 1))
               for name, plane, layout, thickness in wall_layouts(values) if name != 'Bottom']
    cutters += source_magnet_cutters(values)[0]
    regions = []
    for cutter in cutters:
        for face in cutter.faces():
            normal = face.normal_at()
            size = face.bounding_box().size
            if normal.Y > .999 and max(size.X, size.Z) <= c.MAX_BRIDGE_MM:
                regions.append(AUTHOR_TO_MODEL *
                               (Pos(*tuple(-normal*.0005))*Solid.extrude(face, normal*.001)))
    return regions


# ---------------------------------------------------------------- production

def before_bed_chamfer(values=None):
    """Model-frame container before the bed bevel (roofed honeycomb ceilings)."""
    return AUTHOR_TO_MODEL * source_body(values)


def _bed_edges(printed):
    """Square bed edges (print frame Z=0) as (edge, bed face, wall face).

    Edges whose other face is already a bevel (the outer chamfer, the
    handle's 0.4 mm profile chamfers) keep it; only vertical walls meet
    the bed square.
    """
    adjacent = {}
    for face in printed.faces():
        for edge in face.edges():
            adjacent.setdefault(edge, []).append(face)
    edges = []
    for face in printed.faces():
        bb = face.bounding_box()
        if abs(bb.max.Z) > 1e-6 or face.normal_at().Z > -.999:
            continue
        for edge in face.edges():
            if edge.length < 1e-3:
                continue  # where the handle's swept halves meet (2-wide)
            others = [f for f in adjacent.get(edge, []) if f != face]
            if len(others) == 1 and abs(others[0].normal_at(edge.position_at(.5)).Z) < 1e-3:
                edges.append((edge, face, others[0]))
    return edges


def _occt_bevel(printed, edges):
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
    from OCP.StdFail import StdFail_NotDone
    from build123d import Part
    bevel = BRepFilletAPI_MakeChamfer(printed.wrapped)
    for edge, face, _ in edges:
        bevel.AddDA(BED_BEVEL, radians(45.01), edge.wrapped, face.wrapped)
    try:
        result = Part(bevel.Shape())
    except (StdFail_NotDone, ValueError):
        return None
    return result if result.is_valid and len(result.solids()) == 1 else None


def _wedge_bevel(printed, edges):
    """The same bevel as explicit cutters: {z + inset < 0.3} along each
    straight edge, run 0.5 mm past convex ends (corners miter) and
    mitered at 45 deg at concave ones (a stem root continuing the bed
    face): the stem's 0.4 mm root chamfer widens it by z at height z, so
    a square wedge end would undercut the wall behind the stem and leave
    a 0.3 mm triangle of the stem's back face, 0.03-0.6 mm thick."""
    from build123d import Vector
    big = 4*max(printed.bounding_box().size)
    wedges = []
    up, slack = Vector(0, 0, 1), .01
    for edge, _, wall in edges:
        if edge.geom_type != GeomType.LINE:
            return None
        a, b = edge.position_at(0), edge.position_at(1)
        t = (b - a).normalized()
        out = wall.normal_at(edge.position_at(.5))
        ext, miters = [], []
        for end, sign in ((a, -1), (b, 1)):
            probe = end + t*(sign*.15) + out*.05 + up*.05
            concave = printed.is_inside(probe)
            ext.append(0 if concave else .5)
            if concave:
                normal = (t*sign + up).normalized()
                miters.append(Plane(origin=end, z_dir=normal).location *
                              Box(big, big, big, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        start = a - t*ext[0]
        # Hypotenuse exactly on z + inset = BED_BEVEL; legs overshoot.
        # The outer leg lies ON the wall plane: an outward overshoot would
        # nick a swept stem's 0.4 mm root chamfer where it meets the front.
        tri = [start + up*BED_BEVEL,
               start - out*(BED_BEVEL + slack) - up*slack,
               start - up*slack]
        wedge = Solid.extrude(Face(Wire.make_polygon(tri, close=True)),
                              t*((b - a).length + ext[0] + ext[1]))
        wedges.append(wedge.cut(*miters) if miters else wedge)
    result = printed.cut(*wedges)
    return result if result.is_valid and len(result.solids()) == 1 else None


def chamfer_bed(part, values=None):
    """0.3 mm bevel on every square edge of the bed face (print frame Z=0).

    OCCT's chamfer first; where it cannot end the bevel (the front edge
    against a swept handle stem at handle_depth 6 / strut 1.1, 16.3 /
    8 wide, or a honeycomb front with square corners at shell_thickness
    4) the same bevel is cut as explicit wedges; last resort the shell's
    exact section bevel.
    """
    frame = print_frame(values)
    printed = frame * part
    edges = _bed_edges(printed)
    if not edges:
        return part
    result = _occt_bevel(printed, edges) or _wedge_bevel(printed, edges)
    if result is None:
        result = shell._bevel_from_sections(printed)
    return frame.inverse() * result


def build(values=None):
    validate_label(values)
    return chamfer_bed(before_bed_chamfer(values), values)
