"""Cartridge port parity, mount contracts, and self-policing audit exceptions."""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from functools import lru_cache

import pytest
from build123d import Align, Box, Pos
from holders import cartridge_holder as m
from tests import print_audit as pa
from tests.mount_contracts import verify_openconnect_slot


@lru_cache(maxsize=6)
def _built(items):
    return m.build(dict(items))


def built(values):
    return _built(tuple(sorted(values.items())))


def assert_finished_edges(part, values):
    """Measure convex exposed edges; leave concave fit surfaces and mounts alone.

    top_round=0 is the source's explicit sharp-rim option, retained as such.
    Library geometry below the body and inside receiver cutters is unchanged.
    """
    p = m.dimensions(values)
    fx = m.mount_fixtures(m.MOUNT, values)
    boxes = pa._cutter_boxes(fx.cutters, margin=1e-5) if fx else []
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    worst = 0.
    classified = pa._ClassifiedPart(part)
    for edge, faces in adjacency.items():
        if len(faces) == 1:  # periodic seam, not a physical exposed edge
            continue
        assert len(faces) == 2
        point = edge.center()
        if point.Y <= p['lift'] + 1e-5 and p['mount_type'] == 'opengrid':
            continue
        if pa._in_any_box(*point, boxes):
            continue
        if not p['top_round'] and abs(point.Y-p['lift']-p['body_h']) < 1e-5:
            continue
        n0, n1 = [f.normal_at(point) for f in faces]
        angle = math.degrees(math.acos(max(-1., min(1., n0.dot(n1)))))
        if angle > 1e-4 and classified.is_inside(point + (n0-n1)*.005):
            continue  # concave internal fit edge
        worst = max(worst, angle)
        assert angle < 89.999, (tuple(point), angle)
    return worst


def checked(values):
    part = built(values)
    assert part.is_valid and len(part.solids()) == 1
    fx = m.mount_fixtures(m.MOUNT, values)
    report = pa.audit(part, m.SPEC.print_orientation,
                      cutters=fx.cutters if fx else [],
                      exclusions=m.audit_exclusions(values))
    angle = assert_finished_edges(part, values)
    assert report.ok, report.format()
    return report, angle


@pytest.mark.audit
@pytest.mark.parametrize('preset', [
    pytest.param(p, marks=pytest.mark.audit_full) if p.id == 'full_holder' else p
    for p in m.SPEC.presets], ids=lambda p: p.id)
def test_presets(preset):
    report, angle = checked(preset.values)
    print(preset.id, report.min_wall_mm, report.max_overhang_deg, angle, report.ok)


ENDPOINTS = [(f'{p.name}={v}', {p.name:v}) for p in m.SPEC.params
             if p.kind in ('number', 'integer') for v in (p.min, p.max)]
CORNERS = [('full-snaps', {'snap_lite':False}),
           ('wide-slots', {'grid_cols':9, 'slot_w':56}),
           ('shallow-body-deep-pockets', {'body_h':38,'slot_depth':40,'floor_z':2}),
           ('openconnect-low-floor', {'mount_type':'openconnect', 'floor_z':2})]


@pytest.mark.audit
@pytest.mark.audit_full
@pytest.mark.parametrize('name,values', ENDPOINTS+CORNERS, ids=[c[0] for c in ENDPOINTS+CORNERS])
def test_endpoints(name, values):
    report, angle = checked(values)
    print(f'| {name} | {report.min_wall_mm:.3f} | {report.max_overhang_deg:.1f} | {angle:.1f} | {report.ok} |')


def test_openconnect_floor_and_contract():
    v = {'mount_type':'openconnect'}
    assert m.dimensions(v)['floor_z'] == pytest.approx(5.2)
    assert m.dimensions({'mount_type':'blank'})['floor_z'] == 5
    verify_openconnect_slot(built(v), m.mount_fixtures(m.MOUNT, v))


@pytest.mark.parametrize('cols,rows', [(2,4), (9,8)])
def test_receiver_grid(cols, rows):
    positions = m.placements({'grid_cols':cols, 'grid_rows':rows})
    assert len(positions) == cols*rows
    assert {(p.x,p.z) for p in positions} == {
        ((i+.5)*28-cols*14, (j+.5)*28) for i in range(cols) for j in range(rows)}
    assert sum(p.nubs != 'none' for p in positions) == 4
    assert all(p.slide == 'up' and not p.entryramp_flip for p in positions)
    fx = m.mount_fixtures(m.MOUNT, {'mount_type':'openconnect',
                                   'grid_cols':cols, 'grid_rows':rows})
    assert len(fx.cutters) == len(fx.seat_locs) == cols*rows


@pytest.mark.slow
def test_openconnect_9x8_boolean_contract():
    v = {'mount_type':'openconnect', 'grid_cols':9, 'grid_rows':8}
    verify_openconnect_slot(m.build(v), m.mount_fixtures(m.MOUNT, v))


