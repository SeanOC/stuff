# SPDX-License-Identifier: CC-BY-SA-4.0
"""Drawer container (D3): source parity, fit, frames and published print inventory."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from shapely import maximum_inscribed_circle

from drawer import container, shell
from holders import openconnect_drawer as m
from tests import print_audit as audit
from tests.audit_record import record
from tests.openconnect_drawer_inventory import (back_magnet_rims, container_edge_inventory,
                                                container_skin_mask, container_wall_regions,
                                                label_plate_tips)
from tests.parity import bbox_parity, load_reference, surface_distance, volume_parity

REFERENCES = Path(__file__).resolve().parents[2] / 'assets/openConnect-drawer/mesh'
SOLID = {f'container_{wall}_wall_type': 'Solid' for wall in ('front', 'back', 'side', 'bottom')}
ONE = dict(horizontal_grids=1, vertical_grids=1, depth_grids=1)
# The author's container meshes carry CGAL/manifold warnings and 7-17
# unpaired edges, so trimesh volumes are approximate: capped at 0.2 %
# (measured port/ref gaps are 0.02-0.05 %); bbox + surface distance pin shape.
VOLUME_REL = .002


@pytest.fixture(scope='module', params=[
    ('container-default', {}),
    ('container-all-solid', SOLID),
    ('container-1x1x1', ONE),
], ids=lambda case: case[0])
def reference_case(request, tmp_path_factory):
    from build123d import export_stl
    name, values = request.param
    values = {**values, 'honeycomb_ceiling': 'source'}
    body = container.source_body(values)
    # Parity runs in the mesh frame: CONTAINER_AUTHOR_TO_MESH on the PORT.
    mesh = container.author_to_mesh(values)*body
    path = tmp_path_factory.mktemp(name)/'port.stl'
    export_stl(mesh, str(path), tolerance=.01, angular_tolerance=.05)
    return name, values, body, mesh, load_reference(path), load_reference(REFERENCES/f'{name}.stl')


# audit_full, not the 35 min 'audit' job (codex round 4 B2 on #190: that job
# had ~2.5 min headroom on main); the drawer's audit_full runs on 6 shards.
@pytest.mark.audit
@pytest.mark.audit_full
def test_reference_parity(reference_case):
    name, values, body, mesh, port, ref = reference_case
    assert body.is_valid and len(body.solids()) == 1
    # Exact-solid validity is the gate (D1 pattern); the tessellated swept
    # handle is not welded watertight, and references never are.
    assert port.body_count == 1
    assert bbox_parity(mesh, ref, tol=.05, mode='ordered', rtol=0)
    assert volume_parity(port, ref, rel=VOLUME_REL)
    from trimesh.proximity import closest_point
    classifier = audit._ClassifiedPart(mesh)
    directions = {}
    for direction, a, b in [('port->ref', port, ref), ('ref->port', ref, port)]:
        points, distances = surface_distance(a, b, n=40000, seed=1, sampler='uniform',
                                             vertices=True, signed=False)
        skin = np.zeros(len(points), dtype=bool)
        if direction == 'ref->port':
            _, _, triangles = closest_point(ref, points)
            skin = container_skin_mask(points, ref.face_normals[triangles], values, classifier)
        # Skins are a fixed area, so the small drawer's share is larger.
        assert skin.mean() < {'container-default': .04, 'container-all-solid': .04,
                              'container-1x1x1': .15}[name]
        kept = distances[~skin]
        assert kept.max() <= .05, (name, direction, kept.max())
        print(f'PARITY | {name} | {direction} | ref {ref.volume:.3f} | port {port.volume:.3f} | '
              f'max {kept.max():.6f} | skin {skin.mean():.4%}')
        directions[direction] = {'max': kept.max(), 'skin': skin.mean()}
    record(name, ref=ref.volume, port=port.volume, directions=directions)


def test_author_to_mesh_is_the_export_spin():
    """[C] :1358-1362 up(container_height/2) xrot(90); lift 25.2 mm at defaults."""
    from build123d import Pos, Rot
    assert container.dimensions().height/2 == pytest.approx(25.2)
    for values in ({}, ONE, {'vertical_grids': 8}):
        h = container.dimensions(values).height
        moved = container.author_to_mesh(values)*Pos(1, 2, 3)
        assert tuple(moved.position) == pytest.approx((1, -3, 2+h/2))
        assert container.author_to_mesh(values) == Pos(0, 0, h/2)*Rot(90, 0, 0)


@pytest.mark.parametrize('values', [{}, SOLID, {'handle_depth': 20}])
def test_print_frame_bottom_on_bed_handle_toward_minus_y(values):
    v = {'part': 'container', **values}
    part = m.build(v)
    assert part.is_valid and len(part.solids()) == 1
    d = container.dimensions(v)
    hd = v.get('handle_depth', 12)
    bb = (m.print_frame(v)*part).bounding_box()
    assert (bb.min.X, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z) == pytest.approx(
        (-d.width/2, 0, d.width/2, 0, d.height), abs=1e-4)
    # Handle toward -Y, inside mask (a) :1530-1531 (inset=-handle_depth).
    assert -(d.depth+hd)-1e-4 <= bb.min.Y < -d.depth-hd/2
    # print_frame = (author -> print) after (model -> author).
    assert m.print_frame(v) == container.author_to_mesh(v)*container.AUTHOR_TO_MODEL.inverse()


def test_presets_are_valid_single_solids():
    for preset in m.SPEC.presets:
        if preset.values.get('part') == 'container':
            part = m.build(preset.values)
            assert part.is_valid and len(part.solids()) == 1, preset.id
            print(f'VOLUME | {preset.id} | {part.volume/1000:.3f} cm3')


def test_module_fallbacks_match_registered_defaults():
    """Every `v.get('<param>', <fallback>)` in the drawer modules repeats a
    registered Param default; a drift in either copy would silently change
    geometry for callers that skip resolve_values (review N2, PR #190)."""
    import ast
    from drawer import constants
    defaults = m.SPEC.default_values()
    seen = set()
    for module in (container, shell):
        tree = ast.parse(Path(module.__file__).read_text())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'get' and len(node.args) == 2):
                continue
            key, fallback = node.args
            if not isinstance(key, ast.Constant):
                continue
            if isinstance(fallback, ast.Attribute):  # c.<CONSTANT>
                fallback = getattr(constants, fallback.attr)
            else:
                fallback = ast.literal_eval(fallback)
            where = f'{Path(module.__file__).name}:{node.lineno} {key.value}'
            assert key.value in defaults, where
            assert defaults[key.value] == fallback, where
            seen.add(key.value)
    # _wall_types reads its four keys through an f-string.
    for name, fallback in zip(('front', 'back', 'side', 'bottom'),
                              container._wall_types({})):
        assert defaults[f'container_{name}_wall_type'] == fallback, name
    assert len(seen) > 30


