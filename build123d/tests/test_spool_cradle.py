"""Spool contact, placement aids, mount and print regressions (pst-tskv)."""
import math
import re
import sys
from pathlib import Path

import pytest
import trimesh
from build123d import Axis, Box, Cylinder, Plane, Pos, Rot, section

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from holders.registry import all_models
all_models()  # Preserve the manifest emitter's registration order.
from holders.spool_cradle import (APEX_HEIGHT, FP_MOUNT, MOUNT, OC_MOUNT, OC_SLOT_TOP, PARAMS,
                                   POINT_ROW_SPACING, SPEC, WEB, CHORD, check_plate,
                                   dimensions, holder, mount_fixtures, mount_for_values,
                                   point_seats, truss_openings)
from multibuild.constants import PITCH, large_hole_center, small_hole_center
from multibuild import fixpoint as fp
from multibuild.multiconnect import POCKET_DEPTH
from openconnect import constants as oc
from openconnect.slot import slot_cutter
from scripts.export import export_stl
from tests.mount_contracts import verify
from tests import print_audit as pa
from tests.print_audit import audit


@pytest.fixture(scope='module')
def part():
    return holder()


def winding(p):
    return Pos(0,p['center_y'],p['center_z'])*Rot(0,90,0)*Cylinder(
        p['winding_radius'],p['spool_width']-2*p['flange_rim_width'])


def assert_contacts(part,p):
    assert part.distance_to(winding(p)) > 0.5
    # The analytic saddle is R + clearance at each angular sample, on
    # both rim lands. Probe the finished BRep on either side of its surface.
    land = min(WEB, p['flange_rim_width'])/2
    for sign in (-1,1):
        x = sign*(p['spool_width']/2-land)
        for fraction in (-.9, -.5, 0, .5, .9):
            theta = fraction*(math.pi/2-math.radians(p['cradle_angle']))
            y = p['center_y']+p['saddle_radius']*math.sin(theta)
            z = p['center_z']-p['saddle_radius']*math.cos(theta)
            assert part.is_inside((x,y,z-.01))
            assert not part.is_inside((x,y,z+.01))
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
    assert SPEC.mounts == (MOUNT, OC_MOUNT, FP_MOUNT)
    assert [p.id for p in SPEC.presets] == ['bambu_reusable_200','ams_generic_200',
                                            'bambu_reusable_200_points','ams_generic_200_points',
                                            'bambu_reusable_200_openconnect',
                                            'ams_generic_200_openconnect']
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
    assert bb.size.X == pytest.approx(p['cadence']-2*p['guide_gap'])
    assert bb.min.Z == pytest.approx(0,abs=1e-6)
    assert bb.size.X < 340 and bb.size.Y < 320 and bb.size.Z < 340
    assert_contacts(part,p)


NUMERIC=[q for q in PARAMS if q.kind == 'number']
STYLE=next(q for q in PARAMS if q.name == 'mount_style')
# Param endpoints at the default style. The plate ranges cover every style,
# so the cells below a Multiboard style's floor are EXPECTED-INVALID there:
# they must raise, and are swept valid under openconnect instead.
ENDPOINTS=[{q.name:v} for q in NUMERIC for v in (q.min,q.max)]
STYLE_INVALID=[v for v in ENDPOINTS if v in ({'plate_width':82},{'plate_thickness':5.1})]
CASES=[(v,'-'.join(f'{k}={x}' for k,x in v.items())) for v in ENDPOINTS if v not in STYLE_INVALID]
CASES += [({STYLE.name:v},f'{STYLE.name}={v}') for v in STYLE.choices]
CASES += [({**v,'mount_style':'openconnect'},f'openconnect-{k}={x}')
          for v in ENDPOINTS for k,x in v.items() if k.startswith('plate_')]
CASES += [({'spool_width':70,'plate_width':68,'flange_rim_width':1.5,
            'flange_height':4,'spool_diameter':205,'cradle_angle':25,'lip_height':0},
           'narrow-plate-wide-spool')]


def test_style_invalid_endpoints_are_rejected():
    assert len(STYLE_INVALID) == 2
    for values in STYLE_INVALID:
        with pytest.raises(ValueError, match="mount_style='channel' needs plate_"):
            dimensions(values)


@pytest.mark.parametrize('values',[v for v,_ in CASES],ids=[n for _,n in CASES])
def test_endpoints(values):
    p=dimensions(values)
    part=holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    assert p['plate_thickness']-p['pocket_depth'] >= 2.4-1e-9
    assert_contacts(part,p)
    assert_truss_sections(part,p)
    assert_cadence(part,p)


@pytest.mark.parametrize('param',NUMERIC,ids=lambda p:p.name)
def test_reject_out_of_range(param):
    for v in (param.min-.1,param.max+.1,float('nan'),float('inf')):
        with pytest.raises(ValueError): holder(**{param.name:v})


