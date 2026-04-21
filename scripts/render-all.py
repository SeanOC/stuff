#!/usr/bin/env python3
"""Render every models/*.scad into renders/<stem>/ and prune stale dirs.

Thin driver around .claude/skills/scad-render/scripts/render.py: one
subprocess per model so a single broken file doesn't abort the batch.
Prints a one-line summary per model; exits non-zero if any model failed.

Stale-pruning: any renders/<stem>/ directory whose corresponding
models/<stem>.scad is gone gets rm -rf'd so the committed PNG set
mirrors the current model set exactly.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
RENDERS_DIR = REPO_ROOT / "renders"
RENDER_PY = REPO_ROOT / ".claude" / "skills" / "scad-render" / "scripts" / "render.py"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not RENDER_PY.exists():
        print(f"error: render.py not found at {RENDER_PY}", file=sys.stderr)
        return 2

    models = sorted(MODELS_DIR.glob("*.scad"))
    stems = {m.stem for m in models}

    pruned = _prune_stale(stems)
    for stem in pruned:
        print(f"pruned stale renders/{stem}/")

    failures: list[str] = []
    for model in models:
        rc = _render_one(model, angles=args.angles)
        status = "ok" if rc == 0 else f"FAIL(rc={rc})"
        print(f"{status}  {model.name}")
        if rc != 0:
            failures.append(model.name)

    total = len(models)
    print(
        f"\nrendered {total - len(failures)}/{total} models, "
        f"pruned {len(pruned)} stale dir(s)"
    )
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render all models/*.scad")
    p.add_argument(
        "--angles",
        default="top,front,side,iso",
        help="comma-separated views (default: %(default)s)",
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