@pytest.mark.parametrize('values', [{}, ONE, {'horizontal_grids': 8, 'vertical_grids': 3},
                                    {'shell_thickness': 4, 'container_width_clearance': 1,
                                     'container_height_clearance': 1, 'container_depth_clearance': 1}])
def test_container_fits_the_shell_cavity(values):
    """Author frame, no rotation: per-axis fit, handle protrusion intended."""
    sd = shell.dimensions(values)
    d = container.dimensions(values)
    cw = values.get('container_width_clearance', .3)
    ch = values.get('container_height_clearance', .4)
    cd = values.get('container_depth_clearance', .4)
    walls = (container._envelope(d)-container._cavity(d)).bounding_box()
    assert walls.size.X <= sd.inner_width-2*cw+1e-6
    assert walls.size.Y <= sd.inner_height-2*ch+1e-6
    assert walls.size.Z == pytest.approx(d.depth)  # [C] :424, handle excluded
    assert d.depth <= sd.inner_depth-cd+1e-6
    full = container.source_body({**values, 'add_label_holder': False}).bounding_box()
    hd = values.get('handle_depth', 12)
    # mask (a) :1530-1531 inset=-handle_depth: the handle stands proud of
    # the shell's front plane by design (147.98 vs 136.4 at defaults; the
    # bar stops short of the mask, cf. the 32.20 mm 1x1x1 reference).
    assert full.min.Z == pytest.approx(0, abs=1e-6)
    assert sd.inner_depth < full.max.Z <= d.depth+hd+1e-4
    if not values:
        ref = load_reference(REFERENCES/'container-default.stl')
        assert full.max.Z == pytest.approx(-ref.bounds[0][1], abs=.01)
        assert (round(full.max.Z, 2), sd.inner_depth) == (147.98, pytest.approx(136.4))


