"""Device envelope, cooling, load proxy and production endpoint contracts."""
import pytest
from tests.audit_tiers import audit_cases
import trimesh
from build123d import Align, Box, Pos
from holders import rack10_cradle, rack10_shelf, rack10_hub_tray, rack10_ears
from rack10 import constants as c
from rack10.tray import TrayFitError, tray_dimensions
from rack10.shelf import shelf_dimensions, beam_deflections, longitudinal_sections, DECK_TOP
from scripts.export import export_stl
from tests.audit_record import record
from tests.print_audit import audit
from math import acos,degrees
from OCP.BRep import BRep_Tool
from rack10.device_ribs import tie_edge
from rack10 import stiffness
from rack10.cradle import FLOOR_TOP as CRADLE_FLOOR, RAIL_TOP as CRADLE_RAIL
from rack10.ears import FLOOR_TOP as CLAMP_FLOOR, RAIL_TOP as CLAMP_RAIL
from rack10.hub_tray import FLOOR_TOP as HUB_FLOOR, RAIL_TOP as HUB_RAIL


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
        q=edge.center();n0,n1=(f.normal_at(q) for f in faces)
        # Functional 45-degree ceiling ridge of a peaked aperture. It must
        # remain exact; chamfering it creates a horizontal unsupported roof.
        if n0.X*n1.X<0 and all(abs(n.Y)<1e-6 and abs(n.Z+2**-.5)<1e-6 for n in (n0,n1)):
            assert abs(n0.X+n1.X)<1e-6
            continue
        if spec is rack10_ears.SPEC and tie_edge(edge,v['device_w'],v['device_d'],CLAMP_FLOOR): continue
        angle=degrees(acos(max(-1,min(1,n0.dot(n1)))))
        assert angle<90-1e-3,(tuple(q),angle)
        worst=max(worst,angle)
    return worst

SPECS=(rack10_cradle.SPEC,rack10_shelf.SPEC,rack10_hub_tray.SPEC,rack10_ears.SPEC)
PRESETS=[(s,p) for s in SPECS for p in s.presets]
CASES=[(s,p.values,p.id) for s,p in PRESETS]
for s in SPECS:
    for p in s.params:
        if p.kind in ('number','integer'):
            for v in (p.min,p.max): CASES.append((s,{p.name:v},f'{p.name}-{v}'))
CASES += [(rack10_cradle.SPEC,dict(device_w=200,device_d=200,device_h=152,clearance=2,slot_mm=8),'max-corner'),
          (rack10_shelf.SPEC,dict(device_w=217,device_d=220,side_stops=False,slot_mm=8),'max-no-stops'),
          (rack10_shelf.SPEC,dict(device_w=100,device_d=100,device_h=20,side_stops=True,slot_mm=8),'min-stops'),
          (rack10_ears.SPEC,dict(device_w=210,device_d=200,device_h=60,clearance=2,slot_mm=8),'wide-clamp'),
          (rack10_hub_tray.SPEC,dict(left_w=40,left_d=40,right_w=40,right_d=40,slot_mm=8),'min-pockets')]
CASES += [(rack10_cradle.SPEC,dict(device_w=140,device_d=200,clearance=1,slot_mm=8),'narrow-deep'),
          (rack10_cradle.SPEC,dict(device_w=200,device_d=200,clearance=1,slot_mm=8),'wide-min-clearance'),
          (rack10_ears.SPEC,dict(device_w=140,device_d=200,clearance=2,slot_mm=8),'narrow-deep'),
          (rack10_hub_tray.SPEC,dict(left_w=105,left_d=110,right_w=40,right_d=40,slot_mm=8),'left-heavy-corner'),
          (rack10_hub_tray.SPEC,dict(left_w=40,left_d=40,right_w=110,right_d=110,slot_mm=8),'right-heavy-corner'),
          (rack10_hub_tray.SPEC,dict(left_w=100,left_d=110,right_w=105,right_d=110,slot_mm=8),'deep-pockets')]
CASES += [(rack10_hub_tray.SPEC,dict(left_w=w,left_d=110,right_w=105,right_d=110,slot_mm=8),f'notch-root-{w}')
          for w in (86,90)]


def stiffness_cases(spec,v):
    if spec is rack10_cradle.SPEC:
        return [stiffness.cradle_case(v['device_w'],v['device_d'],v['clearance'],CRADLE_FLOOR,CRADLE_RAIL)]
    if spec is rack10_ears.SPEC:
        return [stiffness.clamp_case(v['device_w'],v['device_d'],v['clearance'],CLAMP_FLOOR,CLAMP_RAIL)]
    if spec is rack10_hub_tray.SPEC:
        return list(stiffness.hub_cases(v['left_w'],v['left_d'],v['right_w'],v['right_d'],HUB_FLOOR,HUB_RAIL))
    return []


