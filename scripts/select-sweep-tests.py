#!/usr/bin/env python3
"""Select which param-sweep test files a CI run must execute (pst-776).

Reads a changed-file list (`--changed-paths`, whitespace-separated
`git diff --name-only`-style paths — same convention as
render-all.py / export-all.py) and decides between three modes:

  full      — a sweep-global input changed (wasm driver, param parser,
              vendored libs, sweep infra, lockfile, this script, the
              workflow itself), or no change list is available (push
              to main, workflow_dispatch, paths-filter failure):
              sweep every model.
  selective — only specific models and/or their per-model sweep files
              changed: sweep just those models, plus the cheap
              coverage meta-guard.
  skip      — nothing sweep-relevant changed (docs-only, app-only,
              invariants-sidecar-only diffs): run no sweep at all.

The selected files are then split into cost-balanced shards for the
workflow's job matrix (greedy longest-processing-time binning; a
model's cost is estimated from its `@param` count, which is what
drives its sweep-case count). Shards land in $GITHUB_OUTPUT as:

  mode         full | selective | skip
  shard_total  number of matrix jobs
  shard_matrix JSON list of {id, files} objects for fromJson()

Every emitted file path is regex-sanitized AND verified to exist in
the working tree, so the workflow can safely interpolate the shard
file lists into a `run:` line even on fork PRs with hostile
filenames — an unsanitizable path degrades to a full sweep, never
into the file list.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MAX_SHARDS = 4

# Any change here forces a full sweep: these inputs affect every
# model's render outcome or the sweep harness itself. Keep in sync
# with the `on.paths` lists in .github/workflows/param-sweep.yml.
FULL_TRIGGER_PREFIXES = (
    "lib/wasm/",
    "lib/scad-params/",
    "libs/",
)
FULL_TRIGGER_FILES = frozenset(
    {
        "vitest.sweep.config.ts",
        "scripts/vendor-libs.sh",
        "scripts/select-sweep-tests.py",
        "package-lock.json",
        ".github/workflows/param-sweep.yml",
        # Sweep infrastructure shared by every per-model file.
        "tests/sweep/runner.ts",
        "tests/sweep/expectations.ts",
        "tests/sweep/known-failures.ts",
        "tests/sweep/coverage.test.ts",
    }
)

COVERAGE_TEST = "tests/sweep/coverage.test.ts"

# Measured per-file sweep durations in seconds (CI run 29300566841,
# 2026-07-14, ubuntu-latest). Case count is a poor time proxy — 25
# opengrid_bin cases take 999s while 61 rv_ceiling cases take 61s —
# so shard balance uses these where available. Advisory only: a stale
# or missing entry skews balance, never correctness (new models fall
# back to the @param estimate below). Refresh from a full-sweep run's
# per-file times when balance drifts.
MEASURED_SECONDS = {
    "opengrid_bin": 999,
    "led_remote_holder_55x124mm": 908,
    "led_remote_holder_51x84mm": 645,
    "spraycan_carrier_6x50mm": 587,
    "cylindrical_holder_slot": 447,
    "blu_flow_meter_mount_80mm": 376,
    "blu_black_tank_valve_mount": 349,
    "opengrid_panel_aligner": 322,
    "ego_lb6500_blower_mount": 251,
    "ego_powerhead_mount": 168,
    "lcd_stylus_hex_8mm": 92,
    "goblu_filter_holder_3x90mm": 73,
    "blutech_water_softener_foot": 61,
    "rv_ceiling_ap_adapter_235mm": 61,
    "aquor_bib_drip_deflector": 31,
    "gridfinity_bin": 30,
    "lcd_stylus_75mm": 12,
    "popcorn_kernel": 7,
    "disney_ear_hanger": 1,
}

# Full-sweep seconds per sweep case, for models not in the table
# (5420s / 587 cases in the run above).
FALLBACK_SECONDS_PER_CASE = 9

# Stems become shell-interpolated file paths in the workflow; reject
# anything outside this alphabet (fall back to a full sweep instead).
SAFE_STEM = re.compile(r"[A-Za-z0-9._-]+\Z")


@dataclass
class Selection:
    mode: str  # "full" | "selective" | "skip"
    files: list[str]  # test files to run; empty when mode == "skip"


def classify(paths: list[str]) -> Selection:
    """Map a changed-path list to a sweep mode + per-model stems.

    Conservative by construction: unknown-but-relevant changes widen
    to a full sweep rather than narrowing to a guess. In particular a
    non-.scad file under models/ (e.g. an STL consumed via import())
    forces a full sweep because the asset→model mapping isn't known
    here.
    """
    if not paths:
        return Selection("full", [])

    stems: set[str] = set()
    for p in paths:
        if p in FULL_TRIGGER_FILES or p.startswith(FULL_TRIGGER_PREFIXES):
            return Selection("full", [])
        if p.startswith("models/"):
            rel = p[len("models/") :]
            if "/" not in rel and rel.endswith(".scad"):
                stems.add(rel[: -len(".scad")])
            elif rel.endswith(".invariants.py"):
                continue  # sidecars are a CI-render input, not a sweep input
            else:
                return Selection("full", [])  # asset / unknown model file
        elif p.startswith("tests/sweep/"):
            rel = p[len("tests/sweep/") :]
            if "/" not in rel and rel.endswith(".test.ts"):
                stems.add(rel[: -len(".test.ts")])
            else:
                return Selection("full", [])  # unrecognized sweep-dir file
        # anything else (docs/, app/, scripts/, …) is sweep-irrelevant

    if not stems:
        return Selection("skip", [])
    if any(not SAFE_STEM.match(s) for s in stems):
        return Selection("full", [])

    # Deleted models / not-yet-created sweep files drop out here; the
    # coverage meta-guard (always included) fails the run if a model
    # exists without its sweep file.
    files = [
        f"tests/sweep/{s}.test.ts"
        for s in sorted(stems)
        if (REPO_ROOT / "tests/sweep" / f"{s}.test.ts").is_file()
    ]
    return Selection("selective", [COVERAGE_TEST, *files])


def all_sweep_files() -> list[str]:
    return sorted(
        f"tests/sweep/{p.name}"
        for p in (REPO_ROOT / "tests/sweep").glob("*.test.ts")
    )


def estimated_cost(test_file: str) -> int:
    """Estimated sweep seconds for one per-model test file.

    Prefers the measured table; falls back to an estimate from the
    model's @param count (case count scales with it — numerics
    contribute up to 3 variants each). The coverage meta-guard
    renders nothing and costs ~0.
    """
    if test_file == COVERAGE_TEST:
        return 0
    stem = Path(test_file).name[: -len(".test.ts")]
    measured = MEASURED_SECONDS.get(stem)
    if measured is not None:
        return measured
    scad = REPO_ROOT / "models" / f"{stem}.scad"
    try:
        cases = 1 + 2 * scad.read_text().count("@param")
    except OSError:
        cases = 1
    return cases * FALLBACK_SECONDS_PER_CASE


def build_shards(files: list[str], max_shards: int = MAX_SHARDS) -> list[list[str]]:
    """Greedy LPT binning of test files into ≤ max_shards groups."""
    weighted = sorted(files, key=estimated_cost, reverse=True)
    renderers = sum(1 for f in files if estimated_cost(f) > 0)
    n = max(1, min(max_shards, renderers))
    costs = [0] * n
    members: list[list[str]] = [[] for _ in range(n)]
    for f in weighted:
        idx = costs.index(min(costs))
        costs[idx] += estimated_cost(f)
        members[idx].append(f)
    return [m for m in members if m]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--changed-paths",
        default="",
        help=(
            "whitespace-separated changed paths; empty ⇒ full sweep "
            "(push events and filter failures pass nothing)"
        ),
    )
    args = ap.parse_args(argv)

    sel = classify([p for p in args.changed_paths.split() if p])
    files = sel.files if sel.mode == "selective" else (
        all_sweep_files() if sel.mode == "full" else []
    )
    shards = build_shards(files) if files else []
    matrix = [
        {"id": i + 1, "files": " ".join(members)}
        for i, members in enumerate(shards)
    ]

    summary = f"sweep scope: **{sel.mode}** — {len(files)} test file(s), {len(matrix)} shard(s)"
    print(summary)
    for entry in matrix:
        print(f"  shard {entry['id']}: {entry['files']}")

    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as out:
            out.write(f"mode={sel.mode}\n")
            out.write(f"shard_total={len(matrix)}\n")
            out.write(f"shard_matrix={json.dumps(matrix)}\n")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as out:
            out.write(summary + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