def test_reject_unknown_mount_style():
    for v in ('channels','point','',None,1):
        with pytest.raises(ValueError): holder(mount_style=v)


@pytest.mark.parametrize('cadence',(75,100))
def test_three_holder_channel_alignment(part,cadence):
    p=dimensions()
    origin_x,_=small_hole_center(0,0)
    offset_z=12.5-p['seat_rows'][0]
    placed=[Pos(origin_x+i*cadence,0,offset_z)*part for i in range(3)]
    assert part.bounding_box().size.X <= p['cadence']-1+1e-6
    gaps=[]
    rows=[]
    for a,b in zip(placed,placed[1:]):
        overlap = a & b
        assert overlap is None or abs(overlap.volume) < 1e-6
        gaps.append(b.bounding_box().min.X-a.bounding_box().max.X)
    assert gaps == pytest.approx([cadence-part.bounding_box().size.X]*2)
    for i in range(3):
        fx=mount_fixtures(MOUNT,{})
        rows.append([r.position.Z+offset_z for r in fx.onramp_locs])
        for seat in fx.seat_locs:
            x=seat.position.X+origin_x+i*cadence
            z=seat.position.Z+offset_z
            assert (x,z) == pytest.approx(large_hole_center(round((x-12.5)/PITCH),round((z-12.5)/PITCH)))
    assert rows[0] == rows[1] == rows[2]


@pytest.mark.parametrize('values',[p.values for p in SPEC.presets]+[
    {'plate_width':68,'plate_thickness':6.6},
    {'plate_width':68,'plate_thickness':6.6,'mount_style':'points'},
    {'plate_width':70,'plate_thickness':5.6,'mount_style':'points'},
    {'plate_width':82,'plate_thickness':5.1,'mount_style':'openconnect'}])
def test_mount_contract_and_backing(values):
    p=dimensions(values)
    mount=mount_for_values(p)
    absent=[m for m in SPEC.mounts if m != mount]
    assert all(mount_fixtures(m,values) is None for m in absent)
    fx=mount_fixtures(mount,values)
    if p['mount_style'] == 'channel':
        assert len(fx.cutters) == 2
        assert len(fx.seat_locs) == 2*len(p['seat_rows'])
    else:
        assert len(fx.cutters) == len(fx.seat_locs) == len(fx.onramp_locs) == 4
    assert p['plate_height']-p['channel_length'] == pytest.approx(p['plate_thickness']-p['pocket_depth'])
    assert p['plate_thickness']-p['pocket_depth'] >= 2.4-1e-9
    # Registered contract probes every actual pocket-back face locally,
    # every entry/drop, the entire low-to-high path, retention and closed top.
    assert verify(SPEC,mount,SPEC.resolve_values(values))
    assert not any(verify(SPEC,m,SPEC.resolve_values(values)) for m in absent)


def assert_truss_sections(part,p):
    # Measured sections through every opening: two bottom chords plus two
    # upper load members. Use their actual chamfered area, conservatively
    # projected by 45 degrees for the inclined tension/compression members.
    span=p['front_y']-p['plate_thickness']
    force=15*math.hypot(span,p['contact_z'])/p['contact_z']
    areas=[]
    for tri in truss_openings(p):
        y=tri[2][0]
        cross=section(part,section_by=Plane(origin=(0,y,0),x_dir=(1,0,0),z_dir=(0,1,0)))
        assert len(cross.faces()) == 4
        for face in cross.faces():
            assert 1.6 <= face.bounding_box().size.X <= p['rail_width']+p['guide_reach']+1e-6
            area=face.area/math.sqrt(2)
            assert force/area < 45/3
            areas.append(area)
    return force,min(areas)


@pytest.mark.parametrize('preset',SPEC.presets,ids=lambda p:p.id)
def test_truss_and_panel_hand_calc(preset):
    p=dimensions(preset.values)
    part=holder(**preset.values)
    force,area=assert_truss_sections(part,p)
    # Section normal to panel tension (X). The panel is distinct from both
    # flange webs at X=0; its complete actual cross-section carries spread.
    cross=section(part,section_by=Plane.YZ)
    panel=[f for f in cross.faces() if f.center().Y > p['end_y']-.1]
    assert len(panel)==1
    panel_area=panel[0].area
    spread=30/math.tan(math.radians(p['cradle_angle']))
    assert spread/panel_area < 45/3
    print(preset.id,'member force/area/stress',force,area,force/area,
          'panel force/area/stress',spread,panel_area,spread/panel_area)


