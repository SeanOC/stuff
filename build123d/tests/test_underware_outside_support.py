"""Exact contact, removal and audit contracts for the sacrificial cradle."""
from dataclasses import replace
from math import sqrt

import pytest
from tests.audit_tiers import audit_cases
from build123d import Align, Box, GeomType, Pos

from holders import underware_path_channels as m
from tests import print_audit as pa
from tests.audit_record import record
from tests.test_underware_outside_corner import ENDPOINT_CASES, edge_inventory
from tests.test_underware_path_channels import flat
from underware.outside_support import (ARM_BACKING, CORNER_RADIUS, FIN_THICKNESS,
                                       MARGIN, EAR_LENGTH, CROWN_RISE, TOOTH_LENGTH,
                                       DesignedSupport, cradle, dimensions, tooth_grid)


@pytest.mark.parametrize('gap', [.1, .2, .3])
@pytest.mark.parametrize('width,radius', [(26.4, 6.6), (26.4, 46.6), (54.4, 52.6)])
def test_cradle_gap_teeth_pad_and_ear(width, radius, gap):
    from build123d import Vector
    support = cradle(width, radius, gap)
    pad = support.pad
    assert pad.is_valid and len(pad.solids()) == 1
    assert pad.bounding_box().size.Z == pytest.approx(.6)
    assert pad.bounding_box().size.X == pytest.approx(dimensions(width,radius,gap)[0]+EAR_LENGTH)
    assert pad.bounding_box().size.Y == pytest.approx(sqrt(2)*(radius+gap)+2*(ARM_BACKING+MARGIN))
    assert pad.bounding_box().max.Z == pytest.approx(-gap-CROWN_RISE)
    radii = [e.radius for e in pad.edges() if e.geom_type == GeomType.CIRCLE]
    assert max(radii) >= CORNER_RADIUS-1e-6
    assert any(abs(r-3.7)<1e-6 for r in radii)
    united = pad.fuse(*support.fins)
    assert united.is_valid and len(united.solids()) == 1
    assert pad.bounding_box().max.Y-max(f.bounding_box().max.Y for f in support.fins) == pytest.approx(5.)
    assert support.fins[-1].bounding_box().size.Y == pytest.approx(FIN_THICKNESS)
    xs, angles = tooth_grid(width,radius,gap)
    assert TOOTH_LENGTH <= 1 and .9 <= FIN_THICKNESS <= 1
    for q,n in support.contacts:
        q,n = Vector(q),Vector(n)
        assert any(f.is_inside(q) for f in support.fins)
        assert not united.is_inside(q-n*.01)
        assert (q-Vector(q.X,0,radius)).length-radius == pytest.approx(gap)
    # Both directions between adjacent teeth are recessed, including the crown.
    for a,b in zip(xs,xs[1:]):
        assert not united.is_inside(((a+b)/2,0,-gap-.01))
    from math import sin,cos
    for a,b in zip(angles,angles[1:]):
        t=(a+b)/2
        assert not united.is_inside((xs[0],(radius+gap)*sin(t),radius-(radius+gap)*cos(t)))
    for fin in support.fins:
        assert not pa._downward_curved_faces(pa._ClassifiedPart(fin),(0,0,1),[],fin.bounding_box().min.Z)



@pytest.mark.parametrize('preset', m.SPEC_OUTSIDE.presets[:3], ids=lambda pr: pr.id)
def test_none_preserves_original_geometry(preset, tmp_path):
    from scripts.export import export_stl
    values = {**preset.values, 'supports': 'none'}
    original = m.bend_flat(m.unflattened_outside_corner(values), m.outside_values(values))
    export_stl(original, tmp_path / 'original.stl')
    for gap in (.1, .3):
        part = m.build_outside_corner({**values, 'supports': 'none', 'support_gap_mm': gap})
        assert part.volume == pytest.approx(original.volume, abs=1e-7)
        assert len(part.faces()) == len(original.faces())
        assert (part - original).volume < 1e-7
        assert (original - part).volume < 1e-7
        export_stl(part, tmp_path / 'none.stl')
        assert (tmp_path / 'none.stl').read_bytes() == (tmp_path / 'original.stl').read_bytes()


