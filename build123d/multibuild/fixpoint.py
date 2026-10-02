# Derived from MultiBuild remixing files — Multiboard Licence (non-commercial,
# remixes under the same terms); NOT covered by this repository's MIT licence.
# See build123d/multibuild/LICENSE-MULTIBOARD.md.
"""MultiBuild Fix Point slot negative and Fix Point head fixture (pst-7shtl).

Re-derived from the official "Fix Point Slot - Negative" and "Fix Point -
Positive" STEP remixing files (Multiboard Licence, non-commercial: the
originals are never committed, reference/FETCH.md). Every constant below is
[V], measured into reference/measured/mb-fix-point-*.json, and
tests/test_fixpoint.py checks the rebuilt solids against the originals
(``-m upstream``). Nothing reads a STEP at build time.

* slot frame (the official files'): the consumer back face at Z=0, pocket
  Z=0..3.2. A head enters the well centred on Y=-6, then slides +Y to the
  seat at the origin, where a regular-octagon lip (inradius 6 at the face,
  widening at 45 degrees to 8.5) closes over the head's 45-degree flare.
* consumer frame (same as multibuild.multiconnect): back face Y=0, material
  +Y, the lip end UP (+Z). The head enters the well 6 mm below its seat and
  rides +Z as the consumer lowers; gravity holds it under the lip.
"""
from math import radians, tan

from build123d import Align, Box, Cone, Cylinder, Face, Part, Pos, Rot, Solid, Vector, Wire

from .constants import Provenance

_SLOT = 'multibuild-fix-point-slots/fix-point-slot-negative.step'
_HEAD = 'multibuild-fix-points/fix-point-positive.step'
_SLOT_JSON = 'reference/measured/mb-fix-point-slot-negative.json'
_HEAD_JSON = 'reference/measured/mb-fix-point-positive.json'

# Slot (YZ section at X=0; the lip and well outlines are regular octagons).
SLOT_DEPTH = 3.2
MOUTH_INRADIUS = 6.0     # lip edge at the face, around the seat
LIP_LAND = 0.4           # straight band at the face before the 45-degree flare
DEEP_INRADIUS = 8.5      # pocket half-width behind the lip and in the well
WELL_END = -14.5         # the well's far (-Y) end at the face
TAIL_UNDERCUT_Z = 1.8    # the far end steps out 45 degrees from here ...
TAIL_END = -14.9         # ... to here, at full depth
# Head (XZ section at Y=0, coaxial radii; four 45-degree notches in the top).
HEAD_HEIGHT = 3.0
NECK_RADIUS = 5.87
NECK_HEIGHT = 0.454
HEAD_RADIUS = 8.0
HEAD_FLAT = 7.2          # half-width across the two flats
NOTCH_FLOOR = 2.6
NOTCH_INSET = 2.1        # notch walls from the axes, at the top face
NOTCH_RADIUS = 5.0       # notch outer arc, at the top face

PROVENANCE = {
    **{k: Provenance(v, 'V', _SLOT, _SLOT_JSON) for k, v in (
        ('SLOT_DEPTH', SLOT_DEPTH), ('MOUTH_INRADIUS', MOUTH_INRADIUS), ('LIP_LAND', LIP_LAND),
        ('DEEP_INRADIUS', DEEP_INRADIUS), ('WELL_END', WELL_END),
        ('TAIL_UNDERCUT_Z', TAIL_UNDERCUT_Z), ('TAIL_END', TAIL_END))},
    **{k: Provenance(v, 'V', _HEAD, _HEAD_JSON) for k, v in (
        ('HEAD_HEIGHT', HEAD_HEIGHT), ('NECK_RADIUS', NECK_RADIUS), ('NECK_HEIGHT', NECK_HEIGHT),
        ('HEAD_RADIUS', HEAD_RADIUS), ('HEAD_FLAT', HEAD_FLAT), ('NOTCH_FLOOR', NOTCH_FLOOR),
        ('NOTCH_INSET', NOTCH_INSET), ('NOTCH_RADIUS', NOTCH_RADIUS))},
}

# Derived: 45-degree lip flare, the well centre and the slide to the seat.
LIP_TOP = LIP_LAND + DEEP_INRADIUS - MOUTH_INRADIUS    # 2.9
TRAVEL = -(WELL_END + DEEP_INRADIUS)                     # 6.0
SLOT_LENGTH = DEEP_INRADIUS - TAIL_END                   # 23.4
POCKET_DEPTH = SLOT_DEPTH
FLARE_TOP = NECK_HEIGHT + HEAD_RADIUS - NECK_RADIUS      # 2.584, 45 degrees

_TAN = tan(radians(22.5))
_TO_CONSUMER = Rot(0, 0, 180) * Rot(90, 0, 0)          # (x, y, z) -> (-x, z, y)


