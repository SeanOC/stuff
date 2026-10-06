"""Shared reference parity arithmetic; callers own sampling and acceptance caps."""
import hashlib
from pathlib import Path

import numpy as np
import pytest
import trimesh


def load_reference(path, sha256=None):
    """Load an openGrid snap reference, optionally checking its pinned digest."""
    path = Path(path)
    if sha256 is not None:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha256, path
    return trimesh.load_mesh(path)


def mesh_from_part(part, path, *, tolerance, angular_tolerance):
    """Tessellate the openConnect port with explicitly chosen chord tolerances."""
    from build123d import export_stl

    export_stl(part, str(path), tolerance=tolerance, angular_tolerance=angular_tolerance)
    return load_reference(path)


def _bounds(shape):
    """Read mesh or exact-solid bounds for the shelf pre-treatment comparison."""
    if isinstance(shape, trimesh.Trimesh):
        return shape.bounds
    box = shape.bounding_box()
    return np.array([tuple(box.min), tuple(box.max)])


def bbox_parity(port, ref, *, tol, mode, rtol, pre_treatment=None,
                expected_reduction=None, reduction_tol=None):
    """Compare snap bounds or shelf pre-treatment extents and analytic reduction.

    Direction-pinned ports require ordered bounds (including position). Sorted
    extents are sound only for frame-not-pinned comparisons such as the shelf.
    Treatment reduction is an ordered XYZ triple, measured on the exact solid.
    """
    port_bounds = _bounds(port)
    if pre_treatment is not None:
        if expected_reduction is None or reduction_tol is None:
            raise ValueError('pre_treatment requires expected_reduction and reduction_tol')
        before = _bounds(pre_treatment)
        if not tuple(port_bounds[1] - port_bounds[0]) == pytest.approx(
                tuple(before[1] - before[0] - expected_reduction), abs=reduction_tol):
            return False
        port_bounds = before
    elif expected_reduction is not None or reduction_tol is not None:
        raise ValueError('reduction requires pre_treatment')
    ref_bounds = _bounds(ref)
    if mode == 'ordered':
        return bool(np.allclose(port_bounds, ref_bounds, atol=tol, rtol=rtol))
    if mode == 'sorted':
        return bool(np.allclose(sorted(port_bounds[1] - port_bounds[0]),
                                sorted(ref_bounds[1] - ref_bounds[0]), atol=tol, rtol=rtol))
    raise ValueError(f'unknown bbox mode: {mode}')


def volume_parity(port, ref, *, rel=None, abs=None):
    """Preserve snap/shelf relative and openConnect absolute pytest tolerances."""
    if (rel is None) == (abs is None):
        raise ValueError('supply exactly one of rel or abs')
    return port.volume == pytest.approx(ref.volume, rel=rel, abs=abs)


def sample_surface(mesh, *, n, seed, sampler):
    """Sample the shelf uniformly or openConnect evenly, with no implicit budget."""
    if sampler == 'even':
        return trimesh.sample.sample_surface_even(mesh, n, seed=seed)
    if sampler == 'uniform':
        return trimesh.sample.sample_surface(mesh, n, seed=seed)
    raise ValueError(f'unknown surface sampler: {sampler}')


def point_distances(points, target, *, signed):
    """Measure snap external samples, or signed openConnect seated-head gaps."""
    if signed:
        return trimesh.proximity.signed_distance(target, points)
    return trimesh.proximity.closest_point(target, points)[1]


def surface_distance(port, ref, *, n, seed, sampler, vertices, signed):
    """Return sample points and directed distances, first needed by openConnect.

    Vertex inclusion and signed gaps are explicit: the shelf samples only the
    surface; openConnect and snap's reverse comparison also include vertices.
    """
    points, _ = sample_surface(port, n=n, seed=seed, sampler=sampler)
    if vertices:
        points = np.vstack([points, port.vertices])
    return points, point_distances(points, ref, signed=signed)


def external_boundary_mask(ref, planes, *, normals, classifier, offset, tol):
    """Return snap's interior mask/fraction and pin it to named contact planes.

    ``ref`` contains reference samples. Each plane is (normal, offset) with
    equation dot(point, normal) = offset. Both axis and diagonal planes must
    be supplied by the port; classification uses the original exact solid.
    """
    interior = np.array([
        classifier.is_inside(p + offset*n) and classifier.is_inside(p - offset*n)
        for p, n in zip(ref, normals)
    ])
    distances = [np.abs(ref[interior] @ np.asarray(normal) - distance)
                 / np.linalg.norm(normal) for normal, distance in planes]
    assert np.all(np.min(distances, axis=0) <= tol)
    return interior, interior.mean()


def boundary_edges(mesh, *, normal_z, plane_tol, decimals):
    """Extract the shelf's welded reference bed perimeter, excluding side faces."""
    bed = mesh.triangles[(mesh.face_normals[:, 2] < normal_z)
                         & np.all(np.abs(mesh.triangles[:, :, 2]) < plane_tol, axis=1)]
    counts = {}
    for triangle in np.round(bed, decimals):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((tuple(triangle[i]), tuple(triangle[j]))))
            counts[edge] = counts.get(edge, 0) + 1
    edges = [edge for edge, count in counts.items() if count == 1]
    assert edges, 'reference must have a bed perimeter'
    return edges


def band_mask(ref, boundary_edges, radius):
    """Select shelf samples within radius of the reference's boundary segments."""
    distance = np.full(len(ref), np.inf)
    for start, end in boundary_edges:
        a, b = np.asarray(start), np.asarray(end)
        ab = b - a
        t = np.clip(np.sum((ref-a)*ab, axis=1)/(ab@ab), 0, 1)
        distance = np.minimum(distance, np.linalg.norm(ref-(a+t[:, None]*ab), axis=1))
    return distance <= radius


def over_cap_exclusion(distances, mask, cap):
    """Report shelf E3 band coverage separately from actual over-cap exclusions."""
    return mask.mean(), (mask & (distances > cap)).mean()


def rotate_to_print_frame(part, spec, values):
    """Apply the shelf's declared print transform; author alignment stays local."""
    from holders.registry import in_print_frame

    return in_print_frame(spec, values, part)