# pst-dkqef: the unbacked rear knife read 0.70 mm here in both mount styles.
REAR_LAND_CORNER = dict(spool_width=66, saddle_clearance=.25, cradle_angle=25)
PRINT_CORNER = dict(spool_diameter=205, spool_width=70, flange_height=4,
                    flange_rim_width=1.5, cradle_angle=25, saddle_clearance=.25,
                    lip_height=15, plate_width=68, plate_thickness=6.6,
                    wall_clearance=6)


@pytest.mark.parametrize('values', [{}, SPEC.presets[0].values, PRINT_CORNER,
    dict(spool_width=50, guide_gap=.5, guide_height=12, rail_width=14, flange_height=4),
    dict(spool_width=70, guide_gap=2, guide_height=30, rail_width=14, flange_height=4),
    dict(spool_width=70, guide_gap=.5, guide_height=30, rail_width=6, saddle_clearance=1.5),
    REAR_LAND_CORNER],
    ids=['default', 'bambu-shallow-root', 'diagonal-root-corner',
         'maximum-reach-minimum-height', 'guides-omitted', 'insufficient-crest-room',
         'rear-land-corner'])
def test_production_print_audit(values):
    part=holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    assert_contacts(part, dimensions(values))
    fx=mount_fixtures(MOUNT,values)
    report=audit(part,SPEC.print_orientation,cutters=fx.cutters,model=SPEC.name)
    print(report.format())
    assert report.ok,report.format()
    assert report.bed_chamfer == 'present'
    # No broader bespoke exclusions; only the two registered library pockets.
    assert len(fx.cutters) == 2


def test_plate_shell_and_rib_section(part):
    p=dimensions()
    assert_truss_sections(part,p)
    # Front tie is a thin upright perimeter wall, continuous from the bed
    # to the contact height across the full spool width.
    for x in (-p['spool_width']/2+WEB/2,0,p['spool_width']/2-WEB/2):
        for z in (1,p['contact_z']/2,p['contact_z']-.5):
            assert part.is_inside((x,p['end_y']+WEB/2,z))
    cross=section(part,section_by=Plane.YZ)
    front=[f for f in cross.faces() if f.center().Y > p['end_y']-.1][0]
    assert front.bounding_box().size.Y == pytest.approx(WEB)
    assert front.bounding_box().size.Z >= p['contact_z']


def test_web_closure(part):
    p=dimensions()
    # Actual web section contains three closed triangular holes. Every hole
    # has a lower chord and two returning members, with no free profile end.
    cross=section(part,section_by=Plane(origin=(p['rail_inner']+WEB/2,0,0),x_dir=(0,1,0),z_dir=(1,0,0)))
    assert len(cross.faces())==1
    holes=cross.faces()[0].inner_wires()
    assert len(holes)==3
    for wire in holes:
        degree={}
        for edge in wire.edges():
            for vertex in edge.vertices():
                key=tuple(round(v,5) for v in vertex)
                degree[key]=degree.get(key,0)+1
        assert degree and set(degree.values())=={2}
    # Material immediately below every opening links both web ends to plate.
    for y in (p['plate_thickness']+1,p['center_y'],p['end_y']):
        assert part.is_inside((p['rail_inner']+WEB/2,y,CHORD/2))


def test_arc_contact(part):
    p=dimensions()
    assert p['saddle_radius']==p['radius']+p['saddle_clearance']
    assert_contacts(part,p)
    for x in (p['cap_inner']+.5, p['spool_width']/2-.5):
        for fraction in (-.8, 0, .8):
            theta = fraction*(math.pi/2-math.radians(p['cradle_angle']))
            y = p['center_y']+p['saddle_radius']*math.sin(theta)
            z = p['center_z']-p['saddle_radius']*math.cos(theta)
            for sign in (-1, 1):
                assert part.is_inside((sign*x,y,z-.01))
                assert not part.is_inside((sign*x,y,z+.01))


def test_no_bridge_over_10mm(part):
    p=dimensions()
    # A front wall is present at every height below the saddle. A tie only
    # at contact height would fail these probes and form a >60 mm bridge.
    for x in (-20,0,20):
        for z in (1,p['contact_z']/2):
            assert part.is_inside((x,p['end_y']+WEB/2,z))
    for triangle in truss_openings(p):
        a,b,c=triangle
        assert abs((c[1]-a[1])/(c[0]-a[0]))==pytest.approx(1)
        assert abs((c[1]-b[1])/(c[0]-b[0]))==pytest.approx(1)


def test_bed_edges_and_edge_classes(part):
    assert_finished_edges(part, dimensions())


