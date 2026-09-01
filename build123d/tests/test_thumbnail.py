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
import trimesh
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.thumbnail import (  # noqa: E402
    _BASE_COLOR,
    _render_view,
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
