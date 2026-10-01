"""Multibuild provenance, profile, assembly and production print contracts."""
import inspect
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build123d import Align, Axis, Box, Pos, Rot, Compound, Vector, Mode, Plane, section
from opengrid import constants as oc
from opengrid.multiconnect import RoundHead, RoundHeadCutter, SlotCutter
from multibuild import SmallHoleConePin, LargeHoleThreadCutter, FixPointCutter, channel_cutter, point_cutter
from multibuild import constants as c
from multibuild import demo_plate as demo
from multibuild import tile
from multibuild.multiconnect import POCKET_DEPTH, POINT_ONRAMP, point_length, slot_cutter
from scripts.export import export_stl
from tests.mount_contracts import CONTRACTS, _residual_vol, channel_pairs
from tests.print_audit import audit


# pst-ozpae: every value is [V], measured from an official file (locator =
# committed artefact). test_reference_provenance re-derives each value.
def _check_tag(p):
    assert p.status == 'V' and p.source
    assert p.locator.startswith('reference/measured/') and p.locator.endswith('.json')
    assert (ROOT / p.locator).is_file()


def test_provenance_and_grid():
    for name, p in c.PROVENANCE.items():
        assert getattr(c, name) == p.value
        _check_tag(p)
    for p in c.LARGE_HOLE_PROFILE.values():
        _check_tag(p)
    # Derived stays derived: roots are thickness and the per-face tapers.
    assert c.SMALL_HOLE_TAPER_DEPTH == pytest.approx((c.SMALL_HOLE_MOUTH_D - c.SMALL_HOLE_THROAT_D) / 2)
    assert c.LARGE_HOLE_PROFILE['band_height'].value == pytest.approx(
        c.TILE_THICKNESS - 2 * c.LARGE_HOLE_TAPER_DEPTH)
    status, _, locators = c.GRID_PHASE_PROVENANCE
    assert status == 'V'
    assert all((ROOT / loc).is_file() for loc in locators.split(' + '))
    for i, j in [(0, 0), (-1, 2), (3, -4)]:
        assert c.large_hole_center(i, j) == (25*i+12.5, 25*j+12.5)
        assert c.small_hole_center(i, j) == (25*i+25, 25*j+25)


@pytest.mark.parametrize('cells', [(2, 2), (3, 1), (1, 1)])
def test_regenerated_tile(cells):
    nx, ny = cells
    t = tile.tile(cells)
    thickness = tile.TILE_PROFILE['thickness'].value
    assert t.is_valid and len(t.solids()) == 1
    assert tuple(t.bounding_box().size) == pytest.approx((25*nx, 25*ny, thickness))
    mid = section(t, section_by=Plane.XY.offset(thickness/2), mode=Mode.PRIVATE)
    holes = sorted((round(w.bounding_box().center().X, 3), round(w.bounding_box().center().Y, 3),
                    round(w.bounding_box().size.X, 3)) for f in mid.faces() for w in f.inner_wires())
    central = c.LARGE_HOLE_PROFILE['central_across_flats'].value
    large = [(*c.large_hole_center(i, j), central) for i in range(nx) for j in range(ny)]
    small = [(*c.small_hole_center(i, j), c.SMALL_HOLE_THROAT_D) for i in range(nx-1) for j in range(ny-1)]
    assert holes == sorted(large + small)
    mouth = section(t, section_by=Plane.XY.offset(1e-3), mode=Mode.PRIVATE)
    widths = sorted(round(w.bounding_box().size.X, 2) for f in mouth.faces() for w in f.inner_wires())
    mouth = c.LARGE_HOLE_PROFILE['mouth_across_flats'].value
    assert widths == sorted([mouth]*len(large) + [c.SMALL_HOLE_MOUTH_D]*len(small))


