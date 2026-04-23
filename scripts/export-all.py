#!/usr/bin/env python3
"""Export every models/*.scad to exports/<stem>.stl.

Thin sibling to scripts/render-all.py. One openscad subprocess per
model — a single bad file doesn't abort the batch. Exits non-zero if
any export failed.

Used by CI (and available locally) so scripts/check-invariants.py has
an STL per model to analyze. The scad-export skill still owns the
human-in-the-loop gate for exporting a single model from an interactive
session; this script is for batch runs where no approval step applies.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
EXPORT_PY = REPO_ROOT / ".claude" / "skills" / "scad-export" / "scripts" / "export.py"


def main(argv: list[str] | None = None) -> int:
    _parse_args(argv)

    if not EXPORT_PY.exists():
        print(f"error: export.py not found at {EXPORT_PY}", file=sys.stderr)
        return 2

    models = sorted(MODELS_DIR.glob("*.scad"))
    failures: list[str] = []
    for model in models:
        rc = _export_one(model)
        status = "ok" if rc == 0 else f"FAIL(rc={rc})"
        print(f"{status}  {model.name}")
        if rc != 0:
            failures.append(model.name)

    total = len(models)
    print(f"\nexported {total - len(failures)}/{total} models")
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export all models/*.scad")
    return p.parse_args(argv)


def _export_one(model: Path) -> int:
    cmd = [sys.executable, str(EXPORT_PY), "--model", str(model)]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
