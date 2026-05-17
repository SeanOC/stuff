#!/usr/bin/env python3
"""Export every models/*.scad to exports/<stem>.stl.

Thin sibling to scripts/render-all.py. One openscad subprocess per
model — a single bad file doesn't abort the batch. Exits non-zero if
any export failed.

Used by CI (and available locally) so scripts/check-invariants.py has
an STL per model to analyze. The scad-export skill still owns the
human-in-the-loop gate for exporting a single model from an interactive
session; this script is for batch runs where no approval step applies.

Filename opt-in (st-sq6): a model can flag a `@param enum` line with the
bare-word `filename` attribute to expand the export grid. For each
choice of the flagged param, this script writes
`exports/<stem>-<value>.stl` instead of a single
`exports/<stem>.stl`. Multi-param expansion uses the cartesian product
of choices joined as `<param1>=<value1>-<param2>=<value2>` so the
filename remains parseable. Models without the flag are unaffected.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from itertools import product
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
EXPORT_PY = REPO_ROOT / ".claude" / "skills" / "scad-export" / "scripts" / "export.py"

sys.path.insert(0, str(REPO_ROOT))
from scripts.invariants.params import filename_export_params, parse_params  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    _parse_args(argv)

    if not EXPORT_PY.exists():
        print(f"error: export.py not found at {EXPORT_PY}", file=sys.stderr)
        return 2

    models = sorted(MODELS_DIR.glob("*.scad"))
    failures: list[str] = []
    total_variants = 0
    for model in models:
        variants = plan_variants(model)
        total_variants += len(variants)
        for name, defines in variants:
            rc = _export_one(model, name, defines)
            label = f"{model.name}" if name == model.stem else f"{model.name} [{name}]"
            status = "ok" if rc == 0 else f"FAIL(rc={rc})"
            print(f"{status}  {label}")
            if rc != 0:
                failures.append(f"{model.name}:{name}")

    print(f"\nexported {total_variants - len(failures)}/{total_variants} variants "
          f"across {len(models)} models")
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


def plan_variants(model: Path) -> list[tuple[str, dict[str, str]]]:
    """Return [(name, defines), ...] for one model.

    Default case (no filename opt-in): a single entry whose name is the
    model stem and defines is empty — produces `exports/<stem>.stl`.

    Filename opt-in: one entry per cartesian product of choices across
    every `@param enum ... filename` line, named `<stem>-<value>` for
    a single flagged param or `<stem>-<k1>=<v1>-<k2>=<v2>...` for
    multiple. Each entry's defines map `-D` flags through to openscad.
    """
    stem = model.stem
    try:
        source = model.read_text(encoding="utf-8")
    except OSError:
        return [(stem, {})]
    params = parse_params(source)
    fn_params = filename_export_params(params)
    if not fn_params:
        return [(stem, {})]

    names = [name for name, _ in fn_params]
    choice_lists = [choices for _, choices in fn_params]
    variants: list[tuple[str, dict[str, str]]] = []
    for combo in product(*choice_lists):
        defines = {n: v for n, v in zip(names, combo)}
        if len(names) == 1:
            suffix = combo[0]
        else:
            suffix = "-".join(f"{n}={v}" for n, v in zip(names, combo))
        variants.append((f"{stem}-{suffix}", defines))
    return variants


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export all models/*.scad")
    return p.parse_args(argv)


def _export_one(model: Path, name: str, defines: dict[str, str]) -> int:
    cmd = [sys.executable, str(EXPORT_PY), "--model", str(model), "--name", name]
    for k, v in defines.items():
        cmd += ["-D", f'{k}="{v}"']
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
