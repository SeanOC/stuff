# SPDX-License-Identifier: CC-BY-SA-4.0
"""Drawer D4: compartment lists, shell/container dividers, stopper clips."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from drawer import container, dividers, shell, stopper
from holders import openconnect_drawer as m
from tests import print_audit as audit
from tests.openconnect_drawer_inventory import container_skin_mask, source_contact_mask
from tests.parity import (band_mask, bbox_parity, boundary_edges, load_reference,
                          over_cap_exclusion, surface_distance, volume_parity)

REFERENCES = Path(__file__).resolve().parents[2] / 'assets/openConnect-drawer/mesh'
WIDTH = dict(add_shell_divider='Width', shell_width_compartment_list='3,2')
HEIGHT = dict(add_shell_divider='Height', shell_height_compartment_list='1,1')
ORGANISER = dict(part='container', add_container_divider='Both')


# ------------------------------------------------------------------ parser

@pytest.mark.parametrize('text, count, positions, sizes', [
    ('1,1,1', 3, (1, 2), (1, 1, 1)),   # [C] :59-61, example 1
    ('2,3', 5, (2,), (2, 3)),          # [C] :62-63, example 2
    ('3,3', 5, (3,), (3, 2)),          # [C] :49 default on 5 tiles: remainder
    ('3,2', 5, (3,), (3, 2)),
    ('2,3', 2, (), (2,)),              # [C] :47 default on 2 tiles: no divider
    ('5', 5, (), (5,)),
    ('1', 1, (), (1,)),
    (' 3, 2 ', 5, (3,), (3, 2)),       # spaces removed, not split
    (',3,2,', 5, (3,), (3, 2)),        # the author strips outer commas
    ('1,1,1,1,1,1', 4, (1, 2, 3), (1, 1, 1, 1)),
])
def test_parse_author_rule(text, count, positions, sizes):
    parts = dividers.parse(text, count, 'list')
    assert (parts.positions, parts.sizes) == (positions, sizes)
    assert sum(parts.sizes) == count


@pytest.mark.parametrize('text, count, message', [
    ('', 3, 'list: compartment list is empty'),
    (',', 3, 'list: compartment list is empty'),
    ('a', 3, "list: compartment 'a' is not a positive whole number"),
    ('0,3', 3, "list: compartment '0' is not a positive whole number"),
    ('-1', 3, "list: compartment '-1' is not a positive whole number"),
    ('1.5', 3, "list: compartment '1.5' is not a positive whole number"),
    ('3,,2', 5, "list: compartment '' is not a positive whole number"),
    ('1', 0, 'list: grid count must be a whole number of at least 1'),
    ('1', True, 'list: grid count must be a whole number of at least 1'),
])
def test_parse_named_errors(text, count, message):
    with pytest.raises(dividers.CompartmentListError) as exc:
        dividers.parse(text, count, 'list')
    assert str(exc.value) == message


@pytest.mark.parametrize('values, name', [
    ({**WIDTH, 'shell_width_compartment_list': 'x'}, 'shell_width_compartment_list'),
    ({**HEIGHT, 'shell_height_compartment_list': '0'}, 'shell_height_compartment_list'),
    ({**ORGANISER, 'container_width_compartment_list': '1,-1'}, 'container_width_compartment_list'),
    ({**ORGANISER, 'container_depth_compartment_list': '2;3'}, 'container_depth_compartment_list'),
])
def test_registry_build_names_the_bad_list(values, name):
    with pytest.raises(ValueError, match=f'^{name}: '):
        m.build(values)


def test_container_divider_named_errors():
    with pytest.raises(dividers.CompartmentListError, match='too many divider walls'):
        container.divider_walls({**ORGANISER, 'horizontal_grids': 1, 'container_width_grid_count': 20,
                                 'container_width_compartment_list': ','.join(['1']*20)})
    with pytest.raises(dividers.CompartmentListError, match='do not rise above the floor fillet'):
        container.divider_walls({**ORGANISER, 'vertical_grids': 1,
                                 'container_divider_wall_height_offset': 20})


# ---------------------------------------------------------------- placement

def test_shell_walls_on_tile_boundaries():
    """[C] :1597-1626: 2*shell_thickness thick, width from -X, height from the top."""
    assert shell.divider_walls(WIDTH) == [('x', 3*28-70)]
    assert shell.divider_walls({**HEIGHT, 'vertical_grids': 5,
                                'shell_height_compartment_list': '2,3'}) == [('y', 70-2*28)]
    # Top/Bottom slot faces: the port keeps the wall on the boundary (the
    # author shifts it by the extra slot thickness, docs Deviations).
    for face in ('Top', 'Bottom'):
        assert shell.divider_walls({**HEIGHT, 'shell_slot_position': face}) == [('y', 0)]
    walls = shell.source_divider_walls({**WIDTH, 'shell_divider_wall_type': 'Solid'})
    bb = walls[0].bounding_box()
    assert (bb.min.X, bb.max.X, bb.min.Z) == pytest.approx((14-2.4, 14+2.4, 0))


def test_back_magnets_and_stoppers_per_compartment():
    """[C] :1450-1469 per compartment; magnet rows at each compartment's bottom tile."""
    xs = sorted(round(x, 6) for x, _, _ in shell.source_back_magnet_positions(WIDTH))
    # 3 wide: boundaries 1|2 and 2|3 of the compartment; 2 wide: one, at 1|2.
    assert xs == [-42, -14, 42]
    stops = sorted(round(x, 6) for x, _, _ in shell.source_stopper_positions(WIDTH))
    assert stops == [-56, 0, 28, 56]
    tall = {**HEIGHT, 'vertical_grids': 5, 'shell_height_compartment_list': '2,3'}
    rows = sorted({round(y, 6) for _, y, _ in shell.source_back_magnet_positions(tall)})
    # Top compartment = tiles 3-4 (bottom tile 3), lower = tiles 0-2.
    assert rows == [-56+4.6, -56+3*28+4.6]