def assert_finished_edges(part, p):
    # Final BRep classes: functional slot/contact edges, R1 junctions,
    # eased exterior edges, and edges between coplanar/tangent faces.
    counts={'mount':0,'contact':0,'blend':0,'internal_cap':0,'eased':0,'tangent':0}
    cutters=[c.bounding_box() for c in mount_fixtures(
        mount_for_values(p), {k: p[k] for k in SPEC.param_names()}).cutters]
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
        # Analytic circular saddle boundaries are functional rim contacts;
        # R1 cylinders are structural junction blends.
        if any(f.geom_type.name == 'CYLINDER' for f in faces):
            counts['blend']+=1
            continue
        # Straight saddle extensions at either end preserve the tangent lip
        # and root envelope. These terminate the functional contact profile.
        rear_z=p['contact_z']+(p['rear_y']-c.Y)/math.tan(math.radians(p['cradle_angle']))
        front_z=p['contact_z']+(c.Y-p['front_y'])/math.tan(math.radians(p['cradle_angle']))
        if ((c.Y <= p['rear_y'] and abs(c.Z-rear_z)<1e-5) or
            (p['front_y'] <= c.Y <= p['end_y'] and abs(c.Z-front_z)<1e-5)):
            counts['contact']+=1
            continue
        # Internal triangular corners preserve the specified 45-degree
        # ceilings. Their exterior rims are chamfered separately.
        if e.bounding_box().size.X > 1 and any(
                abs(c.Y-y)<1e-6 and abs(c.Z-z)<1e-6
                for triangle in truss_openings(p) for y,z in triangle):
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


def saddle_z(p, y):
    if y <= p['front_y']:
        return p['center_z']-math.sqrt(p['saddle_radius']**2-(y-p['center_y'])**2)
    return p['contact_z']+(p['panel_height']-p['contact_z'])*(y-p['front_y'])/(p['end_y']-p['front_y'])


PLACEMENT_CORNERS = [
    {},
    dict(spool_width=50, guide_gap=.5, guide_height=12, rail_width=14,
         flange_height=4, flange_rim_width=1.5),
    dict(spool_width=70, guide_gap=2, guide_height=30, rail_width=14,
         flange_height=4),
    dict(spool_width=70, guide_gap=.5, guide_height=30, rail_width=6,
         saddle_clearance=1.5),
]


def assert_cadence(part, p):
    width = part.bounding_box().size.X
    assert width <= p['cadence']-2*p['guide_gap']+1e-6
    assert width <= p['cadence']-1+1e-6
    if p['guide_enabled']:
        assert width == pytest.approx(p['cadence']-2*p['guide_gap'], abs=1e-6)


@pytest.mark.parametrize('values', PLACEMENT_CORNERS)
def test_guide_geometry(values):
    p = dimensions(values)
    model = holder(**values)
    assert model.is_valid and len(model.solids()) == 1
    assert_cadence(model, p)
    assert_contacts(model, p)
    assert math.degrees(math.atan(p['guide_reach']/p['guide_height'])) <= 45
    assert p['guide_enabled'] == (p['guide_reach']+1e-9 >= WEB+p['saddle_clearance'])
    y, z = p['center_y'], APEX_HEIGHT
    xw = p['spool_width']/2
    for sign in (-1, 1):
        if p['guide_enabled']:
            # The lead-in starts clear of the flange and rises outboard.
            foot = xw+p['saddle_clearance']
            for fraction in (.25, .5, .75):
                x = foot+(p['guide_outer']-WEB-.4-foot)*fraction
                top = z+p['guide_height']*fraction
                assert model.is_inside((sign*x, y, top-.05))
                assert not model.is_inside((sign*x, y, top+.05))
            for fraction in (.25, .5, .75):
                crest_x = p['guide_outer']-WEB*fraction
                assert model.is_inside((sign*crest_x,y,z+p['guide_height']-.05))
                assert not model.is_inside((sign*crest_x,y,z+p['guide_height']+.05))
            crest_point = (sign*(p['guide_outer']-WEB/2-.4), y, z+p['guide_height'])
            crest_faces = [f for f in model.faces() if f.is_inside(crest_point, tolerance=1e-5)]
            assert any(f.bounding_box().size.X >= WEB-1e-5 for f in crest_faces)
            assert not model.is_inside((sign*(xw+p['saddle_clearance']/2), y, z+.1))
        else:
            assert not model.is_inside((sign*(xw+.2), y, z+1))
            assert not model.is_inside((sign*(xw+.2), y, z-1))
    if not values:
        assert p['exposed_rim'] >= 20


