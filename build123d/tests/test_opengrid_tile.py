"""Tile geometry contracts and production audit at presets/domain corners."""
import math

import pytest
from build123d import Box, Pos
from opengrid.base import Base
from opengrid_snap import snap
from shapely.geometry import Point

from holders.opengrid_tile import SPEC
from opengrid_tile.tile import FULL, LITE, cells, outline
from tests.audit_record import record
from tests.opengrid_tile_audit import (accepted_report, connector_envelopes,
                                     reference_tapers, taper_regions, waist_boxes)
from tests.print_audit import audit


def volume(part):
    return 0 if part is None else sum(s.volume for s in part.solids())


@pytest.mark.parametrize('preset,expected', [
    ('full', (28,28,6.8)), ('lite', (28,28,4)),
    ('lite-backed-1x6', (28,168,5)), ('lite-backed-l-2x2', (56,56,5)),
])
def test_preset_envelope(preset, expected):
    p = next(p for p in SPEC.presets if p.id == preset)
    part = SPEC.build(p.values)
    assert part.is_valid and len(part.solids()) == 1
    assert tuple(part.bounding_box().size) == pytest.approx(expected)
    assert part.bounding_box().min.Z == pytest.approx(0)


def test_full_preserves_vendor_except_outer_bed_relief():
    part, reference = SPEC.build(), Base()
    assert volume(part-reference) < 1e-6
    removed = reference-part
    assert volume(removed) == pytest.approx(4.5673, abs=.01)
    assert removed.bounding_box().min.Z >= -1e-6
    assert removed.bounding_box().max.Z <= .3+1e-6
    profile = outline(1,1)
    for f in removed.faces():
        for u in (.1,.3,.5,.7,.9):
            for v in (.1,.3,.5,.7,.9):
                pt = f.position_at(u,v)
                if f.is_inside(pt):
                    assert profile.boundary.distance(Point(pt.X,pt.Y)) <= .3+1e-6


@pytest.mark.parametrize('backing', [0, 1, 3])
@pytest.mark.parametrize('directional', [False, True])
def test_lite_snap_fits_like_full_reference(backing, directional):
    # The published click nubs have a small, intentional seated interference.
    # Compare the ACTUAL positive snap collision against the full vendor oracle;
    # do not demand zero interference or merely assert a nominal thickness.
    full = Base()
    full_snap = snap(lite=False, directional=directional)
    reference_interference = volume(full & full_snap)
    lite = SPEC.build({'style':'lite', 'backing_mm':backing})
    seated = Pos(0,0,backing+LITE-3.4)*snap(lite=True, directional=directional)
    assert volume(lite & seated) == pytest.approx(reference_interference, abs=1e-6)
    # At the narrow straight land, a 24.8 mm core has .1 mm per-side clearance.
    for sign in (-1,1):
        assert not lite.is_inside((sign*12.49,0,backing+LITE-.9))
        assert lite.is_inside((sign*12.51,0,backing+LITE-.9))
    if backing:
        assert seated.bounding_box().min.Z-backing == pytest.approx(.6)


@pytest.mark.parametrize('values,message', [
    ({'omit_cells':'0,0'}, 'at least one'),
    ({'x_count':2,'y_count':2,'omit_cells':'0,1 1,0'}, 'edge-connected'),
    ({'omit_cells':'1,0'}, 'outside'), ({'omit_cells':'1,2,3'}, 'x,y pairs'),
    ({'omit_cells':'-1,0'}, 'x,y pairs'), ({'backing_mm':.5}, 'backing_mm'),
    ({'backing_mm':.9}, 'backing_mm'),
    ({'x_count':1.5}, 'integer'),
])
def test_invalid_inputs(values, message):
    with pytest.raises(ValueError, match=message):
        SPEC.build(values)


def test_mask_duplicates_and_spaces():
    assert cells(2,2,'1,1; 1,1') == {(0,0),(0,1),(1,0)}


def test_count_domain_matches_bake_envelope():
    from profiles import PROFILES
    from scripts.export import max_footprint

    width, depth = max_footprint(PROFILES['bambu-h2c-0.4'].settings())
    assert (width, depth) == (323, 244)
    for x in range(1, 13):
        for y in range(1, 13):
            fits = (28*x <= width and 28*y <= depth) or (28*y <= width and 28*x <= depth)
            if fits:
                assert len(cells(x, y)) == x*y
                assert SPEC.resolve_values({'x_count': x, 'y_count': y})['x_count'] == x
            else:
                with pytest.raises(ValueError):
                    cells(x, y)


@pytest.mark.parametrize('x,y', [(9,9), (9,11), (11,9), (11,11)])
def test_reject_oversize_pair_before_geometry(x, y):
    # Both pass the catalog's per-axis range; the model owns the pair rule.
    values = SPEC.resolve_values({'x_count': x, 'y_count': y})
    with pytest.raises(ValueError, match='323 x 244 mm bake envelope'):
        SPEC.build(values)


