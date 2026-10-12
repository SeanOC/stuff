# SPDX-License-Identifier: CC-BY-SA-4.0
"""Source-pinned lattice, frame and degenerate-panel contracts."""
from math import hypot, sqrt
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from build123d import Part, Plane, section

from drawer import shell
from drawer.honeycomb import (HoneycombPanelTooSmall, HoneycombStrutOutOfRange, front_alignment,
                             hole_polygons, honeycomb_panel, strut_dimensions)
from holders.openconnect_drawer import SPEC


def test_default_dimensions_and_front_alignment():
    spacing, strut, ir, radius = strut_dimensions()
    assert (spacing, strut, 2*ir, radius) == pytest.approx(
        (16.1658075373, 4.3301270189, 11.8356805184, 6.8333333333))
    assert front_alignment(134.8, 50.8) == pytest.approx((9, 3, (50.8-3*spacing)/2))
    p = next(p for p in SPEC.params if p.name == 'honeycomb_strut_hyp')
    assert (p.default, p.step, p.min, p.max) == (5, .1, 1.1, 16.3)


@pytest.mark.parametrize('values', [
    {'honeycomb_ceiling': 'source'},
    {'honeycomb_strut_hyp': 1.09},
    {'honeycomb_strut_hyp': 16.4},
])
def test_catalog_rejects_unsupported_honeycomb_settings(values):
    with pytest.raises(ValueError, match=next(iter(values))):
        SPEC.resolve_values(values)


def _opening_width(polygon):
    corners = list(polygon.minimum_rotated_rectangle.exterior.coords)
    return min(hypot(a[0]-b[0], a[1]-b[1])
               for a, b in zip(corners, corners[1:]))


@pytest.mark.parametrize('preset', SPEC.presets, ids=lambda preset: preset.id)
def test_full_hex_opening_meets_minimum_across_catalog_range(preset):
    param = next(p for p in SPEC.params if p.name == 'honeycomb_strut_hyp')
    for tick in range(round((param.max-param.min)/param.step)+1):
        strut = round(param.min+tick*param.step, 1)
        values = SPEC.resolve_values(preset.values | {'honeycomb_strut_hyp': strut})
        widths = []
        for _, layout in shell.honeycomb_layouts(values):
            for polygon in layout.openings:
                corners = list(polygon.exterior.coords)
                lengths = [hypot(a[0]-b[0], a[1]-b[1])
                           for a, b in zip(corners, corners[1:])]
                # Full source hexes have six equal sides; partial cells do not.
                if len(lengths) == 6 and max(lengths)-min(lengths) < 1e-7:
                    widths.append(_opening_width(polygon))
        assert widths, (preset.id, strut)
        assert min(widths) >= 2.0, (preset.id, strut, min(widths))
    assert min(widths) == pytest.approx(2.0495934556, abs=1e-8)


@pytest.mark.parametrize('strut,preset_id,minimum,under_2,total', [
    (5.0, 'default', 1.9090937647, 16, 97),
    (5.0, 'small', 1.4162909656, 10, 19),
    (5.0, 'top-slot', 1.9090937647, 16, 97),
    (16.3, 'default', .4730067020, 14, 63),
    (16.3, 'small', .4730067020, 4, 5),
    (16.3, 'top-slot', .4730067020, 14, 63),
])
def test_frame_clipped_opening_exception_measurements(strut, preset_id, minimum, under_2, total):
    # pst-t0ob3.2 REV 7: decorative closed slots are exempt from Ø2.
    # Pin final profiles after roofing, including split partial cells.
    preset = next(p for p in SPEC.presets if p.id == preset_id)
    values = SPEC.resolve_values(preset.values | {'honeycomb_strut_hyp': strut})
    widths = []
    for _, layout in shell.honeycomb_layouts(values):
        for profile, _, _ in layout.profiles((1, 0)):
            polygons = [profile] if profile.geom_type == 'Polygon' else profile.geoms
            for polygon in polygons:
                widths.append(_opening_width(polygon))
    assert len(widths) == total
    assert sum(width < 2 for width in widths) == under_2
    assert min(widths) == pytest.approx(minimum, abs=1e-8)


@pytest.mark.parametrize('strut', [0, -1, 1.09, float('inf'), float('nan'), 20])
def test_unbuildable_strut_has_named_error(strut):
    with pytest.raises(HoneycombStrutOutOfRange):
        shell.source_honeycomb_cutters({'honeycomb_strut_hyp': strut})