def test_public_contract():
    assert m.SPEC.slug == 'littletikes-dream-machine-cartridge-holder'
    assert m.SPEC.category_id == 'toys'
    assert [p.id for p in m.SPEC.presets] == ['default','full_holder','blank_back','openconnect']
    assert 'snap_every_cell' not in m.SPEC.resolve_values()
    assert next(p for p in m.SPEC.params if p.name == 'mount_type').filename
    assert m.SPEC.print_orientation == (0,1,0)


@pytest.mark.audit
def test_exceptions_are_narrow_and_dense_bridge_is_short():
    v = {}
    part = built(v)
    regions = m.audit_exclusions(v, underside=False)
    raw = pa.audit(part, m.SPEC.print_orientation, exclusions=regions)
    assert raw.max_overhang_deg == 90  # exactly the underside, still unwaived
    assert not raw.downward_fillets
    assert 0 < raw.longest_bridge_mm <= 10
    clean = pa.audit(part, m.SPEC.print_orientation, exclusions=m.audit_exclusions(v))
    assert clean.ok, clean.format()
    blank = built({'mount_type':'blank'})
    raw_dome = pa.audit(blank, m.SPEC.print_orientation)
    assert raw_dome.max_overhang_deg > 45 and len(raw_dome.downward_fillets) == 1
    # A new long overhang outside the dome must not inherit its waiver.
    damaged = blank + Pos(28,20,60)*Box(20,2,20, align=(Align.MIN,Align.MIN,Align.MIN))
    assert not pa.audit(damaged, m.SPEC.print_orientation,
                        exclusions=m.audit_exclusions({'mount_type':'blank'})).ok


def test_blank_reference_envelope_and_volume():
    # [V] OpenSCAD CGAL binary STL at d12a407, default blank mount.
    part = built({'mount_type':'blank'})
    assert sorted(tuple(part.bounding_box().size)) == pytest.approx([41,56,112], abs=.1)
    assert part.volume == pytest.approx(140088.659, rel=.01)


def test_rectangular_exclusion_fast_path_is_equivalent(monkeypatch):
    # Full containment skips work; a partially overlapping envelope must not.
    part = built({'mount_type':'blank'})
    regions = m.audit_exclusions({'mount_type':'blank'}) + [(-28,-.001,0,28,.401,112)]
    fast = pa.audit(part, m.SPEC.print_orientation, exclusions=regions)
    monkeypatch.setattr(pa, '_face_in_box', lambda face, boxes: False)
    assert pa.audit(part, m.SPEC.print_orientation, exclusions=regions) == fast


@pytest.mark.parametrize('lite', [True, False], ids=['lite','full'])
def test_consumes_unmodified_snap_at_every_cell(lite):
    from build123d import Rot
    from opengrid_snap import snap
    values = {'snap_lite':lite}
    p = m.dimensions(values)
    part = built(values)
    frame = Pos(p['width']/2,0,0)*Rot(0,0,180)*Rot(90,0,0)
    clip = Box(28,28,p['lift']-.001,align=(Align.CENTER,Align.CENTER,Align.MIN))
    expected = snap(lite=lite,directional=False) & clip
    for i in range(p['grid_cols']):
        for j in range(p['grid_rows']):
            loc = frame*Pos((i+.5)*28,(j+.5)*28,0)
            actual = (loc.inverse()*part) & clip
            assert sum(s.volume for s in (expected-actual).solids()) < 1e-5
            assert sum(s.volume for s in (actual-expected).solids()) < 1e-5


class _BodyFaces:
    """Keep the full support solid but measure only the tray's BRep faces."""
    def __init__(self, part, lift):
        self.part, self.lift = part, lift

    def __getattr__(self, name):
        return getattr(self.part, name)

    def faces(self):
        return [f for f in self.part.faces() if f.bounding_box().min.Y >= self.lift-1e-6]


@pytest.mark.audit
def test_bridge_exemption_rejects_missing_supports():
    from build123d import Rot
    from opengrid_snap import snap
    p = m.dimensions()
    dense = built({})
    proxy = _BodyFaces(dense,p['lift'])
    # No snap envelope masking: rays must see the REAL gaps between snaps.
    bridge = pa._longest_bridge(pa._ClassifiedPart(proxy),(0,1,0),[],0)
    assert 0 < bridge <= 10, bridge
    connector = snap(lite=True,directional=False)
    sparse = Pos(0,0,p['lift'])*m._body(p)
    sparse = sparse.fuse(*[Pos((i+.5)*28,(j+.5)*28,0)*connector
                          for i in range(2) for j in (0,3)])
    sparse = Pos(p['width']/2,0,0)*Rot(0,0,180)*Rot(90,0,0)*sparse
    failed_bridge = pa._longest_bridge(pa._ClassifiedPart(_BodyFaces(sparse,p['lift'])),
                                       (0,1,0),[],0)
    assert failed_bridge > 10, failed_bridge
    print('actual dense bridge',bridge,'missing-row regression',failed_bridge)