@pytest.mark.parametrize('values', PLACEMENT_CORNERS)
def test_guide_underside_ramp(values):
    p = dimensions(values)
    if not p['guide_enabled']:
        return
    model = holder(**values)
    xw, reach = p['spool_width']/2, p['guide_reach']
    for y in (p['rear_y']+1, p['center_y'], p['end_y']-1):
        for fraction in (.25, .5, .75):
            x = xw+reach*fraction
            bottom = saddle_z(p,y)-reach+reach*fraction
            for sign in (-1, 1):
                assert model.is_inside((sign*x, y, bottom+.05))
                assert not model.is_inside((sign*x, y, bottom-.05))
                faces = [f for f in model.faces()
                         if f.is_inside((sign*x, y, bottom), tolerance=1e-5)]
                assert faces
                assert any(-math.sqrt(.5)-1e-5 <= f.normal_at((sign*x,y,bottom)).Z < 0
                           for f in faces)


@pytest.mark.parametrize('values', [{}, {'rail_width':14, 'spool_width':50, 'flange_height':4}])
def test_rail_cap_overhang(values):
    p = dimensions(values)
    model = holder(**values)
    y = p['center_y']
    for sign in (-1, 1):
        for reach in (.5, p['cap_reach']/2, p['cap_reach']-.5):
            x = p['cap_inner']+reach
            bottom = APEX_HEIGHT-WEB-reach
            assert model.is_inside((sign*x,y,APEX_HEIGHT-.05))
            assert not model.is_inside((sign*x,y,APEX_HEIGHT+.05))
            assert model.is_inside((sign*x,y,bottom+.05))
            assert not model.is_inside((sign*x,y,bottom-.05))
            faces = [f for f in model.faces()
                     if f.is_inside((sign*x,y,bottom), tolerance=1e-5)]
            assert any(f.normal_at((sign*x,y,bottom)).Z == pytest.approx(-math.sqrt(.5),abs=1e-5)
                       for f in faces)
        assert not model.is_inside((sign*(p['cap_inner']-.05),y,APEX_HEIGHT-.1))
    assert_contacts(model,p)


@pytest.mark.parametrize('values', PLACEMENT_CORNERS)
def test_overall_width_within_cadence(values):
    p = dimensions(values)
    assert_cadence(holder(**values), p)


@pytest.mark.parametrize('reach, enabled', [(2.9, True), (2.85, False), (3.0, True)])
def test_guide_threshold(reach, enabled):
    values = dict(spool_width=2*(dimensions()['cadence']/2-.5-reach))
    p = dimensions(values)
    assert p['guide_enabled'] is enabled
    model = holder(**values)
    assert model.is_valid and len(model.solids()) == 1
    assert_cadence(model, p)
    assert_contacts(model, p)
    assert_finished_edges(model, p)
    for sign in (-1, 1):
        if enabled:
            crest_point = (sign*(p['guide_outer']-1), p['center_y'],
                           APEX_HEIGHT+p['guide_height'])
            faces = [f for f in model.faces() if f.is_inside(crest_point, tolerance=1e-5)]
            assert any(f.bounding_box().size.X >= WEB-.6-1e-5 for f in faces)
        point = (sign*(p['guide_outer']-1), p['center_y'],
                 APEX_HEIGHT+p['guide_height']-1)
        assert model.is_inside(point) is enabled
    fx = mount_fixtures(MOUNT, values)
    report = audit(model, SPEC.print_orientation, cutters=fx.cutters, model=SPEC.name)
    assert report.ok, report.format()


@pytest.fixture(scope='module', params=[
    dict(spool_width=width, saddle_clearance=1.5, cradle_angle=angle)
    for width in (66, 50) for angle in (45, 25)
], ids=['narrow-45-reproducer', 'narrow-25', 'wide-45', 'wide-25'])
def max_clearance_guide(request):
    values = request.param
    return values, holder(**values)


def test_max_clearance_guide_corner(max_clearance_guide):
    values, model = max_clearance_guide
    p = dimensions(values)
    assert p['guide_enabled']
    assert model.is_valid and len(model.solids()) == 1
    assert_cadence(model, p)
    assert_contacts(model, p)
    assert_finished_edges(model, p)


# pst-7q2kz B1: shallow angles steepen the lip and saddle ends, and wide
# rails push the cap tail below the opening floors. Edge gate only; the
# max-clearance corners above carry the physical audit.
@pytest.mark.parametrize('values', [
    dict(spool_width=50, cradle_angle=25),
    dict(spool_width=70, cradle_angle=25),
    dict(spool_width=50, cradle_angle=45, rail_width=14),
    dict(spool_width=66, cradle_angle=25, rail_width=14),
    dict(spool_width=50, cradle_angle=25, flange_height=4, rail_width=14,
         saddle_clearance=1.5),
    REAR_LAND_CORNER,
    dict(spool_width=68, saddle_clearance=.25, cradle_angle=25),
    dict(spool_width=66, saddle_clearance=1.5, cradle_angle=45),
    dict(spool_width=50, saddle_clearance=.25, cradle_angle=45),
], ids=['wide-25', 'omitted-25', 'wide-45-rail14', 'narrow-25-rail14',
        'wide-25-rail14-min-flange', 'rear-land-lead-in', 'rear-land-narrow-v',
        'rear-land-vertical-lead-in', 'rear-land-wide-45'])
