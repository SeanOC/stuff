"""Contract tests for the software thumbnail rasteriser (bead pst-o0wy).

These exercise the ACTUAL headless backend (pure numpy — no GL/EGL/OSMesa,
so identical in CI, on Vercel, and locally) and assert the properties the
old matplotlib plot_trisurf path lacked:

  * a real z-buffer: a nearer surface occludes a farther one (no depth
    bleed-through),
  * smooth/uniform shading across a flat face (no triangle-fan striping),
  * a rendered part with a transparent background.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.thumbnail import (  # noqa: E402
    _BASE_COLOR,
    _PAD,
    _RES,
    _VIEW_DIR,
    _WORLD_UP,
    _camera_basis,
    _render_view,
    _scene_mesh_and_colors,
    PlaneSpec,
    ReviewContext,
    model_to_glb_point,
    render_review,
    render_thumbnail,
    render_thumbnail_from_mesh,
)

# Look straight down -Z (eye on +Z); screen right=+X, up=+Y — a predictable
# frame for constructing occlusion by hand.
_DOWN_Z = np.array([0.0, 0.0, 1.0])
_UP_Y = np.array([0.0, 1.0, 0.0])


def _center(rgba: np.ndarray) -> np.ndarray:
    h, w = rgba.shape[:2]
    return rgba[h // 2, w // 2]


def test_zbuffer_nearer_surface_occludes_farther():
    """A near triangle in front of a far one wins the z-test at the overlap.

    Painter's algorithm centroid-sorting is exactly what fails here; a real
    per-pixel depth buffer makes the near surface's shade win regardless of
    triangle order.
    """
    # Far triangle at z=0, flat-facing the eye.
    far_v = np.array([[-3, -3, 0], [3, -3, 0], [0, 3, 0]], float)
    far_f = np.array([[0, 1, 2]])
    far_n = np.tile([0.0, 0.0, 1.0], (3, 1))
    # Near triangle at z=1 (closer to the +Z eye), tilted so it shades
    # DIFFERENTLY from the far one.
    near_n_vec = np.array([0.0, 0.6, 0.8])
    near_v = np.array([[-1, -1, 1], [1, -1, 1], [0, 1, 1]], float)
    near_f = np.array([[0, 1, 2]])
    near_n = np.tile(near_n_vec, (3, 1))

    def render(v, f, n):
        return _render_view(
            v, f, n, color=_BASE_COLOR, view_dir=_DOWN_Z, world_up=_UP_Y, res=64
        )

    far_only = _center(render(far_v, far_f, far_n))
    near_only = _center(render(near_v, near_f, near_n))
    # Sanity: the two surfaces shade differently, so the occlusion test is
    # meaningful.
    assert not np.allclose(far_only[:3], near_only[:3], atol=0.02)

    # Combine (order deliberately puts the FAR triangle last so a naive
    # last-wins / painter path would show the far shade).
    v = np.vstack([near_v, far_v])
    f = np.array([[0, 1, 2], [3, 4, 5]])
    n = np.vstack([near_n, far_n])
    both = _center(render(v, f, n))
    assert both[3] > 0.5  # opaque at the overlap
    assert np.allclose(both[:3], near_only[:3], atol=0.02), "near surface must win"
    assert not np.allclose(both[:3], far_only[:3], atol=0.02)


def test_flat_face_shades_uniformly():
    """A flat quad (two coplanar tris, shared normal) has ~uniform colour.

    The triangle-fan striping of plot_trisurf(shade=True) is precisely a
    NON-uniform gradient across a flat face; smooth per-vertex normals make
    a genuinely flat face a single flat tone.
    """
    v = np.array([[-2, -2, 0], [2, -2, 0], [2, 2, 0], [-2, 2, 0]], float)
    f = np.array([[0, 1, 2], [0, 2, 3]])
    n = np.tile([0.0, 0.0, 1.0], (4, 1))
    rgba = _render_view(
        v, f, n, color=_BASE_COLOR, view_dir=_DOWN_Z, world_up=_UP_Y, res=64
    )
    opaque = rgba[rgba[..., 3] > 0.5][:, :3]
    assert opaque.shape[0] > 100  # the face actually rendered
    # Interior of a flat face is a single tone; supersample edges add a thin
    # AA fringe, so bound the spread rather than demanding exact equality.
    assert float(opaque.std(axis=0).max()) < 0.02


def test_render_thumbnail_from_mesh_writes_transparent_png(tmp_path):
    """End-to-end: a box renders to a 400x400 RGBA PNG with a clear ground."""
    box = trimesh.creation.box(extents=(20, 20, 20))
    out = tmp_path / "thumb.png"
    render_thumbnail_from_mesh(box.vertices, box.faces, box.vertex_normals, out)

    assert out.exists()
    im = Image.open(out)
    assert im.mode == "RGBA"
    assert im.size == (400, 400)
    a = np.asarray(im)
    alpha = a[..., 3]
    assert (alpha > 0).any(), "the part must render some opaque pixels"
    assert (alpha == 0).any(), "the background must stay transparent"
    # Corners are background → transparent.
    assert alpha[0, 0] == 0 and alpha[-1, -1] == 0


@pytest.fixture
def two_colour_glb(tmp_path):
    from build123d import Box, Compound, Pos
    from scripts.export import export_glb

    # Independent solids: transforming a shared OCC shape can share its colour.
    dark = Pos(-20, 0, 0) * Box(20, 20, 20)
    bright = Pos(20, 0, 0) * Box(20, 20, 20)
    glb = tmp_path / "two-colour.glb"
    export_glb(Compound(children=[dark, bright]), glb, colour_parts=[
        ("dark", dark, (0.10, 0.10, 0.10, 1.0)),
        ("bright", bright, (0.96, 0.96, 0.96, 1.0)),
    ])
    return glb


def _screen_pixel(mesh, model_point, view_dir=_VIEW_DIR, world_up=_WORLD_UP, res=_RES):
    """Project a known top-face centre into the renderer's orthographic frame."""
    right, up, _ = _camera_basis(view_dir, world_up)
    projected = mesh.vertices @ np.array([right, up]).T
    lo, hi = projected.min(axis=0), projected.max(axis=0)
    scale = res * (1 - 2 * _PAD) / max(hi - lo)
    xy = (model_to_glb_point(model_point) @ np.array([right, up]).T - (hi + lo) / 2) * scale
    return int(res / 2 - xy[1]), int(res / 2 + xy[0])