def test_regenerated_tile_profile_is_measured_and_licensed():
    assert all(p.status == 'V' and (ROOT / p.locator).is_file() for p in tile.TILE_PROFILE.values())
    head = Path(tile.__file__).read_text(encoding='utf-8').splitlines()[:3]
    assert 'Multiboard Licence' in head[0] and 'NOT covered by' in head[1]
    assert (Path(tile.__file__).parent / 'LICENSE-MULTIBOARD.md').is_file()
    with pytest.raises(ValueError):
        tile.tile((0, 2))


@pytest.mark.parametrize('fit', [-.3, 0, .3])
@pytest.mark.parametrize('angle', [45, 50, 60])
def test_pin_containment(fit, angle):
    # The measured bore wall is 45°, so only pins at least that steep fit.
    pin = SmallHoleConePin(fit, 1.8, angle)
    base = c.SMALL_HOLE_MOUTH_D + 2*fit
    assert pin.base_diameter == base
    assert pin.length == pytest.approx((base-1.8)/(2*math.tan(math.radians(angle))))
    assert pin.bounding_box().size.X == pytest.approx(base)
    assert pin.bounding_box().size.Z == pytest.approx(pin.length)
    for z in [*np.arange(0, pin.length, .05), pin.length]:
        # Measured symmetric envelope; the thread only enlarges it.
        depth_from_face = min(z, c.TILE_THICKNESS-z)
        drop = c.SMALL_HOLE_MOUTH_D - c.SMALL_HOLE_THROAT_D
        cavity = c.SMALL_HOLE_MOUTH_D - drop * min(depth_from_face/c.SMALL_HOLE_TAPER_DEPTH, 1)
        pin_d = base - 2*z*math.tan(math.radians(angle))
        assert pin_d <= cavity + 2*fit + 1e-9
    assert pin.is_valid and len(pin.solids()) == 1


@pytest.mark.parametrize('args', [(.31,1.8,45),(-.31,1.8,45),(0,c.SMALL_HOLE_MOUTH_D,45),
    (0,0,45),(0,1.8,44),(0,1.8,61),(float('nan'),1.8,45)])
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


@pytest.mark.parametrize('length', [25, 50, 75, 100])
def test_channel_profile_matches_short_slot(length):
    channel = channel_cutter(length, onramps=(), seats=())
    slot = slot_cutter(length)
    bb = channel.bounding_box()
    assert channel.is_valid and len(channel.solids()) == 1
    assert (bb.min.Z, bb.max.Z) == pytest.approx((0, length))
    assert (bb.min.Y, bb.max.Y) == pytest.approx((0, POCKET_DEPTH))
    for y in (.2, 1, 2, 3, 3.8):
        probe = Pos(0, y, length/2)*Box(30, .01, .1)
        actual = channel.intersect(probe)
        expected = (Pos(0, 0, length)*slot).intersect(probe)
        assert Compound(actual).volume == pytest.approx(Compound(expected).volume, abs=1e-7)
        assert Compound(actual).bounding_box().size.X == pytest.approx(Compound(expected).bounding_box().size.X)


@pytest.mark.parametrize('kwargs', [
    dict(length=0), dict(length=-25), dict(length=28), dict(length=float('nan')),
    dict(length=float('inf')), dict(drop=0), dict(drop=25), dict(drop=30),
    dict(drop=float('nan')), dict(onramps=(0,)), dict(onramps=(75,)),
    dict(onramps=(10,)), dict(onramps=(65,)), dict(onramps=(12.5, 30)),
    dict(onramps=(12.5, 12.5)), dict(onramps=(float('nan'),)),
    dict(seats=(26,)), dict(seats=(25,25)), dict(seats=(75,)),
    dict(seats=(float('inf'),)), dict(seats=(50,), onramps=(12.5,)),
])
def test_invalid_channel(kwargs):
    params = dict(length=75, onramps=(12.5, 37.5), seats=(25, 50), drop=12.5)
    params.update(kwargs)
    with pytest.raises(ValueError):
        channel_cutter(**params)


@pytest.fixture(scope='module')
def channel_demo():
    return demo.channel_plate()