@pytest.mark.parametrize('values', [{}, ONE, {'horizontal_grids': 8, 'vertical_grids': 4},
                                    {'horizontal_grids': 2}])
def test_back_magnets_face_the_shell_magnets(values):
    """Same X and Y as the shell's in the shared author frame; Z differs."""
    ours = [p for kind, _, p in container.source_magnet_positions(values) if kind == 'back']
    theirs = shell.source_back_magnet_positions(values)
    assert len(ours) == len(theirs)
    if not ours:  # 1 column: the author's Bottom Corners place none
        return
    assert np.asarray(ours)[:, :2] == pytest.approx(np.asarray(theirs)[:, :2], abs=.01)


def test_middle_truss_threshold_is_the_source_constant():
    assert container.MIDDLE_TRUSS_MIN_HANDLE_WIDTH == 50
    for grids, stems in ((5, 3), (2, 2)):
        h = container.handle_layout({'horizontal_grids': grids})
        assert len(h.stems) == stems


@pytest.mark.parametrize('values,message', [
    ({'container_width_clearance': 70}, 'container dimensions must be greater than 0'),
    ({**ONE, 'container_solid_wall_thickness': 12, **SOLID}, 'container inner dimensions must be greater than 0'),
    ({'container_front_wall_type': 'Mesh'}, 'container wall types must be Honeycomb or Solid'),
])
def test_named_errors_for_source_asserts(values, message):
    with pytest.raises(ValueError, match=message):
        container.source_body(values)


@pytest.mark.parametrize('values', [{'horizontal_grids': 1}, {'horizontal_grids': 1, 'label_width': 21},
                                    {'horizontal_grids': 2, 'label_width': 49}])
def test_label_wider_than_front_is_clipped(values):
    """pst-rnpvl option C: the author's mask clips an over-wide holder into a
    lipless ledge; the registry path builds it like the library path does."""
    full = m.SPEC.resolve_values({'part': 'container', **values})  # every default explicit, as the catalog posts
    front = container.dimensions(full).width
    part = m.build(full)
    assert part.is_valid and len(part.solids()) == 1
    assert (m.print_frame(full) * part).bounding_box().size.X == pytest.approx(front, abs=1e-3)
    part = m.build({**full, 'add_label_holder': False})
    assert part.is_valid and len(part.solids()) == 1


def test_label_width_clip_is_documented_in_the_manifest():
    """The catalog reads manifest.json, not the Param: the clip note must land there."""
    note = next(p.description for p in m.SPEC.params if p.name == 'label_width')
    assert 'clipped to the body' in note
    assert json.dumps(note) in (Path(__file__).parents[1] / 'manifest.json').read_text()


def _mesh(author_point, values=None):
    d = container.dimensions(values)
    x, y, z = author_point
    return np.array([x, -z, y+d.height/2])


def _hits(ref, origin, direction):
    points, _, _ = ref.ray.intersects_location([origin], [direction])
    return sorted(float(np.dot(p-origin, direction)) for p in points)