def test_glb_part_colours_match_authored_srgb(two_colour_glb, tmp_path):
    out = tmp_path / "thumb.png"
    render_thumbnail(two_colour_glb, out)
    mesh = trimesh.load(two_colour_glb, force="scene").to_geometry()
    pixels = np.asarray(Image.open(out))
    for x, expected in [(-20, 26), (20, 245)]:
        row, col = _screen_pixel(mesh, (x, 0, 10))
        pixel = pixels[row, col]
        assert pixel[3] == 255
        # Raw linear factors (~3 and 232) cannot satisfy these bands. The
        # tolerance allows for uint8 linear-factor quantisation, especially
        # near black, as well as the existing shading.
        assert np.all(np.abs(pixel[:3].astype(int) - expected) <= 8), pixel


def test_uncoloured_glb_preserves_thumbnail_bytes(tmp_path):
    from build123d import Box
    from scripts.export import export_glb

    glb = tmp_path / "plain.glb"
    export_glb(Box(20, 20, 20), glb, None)
    actual, expected = tmp_path / "actual.png", tmp_path / "expected.png"
    render_thumbnail(glb, actual)
    mesh = trimesh.load(glb, force="scene").to_geometry()
    render_thumbnail_from_mesh(
        mesh.vertices, mesh.faces, mesh.vertex_normals, expected, color=None,
    )
    assert actual.read_bytes() == expected.read_bytes()


@pytest.mark.parametrize("renderer", [render_thumbnail, render_review])
def test_unreferenced_scene_geometry_does_not_affect_render(
    two_colour_glb, tmp_path, monkeypatch, renderer,
):
    scene = trimesh.load(two_colour_glb, force="scene")
    expected, actual = tmp_path / "expected.png", tmp_path / "actual.png"
    renderer(two_colour_glb, expected)
    # Legal GLBs can retain meshes without a node referencing them, as in
    # the cartridge holder's full_holder preset. They must not affect either
    # the colour alignment or the rendered bounds/pixels.
    scene.geometry["orphan"] = trimesh.creation.box(extents=(1000, 1000, 1000))
    assert "orphan" not in scene.graph.geometry_nodes
    monkeypatch.setattr(trimesh, "load", lambda *args, **kwargs: scene)
    renderer(two_colour_glb, actual)
    assert actual.read_bytes() == expected.read_bytes()


def test_multicolour_review_keeps_all_five_tiles(two_colour_glb, tmp_path):
    out = tmp_path / "review.png"
    ctx = ReviewContext("two-colour", (0, 0, 1),
                        (PlaneSpec((0, 0, 0), (0, 1, 0), "midplane"),), ())
    render_review(two_colour_glb, out, ctx=ctx, res=128)
    with Image.open(out) as image:
        assert image.size == (640, 176)
        pixels = np.asarray(image)
    for i in range(5):
        assert np.any(pixels[28:156, i * 128:(i + 1) * 128] < 200)
    mesh = trimesh.load(two_colour_glb, force="scene").to_geometry()
    # Check the ISO tile's actual part colours, not just the sheet dimensions.
    for x, expected in [(-20, 26), (20, 245)]:
        row, col = _screen_pixel(mesh, (x, 0, 10), res=128)
        assert np.all(np.abs(pixels[row + 28, col].astype(int) - expected) <= 8)


def test_scene_colours_follow_graph_order_and_default_uncoloured_faces():
    plain = trimesh.creation.box()
    coloured = trimesh.creation.box()
    coloured.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(baseColorFactor=[255, 0, 0, 255]),
    )
    scene = trimesh.Scene()
    scene.add_geometry(plain, geom_name="plain")
    scene.add_geometry(coloured, geom_name="coloured")
    # Deliberately reverse geometry insertion order without changing the graph.
    scene.geometry = dict(reversed(list(scene.geometry.items())))
    mesh, colors = _scene_mesh_and_colors(scene)
    assert np.array_equal(mesh.vertices, scene.to_geometry().vertices)
    assert np.allclose(colors[:len(plain.faces)], _BASE_COLOR)
    assert np.allclose(colors[len(plain.faces):], [1, 0, 0])


def test_thumbnail_is_in_production_bake_cache_key():
    from scripts.export import _key_builder

    keys = _key_builder()
    assert ROOT / "scripts" / "thumbnail.py" in keys.export_closure
