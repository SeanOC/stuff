"""Pinned QuackWorks snap: external mesh parity and published mating geometry.

References deliberately retain the SCAD's non-manifold nub-root interfaces.
Only the port must be watertight. Ordinary tests need neither native OpenSCAD
nor an upstream checkout; assets/opengrid-snap/NOTICE pins the four renders.
The opt-in upstream provenance test fetches the pinned source into memory.
"""
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pytest
import trimesh
from build123d import Align, Box, Location, Pos, export_stl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holders.registry import MountFixtures
from opengrid_snap import constants as c
from opengrid_snap import snap
from tests import print_audit as audit
from tests.mount_contracts import CONTRACTS, verify_opengrid_snap
from tests.opengrid_snap_inventory import DIRECTIONAL_FACES

ASSETS = Path(__file__).resolve().parents[2] / 'assets/opengrid-snap'
VARIANTS = [('lite', True, False), ('full', False, False), ('directional', True, True),
            ('full-directional', False, True)]


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


@pytest.mark.upstream
def test_provenance_values_match_pinned_upstream():
    # Patch 0001 is line-neutral and preserves these dimensions. Fetch the
    # pinned original in memory; never commit QuackWorks source as a fixture.
    source = 'https://raw.githubusercontent.com/AndyLevesque/QuackWorks/6123129/openGrid/opengrid-snap.scad'
    with urlopen(source, timeout=30) as response:
        lines = response.read().decode('utf-8').splitlines()
    directional_args = {
        'HEIGHT': 'nub_h', 'WIDTH': 'nub_w', 'DEPTH': 'nub_d',
        'TOP_WEDGE': 'top_wedge_h', 'BOTTOM_WEDGE': 'bot_wedge_h',
        'ROUND_X': 'r_x', 'ROUND_SCALE': 'r_s', 'ROUND_RADIUS': 'r_r',
        'BOTTOM_SHIFT': 'b_y',
    }
    for name, provenance in c.PROVENANCE.items():
        match = re.fullmatch(
            r'https://github\.com/AndyLevesque/QuackWorks/blob/6123129/'
            r'openGrid/opengrid-snap\.scad#L(\d+)', provenance.locator)
        assert match, (name, provenance.locator)
        line = lines[int(match[1]) - 1]
        assert f'{provenance.value:g}' in line, (name, provenance.locator, line)
        prefix, _, suffix = name.partition('_')
        if prefix in {'FRONT', 'REAR'} and suffix in directional_args:
            # Adjacent top/bottom wedges both use 0.6: the value alone cannot
            # catch a one-line error, so also bind the defining SCAD argument.
            argument = directional_args[suffix]
            value = re.fullmatch(rf'\s*{argument}\s*=\s*([-\d.]+),?\s*', line)
            assert value, (name, provenance.locator, line)
            assert float(value[1]) == provenance.value


# Full-directional parity exceeds the fast-job 60 s threshold (pst-n60q0).
@pytest.mark.parametrize('built', [
    pytest.param(variant, id=variant[0],
                 marks=pytest.mark.audit if variant[0] == 'full-directional' else ())
    for variant in VARIANTS
], indirect=True)
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
    assert interior.mean() < 0.12
    # Nub roots and top-nub/core interfaces, pinned source :50 and :52-56.
    xy = np.abs(points[interior, :2])
    axis_distance = np.min(np.abs(xy - 12.4), axis=1)
    diagonal_distance = np.abs(xy.sum(axis=1) - 19.98163) / np.sqrt(2)
    assert np.all(np.minimum(axis_distance, diagonal_distance) <= 0.05)
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


def test_fit_at_transformed_seat(built):
    _, part, _, _ = built
    loc = Location((31, -20, 8), (90, 0, 15))
    verify_opengrid_snap(loc * part, MountFixtures(cutters=[], seat_locs=[loc]))


def test_fit_rejects_oversize_core_and_non_nub_protrusion():
    part = snap()
    fx = MountFixtures(cutters=[], seat_locs=[Location()])
    oversize = part + Pos(12.4, 0, 2.7) * Box(.4, 8, .2)
    with pytest.raises(AssertionError, match='core span'):
        verify_opengrid_snap(oversize, fx)
    stray = part + Pos(12.2, 8, 1) * Box(
        .6, 1, 1, align=(Align.MIN, Align.CENTER, Align.MIN))
    with pytest.raises(AssertionError, match='non-nub material'):
        verify_opengrid_snap(stray, fx)


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


