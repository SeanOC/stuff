"""openConnect grid placement, ported from mitufy's CC BY 4.0 source.

[C] openconnect_lib.scad:478-485 and opengrid_base.scad:139-153 at
04e2277a71c5 (assets/openConnect). Indices run left to right, TOP to bottom.
"""
from dataclasses import dataclass

from build123d import Align, Box, Pos
from holders.registry import MountFixtures
from .constants import DEPTH_CLEARANCE, EPS, SIDE_CLEARANCE, TILE_SIZE
from .slot import onramp_location, pocket_depth, seat_location, slot_cutter

POSITIONS = ('all', 'staggered', 'edge-rows', 'edge-columns', 'corners')
LOCKS = ('corners', 'all', 'staggered', 'top-corners', 'none')
SLIDES = {'up': (0., 0., 1.), 'down': (0., 0., -1.),
          'left': (-1., 0., 0.), 'right': (1., 0., 0.)}


@dataclass(frozen=True)
class SlotPlacement:
    x: float
    z: float
    nubs: str
    slide: str
    entryramp_flip: bool


def _matches(i, j, h, v, pattern):
    row, column = j in (0, v - 1), i in (0, h - 1)
    return {'all': True, 'none': False, 'staggered': i % 2 == j % 2,
            'edge-rows': row, 'edge-columns': column, 'corners': row and column,
            'top-corners': j == 0 and column}[pattern]


def layout(h_grids, v_grids, *, position='all', lock='corners', slide='up',
           entryramp_flip=False, except_positions=()) -> list[SlotPlacement]:
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 1
           for n in (h_grids, v_grids)):
        raise ValueError('grid counts must be positive integers')
    if position not in POSITIONS or lock not in LOCKS or slide not in SLIDES:
        raise ValueError('invalid grid position, lock or slide')
    excluded = {tuple(p) for p in except_positions}
    return [SlotPlacement(-(h_grids - 2*i - 1)*TILE_SIZE/2,
                          (v_grids - 2*j - 1)*TILE_SIZE/2,
                          'left' if _matches(i, j, h_grids, v_grids, lock) else 'none',
                          slide, entryramp_flip)
            for i in range(h_grids) for j in range(v_grids)
            if (i, j) not in excluded and _matches(i, j, h_grids, v_grids, position)]


def fixtures(placements, clearance=(SIDE_CLEARANCE, DEPTH_CLEARANCE), *,
             edge_feature='both', excess_thickness=EPS, excess_length=0.0) -> MountFixtures:
    placements = list(placements)
    slides = {p.slide for p in placements}
    if len(slides) > 1:
        raise ValueError('MountFixtures requires one shared slide direction')
    return MountFixtures(
        cutters=[Pos(p.x, 0, p.z) * slot_cutter(
            nubs=p.nubs, slide=p.slide, entryramp_flip=p.entryramp_flip,
            clearance=clearance, edge_feature=edge_feature,
            excess_thickness=excess_thickness, excess_length=excess_length) for p in placements],
        seat_locs=[seat_location(p.x, p.z, slide=p.slide) for p in placements],
        onramp_locs=[onramp_location(p.x, p.z, slide=p.slide,
                                  entryramp_flip=p.entryramp_flip) for p in placements],
        entry_axis=SLIDES[next(iter(slides), 'up')],
    )


def row_strip(h_grids, excess_length, excess_thickness=EPS):
    """[C] shelf source:1134-1138, row extension at the lower on-ramp end.

    Separate from MountFixtures: those lists remain one item per slot.
    Frame matches layout(h_grids, 1), with the row centred at Z=0.
    """
    return Pos(0, -excess_thickness, -TILE_SIZE/2-excess_length)*Box(
        h_grids*TILE_SIZE, pocket_depth()+excess_thickness, excess_length,
        align=(Align.CENTER, Align.MIN, Align.MIN))
