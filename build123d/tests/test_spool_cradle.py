"""Spool contact, mount, load section and endpoint regressions for pst-ir0v."""
import math
import sys
from pathlib import Path

import pytest
import trimesh
from build123d import Align, Axis, Box, Compound, Cylinder, Plane, Pos, Rot, section
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Ax1, gp_Dir

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from holders.registry import all_models
all_models()  # Preserve the manifest emitter's registration order.
from holders.spool_cradle import (APEX_HEIGHT, MOUNT, PARAMS, SPEC, WEB, SEAT_Z, dimensions,
                                   holder, mount_fixtures)
from multibuild.constants import PITCH, large_hole_center, small_hole_center
from multibuild.multiconnect import POCKET_DEPTH
from scripts.export import export_stl
from tests.mount_contracts import verify
from tests.print_audit import audit


@pytest.fixture(scope='module')
def part():
    return holder()


def winding(p):
    return Pos(0,p['center_y'],p['center_z'])*Rot(0,90,0)*Cylinder(
        p['winding_radius'],p['spool_width']-2*p['flange_rim_width'])


def assert_contacts(part,p):
    assert part.distance_to(winding(p)) > 0.5
    # Both tangent lines must land on both flange rims in the finished BRep.
    # Just below is material, just above is air; no winding bears the load.
    land = min(WEB, p['flange_rim_width'])/2
    for sign in (-1,1):
        x = sign*(p['spool_width']/2-land)
        for y in (p['rear_y'],p['front_y']):
            assert part.is_inside((x,y,p['contact_z']-.01))
            assert not part.is_inside((x,y,p['contact_z']+.01))
    # Circular flange envelopes do not intersect the holder.
    for sign in (-1,1):
        flange=Pos(sign*(p['spool_width']/2-p['flange_rim_width']/2),
                   p['center_y'],p['center_z'])*Rot(0,90,0)*Cylinder(
                       p['radius'],p['flange_rim_width'])
        overlap = part & flange
        assert overlap is None or abs(overlap.volume) < 1e-5
    # Projected COM lies inside the support footprint in both horizontal axes.
    bb=part.bounding_box()
    for center,lo,hi in ((0,bb.min.X,bb.max.X),
                         (p['center_y'],bb.min.Y,bb.max.Y)):
        assert min(center-lo,hi-center) >= .15*(hi-lo)
    assert p['center_y']-p['radius']-p['plate_thickness'] >= 3-1e-8


def test_registered_default(part):
    assert SPEC in all_models()
    assert SPEC.print_orientation == (0,0,1)
    assert SPEC.mounts == (MOUNT,)
    assert [p.id for p in SPEC.presets] == ['bambu_reusable_200','ams_generic_200']
    assert not {'slot_count','slot_travel','snap_notches','pitch'} & SPEC.param_names()
    assert_contacts(part,dimensions())


@pytest.mark.parametrize('preset',SPEC.presets,ids=lambda p:p.id)
def test_presets_mesh_and_envelope(preset,tmp_path):
    p=dimensions(preset.values)
    part=holder(**preset.values)
    assert part.is_valid and len(part.solids()) == 1
    path=tmp_path/'spool.stl'
    export_stl(part,path)
    mesh=trimesh.load_mesh(path)
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert len(mesh.split()) == 1
    bb=part.bounding_box()
    assert bb.size.X == pytest.approx(p['plate_width'])
    assert bb.min.Z == pytest.approx(0,abs=1e-6)
    assert bb.size.X < 340 and bb.size.Y < 320 and bb.size.Z < 340
    assert_contacts(part,p)


CASES=[({q.name:v},f'{q.name}={v}') for q in PARAMS for v in (q.min,q.max)]
CASES += [({'spool_width':70,'plate_width':68,'flange_rim_width':1.5,
            'flange_height':4,'spool_diameter':205,'cradle_angle':25,'lip_height':0},
           'narrow-plate-wide-spool')]