@pytest.mark.parametrize('preset', m.SPEC.presets, ids=lambda p:p.id)
def test_source_pocket_fit(preset):
    """Independent fixed-default fit probes, 0.11 mm either side of each nominal cartridge wall.

    Probe below the lead-ins: the body edge relief and mouth chamfers do not
    change the source 52x14 cartridge or 43.5 mm domed figure fit profiles.
    """
    part = built(preset.values)
    classified = pa._ClassifiedPart(part)
    p = m.dimensions(preset.values)
    full = preset.id == 'full_holder'
    cols, rows = (4,10) if full else (1,4)
    source_x = 28
    source_y = 7 if full else 17
    for i in range(cols):
        x = p['width']/2-source_x-i*56
        for j in range(rows):
            z = source_y+j*22
            y = p['lift']+20
            assert not classified.is_inside((x,y,z))
            assert not classified.is_inside((x+25.89,y,z))
            assert classified.is_inside((x+26.11,y,z))
            assert not classified.is_inside((x,y,z+6.89))
            assert classified.is_inside((x,y,z+7.11))
            distances = []
            for sign in (-1,1):
                lo, hi = 25.8, 26.2
                for _ in range(18):
                    mid = (lo+hi)/2
                    if classified.is_inside((x+sign*mid,y,z)):
                        hi = mid
                    else:
                        lo = mid
                distances.append((lo+hi)/2)
            assert abs(sum(distances)-52) <= .10001
            floor = p['lift']+(5.1 if preset.id == 'openconnect' else 4.9)
            assert classified.is_inside((x,floor-.05,z))
            assert not classified.is_inside((x,floor+.05,z))
    for i in range(5 if full else 1):
        x = (2-i)*49.25 if full else 0
        y = p['lift']+p['floor_z']+9
        z = p['height']-1
        assert not classified.is_inside((x+21.70,y,z))
        assert classified.is_inside((x+21.80,y,z))
        assert not classified.is_inside((x,y+21.70,z))
        assert classified.is_inside((x,y+21.80,z))
    assert len(part.solids()) == 1


def test_default_scad_volume_and_envelope():
    part = built({})
    assert sorted(tuple(part.bounding_box().size)) == pytest.approx([44.38,56,112],abs=.1)
    assert part.volume == pytest.approx(155058.179208,rel=.01)


def test_full_holder_scad_volume_and_envelope():
    part = built({'grid_cols':9,'grid_rows':8})
    assert sorted(tuple(part.bounding_box().size)) == pytest.approx([44.38,224,252],abs=.1)
    assert part.volume == pytest.approx(1338919.775606,rel=.01)


def test_receiver_centres_and_corner_locks_at_every_grid_size():
    for cols in range(2,10):
        for rows in range(3,10):
            positions = m.placements({'grid_cols':cols,'grid_rows':rows})
            assert {(p.x,p.z) for p in positions} == {
                ((i+.5)*28-cols*14,(j+.5)*28)
                for i in range(cols) for j in range(rows)}
            assert {(p.x,p.z) for p in positions if p.nubs != 'none'} == {
                (x,z) for x in (-(cols-1)*14,(cols-1)*14)
                for z in (14,rows*28-14)}


@pytest.mark.audit
@pytest.mark.audit_full
def test_spatial_classifier_matches_native_full_holder():
    import random
    part = built({'grid_cols':9,'grid_rows':8})
    native = pa._ClassifiedPart(part,partition=False)
    spatial = pa._ClassifiedPart(part)
    assert spatial._pieces is not None
    rng = random.Random(7)
    points = [(rng.uniform(-130,130),rng.uniform(-1,46),rng.uniform(-1,225))
              for _ in range(120)]
    faces = list(part.faces())
    for face in faces[::max(1,len(faces)//60)]:
        point = pa._face_point(face)
        normal = face.normal_at(point)
        points.extend(point+normal*d for d in (-.02,0,.02))
    for axis,middle in spatial._pieces[1]:
        for offset in (-2e-6,0,2e-6):
            point = [0,20,112]
            point[axis] = middle+offset
            points.append(point)
    for point in points:
        assert spatial.is_inside(point) == native.is_inside(point), tuple(point)


@pytest.mark.audit
def test_spatial_and_native_audit_reports_match(monkeypatch):
    part = built({})
    regions = m.audit_exclusions()
    spatial = pa.audit(part,m.SPEC.print_orientation,exclusions=regions)
    monkeypatch.setattr(pa,'_PARTITION_TRIGGER_FACES',float('inf'))
    assert pa.audit(part,m.SPEC.print_orientation,exclusions=regions) == spatial
