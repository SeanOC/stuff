"""Unregistered openConnect test plate: print standing, +Z up, bottom at Z=0.

84 x 84 x 5.5 mm (3 x 3 openGrid tiles) with four slots on the 28 mm pitch,
at the tile centres of the central 2 x 2 block (X = +-14, Z = 28 / 56).
Backing behind each 2.7 mm pocket is 2.8 mm (minimum 2.4). No service-load
rating; a consumer must assess its own off-wall bending load. Only the slot
pockets are accepted support-requiring features in PLA/PCTG.
"""
from build123d import Align, Axis, Box, Part, Pos, chamfer
from holders.registry import MountFixtures
from .constants import TILE_SIZE
from .slot import onramp_location, seat_location, slot_cutter

MOUNT = 'openconnect-slot'
WIDTH, HEIGHT, THICKNESS = 3 * TILE_SIZE, 3 * TILE_SIZE, 5.5
BED_CHAMFER = 0.4
PRINT_ORIENTATION = (0.0, 0.0, 1.0)
SLOTS = tuple((x, HEIGHT / 2 + z) for z in (-TILE_SIZE / 2, TILE_SIZE / 2)
              for x in (-TILE_SIZE / 2, TILE_SIZE / 2))


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    cutter = slot_cutter(snap=True)
    return MountFixtures(
        cutters=[Pos(x, 0, z) * cutter for x, z in SLOTS],
        seat_locs=[seat_location(x, z) for x, z in SLOTS],
        entry_axis=(0.0, 0.0, 1.0), face_normal=(0.0, -1.0, 0.0),
        onramp_locs=[onramp_location(x, z) for x, z in SLOTS],
    )


def build(values=None) -> Part:
    plate = Box(WIDTH, THICKNESS, HEIGHT, align=(Align.CENTER, Align.MIN, Align.MIN))
    # The pockets never reach the bed face, so a plain chamfer gives the relief.
    plate = chamfer(plate.faces().sort_by(Axis.Z)[0].edges(), BED_CHAMFER)
    for cutter in mount_fixtures(MOUNT, {}).cutters:
        plate -= cutter
    return plate