@pytest.mark.parametrize('values',[v for v,_ in CASES],ids=[n for _,n in CASES])
def test_endpoints(values):
    p=dimensions(values)
    part=holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    assert p['plate_thickness']-POCKET_DEPTH >= 2.4
    assert_contacts(part,p)
    # The V waist, rather than the tall root, controls arm bending.
    waist_s=2*WEB*(APEX_HEIGHT-.8)**2/6
    assert 30*(p['front_y']-p['center_y'])/waist_s < 45/3
    # Inspect a section away from ribs/blends: both webs are perimeters only.
    y=p['center_y']
    cross=section(part,section_by=Plane(origin=(0,y,0),x_dir=(1,0,0),z_dir=(0,1,0)))
    assert len(cross.faces()) == 2
    for f in cross.faces():
        assert 1.6 <= f.bounding_box().size.X <= 2.4+1e-6
        assert f.bounding_box().size.Z == pytest.approx(APEX_HEIGHT)


@pytest.mark.parametrize('param',PARAMS,ids=lambda p:p.name)
def test_reject_out_of_range(param):
    for v in (param.min-.1,param.max+.1,float('nan'),float('inf')):
        with pytest.raises(ValueError): holder(**{param.name:v})


@pytest.mark.parametrize('cadence',(75,100))
def test_three_holder_alignment(part,cadence):
    # Z translation seats the local 24 mm row on a 12.5+25j large-hole row.
    origin_x,_=small_hole_center(0,0)
    _,seat_z=large_hole_center(0,1)
    placed=[Pos(origin_x+i*cadence,0,seat_z-SEAT_Z)*part for i in range(3)]
    gaps=[]
    for a,b in zip(placed,placed[1:]):
        overlap = a & b
        assert overlap is None or abs(overlap.volume) < 1e-6
        gaps.append(b.bounding_box().min.X-a.bounding_box().max.X)
    assert gaps == pytest.approx([cadence-70]*2)
    for i in range(3):
        for seat in mount_fixtures(MOUNT,{}).seat_locs:
            x=seat.position.X+origin_x+i*cadence
            assert (x,seat_z) == pytest.approx(large_hole_center(round((x-12.5)/PITCH),1))


def test_mount_contract_and_backing():
    # Exactly the approved mount range; simultaneous entry along two channels.
    for values in ({},{'plate_width':68,'plate_thickness':6.6}):
        fx=mount_fixtures(MOUNT,values)
        assert len(fx.cutters) == len(fx.seat_locs) == 2
        assert [s.position.X for s in fx.seat_locs] == [-12.5,12.5]
        assert [s.position.Z for s in fx.seat_locs] == [24,24]
        verify(SPEC,MOUNT,SPEC.resolve_values(values))


def test_actual_root_section_modulus(part):
    p=dimensions()
    # Y=t+2 avoids the R1 blend: the two real web sections carry bending
    # about X. OCP area inertia includes the final bed chamfers.
    y=p['plate_thickness']+2
    cross=section(part,section_by=Plane(origin=(0,y,0),x_dir=(1,0,0),z_dir=(0,1,0)))
    cross=Compound(children=[f for f in cross.faces()
                    if abs(f.center().X) > p['root_inner']-1])
    assert len(cross.faces()) == 2
    props=GProp_GProps()
    BRepGProp.SurfaceProperties_s(cross.wrapped,props)
    center=props.CentreOfMass()
    inertia=props.MomentOfInertia(gp_Ax1(center,gp_Dir(1,0,0)))
    bb=cross.bounding_box()
    modulus=inertia/max(center.Z()-bb.min.Z,bb.max.Z-center.Z())
    # Conservative rectangular core wholly inside the chamfered section.
    h=p['root_height']-2/math.tan(math.radians(p['cradle_angle']))-.8
    core_modulus=2*WEB*h*h/6
    assert modulus >= core_modulus
    assert 30*(p['front_y']-y)/core_modulus < 45/3
    assert 15000 < modulus < 16000


def test_production_print_audit(part):
    fx=mount_fixtures(MOUNT,{})
    report=audit(part,SPEC.print_orientation,cutters=fx.cutters,model=SPEC.name)
    print(report.format())
    assert report.ok,report.format()
    assert report.bed_chamfer == 'present'
    # No broader bespoke exclusions; only the two registered library pockets.
    assert len(fx.cutters) == 2


@pytest.mark.parametrize('values', ({}, {'plate_width':68,'plate_thickness':6.6,
    'spool_diameter':205,'wall_clearance':6,'cradle_angle':25}))
