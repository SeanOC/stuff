"""Reproduce the drawer/library maximum-clearance retention contract conflict.

Run from build123d/: uv run python scripts/drawer_retention_preflight.py
Add --search-caps to reproduce the REV 3e retention-domain bisection.
No contract or cutter is changed. Compare the isolated library tile, the
untreated shell and the mandatory-bevel shell at the same positive head pose.
"""
import argparse
import json
from contextlib import ExitStack
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build123d import Align, Box, Pos
from drawer import shell
from drawer import constants as c
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


def search_caps():
    """REV 3e: discrete bisection, full default shell with mandatory bevel.

    Record the least interference across ALL ten seats at each pull distance.
    Independent axes are searched first, then their combined maximum. If
    necessary, search a common cap for the pair. Each candidate
    also runs the complete, unchanged shallow mount contract.
    """
    from tests.mount_contracts import verify_openconnect_slot

    rows, cache = [], {}

    def probe(side, depth):
        key = (side, depth)
        if key in cache:
            return cache[key]
        values = dict(slot_side_clearance=side, slot_depth_clearance=depth)
        before = shell.before_bed_chamfer(values)
        part = shell.chamfer_bed(before, values)
        fx = shell.slot_fixtures(values)
        positive = head()
        pulls = [min(interference(part, Pos(0, -d, 0)*loc*positive)
                     for loc in fx.seat_locs) for d in (.5, 1, 2)]
        try:
            verify_openconnect_slot(part, fx, min_backing=.8,
                                    backing_envelope=shell.body(values)-(before-part))
            error = None
        except AssertionError as exc:
            error = str(exc)
        row = dict(side=side, depth=depth, min_interference_mm3=pulls,
                   passed=error is None, error=error)
        rows.append(row)
        print(json.dumps(row), file=sys.stderr, flush=True)
        cache[key] = error is None
        return cache[key]

    def search(pair):
        low, high = 2, 11  # 0.10..0.50, in exact 0.05 mm steps
        assert probe(*pair(.1)), 'author defaults must pass'
        while high-low > 1:
            mid = (low+high)//2
            if probe(*pair(mid/20)):
                low = mid
            else:
                high = mid
        return low/20

    side = search(lambda value: (value, .1))
    depth = search(lambda value: (.1, value))
    paired = (side, depth)
    if not probe(*paired):
        common = search(lambda value: (value, value))
        paired = (common, common)
    return dict(independent_side_cap=side, independent_depth_cap=depth,
                paired_caps=paired, pull_distances_mm=[.5, 1, 2], rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--search-caps', action='store_true')
    args = parser.parse_args()
    # Diagnostic-only: reconstruct the author's wider domain, including the
    # rejected geometry. Production builds always enforce the measured caps;
    # neither the mount contract nor the cutters are changed by this probe.
    with ExitStack() as stack:
        for name in ('SLOT_SIDE_CLEARANCE_MAX', 'SLOT_DEPTH_CLEARANCE_MAX'):
            stack.enter_context(patch.object(c, name, .5, create=True))
        print(json.dumps(search_caps() if args.search_caps else measure(), indent=2))
