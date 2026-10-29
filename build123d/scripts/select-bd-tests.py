#!/usr/bin/env python3
"""Select which bd123 pytest items a PR runs in the fast and audit jobs (pst-3bga4).

Reads a changed-file list (`--changed-paths`, whitespace-separated
repo-relative paths — dorny/paths-filter `list-files: shell`, the same
convention as the repo-root scripts/select-sweep-tests.py) and decides:

  full    — a shared input changed (SHARED_FILES / SHARED_PREFIXES, this
            script, the workflow), a path the registry cannot attribute to
            a model changed, or no change list is available (push to main,
            schedule, filter failure), or no model module is affected
            (manifest.json, baselines or a non-model test file alone):
            run every test. There is nothing to scope to then, and the
            budget tier, whose ids name only models, would collect nothing.
  scoped  — only registered model modules (holders/<stem>.py), test files
            (tests/test_*.py), manifest.json, baselines, docs, test data and
            NEUTRAL paths changed: run the K_EXPR selection below. A section
            golden docs/renders/sections/<slug>.svg counts as its model's
            change; any other docs/ file or non-.py file under tests/ counts
            as a change to the model modules and test files that name it,
            and is full when other code (or, under tests/, nothing) does.
            tests/test_<stem>.py of a model module counts as that module's
            change.
  skip    — only NEUTRAL paths changed (ci/, shard durations, render PNGs,
            docs no code names): run nothing.

K_EXPR is `(<mine>) or not (<others>)`. <mine> is, for each affected model
module, every registry name and slug it registers (module -> models is 1:N,
read from spec.build.__module__ as holders/registry.py does) plus its test stem
test_<stem>, and the stem of every changed test file. A module is affected
when it changed or imports an affected model module (bench_width_saddle
imports bench_lip_clip). <others> is the same terms for every unaffected
module. So the selection drops only tests attributable to an UNCHANGED
model; registry-wide tests whose ids name no model (the geometry baseline,
presets bake, manifest and registry contracts) and library tests always
run. A plain `-k "(<mine>)"` would drop those, and the geometry baseline is
the test every geometry PR must update. The `(<mine>) or` guard keeps the
changed models' tests when an unchanged model's name is a substring of
theirs (underware_t is inside underware_transition).

Writes mode and k_expr to $GITHUB_OUTPUT. Every term is a registry name,
slug or file stem checked against TERM_RE, so the expression is safe to pass to
`pytest -k` through an env var; anything else degrades to full.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # build123d/
PREFIX = "build123d/"

# Any change here runs everything: these inputs feed every model's build,
# audit or test harness. holders/ helpers that register no model (signs.py,
# sign_ghost.py) are unattributable and land in full the same way.
SHARED_FILES = frozenset(
    {
        "holders/printer.py",
        "holders/registry.py",
        "scripts/manifest.py",
        "scripts/select-bd-tests.py",
        "tests/print_audit.py",
        "tests/audit_cache.py",
        "tests/mount_contracts.py",
        "tests/conftest.py",
        "pyproject.toml",
        "uv.lock",
    }
)
SHARED_PREFIXES = ("labels/", "multibuild/", "openconnect/")
WORKFLOW = ".github/workflows/bd123.yml"

# Paths no fast/audit test reads.
NEUTRAL_PREFIXES = ("ci/",)
NEUTRAL_FILES = frozenset({"tests/.test_durations"})
# tests/baselines/** is read through scripts/baseline_common.py by these two;
# both name no model, so every scoped run keeps them anyway.
BASELINE_READERS = ("test_baseline_tools", "test_geometry_baseline")
# This script and its test name data files in tables, not as reads.
SELF = frozenset({"scripts/select-bd-tests.py", "tests/test_select_bd_tests.py"})

MODEL_RE = re.compile(r"^holders/([a-z0-9_]+)\.py$")
SECTION_RE = re.compile(r"^docs/renders/sections/([a-z0-9-]+)\.svg$")
TEST_RE = re.compile(r"^tests/(test_[a-z0-9_]+)\.py$")
TERM_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class Selection:
    mode: str  # full | scoped | skip
    k_expr: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Registry:
    modules: dict[str, list[str]]  # model module stem -> registry names + slugs (1:N)
    slugs: dict[str, str]  # spec slug -> model module stem


def load_registry() -> Registry:
    sys.path.insert(0, str(ROOT))
    from holders.registry import all_models

    names: dict[str, list[str]] = defaultdict(list)
    slugs: dict[str, str] = {}
    for spec in all_models():
        module = spec.build.__module__
        if module.startswith("holders.") and module.count(".") == 1:
            stem = module.split(".", 1)[1]
            # Slugs too: test_review_sheet ids its section goldens by slug.
            names[stem] += [spec.name, spec.slug]
            slugs[spec.slug] = stem
    return Registry({stem: sorted(set(v)) for stem, v in names.items()}, slugs)


def data_readers(rel: str, modules: dict[str, list[str]]) -> list[str] | None:
    """Python files under build123d/ that name a data file, as test stems or
    model module stems; None when any other code names it."""
    name = Path(rel).name
    readers = []
    for py in ROOT.rglob("*.py"):
        parts = py.relative_to(ROOT).parts
        if parts[0] in (".venv", "out") or "/".join(parts) in SELF:
            continue
        if name not in py.read_text(encoding="utf-8", errors="ignore"):
            continue
        if TEST_RE.match("/".join(parts)):
            readers.append(py.stem)
        elif (m := MODEL_RE.match("/".join(parts))) and m.group(1) in modules:
            readers.append(m.group(1))
        else:
            return None
    return sorted(readers)


def holders_imports(path: Path) -> set[str]:
    """holders.<x> module stems a source file imports (from/import forms)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "holders":
                found.update(a.name for a in node.names)
            elif node.module.startswith("holders."):
                found.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("holders."):
                    found.add(a.name.split(".")[1])
    return found


