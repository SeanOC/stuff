"""Export every registered model to out/: STL (print), GLB (viewer), PNG (review).

PNG is a software render (matplotlib over the tessellation) — no GPU/GL needed,
so it runs on bare CI runners. Three fixed views: iso, front, top.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from build123d import export_stl, export_gltf

from holders.registry import all_models

OUT = Path(__file__).resolve().parent.parent / "out"


def render_png(stl_path: Path, png_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh

    mesh = trimesh.load_mesh(stl_path)
    fig = plt.figure(figsize=(12, 4))
    views = [("iso", (30, -60)), ("front", (0, -90)), ("top", (90, -90))]
    for i, (label, (elev, azim)) in enumerate(views, 1):
        ax = fig.add_subplot(1, 3, i, projection="3d")
        ax.plot_trisurf(
            mesh.vertices[:, 0], mesh.vertices[:, 1], mesh.vertices[:, 2],
            triangles=mesh.faces, color="#8fb4d9", edgecolor="none", shade=True,
        )
        # equal aspect
        ext = mesh.bounding_box.extents
        c = mesh.bounding_box.centroid
        r = float(max(ext)) / 2
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off(); ax.set_title(label)
    fig.tight_layout()
    fig.savefig(png_path, dpi=110)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    specs = all_models()
    if not specs:
        print("no models registered"); return 1
    for spec in specs:
        part = spec.build()
        stl = OUT / f"{spec.name}.stl"
        glb = OUT / f"{spec.name}.glb"
        png = OUT / f"{spec.name}.png"
        export_stl(part, str(stl))
        export_gltf(part, str(glb), binary=True)
        render_png(stl, png)
        print(f"{spec.name}: vol={part.volume:.0f}mm3 -> {stl.name}, {glb.name}, {png.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