@pytest.mark.parametrize('lists', ['3,2', '1,4', '2,1,2'])
def test_top_slot_frees_every_stopper_tile(lists):
    """No Top-face slot pocket may meet a per-compartment stopper hole."""
    v = {**WIDTH, 'shell_width_compartment_list': lists, 'shell_slot_position': 'Top'}
    stops = [shell.AUTHOR_TO_MODEL*cut for cut in shell.source_stopper_cutters(v)]
    slots = shell.slot_fixtures(v).cutters
    assert len(slots) == 5*5-len(shell.stopper_columns(v))
    for stop in stops:
        assert all(getattr(stop & slot, 'volume', 0) < 1e-9 for slot in slots)


def test_container_walls_by_unit():
    """[C] :1615-1628: unit = (inner - n*1.2)/grid; inset = sum*unit + first + i*1.2."""
    v = {**ORGANISER}
    d = container.dimensions(v)
    walls = container.divider_walls(v)
    unit_x = (d.width-2*d.side-2*1.2)/3
    unit_z = (d.depth-d.front-d.back-1.2)/5
    xs = [w.low for w in walls if w.axis == 'x']
    zs = [w.high for w in walls if w.axis == 'z']
    assert xs == pytest.approx([-d.width/2+d.side+unit_x, -d.width/2+d.side+2*unit_x+1.2])
    assert zs == pytest.approx([d.depth-d.front-2*unit_z])
    body = container.source_divider_walls(v)[0]
    assert body.bounding_box().max.Y == pytest.approx(-d.height/2+d.side_height-10+d.bottom)


# ------------------------------------------------------------------ parity

@pytest.fixture(scope='module', params=[
    ('shell-divider-width', WIDTH),
    ('shell-divider-height', HEIGHT),
], ids=lambda case: case[0])
def shell_case(request, tmp_path_factory):
    from build123d import export_stl
    name, values = request.param
    values = {**values, 'honeycomb_ceiling': 'source'}
    before = shell.before_bed_chamfer(values)
    finished = shell.chamfer_bed(before, values)
    source = shell.AUTHOR_TO_MODEL.inverse()*finished
    path = tmp_path_factory.mktemp(name)/'port.stl'
    export_stl(source, str(path), tolerance=.01, angular_tolerance=.05)
    return name, values, before, finished, source, load_reference(path), load_reference(REFERENCES/f'{name}.stl')


