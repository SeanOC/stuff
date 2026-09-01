"""Depth-buffered, smooth-shaded gallery thumbnail renderer (bead pst-o0wy).

Replaces the matplotlib ``mplot3d.plot_trisurf`` path, which is a
painter's-algorithm rasteriser: it has no true z-buffer (whole triangles
are centroid-sorted, so overlapping surfaces bleed through) and flat
per-triangle shading (so flat faces show triangle-fan shading and curved
surfaces show facet striping). The interactive detail view does NOT show
those artefacts because three.js/WebGL has a real depth buffer and shades
the GLB's smooth vertex normals — the geometry was always fine; only the
PNG rasteriser was wrong.

This module is a tiny self-contained software rasteriser (numpy only) that
reproduces the WebGL properties the thumbnail was missing:

  * a real per-pixel z-buffer (no depth bleed-through),
  * Gouraud shading from smooth vertex normals (no facets / fan shading),
  * front-face culling + 2x supersampled anti-aliasing to match the crisp
    look of the antialiased three.js viewer.

It renders from the SAME baked GLB the detail viewer loads (single source
of truth, bead pst-1vi5) using that mesh's own smooth vertex normals, so
the card matches the live preset preview.

Crucially it uses NO OpenGL / EGL / OSMesa / display server: the preset
bake runs in the headless Vercel build image (scripts/bake-bd-presets.sh
in the `prebuild` hook) as well as in CI, and neither can spin up a GL
context or add system graphics libraries. A pure-numpy rasteriser is the
only renderer that satisfies "depth-buffered + smooth shading" AND "still
bakes headless on Vercel".
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

# --- Look, pinned so thumbnails are reproducible across CI and local runs.
# Camera is an orthographic iso view down the +X+Y+Z diagonal with +Y up —
# the same framing as the GLB viewer's default camera (three.js is Y-up and
# the OCP-exported GLB carries the Z-up→Y-up rotation, so we view it Y-up
# too). Lighting mirrors the viewer: ambient 0.6 + a camera headlight 0.9.
_VIEW_DIR = np.array([1.0, 1.0, 1.0])   # from the model toward the eye
_WORLD_UP = np.array([0.0, 1.0, 0.0])   # +Y up (GLB viewer frame)
_AMBIENT = 0.6
_KEY = 0.9
# Neutral cool-grey fill, close to the viewer's default GLB material tone.
_BASE_COLOR = np.array([0.62, 0.70, 0.80])
_RES = 400          # output PNG is _RES x _RES
_SUPERSAMPLE = 2    # render at 2x then box-downsample for anti-aliasing
_PAD = 0.06         # fraction of the frame left as margin around the part


def _camera_basis(
    view_dir: np.ndarray, world_up: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Orthonormal (right, up, toward-eye) basis for a view direction."""
    to_eye = view_dir / np.linalg.norm(view_dir)
    right = np.cross(world_up, to_eye)
    if np.linalg.norm(right) < 1e-6:
        # view_dir parallel to world_up (e.g. a straight-down top view) —
        # fall back to an alternate up so the basis stays well-defined.
        right = np.cross(np.array([0.0, 0.0, 1.0]), to_eye)
    right = right / np.linalg.norm(right)
    up = np.cross(to_eye, right)  # already unit (both operands unit, orthogonal)
    return right, up, to_eye


