"""CB2 checkpoint: parity and reference evidence for the rev-3 audit conflict.

These are diagnostic regression tests, not the completed acceptance suite.
The endpoint/edge/socket/containment suite awaits the spec's bridge decision.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gridfinity import bin as gf
from tests.parity import (
    bbox_parity,
    load_reference,
    mesh_from_part,
    surface_distance,
    volume_parity,
)
from tests.print_audit import audit

REFERENCE = Path(__file__).resolve().parents[2]/'assets/gridfinity-rebuilt/mesh/gr-bin-2x2x3-nolip.stl'


def test_pre_treatment_reference_parity(tmp_path):
    ref = load_reference(REFERENCE)
    part = gf.body(2, 2, 3, gf.REFERENCE_WALL)
    port = mesh_from_part(part, tmp_path/'port.stl', tolerance=.01, angular_tolerance=.1)
    assert ref.is_watertight and port.is_watertight
    assert bbox_parity(port, ref, tol=.05, mode='ordered', rtol=0)
    assert volume_parity(port, ref, rel=.01)
    for left, right in ((port, ref), (ref, port)):
        _, distances = surface_distance(left, right, n=10000, seed=17,
                                        sampler='uniform', vertices=True, signed=False)
        assert max(distances) <= .15


def test_reference_has_horizontal_underside_between_feet():
    """Exact reference evidence: 374 downward triangles, Z=4.75 mm."""
    ref = load_reference(REFERENCE)
    face_mask = ((ref.face_normals[:, 2] < -.999999)
                 & (np.abs(ref.triangles_center[:, 2]-gf.PROFILE_HEIGHT) < 1e-6))
    assert np.count_nonzero(face_mask) == 374
    assert ref.area_faces[face_mask].sum() == pytest.approx(119.5754275, abs=.001)
    # A probe in the 0.5 mm inter-foot gap meets the horizontal underside.
    hits, _, _ = ref.ray.intersects_location([[0, 10, 0]], [[0, 0, 1]])
    assert min(hits[:, 2]) == pytest.approx(4.75, abs=1e-6)


@pytest.mark.audit
def test_reference_parity_port_reproduces_rev3_audit_conflict():
    """Remove/replace this diagnostic ONLY after the spec resolves the conflict."""
    report = audit(gf.body(2, 2, 3, gf.REFERENCE_WALL))
    assert report.max_overhang_deg == 90
    assert report.longest_bridge_mm <= 10
    assert report.min_wall_mm >= .9
    assert report.bed_chamfer == 'present'
    assert not report.downward_fillets
    assert report.failures() == ['overhang 90.0° > 45° (steeper than 45° from vertical)']
