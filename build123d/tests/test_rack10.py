"""Rack10 interface, fit, apertures, topology and production endpoint audit."""
from math import acos, degrees

import pytest
import trimesh
from OCP.BRep import BRep_Tool
from build123d import Align, Box, Cylinder, Pos

from holders import rack10_blank_panel as blank, rack10_keystone_panel as keystone, rack10_tray as shelf
from holders import rack10_rail_strip as rail
from holders.registry import in_print_frame
from rack10 import constants as c
from rack10.keystone import keystone_row, mating_edge
from rack10.panel import ear_profile, hole_centres, panel, panel_height
from rack10.rail_strip import peg_stations, rail_hole_centres
from rack10.tray import TrayFitError, tie_mating_edge, tray, tray_dimensions
from rack10.vent import vent_pattern
from scripts.export import export_stl
from tests.audit_record import record
from tests.print_audit import audit

SPECS = (blank.SPEC, keystone.SPEC, shelf.SPEC, rail.SPEC)
PRESETS = [(spec, pr) for spec in SPECS for pr in spec.presets]
CASES = [(spec, pr.values, pr.id) for spec, pr in PRESETS]
for spec in SPECS:
    for param in spec.params:
        if param.kind in ('number', 'integer'):
            for endpoint in (param.min, param.max):
                CASES.append((spec, {param.name:endpoint}, f'{param.name}-{endpoint}'))
CASES += [(blank.SPEC, {'units':2,'vented':True,'slot_mm':8}, 'vented-max-slot'),
          (keystone.SPEC, {'count':c.MAX_KEYSTONES,'slot_mm':8}, 'max-ports-slot'),
          (shelf.SPEC, {'device_w':211.45,'device_d':200,'device_h':72,'clearance':2,'slot_mm':8}, 'max-corner'),
          (shelf.SPEC, {'device_w':40,'device_d':40,'device_h':10,'clearance':.5,'slot_mm':8}, 'min-corner')]

# Hardware modes exercise both thickness limits and the longest diagonal rail.
CASES += [(rail.SPEC, {'pin_units':n, 'thickness':t, 'mount':m, 'hole':h},
           f'{h}-{m}-{n}-{t}')
          for h,m in [('cage_nut','pegs'),('cage_nut','pin_holes'),('insert','pin_holes')]
          for n,t in [(5,11),(27,14)]]


def test_panel_datum_and_round_apertures():
    part = panel(1)
    assert part.bounding_box().size.Y == pytest.approx(43.65)
    centres = hole_centres(1)
    assert [y for x,y in centres[:3]] == pytest.approx([5.95,21.825,37.7])
    assert centres[3][0]-centres[0][0] == pytest.approx(c.HOLE_SPAN)
    for x,y in centres:
        assert not part.is_inside((x,y,2))
        assert not part.is_inside((x+c.EAR_HOLE_D/2-.01,y,2))
        assert part.is_inside((x+c.EAR_HOLE_D/2+.01,y,2))
    for units in (1,2,7):
        ys = sorted({y for x,y in hole_centres(units)})
        assert len(ys) == 3*units
        assert ys[0] == pytest.approx(panel_height(units)-ys[-1])


@pytest.mark.parametrize('slot',[1,6,9,10,float('nan')])
def test_slot_ligament_guard(slot):
    with pytest.raises(ValueError,match='ear ligament'):
        ear_profile(1,slot)


def test_maximum_slot_has_symmetric_ligaments():
    part = panel(1,slot_mm=8)
    for x,y in hole_centres(1):
        assert not part.is_inside((x,y+4-.01,2))
        assert part.is_inside((x,y+4+.01,2))
    assert hole_centres(1)[0][1]-4 == pytest.approx(1.95)


def test_ear_ligament_guard_measures_the_actual_boundary(monkeypatch):
    monkeypatch.setattr(c,'HOLE_EDGE',4.5)
    with pytest.raises(ValueError,match='ear ligament 0.600 mm is below 0.9 mm'):
        ear_profile(1)


def test_keystone_count_and_latch_are_functional():
    with pytest.raises(ValueError,match='USABLE_WIDTH'):
        keystone_row(c.MAX_KEYSTONES+1)
    part=keystone.build({'count':c.MAX_KEYSTONES})
    y=panel_height(1)/2
    for i in range(c.MAX_KEYSTONES):
        x=(i-(c.MAX_KEYSTONES-1)/2)*c.KEYSTONE_PITCH
        for z in (.5,1.5,2.9):
            assert not part.is_inside((x,y,z))
        assert not part.is_inside((x+c.KEYSTONE_WIDTH/2-.01,y,1.5))
        assert part.is_inside((x+c.KEYSTONE_WIDTH/2+.01,y,1.5))
        assert part.is_inside((x,y+c.KEYSTONE_HEIGHT/2+.1,2.4))
        assert not part.is_inside((x,y+c.KEYSTONE_HEIGHT/2+.1,2.6))


