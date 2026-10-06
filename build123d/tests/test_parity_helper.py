"""Independent analytic cases for the reference parity arithmetic."""
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import trimesh
from build123d import Box, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.parity import (band_mask, bbox_parity, boundary_edges, external_boundary_mask,
                          load_reference, over_cap_exclusion, rotate_to_print_frame,
                          sample_surface, surface_distance, volume_parity)


def test_ordered_bounds_detect_translation_and_axis_swap():
    cube = trimesh.creation.box(extents=(1, 2, 3))
    shifted = cube.copy().apply_translation((0, 0, .2))
    swapped = trimesh.creation.box(extents=(2, 1, 3))
    for wrong in (shifted, swapped):
        assert not bbox_parity(wrong, cube, tol=.05, mode='ordered', rtol=0)
        assert bbox_parity(wrong, cube, tol=.05, mode='sorted', rtol=0)
    with pytest.raises(ValueError, match='mode'):
        bbox_parity(cube, cube, tol=0, mode='invalid', rtol=0)


def test_chamfered_cube_bbox_volume_and_band():
    # Clip the top four edges of a unit cube by 0.25 at 45 degrees.
    cube = trimesh.creation.box()
    cube.apply_translation((.5, .5, .5))
    vertices = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, .75)]
    vertices += [(x, y, 1) for x in (.25, .75) for y in (.25, .75)]
    chamfered = trimesh.convex.convex_hull(vertices)
    assert bbox_parity(chamfered, cube, tol=1e-12, mode='ordered', rtol=0)
    # The upper quarter is a square frustum: h/3*(1 + .25 + .5).
    assert chamfered.volume == pytest.approx(.75 + .25/3*1.75)
    assert volume_parity(chamfered, cube, abs=.105)
    assert not volume_parity(chamfered, cube, rel=.1)
    edges = boundary_edges(cube, normal_z=-.99999, plane_tol=.02, decimals=5)
    assert len(edges) == 4
    points = np.array([[.5, 0, 0], [.5, .1, 0], [.5, .5, 0], [.5, 0, .3]])
    mask = band_mask(points, edges, radius=.1)
    np.testing.assert_array_equal(mask, [True, True, False, False])
    # A band point exactly at the cap is not excluded; a remote over-cap
    # point stays subject to the distance check.
    assert over_cap_exclusion(np.array([.2, .15, .3, 0]), mask, .15) == (.5, .25)


def test_analytic_reduction_uses_pre_treatment_solid():
    before, after = Box(1, 2, 3), Box(1, 1.8, 3)
    ref = trimesh.creation.box(extents=(1, 2, 3))
    kwargs = dict(tol=1e-8, mode='sorted', rtol=0, pre_treatment=before,
                  reduction_tol=1e-8)
    assert bbox_parity(after, ref, expected_reduction=(0, .2, 0), **kwargs)
    assert not bbox_parity(after, ref, expected_reduction=(.2, 0, 0), **kwargs)
    with pytest.raises(ValueError, match='requires'):
        bbox_parity(after, ref, tol=.05, mode='sorted', rtol=0, pre_treatment=before)


@pytest.mark.parametrize('sampler', ['even', 'uniform'])
def test_translated_cube_distance_and_explicit_sampling(sampler):
    cube = trimesh.creation.box()
    shifted = cube.copy().apply_translation((0, 0, .2))
    points, distances = surface_distance(shifted, cube, n=100, seed=2,
                                         sampler=sampler, vertices=True, signed=False)
    assert distances.max() == pytest.approx(.2)
    original = getattr(trimesh.sample, 'sample_surface_even' if sampler == 'even'
                       else 'sample_surface')
    expected, _ = original(shifted, 100, seed=2)
    np.testing.assert_array_equal(points, np.vstack([expected, shifted.vertices]))
    _, signed = surface_distance(shifted, cube, n=100, seed=2, sampler=sampler,
                                 vertices=True, signed=True)
    assert signed.min() == pytest.approx(-.2)
    assert signed.max() > 0


def test_sampling_and_volume_require_explicit_choices():
    cube = trimesh.creation.box()
    with pytest.raises(TypeError):
        surface_distance(cube, cube)
    with pytest.raises(ValueError, match='sampler'):
        sample_surface(cube, n=10, seed=1, sampler='invalid')
    for kwargs in ({}, {'rel': .01, 'abs': .05}):
        with pytest.raises(ValueError, match='exactly one'):
            volume_parity(cube, cube, **kwargs)


def test_external_exclusion_requires_axis_or_diagonal_contact_plane():
    cube = trimesh.creation.box(extents=(2, 2, 2))
    classifier = SimpleNamespace(is_inside=lambda p: cube.contains([p])[0])
    points = np.array([[0, 0, 0], [.5, .5, 0], [1, 0, 0]])
    normals = np.tile([1, 0, 0], (3, 1))
    kwargs = dict(normals=normals, classifier=classifier, offset=.05, tol=1e-8)
    mask, fraction = external_boundary_mask(points, [((1, 0, 0), 0), ((1, 1, 0), 1)], **kwargs)
    np.testing.assert_array_equal(mask, [True, True, False])
    assert fraction == pytest.approx(2/3)
    with pytest.raises(AssertionError):
        external_boundary_mask(points, [((1, 0, 0), 0)], **kwargs)


def test_reference_hash_and_print_frame(tmp_path):
    mesh = trimesh.creation.box()
    path = tmp_path/'reference.stl'
    mesh.export(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert load_reference(path, sha256=digest).volume == mesh.volume
    with pytest.raises(AssertionError):
        load_reference(path, sha256='bad hash')
    part = Box(1, 2, 3)
    spec = SimpleNamespace(resolve_values=lambda values: {'angle': values['angle']},
                           print_frame=lambda values: Pos(0, 0, 5)*Rot(0, 0, values['angle']))
    rotated = rotate_to_print_frame(part, spec, {'angle': 90})
    assert tuple(rotated.bounding_box().size) == pytest.approx((2, 1, 3))
    assert rotated.bounding_box().min.Z == pytest.approx(3.5)