def test_channel_centres_and_snap_features():
    from build123d import Rot
    from opengrid.multiconnect import SlotOpeningCutter
    channel = channel_cutter(75, onramps=demo.ONRAMPS, seats=demo.SEATS)
    assert channel.is_valid and len(channel.solids()) == 1
    assert (channel.bounding_box().min.Z, channel.bounding_box().max.Z) == pytest.approx((0,75))
    spine = channel_cutter(75, onramps=(), seats=())
    for z in (12.5, 37.5):
        opening = Pos(0,POCKET_DEPTH,z)*Rot(90,0,0)*SlotOpeningCutter()
        assert (opening-channel).volume == pytest.approx(0, abs=1e-7)
        assert channel.is_inside((10.5,.1,z))
    assert not channel.is_inside((10.5,.1,62.5))
    for z in (25,50):
        # Retained snap material has exactly the pinned library shape,
        # except where the required neighbouring on-ramp intersects it.
        notch = Pos(0,0,z)*(slot_cutter(snap=False)-slot_cutter(snap=True))
        retained = notch-channel
        assert retained.volume > 0
        assert (retained-spine).volume == pytest.approx(0, abs=1e-7)


def test_channel_demo_contract_and_audit(channel_demo, tmp_path):
    plate = channel_demo
    fx = demo.mount_fixtures(demo.CHANNEL_MOUNT,{})
    assert plate.is_valid and len(plate.solids()) == 1
    assert tuple(plate.bounding_box().size) == pytest.approx((70,7,100))
    assert [loc.position.Z for loc in fx.onramp_locs] == [12.5,37.5,12.5,37.5]
    assert [loc.position.Z for loc in fx.seat_locs] == [25,50,25,50]
    CONTRACTS[demo.CHANNEL_MOUNT](plate,fx)
    stl = tmp_path/'channel.stl'
    export_stl(plate,str(stl))
    assert trimesh.load(stl).is_watertight
    report = audit(plate,demo.PRINT_ORIENTATION,cutters=fx.cutters)
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
    assert not audit(plate,demo.PRINT_ORIENTATION).ok
    # Four board heads move together through the one-unit insertion sequence.
    for dz in np.linspace(-12.5,0,26):
        assert all(_residual_vol(plate,Pos(0,0,float(dz))*loc*RoundHead()) < 2 for loc in fx.seat_locs)


@pytest.mark.parametrize('defect', ['sealed_entry', 'blocked_channel', 'open_top', 'thin_backing'])
def test_channel_contract_detects_broken_paths(channel_demo, defect):
    fx = demo.mount_fixtures(demo.CHANNEL_MOUNT,{})
    part = channel_demo
    if defect == 'sealed_entry':
        part += Pos(-12.5,.25,12.5)*Box(23,.5,23)
    elif defect == 'blocked_channel':
        part += Pos(-12.5,2,32)*Box(21,4,.5)
    elif defect == 'thin_backing':
        for x in (-12.5,12.5):
            part -= Pos(x,POCKET_DEPTH+1,0)*Box(
                22,3,demo.CHANNEL_LENGTH,align=(Align.CENTER,Align.MIN,Align.MIN))
        assert part.is_valid and len(part.solids()) == 1
        assert part.bounding_box().max.Y == pytest.approx(7)
        with pytest.raises(AssertionError, match='local backing'):
            CONTRACTS[demo.CHANNEL_MOUNT](part,fx)
        return
    else:
        part -= Pos(-12.5,3,87.5)*Box(21,6,26)
    with pytest.raises(AssertionError):
        CONTRACTS[demo.CHANNEL_MOUNT](part,fx)


def test_slot_demo_volume_unchanged(plate):
    assert plate.volume == pytest.approx(44255.325, abs=.001)


def test_channel_100_uses_explicit_centres():
    channel = channel_cutter(100, onramps=(12.5,37.5,62.5), seats=(25,50,75))
    assert channel.bounding_box().max.Z == pytest.approx(100)
    for z in (12.5,37.5,62.5):
        assert channel.is_inside((10.5,.1,z))
    # The library never generates the next row implicitly.
    assert not channel.is_inside((10.5,.1,87.5))


