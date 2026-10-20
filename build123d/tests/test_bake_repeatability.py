"""The diagnostic must not mistake scalar agreement for equal surfaces."""
from pathlib import Path
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.bake_repeatability import _oriented_triangles, compare_bakes, compare_stl, main


def write_mesh(path, vertices, faces):
    trimesh.Trimesh(vertices=vertices, faces=faces, process=False).export(path)


@pytest.fixture
def box():
    return trimesh.creation.box()


def test_face_and_vertex_order_and_cyclic_starts_are_equivalent(tmp_path, box):
    before, after = tmp_path / "a.stl", tmp_path / "b.stl"
    write_mesh(before, box.vertices, box.faces)
    # Reverse vertex storage, reverse face storage, rotate each triangle's
    # start; every directed triangle and its multiplicity remain intact.
    write_mesh(after, box.vertices[::-1], len(box.vertices) - 1 - np.roll(box.faces[::-1], 1, axis=1))
    report = compare_stl(before, after)
    assert before.read_bytes() != after.read_bytes()
    assert report["classification"] == "same-oriented-triangles"
    assert report["before"]["watertight"] and report["after"]["watertight"]


def test_reversed_winding_is_not_ordering(tmp_path, box):
    before, after = tmp_path / "a.stl", tmp_path / "b.stl"
    write_mesh(before, box.vertices, box.faces)
    write_mesh(after, box.vertices, box.faces[:, ::-1])
    report = compare_stl(before, after)
    assert report["same_vertex_coordinates"]
    assert not report["same_oriented_triangles"]
    assert report["classification"] == "connectivity-or-winding"
    assert report["before"]["volume_mm3"] > 0 > report["after"]["volume_mm3"]


def test_changed_diagonal_is_not_ordering_even_with_equal_metrics(tmp_path):
    before, after = tmp_path / "a.stl", tmp_path / "b.stl"
    vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [.5, .5, 1]]
    sides = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    write_mesh(before, vertices, sides + [[0, 2, 1], [0, 3, 2]])
    write_mesh(after, vertices, sides + [[0, 3, 1], [1, 3, 2]])
    report = compare_stl(before, after)
    assert report["before"] == report["after"]
    assert report["before"]["watertight"]
    assert report["classification"] == "connectivity-or-winding"


def test_duplicate_triangles_are_not_discarded(tmp_path, box):
    before, after = tmp_path / "a.stl", tmp_path / "b.stl"
    write_mesh(before, box.vertices, box.faces)
    write_mesh(after, box.vertices, np.vstack((box.faces, box.faces[:1])))
    assert not compare_stl(before, after)["same_oriented_triangles"]


def test_signed_zero_and_collapsed_triangle_cyclic_starts():
    a = trimesh.Trimesh(vertices=[[0, 0, 0], [1, 1, 1]], faces=[[0, 0, 1]], process=False)
    b = trimesh.Trimesh(vertices=[[-0.0, 0, 0], [1, 1, 1]], faces=[[0, 1, 0]], process=False)
    np.testing.assert_array_equal(_oriented_triangles(a), _oriented_triangles(b))


def test_small_coordinate_change_is_not_hidden_by_vertex_welding(tmp_path, box):
    before, after = tmp_path / "a.stl", tmp_path / "b.stl"
    vertices = box.vertices + .5
    write_mesh(before, vertices, box.faces)
    vertices[0, 2] = 1e-10
    write_mesh(after, vertices, box.faces)
    assert compare_stl(before, after)["classification"] == "vertex-coordinates"


def test_byte_differences_and_missing_files_always_fail(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    for path in (a, b):
        (path / "preview.glb").write_bytes(b"same bytes")
    assert main([str(a), str(b)]) == 0
    (b / "preview.glb").write_bytes(b"different bytes")
    assert main([str(a), str(b)]) == 1
    (a / "extra.png").write_bytes(b"png")
    (b / "extra.3mf").write_bytes(b"3mf")
    report = compare_bakes(a, b)
    assert report["missing_after"] == ["extra.png"]
    assert report["missing_before"] == ["extra.3mf"]
    assert list(report["changes"]) == ["preview.glb"]
    assert not report["byte_identical"]


def test_identical_surfaces_still_report_byte_changes(tmp_path, box):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    write_mesh(a / "part.stl", box.vertices, box.faces)
    write_mesh(b / "part.stl", box.vertices, box.faces[::-1])
    assert main([str(a), str(b)]) == 1
    assert compare_bakes(a, b)["changes"]["part.stl"]["same_oriented_triangles"]


def test_missing_and_empty_directories_do_not_report_success(tmp_path):
    with pytest.raises(ValueError, match="not a bake directory"):
        compare_bakes(tmp_path / "missing", tmp_path)
    with pytest.raises(ValueError, match="empty bake directory"):
        compare_bakes(tmp_path, tmp_path)
