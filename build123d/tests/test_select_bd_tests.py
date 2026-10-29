"""pst-3bga4: scripts/select-bd-tests.py picks the bd123 fast/audit scope.

Unmarked, so it runs in the fast job. It lives here rather than beside the
script because bd123 only runs tests/. The collection tests run pytest
--collect-only in a subprocess (~2 s each); they check the selected file
set, because a correct-looking -k string can still select one test.
"""

import importlib.util
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("select_bd_tests", ROOT / "scripts/select-bd-tests.py")
sel = sys.modules["select_bd_tests"] = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sel)

AUDIT = "audit and not audit_full and not upstream"
FAST = "not audit and not budget and not upstream"
BUDGET = "budget and not upstream"
# PR #247's model-scoped files (the PR itself also touched registry.py, so
# the real PR is full): one model module, its test, its docs and manifest.
PR_247 = [
    "build123d/docs/bench-lip-clip.md",
    "build123d/docs/renders/review/holder-bench-lip-clip.png",
    "build123d/docs/renders/sections/holder-bench-lip-clip.svg",
    "build123d/holders/bench_lip_clip.py",
    "build123d/manifest.json",
    "build123d/tests/test_bench_lip_clip.py",
    "lib/models/catalog.ts",
]


@pytest.fixture(scope="module")
def registry():
    return sel.load_registry()


def mine_terms(k_expr):
    """The `(<mine>)` group of a scoped k_expr, empty when it has none."""
    m = re.match(r"^\(([^()]*)\) or not \(", k_expr)
    return set(m.group(1).split(" or ")) if m else set()


def dropped_terms(k_expr):
    """The `not (<others>)` group of a scoped k_expr."""
    return set(k_expr.split("not (", 1)[1].removesuffix(")").split(" or "))


def collected(markexpr, k_expr, *paths):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BD_AUDIT_OUT", "PYTEST_XDIST"))}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *(paths or ["tests/"]), "--collect-only", "-q",
         "-p", "no:cacheprovider", "-m", markexpr, "-k", k_expr],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    return Counter(line.split("::")[0] for line in proc.stdout.splitlines() if "::" in line)


@pytest.mark.parametrize("paths", [
    [],
    [".github/workflows/bd123.yml"],
    *([f"build123d/{p}"] for p in sorted(sel.SHARED_FILES)),
    ["build123d/labels/label_text.py"],
    ["build123d/multibuild/channel.py"],
    ["build123d/openconnect/slot.py"],
    ["build123d/holders/signs.py"],  # helper that registers no model
    ["build123d/holders/bench_lip_clip.py", "build123d/drawer/body.py"],
    ["build123d/README.md"],
    ["build123d/tests/fixtures/unnamed-by-any-test.bin"],
    ["build123d/docs/design-guidelines.md"],  # named by tests/print_audit.py
    ["build123d/docs/renders/sections/not-a-model.svg"],
    ["build123d/tests/test_x;rm -rf.py"],
    # No model module affected: nothing to scope to, and the budget tier
    # would collect zero items (codex #249 round 1).
    ["build123d/manifest.json"],
    ["build123d/tests/test_honeycomb.py"],
    ["build123d/docs/spool-cradle-validation.md"],
    ["build123d/tests/baselines/geometry/geometry-baseline.json"],
    ["build123d/tests/gridfinity_capture_bin_edges.json"],
    ["build123d/tests/test_bd_render_service.py"],  # #181
])
def test_full(paths, registry):
    assert sel.classify(paths, registry).mode == "full"


def test_every_model_module_changed_is_full(registry):
    paths = [f"build123d/holders/{stem}.py" for stem in registry.modules]
    assert sel.classify(paths, registry).mode == "full"


@pytest.mark.parametrize("paths", [
    ["build123d/ci/README.md"],
    ["build123d/ci/README.md", "build123d/docs/renders/review/x.png",
     "build123d/tests/.test_durations", "lib/models/catalog.ts"],
])
def test_skip(paths, registry):
    assert sel.classify(paths, registry) == sel.Selection("skip", reason="no build123d test input changed")


