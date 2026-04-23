#!/usr/bin/env python3
"""Run scripts/check-invariants.py for every models/*.scad.

One subprocess per stem so a failure in one model doesn't cut the
batch short. Exits non-zero if any model failed; prints a final
summary with counts.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
CHECK_PY = REPO_ROOT / "scripts" / "check-invariants.py"


def main() -> int:
    stems = sorted(p.stem for p in MODELS_DIR.glob("*.scad"))
    failures: list[str] = []
    for stem in stems:
        rc = subprocess.run([sys.executable, str(CHECK_PY), stem]).returncode
        if rc != 0:
            failures.append(stem)

    total = len(stems)
    print(f"\nchecked {total} models, {len(failures)} failed")
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
