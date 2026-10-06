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
def test_rev10_backing_envelope(values, thickness):
    """Rev 10: exclude only the below-wedge slab plus the E1 envelope bevel."""
    part = m.build(values)
    fx = m.mount_fixtures(m.MOUNT, values)
    _, width, depth, _, _, tilt, *_ = m.dimensions(values)
    envelope = m.backing_envelope(values)
    below = Solid.extrude(Face(Wire.make_polygon([
        (-width/2, 0, -10), (-width/2, depth, -10),
        (-width/2, depth, tilt), (-width/2, 0, 0)], close=True)), (width, 0, 0))
    bevel = m.uncut_wedge(values) - envelope
    for cutter in fx.cutters:
        back = cutter.bounding_box().max.Y
        for face in cutter.faces().filter_by(Axis.Y):
            if abs(face.center().Y-back) > 1e-7:
                continue
            probe = Solid.extrude(face, (0, thickness, 0))
            clipped = probe & envelope
            removed = probe-clipped
            lower = (probe & below) + (probe & bevel)
            assert removed.volume == pytest.approx(lower.volume, abs=0.05)
            assert (removed-lower).volume < 1e-7
            assert (lower-removed).volume < 1e-7
    verify_openconnect_slot(part, fx, min_backing=thickness, backing_envelope=envelope)


def reference_bed_band(mesh, points):
    """Rev 9 E3 band, from the reference underside's welded triangle boundary.

    Reference meshes already use the author's bed-down print frame. The
    0.02 mm plane tolerance includes only the source's EPS-sized bed drift;
    downward normals reject short side faces near the same plane.
    """
    import numpy as np

    bed = mesh.triangles[(mesh.face_normals[:, 2] < -0.99999)
                         & np.all(np.abs(mesh.triangles[:, :, 2]) < 0.02, axis=1)]
    counts = {}
    for triangle in np.round(bed, 5):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((tuple(triangle[i]), tuple(triangle[j]))))
            counts[edge] = counts.get(edge, 0) + 1
    edges = [edge for edge, count in counts.items() if count == 1]
    assert edges, 'reference must have a bed perimeter'
    distance = np.full(len(points), np.inf)
    for start, end in edges:
        a, b = np.asarray(start), np.asarray(end)
        ab = b - a
        t = np.clip(np.sum((points-a)*ab, axis=1)/(ab@ab), 0, 1)
        distance = np.minimum(distance, np.linalg.norm(points-(a+t[:, None]*ab), axis=1))
    return distance <= 0.5


@pytest.mark.parametrize('preset', ['default', 'magnets', 'wide'])
def test_rev10_reference_bed_band_coverage(preset):
    """Rev 10 measures the full band separately from distance exemptions."""
    import trimesh

    root = Path(__file__).resolve().parents[2]
    mesh = trimesh.load_mesh(root/'assets'/'openConnect-gridfinity-shelf'/'mesh'/f'{preset}.stl')
    points, _ = trimesh.sample.sample_surface(mesh, 100000, seed=1)
    excluded = reference_bed_band(mesh, points)
    print(f'BED_BAND | {preset} | {excluded.mean():.5%}')
    assert excluded.mean() <= 0.06, f'{preset}: band coverage {excluded.mean():.3%}, cap 6%'