def test_panel_frame_struts_holes_and_envelope():
    width, height, thickness = 138.8, 138.8117749006, 2.4
    p = honeycomb_panel(width, height, thickness)
    assert isinstance(p, Part)
    assert p.is_valid and len(p.solids()) == 1
    assert tuple(p.bounding_box().size) == pytest.approx((width, height, thickness))
    polygons = hole_polygons(width, height)
    # The padded, centred lattice leaves 97 full/partial openings after
    # clipping, independently counted in the reference STL section below.
    assert len(polygons) == 9*9 + 2*8  # nine full rows, two clipped boundary rows
    assert len(section(p, section_by=Plane.XY).faces()[0].inner_wires()) == 97
    _, strut, ir, radius = strut_dimensions()
    assert min(x for hole in polygons for x, _ in hole) == pytest.approx(-width/2+strut)
    assert max(y for hole in polygons for _, y in hole) == pytest.approx(height/2-strut)
    # Adjacent hexes normal to their flats retain the perpendicular strut.
    assert 14*2/sqrt(3)-2*ir == pytest.approx(strut)
    assert p.volume == pytest.approx((width*height-sum(
        abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(hole, hole[1:]+hole[:1])))/2
        for hole in polygons))*thickness)


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('delta', [-1, 0])
def test_strict_source_guard(axis, delta):
    spacing, strut, *_ = strut_dimensions()
    sizes = [60, 60]
    sizes[axis] = 2*strut+spacing+delta
    with pytest.raises(HoneycombPanelTooSmall, match='2\\*frame \\+ spacing'):
        honeycomb_panel(*sizes, 2.4)


def test_shell_propagates_small_panel_error():
    with pytest.raises(HoneycombPanelTooSmall):
        shell.source_honeycomb_cutters(dict(horizontal_grids=1, shell_outer_chamfer=4))
    assert shell.source_honeycomb_cutters(dict(shell_bottom_wall_type='Solid')) == []
    assert shell.source_honeycomb_cutters(dict(shell_slot_position='Bottom')) == []


def test_side_magnet_infill_includes_hole_clearance():
    # SCAD :1435/:1441 uses hole diameter (:479), including both .2 mm
    # clearances, rather than the nominal magnet's diameter.
    holes = shell.source_honeycomb_cutters(dict(
        shell_bottom_wall_type='Solid', shell_side_wall_type='Honeycomb'))
    assert max(h.bounding_box().max.Z for h in holes) == pytest.approx(140-(6+6.4+3))


def test_reference_bottom_count_orientation_and_ceiling_span():
    import numpy as np
    import trimesh
    from pathlib import Path
    ref = trimesh.load_mesh(Path(__file__).resolve().parents[2]/
                            'assets/openConnect-drawer/mesh/shell-default.stl')
    paths = ref.section(plane_origin=(0, -27, 0), plane_normal=(0, 1, 0)).discrete
    assert len(paths)-1 == 97
    # Full hole centred at source (14, -27, 90.8072594). Section vertices
    # measure both orientations and the conservative flat-to-flat span.
    hole = next(p for p in paths if np.allclose(
        (p.min(axis=0)+p.max(axis=0))/2, (14, -27, 90.8072594), atol=1e-4))
    assert np.ptp(hole, axis=0) == pytest.approx((13.6666667, 0, 11.8356805), abs=1e-5)
    roof = hole[np.abs(hole[:, 2]-hole[:, 2].max()) < 1e-5]
    assert np.ptp(roof, axis=0)[0] == pytest.approx(6.8333333, abs=1e-5)
    assert np.ptp(hole, axis=0)[2] > 10  # Vertical opening height, not the horizontal bridge span.
    mids = ref.vertices[ref.face_adjacency_edges].mean(axis=1)
    at_frame = np.linalg.norm(mids-(65.07575989, -26.79999924, 126.44551849), axis=1) < 1e-4
    assert at_frame.sum() == 1
    assert np.degrees(ref.face_adjacency_angles[at_frame])[0] == pytest.approx(150, abs=.001)
    clipped = next(p for p in paths if np.allclose(
        p.min(axis=0), (63.1666641, -27, 39.0031891), atol=1e-4))
    assert np.ptp(clipped, axis=0)[0] == pytest.approx(1.9090958, abs=1e-5)