@pytest.mark.audit
def test_shell_divider_parity(shell_case):
    """Same treatment as the D1/D2 shell parity (test_openconnect_drawer)."""
    name, values, before, finished, source, port, ref = shell_case
    assert finished.is_valid and len(finished.solids()) == 1
    assert port.is_watertight and port.body_count == 1
    assert bbox_parity(source, ref, tol=.05, mode='ordered', rtol=0,
                       pre_treatment=shell.AUTHOR_TO_MODEL.inverse()*before,
                       expected_reduction=(0, 0, 0), reduction_tol=1e-5)
    assert volume_parity(port, ref, rel=.01)
    edges = boundary_edges(ref, normal_z=-.99999, plane_tol=.02, decimals=6)
    edges = [(a, b) for a, b in edges if np.linalg.norm(np.asarray(a)-b) > 1e-8]
    classifier = audit._ClassifiedPart(source)
    for direction, a, b in [('port->ref', port, ref), ('ref->port', ref, port)]:
        points, distances = surface_distance(a, b, n=40000, seed=1, sampler='uniform',
                                             vertices=True, signed=False)
        contact = (source_contact_mask(points, values, classifier) if direction == 'ref->port'
                   else np.zeros(len(points), dtype=bool))
        assert contact.mean() < .01
        points, distances = points[~contact], distances[~contact]
        band = band_mask(points, edges, radius=.5)
        coverage, excluded = over_cap_exclusion(distances, band, cap=.15)
        kept = ~(band & (distances > .15))
        # Measured port->ref band shares .054 (width) / .067 (height, four
        # back-magnet mouth bevels instead of two) with nothing excluded.
        assert coverage <= {'shell-divider-width': .06, 'shell-divider-height': .075}[name]
        assert excluded <= .02
        assert distances[kept].max() <= .15
        print(f'PARITY | {name} | {direction} | {ref.volume:.3f} | {port.volume:.3f} | '
              f'{distances[kept].max():.6f} | contact {contact.mean():.4%}')


@pytest.mark.audit
def test_container_divider_parity(tmp_path):
    """Same treatment as the D3 container parity."""
    from build123d import export_stl
    from trimesh.proximity import closest_point
    values = {**ORGANISER, 'honeycomb_ceiling': 'source'}
    body = container.source_body(values)
    assert body.is_valid and len(body.solids()) == 1
    mesh = container.author_to_mesh(values)*body
    export_stl(mesh, str(tmp_path/'port.stl'), tolerance=.01, angular_tolerance=.05)
    port, ref = load_reference(tmp_path/'port.stl'), load_reference(REFERENCES/'container-divider-both.stl')
    assert port.body_count == 1
    assert bbox_parity(mesh, ref, tol=.05, mode='ordered', rtol=0)
    assert volume_parity(port, ref, rel=.002)
    classifier = audit._ClassifiedPart(mesh)
    for direction, a, b in [('port->ref', port, ref), ('ref->port', ref, port)]:
        points, distances = surface_distance(a, b, n=40000, seed=1, sampler='uniform',
                                             vertices=True, signed=False)
        skin = np.zeros(len(points), dtype=bool)
        if direction == 'ref->port':
            _, _, triangles = closest_point(ref, points)
            skin = container_skin_mask(points, ref.face_normals[triangles], values, classifier)
        assert skin.mean() < .04
        assert distances[~skin].max() <= .05, (direction, distances[~skin].max())
        print(f'PARITY | container-divider-both | {direction} | {ref.volume:.3f} | '
              f'{port.volume:.3f} | max {distances[~skin].max():.6f} | skin {skin.mean():.4%}')


