#!/usr/bin/env python3
"""Render every models/*.scad into renders/<stem>/ and prune stale dirs.

Thin driver around .claude/skills/scad-render/scripts/render.py: one
subprocess per model so a single broken file doesn't abort the batch.
Prints a one-line summary per model; exits non-zero if any model failed.

Stale-pruning: any renders/<stem>/ directory whose corresponding
models/<stem>.scad is gone gets rm -rf'd so the committed PNG set
mirrors the current model set exactly.

build123d mirror (pst-dsiq): the gallery serves BD thumbnails through
the same renders/<stem>/iso.png path as SCAD models. After the SCAD
pass, each build123d/manifest.json model gets its committed review
render (build123d/docs/renders/<name>.png — 3-view, tracked) copied to
renders/<slug-as-stem>/iso.png, and BD stems not in the manifest are
pruned like SCAD ones. Missing review PNGs are a warning, not a
failure — the gallery degrades to a blank tile, and the render job's
commit-back keeps the mirror canonical after the next push to main.

Selective re-render (st-mrt): pass `--changed-paths "<paths>"` to
restrict the render set to models actually touched by the current
push/PR. The string is whitespace-separated:
  - libs/* in the list  → render ALL models (a vendored lib change
                          can affect every downstream model).
  - models/*.scad only  → render just those models.
  - neither             → skip rendering (prune still runs).
  - flag absent / empty → render all (backward-compat default for
                          local invocations that don't compute a diff).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
RENDERS_DIR = REPO_ROOT / "renders"
RENDER_PY = REPO_ROOT / ".claude" / "skills" / "scad-render" / "scripts" / "render.py"
BD_MANIFEST = REPO_ROOT / "build123d" / "manifest.json"
BD_DOCS_RENDERS = REPO_ROOT / "build123d" / "docs" / "renders"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not RENDER_PY.exists():
        print(f"error: render.py not found at {RENDER_PY}", file=sys.stderr)
        return 2

    models = sorted(MODELS_DIR.glob("*.scad"))
    stems = {m.stem for m in models}

    bd_stems = bd_manifest_stems()
    pruned = _prune_stale(stems | bd_stems)
    for stem in pruned:
        print(f"pruned stale renders/{stem}/")

    selected = select_models(models, args.changed_paths)
    if selected is None:
        print("no models/*.scad or libs/ changes — skipping SCAD renders")
    else:
        if len(selected) < len(models):
            print(
                f"selective re-render: {len(selected)}/{len(models)} models "
                f"({', '.join(m.stem for m in selected)})"
            )

        failures: list[str] = []
        for model in selected:
            rc = _render_one(model, angles=args.angles)
            status = "ok" if rc == 0 else f"FAIL(rc={rc})"
            print(f"{status}  {model.name}")
            if rc != 0:
                failures.append(model.name)

        total = len(selected)
        print(
            f"\nrendered {total - len(failures)}/{total} models, "
            f"pruned {len(pruned)} stale dir(s)"
        )
        if failures:
            print("failed: " + ", ".join(failures), file=sys.stderr)
            return 1

    missing = _mirror_bd_thumbnails(bd_stems)
    print(
        f"build123d mirror: {len(bd_stems) - len(missing)}/{len(bd_stems)} "
        f"thumbnail(s) up to date"
        + (f", missing review PNG: {', '.join(missing)}" if missing else "")
    )
    return 0


def bd_manifest_stems() -> set[str]:
    """Stems (slug with dashes -> underscores) of manifest-listed BD models.

    A missing or unreadable manifest degrades to an empty set with a
    warning: the SCAD pipeline is never blocked by build123d state.
    """
    if not BD_MANIFEST.exists():
        print("warning: build123d/manifest.json not found — skipping BD mirror")
        return set()
    try:
        doc = json.loads(BD_MANIFEST.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"warning: unreadable build123d/manifest.json ({e}) — skipping BD mirror",
            file=sys.stderr,
        )
        return set()
    stems: set[str] = set()
    for model in doc.get("models", []):
        slug = model.get("slug")
        if isinstance(slug, str) and slug:
            stems.add(slug.replace("-", "_"))
    return stems


def _mirror_bd_thumbnails(bd_stems: set[str]) -> list[str]:
    """Copy each BD model's review PNG to renders/<stem>/iso.png.

    Mirrors the SCAD render convention (renders/<stem>/iso.png is what
    /api/thumbnail serves) so the gallery needs no BD-specific route.
    Returns the stems whose review PNG was missing.
    """
    missing: list[str] = []
    for stem in sorted(bd_stems):
        if (MODELS_DIR / f"{stem}.scad").exists():
            # A SCAD model and a BD model must never share a stem; if
            # one does, the SCAD set owns the dir and the mirror yields.
            print(f"warning: {stem} is both .scad and BD — mirror skipped")
            continue
        src = BD_DOCS_RENDERS / f"{stem}.png"
        if not src.exists():
            missing.append(stem)
            print(f"warning: no review PNG for BD model {stem} ({src})")
            continue
        dest_dir = RENDERS_DIR / stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest_dir / "iso.png")
        print(f"mirror  {src.relative_to(REPO_ROOT)} -> renders/{stem}/iso.png")
    return missing


def select_models(
    all_models: list[Path], changed_paths: str | None
) -> list[Path] | None:
    """Decide which subset of `all_models` to re-process from a diff list.

    Shared between scripts/render-all.py and scripts/export-all.py so
    both batches make the same selection from the same input.

    Returns:
      None          — change list had neither libs/ nor models/ entries;
                      caller should skip its main pass.
      [Path, ...]   — models to process (the full input when no filter
                      is active or when a libs/* change forces a full
                      re-process).
    """
    if not changed_paths or not changed_paths.strip():
        return all_models  # backward-compat: no filter → process all.
    paths = [p for p in changed_paths.split() if p]
    if any(p.startswith("libs/") for p in paths):
        return all_models  # any libs/ change forces a full re-process.
    model_paths = [
        p for p in paths
        if p.startswith("models/") and p.endswith(".scad")
    ]
    if not model_paths:
        return None
    wanted_stems = {Path(p).stem for p in model_paths}
    return [m for m in all_models if m.stem in wanted_stems]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render all models/*.scad")
    p.add_argument(
        "--angles",
        default="top,front,side,iso",
        help="comma-separated views (default: %(default)s)",
    )
    p.add_argument(
        "--changed-paths",
        default="",
        help=(
            "whitespace-separated paths from `git diff --name-only`; "
            "restricts the render set to the models actually touched. "
            "Empty/absent → render all. See module docstring."
        ),
    )
    return p.parse_args(argv)


def _render_one(model: Path, *, angles: str) -> int:
    # Pipe stdout to /dev/null: render.py emits a JSON blob per model
    # that's only useful for the scad-render skill. Warnings and errors
    # still surface via stderr.
    cmd = [
        sys.executable,
        str(RENDER_PY),
        "--model",
        str(model),
        "--angles",
        angles,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL)
    return proc.returncode


def _prune_stale(live_stems: set[str]) -> list[str]:
    if not RENDERS_DIR.exists():
        return []
    pruned: list[str] = []
    for child in sorted(RENDERS_DIR.iterdir()):
        if not child.is_dir():
            continue
        if child.name not in live_stems:
            shutil.rmtree(child)
            pruned.append(child.name)
    return pruned


if __name__ == "__main__":
    raise SystemExit(main())
