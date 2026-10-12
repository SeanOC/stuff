# SPDX-License-Identifier: CC-BY-SA-4.0
"""Source-pinned lattice, frame and degenerate-panel contracts."""
from math import sqrt
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from build123d import Part, Plane, section

from drawer import shell
from drawer.honeycomb import (HoneycombPanelTooSmall, front_alignment,
                             hole_polygons, honeycomb_panel, strut_dimensions)
from holders.openconnect_drawer import SPEC


def test_default_dimensions_and_front_alignment():
    spacing, strut, ir, radius = strut_dimensions()
    assert (spacing, strut, 2*ir, radius) == pytest.approx(
        (16.1658075373, 4.3301270189, 11.8356805184, 6.8333333333))
    assert front_alignment(134.8, 50.8) == pytest.approx((9, 3, (50.8-3*spacing)/2))
    p = next(p for p in SPEC.params if p.name == 'honeycomb_strut_hyp')
    assert (p.default, p.step, p.min, p.max) == (5, .1, None, None)


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
    assert np.ptp(hole, axis=0)[2] > 10  # REV 2 author-geometry bridge exception
    mids = ref.vertices[ref.face_adjacency_edges].mean(axis=1)
    at_frame = np.linalg.norm(mids-(65.07575989, -26.79999924, 126.44551849), axis=1) < 1e-4
    assert at_frame.sum() == 1
    assert np.degrees(ref.face_adjacency_angles[at_frame])[0] == pytest.approx(150, abs=.001)
    clipped = next(p for p in paths if np.allclose(
        p.min(axis=0), (63.1666641, -27, 39.0031891), atol=1e-4))
    assert np.ptp(clipped, axis=0)[0] == pytest.approx(1.9090958, abs=1e-5)


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
