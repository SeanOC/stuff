"""Unregistered test plate: print standing, +Z up, bottom at Z=0.

No service-load rating; a consumer must assess its own off-wall bending load.
Only library slot pockets are accepted support-requiring features in PLA/PCTG.
"""
from build123d import Align, Axis, Box, Pos, Rot, Cone, Face, Wire, Solid, Vector, Part
from holders.registry import MountFixtures
from .constants import PITCH
from .multiconnect import POCKET_DEPTH, slot_cutter, channel_cutter

MOUNT = 'multibuild-multiconnect-slot'
WIDTH, HEIGHT, THICKNESS = 70.0, 100.0, 7.0
BED_CHAMFER = 0.4
SEAT_Z = 24.0  # 25 mm channel extends 1 mm below the plate for entry.
PRINT_ORIENTATION = (0.0, 0.0, 1.0)
CHANNEL_MOUNT = 'multibuild-multiconnect-channel'
CHANNEL_LENGTH = 75.0
ONRAMPS = (12.5, 37.5)
SEATS = (25.0, 50.0)


def mount_fixtures(mount_type, values):
    if mount_type == CHANNEL_MOUNT:
        channel = channel_cutter(CHANNEL_LENGTH, onramps=ONRAMPS, seats=SEATS)
        return MountFixtures(
            cutters=[Pos(x, 0, 0) * channel for x in (-PITCH / 2, PITCH / 2)],
            seat_locs=[Pos(x, POCKET_DEPTH, z) * Rot(90, 0, 0)
                       for x in (-PITCH / 2, PITCH / 2) for z in SEATS],
            onramp_locs=[Pos(x, POCKET_DEPTH, z) * Rot(90, 0, 0)
                         for x in (-PITCH / 2, PITCH / 2) for z in ONRAMPS],
        )
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    xs = (-PITCH / 2, PITCH / 2)
    return MountFixtures(
        cutters=[Pos(x, 0, SEAT_Z) * slot_cutter(snap=True) for x in xs],
        seat_locs=[Pos(x, POCKET_DEPTH, SEAT_Z) * Rot(90, 0, 0) for x in xs],
        entry_axis=(0.0, 0.0, 1.0), face_normal=(0.0, -1.0, 0.0),
    )


def build(values=None) -> Part:
    plate = Box(WIDTH, THICKNESS, HEIGHT, align=(Align.CENTER, Align.MIN, Align.MIN))
    for cutter in mount_fixtures(MOUNT, {}).cutters:
        plate -= cutter
    return _relieve_bed(plate)


def channel_plate() -> Part:
    """70x100x7 demo; 2.85 mm backing, 25 mm closed cap, no service load."""
    plate = Box(WIDTH, THICKNESS, HEIGHT, align=(Align.CENTER, Align.MIN, Align.MIN))
    for cutter in mount_fixtures(CHANNEL_MOUNT, {}).cutters:
        plate -= cutter
    return _relieve_bed(plate)


def _relieve_bed(plate: Part) -> Part:
    # Include the aperture edges: every edge of the remaining bed-contact face.
    bottom = plate.faces().filter_by(Axis.Z).sort_by(Axis.Z)[0]
    # OCCT's chamfer builder fails at the short lip edges (0.438 mm).
    # Subtract finite 45-degree wedges and conical corner joins instead.
    unrelieved = plate
    for edge in bottom.edges():
        a, b = edge.vertices()
        start, end = Vector(a), Vector(b)
        tangent = (end - start).normalized()
        inward = Vector(-tangent.Y, tangent.X, 0)
        if not unrelieved.is_inside(edge.center() + inward * 0.01 + Vector(0, 0, 0.01)):
            inward = -inward
        triangle = Face(Wire.make_polygon([
            start, start + inward * BED_CHAMFER,
            start + Vector(0, 0, BED_CHAMFER), start,
        ]))
        plate -= Solid.extrude(triangle, tangent * edge.length)
    for vertex in bottom.vertices():
        plate -= Pos(vertex.X, vertex.Y, 0) * Cone(
            BED_CHAMFER, 0, BED_CHAMFER,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    return plate