@pytest.mark.parametrize('name,values,y,expected', [
    ('default', {}, -27, 9.4695507),
    ('1x1x1', dict(horizontal_grids=1, vertical_grids=1, depth_grids=1), -13, 7.8603461),
])
def test_clipped_ceiling_chords_match_reference(name, values, y, expected):
    import numpy as np
    import trimesh
    ref = trimesh.load_mesh(Path(__file__).resolve().parents[2]/
                            f'assets/openConnect-drawer/mesh/shell-{name}.stl')
    paths = ref.section(plane_origin=(0, y, 0), plane_normal=(0, 1, 0)).discrete
    # Drop the enclosing wall perimeter, then measure each opening's top
    # horizontal chord independently of the production local-width scan.
    holes = sorted(paths, key=lambda p: np.ptp(p[:, 0])*np.ptp(p[:, 2]))[:-1]
    reference_chords = [np.ptp(p[np.abs(p[:, 2]-p[:, 2].max()) < 1e-5, 0])
                        for p in holes]
    assert max(reference_chords) == pytest.approx(expected, abs=1e-5)
    ceilings = [f for h in shell.source_honeycomb_cutters(values)
                for f in h.faces() if f.normal_at().Z > .999]
    assert max(max(f.bounding_box().size.X, f.bounding_box().size.Y)
               for f in ceilings) == pytest.approx(expected, abs=1e-5)


def test_cached_exact_ceiling_exclusions_preserve_membership():
    from tests.print_audit import _ExactExclusion
    regions = shell.honeycomb_ceiling_regions(
        dict(horizontal_grids=1, vertical_grids=1, depth_grids=1))
    assert regions
    for region in regions:
        cached = _ExactExclusion(region)
        bb = region.bounding_box()
        points = [tuple(bb.center()), tuple(bb.min), tuple(bb.max), (1000, 1000, 1000)]
        for face in region.faces():
            p, n = face.center(), face.normal_at()
            points.extend(tuple(p+n*t) for t in (-.01, -1e-7, 0, 1e-7, .01))
        for point in points:
            assert cached.is_inside(point) == region.is_inside(point, tolerance=1e-6)


@pytest.mark.parametrize('values,expected', [
    ({}, 9.4695507),
    (dict(horizontal_grids=1, vertical_grids=1, depth_grids=1), 7.8603461),
    (dict(honeycomb_strut_hyp=4.7), 10.0695507),
    (dict(honeycomb_strut_hyp=2.0), 15.4695507),
    (dict(horizontal_grids=2, vertical_grids=1, depth_grids=2), 12.3054614),
    (dict(shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb'), 13.2299342),
    (dict(horizontal_grids=8, vertical_grids=8, depth_grids=8), 11.3003066),
    (dict(shell_thickness=4), 10.3933111),
    (dict(shell_side_wall_type='Honeycomb'), 11.9795043),
    (dict(shell_top_wall_type='Honeycomb'), 13.2299338),
    (dict(shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb',
          honeycomb_strut_hyp=2), 16.2299338),
])
def test_ceiling_exclusions_never_waive_over_limit_chord(values, expected):
    values = {**values, "honeycomb_ceiling": "source"}
    from drawer.constants import MAX_BRIDGE_MM
    from tests.print_audit import MAX_BRIDGE_MM as audit_limit
    assert MAX_BRIDGE_MM == audit_limit
    ceilings = [f for h in shell.source_honeycomb_cutters(values)
                for f in h.faces() if f.normal_at().Z > .999]
    chords = [max(f.bounding_box().size.X, f.bounding_box().size.Y)
              for f in ceilings]
    assert max(chords) == pytest.approx(expected, abs=1e-5)
    regions = [shell.AUTHOR_TO_MODEL.inverse()*r
               for r in shell.honeycomb_ceiling_regions(values)]
    assert regions
    assert len(regions) == sum(chord <= MAX_BRIDGE_MM for chord in chords)
    # Slabs extend .0005 mm to each side of their source face.
    excluded_max = max(max(r.bounding_box().size.X, r.bounding_box().size.Y)
                       for r in regions)
    assert excluded_max <= MAX_BRIDGE_MM+.001
    if expected <= MAX_BRIDGE_MM:
        assert excluded_max == pytest.approx(expected, abs=.001)


@pytest.mark.parametrize('name,values,source_count,roofed_count', [
    ('default', {}, 97, 97),
    ('small', dict(horizontal_grids=2, vertical_grids=1, depth_grids=2), 17, 19),
    ('top-slot', dict(shell_slot_position='Top'), 97, 97),
    ('strut-2', dict(honeycomb_strut_hyp=2), 99, 103),
])
def test_roofed_profiles_match_independent_source_oracle(name, values, source_count, roofed_count):
    import runpy
    oracle = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                               'scripts/check-drawer-roof-contract.py'))['inspect']
    measured = oracle(name, {**values, 'honeycomb_ceiling': 'source'}, source_count)
    assert measured['roofed_openings'] == roofed_count
    assert len(shell.source_honeycomb_cutters(values)) == roofed_count
    removed = 0
    for _, layout in shell.honeycomb_layouts(values):
        for source, (roofed, chord, changed) in zip(layout.openings, layout.profiles((1, 0))):
            removed += source.area-roofed.area
            assert roofed.difference(source).area < 1e-8
            if changed:
                assert roofed.area < source.area
                assert roofed.area >= source.area-chord**2/4-1e-8
            else:
                assert roofed.symmetric_difference(source).area < 1e-8
    assert removed == pytest.approx(measured['removed_area_mm2'], abs=1e-7)