def test_shallow_angle_and_wide_rail_edges(values):
    model = holder(**values)
    assert model.is_valid and len(model.solids()) == 1
    assert_finished_edges(model, dimensions(values))


@pytest.mark.parametrize('values', [{}, REAR_LAND_CORNER], ids=['default', 'rear-land-corner'])
def test_outboard_rear_end_has_no_knife(values):
    # pst-dkqef: the print audit samples each face at UV 0.3/0.5/0.7 only,
    # so it saw the saddle's unbacked rear knife (~0.02 mm, including both
    # presets) only by luck. Probe a denser grid over the outboard rear end.
    p = dimensions(values)
    part = holder(**values)
    xw, rear, top = p['spool_width']/2, p['rear_y'], p['contact_z']
    lo, hi = (xw-.2, rear-.5, top-3), (p['guide_outer'], rear+2, top+.5)
    def near(b):
        return all(a <= y and x <= c for a, x, y, c in zip(lo, (b.min.X, b.min.Y, b.min.Z),
                                                            (b.max.X, b.max.Y, b.max.Z), hi))
    uv = tuple(i/10 for i in range(1, 10))
    thin = []
    for face in part.faces():
        if not near(face.bounding_box()):
            continue
        c, n = pa._outward_normal(part, face)
        for point, normal in pa._face_samples(face, uv):
            if not all(a <= v <= b for a, v, b in zip(lo, point, hi)):
                continue
            s = pa._signed(normal, n, face.normal_at(c))
            if part.is_inside(point-s*.02) and not part.is_inside(point-s*pa.MIN_WALL_MM):
                thin.append(tuple(round(v, 2) for v in point))
    assert not thin, thin[:5]


def test_max_clearance_guide_print_audit(max_clearance_guide):
    values, model = max_clearance_guide
    fx = mount_fixtures(MOUNT, values)
    report = audit(model, SPEC.print_orientation, cutters=fx.cutters, model=SPEC.name)
    assert report.ok, report.format()


# pst-93yd5 / pst-7shtl: mount_style='points' — four Fix Point slots, same body.
POINTS_PRESETS = [p for p in SPEC.presets if p.values.get('mount_style') == 'points']


def test_every_mount_style_has_a_preset():
    # Mount coverage is registry._validate_spec's (mount_for_values); this
    # pins every style, one mount type each.
    styles = {p.values.get('mount_style', STYLE.default) for p in SPEC.presets}
    assert styles == set(STYLE.choices)
    assert len(POINTS_PRESETS) == 2


def recorded_volumes():
    """Last recorded volume per preset in the validation doc's tables."""
    doc = (Path(__file__).resolve().parent.parent/'docs/spool-cradle-validation.md').read_text()
    volumes = {}
    for line in doc.splitlines():
        row = re.match(r'\|\s*`(\w+)`\s*\|(.*)\|\s*$', line)
        if row and row.group(1) in {p.id for p in SPEC.presets}:
            cells = [c.strip().replace(',', '') for c in row.group(2).split('|')]
            numbers = [c for c in cells if re.fullmatch(r'\d+\.\d+', c)]
            if numbers:
                volumes[row.group(1)] = float(numbers[-1])
    return volumes


@pytest.mark.parametrize('preset', SPEC.presets, ids=lambda p: p.id)
def test_preset_volume_matches_validation_doc(preset):
    # Channel presets must stay byte-identical at the default mount_style.
    assert holder(**preset.values).volume == pytest.approx(recorded_volumes()[preset.id], abs=1e-3)


def test_points_too_short_root_is_rejected():
    upper = 100-fp.DEEP_INRADIUS
    assert point_seats(100) == pytest.approx((upper-POINT_ROW_SPACING, upper))
    with pytest.raises(ValueError, match=r'root_height > 75 mm'):
        point_seats(75)


@pytest.fixture(scope='module', params=POINTS_PRESETS, ids=lambda p: p.id)
def points_model(request):
    values = request.param.values
    return values, holder(**values)


