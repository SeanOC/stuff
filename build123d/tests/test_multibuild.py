"""Multibuild provenance, profile, assembly and production print contracts."""
import inspect
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build123d import Align, Axis, Box, Pos, Compound, Vector
from opengrid import constants as oc
from opengrid.multiconnect import RoundHead, RoundHeadCutter, SlotCutter
from multibuild import SmallHoleConePin, LargeHoleThreadCutter, FixPointCutter
from multibuild import constants as c
from multibuild import demo_plate as demo
from multibuild.multiconnect import POCKET_DEPTH, slot_cutter
from scripts.export import export_stl
from tests.mount_contracts import CONTRACTS, _residual_vol
from tests.print_audit import audit


def test_provenance_and_grid():
    expected = dict(PITCH=25, TILE_THICKNESS=6.4, SMALL_HOLE_MOUTH_D=7.5,
                    SMALL_HOLE_THROAT_D=6, SMALL_HOLE_THROAT_BAND=2.9,
                    SMALL_HOLE_TAPER_DEPTH=1.75)
    for name, value in expected.items():
        assert getattr(c, name) == c.PROVENANCE[name].value
        assert getattr(c, name) == pytest.approx(value)
        assert c.PROVENANCE[name].status == ('V' if name.endswith('DEPTH') else 'C')
        assert c.PROVENANCE[name].source and c.PROVENANCE[name].locator
    assert {k: v.value for k, v in c.LARGE_HOLE_PROFILE.items()} == dict(
        mouth_across_flats=23.4, central_across_flats=21.4, band_height=2.4,
        helix_outer_d=22.6, helix_inner_d=21.4, helix_outer_width=.5,
        helix_inner_width=1.583, helix_pitch=2.5)
    assert all(v.status == 'C' and v.source and v.locator for v in c.LARGE_HOLE_PROFILE.values())
    assert c.GRID_PHASE_PROVENANCE[0] == 'V'
    for i, j in [(0, 0), (-1, 2), (3, -4)]:
        assert c.large_hole_center(i, j) == (25*i+12.5, 25*j+12.5)
        assert c.small_hole_center(i, j) == (25*i+25, 25*j+25)


@pytest.mark.parametrize('fit', [-.3, 0, .3])
@pytest.mark.parametrize('angle', [30, 45, 60])
def test_pin_containment(fit, angle):
    pin = SmallHoleConePin(fit, 1.8, angle)
    base = 7.5 + 2*fit
    assert pin.base_diameter == base
    assert pin.length == pytest.approx((base-1.8)/(2*math.tan(math.radians(angle))))
    assert pin.bounding_box().size.X == pytest.approx(base)
    assert pin.bounding_box().size.Z == pytest.approx(pin.length)
    for z in [*np.arange(0, pin.length, .05), pin.length]:
        # Sourced symmetric envelope; no inferred thread surface.
        depth_from_face = min(z, 6.4-z)
        cavity = 7.5 - 1.5 * min(depth_from_face/1.75, 1)
        pin_d = base - 2*z*math.tan(math.radians(angle))
        assert pin_d <= cavity + 2*fit + 1e-9
    assert pin.is_valid and len(pin.solids()) == 1


@pytest.mark.parametrize('args', [(.31,1.8,45),(-.31,1.8,45),(0,7.5,45),
    (0,8,45),(0,0,45),(0,1.8,29),(0,1.8,61),(float('nan'),1.8,45)])
def test_invalid_pin(args):
    with pytest.raises(ValueError): SmallHoleConePin(*args)


@pytest.mark.parametrize('travel,snap', [(25,False),(50,True)])
def test_pinned_profile_and_allowances(travel, snap):
    names = ['BOTTOM_RADIUS', 'TOP_RADIUS', 'BOTTOM_HEIGHT', 'TAPER_HEIGHT', 'TOP_HEIGHT']
    assert [getattr(oc, 'MULTICONNECT_ROUND_HEAD_'+n) for n in names] == [10,7.5,1,2.5,.5]
    for cls, fields in [(RoundHeadCutter, {'bottom_radius_clearance':.15,'top_radius_clearance':.15}),
                         (SlotCutter, {'bottom_width_clearance':.3,'top_width_clearance':.3})]:
        fields.update(bottom_height_clearance=.212132034, top_height_clearance=-.062132034)
        for key, value in fields.items():
            assert inspect.signature(cls).parameters[key].default == value
    assert POCKET_DEPTH == pytest.approx(4.15)
    before = (oc.OPEN_GRID_UNIT_SIZE, oc.MULTICONNECT_SLOT_LENGTH)
    cutter = slot_cutter(travel, snap=snap)
    bb = cutter.bounding_box()
    assert bb.min.Y == pytest.approx(0, abs=1e-7)
    assert bb.max.Y == pytest.approx(4.15)
    assert bb.min.Z == pytest.approx(-travel)
    assert bb.size.X == pytest.approx(20.3)
    assert (oc.OPEN_GRID_UNIT_SIZE, oc.MULTICONNECT_SLOT_LENGTH) == before == (28,28)
    # Actual cutter sections pin both narrow and wide clearanced profile widths.
    for y, width in [(.2,15.3),(3.8,20.3)]:
        probe = Pos(0,y,-travel/2)*Box(30,.01,.1)
        assert Compound(cutter.intersect(probe)).bounding_box().size.X == pytest.approx(width)


