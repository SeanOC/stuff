# SPDX-License-Identifier: CC-BY-SA-4.0
"""Reference checks for the drawer body foundation (feature port in progress)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
import trimesh

from drawer import shell


REFERENCES = Path(__file__).resolve().parents[2] / 'assets/openConnect-drawer/mesh'


@pytest.mark.parametrize('name,values', [
    ('shell-all-solid', {}),
    ('shell-1x1x1-solid', dict(horizontal_grids=1, vertical_grids=1, depth_grids=1)),
    ('shell-top-slot-solid', dict(shell_slot_position='Top')),
])
def test_reference_body_envelope_and_cavity(name, values):
    """Check the box/cavity against actual source meshes away from cut features.

This is deliberately not finished-model parity: slots, magnets, stoppers
and bed treatment are still absent from the body primitive.
"""
    ref = trimesh.load_mesh(REFERENCES / f'{name}.stl')
    body = shell.source_body(values)
    assert body.is_valid
    assert len(body.solids()) == 1
    bb = body.bounding_box()
    assert np.array([tuple(bb.min), tuple(bb.max)]) == pytest.approx(ref.bounds, abs=1e-5)
    # Mid-depth sections avoid front magnet/stopper cuts and back pockets.
    # Probe both sides of the side walls and the non-slot bottom wall.
    w = values.get('horizontal_grids', 5)*28-4.8
    h = values.get('vertical_grids', 2)*28-4.8
    y = values.get('depth_grids', 5)*14
    points = [(0, 0, y), (w/2-.1, 0, y), (w/2+.1, 0, y),
              (-w/2+.1, 0, y), (-w/2-.1, 0, y),
              (0, -h/2+.1, y), (0, -h/2-.1, y)]
    expected = [False, False, True, False, True, False, True]
    assert ref.contains(points).tolist() == expected
    assert [body.is_inside(p) for p in points] == expected


@pytest.mark.parametrize('face', shell.SLOT_FACES)
def test_requested_print_face_lies_on_bed(face):
    values = {'shell_slot_position': face}
    printed = shell.print_frame(values) * shell.body(values)
    assert printed.bounding_box().min.Z == pytest.approx(0, abs=1e-7)


@pytest.mark.parametrize('backing', [.6, .7])
def test_reject_backing_below_decided_shallow_contract(backing):
    with pytest.raises(ValueError, match='shell_to_slot_wall_thickness below 0.8 mm'):
        shell.body({'shell_to_slot_wall_thickness': backing})


def test_reject_empty_cavity_with_author_error():
    with pytest.raises(ValueError, match='shell inner dimensions must be greater than 0'):
        shell.body({'horizontal_grids': 1, 'shell_thickness': 14})