def test_points_layout_and_solid_between_rows(points_model):
    values, model = points_model
    p = dimensions(values)
    fx = mount_fixtures(FP_MOUNT, values)
    boxes = [c.bounding_box() for c in fx.cutters]
    assert sorted({round((b.min.X+b.max.X)/2, 6) for b in boxes}) == [-PITCH/2, PITCH/2]
    seats = sorted({round(s.position.Z, 6) for s in fx.seat_locs})
    assert seats[1]-seats[0] == pytest.approx(POINT_ROW_SPACING)
    drops = {round(s.position.Z-r.position.Z, 6) for s, r in zip(fx.seat_locs, fx.onramp_locs)}
    assert drops == {fp.TRAVEL}
    for x in (-PITCH/2, PITCH/2):
        lower, upper = sorted((b for b in boxes if abs((b.min.X+b.max.X)/2-x) < 1e-6),
                              key=lambda b: b.min.Z)
        # Pocket floor above the bed relief; upper cap at least 2.4 mm.
        assert lower.min.Z >= WEB+.5-1e-6
        assert p['plate_height']-upper.max.Z >= 2.4-1e-6
        # Solid plate between the rows, across the full pocket footprint.
        gap = upper.min.Z-lower.max.Z
        assert gap > 10
        between = Pos(x, fp.POCKET_DEPTH/2, (lower.max.Z+upper.min.Z)/2)*Box(
            lower.size.X, fp.POCKET_DEPTH, gap-.2)
        assert (model & between).volume == pytest.approx(between.volume, rel=1e-6)
        # No pocket opens through the bottom edge.
        assert model.is_inside((x, fp.POCKET_DEPTH/2, 1))


