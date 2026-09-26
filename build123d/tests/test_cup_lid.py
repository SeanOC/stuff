"""Lower circular-segment v2.1 geometry contract for pst-5slt.

Tests inspect the final BRep/mesh, not just construction metadata. Physical
bolt/lid fit remains the downstream pst-mvno print experiment.
"""
import math
import sys
from pathlib import Path

import pytest
import trimesh
from build123d import Plane
from OCP.BRepAdaptor import BRepAdaptor_Surface

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from holders.cup_lid import PARAMS, PITCH, SPEC, dimensions, holder, pin_centers, pin_length_mm
from scripts.export import export_stl
from holders.registry import all_models


@pytest.fixture(scope='module')
def part():
    return holder()


def test_registered_default():
    assert SPEC in all_models()
    assert SPEC.title == 'Cup lid holder (Multibuild)'
    assert SPEC.category_id == 'multiboard'
    assert SPEC.presets[0].id == 'sippy_cup_85mm'
    assert SPEC.print_orientation == (0, 0, 1)


def test_presets_watertight_and_envelope(part, tmp_path):
    p = dimensions({})
    assert part.is_valid and len(part.solids()) == 1 and part.volume > 0
    stl = tmp_path / 'cup.stl'
    export_stl(part, str(stl))
    mesh = trimesh.load(stl, force='mesh')
    assert mesh.is_watertight and mesh.is_winding_consistent
    size = part.bounding_box().size
    # Chord-edge relief trims the ideal outline slightly.
    ideal_width = 2*math.sqrt(p['radius']**2-p['top_chord_offset']**2)
    assert ideal_width-1 < size.X < ideal_width
    assert size.Z == pytest.approx(p['mount_height'])
    assert size.Y == pytest.approx(p['lip_top']+p['pin_length'])


def test_lower_segment_outline(part):
    p = dimensions({})
    # Recover the circle from the final outer wall, independently of dimensions().
    walls = [BRepAdaptor_Surface(f.wrapped).Cylinder() for f in part.faces()
             if f.geom_type.name == 'CYLINDER'
             and abs(BRepAdaptor_Surface(f.wrapped).Cylinder().Radius()-p['radius']) < 1e-6]
    assert len(walls) == 2
    circle_z = walls[0].Location().Z()
    r = walls[0].Radius()
    chords = []
    for normal in (1, -1):
        face = next(f for f in part.faces() if f.geom_type.name == 'PLANE'
                    and f.normal_at().Z*normal > 0.99)
        z = face.center().Z
        ideal_width = 2*math.sqrt(r*r-(z-circle_z)**2)
        # The real chord face is inset by the deliberate edge relief.
        assert ideal_width-2 < face.bounding_box().size.X < ideal_width
        chords.append((z, ideal_width, face.bounding_box().size.X))
    assert chords[0][0]-circle_z == pytest.approx(-p['top_chord_offset'], abs=1e-6)
    assert chords[1][0]-circle_z == pytest.approx(-p['top_chord_offset']-p['mount_height'], abs=1e-6)
    assert chords[0][1] == pytest.approx(
        2*math.sqrt(p['radius']**2-p['top_chord_offset']**2), abs=1e-3)
    assert chords[0][1] > chords[1][1]
    assert chords[0][2] > chords[1][2]
    lean = math.degrees(math.atan(abs(chords[1][0]-circle_z)/(chords[1][1]/2)))
    assert lean == pytest.approx(p['wall_lean_deg'])
    assert lean <= 45


def test_mirror_symmetry(part):
    reflected = part.mirror(Plane.YZ)
    assert abs((part-reflected).volume) < 1e-3
    assert abs((reflected-part).volume) < 1e-3


def test_front_face_planar_inset_grid(part):
    p = dimensions({})
    faces = [f for f in part.faces() if abs(f.center().Y-p['plate_thickness']) < 1e-6
             and f.normal_at().Y > 1-1e-6]
    assert len(faces) == 1
    face = faces[0]
    assert face.geom_type.name == 'PLANE'
    # A circle can have a locally +Y normal (the rear cone), but a front
    # face with constant +Y normal must be planar, never a cylinder/cone.
    for f in part.faces():
        if all(n.Y > 1-1e-6 for _, n in _samples(f)):
            assert f.geom_type.name == 'PLANE'
    inset = 1.2  # max(bed_chamfer, 0.5, R1) + 0.2
    tested = 0
    for x in range(-math.ceil(p['radius']), math.ceil(p['radius'])+1, 2):
        for z in range(-math.ceil(p['mount_height']/2), math.ceil(p['mount_height']/2)+1, 2):
            radial = math.hypot(x, z-p['circle_center_z'])
            if (abs(z) < p['mount_height']/2-inset
                    and radial < p['wall_radius']-inset
                    and math.hypot(x, z) > p['countersink_diameter']/2+0.2):
                assert face.is_inside((x, p['plate_thickness'], z))
                tested += 1
    assert tested > 300