def test_published_thin_features():
    """Pin every container_wall_regions row against the source meshes."""
    default = load_reference(REFERENCES/'container-default.stl')
    solid = load_reference(REFERENCES/'container-all-solid.stl')
    d = container.dimensions()
    # Back magnet floor: 1 + .15 deep into the 1.6 Solid back -> .45 mm.
    (_, _, (x, y, _)), = [p for p in container.source_magnet_positions() if p[0] == 'back'][:1]
    # Small offsets keep every ray off triangle edges of the source STL.
    origin = _mesh((x, y+.017, -1))
    assert _hits(default, origin, (0, -1, 0))[:2] == pytest.approx([2.15, 2.6], abs=1e-4)
    # Side magnet floor: .85 behind the 2.0 Honeycomb side, .45 behind 1.6 Solid.
    (_, side, (x, y, z)) = [p for p in container.source_magnet_positions() if p[0] == 'side'][0]
    for ref, wall in ((default, 2.), (solid, 1.6)):
        origin = _mesh((x+side, y+.017, z+.013))
        hits = _hits(ref, origin, (-side, 0, 0))
        assert hits[:2] == pytest.approx([2.15, 1+wall], abs=1e-4)
    # Label holder rails: LABEL_WALL .8 [C] :1779 either side of the pocket
    # (pocket layer), and the .8 front lip over it.
    width, depth, height, y0, y1 = container._label_box(d, {})
    wall = container.LABEL_WALL
    origin = _mesh((-width/2-1, y1-3.017, d.depth+.613))
    hits = _hits(default, origin, (1, 0, 0))
    assert hits == pytest.approx([1, 1+wall, 1+width-wall, 1+width], abs=1e-4)
    origin = _mesh((width/2-wall-1.013, y1-3.017, d.depth+depth+1))
    assert _hits(default, origin, (0, 1, 0))[:2] == pytest.approx([1, 1+wall], abs=1e-4)
    # Label plate 60-degree tips poke into front cells (:1783-1793): solid
    # 0.3 mm inside each tip, air 0.3 mm beyond it, through the wall.
    tips = label_plate_tips({})
    assert len(tips) == 2
    for (x, y), inward in tips:
        for step, wall in ((.3, [0, d.front]), (-.3, [])):
            px, py = np.array((x, y))+step*np.asarray(inward)
            origin = _mesh((px, py, d.depth+1))
            hits = [h-1 for h in _hits(default, origin, (0, 1, 0)) if h < 1+d.front+.01]
            assert hits == pytest.approx(wall, abs=1e-4)
    # Back magnet rim (vertical_grids 1 only): from inside the hole along
    # author +Y, the teardrop's flat cap then the back wall's top bound a
    # 0.2 mm skin over the hole depth. container-2x1x5 is the reference.
    assert back_magnet_rims({}) == [] and back_magnet_rims(ONE) == []
    rim = dict(horizontal_grids=2, vertical_grids=1, depth_grids=5)
    narrow = load_reference(REFERENCES/'container-2x1x5.stl')
    ((x, gap), _), = back_magnet_rims(rim)
    (_, _, (_, y, _)), = [p for p in container.source_magnet_positions(rim) if p[0] == 'back']
    assert gap == pytest.approx(.2, abs=1e-6)
    for dx in (-1.013, .013, 1.013):
        for z in (.313, .813):
            hits = _hits(narrow, _mesh((x+dx, y, z), rim), (0, 0, 1))
            assert hits[:2] == pytest.approx([3.4, 3.4+gap], abs=1e-4)


@pytest.mark.parametrize('values', [{'shell_thickness': 4}, {'container_back_side_height_offset': 10}])
def test_honeycomb_wall_cutters_are_valid(values):
    """shell_thickness 4: the top V of a shallow front cell pierces its
    bottom and used to leave a 1e-15 mm bridge (invalid cutter).
    back_side_height_offset 10: the side window clips a hex row into a
    0.028 mm strip, which is dropped (no opening narrower than 0.1 mm)."""
    v = {'part': 'container', **values}
    for name, plane, layout, thickness in container.wall_layouts(v):
        assert layout.cutter(thickness, (0, 1)).is_valid, name
        assert all(not p.buffer(-.05).is_empty for p in layout.openings), name


def test_exclusions_reject_new_thin_overhang():
    from build123d import Box, Pos
    v = {'part': 'container', **ONE, 'add_label_holder': False}
    # A thin shelf on the back wall's inner face: no source reason exists.
    d = container.dimensions(v)
    bad = m.build(v)+container.AUTHOR_TO_MODEL*(Pos(0, 0, d.back+3)*Box(6, .6, 6))
    report = audit.audit(bad, cutters=[], print_frame=m.print_frame(v),
                         exclusions=m.audit_exclusions(v)+container_wall_regions(v))
    assert not report.ok
    assert report.max_overhang_deg > 45
    assert report.min_wall_mm < .9