def synthetic(pad_thickness=.6, fin_thickness=.95, retained_wall=1.2):
    """Two fins bracket a flat ceiling; the audit must see the actual material."""
    pad = Box(20, 20, pad_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
    fins = tuple(Pos(x, 0, pad_thickness) * Box(fin_thickness, 12, 4-pad_thickness,
                 align=(Align.CENTER, Align.CENTER, Align.MIN)) for x in (-3, 3))
    roof = Pos(0, 0, 4.2) * Box(6 + fin_thickness, 12, retained_wall,
                               align=(Align.CENTER, Align.CENTER, Align.MIN))
    part = pad.fuse(*fins, roof)
    return part, DesignedSupport(.2, pad, fins)


def test_opt_in_audit_checks_support_contacts_and_preserves_default():
    part, support = synthetic()
    assert not pa.audit(part).ok
    report = pa.audit(part, designed_support=support)
    assert report.ok, report.format()
    assert 5 < report.longest_bridge_mm < 10
    # A false declaration cannot waive overhangs on absent support geometry.
    report = pa.audit(part - support.fins[0], designed_support=support)
    assert any('absent' in f for f in report.failures())
    assert not pa.audit(part, designed_support=replace(support, gap_mm=.1)).ok
    # Widen the gap between contacts past 10 mm, with valid declared material.
    shifted = tuple(Pos(-3 if i == 0 else 3, 0, 0) * f for i, f in enumerate(support.fins))
    roof = Pos(0, 0, 4.2) * Box(12.95, 12, 1.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    wide = support.pad.fuse(*shifted, roof)
    assert not pa.audit(wide, designed_support=replace(support, fins=shifted)).ok


@pytest.mark.parametrize('change,reason', [
    ({'pad_thickness': .7}, 'pad thickness'),
    ({'fin_thickness': .8}, 'wall'),
    ({'fin_thickness': 1.1}, 'fin wall'),
    ({'retained_wall': .8}, 'wall'),
])
def test_support_wall_limits_cannot_be_waived(change, reason):
    part, support = synthetic(**change)
    report = pa.audit(part, designed_support=support)
    assert not report.ok
    assert any(reason in f for f in report.failures()), report.format()


def test_supported_bed_error_names_pad():
    with pytest.raises(ValueError, match='built-in supports.*pad included.*build volume'):
        m.build_outside_corner({'supports': 'built_in', 'length_units': 7, 'channel_total_height': 40})


@pytest.mark.parametrize('values,reason', [
    ({'grip_flare': 15}, 'grip_flare above'),
    ({'number_of_cord_cutouts': 12}, 'cutout'),
    ({'number_of_cord_cutouts': 2, 'shift_cutouts': 28}, 'cutout'),
])
def test_supported_infeasible_numeric_endpoints(values, reason):
    with pytest.raises(ValueError, match=reason):
        m.build_outside_corner({**values, 'supports': 'built_in'})


SUPPORTED_CASES = {name: {**values, 'supports': 'built_in'} for name, values in ENDPOINT_CASES.items()}
SUPPORTED_CASES.update({'gap-min': {'supports': 'built_in', 'added_radius': 1, 'support_gap_mm': .1},
                        'gap-max': {'supports': 'built_in', 'added_radius': 1, 'support_gap_mm': .3},
                        'w2-h28-r1': {'supports': 'built_in', 'added_radius': 1,
                                     'channel_width_units': 2, 'channel_total_height': 28},
                        'cut-n12-max': {'supports': 'built_in', 'length_units': 7,
                                       'number_of_cord_cutouts': 12, 'cord_cutout_width': 6,
                                       'distance_between_cutouts': 14, 'suppress_connectors': 'BBBBBBB'},
                        'cut-shift28-max': {'supports': 'built_in', 'length_units': 7,
                                           'number_of_cord_cutouts': 2, 'shift_cutouts': 28,
                                           'suppress_connectors': 'BBBBBBB'}})

for corner in ('min-corner', 'max-corner'):
    for gap in (.1, .3):
        SUPPORTED_CASES[f'{corner}-gap-{gap}'] = {**SUPPORTED_CASES[corner], 'support_gap_mm': gap}


@pytest.mark.audit
@pytest.mark.parametrize('case', SUPPORTED_CASES)
@audit_cases(m.SPEC_OUTSIDE, lambda p: SUPPORTED_CASES[p['case']])
def test_underware_outside_supported_endpoint_audit(case):
    values = SUPPORTED_CASES[case]
    part = m.build_outside_corner(values)
    support = m.outside_designed_support(values)
    frame = m.outside_print_frame(values)
    regions = m.audit_exclusions(m.SPEC_OUTSIDE.name, values)
    assert 'bend-underside' not in regions
    assert part.is_valid and len(part.solids()) == 2
    assert part.volume == pytest.approx(sum(s.volume for s in part.solids()),abs=1e-6)
    bbox = (frame * part).bounding_box()
    assert m.outside_extent(m.outside_values(values)) == pytest.approx(
        (bbox.size.Y, bbox.size.X, bbox.size.Z), abs=1e-4)
    report = pa.audit(part, print_frame=frame, exclusions=flat(regions), designed_support=support)
    assert report.ok, report.format()
    families, worst = edge_inventory(part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    print(f'SUPPORTED | {case} | {report.min_wall_mm:.3f} | {report.max_overhang_deg:.1f} | '
          f'{worst:.1f} | {part.volume:.1f} | PASS', flush=True)
    v = m.outside_values(values)
    xs, angles = tooth_grid(m.c.channel_width(v['channel_width_units']),
                            m.p.outside_floor_radius(v['channel_total_height'], v['added_radius']),
                            v['support_gap_mm'])
    record(f'outside-corner-supported-{case}', filtered_wall=report.min_wall_mm,
           filtered_ovh=report.max_overhang_deg, edges_worst_exposed=worst,
           bridge=report.longest_bridge_mm, vol=part.volume,
           support_volume=support.pad.fuse(*support.fins).volume,
           contact_dots=len(xs)*len(angles), extent=report.extent_mm,
           edges=dict(sorted(families.items())), result='PASS')


@pytest.mark.parametrize('values', [{}, {'added_radius': 1},
    {'channel_width_units': 2, 'channel_total_height': 28, 'added_radius': 1},
    {'channel_total_height': 10, 'mirror_channel': True}])
def test_full_arc_is_exactly_retained_and_cradle_is_detached(values):
    part = m.build_outside_corner(values)
    support = m.outside_designed_support(values)
    disposable = support.pad.fuse(*support.fins)
    retained = part-disposable
    raw = m.unflattened_outside_corner(values)
    assert len(part.solids()) == 2 and len(disposable.solids()) == 1
    assert (retained-raw).volume < 1e-6 and (raw-retained).volume < 1e-6
    assert retained.volume == pytest.approx(raw.volume,abs=1e-6)
    gap = m.outside_values(values)['support_gap_mm']
    assert disposable.distance_to(retained) == pytest.approx(gap,abs=1e-6)
    frame = m.outside_print_frame(values)
    assert (frame*retained).bounding_box().min.Z-(frame*support.pad).bounding_box().max.Z == pytest.approx(1+gap)


def test_contact_cells_reject_missing_teeth_false_probes_and_bonding():
    from build123d import Vector
    values = {'channel_total_height': 10}
    part = m.build_outside_corner(values)
    support = m.outside_designed_support(values)
    frame = m.outside_print_frame(values)
    def check(p=part, s=support):
        return pa._DesignedSupport(s.moved(frame),frame*p,(0,0,1))
    assert not check().failures
    q,n = support.contacts[len(support.contacts)//2]
    false = replace(support, contacts=((tuple(Vector(q)+Vector(n)),n),*support.contacts[1:]))
    assert any('probe' in error for error in check(s=false).failures)
    assert any('bracketed' in error for error in check(s=replace(support,cells=())).failures)
    assert any('absent' in error for error in check(p=part-support.fins[0]).failures)
    # A solid link between an actual crown tooth and the retained channel.
    local_q = (frame*Pos(*q)).position
    link = frame.inverse()*Pos(*local_q)*Box(.3,.3,.4,align=(Align.CENTER,Align.CENTER,Align.MIN))
    assert any('touches' in error for error in check(p=part.fuse(link)).failures)
    assert any('bridge limit' in error for error in
               check(s=replace(support,cells=((0,1,len(support.contacts)-1,len(support.contacts)-2),))).failures)


def test_grooved_pad_cannot_hide_a_remnant_in_its_envelope():
    part, support = synthetic()
    groove = Pos(0,0,.2)*Box(1,20,.5,align=(Align.CENTER,Align.CENTER,Align.MIN))
    report = pa.audit(part-groove, designed_support=replace(support,pad=support.pad-groove))
    assert any('uniform top' in error for error in report.failures())


def test_supported_classifier_is_the_exact_material_union():
    import itertools
    from build123d import Vector
    part = m.build_outside_corner()
    declaration = m.outside_designed_support()
    frame = m.outside_print_frame({})
    part = frame*part
    support = pa._DesignedSupport(declaration.moved(frame),part,(0,0,1))
    assert not support.failures
    classified = pa._SupportedPart(part,support)
    native = pa._ClassifiedPart(part,partition=False)
    bb = part.bounding_box()
    points = [Vector(*(lo+(hi-lo)*t for lo,hi,t in zip(bb.min,bb.max,ts)))
              for ts in itertools.product((0,.1,.3,.5,.7,.9,1),repeat=3)]
    # Include real material boundaries and both sides of every contact gap.
    for q,n in declaration.moved(frame).contacts:
        q,n = Vector(q),Vector(n)
        points.extend((q,q+n*.01,q-n*.01,q-n*.2,q-n*.21))
    for point in points:
        assert classified.is_inside(point) == native.is_inside(point), tuple(point)