def _samples(face):
    from tests.print_audit import _face_samples, _OVERHANG_UV
    return _face_samples(face, _OVERHANG_UV)


@pytest.mark.parametrize('values', [{}, {'pin_tip_diameter': 0.8}, {'pin_cone_half_angle': 49}])
def test_pins_are_cones_at_25mm(values):
    p = dimensions(values)
    solid = holder(**values)
    cones = [f for f in solid.faces() if f.geom_type.name == 'CONE' and f.center().Y < 0]
    assert len(cones) == 2
    assert pin_centers(values) == ((-25, 0, 0), (25, 0, 0))
    centers = []
    for face in cones:
        cone = BRepAdaptor_Surface(face.wrapped).Cone()
        axis = cone.Axis()
        centers.append(axis.Location().X())
        assert axis.Location().Z() == pytest.approx(0)
        assert abs(axis.Direction().Y()) == pytest.approx(1)
        assert abs(cone.SemiAngle()) == pytest.approx(math.radians(p['pin_cone_half_angle']))
        bb = face.bounding_box()
        assert bb.max.Y == pytest.approx(0, abs=1e-6)
        assert bb.min.Y == pytest.approx(-p['pin_length'], abs=1e-6)
        assert bb.size.X == pytest.approx(p['pin_base_diameter'], abs=1e-6)
    assert sorted(centers) == pytest.approx([-PITCH, PITCH])
    back = [f for f in solid.faces() if f.geom_type.name == 'PLANE'
            and f.normal_at().Y < -0.99 and abs(f.center().Y) < 1e-6]
    assert len(back) == 1  # cone bases share the board-flush back plane


@pytest.mark.parametrize('base', [6.9, 7.1, 7.3])
@pytest.mark.parametrize('tip', [0, 0.8])
@pytest.mark.parametrize('angle', [45, 49])
def test_pin_clears_board_cavity(base, tip, angle):
    p = dimensions(dict(pin_base_diameter=base, pin_tip_diameter=tip, pin_cone_half_angle=angle))
    assert 2.4 <= p['pin_length'] <= 6.0
    depths = [i*0.05 for i in range(math.ceil(p['pin_length']/0.05))]+[p['pin_length']]
    for z in depths:
        cavity_d = 7.5-z if z <= 1.5 else 6.0
        cone_d = base-2*z*math.tan(math.radians(angle))
        # Reviewer clarification: equality at base=7.3 means exactly
        # 0.1 mm clearance per side and is explicitly accepted.
        assert cone_d <= cavity_d-0.2+1e-9


def test_bolt_hole_through_and_countersunk(part):
    p = dimensions({})
    for i in range(51):
        y = p['plate_thickness']*i/50
        assert not part.is_inside((0, y, 0))
        assert not part.is_inside((p['bolt_clearance_diameter']/2-0.05, y, 0))
    seat_start = p['plate_thickness']-p['seat_depth']
    assert seat_start == pytest.approx(2.75)
    for y in (0.5, seat_start-0.1):
        assert part.is_inside((p['bolt_clearance_diameter']/2+0.05, y, 0))
    for fraction in (0.1, 0.5, 0.9):
        y = seat_start+fraction*p['seat_depth']
        radius = p['bolt_clearance_diameter']/2+fraction*(p['countersink_diameter']-p['bolt_clearance_diameter'])/2
        assert not part.is_inside((radius-0.05, y, 0))
        assert part.is_inside((radius+0.05, y, 0))


def test_shoulder_capture(part):
    p = dimensions({})
    for sign in (-1, 1):
        for z in (0, 5, 10):
            def point(radius, y):
                return (sign*math.sqrt(radius**2-(z-p['circle_center_z'])**2), y, z)
            assert part.is_inside(point(p['wall_radius']+0.1, p['plate_thickness']+3))
            assert not part.is_inside(point(p['wall_radius']-0.1, p['plate_thickness']+3))
            assert part.is_inside(point(p['lip_radius']+0.1, p['lip_bottom']+0.1))
            assert not part.is_inside(point(p['lip_radius']-0.1, p['lip_bottom']+0.1))
            assert not part.is_inside(point(p['lip_radius']+0.1, p['lip_bottom']-0.1))


