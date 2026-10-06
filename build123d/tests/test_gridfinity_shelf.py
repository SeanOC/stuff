"""Regression checks for the Gridfinity shelf's published mount geometry."""
import sys
from pathlib import Path

import pytest
from build123d import Align, Axis, Box, Pos, Solid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holders import gridfinity_shelf as m
from tests.mount_contracts import verify_openconnect_slot


@pytest.mark.parametrize('values,thickness', [({}, 0.8), ({'shelf_back_offset': 1.55}, 2.4)],
                         ids=['default', 'sturdy-back'])
def test_rev7_backing_envelope(values, thickness):
    """Rev 7: remove exactly the Z<0 slab, then require full backing."""
    part = m.build(values)
    fx = m.mount_fixtures(m.MOUNT, values)
    _, width, depth, *_ = m.dimensions(values)
    envelope = Box(width, depth, 28, align=(Align.CENTER, Align.MIN, Align.MIN))
    below = Pos(0, 0, -10)*Box(width, depth, 10,
                             align=(Align.CENTER, Align.MIN, Align.MIN))
    for cutter in fx.cutters:
        back = cutter.bounding_box().max.Y
        for face in cutter.faces().filter_by(Axis.Y):
            if abs(face.center().Y-back) > 1e-7:
                continue
            probe = Solid.extrude(face, (0, thickness, 0))
            clipped = probe & envelope
            removed = probe-clipped
            lower = probe & below
            assert removed.volume == pytest.approx(lower.volume, abs=1e-7)
            assert (removed-lower).volume < 1e-7
            assert (lower-removed).volume < 1e-7
    verify_openconnect_slot(part, fx, min_backing=thickness, backing_envelope=envelope)