def test_channel_pairs_keep_x_only_matching_on_demo():
    # pst-93yd5 2c: X + Z matching is a superset rule; on full-height
    # spines it must reproduce the previous X-centre-only matching exactly.
    fx = demo.mount_fixtures(demo.CHANNEL_MOUNT, {})
    old = []
    for cutter in fx.cutters:
        bb = cutter.bounding_box()
        x = (bb.min.X+bb.max.X)/2
        old.append([(s, r) for s, r in zip(fx.seat_locs, fx.onramp_locs)
                    if abs(s.position.X-x) < 1e-7])
    new = channel_pairs(fx)
    assert [[(s.position, r.position) for s, r in pairs] for pairs in new] == \
        [[(s.position, r.position) for s, r in pairs] for pairs in old]
    assert [len(pairs) for pairs in new] == [2, 2]


def test_point_cutter_is_shortest_channel_segment():
    pocket = point_cutter()
    bb = pocket.bounding_box()
    assert pocket.is_valid and len(pocket.solids()) == 1
    # One head-cutter radius above the seat, from the library cutter.
    assert point_length() == pytest.approx(
        POINT_ONRAMP+c.PITCH/2+RoundHeadCutter().bounding_box().size.X/2)
    assert (bb.min.Z, bb.max.Z) == pytest.approx((0, point_length()))
    assert (bb.min.Y, bb.max.Y) == pytest.approx((0, POCKET_DEPTH))
    # Same features as a channel with that one on-ramp and seat.
    channel = channel_cutter(50, onramps=(POINT_ONRAMP,), seats=(POINT_ONRAMP+c.PITCH/2,))
    clip = Box(30, 10, point_length()-1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    assert (pocket & clip).volume == pytest.approx((channel & clip).volume, abs=1e-6)
    with pytest.raises(ValueError):
        point_cutter(drop=25)


def _point_plate(gap):
    """70x7 plate, four point pockets; the upper row sits gap above the lower."""
    pocket = point_cutter()
    bottoms = (3.0, 3.0+point_length()+gap)
    plate = Box(70, 7, bottoms[1]+point_length()+3,
                align=(Align.CENTER, Align.MIN, Align.MIN))
    cutters = [Pos(x, 0, z)*pocket for x in (-12.5, 12.5) for z in bottoms]
    for cutter in cutters:
        plate -= cutter
    def poses(offset):
        return [Pos(x, POCKET_DEPTH, z+offset)*Rot(90, 0, 0)
                for x in (-12.5, 12.5) for z in bottoms]
    from holders.registry import MountFixtures
    return plate, MountFixtures(cutters, poses(POINT_ONRAMP+12.5), onramp_locs=poses(POINT_ONRAMP),
                                entry_axis=(0, 0, 1), face_normal=(0, -1, 0))


def test_channel_contract_accepts_discrete_pockets_sharing_x():
    plate, fx = _point_plate(gap=14.85)
    CONTRACTS[demo.CHANNEL_MOUNT](plate, fx)
    # Under X-only matching each column's two pockets formed one spine.
    assert [len(p) for p in channel_pairs(fx)] == [1, 1, 1, 1]


def test_channel_contract_rejects_abutting_point_pockets():
    # Abutting pockets leave no cap over the lower one: its head rides
    # straight into the upper pocket, i.e. they are one spine.
    plate, fx = _point_plate(gap=0)
    with pytest.raises(AssertionError, match='exit through channel top|not enclosed'):
        CONTRACTS[demo.CHANNEL_MOUNT](plate, fx)


def test_channel_contract_rejects_pose_outside_every_cutter():
    plate, fx = _point_plate(gap=14.85)
    fx.seat_locs[0] = Pos(0, 0, 100)*fx.seat_locs[0]
    fx.onramp_locs[0] = Pos(0, 0, 100)*fx.onramp_locs[0]
    with pytest.raises(AssertionError, match='exactly one channel cutter'):
        channel_pairs(fx)
