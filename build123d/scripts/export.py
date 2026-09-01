"""Export registered models: STL (print), GLB (viewer), PNG (review).

Default mode (export-all behavior, unchanged):
    uv run python scripts/export.py
Builds EVERY registered model (smoke included) at its defaults and writes
out/<name>.{stl,glb,png}.

Presets-only mode (build-time baking, bead pst-pa1o):
    uv run python scripts/export.py --presets-only TARGET_DIR
For every APP-LISTED (non-smoke) registered model, builds each of its
presets and writes exactly three artifacts per preset into TARGET_DIR:

    TARGET_DIR/<model-slug>/<preset-id>.stl   # print download
    TARGET_DIR/<model-slug>/<preset-id>.glb   # viewer geometry
    TARGET_DIR/<model-slug>/<preset-id>.png   # gallery thumbnail

Single source of truth (bead pst-1vi5): the thumbnail is rendered from
the same built part as the GLB/STL, so a model or preset change can
never leave the gallery card showing stale geometry. The gallery's
/api/thumbnail route serves this baked PNG for build123d models (the
first preset), exactly as /api/bd-asset serves the baked GLB/STL.

Contract (validated by tests/test_presets_bake.py):
  - every registered app-listed model appears (no silent skips),
  - every preset of every such model appears,
  - names are deterministic and filesystem-safe (slug + preset id, both
    URL-safe by registry validation),
  - exactly STL + GLB + PNG per preset (thumbnail is a bake output, not
    a separate committed review artifact).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build123d import export_stl, export_gltf  # noqa: E402

from holders.registry import all_models  # noqa: E402

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


def render_thumbnail(stl_path: Path, png_path: Path) -> None:
    """Single iso-view PNG for the gallery card (bead pst-1vi5).

    Square figure so the gallery's 4:3 object-cover crop stays centred
    on the part. Software rasteriser (Agg) — no GL — so it renders in
    the headless Vercel build image the same as in CI.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh

    mesh = trimesh.load_mesh(stl_path)
    fig = plt.figure(figsize=(4, 4))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_trisurf(
        mesh.vertices[:, 0], mesh.vertices[:, 1], mesh.vertices[:, 2],
        triangles=mesh.faces, color="#8fb4d9", edgecolor="none", shade=True,
    )
    # Equal aspect around the centroid so the part isn't distorted.
    ext = mesh.bounding_box.extents
    c = mesh.bounding_box.centroid
    r = float(max(ext)) / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=30, azim=-60)
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    fig.savefig(png_path, dpi=100)
    plt.close(fig)


def export_all() -> int:
    """Existing behavior: every registered model (smoke included) at defaults."""
    OUT.mkdir(exist_ok=True)
    specs = all_models()
    if not specs:
        print("no models registered"); return 1
    for spec in specs:
        part = spec.build(spec.resolve_values())
        stl = OUT / f"{spec.name}.stl"
        glb = OUT / f"{spec.name}.glb"
        png = OUT / f"{spec.name}.png"
        export_stl(part, str(stl))
        export_gltf(part, str(glb), binary=True)
        render_png(stl, png)
        print(f"{spec.name}: vol={part.volume:.0f}mm3 -> {stl.name}, {glb.name}, {png.name}")
    return 0


def export_presets_only(target: Path) -> int:
    """Bake every preset of every app-listed model into target/<slug>/<preset-id>.{stl,glb,png}."""
    target.mkdir(parents=True, exist_ok=True)
    specs = [s for s in all_models() if not s.is_smoke]
    if not specs:
        print("no app-listed models registered"); return 1
    baked = 0
    for spec in specs:
        if not spec.presets:
            # Registry validation forbids app-listed models without presets,
            # but fail loudly here too: a silent skip would leak into CI.
            print(f"SKIP {spec.name}: no presets registered", file=sys.stderr)
            return 1
        for preset in spec.presets:
            part = spec.build(spec.resolve_values(preset.values))
            if part.volume <= 0:
                print(f"SKIP {spec.name}/{preset.id}: zero volume", file=sys.stderr)
                return 1
            model_dir = target / spec.slug
            model_dir.mkdir(exist_ok=True)
            stl = model_dir / f"{preset.id}.stl"
            glb = model_dir / f"{preset.id}.glb"
            png = model_dir / f"{preset.id}.png"
            export_stl(part, str(stl))
            export_gltf(part, str(glb), binary=True)
            # Thumbnail from the same STL → same source as the GLB the
            # detail viewer loads (pst-1vi5 single-source-of-truth).
            render_thumbnail(stl, png)
            baked += 1
            print(f"{spec.name}/{preset.id}: vol={part.volume:.0f}mm3 -> {stl}, {glb}, {png}")
    print(f"baked {baked} presets from {len(specs)} models into {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--presets-only",
        metavar="TARGET_DIR",
        help="bake every preset of every app-listed model into TARGET_DIR and exit",
    )
    args = parser.parse_args()
    if args.presets_only:
        return export_presets_only(Path(args.presets_only))
    return export_all()


if __name__ == "__main__":
    raise SystemExit(main())