def _check_directional_inventory(part, lite, name):
    """Exact asymmetric face sets, including thin faces that are not ceilings."""
    expected = DIRECTIONAL_FACES[lite]
    seen = Counter()
    for face in part.faces():
        one = _OneFace(part, face)
        wall = audit._min_wall(one, (0, 0, 1), [])
        angle = audit._max_overhang(one, (0, 0, 1), [], 0)
        bridge = audit._longest_bridge(one, (0, 0, 1), [], 0)
        bb = face.bounding_box()
        bounds = (*bb.min, *bb.max)
        matches = [i for i, (_, box, *_) in enumerate(expected)
                   if np.allclose(bounds, box, atol=1e-5, rtol=0)]
        if matches:
            assert len(matches) == 1
            i = matches[0]
            region, _, want_wall, want_angle, want_bridge = expected[i]
            assert wall == pytest.approx(want_wall, abs=.01), (name, region, bounds)
            assert angle == pytest.approx(want_angle, abs=.01), (name, region, bounds)
            assert bridge == pytest.approx(want_bridge, abs=1e-6), (name, region, bounds)
            seen[i] += 1
        else:
            assert wall >= .9 and angle <= 45.01 and bridge == 0, (name, bounds, wall, angle, bridge)
    assert seen == Counter(range(len(expected)))  # no missing or duplicate face
    assert not audit._downward_curved_faces(part, (0, 0, 1), [], 0)
    walls = Counter(row[2] for row in expected if row[2] < .9)
    ceilings = Counter(row[0] for row in expected if row[3] > 45)
    print(f'{name}: min_wall/count={dict(walls)}; overhang/count={dict(ceilings)}; '
          f'worst overhang=90; bridge=1.5; downward fillets=0')


@pytest.mark.audit
@pytest.mark.parametrize('name,lite,directional', VARIANTS, ids=[v[0] for v in VARIANTS])
def test_published_print_inventory(name, lite, directional):
    extra = 0 if lite else 3.4
    part = audit._ClassifiedPart(snap(lite=lite, directional=directional))
    if directional:
        _check_directional_inventory(part, lite, name)
        return
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


@pytest.mark.parametrize('name,lite,directional', VARIANTS, ids=[v[0] for v in VARIANTS])
def test_reference_wall_thicknesses(name, lite, directional):
    """Independent ray evidence for the inventory's source thickness buckets.

    Probe all four rotated features, including the full snap's lower ligaments.
    Mesh triangles are not BRep faces: counts are locked by the inventory test.
    """
    extra = 0 if lite else 3.4
    ref = reference(name)
    probes = [([9.5, 9.5, 2.99 + extra], [0, 0, 1], .41),
              ([11.4, 0, 2.8 + extra], [0, 0, 1], .60),
              ([11.7, 0, 2.7 + extra], [1, 0, 0], .70),
              ([12, 0, 2.6 + extra], [0, 0, 1], .80)]
    if extra:
        probes.append(([11.7, 0, 1], [1, 0, 0], .70))
    for origin, direction, expected in probes:
        for angle in np.arange(4) * np.pi / 2:
            if directional and origin[0] != 9.5 and abs(np.cos(angle)) > .5:
                continue  # directional +/-X features have their own probes below
            rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                                 [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
            d = rotation @ direction
            p = rotation @ origin + 1e-4 * d
            hits, _, _ = ref.ray.intersects_location([p], [d])
            thickness = np.linalg.norm(hits - p, axis=1).min() + 1e-4
            assert thickness == pytest.approx(expected, abs=.01)


@pytest.mark.parametrize('lite', [True, False], ids=['directional', 'full-directional'])
def test_directional_reference_features(lite):
    ref = reference('directional' if lite else 'full-directional')
    extra = 0 if lite else 3.4
    # First-hit rays through the independent SCAD mesh. The lower rear
    # ligament is physically .7 mm; the production bisection proxy reports
    # .88666 on lite because it can step across the neighbouring void.
    probes = [([-11.56, -2.36, .18], [-3, 0, -1], .56921),
              ([-11.52, 0, 2.799 + extra], [0, 0, 1], .601),
              ([-11.7, 0, 1.08], [-1, 0, 0], .7),
              ([-11.7, 0, 2.6597 + extra], [-1, 0, 0], .7),
              ([-12, 0, 2.6 + extra], [0, 0, 1], .8)]
    for origin, direction, expected in probes:
        d = np.array(direction, dtype=float)
        d /= np.linalg.norm(d)
        p = np.array(origin) + 1e-4 * d
        hits, _, _ = ref.ray.intersects_location([p], [d])
        assert len(hits)
        thickness = np.linalg.norm(hits - p, axis=1).min() + 1e-4
        assert thickness == pytest.approx(expected, abs=.01)
    # Every published ceiling must have a downward reference surface at its
    # recorded plane and inside its complete bounds (including the indicator
    # at fixed Z=.4, and the full-only front nub at Z=3.4).
    for region, bounds, _, angle, _ in DIRECTIONAL_FACES[lite]:
        if angle <= 45:
            continue
        lo, hi = np.array(bounds[:3]), np.array(bounds[3:])
        assert lo[2] == hi[2]
        vertices = ref.triangles
        within = np.all((vertices >= lo - 1e-4) & (vertices <= hi + 1e-4), axis=(1, 2))
        downward = ref.face_normals[:, 2] < -.99999
        selected = vertices[within & downward]
        assert len(selected), (region, bounds)
        assert np.allclose(selected.min(axis=(0, 1)), lo, atol=.01, rtol=0), region
        assert np.allclose(selected.max(axis=(0, 1)), hi, atol=.01, rtol=0), region