def test_vent_fraction_and_guards():
    cutters=vent_pattern((200,24),.35)
    assert sum(p.volume/(c.EAR_THICKNESS+2) for p in cutters) == pytest.approx(200*24*.35)
    assert all(max(p.bounding_box().size.X,p.bounding_box().size.Y)<=10 for p in cutters)
    assert vent_pattern((200,24),0) == []
    for area,fraction in [((200,24),.9),((3,24),.35),((200,24),.001)]:
        with pytest.raises(ValueError): vent_pattern(area,fraction)


def test_tray_width_boundary_and_units():
    good=220.24-2-2*c.RAIL_WALL
    bad=220.26-2-2*c.RAIL_WALL
    assert tray_dimensions(good,100,28)['outer_width'] == pytest.approx(220.24)
    with pytest.raises(TrayFitError,match='tray fit'):
        tray_dimensions(bad,100,28)
    assert tray_dimensions(98,98,31)['units']==1
    assert tray_dimensions(160,100,28)['units']==1
    assert tray_dimensions(117,112,51)['units']==2
    with pytest.raises(TrayFitError,match='tray height'):
        tray_dimensions(117,112,51,units=1)
    with pytest.raises(TrayFitError,match='tray fit'):
        tray_dimensions(213.45,100,28,clearance=2)


def test_tray_device_envelope_rear_and_tie_apertures():
    part=tray(98,98,31,front_cutouts=[(0,20,20,10)])
    assert not part.is_inside((0,20,1.5))
    # Device envelope corners are clear; rear is open above the floor.
    for x in (-49,49):
        for y in (4,35):
            for z in (4,102):
                assert not part.is_inside((x,y,z))
    assert not part.is_inside((0,20,102.9))
    assert part.is_inside((0,1.5,50))
    for x in (-24.5,24.5):
        for z in (3+98/3,3+196/3):
            assert not part.is_inside((x,1.5,z))
            assert part.is_inside((x+2,1.5,z))
    with pytest.raises(TrayFitError,match='3 mm frame'):
        tray(98,98,31,front_cutouts=[(0,3,20,10)])


def assert_finished_edges(part,spec,values):
    v=spec.resolve_values(values)
    adjacent={}
    for face in part.faces():
        for edge in face.edges(): adjacent.setdefault(edge,[]).append(face)
    worst=0.
    for edge,faces in adjacent.items():
        if len(faces)==1:
            assert BRep_Tool.IsClosed_s(edge.wrapped,faces[0].wrapped) or BRep_Tool.Degenerated_s(edge.wrapped)
            continue
        assert len(faces)==2
        if spec is keystone.SPEC and mating_edge(edge,v['count'],panel_height(1)/2): continue
        if spec is shelf.SPEC and tie_mating_edge(edge,v['device_w'],v['device_d']): continue
        q=edge.center()
        n0,n1=(f.normal_at(q) for f in faces)
        angle=degrees(acos(max(-1,min(1,n0.dot(n1)))))
        assert angle<90-1e-3,(tuple(q),angle)
        worst=max(worst,angle)
    return worst


@pytest.mark.parametrize('spec,preset',PRESETS,ids=[f'{s.name}-{p.id}' for s,p in PRESETS])
def test_preset_is_one_watertight_solid_inside_both_beds(spec,preset,tmp_path):
    part=spec.build(preset.values)
    assert part.is_valid and len(part.solids())==1
    size=part.bounding_box().size
    assert size.X<=305 and size.Y<=320 and size.Z<=320
    export_stl(part,tmp_path/'part.stl')
    assert trimesh.load_mesh(tmp_path/'part.stl').is_watertight


@pytest.mark.audit
@pytest.mark.parametrize('spec,values,case',CASES,ids=[f'{s.name}-{n}' for s,v,n in CASES])
def test_endpoint_audit_and_edges(spec,values,case):
    part=spec.build(values)
    if spec is shelf.SPEC:
        v=spec.resolve_values(values)
        device=Pos(0,c.FLOOR+v['clearance'],c.PANEL_THICKNESS+v['clearance'])*Box(
            v['device_w'],v['device_h'],v['device_d'],align=(Align.CENTER,Align.MIN,Align.MIN))
        assert (part & device).volume < 1e-6, 'floor, rails or root blend intrudes into the device envelope'
    worst=assert_finished_edges(part,spec,values)
    report=audit(in_print_frame(spec, values, part),model=spec.name)
    assert report.ok,report.format()
    print(f'RACK10 | {spec.name}/{case} | wall {report.min_wall_mm:.3f} | overhang {report.max_overhang_deg:.1f} | edges {worst:.1f} | volume {part.volume:.3f} | PASS')
    record(f'{spec.name}-{case}',min_wall=report.min_wall_mm,worst_overhang=report.max_overhang_deg,
           exposed_edge_angle=worst,volume=part.volume,result='PASS')


