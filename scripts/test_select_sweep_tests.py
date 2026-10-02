"""Tests for scripts/select-sweep-tests.py (pst-776).

Exercises the mode decision (full / selective / skip), the
conservative widenings (assets, hostile filenames, sweep infra), and
the shard binning against the real repo tree.

Runs in CI via the scripts/ pytest step (wired in pst-u6t); run
locally with `python3 -m pytest scripts/`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "select-sweep-tests.py"

spec = importlib.util.spec_from_file_location("select_sweep_tests", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod  # dataclass introspection needs the registry
spec.loader.exec_module(mod)

# A model that exists in the tree, so its sweep file passes the
# existence check.
REAL_STEM = "gridfinity_bin"
REAL_TEST = f"tests/sweep/{REAL_STEM}.test.ts"


def test_empty_change_list_is_full_sweep() -> None:
    assert mod.classify([]).mode == "full"


def test_docs_and_app_only_skips() -> None:
    sel = mod.classify(["docs/ci.md", "app/page.tsx", "components/StlViewer.tsx"])
    assert sel.mode == "skip"
    assert sel.files == []


def test_invariants_sidecar_only_skips() -> None:
    sel = mod.classify([f"models/{REAL_STEM}.invariants.py"])
    assert sel.mode == "skip"


def test_single_model_is_selective_with_coverage_guard() -> None:
    sel = mod.classify([f"models/{REAL_STEM}.scad", "docs/ci.md"])
    assert sel.mode == "selective"
    assert sel.files == [mod.COVERAGE_TEST, REAL_TEST]


def test_per_model_sweep_file_change_is_selective() -> None:
    sel = mod.classify([REAL_TEST])
    assert sel.mode == "selective"
    assert REAL_TEST in sel.files


def test_deleted_model_drops_to_coverage_guard_only() -> None:
    # A stem with no sweep file in the tree (deleted or not yet
    # created): only the coverage meta-guard runs, and it is what
    # fails the run when a model exists without a sweep file.
    sel = mod.classify(["models/no_such_model_xyz.scad"])
    assert sel.mode == "selective"
    assert sel.files == [mod.COVERAGE_TEST]


def test_global_inputs_force_full() -> None:
    for path in [
        "lib/wasm/render.ts",
        "lib/scad-params/parse.ts",
        "libs/README.md",
        "vitest.sweep.config.ts",
        "scripts/vendor-libs.sh",
        "scripts/select-sweep-tests.py",
        "package-lock.json",
        ".github/workflows/param-sweep.yml",
        "tests/sweep/runner.ts",
        "tests/sweep/known-failures.ts",
    ]:
        sel = mod.classify([f"models/{REAL_STEM}.scad", path])
        assert sel.mode == "full", f"{path} should force a full sweep"


def test_model_asset_forces_full() -> None:
    # Non-.scad files under models/ (e.g. STLs consumed via import())
    # can affect any model that imports them — widen, don't guess.
    assert mod.classify(["models/ego_powerhead_operator.stl"]).mode == "full"


def test_hostile_filename_degrades_to_full_not_injection() -> None:
    sel = mod.classify(["models/$(curl evil).scad"])
    assert sel.mode == "full"
    assert sel.files == []


def _table_drift(root: Path, table: dict) -> tuple[list[str], list[str]]:
    """(dead keys with no models/<stem>.scad, models/*.scad stems with no key)."""
    stems = {p.stem for p in (root / "models").glob("*.scad")}
    return sorted(set(table) - stems), sorted(stems - set(table))


def test_measured_table_stems_exist() -> None:
    # A table entry whose model is gone is dead weight; a renamed
    # model silently falls back to the @param estimate. Keep the
    # table in sync with models/.
    dead, _ = _table_drift(REPO_ROOT, mod.MEASURED_SECONDS)
    assert not dead, (
        f"MEASURED_SECONDS entries with no models/<stem>.scad: {dead} — "
        "remove or rename the entries in scripts/select-sweep-tests.py"
    )


def test_every_model_has_a_measured_entry() -> None:
    # pst-l7c92: the 2026-07 table silently lost 9 of 28 models. None is
    # allowed (same fallback as a missing key) and is what
    # scripts/new-model.py inserts, so a scaffolded model passes; this
    # fails only for a model added by hand.
    _, missing = _table_drift(REPO_ROOT, mod.MEASURED_SECONDS)
    assert not missing, "".join(
        f'\nadd "{stem}": None, to the END of MEASURED_SECONDS in '
        "scripts/select-sweep-tests.py — or scaffold with scripts/new-model.py"
        for stem in missing
    )


def test_none_entry_falls_back_like_a_missing_key(monkeypatch) -> None:
    monkeypatch.setitem(mod.MEASURED_SECONDS, REAL_STEM, None)
    with_none = mod.estimated_cost(REAL_TEST)
    monkeypatch.delitem(mod.MEASURED_SECONDS, REAL_STEM)
    assert with_none == mod.estimated_cost(REAL_TEST)


def test_new_model_scaffold_keeps_the_table_guard_green(tmp_path: Path) -> None:
    # Acceptance (b): scaffold a model into a scratch tree seeded with
    # the real catalog + selector script, then load the EDITED script
    # and check the parity guard against the scratch models/.
    (tmp_path / "lib" / "models").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "models").mkdir()
    (tmp_path / "lib" / "models" / "catalog.ts").write_text(
        (REPO_ROOT / "lib" / "models" / "catalog.ts").read_text()
    )
    (tmp_path / "scripts" / "select-sweep-tests.py").write_text(SCRIPT.read_text())
    for stem in mod.MEASURED_SECONDS:
        (tmp_path / "models" / f"{stem}.scad").touch()

    res = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "new-model.py"),
            "zz_guard_demo",
            "--category",
            "storage",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr

    edited = tmp_path / "scripts" / "select-sweep-tests.py"
    spec2 = importlib.util.spec_from_file_location("select_sweep_scaffolded", edited)
    scaffolded = importlib.util.module_from_spec(spec2)
    sys.modules[spec2.name] = scaffolded
    spec2.loader.exec_module(scaffolded)

    assert scaffolded.MEASURED_SECONDS["zz_guard_demo"] is None
    assert list(scaffolded.MEASURED_SECONDS)[-1] == "zz_guard_demo"
    assert _table_drift(tmp_path, scaffolded.MEASURED_SECONDS) == ([], [])


def test_unknown_model_falls_back_to_param_estimate() -> None:
    cost = mod.estimated_cost("tests/sweep/no_such_model_xyz.test.ts")
    assert cost == mod.FALLBACK_SECONDS_PER_CASE  # 1 case × fallback rate


def test_shards_cover_all_files_exactly_once() -> None:
    files = mod.all_sweep_files()
    shards = mod.build_shards(files)
    assert 1 <= len(shards) <= mod.MAX_SHARDS
    flat = [f for shard in shards for f in shard]
    assert sorted(flat) == sorted(files)


def test_selective_single_model_gets_one_shard() -> None:
    shards = mod.build_shards([mod.COVERAGE_TEST, REAL_TEST])
    assert len(shards) == 1


def test_cli_writes_github_output(tmp_path: Path) -> None:
    out_file = tmp_path / "gh_output"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--changed-paths", f"models/{REAL_STEM}.scad"],
        check=True,
        capture_output=True,
        text=True,
        env={"GITHUB_OUTPUT": str(out_file), "PATH": "/usr/bin:/bin"},
    )
    assert "selective" in result.stdout
    lines = dict(
        line.split("=", 1) for line in out_file.read_text().splitlines()
    )
    assert lines["mode"] == "selective"
    assert lines["shard_total"] == "1"
    matrix = json.loads(lines["shard_matrix"])
    assert matrix == [{"id": 1, "files": f"{REAL_TEST} {mod.COVERAGE_TEST}"}]