@pytest.mark.parametrize('travel', [0,-25,28,12.5,float('inf'),float('nan')])
def test_invalid_travel(travel):
    with pytest.raises(ValueError): slot_cutter(travel)


@pytest.fixture(scope='module')
def plate():
    return demo.build()


def test_demo_geometry_and_mount_contract(plate, tmp_path):
    assert plate.is_valid and len(plate.solids()) == 1
    assert demo.THICKNESS - POCKET_DEPTH >= 2.4
    assert tuple(plate.bounding_box().size) == pytest.approx((70,7,100))
    stl = tmp_path/'demo.stl'
    export_stl(plate, str(stl))
    assert trimesh.load(stl).is_watertight
    fx = demo.mount_fixtures(demo.MOUNT,{})
    assert [loc.position.X for loc in fx.seat_locs] == [-12.5,12.5]
    for cutter in fx.cutters:
        assert cutter.bounding_box().min.Y == pytest.approx(0,abs=1e-7)
        assert cutter.bounding_box().max.Y == pytest.approx(4.15)
    CONTRACTS[demo.MOUNT](plate,fx)
    # Both heads move together from completely below the plate to their seats.
    heads = [loc*RoundHead() for loc in fx.seat_locs]
    for dz in np.arange(-demo.SEAT_Z-11, .01, 1):
        assert sum(_residual_vol(plate,Pos(0,0,float(dz))*h) for h in heads) < 4


def test_demo_bed_edges_and_slot_pocket_only_audit_exception(plate):
    fx = demo.mount_fixtures(demo.MOUNT,{})
    report = audit(plate,demo.PRINT_ORIENTATION,cutters=fx.cutters)
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
    assert not audit(plate,demo.PRINT_ORIENTATION).ok
    # A cross-section of each outer bed edge loses 0.4 mm at Z=0,
    # tapering to the full envelope at Z=0.4.
    for z, inset in [(.05,.35),(.2,.2),(.4,0)]:
        slab=Pos(0,0,z)*Box(100,30,.0001,align=(Align.CENTER,Align.CENTER,Align.MIN))
        bb=Compound(plate.intersect(slab)).bounding_box()
        assert bb.min.X == pytest.approx(-35+inset,abs=.001)
        assert bb.max.X == pytest.approx(35-inset,abs=.001)
        assert bb.max.Y == pytest.approx(7-inset,abs=.001)
    # Probe relief at every original bed edge, including the slot apertures.
    raw = Box(70,7,100,align=(Align.CENTER,Align.MIN,Align.MIN))
    for cutter in fx.cutters:
        raw -= cutter
    bottom = raw.faces().filter_by(Axis.Z).sort_by(Axis.Z)[0]
    assert len(bottom.edges()) == 20
    for edge in bottom.edges():
        a, b = edge.vertices()
        t = (Vector(b)-Vector(a)).normalized()
        inward = Vector(-t.Y,t.X,0)
        if not raw.is_inside(edge.center()+inward*.01+Vector(0,0,.01)):
            inward = -inward
        assert not plate.is_inside(edge.center()+inward*.1+Vector(0,0,.1))
        assert plate.is_inside(edge.center()+inward*.5+Vector(0,0,.5))


def test_demo_is_not_registered():
    from holders.registry import all_models
    assert all(spec.build.__module__ != demo.__name__ for spec in all_models())


@pytest.mark.parametrize('stub', [LargeHoleThreadCutter,FixPointCutter])
def test_deferred(stub):
    with pytest.raises(NotImplementedError,match='multibuild-research.md'): stub()
