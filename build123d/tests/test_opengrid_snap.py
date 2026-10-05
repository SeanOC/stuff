"""Pinned QuackWorks snap: external mesh parity and published mating geometry.

References deliberately retain the SCAD's non-manifold nub-root interfaces.
Only the port must be watertight. No native OpenSCAD or upstream checkout is
needed to run these tests; assets/opengrid-snap/NOTICE pins the three renders.
"""
import hashlib
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import Location, export_stl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holders.registry import MountFixtures
from opengrid_snap import constants as c
from opengrid_snap import snap
from tests import print_audit as audit
from tests.mount_contracts import CONTRACTS, verify_opengrid_snap

ASSETS = Path(__file__).resolve().parents[2] / 'assets/opengrid-snap'
VARIANTS = [('lite', True, False), ('full', False, False), ('directional', True, True)]


@pytest.fixture(scope='module', params=VARIANTS, ids=lambda v: v[0])
def built(request, tmp_path_factory):
    name, lite, directional = request.param
    part = snap(lite=lite, directional=directional)
    path = tmp_path_factory.mktemp(name) / 'snap.stl'
    export_stl(part, str(path), tolerance=0.001, angular_tolerance=0.05)
    return name, part, trimesh.load_mesh(path), path


def reference(name):
    return trimesh.load_mesh(ASSETS / 'mesh' / f'{name}.stl')


def test_reference_hashes_and_constant_provenance():
    notice = (ASSETS / 'NOTICE').read_text()
    assert '6123129+patches-0244598ecb92' in notice
    assert 'CC BY-NC-SA 4.0' in notice
    for name, _, _ in VARIANTS:
        path = ASSETS / 'mesh' / f'{name}.stl'
        assert f'{hashlib.sha256(path.read_bytes()).hexdigest()}  mesh/{name}.stl' in notice
    dimensions = {key for key, value in vars(c).items() if key.isupper() and isinstance(value, float)}
    assert set(c.PROVENANCE) == dimensions
    for name, provenance in c.PROVENANCE.items():
        assert provenance.value == getattr(c, name)
        assert provenance.status == 'C'
        assert provenance.locator.startswith(
            'https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad#L')


def test_mesh_parity(built):
    name, part, mesh, _ = built
    ref = reference(name)
    assert np.allclose(mesh.bounds, ref.bounds, atol=0.05, rtol=0)
    assert mesh.volume == pytest.approx(ref.volume, rel=0.01)
    points, faces = trimesh.sample.sample_surface(ref, 15000, seed=1)
    normals = ref.face_normals[faces]
    classifier = audit._ClassifiedPart(part)
    interior = np.array([
        classifier.is_inside(p + 0.05 * n) and classifier.is_inside(p - 0.05 * n)
        for p, n in zip(points, normals)
    ])
    assert interior.mean() < 0.03
    # Z is height: the four nub-root contact planes are |X|/|Y|=12.4.
    # The rev5 decision's |z|=12.4 is its axis-name typo, not another exemption.
    assert np.all(np.min(np.abs(np.abs(points[interior, :2]) - 12.4), axis=1) <= 0.05)
    _, forward, _ = trimesh.proximity.closest_point(mesh, points[~interior])
    points, _ = trimesh.sample.sample_surface(mesh, 15000, seed=1)
    _, reverse, _ = trimesh.proximity.closest_point(ref, np.vstack([points, mesh.vertices]))
    print(f'{name}: bbox ref={ref.extents} port={mesh.extents}; volume '
          f'ref={ref.volume:.6f} port={mesh.volume:.6f}; distance '
          f'ref->port={forward.max():.6f} port->ref={reverse.max():.6f}; '
          f'excluded={interior.mean():.4%}')
    assert forward.max() <= 0.15
    assert reverse.max() <= 0.15


def test_single_watertight_solid(built):
    _, part, mesh, _ = built
    assert part.is_valid
    assert len(part.solids()) == 1
    assert mesh.is_watertight
    assert mesh.body_count == 1


def test_core_fit_and_only_click_nubs_outside_core(built):
    _, part, _, _ = built
    verify_opengrid_snap(part, MountFixtures(cutters=[], seat_locs=[Location()]))
    assert 'opengrid-snap' not in CONTRACTS  # registration belongs to OC4b


def test_deterministic_stl(built, tmp_path):
    name, _, _, first = built
    _, lite, directional = next(v for v in VARIANTS if v[0] == name)
    second = tmp_path / 'second.stl'
    export_stl(snap(lite=lite, directional=directional), str(second),
               tolerance=0.001, angular_tolerance=0.05)
    assert first.read_bytes() == second.read_bytes()