def assert_device_load_paths(part,spec,v):
    cases=stiffness_cases(spec,v)
    worst={}
    longitudinal=[]
    for case in cases:
        sections,cross,loads,depth,span=case
        if spec is rack10_hub_tray.SPEC:
            assert sections[0].width>=1.6 and 2*sections[1].width>=1.6
        else:
            assert all(b.width>=1.6 for b in sections)
        assert all(b.height>=1.6 for b in sections+cross)
        longitudinal.extend(sections)
        for b in sections+cross:
            assert min(b.width,b.height,b.length)>0
            probe=Pos(b.x,b.y,b.z)*Box(b.width,b.height,b.length,align=(Align.CENTER,Align.MIN,Align.MIN))
            actual=(part & probe).volume
            assert actual==pytest.approx(probe.volume,abs=1e-5),(spec.name,b,actual,probe.volume)
        for name,modulus in (('petg',stiffness.PETG_MPA),('pctg',stiffness.PCTG_MPA)):
            result=stiffness.evaluate(case,modulus,hub=spec is rack10_hub_tray.SPEC)
            assert max(result.values())<=1,(spec.name,v,result)
            assert result['tip']>=result['rear_contact']
            for key,value in result.items(): worst[f'{name}_{key}']=max(worst.get(f'{name}_{key}',0),value)
    # All counted longitudinal material is disjoint, including the two
    # allocations of the hubs' shared divider; no double-crediting its I.
    for i,a in enumerate(longitudinal):
        for b in longitudinal[i+1:]:
            overlap_x=min(a.x+a.width/2,b.x+b.width/2)-max(a.x-a.width/2,b.x-b.width/2)
            overlap_y=min(a.y+a.height,b.y+b.height)-max(a.y,b.y)
            assert overlap_x<1e-7 or overlap_y<1e-7
    return worst


def test_stiffness_loads_and_elastic_scaling():
    assert (stiffness.STEAM_MACHINE_KG,stiffness.USW_LITE_16_KG,stiffness.LUTRON_DESIGN_KG,stiffness.AQARA_DESIGN_KG)==(2.6,1.2,.5,.5)
    for mass in (2.6,1.2,.5):
        loads=stiffness.reactions(mass,5,205,105)
        assert [p for p,a in loads]==pytest.approx([mass*9.81/2]*2)
        assert sum(p*a for p,a in loads)==pytest.approx(mass*9.81*105)
    beam=stiffness.Beam(0,0,0,10,10,100)
    assert stiffness.inertia([beam])==pytest.approx(10**4/12)
    assert stiffness.deflections([beam],[(1,100)],100,2000)['tip']==pytest.approx(100**3/(3*2000*(10**4/12)))
    with pytest.raises(ValueError): stiffness.reactions(1,10,5,7)
    with pytest.raises(ValueError): stiffness.deflections([beam],[(1,100)],99,2000)
    with pytest.raises(ValueError): stiffness.deflections([beam],[(1,100)],100,0)


def test_stiffness_dimension_corners():
    # Full width/depth/clearance corner product, including the easily missed
    # narrow/deep case; BREP proofs run separately at production endpoints.
    for w in (140,156,200):
        for d in (140,162.4,200):
            for clearance in (1,2):
                case=stiffness.cradle_case(w,d,clearance,CRADLE_FLOOR,CRADLE_RAIL)
                assert max(stiffness.evaluate(case,stiffness.PCTG_MPA).values())<=1
    for w in (140,192,210):
        for d in (100,185,200):
            for clearance in (1,2):
                case=stiffness.clamp_case(w,d,clearance,CLAMP_FLOOR,CLAMP_RAIL)
                assert max(stiffness.evaluate(case,stiffness.PCTG_MPA).values())<=1
    for lw in (40,70,105):
        for rw in (40,105,110):
            for ld in (40,70,110):
                for rd in (40,105,110):
                    for case in stiffness.hub_cases(lw,ld,rw,rd,HUB_FLOOR,HUB_RAIL):
                        assert max(stiffness.evaluate(case,stiffness.PCTG_MPA,hub=True).values())<=1


def test_sonos_fit_and_cradle_clearance():
    with pytest.raises(TrayFitError,match='tray fit'):
        tray_dimensions(217,217,64,2,1)
    assert shelf_dimensions(217,217,64)['width'] >= 217
    assert tray_dimensions(156,162.4,152,4,2)['inner_width']==160
    with pytest.raises(TrayFitError,match='clamp clearance'):
        rack10_ears.ears(clearance=.5)


def test_shelf_both_load_cases():
    for width in (100,180,217):
        for depth in (100,217,220):
            for stops in (False,True):
                d=shelf_dimensions(width,depth,64,stops)
                result=beam_deflections(device_w=width,device_d=depth,
                                        deck_width=d['width'],deck_depth=d['depth'])
                assert max(result.values())<=1
                assert result['cantilever']>result['rear_pad']
    sonos=beam_deflections(device_w=217,device_d=217,deck_width=222.2,deck_depth=236)
    assert sonos['rear_pad']==pytest.approx(.835042021376)
    assert sonos['cantilever']==pytest.approx(.921034539132)
    with pytest.raises(ValueError,match='deck_depth'):
        beam_deflections(device_w=217,device_d=217,deck_width=222.2,deck_depth=217)


