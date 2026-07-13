#!/usr/bin/env python3
"""Run scripts/check-invariants.py for every models/*.scad.

One subprocess per stem so a failure in one model doesn't cut the
batch short. Exits non-zero if any model failed; prints a final
summary with counts.

Selective checking (st-qdz): pass `--changed-paths "<paths>"` to
restrict the check set to models actually touched by the current
push/PR. Mirrors render-all.py/export-all.py via the shared
`render_all.select_models` helper (see render-all.py docstring for
the path-rules table) so the invariants pass covers exactly the set
export-all.py just exported — exports/*.stl is gitignored, so on a
fresh CI runner the untouched models have no STL to analyze. The
flag defaults to $CHANGED_PATHS because CI sets that variable on the
step that runs export-all and this script back to back.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
CHECK_PY = REPO_ROOT / "scripts" / "check-invariants.py"

# Share the selective-re-process logic with the renderer/exporter so
# all three batches make the same selection from the same input.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import importlib  # noqa: E402
_render_all = importlib.import_module("render-all")  # filename has a dash
select_models = _render_all.select_models


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    models = sorted(MODELS_DIR.glob("*.scad"))
    selected = select_models(models, args.changed_paths)
    if selected is None:
        print("no models/*.scad or libs/ changes — skipping invariants")
        return 0
    if len(selected) < len(models):
        print(
            f"selective check: {len(selected)}/{len(models)} models "
            f"({', '.join(m.stem for m in selected)})"
        )

    failures: list[str] = []
    for model in selected:
        rc = subprocess.run([sys.executable, str(CHECK_PY), model.stem]).returncode
        if rc != 0:
            failures.append(model.stem)

    total = len(selected)
    print(f"\nchecked {total} models, {len(failures)} failed")
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check invariants for all models/*.scad")
    p.add_argument(
        "--changed-paths",
        default=os.environ.get("CHANGED_PATHS", ""),
        help=(
            "whitespace-separated paths from `git diff --name-only`; "
            "restricts the check set to the models actually touched. "
            "Defaults to $CHANGED_PATHS (set by CI), else empty → check "
            "all. See render-all.py docstring."
        ),
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