def test_stopper_clip_parity(tmp_path):
    """stoppers.stl is the print frame itself: no transform, same pair, same bbox."""
    from build123d import export_stl
    part = stopper.build()
    assert part.is_valid and len(part.solids()) == 2
    bb = part.bounding_box()
    assert (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z) == pytest.approx(
        (-3.2, -8.3, 0, 31.2, 0, 2), abs=1e-9)
    a, b = part.solids()
    assert a.volume == pytest.approx(b.volume, rel=1e-9)
    export_stl(part, str(tmp_path/'port.stl'), tolerance=.001, angular_tolerance=.05)
    port, ref = load_reference(tmp_path/'port.stl'), load_reference(REFERENCES/'stoppers.stl')
    assert bbox_parity(part, ref, tol=.001, mode='ordered', rtol=0)
    assert volume_parity(port, ref, rel=1e-4)
    classifier = audit._ClassifiedPart(part)
    for direction, a, b in [('port->ref', port, ref), ('ref->port', ref, port)]:
        points, distances = surface_distance(a, b, n=20000, seed=1, sampler='uniform',
                                             vertices=True, signed=False)
        # The reference keeps its cuboids' coincident faces inside the clip
        # (flange/shaft Y=-0.7, shaft/leg Y=-2.3, leg/nub X=+-2.2): solid
        # on every side in the port, so no physical boundary is masked.
        steps = np.vstack([np.eye(3), -np.eye(3)])*.01
        skin = np.array([direction == 'ref->port' and
                         all(classifier.is_inside(tuple(p+s)) for s in steps) for p in points])
        if direction == 'ref->port':
            # Independent size check: the reference's surplus area (420.0 vs
            # 295.5 mm2) is exactly its internal faces.
            assert abs(skin.mean()-(1-part.area/ref.area)) < .05
        # $fn=64 chords vs exact arcs (r 0.4).
        assert distances[~skin].max() <= .02, (direction, distances[~skin].max())


# ------------------------------------------------------------ stopper audit

def test_stopper_exclusions_cover_only_the_snap_features():
    """Q2 (pending): only the 0.7 flange (+ flare) and 0.6 nubs miss 0.9 mm."""
    v = m.SPEC.resolve_values({'part': 'stopper_clips'})
    part = m.build(v)
    raw = audit.audit(part, m.SPEC.print_orientation, model='clips_raw', print_frame=m.print_frame(v))
    assert raw.min_wall_mm == pytest.approx(.7, abs=.01)
    clean = audit.audit(part, m.SPEC.print_orientation, exclusions=m.audit_exclusions(v),
                        model='clips', print_frame=m.print_frame(v))
    assert clean.ok, clean.format()
    assert clean.min_wall_mm >= 1.5
    # Envelopes, not the clip: the shaft and both legs stay audited.
    regions = m.audit_exclusions(v)
    assert sum(r.volume for r in regions) < .3*part.volume
    d = stopper.dimensions(v)
    leg = -d['flange_depth']-d['shaft']-d['length']/2
    for x in (0, -1.4, 1.4, 28, 26.6, 29.4):
        for y in (-d['flange_depth']-d['shaft']/2-.4, leg):
            assert not any(r.is_inside((x, y, 1)) for r in regions), (x, y)


@pytest.mark.parametrize('length', [4, 12])
def test_stopper_clip_length_endpoints(length):
    d = stopper.dimensions({'stopper_clip_length': length})
    part = stopper.build({'stopper_clip_length': length})
    assert part.is_valid and len(part.solids()) == 2
    assert part.bounding_box().size.Y == pytest.approx(d['flange_depth']+d['shaft']+length)


# ------------------------------------------------------------------ presets

@pytest.mark.audit
@pytest.mark.parametrize('preset', ['two-compartments', 'organiser', 'stopper-clips'])
def test_new_presets_build(preset):
    values = next(p.values for p in m.SPEC.presets if p.id == preset)
    part = m.build(values)
    assert part.is_valid
    assert len(part.solids()) == (2 if values.get('part') == 'stopper_clips' else 1)
    print(f'VOLUME | {preset} | {part.volume/1000:.3f} cm3')