@pytest.mark.parametrize('style', ['full','lite'])
def test_backing_kept_cells_and_new_corners(style):
    v = {'x_count':2,'y_count':2,'omit_cells':'1,1','backing_mm':1,'style':style}
    part = SPEC.build(v)
    for x,y in ((-14,-14),(-14,14),(14,-14)):
        assert part.is_inside((x,y,.5))
        assert not part.is_inside((x,y,2))
    assert not part.is_inside((14,14,.5))
    # New convex corners (0,28) and (28,0), not just old rectangle corners.
    for x,y in ((-.1,27.9),(27.9,-.1)):
        assert not part.is_inside((x,y,.5))
    for x,y in ((-.1,23.7),(23.7,-.1)):
        assert part.is_inside((x,y,.5))
    # Reflex lattice corner remains sharp.
    assert part.is_inside((-.1,.1,.5))
    assert part.is_inside((.1,-.1,.5))
    assert not part.is_inside((.1,.1,.5))
    # The new edge is a standard half-wall at the original lattice line.
    waist_z = (FULL if style=='full' else LITE)+1-3
    assert part.is_inside((-.4,14,waist_z))
    assert not part.is_inside((-.9,14,waist_z))
    # All connector switches are inert on masks, including the reflex edges.
    disabled = SPEC.build(v | {p.name:False for p in SPEC.params if p.kind=='boolean'})
    assert volume(part-disabled)+volume(disabled-part) < 1e-6


def test_hole_mask_is_connected_and_backing_has_hole():
    part = SPEC.build({'x_count':3,'y_count':3,'omit_cells':'1,1','backing_mm':1})
    assert len(part.solids()) == 1 and part.is_valid
    assert not part.is_inside((0,0,.5))
    assert part.is_inside((28,0,.5))


@pytest.mark.parametrize('edge', ['neg_x','pos_x','neg_y','pos_y'])
def test_rectangle_connector_switch(edge):
    values = {'x_count':2,'y_count':2}
    cut = SPEC.build(values)
    filled = SPEC.build(values | {'connector_'+edge:False})
    assert volume(cut-filled) < 1e-6
    assert volume(filled-cut) > 1


def assert_bed_edges(part, values):
    """Classify exterior bed joins separately from functional snap/mating seams.

    Every perimeter bed edge must meet an outward 45-degree relief face.
    Internal bed edges are vendor opening profile boundaries (functional).
    This catches a sharp outside edge even when the generic audit notices only
    an inner snap chamfer and returns bed_chamfer='present'.
    """
    profile = outline(values['x_count'], values['y_count'], values['omit_cells'])
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    worst, count = 0., 0
    for edge, faces in adjacency.items():
        bb, c = edge.bounding_box(), edge.center()
        if abs(bb.min.Z)>1e-6 or abs(bb.max.Z)>1e-6:
            continue
        if profile.boundary.distance(Point(c.X,c.Y)) > .3+1e-6:
            continue
        assert len(faces) == 2
        normals = [f.normal_at(c) for f in faces]
        assert any(n.Z < -.999 for n in normals)
        assert any(abs(n.Z+math.sqrt(.5)) < 1e-5 for n in normals)
        angle = math.degrees(math.acos(max(-1,min(1,normals[0].dot(normals[1])))))
        worst = max(worst, angle)
        count += 1
    assert count >= len(profile.exterior.coords)-1
    return worst, count


CASES = [(p.id, p.values) for p in SPEC.presets]
CASES += [(f'{s}-{x}x{y}-back{b}', dict(style=s,x_count=x,y_count=y,backing_mm=b))
          for s in ('full','lite') for x,y in ((1,1),(6,1),(1,6),(6,6)) for b in (0,1,3)]
CASES += [(f'{s}-L-back{b}', dict(style=s,x_count=2,y_count=2,omit_cells='1,1',backing_mm=b))
          for s in ('full','lite') for b in (0,1,3)]
# Audit representative new boundaries: the largest backed footprint and the
# transposed long axis in full style. The cheap domain test above covers every
# count pair; repeating large geometry for every style/backing exceeds CI time.
CASES += [
    ('lite-11x8-back1', dict(style='lite',x_count=11,y_count=8,backing_mm=1)),
    ('full-1x11-back0', dict(style='full',x_count=1,y_count=11,backing_mm=0)),
]