def test_edge_inventory_rejects_unpublished_protrusion():
    from build123d import Box, Pos
    v = {'part': 'container', **ONE, 'add_label_holder': False}
    d = container.dimensions(v)
    bad = m.build(v)+container.AUTHOR_TO_MODEL*(Pos(d.width/2, 0, d.depth/2)*Box(4, 4, 4))
    with pytest.raises(AssertionError, match='uninventoried edge'):
        container_edge_inventory(bad, v)


CONTAINER_PARAMS = {'horizontal_grids', 'vertical_grids', 'depth_grids', 'honeycomb_strut_hyp',
                    'shell_thickness', 'shell_outer_chamfer', 'shell_to_slot_wall_thickness',
                    'slot_depth_clearance'}
CASES = [(p.id, p.values) for p in m.SPEC.presets if p.values.get('part') == 'container'] + [
    (f'{p.name}={x:g}', {'part': 'container', p.name: x}) for p in m.SPEC.params
    if p.kind in ('number', 'integer') and (p.group == 'Container' or p.name in CONTAINER_PARAMS)
    for x in (p.min, p.max) if x is not None
] + [
    # D4: divider params only act with dividers on.
    (f'divider-{p.name}={x:g}', {'part': 'container', 'add_container_divider': 'Both', p.name: x})
    for p in m.SPEC.params if p.group == 'Container Divider' and p.kind in ('number', 'integer')
    for x in (p.min, p.max)
] + [(name, {'part': 'container', 'add_container_divider': 'Both', **values}) for name, values in [
    ('divider-1x1x1', ONE),
    ('divider-all-honeycomb', {f'container_{w}_wall_type': 'Honeycomb' for w in ('front', 'back', 'side', 'bottom')}),
    ('divider-fillet-0', {'container_inner_fillet': 0}),
    ('divider-fillet-4', {'container_inner_fillet': 4}),
    ('divider-8x8x8-fine', dict(horizontal_grids=8, vertical_grids=8, depth_grids=8,
                                container_width_grid_count=8, container_width_compartment_list='1,1,1,1,1,1,1,1')),
    ('divider-thick-walls-1-vertical', dict(vertical_grids=1, container_solid_wall_thickness=3,
                                            container_honeycomb_wall_thickness=3)),
]] + [(name, {'part': 'container', **values}) for name, values in [
    ('1x1x1-no-label', {**ONE, 'add_label_holder': False}),
    ('2-wide-label-20', {'horizontal_grids': 2, 'vertical_grids': 1, 'label_width': 20}),
    ('8x8x8', dict(horizontal_grids=8, vertical_grids=8, depth_grids=8)),
    ('all-honeycomb', {f'container_{w}_wall_type': 'Honeycomb' for w in ('front', 'back', 'side', 'bottom')}),
    ('all-honeycomb-strut-2', {'honeycomb_strut_hyp': 2, **{
        f'container_{w}_wall_type': 'Honeycomb' for w in ('front', 'back', 'side', 'bottom')}}),
    ('max-clearance', dict(container_width_clearance=1, container_height_clearance=1, container_depth_clearance=1)),
    ('min-clearance', dict(container_width_clearance=.1, container_height_clearance=.1, container_depth_clearance=.1)),
    ('thin-walls', dict(container_solid_wall_thickness=1.2, container_honeycomb_wall_thickness=1.6)),
    ('thick-walls', dict(container_solid_wall_thickness=3, container_honeycomb_wall_thickness=3)),
    ('mid-walls', dict(container_solid_wall_thickness=2.1, container_honeycomb_wall_thickness=2.3)),
    ('top-slot', dict(shell_slot_position='Top')),
    ('max-label', dict(horizontal_grids=8, vertical_grids=3, label_width=100, label_height=20, label_thickness=1.6)),
    ('no-label-no-magnets', dict(add_label_holder=False, add_back_magnet_holes=False, add_side_magnet_holes=False)),
]]
@pytest.mark.parametrize('name,values', CASES, ids=[name for name, _ in CASES])
def test_lattice_openings_under_2mm_are_closed(name, values):
    """DECISION C (b): production closes, by size, exactly the sub-2 mm openings."""
    try:
        closed = container.wall_layouts(values)
    except ValueError as exc:
        assert any(text in str(exc) for text in NAMED), str(exc)
        return
    raw = container.wall_layouts(values, close_openings=False)
    assert [w[0] for w in closed] == [w[0] for w in raw if any(
        container.opening_diameter(prof) >= container.c.MIN_LATTICE_OPENING_MM
        for prof, _, _ in w[2].profiles((0, 1)))]
    kept = {name: layout for name, _, layout, _ in closed}
    shut = []
    for wall, _, layout, _ in raw:
        keep = kept[wall].openings if wall in kept else []
        assert all(any(p.equals(q) for q in layout.openings) for p in keep), wall
        profiles = dict(zip(map(id, layout.openings), layout.profiles((0, 1))))
        for p in layout.openings:
            diameter = container.opening_diameter(profiles[id(p)][0])
            assert any(p.equals(q) for q in keep) == (diameter >= container.c.MIN_LATTICE_OPENING_MM), \
                (wall, round(diameter, 3))
            if diameter < container.c.MIN_LATTICE_OPENING_MM:
                shut.append(diameter)
    print(f'CLOSED | {name} | {len(shut)} | {min(shut, default=0):.3f}')
    # Rule 3: no through-wall opening under 2 mm in production. Measured
    # piece by piece here, not through opening_diameter: a roof can split a
    # cell in two and the small lobe is a hole too (review round 5 B1, #190).
    pieces = [2*maximum_inscribed_circle(g, .001).length
              for _, _, layout, _ in closed for prof, _, _ in layout.profiles((0, 1))
              for g in getattr(prof, 'geoms', [prof]) if not g.is_empty]
    assert min(pieces, default=2.) >= container.c.MIN_LATTICE_OPENING_MM, round(min(pieces), 3)


