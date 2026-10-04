"""openConnect slot negative and head fixture, ported from the author's SCAD.

Port of ``ocslot_body`` / ``openconnect_head`` / ``openconnect_lock`` in
mitufy/opengrid-projects lib/openconnect_lib.scad @ 04e2277a71c5 (CC BY 4.0,
vendored under assets/openConnect/). The same CSG is rebuilt in the SCAD's
own slot frame, then rotated once into the consumer frame:

* slot frame: origin on the connector axis (the tile centre), the pocket's
  deep flange band at Z=0 and the mouth at Z=depth; the head slides +Y from
  the on-ramp (Y-10.6) to the seat.
* consumer frame (same as multibuild): back face Y=0, material +Y, pocket
  Y=0..depth; the head enters through the on-ramp on the back face, then
  rides +Z by 10.6 mm to the seat at the origin.

Nothing is invented: every number comes from ``constants`` (each [C], cited
to its SCAD line), and tests/test_openconnect.py checks the result against
committed renders of the author's own plate and head.

Adapted from openConnect by mitufy, licensed CC BY 4.0.
"""
from math import cos, isfinite, radians, sin, sqrt, tan
import warnings

from build123d import (Align, Box, Face, Line, Part, Plane, Pos, Rot, Solid, ThreePointArc,
                       Vector, Wire)

from . import constants as c

_SQ2 = sqrt(2)


def _poly(points, z=0.0) -> Face:
    return Face(Wire.make_polygon([Vector(x, y, z) for x, y in points], close=True))


def _chamfered_rect(width, height, back_y, chamfer_pos_x, chamfer_neg_x, x_shift=0.0):
    """BOSL2 ``rect(..., chamfer=[cx+, cx-, 0, 0], anchor=BACK)`` moved back to
    ``back_y``: both +Y corners chamfered, counter-clockwise points."""
    l, r = x_shift - width / 2, x_shift + width / 2
    f = back_y - height
    return [(l, f), (r, f), (r, back_y - chamfer_pos_x), (r - chamfer_pos_x, back_y),
            (l + chamfer_neg_x, back_y), (l, back_y - chamfer_neg_x)]