def assert_shelf_load_paths(part,v):
    """Pin every actual solid rectangle counted by the beam calculation."""
    d=shelf_dimensions(v['device_w'],v['device_d'],v['device_h'],v['side_stops'])
    height=DECK_TOP-.6
    for z in (3,d['depth']-30):
        beam=Pos(0,.3,z)*Box(d['width']-.6,height,20,align=(Align.CENTER,Align.MIN,Align.MIN))
        assert (part & beam).volume==pytest.approx(beam.volume,abs=1e-5)
    sections=longitudinal_sections(v['device_w'],d['width'])
    assert len(sections)==int((v['device_w']-24)//10)+1
    intervals=sorted((x-w/2,x+w/2) for x,w in sections)
    assert all(a[1]<b[0] for a,b in zip(intervals,intervals[1:])), 'do not count material twice'
    for x,width in sections:
        beam=Pos(x,.3,3)*Box(width,height,d['depth']-13,align=(Align.CENTER,Align.MIN,Align.MIN))
        assert (part & beam).volume==pytest.approx(beam.volume,abs=1e-5)


def device_envelopes(spec,v):
    if spec is rack10_hub_tray.SPEC:
        inner=v['left_w']+v['right_w']+4+c.RAIL_WALL
        for x,w,d,h in ((-inner/2+(v['left_w']+2)/2,v['left_w'],v['left_d'],30.23),
                        (inner/2-(v['right_w']+2)/2,v['right_w'],v['right_d'],36.5)):
            yield Pos(x,HUB_FLOOR,4)*Box(w,h,d,align=(Align.CENTER,Align.MIN,Align.MIN))
    else:
        y=DECK_TOP+1 if spec is rack10_shelf.SPEC else (CRADLE_FLOOR+1 if spec is rack10_cradle.SPEC else CLAMP_FLOOR)
        z=5 if spec is rack10_shelf.SPEC else 3+v['clearance']
        yield Pos(0,y,z)*Box(v['device_w'],v['device_h'],v['device_d'],align=(Align.CENTER,Align.MIN,Align.MIN))


@pytest.mark.parametrize('spec,preset',PRESETS,ids=[f'{s.name}-{p.id}' for s,p in PRESETS])
def test_preset_topology_envelope_and_bed(spec,preset,tmp_path):
    v=spec.resolve_values(preset.values)
    part=spec.build(v)
    assert part.is_valid and len(part.solids())==1
    b=part.bounding_box().size
    assert b.X<=305 and b.Y<=320 and b.Z<=320
    for device in device_envelopes(spec,v):
        assert (part & device).volume<1e-6
    export_stl(part,tmp_path/'part.stl')
    assert trimesh.load_mesh(tmp_path/'part.stl').is_watertight
    if spec is rack10_cradle.SPEC:
        # Actual open fraction under the device, including pads/notch and
        # excluding chamfer entrance inflation, via the middle floor slice.
        slab=Pos(0,CRADLE_FLOOR/2-.1,3+v['clearance'])*Box(v['device_w'],.2,v['device_d'],align=(Align.CENTER,Align.MIN,Align.MIN))
        assert 1-(part & slab).volume/slab.volume>=.4


@pytest.mark.audit
@pytest.mark.parametrize('spec,values,case',CASES,ids=[f'{s.name}-{n}' for s,v,n in CASES])
@audit_cases(lambda p: p['spec'])
def test_endpoint_audit_and_edges(spec,values,case):
    try:
        part=spec.build(values)
    except TrayFitError as e:
        # Only these genuinely unbuildable domain corners are allowed.
        assert (spec is rack10_cradle.SPEC and values=={'units':3}) or (spec is rack10_ears.SPEC and values=={'units':1}) or (spec is rack10_hub_tray.SPEC and values=={'left_w':105})
        record(f'{spec.name}-{case}',result='REJECT',reason=str(e))
        return
    v=spec.resolve_values(values)
    for device in device_envelopes(spec,v): assert (part & device).volume<1e-6
    if spec is rack10_shelf.SPEC: assert_shelf_load_paths(part,v)
    sag=assert_device_load_paths(part,spec,v)
    report=audit(part,model=spec.name)
    assert report.ok,report.format()
    worst=assert_finished_edges(part,spec,values)
    record(f'{spec.name}-{case}',min_wall=report.min_wall_mm,worst_overhang=report.max_overhang_deg,
           exposed_edge_angle=worst,volume=part.volume,result='PASS',**sag)
    print(f'RACK10 DEVICE | {spec.name}/{case} | wall {report.min_wall_mm:.3f} | overhang {report.max_overhang_deg:.1f} | edges {worst:.1f} | volume {part.volume:.3f} | PASS')