def test_lip_end_ramps(part):
    p = dimensions({})
    expected_depth = min(p['top_chord_offset']+p['mount_height'],
                         p['lip_radius']/math.sqrt(2))-p['lip_end_margin']
    assert p['lip_stop_z'] == pytest.approx(p['circle_center_z']-expected_depth)
    ramps = [f for f in part.faces() if f.geom_type.name == 'PLANE'
             and f.center().Y > p['lip_bottom']
             and abs(f.normal_at().X) == pytest.approx(math.sqrt(0.5), abs=1e-6)
             and f.normal_at().Z == pytest.approx(-math.sqrt(0.5), abs=1e-6)]
    assert len(ramps) == 2
    ramp_x = math.sqrt(p['wall_radius']**2-expected_depth**2)
    for face in ramps:
        sign = 1 if face.center().X > 0 else -1
        assert face.is_inside((sign*ramp_x, p['lip_top']-1, p['lip_stop_z']), tolerance=1e-6)
        # The R1 junction extends the ramp slightly into the wall, while
        # retaining clearance from the bed. The inner arc is checked below.
        assert face.bounding_box().min.Z > -p['mount_height']/2+p['bed_chamfer']


def test_bottom_contact_face_and_bed_chamfer(part):
    p = dimensions({})
    bottom = -p['mount_height']/2
    faces = [f for f in part.faces() if f.geom_type.name == 'PLANE'
             and abs(f.center().Z-bottom) < 1e-6 and f.normal_at().Z < -0.99]
    assert len(faces) == 1
    assert part.bounding_box().min.Z == pytest.approx(bottom, abs=1e-6)
    bed = faces[0]
    # Only plate + full-height walls touch the bed; the lip and its
    # junction stop above it.
    for sign in (-1, 1):
        depth = bottom-p['circle_center_z']
        x = sign*math.sqrt((p['lip_radius']+p['reach']/2)**2-depth**2)
        assert not part.is_inside((x, p['lip_bottom']+p['lip_thickness']/2, bottom+0.5))
        wall_x = sign*math.sqrt((p['wall_radius']+p['tab_thickness']/2)**2-depth**2)
        assert part.is_inside((wall_x, p['lip_top']-1, bottom+0.5))
    for edge in bed.edges():
        adjacent = [f for f in part.faces() if f != bed and edge in f.edges()]
        assert len(adjacent) == 1
        for _, normal in _samples(adjacent[0]):
            # Spline approximation of the angle-defined OCP chamfer.
            assert normal.Z == pytest.approx(-math.sqrt(0.5), abs=2e-5)
    # The long front/back bed edges carry the configured setback and rise.
    for y in (p['bed_chamfer'], p['plate_thickness']-p['bed_chamfer']):
        assert any(abs(e.center().Y-y) < 1e-6 for e in bed.edges())


def test_joint_overlaps_solid(part):
    p = dimensions({})
    for sign in (-1, 1):
        x = sign*math.sqrt((p['wall_radius']+p['tab_thickness']/2)**2-p['circle_center_z']**2)
        # Plate/wall overlap is one tab thickness deep into the plate.
        assert part.is_inside((x, p['plate_thickness']-p['tab_thickness']/2, 0))
        # Lip/wall overlap is one lip thickness along Y.
        assert part.is_inside((x, p['lip_bottom']+p['lip_thickness']/2, 0))
        # Inside R1 blends add solid material in both otherwise-empty corners.
        assert part.is_inside((sign*math.sqrt((p['wall_radius']-0.2)**2-p['circle_center_z']**2), p['plate_thickness']+0.2, 0))
        assert part.is_inside((sign*math.sqrt((p['wall_radius']-0.2)**2-p['circle_center_z']**2), p['lip_bottom']-0.2, 0))
    blends = [f for f in part.faces() if f.geom_type.name == 'TORUS']
    assert len(blends) == 4
    for f in blends:
        assert BRepAdaptor_Surface(f.wrapped).Torus().MinorRadius() >= 1-1e-6