@pytest.mark.audit
@pytest.mark.parametrize('name,values', CASES, ids=[c[0] for c in CASES])
def test_endpoint_audit(name, values):
    v = SPEC.resolve_values(values)
    part = SPEC.build(v)
    assert part.is_valid and len(part.solids()) == 1
    angle, edges = assert_bed_edges(part, v)
    raw = audit(part, model=SPEC.name)
    accepted, count = accepted_report(part, v, raw)
    record('opengrid-tile-endpoint', case=name, raw_min_wall=raw.min_wall_mm,
           min_wall=accepted.min_wall_mm, raw_max_overhang=raw.max_overhang_deg,
           max_overhang=accepted.max_overhang_deg, bridge_mm=raw.longest_bridge_mm,
           exposed_edge_angle=angle, bed_edges=edges, waist_regions=count,
           taper_regions=count*(2 if v['style']=='full' else 1),
           volume=part.volume, ok=accepted.ok)
    assert accepted.ok, accepted.format()


def test_exception_rejects_damage_inside_waist():
    v = SPEC.resolve_values()
    part = SPEC.build(v)
    damaged = part - Pos(13.5,0,3)*Box(.3,1,.4)
    with pytest.raises(AssertionError, match='damaged retention waist'):
        accepted_report(damaged,v,audit(damaged))


def test_waist_and_taper_are_separate_from_backing_and_corners():
    v = SPEC.resolve_values(SPEC.presets[-1].values)
    regions = waist_boxes(v)
    # Backed Lite waist is z=1..2.6; observed thin taper is at z=2.65.
    assert all(b[2] == pytest.approx(1) and b[5] == pytest.approx(2.6) for b in regions)
    tapers = taper_regions(v)
    assert len(reference_tapers())==8 and len(tapers)==8
    assert all(r.bounding_box().min.Z == pytest.approx(2.6) and
               r.bounding_box().max.Z == pytest.approx(3.6) for r in tapers)
    assert any(r.is_inside((28,-14,2.65)) for r in tapers)
    for point in ((28,-14,.5),(28,-14,3.7),(27,-27,2.65)):
        assert not any(r.is_inside(point) for r in tapers)


def test_bare_lite_relief_leaves_vendor_waist_above_point_three():
    part = SPEC.build({'style':'lite'})
    for z in (.05,.15,.3,.8,1.5):
        outside = 14-max(0,.3-z)
        assert part.is_inside((outside-.01,0,z))
        assert not part.is_inside((outside+.01,0,z))
        assert part.is_inside((13.21,0,z))
        assert not part.is_inside((13.19,0,z))


def test_thin_taper_reproduces_in_unmodified_vendor():
    # Source taper z=1.4..2.4 linearly changes the wall from 1.5 to .8 mm.
    # At z=2.35 it is .835 mm: approved separately from the planar waist.
    reference = Base()
    backed_l = SPEC.build(SPEC.presets[-1].values)
    for delta, inside in ((-.005,False),(.005,True)):
        assert reference.is_inside((13.165+delta,0,2.35)) == inside
        assert backed_l.is_inside((27.165+delta,-14,2.65)) == inside
    assert 1.5-.7*(2.35-1.4) == pytest.approx(.835)


def test_exception_rejects_damage_inside_taper():
    v = SPEC.resolve_values({'style':'lite','backing_mm':1})
    part = SPEC.build(v)-Pos(13.6,0,2.7)*Box(.2,.5,.1)
    with pytest.raises(AssertionError,match='damaged retention taper'):
        accepted_report(part,v,audit(part))


def test_exception_does_not_hide_thin_backing():
    v = SPEC.resolve_values({'style':'lite','backing_mm':1})
    # Thin the backing at the cavity floor, far from all approved cell walls.
    part = SPEC.build(v)-Pos(0,0,.9)*Box(12,12,.6)
    accepted,_ = accepted_report(part,v,audit(part))
    assert accepted.min_wall_mm == pytest.approx(.6,abs=.01)
    assert not accepted.ok


def test_connector_exclusion_is_clipped_and_absent_on_masks():
    v = SPEC.resolve_values(SPEC.presets[2].values)
    regions = connector_envelopes(v)
    assert len(regions) == 10
    for region in regions:
        bb = region.bounding_box()
        assert bb.min.Z >= 1-1e-6  # never enter adhesive backing
        assert bb.max.Z == pytest.approx(2.8)
        assert min(bb.size.X, bb.size.Y) == pytest.approx(5.1)
    assert not connector_envelopes(SPEC.resolve_values(SPEC.presets[-1].values))


def test_connector_exception_rejects_an_unrelated_ceiling():
    v = SPEC.resolve_values({'x_count':2})
    part = SPEC.build(v)
    # Horizontal ledge inside a cell, far from the edge connector cutter.
    part += Pos(18,0,5)*Box(8,3,1)
    raw = audit(part)
    accepted, _ = accepted_report(part,v,raw)
    assert accepted.max_overhang_deg == 90
    assert not accepted.ok