def _octagon(r, yc=0.0):
    """Regular octagon of inradius ``r`` centred on (0, yc), flats on the axes."""
    h = r * _TAN
    return [(r, yc - h), (r, yc + h), (h, yc + r), (-h, yc + r),
            (-r, yc + h), (-r, yc - h), (-h, yc - r), (h, yc - r)]


def _face(points, z=0.0) -> Face:
    return Face(Wire.make_polygon([Vector(x, y, z) for x, y in points], close=True))


def slot_body() -> Part:
    """The Fix Point Slot negative in the official files' frame."""
    # Well: deep octagon around the entry centre, full depth; its far end
    # runs on along the 45-degree sides to TAIL_END, undercut from the face.
    well = _octagon(DEEP_INRADIUS, -TRAVEL)
    run = WELL_END - TAIL_END
    well = [(x - run * (1 if x > 0 else -1), TAIL_END) if y < WELL_END + 1e-9 else (x, y)
            for x, y in well]
    body = Solid.extrude(_face(well), Vector(0, 0, SLOT_DEPTH))
    edge = TAIL_UNDERCUT_Z + run
    keep = Face(Wire.make_polygon([Vector(-DEEP_INRADIUS - 1, y, z) for y, z in (
        (WELL_END, -1), (WELL_END, TAIL_UNDERCUT_Z), (TAIL_END - 1, edge + 1), (TAIL_END - 1, -1))],
        close=True))
    body -= Solid.extrude(keep, Vector(2 * DEEP_INRADIUS + 2, 0, 0))
    # Lip around the seat: straight land, 45-degree flare, straight to depth.
    mouth, deep = _octagon(MOUTH_INRADIUS), _octagon(DEEP_INRADIUS)
    body += Solid.extrude(_face(mouth), Vector(0, 0, LIP_LAND))
    body += Solid.make_loft([_face(mouth, LIP_LAND).outer_wire(),
                             _face(deep, LIP_TOP).outer_wire()], ruled=True)
    body += Solid.extrude(_face(deep, LIP_TOP), Vector(0, 0, SLOT_DEPTH - LIP_TOP))
    return body.clean()


def head_body() -> Part:
    """The Fix Point (Regular) positive head in the official files' frame:
    neck on the board at Z=0, top at Z=3.0."""
    up = (Align.CENTER, Align.CENTER, Align.MIN)
    part = (Cylinder(NECK_RADIUS, NECK_HEIGHT, align=up)
            + Pos(0, 0, NECK_HEIGHT) * Cone(NECK_RADIUS, HEAD_RADIUS, FLARE_TOP - NECK_HEIGHT, align=up)
            + Pos(0, 0, FLARE_TOP) * Cylinder(HEAD_RADIUS, HEAD_HEIGHT - FLARE_TOP, align=up))
    part &= Pos(0, 0, -1) * Box(2 * HEAD_FLAT, 2 * HEAD_RADIUS + 2, HEAD_HEIGHT + 2, align=up)
    # Four 45-degree notches in the top face (quadrants between a cross).
    depth, over = HEAD_HEIGHT - NOTCH_FLOOR, 0.1
    floor_inset, floor_r = NOTCH_INSET + depth, NOTCH_RADIUS - depth
    ring = Pos(0, 0, NOTCH_FLOOR) * Cone(floor_r, NOTCH_RADIUS + over, depth + over, align=up)
    far = NOTCH_RADIUS + 1
    for sx in (1, -1):
        for sy in (1, -1):
            lo = [(sx * floor_inset, sy * floor_inset), (sx * far, sy * floor_inset),
                  (sx * far, sy * far), (sx * floor_inset, sy * far)]
            hi = [(sx * (NOTCH_INSET - over), sy * (NOTCH_INSET - over)), (sx * far, sy * (NOTCH_INSET - over)),
                  (sx * far, sy * far), (sx * (NOTCH_INSET - over), sy * far)]
            wedge = Solid.make_loft([_face(lo, NOTCH_FLOOR).outer_wire(),
                                     _face(hi, HEAD_HEIGHT + over).outer_wire()], ruled=True)
            part -= ring & wedge
    return part.clean()


def slot_cutter() -> Part:
    """Fix Point slot negative in the consumer frame: back face Y=0, pocket
    Y=0..3.2 at +Y, the seat on the origin and the lip end up (+Z); the well
    opens on the back face, centred TRAVEL (6 mm) below the seat."""
    return _TO_CONSUMER * slot_body()


def head() -> Part:
    """Fix Point head as a contract FIXTURE only, never printed from here:
    official frame, neck at Z=0, axis on the origin."""
    return head_body()


def seat_location(x: float, z: float):
    """``seat_location(x, z) * head()`` is a head seated in the slot whose
    cutter was placed at ``Pos(x, 0, z)``: neck on the board (Y=0)."""
    return Pos(x, 0, z) * _TO_CONSUMER


def entry_location(x: float, z: float):
    """The same head pushed into that slot's well, TRAVEL below the seat."""
    return Pos(x, 0, z - TRAVEL) * _TO_CONSUMER