@pytest.mark.parametrize('pin_units,units', [(5,1),(15,5),(18,6),(27,9)])
def test_rack10_rail_strip_hole_and_peg_layout(pin_units, units):
    centres = rail_hole_centres(pin_units)
    length = pin_units * 15
    datum = (length-units*44.45)/2
    assert len(centres) == 3*units
    assert [y for x,y in centres[:3]] == pytest.approx([datum+6.35, datum+22.225, datum+38.1])
    assert centres[-1][1] == pytest.approx(length-centres[0][1])
    # Place the left outer edge at -15 and the mirrored right edge at 270.
    left = -15+centres[0][0]
    right = 270-centres[0][0]
    assert right-left == pytest.approx(236.525)
    assert 255-2*c.RAIL_FLANGE >= c.CLEAR_OPENING
    assert peg_stations(pin_units) == [7.5+15*k for k in range(1,pin_units-1)]
    assert centres[0][0]-4-c.SLEEVE_RELIEF_W >= 3
    assert centres[0][0]-4-(7.5+1.9) >= 2


@pytest.mark.parametrize('pin_units,thickness', [(5,11),(15,12),(18,14)])
def test_rack10_rail_strip_sleeves_and_through_insert(pin_units, thickness):
    length = 15*pin_units
    part = rail.build({'pin_units':pin_units, 'thickness':thickness})
    for y in (0,length-15):
        sleeve = Pos(-2.1,y,thickness-2.1)*Box(19.2,15,2.1,align=(Align.MIN,)*3)
        assert (part & sleeve).volume < 1e-6
    for x,y in rail_hole_centres(pin_units):
        assert not part.is_inside((x+3.99,y,4))
        assert part.is_inside((x+4.01,y,4))
        assert not part.is_inside((x+3.99,y,9.49))
        # 45° seat: radius 3.6 at z=9.9, followed by the Ø6.4 exit.
        assert not part.is_inside((x+3.59,y,9.9))
        assert part.is_inside((x+3.61,y,9.9))
        assert not part.is_inside((x+3.19,y,10.5))
        assert part.is_inside((x+3.21,y,10.5))
        assert not part.is_inside((x,y,thickness-.01))
        screw = Pos(x,y,-1)*Cylinder(3.2,thickness+2,
                                    align=(Align.CENTER,Align.CENTER,Align.MIN))
        assert (part & screw).volume < 1e-6
        assert c.RAIL_WIDTH-x-4 >= c.INSERT_WALL_MIN
    for y in peg_stations(pin_units):
        assert part.is_inside((7.5,y,thickness+10))
        assert part.is_inside((7.5+1.89,y,thickness+10))
        assert not part.is_inside((7.5+1.91,y,thickness+10))
    for y in (7.5,length-7.5):
        assert not part.is_inside((7.5,y,thickness+1))


@pytest.mark.parametrize('hole', ['insert','cage_nut'])
@pytest.mark.parametrize('mount', ['pegs','pin_holes'])
def test_rack10_rail_strip_coupon_modes(hole, mount):
    part = rail.build({'pin_units':5, 'hole':hole, 'mount':mount})
    assert part.is_valid and len(part.solids()) == 1
    for y in peg_stations(5):
        assert part.is_inside((7.5,y,6)) == (mount == 'pegs')
    if hole == 'cage_nut':
        x,y = rail_hole_centres(5)[1]
        assert not part.is_inside((x+4.75,y,1))
        assert part.is_inside((x+4.78,y,1))
        assert part.is_inside((x,y+5.2,1.99))
        assert not part.is_inside((x,y+5.2,2.01))


def test_rack10_rail_strip_rejects_bed_overflow():
    from rack10.rail_strip import rail_strip
    for units in (28, 29, 30):
        with pytest.raises(ValueError, match='bed limit.*segment at a connector sleeve'):
            rail_strip(units)
        with pytest.raises(ValueError, match='bed limit.*segment at a connector sleeve'):
            rail.build({'pin_units':units})