def test_plate_shell_and_rib_section(values):
    p=dimensions(values)
    part=holder(**values)
    t=p['plate_thickness']
    w=p['plate_width']
    # Non-overlapping conservative rectangles in the actual XY section at
    # the seat. Whole cutter envelopes are omitted from the rear skin.
    # No infill is counted; the two 2.4 mm ribs are solid perimeters.
    rectangles=[] # x0,x1,y0,y1
    for lo,hi in ((-w/2+.5,-22.65),(-2.35,2.35),(22.65,w/2-.5)):
        rectangles.append((lo,hi,0,1.2))
    rectangles.append((-w/2+.5,w/2-.5,t-1.2,t))
    for lo,hi in ((-w/2,-w/2+1.2),(w/2-1.2,w/2)):
        rectangles.append((lo,hi,1.2,t-1.2))
    for x in (-12.5,12.5):
        rectangles.append((x-1.2,x+1.2,t,t+14.5))
    for x0,x1,y0,y1 in rectangles:
        probe=Pos(x0,y0,SEAT_Z)*Box(x1-x0,y1-y0,.1,
                align=(Align.MIN,Align.MIN,Align.MIN))
        residual=probe-part
        assert residual is None or residual.volume < 1e-6
    area=sum((x1-x0)*(y1-y0) for x0,x1,y0,y1 in rectangles)
    centroid=sum((x1-x0)*(y1-y0)*(y0+y1)/2
                 for x0,x1,y0,y1 in rectangles)/area
    inertia=sum((x1-x0)*(y1-y0)**3/12 +
                (x1-x0)*(y1-y0)*((y0+y1)/2-centroid)**2
                for x0,x1,y0,y1 in rectangles)
    # Use the ACTUAL outermost fibre, including the last 0.5 mm of rib tip
    # not counted in the conservative moment of inertia.
    modulus=inertia/max(centroid,t+15-centroid)
    stress=30*p['front_y']/modulus
    print('plate',values,'S=',modulus,'stress=',stress)
    assert modulus > 425
    assert stress < 45/3


def test_bed_edges_and_edge_classes(part):
    p=dimensions()
    # Final BRep classes: functional slot/contact edges, R1 junctions,
    # eased exterior edges, and edges between coplanar/tangent faces.
    counts={'mount':0,'contact':0,'blend':0,'internal_cap':0,'eased':0,'tangent':0}
    cutters=[c.bounding_box() for c in mount_fixtures(MOUNT,{}).cutters]
    adjacency={}
    for f in part.faces():
        for e in f.edges(): adjacency.setdefault(e,[]).append(f)
    bed=part.faces().filter_by(Axis.Z).sort_by(Axis.Z)[0]
    for e in bed.edges():
        other=[f for f in adjacency[e] if f != bed]
        assert len(other) == 1
        assert other[0].normal_at(e.center()).Z == pytest.approx(-math.sqrt(.5),abs=1e-4)
    for e,faces in adjacency.items():
        assert len(faces) == 2
        c=e.center()
        if any(b.min.X-.5 <= c.X <= b.max.X+.5 and
               b.min.Y-.5 <= c.Y <= b.max.Y+.5 and
               b.min.Z-.5 <= c.Z <= b.max.Z+.5 for b in cutters):
            counts['mount']+=1
            continue
        # The untouched tangent planes are the reason these edges are sharp.
        if abs(c.Z-(APEX_HEIGHT+abs(c.Y-p['center_y'])/math.tan(math.radians(p['cradle_angle'])))) < 1e-5:
            counts['contact']+=1
            continue
        if any(f.geom_type.name == 'CYLINDER' for f in faces):
            counts['blend']+=1
            continue
        # Concave cap-to-web boundaries terminate the vertical R1 rib
        # blends. These are interior structural corners, not outer rims.
        rib_ys=(p['center_y']-35,p['center_y']+35)
        if abs(abs(c.X)-p['rail_inner']) < 1e-6 and any(
                abs(c.Y-y) <= WEB/2+1 and
                abs(c.Z-(APEX_HEIGHT+abs(y-p['center_y'])/math.tan(math.radians(p['cradle_angle']))-12)) <= 1.5+1e-6
                for y in rib_ys):
            counts['internal_cap']+=1
            continue
        normals=[f.normal_at(c) for f in faces]
        cosine=max(-1,min(1,normals[0].dot(normals[1])))
        angle=math.degrees(math.acos(cosine))
        if angle < 1e-3:
            counts['tangent']+=1
        else:
            assert angle < 90-1e-3, (tuple(c),angle)
            counts['eased']+=1
    assert all(counts[k] > 0 for k in ('mount','contact','blend','eased'))