def test_edge_classification(part):
    p = dimensions({})
    # Upper front/back chord edges have a 0.5 mm chamfer.
    for y in (0.25, p['plate_thickness']-0.25):
        assert any(f.geom_type.name == 'PLANE'
                   and f.is_inside((0, y, p['mount_height']/2-0.25), tolerance=1e-6)
                   and f.normal_at().Z == pytest.approx(math.sqrt(0.5), abs=1e-6)
                   for f in part.faces())
    shoulder_edges = [e for e in part.edges() if e.geom_type.name == 'CIRCLE'
                      and abs(e.radius-p['lip_radius']) < 1e-6
                      and abs(e.center().Y-p['lip_bottom']) < 1e-6]
    assert len(shoulder_edges) == 2
    for edge in shoulder_edges:
        adjacent = [f for f in part.faces() if edge in f.edges()]
        assert sorted(f.geom_type.name for f in adjacent) == ['CYLINDER', 'PLANE']
        plane = next(f for f in adjacent if f.geom_type.name == 'PLANE')
        assert plane.normal_at().Y == pytest.approx(-1)


@pytest.mark.parametrize('name,value', [(q.name, v) for q in PARAMS for v in (q.min, q.max)])
def test_param_boundaries_build(name, value):
    p = dimensions({name: value})
    assert p['wall_lean_deg'] <= 45
    assert p['lip_lean_deg'] <= 45
    solid = holder(**{name: value})
    assert solid.is_valid and len(solid.solids()) == 1 and solid.volume > 0
    # Final outer wall normals also respect the analytic tangent bound.
    for f in solid.faces():
        if f.geom_type.name == 'CYLINDER':
            cylinder = BRepAdaptor_Surface(f.wrapped).Cylinder()
            if abs(cylinder.Radius()-p['lip_radius']) < 1e-6:
                assert f.bounding_box().min.Z >= p['lip_stop_z']-1e-6
                depth = p['circle_center_z']-f.bounding_box().min.Z
                assert math.degrees(math.asin(depth/p['lip_radius'])) <= 45
            if abs(cylinder.Radius()-p['radius']) < 1e-6:
                for _, normal in _samples(f):
                    assert normal.Z >= -math.sqrt(0.5)-1e-6


@pytest.mark.parametrize('name,value', [(q.name, v) for q in PARAMS for v in (q.min-0.01, q.max+0.01)])
def test_outside_param_range_raises(name, value):
    with pytest.raises(ValueError, match=name):
        holder(**{name: value})


@pytest.mark.parametrize('values,message', [
    ({'lid_diameter': 84, 'tab_thickness': 2, 'top_chord_offset': 2, 'mount_height': 30}, 'wall outward lean'),
    ({'top_chord_offset': 2, 'mount_height': 30, 'lid_clearance': 0.1, 'tab_thickness': 2}, 'wall outward lean'),
    ({'shoulder_depth': 2, 'lid_clearance': 0.8}, '>= 1.6'),
    ({'bolt_clearance_diameter': 8.5, 'countersink_diameter': 10.5}, 'must exceed'),
    ({'bolt_clearance_diameter': 7.5, 'countersink_diameter': 13}, 'leave 2.4'),
    ({'pin_tip_diameter': 7.1}, 'pin_tip_diameter'),
    ({'pin_base_diameter': 7.4}, 'pin_base_diameter'),
    ({'plate_height': 30}, 'unknown parameters'),
    ({'lid_diameter': float('nan')}, 'lid_diameter'),
    ({'lid_diameter': True}, 'lid_diameter'),
])
def test_cross_constraints_raise(values, message):
    with pytest.raises(ValueError, match=message):
        holder(**values)


@pytest.mark.parametrize('values', [
    {'lid_diameter': 84, 'mount_height': 30, 'top_chord_offset': 2},  # tightest specified legal build
    {'shoulder_depth': 2, 'lid_clearance': 0.4},
    {'bolt_clearance_diameter': 7.5, 'countersink_diameter': 12.5},
    {'bolt_clearance_diameter': 8, 'countersink_diameter': 13},
    {'pin_base_diameter': 7.3, 'pin_tip_diameter': 0.8, 'pin_cone_half_angle': 49},
])
def test_cross_constraint_accepted_cases(values):
    assert holder(**values).is_valid


def test_pin_length_helper():
    assert pin_length_mm(5, 0, 45) == pytest.approx(2.5)
    assert pin_length_mm(4.8, 0, 45) == pytest.approx(2.4)
    assert pin_length_mm(12, 0, 45) == pytest.approx(6)
    with pytest.raises(ValueError, match='pin length below 2.4'):
        pin_length_mm(4, 0, 45)
    with pytest.raises(ValueError, match='pin length above 6.0'):
        pin_length_mm(13, 0, 45)