def _offset_convex(points, d):
    """Mitred outward offset of a convex CCW polygon (SCAD ``offset(delta=)``)."""
    n = len(points)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = points[i], points[(i + 1) % n]
        tx, ty = x1 - x0, y1 - y0
        length = sqrt(tx * tx + ty * ty)
        nx, ny = ty / length, -tx / length  # outward normal for CCW
        lines.append(((x0 + nx * d, y0 + ny * d), (tx, ty)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        det = u[0] * v[1] - u[1] * v[0]
        s = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / det
        out.append((p[0] + u[0] * s, p[1] + u[1] * s))
    return out


def _nub_face(base_x, centre_y, inward) -> Face:
    """``openconnect_lock`` cross-section: 45° trapezoid, tip 1.2, depth 0.6,
    convex r0.8 tip corners and concave r0.8 flares blending into the wall.

    Local (u, v): u along the wall (slot Y), v into the slot from the wall at
    ``base_x``; ``inward`` is +1 for the -X wall and -1 for the +X wall.
    """
    assert c.NUB_FLANK_ANGLE == 45, 'the arc construction below assumes 45° flanks'
    d, r = c.NUB_DEPTH, c.NUB_FILLET
    b = c.NUB_TIP_HEIGHT / 2 + d / tan(radians(c.NUB_FLANK_ANGLE))  # base half-width
    flare_u = b - r + r * _SQ2      # flare arc meets the wall here
    tip_u = b - d + r - r * _SQ2    # tip arc meets the flat tip here
    k = r / _SQ2                    # arc centre to flank tangent, per axis
    m1, m2 = sin(radians(22.5)), cos(radians(22.5))  # arc mid-points (bisectors)

    def p(u, v):
        return Vector(base_x + inward * v, centre_y + u, 0)

    edges = []
    for s in (1, -1):
        # Mirror the half-profile: s=+1 walks from the base out to the tip.
        flare = (s * flare_u, 0.0)
        side_lo = (s * (flare_u - k), r - k)
        side_hi = (s * (tip_u + k), d - r + k)
        tip = (s * tip_u, d)
        flare_mid = (s * (flare_u - r * m1), r - r * m2)
        tip_mid = (s * (tip_u + r * m1), d - r + r * m2)
        half = [ThreePointArc(p(*flare), p(*flare_mid), p(*side_lo)),
                Line(p(*side_lo), p(*side_hi)),
                ThreePointArc(p(*side_hi), p(*tip_mid), p(*tip))]
        if s == -1:
            half = [e.reversed() for e in reversed(half)]
        edges.append(half)
    right, left = edges
    wire = Wire([Line(p(-flare_u, 0), p(flare_u, 0)), *right,
                 Line(p(tip_u, d), p(-tip_u, d)), *left])
    return Face(wire)


def _lock(base_x, inward, bottom_h, taper_in) -> Part:
    """Nub prism: straight through the flange band, then sheared across the
    taper (``taper_in``: shift 0.8 so it vanishes into the 45° flank)."""
    centre_y = c.HEAD_WIDTH / 2 - c.NUB_TO_TOP_DISTANCE + c.BACK_POS_OFFSET
    face = _nub_face(base_x, centre_y, inward)
    shift = inward * c.NUB_TAPER_SHIFT if taper_in else 0.0
    lower = Solid.extrude(face, Vector(0, 0, bottom_h))
    upper = Solid.extrude(Pos(0, 0, bottom_h) * face, Vector(shift, 0, c.HEAD_MIDDLE_HEIGHT))
    return lower + upper


def _stack(bottom, top, bottom_h, top_h, top_extra=0.0) -> Part:
    """Flange band, ruled 45° taper (the SCAD hull), neck band."""
    mid = c.HEAD_MIDDLE_HEIGHT
    flange = Solid.extrude(_poly(bottom), Vector(0, 0, bottom_h))
    taper = Solid.make_loft([_poly(bottom, bottom_h).outer_wire(),
                             _poly(top, bottom_h + mid).outer_wire()], ruled=True)
    neck = Solid.extrude(_poly(top, bottom_h + mid), Vector(0, 0, top_h + top_extra))
    return flange + taper + neck


def _consumer(slot_frame_part: Part, depth: float) -> Part:
    return Pos(0, depth, 0) * Rot(90, 0, 0) * slot_frame_part


def head(*, nubs: bool = True) -> Part:
    """openConnect head (``openconnect_head(head_type="head")``) — a contract
    FIXTURE only, never printed from here. Flange at Z=0, mouth-side top at
    Z=2.6, connector axis at the origin, seat end towards +Y. Lock notches on
    both flanks: the -X one tapers in, the +X one is straight."""
    w, h, ch, mid = c.HEAD_WIDTH, c.HEAD_HEIGHT, c.HEAD_CHAMFER, c.HEAD_MIDDLE_HEIGHT
    sw, sh = w - 2 * mid, h - mid
    sch = ch - mid + c.half_angle_share(mid)
    bottom = _chamfered_rect(w, h, w / 2 + c.BACK_POS_OFFSET, ch, ch)
    top = _chamfered_rect(sw, sh, sw / 2 + c.BACK_POS_OFFSET, sch, sch)
    part = _stack(bottom, top, c.HEAD_BOTTOM_HEIGHT, c.HEAD_TOP_HEIGHT)
    if nubs:
        part -= _lock(-w / 2 - c.EPS, 1, c.HEAD_BOTTOM_HEIGHT, True)
        part -= _lock(w / 2 + c.EPS, -1, c.HEAD_BOTTOM_HEIGHT, False)
    return part


def _nubs(nubs, snap):
    if snap is not None:
        warnings.warn("snap is deprecated; use nubs='left' or 'none'",
                      DeprecationWarning, stacklevel=3)
        alias = 'left' if snap else 'none'
        if nubs is not None and nubs != alias:
            raise ValueError('snap and nubs disagree')
        nubs = alias
    nubs = 'left' if nubs is None else nubs
    if nubs not in ('left', 'right', 'both', 'none'):
        raise ValueError('nubs must be left, right, both or none')
    return nubs


def _slide(slide):
    try:
        return {'up': c.SLIDE_UP, 'down': c.SLIDE_DOWN,
                'left': c.SLIDE_LEFT, 'right': c.SLIDE_RIGHT}[slide]
    except (KeyError, TypeError):
        raise ValueError('slide must be up, down, left or right') from None


def slot_body(*, snap: bool | None = None, nubs: str | None = None,
              clearance=(c.SIDE_CLEARANCE, c.DEPTH_CLEARANCE), excess: float = 0.0,
              excess_length: float = 0.0, entryramp_flip: bool = False,
              edge_feature: str = 'both') -> Part:
    """Single tile negative in the author's XY slot frame (mouth at +Z).

    ``excess`` is the historical name for excess_thickness; the consumer API
    uses the upstream name. The grid's tile clipping is applied after flip.
    """
    nubs = _nubs(nubs, snap)
    if edge_feature not in ('both', 'top', 'side', 'none'):
        raise ValueError('edge_feature must be both, top, side or none')
    if any(not isfinite(v) or v < 0 for v in (excess, excess_length)):
        raise ValueError('excess dimensions must be finite and nonnegative')
    cs, cd = clearance
    mid, move, ramp_cl = c.HEAD_MIDDLE_HEIGHT, c.MOVE_DISTANCE, c.ONRAMP_CLEARANCE
    bpo = c.BACK_POS_OFFSET
    share = c.half_angle_share(cs)
    bottom_h = c.HEAD_BOTTOM_HEIGHT + share + cd
    top_h = c.HEAD_TOP_HEIGHT - share
    total = bottom_h + mid + top_h
    w, h = c.HEAD_WIDTH + 2 * cs, c.HEAD_HEIGHT + 2 * cs
    ch = c.HEAD_CHAMFER + cs - share
    sw, sh = c.MOUTH_WIDTH + 2 * cs, c.HEAD_HEIGHT - mid + 2 * cs
    sch = c.HEAD_CHAMFER - mid + c.half_angle_share(mid) + cs - share
    mid_to_bottom = h - w / 2 - bpo

    # 1. Seat: head-shaped pocket, minus the lock nub (plate material).
    bottom = _chamfered_rect(w, h, w / 2 + bpo, ch, ch)
    top = _chamfered_rect(sw, sh, sw / 2 + bpo, sch, sch)
    seat = _stack(bottom, top, bottom_h, top_h, excess)
    if nubs in ('left', 'both'):
        seat -= _lock(-w / 2 - c.EPS, 1, bottom_h, True)
    if nubs in ('right', 'both'):
        seat -= _lock(w / 2 + c.EPS, -1, bottom_h, False)

    # 2. Slide channel: the dovetail section swept from the seat to the ramp.
    run = move + ramp_cl + bpo + excess_length
    y0 = bpo - mid_to_bottom
    section = [(-w / 2, 0), (w / 2, 0), (w / 2, bottom_h), (sw / 2, bottom_h + mid),
               (sw / 2, total + excess), (-sw / 2, total + excess),
               (-sw / 2, bottom_h + mid), (-w / 2, bottom_h)]
    channel_face = Face(Wire.make_polygon([Vector(x, y0, z) for x, z in section], close=True))
    channel = Solid.extrude(channel_face, Vector(0, -run, 0))

    # 3. Bridge widening (edge_feature "Both"): mouth-width prism over the
    #    taper and neck, widened so the lip's bridges and walls stay printable.
    top_bridge = max(0.0, c.EDGE_BRIDGE_MIN_W - top_h) if edge_feature in ('both', 'top') else 0
    side_bridge = max(0.0, c.EDGE_BRIDGE_MIN_W - top_h) if edge_feature in ('both', 'side') else 0
    side_cliff = max(0.0, c.EDGE_WALL_MIN_W - top_h) if edge_feature in ('both', 'side') else 0
    bridge = _chamfered_rect(
        sw + side_bridge + side_cliff, sh + move + ramp_cl + top_bridge,
        sw / 2 + bpo + top_bridge,
        sch + top_bridge + side_bridge, sch + top_bridge + side_cliff,
        x_shift=side_bridge / 2 - side_cliff / 2)
    bridge_prism = Solid.extrude(_poly(bridge, bottom_h), Vector(0, 0, top_h + mid + min(excess, c.EPS)))

    # 4. On-ramp: flange outline plus a 45° roof continuing its chamfers,
    #    offset by the ramp clearance; leans -X by the taper height going up.
    # The roof's flanks are collinear with the chamfers, so its base corners
    # are not vertices of the outline.
    roof_top = w - 2 * ch - 2 * c.ONRAMP_ROOF_HEIGHT
    outline = [(-w / 2, -h - excess_length), (w / 2, -h - excess_length), (w / 2, -ch),
               (roof_top / 2, c.ONRAMP_ROOF_HEIGHT), (-roof_top / 2, c.ONRAMP_ROOF_HEIGHT),
               (-w / 2, -ch)]
    dx, dy = -c.ONRAMP_SHIFT, w / 2 + bpo - move
    ramp = _offset_convex([(x + dx, y + dy) for x, y in outline], ramp_cl)
    onramp = (Solid.extrude(_poly(ramp), Vector(0, 0, bottom_h))
              + Solid.extrude(_poly(ramp, bottom_h), Vector(-mid, 0, mid))
              + Solid.extrude(_poly([(x - mid, y) for x, y in ramp], bottom_h + mid),
                              Vector(0, 0, top_h + excess)))

    body = seat + channel + bridge_prism + onramp
    if excess > 0:
        body += Pos(0, -sch, 0) * Box(sw, sh, total + excess,
                                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    tile = c.TILE_SIZE
    # openconnect_slot:403-405; grid clip at :471-475.
    if c.EDGE_WALL_MIN_W > excess_length:
        body -= Pos(0, -tile / 2, 0) * Box(
            tile, c.EDGE_WALL_MIN_W, total + excess + c.EPS,
            align=(Align.CENTER, Align.MIN, Align.MIN))
    if entryramp_flip:
        body = body.mirror(Plane.YZ)
    body &= Pos(0, -excess_length / 2, 0) * Box(
        tile, tile + excess_length, total + excess,
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body



def pocket_depth(clearance=(c.SIDE_CLEARANCE, c.DEPTH_CLEARANCE)) -> float:
    return c.HEAD_DEPTH + clearance[1]


def slot_cutter(*, snap: bool | None = None, nubs: str | None = None,
                clearance=(c.SIDE_CLEARANCE, c.DEPTH_CLEARANCE),
                entryramp_flip: bool = False, edge_feature: str = 'both',
                slide: str = 'up', excess_thickness: float = c.EPS,
                excess_length: float = 0.0) -> Part:
    """Slot negative at back face Y=0, material +Y, seated axis at origin.

    Slide is applied once here, including the upstream grid's ramp flip.
    Excess thickness extends outside the face (-Y); excess length extends
    the on-ramp end. ``snap`` is a deprecated left/none alias for ``nubs``.
    """
    side, depth = clearance
    if not (0 <= side <= 0.5 and 0 <= depth <= 0.5):
        raise ValueError('clearance must be (side, depth) within 0..0.5 mm')
    spin = _slide(slide)
    flip = (slide in ('right', 'down')) ^ entryramp_flip
    body = slot_body(nubs=_nubs(nubs, snap), clearance=clearance,
                     excess=excess_thickness, excess_length=excess_length,
                     entryramp_flip=flip, edge_feature=edge_feature)
    return _consumer(Rot(0, 0, spin) * body, pocket_depth(clearance))


POCKET_DEPTH = pocket_depth()


def seat_location(x: float, z: float, *, slide: str = 'up'):
    """Place the head fixture at the seat, rotated with the cutter."""
    return Pos(x, c.HEAD_DEPTH, z) * Rot(90, 0, 0) * Rot(0, 0, _slide(slide))


def onramp_location(x: float, z: float, *, slide: str = 'up',
                    entryramp_flip: bool = False):
    """Place the inserted head at the direction/flip-adjusted on-ramp."""
    flip = (slide in ('right', 'down')) ^ entryramp_flip
    shift = c.ONRAMP_SHIFT if flip else -c.ONRAMP_SHIFT
    return seat_location(x, z, slide=slide) * Pos(shift, -c.MOVE_DISTANCE, 0)


def vase_body(*, linewidth: float = c.VASE_LINEWIDTH,
              overhang_angle: float = c.VASE_OVERHANG_ANGLE,
              nubs: str = 'left',
              clearance=(c.SIDE_CLEARANCE, c.DEPTH_CLEARANCE)) -> Part:
    """Positive ``ocvase_body`` in the author's slot frame, bed normal +Z.

    Two walls for integration into a vase plate; not a standalone print.
    Worst load pulls the connector off the plate, across the dovetail walls.
    Profile, turtle path, mirrored copy, locks and trim follow upstream
    openconnect_lib.scad:136-148,342-370. All mating edges are spec geometry.
    """
    nubs = _nubs(nubs, None)
    if not isfinite(linewidth) or linewidth <= 0:
        raise ValueError('linewidth must be finite and positive')
    if not isfinite(overhang_angle) or not 0 < overhang_angle < 90:
        raise ValueError('overhang_angle must be between 0 and 90 degrees')
    cs, cd = clearance
    if not (0 <= cs <= 0.5 and 0 <= cd <= 0.5):
        raise ValueError('clearance must be (side, depth) within 0..0.5 mm')
    mid = c.HEAD_MIDDLE_HEIGHT
    wall = 2 * linewidth
    bottom = c.HEAD_BOTTOM_HEIGHT + c.half_angle_share(cs) + cd
    total = pocket_depth(clearance)
    vase_bottom = bottom + c.half_angle_share(wall)
    if vase_bottom >= total:
        raise ValueError('linewidth leaves no vase taper at this clearance')
    profile = [(0, 0), (0, vase_bottom)]
    if total - vase_bottom > mid:
        profile.append((mid, vase_bottom + mid))
    profile += [(min(mid, total - vase_bottom), total), (mid + wall, total),
                (mid + wall, bottom + mid), (wall, bottom), (wall, 0)]
    width = c.HEAD_WIDTH + 2 * cs
    height = c.HEAD_HEIGHT + 2 * cs
    ch = c.HEAD_CHAMFER + cs - c.half_angle_share(cs)
    extra = tan(radians(overhang_angle)) * total
    radius = wall * _SQ2
    corner_offset = c.half_angle_share(radius - wall)
    x = wall + width / 2
    y = -(height - width / 2 - c.BACK_POS_OFFSET + extra)
    straight = extra + height - ch - corner_offset
    p0 = Vector(x, y, 0)
    p1 = Vector(x, y + straight, 0)
    pm = Vector(x - radius + radius * cos(radians(22.5)),
                y + straight + radius * sin(radians(22.5)), 0)
    p2 = Vector(x - radius + radius / _SQ2, y + straight + radius / _SQ2, 0)
    p3 = p2 + Vector(-ch, ch, 0)
    path = Wire([Line(p0, p1), ThreePointArc(p1, pm, p2), Line(p2, p3)])
    face = Face(Wire.make_polygon([Vector(x - u, y, z) for u, z in profile], close=True))
    right = Solid.sweep(face, path)
    body = right + right.mirror(Plane.YZ)
    if nubs in ('left', 'both'):
        body += _lock(-width / 2, 1, bottom, True)
        body -= _lock(-width / 2 - wall - c.EPS, 1, vase_bottom, True)
    if nubs in ('right', 'both'):
        body += _lock(width / 2, -1, bottom, True)
        body -= _lock(width / 2 + wall + c.EPS, -1, vase_bottom, True)
    trim = (Pos(0, y, 0) * Rot(90 - overhang_angle, 0, 0)
            * Box(c.TILE_SIZE, c.VASE_TRIM_LENGTH, total * 2,
                  align=(Align.CENTER, Align.MIN, Align.MIN)))
    return body - trim