def _render_view(
    vertices: np.ndarray,
    faces: np.ndarray,
    normals: np.ndarray,
    *,
    color: np.ndarray,
    view_dir: np.ndarray,
    world_up: np.ndarray,
    res: int,
) -> np.ndarray:
    """Rasterise a single view to an (res, res, 4) float RGBA array [0,1].

    z-buffered, front-face culled, Gouraud-shaded, 2x supersampled. The
    background is transparent (alpha 0) so the card composites the part the
    same way the alpha:true GLB viewer does.
    """
    right, up, to_eye = _camera_basis(view_dir, world_up)

    v = np.asarray(vertices, float)
    n = np.asarray(normals, float)
    f = np.asarray(faces, np.int64)

    # World → camera screen space. sx/sy are view-plane coords, depth grows
    # away from the eye (smaller = nearer), so the z-test keeps the min.
    center = 0.5 * (v.max(0) + v.min(0))
    vc = v - center
    sx = vc @ right
    sy = vc @ up
    depth = -(vc @ to_eye)  # nearer the eye ⇒ larger (vc·to_eye) ⇒ smaller depth

    # Orthographic fit: scale the larger screen extent into the padded frame.
    span = max(sx.max() - sx.min(), sy.max() - sy.min()) or 1.0
    hi = res * _SUPERSAMPLE
    scale = (hi * (1.0 - 2.0 * _PAD)) / span
    px = (sx - 0.5 * (sx.max() + sx.min())) * scale + hi / 2.0
    # Flip Y: image row 0 is the top, but +up should point up on screen.
    py = hi / 2.0 - (sy - 0.5 * (sy.max() + sy.min())) * scale

    # Per-vertex Gouraud intensity. Headlight from the camera, matching the
    # viewer's key light parented to the camera (cam-space ~(0.5,1,0.5)).
    light = 0.5 * right + 1.0 * up + 0.5 * to_eye
    light = light / np.linalg.norm(light)
    nn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    lambert = np.clip(nn @ light, 0.0, 1.0)
    intensity = np.clip(_AMBIENT + _KEY * lambert, 0.0, 1.0)

    # Geometric face normals (from winding) for front-face culling — cull a
    # triangle whose front side points away from the eye, exactly as the
    # viewer's default FrontSide material does.
    p0, p1, p2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    face_n = np.cross(p1 - p0, p2 - p0)
    facing = face_n @ to_eye  # > 0 ⇒ front side toward eye
    keep = facing > 0
    f = f[keep]

    hi_i = hi
    rgb = np.zeros((hi_i, hi_i, 3), float)
    alpha = np.zeros((hi_i, hi_i), bool)
    zbuf = np.full((hi_i, hi_i), np.inf)

    for tri in f:
        i0, i1, i2 = tri
        x0, y0 = px[i0], py[i0]
        x1, y1 = px[i1], py[i1]
        x2, y2 = px[i2], py[i2]

        min_x = max(int(np.floor(min(x0, x1, x2))), 0)
        max_x = min(int(np.ceil(max(x0, x1, x2))), hi_i - 1)
        min_y = max(int(np.floor(min(y0, y1, y2))), 0)
        max_y = min(int(np.ceil(max(y0, y1, y2))), hi_i - 1)
        if min_x > max_x or min_y > max_y:
            continue

        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue

        ys, xs = np.mgrid[min_y : max_y + 1, min_x : max_x + 1]
        xs = xs + 0.5
        ys = ys + 0.5
        # Barycentric weights via edge functions.
        w0 = ((x1 - xs) * (y2 - ys) - (x2 - xs) * (y1 - ys)) / area
        w1 = ((x2 - xs) * (y0 - ys) - (x0 - xs) * (y2 - ys)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue

        tri_depth = w0 * depth[i0] + w1 * depth[i1] + w2 * depth[i2]
        tri_int = w0 * intensity[i0] + w1 * intensity[i1] + w2 * intensity[i2]

        rows = ys[inside].astype(int)
        cols = xs[inside].astype(int)
        d = tri_depth[inside]
        shade = tri_int[inside]

        nearer = d < zbuf[rows, cols]
        rows, cols, d, shade = rows[nearer], cols[nearer], d[nearer], shade[nearer]
        if rows.size == 0:
            continue
        zbuf[rows, cols] = d
        rgb[rows, cols] = shade[:, None] * color[None, :]
        alpha[rows, cols] = True

    # Box-downsample the supersampled buffers to the output resolution.
    rgba = np.zeros((hi_i, hi_i, 4), float)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha.astype(float)
    s = _SUPERSAMPLE
    down = rgba.reshape(res, s, res, s, 4).mean(axis=(1, 3))
    return np.clip(down, 0.0, 1.0)


def render_thumbnail_from_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    normals: np.ndarray,
    out_path: Path,
    *,
    color: np.ndarray | None = None,
    res: int = _RES,
) -> None:
    """Rasterise (vertices, faces, smooth normals) to a square iso-view PNG."""
    from PIL import Image

    col = _BASE_COLOR if color is None else np.asarray(color, float)[:3]
    rgba = _render_view(
        vertices, faces, normals,
        color=col, view_dir=_VIEW_DIR, world_up=_WORLD_UP, res=res,
    )
    out = (rgba * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(out, mode="RGBA").save(out_path)


# iso / front / top review views (replaces render_png's mplot3d 3-view). In
# the GLB's Y-up frame: iso down the diagonal, front along -Z, top looking
# straight down -Y (world-up falls back to +Z for that degenerate case).
_REVIEW_VIEWS = (
    ("iso", np.array([1.0, 1.0, 1.0]), _WORLD_UP),
    ("front", np.array([0.0, 0.0, 1.0]), _WORLD_UP),
    ("top", np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])),
)


def _mesh_color(mesh: trimesh.Trimesh) -> np.ndarray | None:
    """Adopt the GLB's own colour unless it's the neutral trimesh default."""
    try:
        main = np.asarray(mesh.visual.main_color, float) / 255.0
        if not np.allclose(main[:3], np.array([102, 102, 102]) / 255.0, atol=0.02):
            return main[:3]
    except Exception:
        pass
    return None


def render_thumbnail(glb_path: Path, png_path: Path) -> None:
    """Render the gallery thumbnail from a baked GLB.

    Loads the GLB the detail viewer serves and rasterises it with this
    module's software renderer, using the mesh's own smooth vertex normals
    so the card matches the live preview (single source of truth).
    """
    scene = trimesh.load(str(glb_path), force="scene")
    mesh = scene.to_geometry()  # concatenate scene geometries into one Trimesh
    render_thumbnail_from_mesh(
        mesh.vertices, mesh.faces, mesh.vertex_normals, png_path,
        color=_mesh_color(mesh),
    )


def render_review(glb_path: Path, png_path: Path, *, res: int = _RES) -> None:
    """Three-view (iso/front/top) review sheet from a baked GLB.

    The dev/CI review artifact written by export.py's default export-all
    mode. Same software rasteriser as the gallery thumbnail, just three
    stacked views — so no mplot3d/plot_trisurf anywhere in the pipeline.
    """
    from PIL import Image

    scene = trimesh.load(str(glb_path), force="scene")
    mesh = scene.to_geometry()
    col = _mesh_color(mesh)
    col = _BASE_COLOR if col is None else np.asarray(col, float)[:3]
    tiles = []
    for _label, view_dir, world_up in _REVIEW_VIEWS:
        rgba = _render_view(
            mesh.vertices, mesh.faces, mesh.vertex_normals,
            color=col, view_dir=view_dir, world_up=world_up, res=res,
        )
        tiles.append((rgba * 255.0 + 0.5).astype(np.uint8))
    strip = np.concatenate(tiles, axis=1)  # side by side: iso | front | top
    Image.fromarray(strip, mode="RGBA").save(png_path)
