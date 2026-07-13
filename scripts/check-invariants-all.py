#!/usr/bin/env python3
"""Run scripts/check-invariants.py for every models/*.scad.

One subprocess per stem so a failure in one model doesn't cut the
batch short. Exits non-zero if any model failed; prints a final
summary with counts.

Stems whose export .stl doesn't exist (check-invariants.py exit code
3) are skipped, not failed: in CI's scoped-render mode (st-mrt),
export-all only regenerates the models a PR touched, and
exports/*.stl is gitignored — so a fresh workspace only contains this
run's exports. The batch analyzes what exports/ contains, per
docs/ci.md. Full coverage still happens on every push to main, where
export-all runs unscoped.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
CHECK_PY = REPO_ROOT / "scripts" / "check-invariants.py"

EXIT_NO_EXPORT = 3


def main() -> int:
    stems = sorted(p.stem for p in MODELS_DIR.glob("*.scad"))
    failures: list[str] = []
    skipped: list[str] = []
    for stem in stems:
        rc = subprocess.run([sys.executable, str(CHECK_PY), stem]).returncode
        if rc == EXIT_NO_EXPORT:
            skipped.append(stem)
        elif rc != 0:
            failures.append(stem)

    total = len(stems)
    print(
        f"\nchecked {total - len(skipped)}/{total} models, "
        f"{len(failures)} failed, {len(skipped)} skipped (no export)"
    )
    if skipped:
        print("skipped (not exported this run): " + ", ".join(skipped))
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
