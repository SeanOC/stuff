"""Pattern tables read independently from opengrid_base.scad:139-153.

Rows in each string run TOP to bottom; columns run left to right.
"""
import sys
from pathlib import Path

import pytest
from build123d import Pos

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openconnect.grid import LOCKS, POSITIONS, SlotPlacement, fixtures, layout
from openconnect.slot import onramp_location, seat_location, slot_cutter


TABLES = {
    (1, 1): dict(all='1', staggered='1', corners='1',
                 top_corners='1', edge_rows='1', edge_columns='1'),
    (2, 2): dict(all='11/11', staggered='10/01', corners='11/11',
                 top_corners='11/00', edge_rows='11/11', edge_columns='11/11'),
    (3, 2): dict(all='111/111', staggered='101/010', corners='101/101',
                 top_corners='101/000', edge_rows='111/111', edge_columns='101/101'),
    (4, 3): dict(all='1111/1111/1111', staggered='1010/0101/1010',
                 corners='1001/0000/1001', top_corners='1001/0000/0000',
                 edge_rows='1111/0000/1111', edge_columns='1001/1001/1001'),
}


def cells(h, v, pattern):
    if pattern == 'none':
        return set()
    rows = TABLES[h, v][pattern.replace('-', '_')].split('/')
    return {(i, j) for j, row in enumerate(rows) for i, value in enumerate(row)
            if value == '1'}


@pytest.mark.parametrize('h,v', TABLES)
@pytest.mark.parametrize('position', POSITIONS)
@pytest.mark.parametrize('lock', LOCKS)
def test_pattern_tables(h, v, position, lock):
    selected, locked = cells(h, v, position), cells(h, v, lock)
    expected = [SlotPlacement((i - (h-1)/2)*28, ((v-1)/2 - j)*28,
                              'left' if (i, j) in locked else 'none', 'up', False)
                for i, j in sorted(selected)]
    assert layout(h, v, position=position, lock=lock) == expected


def test_exceptions_are_top_indexed_and_do_not_shift_lock_parity():
    placements = layout(3, 2, lock='staggered', except_positions=[(0, 0), (1, 1)])
    assert [(p.x, p.z, p.nubs) for p in placements] == [
        (-28, -14, 'none'), (0, 14, 'none'), (28, 14, 'left'), (28, -14, 'none')]


def test_oc3_four_corner_slots():
    assert [(p.x, p.z, p.nubs) for p in layout(2, 2, lock='corners')] == [
        (-14, 14, 'left'), (-14, -14, 'left'), (14, 14, 'left'), (14, -14, 'left')]


@pytest.mark.parametrize('slide,axis', [('up', (0, 0, 1)), ('down', (0, 0, -1)),
                                     ('left', (-1, 0, 0)), ('right', (1, 0, 0))])
@pytest.mark.parametrize('flip', [False, True])
def test_fixtures_pass_slide_and_flip_raw(slide, axis, flip):
    p = SlotPlacement(17, 31, 'left', slide, flip)
    fx = fixtures([p], clearance=(0.2, 0.3))
    direct = Pos(p.x, 0, p.z) * slot_cutter(
        nubs='left', slide=slide, entryramp_flip=flip, clearance=(0.2, 0.3))
    assert (fx.cutters[0] - direct).volume < 1e-8
    assert (direct - fx.cutters[0]).volume < 1e-8
    assert fx.seat_locs == [seat_location(p.x, p.z, slide=slide)]
    assert fx.onramp_locs == [onramp_location(p.x, p.z, slide=slide, entryramp_flip=flip)]
    assert fx.entry_axis == axis
    assert fx.face_normal == (0, -1, 0)


@pytest.mark.parametrize('args,kwargs', [((0, 1), {}), ((1, -1), {}),
    ((1.5, 1), {}), ((True, 1), {}), ((1, 1), {'position': 'bad'}),
    ((1, 1), {'lock': 'bad'}), ((1, 1), {'slide': 'bad'})])
def test_invalid_layout(args, kwargs):
    with pytest.raises(ValueError):
        layout(*args, **kwargs)


def test_fixtures_reject_mixed_slide_directions():
    with pytest.raises(ValueError, match='shared slide'):
        fixtures([SlotPlacement(0, 0, 'none', 'up', False),
                  SlotPlacement(28, 0, 'none', 'down', False)])