def test_points_truss_returns_to_backing(points_model):
    values, model = points_model
    p = dimensions(values)
    assert_truss_sections(model, p)
    boxes = [c.bounding_box() for c in mount_fixtures(FP_MOUNT, values).cutters]
    for tri in truss_openings(p):
        cross = section(model, section_by=Plane(origin=(0, tri[2][0], 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
        for face in cross.faces():
            assert not any(face.bounding_box().overlaps(b) for b in boxes)
    # Webs and rails join the plate behind the pocket backing, never a void.
    for sign in (-1, 1):
        x = sign*(p['root_inner']+WEB/2)
        for z in (CHORD/2, p['contact_z']/2):
            assert model.is_inside((x, p['plate_thickness']-WEB/2, z))
            assert model.is_inside((x, fp.POCKET_DEPTH+.1, z))


POINTS_AUDIT_CASES = [p.values for p in POINTS_PRESETS] + [
    dict(spool_width=w, saddle_clearance=c, cradle_angle=a, mount_style='points')
    for w in (50, 66, 70) for c in (.25, 1.5) for a in (25, 45)]


@pytest.mark.parametrize('values', POINTS_AUDIT_CASES,
                         ids=[p.id for p in POINTS_PRESETS]+[
                             f"w{v['spool_width']}-c{v['saddle_clearance']}-a{v['cradle_angle']}"
                             for v in POINTS_AUDIT_CASES[len(POINTS_PRESETS):]])
def test_points_print_audit_and_edges(values):
    model = holder(**values)
    assert model.is_valid and len(model.solids()) == 1
    p = dimensions(values)
    assert_finished_edges(model, p)
    fx = mount_fixtures(FP_MOUNT, values)
    assert len(fx.cutters) == 4
    report = audit(model, SPEC.print_orientation, cutters=fx.cutters, model=SPEC.name)
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'


# pst-pwtnq: mount_style='openconnect' — four openConnect slots, same body.
OC_PRESETS = [p for p in SPEC.presets if p.values.get('mount_style') == 'openconnect']


def test_grid_follows_the_style():
    for style, pitch, cadence, depth in (('channel', PITCH, 75, POCKET_DEPTH),
                                         ('points', PITCH, 75, fp.POCKET_DEPTH),
                                         ('openconnect', 28, 84, 2.7)):
        p = dimensions({'mount_style': style})
        assert (p['pitch'], p['cadence']) == (pitch, cadence)
        assert p['pocket_depth'] == pytest.approx(depth)
        assert p['guide_outer'] == pytest.approx(cadence/2-p['guide_gap'])
        assert p['guide_reach'] == pytest.approx(cadence/2-p['guide_gap']-p['spool_width']/2)
        assert p['channel_length'] % pitch == pytest.approx(0)
    assert len(OC_PRESETS) == 2
    for preset in OC_PRESETS:
        assert preset.values['plate_width'] == 82 and preset.values['plate_thickness'] == 5.5


@pytest.mark.parametrize(('style', 'floor'), (('channel', 6.55), ('points', 5.6)))
def test_multiboard_plate_floors(style, floor):
    dimensions({'mount_style': style, 'plate_width': 70, 'plate_thickness': floor})
    with pytest.raises(ValueError, match=rf"mount_style='{style}' needs plate_width <= 70 mm"):
        dimensions({'mount_style': style, 'plate_width': 70.5})
    with pytest.raises(ValueError, match=rf"mount_style='{style}' needs plate_thickness >= {floor:g} mm"):
        dimensions({'mount_style': style, 'plate_thickness': floor-0.1})


def test_openconnect_plate_floors():
    # Both floors equal the shared range bounds, so resolve_values rejects a
    # violation first; check_plate is the style rule itself.
    values = SPEC.resolve_values({'mount_style': 'openconnect'})
    check_plate({**values, 'plate_width': 82, 'plate_thickness': 5.1})
    with pytest.raises(ValueError, match=r"mount_style='openconnect' needs plate_width <= 82 mm"):
        check_plate({**values, 'plate_width': 82.5})
    with pytest.raises(ValueError, match=r"mount_style='openconnect' needs plate_thickness >= 5.1 mm"):
        check_plate({**values, 'plate_thickness': 5.0})
    for name, value in (('plate_width', 82.5), ('plate_thickness', 5.0)):
        with pytest.raises(ValueError):
            dimensions({'mount_style': 'openconnect', name: value})


def test_openconnect_slot_top_is_the_cutter_roof():
    # OCCT bounding boxes overshoot by ~1e-7.
    assert OC_SLOT_TOP == pytest.approx(slot_cutter().bounding_box().max.Z, abs=1e-6)


@pytest.fixture(scope='module', params=OC_PRESETS, ids=lambda p: p.id)
def oc_model(request):
    values = request.param.values
    return values, holder(**values)


def test_openconnect_layout(oc_model):
    values, model = oc_model
    p = dimensions(values)
    fx = mount_fixtures(OC_MOUNT, values)
    assert mount_fixtures(MOUNT, values) is None
    assert len(fx.cutters) == len(fx.seat_locs) == len(fx.onramp_locs) == 4
    seats = [s.position for s in fx.seat_locs]
    assert sorted({round(s.X, 6) for s in seats}) == [-14, 14]
    lower, upper = sorted({round(s.Z, 6) for s in seats})
    assert upper-lower == pytest.approx(oc.TILE_SIZE)
    boxes = [c.bounding_box() for c in fx.cutters]
    # Upper roof WEB below the plate top; lower slots well above the bed.
    assert p['plate_height']-max(b.max.Z for b in boxes) == pytest.approx(WEB)
    assert min(b.min.Z for b in boxes) >= WEB+.5
    assert all(-p['plate_width']/2+2.4 <= b.min.X and b.max.X <= p['plate_width']/2-2.4
               for b in boxes)
    # One push-in, shift and downward slide seats all four heads at once.
    moves = {tuple(round(v, 6) for v in s.position-r.position)
             for s, r in zip(fx.seat_locs, fx.onramp_locs)}
    assert moves == {(oc.ONRAMP_SHIFT, 0, oc.MOVE_DISTANCE)}
    assert p['plate_thickness']-p['pocket_depth'] == pytest.approx(2.8)
    assert model.bounding_box().size.X == pytest.approx(84-2*p['guide_gap'])


def test_openconnect_truss_returns_to_backing(oc_model):
    values, model = oc_model
    p = dimensions(values)
    assert_truss_sections(model, p)
    boxes = [c.bounding_box() for c in mount_fixtures(OC_MOUNT, values).cutters]
    for tri in truss_openings(p):
        cross = section(model, section_by=Plane(origin=(0, tri[2][0], 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
        for face in cross.faces():
            assert not any(face.bounding_box().overlaps(b) for b in boxes)
    for sign in (-1, 1):
        x = sign*(p['root_inner']+WEB/2)
        for z in (CHORD/2, p['contact_z']/2):
            assert model.is_inside((x, p['plate_thickness']-WEB/2, z))
            assert model.is_inside((x, p['pocket_depth']+.1, z))


OC_PLATE = dict(mount_style='openconnect', plate_width=82, plate_thickness=5.5)
OC_AUDIT_CASES = [p.values for p in OC_PRESETS] + [
    dict(spool_width=w, saddle_clearance=c, cradle_angle=a, **OC_PLATE)
    for w in (50, 66, 70) for c in (.25, 1.5) for a in (25, 45)]


@pytest.mark.parametrize('values', OC_AUDIT_CASES,
                         ids=[p.id for p in OC_PRESETS]+[
                             f"w{v['spool_width']}-c{v['saddle_clearance']}-a{v['cradle_angle']}"
                             for v in OC_AUDIT_CASES[len(OC_PRESETS):]])
def test_openconnect_print_audit_and_edges(values):
    model = holder(**values)
    assert model.is_valid and len(model.solids()) == 1
    p = dimensions(values)
    assert_contacts(model, p)
    assert_cadence(model, p)
    assert_finished_edges(model, p)
    fx = mount_fixtures(OC_MOUNT, values)
    assert len(fx.cutters) == 4
    report = audit(model, SPEC.print_orientation, cutters=fx.cutters, model=SPEC.name)
    assert report.ok, report.format()
    assert report.bed_chamfer == 'present'
