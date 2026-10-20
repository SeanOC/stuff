"""Face-local tessellation must become a closed, oriented 3MF mesh."""
import lib3mf
import pytest

from scripts.export import _weld_3mf_mesh


def test_weld_closes_face_seams_and_removes_collapsed_triangles():
    # An outward-facing tetrahedron, with each face owning its vertices.
    # Sub-grid noise at the shared corners must not leave open seams.
    corners = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
    winding = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
    vertices = [tuple(c + face * 1e-7 for c in corners[i])
                for face, triangle in enumerate(winding) for i in triangle]
    triangles = [(i, i + 1, i + 2) for i in range(0, 12, 3)]
    triangles.append((0, 3, 1))  # first two corners weld together
    positions, faces = _weld_3mf_mesh(vertices, triangles)

    model = lib3mf.get_wrapper().CreateModel()
    mesh = model.AddMeshObject()
    mesh.SetGeometry(positions, faces)
    assert mesh.GetVertexCount() == 4
    assert mesh.GetTriangleCount() == 4
    assert mesh.IsManifoldAndOriented()
    assert {tuple(p.Coordinates) for p in mesh.GetVertices()} == set(corners)


def test_weld_keeps_vertices_on_distinct_grid_points():
    # The weld is coordinate rounding, not a distance-based merge: adjacent
    # grid points remain separate even when the inputs are <1e-6 mm apart.
    positions, faces = _weld_3mf_mesh(
        [(0.49e-6, 0, 0), (0.51e-6, 0, 0), (0, 1, 0)], [(0, 1, 2)])
    assert len(positions) == 3
    assert len(faces) == 1
    assert positions[0].Coordinates[0] == 0
    assert positions[1].Coordinates[0] == pytest.approx(1e-6)