@pytest.mark.parametrize("paths, mine", [
    # A model's own test file counts as a change to that model.
    (["build123d/tests/test_cup_lid.py"], {"holder_cup_lid", "holder-cup-lid", "test_cup_lid"}),
    (["build123d/holders/cup_lid.py", "build123d/manifest.json",
      "build123d/tests/baselines/geometry/geometry-baseline.json"],
     {"holder_cup_lid", "holder-cup-lid", "test_cup_lid", "test_manifest", *sel.BASELINE_READERS}),
    # 1:N modules select every model they register.
    (["build123d/holders/smoke.py"],
     {"smoke_opengrid_tile_1x1", "smoke-opengrid-tile-1x1", "smoke_multiconnect_roundhead",
      "smoke-multiconnect-roundhead", "test_smoke"}),
    (["build123d/holders/underware_junctions.py"],
     {"underware_l", "underware-l", "underware_t", "underware-t", "underware_x", "underware-x",
      "test_underware_junctions"}),
    # bench_width_saddle imports bench_lip_clip.
    (PR_247,
     {"holder_bench_lip_clip", "holder-bench-lip-clip", "test_bench_lip_clip",
      "holder_bench_width_saddle", "holder-bench-width-saddle", "test_bench_width_saddle",
      "test_manifest"}),
])
def test_scoped(paths, mine, registry):
    got = sel.classify(paths, registry)
    assert got.mode == "scoped"
    assert mine_terms(got.k_expr) == mine


def test_importers_of_a_changed_model_are_affected(registry):
    got = sel.classify(["build123d/holders/label_card.py"], registry)
    assert {"test_tombstone_sign", "test_underware_text_label", "test_label_card"} <= mine_terms(got.k_expr)


def test_unchanged_models_are_the_dropped_terms(registry):
    dropped = dropped_terms(sel.classify(["build123d/holders/cup_lid.py"], registry).k_expr)
    assert "holder_cup_lid" not in dropped and "test_cup_lid" not in dropped
    assert {"holder_spool_cradle", "test_spool_cradle", "underware_l"} <= dropped


def test_a_non_model_test_file_rides_along_with_a_model_change():
    got = sel.classify(["build123d/holders/cup_lid.py", "build123d/tests/test_honeycomb.py"])
    assert got.mode == "scoped"
    assert {"test_honeycomb", "holder_cup_lid"} <= mine_terms(got.k_expr)


@pytest.mark.parametrize("paths", [
    ["build123d/holders/cup_lid.py"],
    ["build123d/tests/test_cup_lid.py"],
    ["build123d/docs/renders/sections/holder-cup-lid.svg"],
])
@pytest.mark.parametrize("markexpr", [FAST, AUDIT, BUDGET])
def test_every_tier_collects_something_when_scoped(paths, markexpr):
    # pytest exits 5 on an empty selection, so an empty tier is a red job.
    got = sel.classify(paths)
    assert got.mode == "scoped"
    assert sum(collected(markexpr, got.k_expr).values()) >= 1


def test_github_output(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert sel.main(["--changed-paths", "build123d/holders/printer.py"]) == 0
    assert out.read_text() == "mode=full\nk_expr=\n"


def test_pr_247_audit_selection_keeps_the_models_own_sweep_and_registry_audits():
    k_expr = sel.classify(PR_247).k_expr
    files = collected(AUDIT, k_expr)
    own = collected(AUDIT, "test_bench_lip_clip", "tests/test_bench_lip_clip.py")
    # every endpoint/corner audit in the model's own file, not just the
    # registry-wide test_print_audit row (round-1 BLOCKING 1: 1 test, not 35)
    assert files["tests/test_bench_lip_clip.py"] == own["tests/test_bench_lip_clip.py"] > 1
    assert files["tests/test_print_audit.py"] >= 1
    # registry-wide audits whose ids name no model still run
    assert files["tests/test_geometry_baseline.py"] == 1
    assert "tests/test_spool_cradle.py" not in files
    assert sum(files.values()) < sum(collected(AUDIT, "not nothing_matches_this").values())


def test_pr_247_fast_selection_keeps_its_section_golden_and_drops_others():
    k_expr = sel.classify(PR_247).k_expr
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_review_sheet.py", "--collect-only", "-q",
         "-p", "no:cacheprovider", "-m", FAST, "-k", k_expr],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    goldens = {line for line in proc.stdout.splitlines() if "test_section_golden[" in line}
    assert goldens == {
        "tests/test_review_sheet.py::test_section_golden[holder-bench-lip-clip]",
        "tests/test_review_sheet.py::test_section_golden[holder-bench-width-saddle]",
    }


def test_baseline_readers_exist():
    for stem in sel.BASELINE_READERS:
        assert (ROOT / "tests" / f"{stem}.py").is_file()


def test_substring_names_of_unchanged_models_keep_the_changed_models_tests():
    # underware_t (junctions, unchanged) is a substring of underware_transition
    k_expr = sel.classify(["build123d/holders/underware_transition.py"]).k_expr
    assert "underware_t" in dropped_terms(k_expr)
    path = "tests/test_underware_transition.py"
    assert collected(FAST, k_expr, path) == collected(FAST, "not nothing_matches_this", path)
