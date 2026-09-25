"""Geometry contracts for the cup-lid prototype (pst-tti3).

Passing these checks is not print approval: see docs/cup-lid-validation.md
for the measured full-part audit and unresolved Fix Point interface.
"""
import math
import sys
from pathlib import Path

import pytest
import trimesh
from build123d import export_stl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from holders.cup_lid import CLEARANCE, LIP_THICKNESS, PARAMS, PITCH, SPEC, WALL, dimensions, holder, pin_centers
from holders.registry import all_models


@pytest.fixture(scope='module')
def part():
    return SPEC.build(SPEC.resolve_values())


def test_registered_default():
    assert SPEC in all_models()
    assert SPEC.title == 'Cup lid holder (Multibuild)'
    assert SPEC.category_id == 'multiboard'
    assert SPEC.presets[0].id == 'sippy_cup_85mm'
    p = SPEC.resolve_values(SPEC.presets[0].values)
    assert (p['lid_diameter'], p['shoulder_height'], p['shoulder_depth']) == (85.3, 13, 4.5)


@pytest.mark.parametrize('preset', SPEC.presets, ids=lambda p: p.id)
def test_presets_watertight_and_envelope(preset, tmp_path):
    values = SPEC.resolve_values(preset.values)
    p = dimensions(values)
    solid = SPEC.build(values)
    assert solid.is_valid
    assert len(solid.solids()) == 1
    assert solid.volume > 0
    stl = tmp_path / 'cup.stl'
    export_stl(solid, str(stl))
    mesh = trimesh.load(stl, force='mesh')
    assert mesh.is_watertight
    assert mesh.is_winding_consistent
    size = solid.bounding_box().size
    sag = p['radius'] - math.sqrt(p['radius']**2 - (p['plate_height']/2)**2)
    assert size.X == pytest.approx(p['width'])
    assert size.Z == pytest.approx(p['plate_height'])
    # Actual depth includes concavity, shoulder gap, lip, AND rear pins.
    assert size.Y == pytest.approx(p['plate_thickness'] + sag + p['shoulder_height'] + CLEARANCE + LIP_THICKNESS + p['pin_length'])


def test_mount_engagement_and_through_hole(part):
    values = SPEC.resolve_values()
    for x, y, z in pin_centers(values):
        assert x == pytest.approx((-1 if x < 0 else 1) * float(values['pin_spacing'])/2)
        assert x / PITCH == round(x/PITCH)
        assert y == z == 0
        # Probe the exported body, not just the positioning helper.
        assert part.is_inside((x, -values['pin_length']/2, 0))
        assert not part.is_inside((x, -values['pin_length']-0.1, 0))
        assert not part.is_inside((x, -2, values['pin_diameter']/2 + 0.1))
    # Sample all the way from behind the pins through the frontmost lips.
    for y in range(-7, 26):
        assert not part.is_inside((0, y, 0))
    assert part.is_inside((0, 2, 5))


def test_shoulder_capture(part):
    p = dimensions({})
    assert p['engagement'] == pytest.approx(4.2)
    assert p['contact_band'] <= p['shoulder_height']
    sag = p['radius'] - math.sqrt(p['radius']**2 - (p['plate_height']/2)**2)
    front = p['plate_thickness'] + sag + p['shoulder_height'] + CLEARANCE
    for sign in (-1, 1):
        assert part.is_inside((sign*(p['radius']-p['engagement']/2), front+WALL/2, 0))
        assert not part.is_inside((sign*(p['radius']-p['engagement']/2), front-1, 0))
        assert not part.is_inside((sign*(p['radius']-p['engagement']-0.1), front+WALL/2, 0))


@pytest.mark.parametrize('param', [p for p in PARAMS if p.kind == 'number'], ids=lambda p:p.name)
@pytest.mark.parametrize('which', ('below', 'above', 'nan', 'boolean'))
def test_out_of_range(param, which):
    bad = {'below': param.min-0.01, 'above':param.max+0.01, 'nan':float('nan'), 'boolean':True}[which]
    with pytest.raises(ValueError, match=param.name):
        holder(**{param.name:bad})


@pytest.mark.parametrize('spacing', ('25', '75', 50, '101'))
def test_spacing_must_put_each_pin_on_the_small_hole_lattice(spacing):
    with pytest.raises(ValueError, match='pin_spacing'):
        holder(pin_spacing=spacing)


def test_wide_mount_needs_wide_lid():
    with pytest.raises(ValueError, match='pin_spacing'):
        holder(pin_spacing='100')
    p = dimensions({'lid_diameter':130, 'pin_spacing':'100'})
    assert p['spacing'] == 100
    assert pin_centers({'lid_diameter':130, 'pin_spacing':'100'}) == ((-50,0,0),(50,0,0))


@pytest.mark.parametrize('param', [p for p in PARAMS if p.kind == 'number'], ids=lambda p:p.name)
@pytest.mark.parametrize('bound', ('min', 'max'))
def test_individual_parameter_extremes_build(param, bound):
    solid = holder(**{param.name:getattr(param, bound)})
    assert solid.is_valid
    assert len(solid.solids()) == 1
    assert solid.volume > 0