class _OneFace:
    """Keep the production solid classifier but audit just one BRep face."""
    def __init__(self, part, face):
        self.part, self.face = part, face

    def __getattr__(self, name):
        return getattr(self.part, name)

    def faces(self):
        return [self.face]


def _published_downward_region(face, extra):
    """Identify each permitted face by its full bounds, not an index or blanket box."""
    bb = face.bounding_box()
    lo, hi = np.array(tuple(bb.min)), np.array(tuple(bb.max))
    if abs(lo[2] - hi[2]) > 1e-5:
        return None
    z = lo[2] - extra
    # Fold the four quadrants/rotations onto the +X side.
    small = np.minimum(np.abs(lo[:2]), np.abs(hi[:2]))
    small[lo[:2] * hi[:2] <= 0] = 0
    large = np.maximum(np.abs(lo[:2]), np.abs(hi[:2]))
    order = np.argsort(large)
    near, far = small[order], large[order]
    if abs(z - 2.99) < 1e-5 and np.all(near >= 7.58162) and np.allclose(far, 12.4):
        return 'top-plate ledges'
    if abs(z - 0.19) < 1e-5 and np.allclose(near, [0, 12.4]) and np.allclose(far, [5.5, 12.8]):
        return 'bottom click nubs'
    if abs(z - 2.8) < 1e-5 and np.allclose(near, [0, 11.1]) and np.allclose(far, [6.2, 11.7]):
        return 'click-hole roofs'
    if abs(z - 2.6) < 1e-5 and np.allclose(near, [0, 11.7]) and np.allclose(far, [6, 12.4]):
        return 'wall click-hole roofs'
    return None


@pytest.mark.audit
@pytest.mark.parametrize('lite', [True, False], ids=['lite', 'full'])
def test_published_print_inventory(lite):
    name, extra = ('lite', 0) if lite else ('full', 3.4)
    part = audit._ClassifiedPart(snap(lite=lite))
    walls, overhangs = Counter(), Counter()
    worst_bridge = 0
    for face in part.faces():
        one = _OneFace(part, face)
        wall = audit._min_wall(one, (0, 0, 1), [])
        assert wall >= 0.40, (name, face.bounding_box(), wall)
        if wall < 0.9:
            bucket = min([0.41, 0.60, 0.70, 0.80], key=lambda v: abs(v - wall))
            assert abs(bucket - wall) <= 0.01
            walls[bucket] += 1
        angle = audit._max_overhang(one, (0, 0, 1), [], 0)
        bridge = audit._longest_bridge(one, (0, 0, 1), [], 0)
        worst_bridge = max(worst_bridge, bridge)
        if angle > 45.01 or bridge > 10:
            region = _published_downward_region(face, extra)
            assert region, (name, face.bounding_box(), angle, bridge)
            assert angle == pytest.approx(90)
            overhangs[region] += 1
    assert walls == {0.41: 8, 0.60: 4, 0.70: 4 if lite else 8, 0.80: 4}
    assert overhangs == {'top-plate ledges': 8, 'bottom click nubs': 4,
                         'click-hole roofs': 4, 'wall click-hole roofs': 4}
    assert worst_bridge <= 0.5 + 1e-6
    assert not audit._downward_curved_faces(part, (0, 0, 1), [], 0)
    print(f'{name}: min_wall/count={dict(walls)}; overhang/count={dict(overhangs)}; '
          f'worst overhang=90; bridge={worst_bridge}; downward fillets=0')


@pytest.mark.parametrize('name,extra', [('lite', 0), ('full', 3.4)])
def test_reference_wall_thicknesses(name, extra):
    """Independent ray evidence for the inventory's source thickness buckets.

    Probe all four rotated features, including the full snap's lower ligaments.
    Mesh triangles are not BRep faces: counts are locked by the inventory test.
    """
    ref = reference(name)
    probes = [([9.5, 9.5, 2.99 + extra], [0, 0, 1], .41),
              ([11.4, 0, 2.8 + extra], [0, 0, 1], .60),
              ([11.7, 0, 2.7 + extra], [1, 0, 0], .70),
              ([12, 0, 2.6 + extra], [0, 0, 1], .80)]
    if extra:
        probes.append(([11.7, 0, 1], [1, 0, 0], .70))
    for origin, direction, expected in probes:
        for angle in np.arange(4) * np.pi / 2:
            rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                                 [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
            d = rotation @ direction
            p = rotation @ origin + 1e-4 * d
            hits, _, _ = ref.ray.intersects_location([p], [d])
            thickness = np.linalg.norm(hits - p, axis=1).min() + 1e-4
            assert thickness == pytest.approx(expected, abs=.01)