def attributed_test_files(stem: str) -> list[Path]:
    """Test files `-k test_<stem>` attributes to a module (prefix match)."""
    return sorted((ROOT / "tests").glob(f"test_{stem}*.py"))


def affected_modules(changed: set[str], modules: dict[str, list[str]]) -> set[str]:
    """Changed modules plus every model module (or its tests) importing one."""
    deps = {}
    for stem in modules:
        sources = [ROOT / "holders" / f"{stem}.py", *attributed_test_files(stem)]
        deps[stem] = set().union(*(holders_imports(p) for p in sources))
        deps[stem] &= set(modules)
    affected = set(changed)
    grew = True
    while grew:
        grew = False
        for stem, imported in deps.items():
            if stem not in affected and imported & affected:
                affected.add(stem)
                grew = True
    return affected


def module_terms(stem: str, modules: dict[str, list[str]], *, require_tests: bool) -> list[str]:
    terms = list(modules[stem])
    if not require_tests or attributed_test_files(stem):
        terms.append(f"test_{stem}")
    return terms


def classify(paths: list[str], registry: Registry | None = None) -> Selection:
    if not paths:
        return Selection("full", reason="no change list (push, schedule or filter failure)")
    if registry is None:
        registry = load_registry()
    modules = registry.modules

    changed: set[str] = set()
    mine: set[str] = set()
    for path in paths:
        if path == WORKFLOW:
            return Selection("full", reason=f"{path} changed")
        if not path.startswith(PREFIX):
            continue
        rel = path[len(PREFIX):]
        if rel in SHARED_FILES or rel.startswith(SHARED_PREFIXES):
            return Selection("full", reason=f"shared input {path}")
        if rel in NEUTRAL_FILES or rel.startswith(NEUTRAL_PREFIXES):
            continue
        if rel == "manifest.json":
            mine.add("test_manifest")
        elif (m := MODEL_RE.match(rel)) and m.group(1) in modules:
            changed.add(m.group(1))
        elif m := TEST_RE.match(rel):
            mine.add(m.group(1))
            if (stem := m.group(1).removeprefix("test_")) in modules:
                changed.add(stem)
        elif m := SECTION_RE.match(rel):
            if m.group(1) not in registry.slugs:
                return Selection("full", reason=f"{path} names no registered slug")
            changed.add(registry.slugs[m.group(1)])
        elif rel.startswith("docs/renders/"):
            continue
        elif rel.startswith("tests/baselines/"):
            mine.update(BASELINE_READERS)
        elif rel.startswith("docs/") or (rel.startswith("tests/") and not rel.endswith(".py")):
            readers = data_readers(rel, modules)
            if readers is None or (not readers and rel.startswith("tests/")):
                return Selection("full", reason=f"{path} is named outside tests/ and model modules")
            changed.update(r for r in readers if r in modules)
            mine.update(r for r in readers if r not in modules)
        else:
            return Selection("full", reason=f"{path} is not attributable to a model")

    if not changed and not mine:
        return Selection("skip", reason="no build123d test input changed")

    affected = affected_modules(changed, modules)
    if not affected:
        # Nothing to scope to: `<mine>` would name no model, and the budget
        # tier (keyed only by model name) would collect nothing and exit 5.
        return Selection("full", reason="no model module changed")
    for stem in affected:
        mine.update(module_terms(stem, modules, require_tests=False))
    others: set[str] = set()
    for stem in modules.keys() - affected:
        others.update(module_terms(stem, modules, require_tests=True))
    if not others:
        return Selection("full", reason="every model module is affected")

    terms = mine | others
    if bad := sorted(t for t in terms if not TERM_RE.match(t)):
        return Selection("full", reason=f"unsafe -k term(s) {bad}")
    drop = f"not ({' or '.join(sorted(others))})"
    k_expr = f"({' or '.join(sorted(mine))}) or {drop}" if mine else drop
    return Selection("scoped", k_expr, reason=f"affected modules: {', '.join(sorted(affected)) or 'none'}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--changed-paths",
        default="",
        help="whitespace-separated repo-relative changed paths; empty ⇒ full",
    )
    args = ap.parse_args(argv)

    sel = classify(args.changed_paths.split())
    summary = f"bd123 test scope: **{sel.mode}** — {sel.reason}"
    print(summary)
    if sel.k_expr:
        print(f"  -k {sel.k_expr}")

    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as out:
            out.write(f"mode={sel.mode}\n")
            out.write(f"k_expr={sel.k_expr}\n")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as out:
            out.write(summary + "\n")
            if sel.k_expr:
                out.write(f"\n`-k {sel.k_expr}`\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
