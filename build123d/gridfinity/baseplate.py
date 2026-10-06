"""Gridfinity Rebuilt-derived baseplate profile (MIT-derived constants).

All dimensions [C]: assets/openConnect-gridfinity-shelf/
openconnect_gridfinity_shelf_online.scad:291-311, 1263-1340 (mitufy).
The shelf adaptation carrying these routines is CC-BY-SA-4.0.
"""
from itertools import product

from build123d import Circle, Pos, RectangleRounded, extrude, loft

PITCH = 42
LOWER_TAPER = 0.7
RISER = 1.8
UPPER_TAPER = 2.15
PROFILE_HEIGHT = LOWER_TAPER + RISER + UPPER_TAPER
CLEARANCE = 0.35
TOP_CORNER_RADIUS = 4
MID_INSET = UPPER_TAPER
BOTTOM_INSET = LOWER_TAPER + UPPER_TAPER
MID_RADIUS = TOP_CORNER_RADIUS - MID_INSET
BOTTOM_RADIUS = TOP_CORNER_RADIUS - BOTTOM_INSET
ATTACHMENT_BORDER = 8
EDGE_CLEARANCE = 4
BOSS_EXTRA = 4
BOSS_RAIL_OVERLAP = 2.4
WINDOW_SIZE = PITCH - 2 * BOTTOM_INSET
EPS = 0.005


def cell_positions(w, d):
    return [((i-(w-1)/2)*PITCH, (j-(d-1)/2)*PITCH)
            for i, j in product(range(w), range(d))]


def magnet_offset(diameter):
    return min(PITCH/2-ATTACHMENT_BORDER, PITCH/2-EDGE_CLEARANCE-diameter/2)


def magnet_positions(w, d, mode, diameter=6.4):
    offset = magnet_offset(diameter)
    if mode == 'None':
        return []
    if mode == 'Corners Only':
        return list(product((-(w-1)*PITCH/2-offset, (w-1)*PITCH/2+offset),
                            (-(d-1)*PITCH/2-offset, (d-1)*PITCH/2+offset)))
    if mode != 'All':
        raise ValueError('unknown magnet mode')
    return [(x+dx, y+dy) for x, y in cell_positions(w, d)
            for dx, dy in product((-offset, offset), repeat=2)]


def socket_cutout(clearance=0, magnets=False):
    """Socket bottom at Z=0; top square saturates at pitch + 0.2 mm."""
    top = min(PITCH+0.2, PITCH+max(0, clearance))
    mid, bottom = top-2*MID_INSET, top-2*BOTTOM_INSET
    gap = CLEARANCE if magnets else 0
    low = RectangleRounded(bottom, bottom, BOTTOM_RADIUS)
    middle = RectangleRounded(mid, mid, MID_RADIUS)
    high = RectangleRounded(top, top, TOP_CORNER_RADIUS)
    part = extrude(low, amount=gap+EPS)
    part += loft([Pos(0, 0, gap)*low, Pos(0, 0, gap+LOWER_TAPER)*middle], ruled=True)
    part += extrude(Pos(0, 0, gap+LOWER_TAPER)*middle, amount=RISER)
    part += loft([Pos(0, 0, gap+LOWER_TAPER+RISER)*middle,
                  Pos(0, 0, gap+PROFILE_HEIGHT+EPS)*high], ruled=True)
    return part


def window_cutouts(w, d, height, *, magnets=False, diameter=6.4, mode='All'):
    """Through windows below the sockets, retaining each enabled magnet boss."""
    size = (max(1, min(WINDOW_SIZE, 2*(magnet_offset(diameter)+(diameter+BOSS_EXTRA)/2
                                     - BOSS_RAIL_OVERLAP))) if magnets else WINDOW_SIZE)
    windows = None
    for x, y in cell_positions(w, d):
        face = Pos(x, y)*RectangleRounded(size, size, BOTTOM_RADIUS)
        windows = face if windows is None else windows+face
    if magnets:
        for x, y in magnet_positions(w, d, mode, diameter):
            windows -= Pos(x, y)*Circle((diameter+BOSS_EXTRA)/2)
    return extrude(Pos(0, 0, -height-EPS)*windows, amount=height+2*EPS)
