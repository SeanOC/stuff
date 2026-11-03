"""Exact contact, removal and audit contracts for the sacrificial cradle."""
from dataclasses import replace
from math import sqrt

import pytest
from build123d import Align, Box, GeomType, Pos

from holders import underware_path_channels as m
from tests import print_audit as pa
from tests.audit_record import record
from tests.test_underware_outside_corner import ENDPOINT_CASES, edge_inventory
from tests.test_underware_path_channels import flat
from underware.outside_support import (ARM_BACKING, CORNER_RADIUS, FIN_THICKNESS, GROOVE_WIDTH,
                                       MARGIN, DesignedSupport, cradle, dimensions)


@pytest.mark.parametrize('gap', [.1, .15, .2, .25, .3])
@pytest.mark.parametrize('width,radius', [(26.4, 6.6), (26.4, 46.6), (54.4, 52.6)])
def test_cradle_gap_fins_pad_and_grooves(width, radius, gap):
    support = cradle(width, radius, gap)
    pad = support.pad
    assert pad.is_valid and len(pad.solids()) == 1
    assert pad.bounding_box().size.Z == pytest.approx(.6)
    assert pad.bounding_box().size.X == pytest.approx(dimensions(width, radius, gap)[0])
    assert pad.bounding_box().size.Y == pytest.approx(sqrt(2) * (radius + gap) + 2 * (ARM_BACKING + MARGIN))
    assert CORNER_RADIUS == 4 and GROOVE_WIDTH >= .4
    radii = [e.radius for e in pad.edges() if e.geom_type == GeomType.CIRCLE
             and abs(e.tangent_at(0).cross(e.tangent_at(.5)).normalized().Z) > .99]
    assert max(radii) == pytest.approx(4.)
    assert min(radii) == pytest.approx(3.7)  # R4 less the 0.3 mm bed chamfer
    united = pad.fuse(*support.fins)
    assert united.is_valid and len(united.solids()) == 1
    fin_y = max(f.bounding_box().max.Y for f in support.fins)
    assert pad.bounding_box().max.Y - fin_y == pytest.approx(5.)
    # Central contact strip has exactly one default layer of removable skin.
    assert pad.is_inside((0, 0, -.1))
    assert pad.is_inside((0, 0, 0))
    assert pad.is_inside((0, 0, -.2))
    assert not pad.is_inside((0, 0, -.20001))
    assert not pad.is_inside((0, 0, .01))
    assert pad.bounding_box().min.Z == pytest.approx(-.2)
    for fin in support.fins:
        bb = fin.bounding_box()
        assert bb.size.X == pytest.approx(FIN_THICKNESS)
        assert .9 <= bb.size.X <= 1.0
        # A top sample is exactly a normal gap below the retained cylinder.
        root = sqrt((radius + gap)**2 - (radius - 1.)**2)
        y = (root + (radius + gap)/sqrt(2))/2 * (1 if bb.center().Y > 0 else -1)
        z = radius - .6 - sqrt((radius + gap)**2 - y*y)
        x = bb.center().X
        assert fin.is_inside((x, y, z), tolerance=1e-5)
        assert not fin.is_inside((x, y, z + .01))
        assert sqrt(y*y + (z - (radius - .6))**2) - radius == pytest.approx(gap)
        turn = (radius + gap)/sqrt(2)
        ty = (turn + ARM_BACKING/2) * (1 if y > 0 else -1)
        tz = radius - .6 - turn + ARM_BACKING/2
        assert fin.is_inside((x, ty, tz), tolerance=1e-5)
        assert not fin.is_inside((x, ty, tz + .01))
        # Both long-side grooves are open above the skin and closed below it.
        for sign in (-1, 1):
            qx = x + sign * (FIN_THICKNESS / 2 + GROOVE_WIDTH / 2)
            assert pad.is_inside((qx, y, -.1))
            assert not pad.is_inside((qx, y, .1))
            assert not pad.is_inside((x + sign*(FIN_THICKNESS/2 + .399), y, .1))
            assert pad.is_inside((x + sign*(FIN_THICKNESS/2 + .401), y, .1))
        assert not pa._downward_curved_faces(pa._ClassifiedPart(fin), (0,0,1), [], bb.min.Z)
        assert pa._max_overhang(pa._ClassifiedPart(fin), (0,0,1), [], bb.min.Z) <= 45


@pytest.mark.parametrize('preset', m.SPEC_OUTSIDE.presets[:3], ids=lambda pr: pr.id)
def test_none_preserves_original_geometry(preset, tmp_path):
    from scripts.export import export_stl
    values = preset.values
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


def synthetic(pad_thickness=.6, fin_thickness=.95, remnant=.2, retained_wall=1.2):
    """Two fins bracket a flat ceiling; the audit must see the actual material."""
    pad = Box(20, 20, pad_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
    groove = Pos(0, 0, remnant) * Box(.4, 20, pad_thickness,
                                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    pad = pad - groove
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
    ({'remnant': .1}, 'groove remnant'),
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


@pytest.mark.audit
@pytest.mark.parametrize('case', SUPPORTED_CASES)
def test_underware_outside_supported_endpoint_audit(case):
    values = SUPPORTED_CASES[case]
    part = m.build_outside_corner(values)
    support = m.outside_designed_support(values)
    frame = m.outside_print_frame(values)
    regions = m.audit_exclusions(m.SPEC_OUTSIDE.name, values)
    assert 'bend-underside' not in regions
    assert part.is_valid and len(part.solids()) == 1
    bbox = (frame * part).bounding_box()
    assert m.outside_extent(m.outside_values(values)) == pytest.approx(
        (bbox.size.Y, bbox.size.X, bbox.size.Z), abs=1e-4)
    report = pa.audit(part, print_frame=frame, exclusions=flat(regions), designed_support=support)
    assert report.ok, report.format()
    families, worst = edge_inventory(part, values)
    assert not [f for f in families if f.startswith('UNCLASSIFIED')], families
    print(f'SUPPORTED | {case} | {report.min_wall_mm:.3f} | {report.max_overhang_deg:.1f} | '
          f'{worst:.1f} | {part.volume:.1f} | PASS', flush=True)
    record(f'outside-corner-supported-{case}', filtered_wall=report.min_wall_mm,
           filtered_ovh=report.max_overhang_deg, edges_worst_exposed=worst,
           bridge=report.longest_bridge_mm, vol=part.volume,
           support_volume=support.pad.volume + sum(f.volume for f in support.fins), result='PASS')