@pytest.mark.parametrize('values', [{}, dict(horizontal_grids=2, vertical_grids=1, depth_grids=2)])
def test_roof_volume_matches_polygon_area(values):
    source = shell.build({**values, 'honeycomb_ceiling': 'source'})
    roofed = shell.build(values)
    removed = sum(original.area-profile.area
                  for _, layout in shell.honeycomb_layouts(values)
                  for original, (profile, _, _) in zip(layout.openings, layout.profiles((1, 0))))
    expected = removed*shell.dimensions(values).wall
    assert roofed.volume-source.volume == pytest.approx(expected, rel=.01, abs=1e-6)
    print(f'VOLUME | {values} | source {source.volume:.6f} | roofed {roofed.volume:.6f}')


@pytest.mark.parametrize('values', [
    dict(shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb'),
    dict(shell_top_wall_type='Honeycomb', shell_side_wall_type='Honeycomb', honeycomb_strut_hyp=2),
    dict(honeycomb_strut_hyp=1.1), dict(honeycomb_strut_hyp=4.7),
])
def test_roofed_geometry_has_no_over_limit_flat_ceiling(values):
    from drawer.constants import MAX_BRIDGE_MM
    rows = shell.honeycomb_ceiling_chords(values)
    assert any(roofed for _, _, roofed in rows)
    assert all(chord <= MAX_BRIDGE_MM for _, chord, roofed in rows if not roofed)
    # Independent 3D check: flags alone cannot make the analytic audit pass.
    flat = [face for hole in shell.source_honeycomb_cutters(values)
            for face in hole.faces() if face.normal_at().Z > .999]
    assert all(max(f.bounding_box().size.X, f.bounding_box().size.Y) <= MAX_BRIDGE_MM+1e-7
               for f in flat)
    # The bridge waiver must not hide the new 45-degree roof faces.
    for region in shell.honeycomb_ceiling_regions(values):
        assert (shell.AUTHOR_TO_MODEL.inverse()*region).bounding_box().size.Z < .002


def test_panel_roof_direction_and_span_api():
    from drawer.honeycomb import HoneycombLayout
    from shapely.geometry import Polygon
    opening = Polygon([(0, 0), (12, 0), (12, 8), (0, 8)])
    layout = HoneycombLayout([opening], 'roofed', 'Bottom')
    assert layout.ceiling_chords((0, 1)) == [('Bottom', 12, True)]
    assert layout.ceiling_chords((1, 0)) == [('Bottom', 8, False)]
    profile, _, _ = layout.profiles((0, 1))[0]
    assert profile.area == pytest.approx(12*8-12**2/4)
    panel = honeycomb_panel(50, 50, 2.4, ceiling='roofed')
    assert panel.ceiling_chords((1, 0))


@pytest.mark.parametrize('slot_face', shell.SLOT_FACES)
def test_wall_clipping_stays_centred_when_mount_face_moves(slot_face):
    # The source wall window and lattice translate together when the slot
    # backing moves a side face. The 2D window must not apply that offset twice.
    values = dict(shell_slot_position=slot_face, shell_top_wall_type='Honeycomb',
                  shell_side_wall_type='Honeycomb', honeycomb_ceiling='source')
    for _, layout in shell.honeycomb_layouts(values):
        assert min(p.bounds[1] for p in layout.openings) == pytest.approx(
            -max(p.bounds[3] for p in layout.openings))