NAMED = (
    'shell_to_slot_wall_thickness below 0.8 mm leaves less slot backing than the openconnect-slot-shallow contract',
)


@pytest.mark.audit
@pytest.mark.audit_full
@pytest.mark.parametrize('name,values', CASES, ids=[name for name, _ in CASES])
def test_endpoint_audit_and_edges(name, values):
    try:
        part = m.build(values)
    except ValueError as exc:
        assert any(text in str(exc) for text in NAMED), str(exc)
        print(f'AUDIT | {name} | named error: {exc}')
        record(name, named_error=str(exc))
        return
    assert part.is_valid and len(part.solids()) == 1
    chords = container.honeycomb_ceiling_chords(values)
    max_unroofed = max((chord for _, chord, roofed in chords if not roofed), default=0)
    assert max_unroofed <= audit.MAX_BRIDGE_MM
    report = audit.audit(part, cutters=[], print_frame=m.print_frame(values),
                         exclusions=m.audit_exclusions(values)+container_wall_regions(values))
    assert report.ok, report.format()
    assert report.longest_bridge_mm <= audit.MAX_BRIDGE_MM
    # The 0.3 mm bed bevel, measured on exact print-frame sections.
    from build123d import Plane, section
    printed = m.print_frame(values)*part
    d = container.dimensions(values)
    full = printed.bounding_box()
    for z in (.001, .15, .301):
        box = section(printed, section_by=Plane.XY.offset(z)).bounding_box()
        # Chamfered bottom edges keep the outer chamfer (= shell inner
        # chamfer, :360); square ones (the back wall) get the .3 bevel.
        bevel = d.outer_chamfer or .3
        assert box.size.X == pytest.approx(d.width-2*max(0, bevel-z), abs=.001)
        assert box.max.Y == pytest.approx(full.max.Y-max(0, .3-z), abs=.001)
    inventory, angle = container_edge_inventory(part, values)
    print(f'AUDIT | {name} | wall {report.min_wall_mm:.3f} | overhang {report.max_overhang_deg:.1f} | '
          f'bridge {report.longest_bridge_mm:.2f} | unroofed chord {max_unroofed:.3f} | '
          f'convex edge {angle:.3f} | vol {part.volume/1000:.3f} | PASS {inventory}')
    record(name, wall=report.min_wall_mm, overhang=report.max_overhang_deg,
           bridge=report.longest_bridge_mm, unroofed_chord=max_unroofed, convex_edge=angle,
           vol_cm3=part.volume/1000, result='PASS', inventory=inventory)
