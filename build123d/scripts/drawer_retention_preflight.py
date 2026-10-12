"""Reproduce the drawer/library maximum-clearance retention contract conflict.

Run from build123d/: uv run python scripts/drawer_retention_preflight.py
No contract or cutter is changed. Compare the isolated library tile, the
untreated shell and the mandatory-bevel shell at the same positive head pose.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build123d import Align, Box, Pos
from drawer import shell
from openconnect.grid import fixtures, layout
from openconnect.slot import head, pocket_depth


def interference(part, fixture):
    overlap = part & fixture
    return 0.0 if overlap is None else overlap.volume


def measure():
    rows = []
    distances = (0, .5, .6, 1, 2)
    for clearance in ((.1, .1), (.5, .1), (.1, .5), (.5, .5)):
        fx = fixtures(layout(1, 1), clearance=clearance, edge_feature='none')
        tile = Box(28, pocket_depth(clearance)+.9, 28,
                   align=(Align.CENTER, Align.MIN, Align.CENTER))-fx.cutters[0]
        v = dict(horizontal_grids=1, vertical_grids=1, depth_grids=1,
                 slot_side_clearance=clearance[0], slot_depth_clearance=clearance[1])
        drawer_fx = shell.slot_fixtures(v)
        before = shell.before_bed_chamfer(v)
        cases = [('library', tile, fx), ('before', before, drawer_fx),
                 ('bevel', shell.chamfer_bed(before, v), drawer_fx)]
        for name, part, placement in cases:
            fixture = placement.seat_locs[0]*head()
            rows.append(dict(case=name, clearance=clearance,
                             pull_distances_mm=distances,
                             interference_mm3=[round(interference(part, Pos(0, -d, 0)*fixture), 6)
                                               for d in distances]))
    return rows


if __name__ == '__main__':
    print(json.dumps(measure(), indent=2))
