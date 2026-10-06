"""Regression checks for the Gridfinity shelf's published mount geometry."""
import sys
from pathlib import Path

import pytest
from build123d import Axis, Face, Solid, Wire

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holders import gridfinity_shelf as m
from tests.mount_contracts import verify_openconnect_slot


@pytest.mark.parametrize('values,thickness', [({}, 0.8), ({'shelf_back_offset': 1.55}, 2.4)],
                         ids=['default', 'sturdy-back'])
def test_rev8_backing_envelope(values, thickness):
    """Rev 8: remove exactly the below-wedge slab, then require full backing."""
    part = m.build(values)
    fx = m.mount_fixtures(m.MOUNT, values)
    _, width, depth, _, _, tilt, *_ = m.dimensions(values)
    envelope = m.backing_envelope(values)
    below = Solid.extrude(Face(Wire.make_polygon([
        (-width/2, 0, -10), (-width/2, depth, -10),
        (-width/2, depth, tilt), (-width/2, 0, 0)], close=True)), (width, 0, 0))
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
