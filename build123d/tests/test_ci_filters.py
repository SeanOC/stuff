"""Pin the live workflow's PR/full tier routing and artifact contract.

The old cradle path filter is deliberately gone: promoting more carriers must
not accidentally run the extended sweep on every model PR. Staged historical
workflow proposals must be rebased before activation (see ci/README.md).
"""
import os
from pathlib import Path
import subprocess
import sys

WORKFLOW = Path(__file__).resolve().parents[2]/'.github/workflows/bd123.yml'


def test_model_package_and_workflow_keep_package_scope(tmp_path):
    """Replay PR #286's actual paths through the workflow's selector CLI."""
    paths = [
        ".github/workflows/bd123.yml",
        "build123d/holders/opengrid_tile.py",
        "build123d/manifest.json",
        "build123d/opengrid_tile/tile.py",
        "build123d/tests/baselines/audit-rows/audit-rows-baseline.json",
        "build123d/tests/test_bd_render_service.py",
        "build123d/tests/test_opengrid_tile.py",
    ]
    assert 'run: uv run python scripts/select-bd-tests.py --changed-paths "$CHANGED_PATHS"' in WORKFLOW.read_text()
    output = tmp_path / "output"
    env = {**os.environ, "GITHUB_OUTPUT": str(output),
           "GITHUB_STEP_SUMMARY": str(tmp_path / "summary")}
    subprocess.run(
        [sys.executable, "scripts/select-bd-tests.py", "--changed-paths", " ".join(paths)],
        cwd=WORKFLOW.parents[2] / "build123d", env=env, check=True,
        capture_output=True, text=True, timeout=60,
    )
    selected = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert selected["mode"] == "scoped"
    mine, others = selected["k_expr"].split(" or not ", 1)
    assert {"opengrid_tile", "opengrid-tile", "test_opengrid_tile",
            "test_bd_render_service"} <= set(mine.strip("()").split(" or "))
    assert "test_spool_cradle" in others


def test_full_sweep_runs_on_main_and_schedule_not_prs():
    text = WORKFLOW.read_text()
    full = text.split('\n  audit_full:\n', 1)[1]
    assert "if: ${{ !cancelled() && github.event_name != 'pull_request' }}" in full
    assert 'needs.changes.outputs.cradle' not in text
    assert 'cradle:' not in text
    assert '-m "audit_full and not upstream"' in full
    assert '--splits 6' in full
    assert '--durations-path tests/.test_durations' in full


def test_pr_audits_keep_scope_and_rows():
    text = WORKFLOW.read_text()
    audit = text.split('\n  audit:\n', 1)[1].split('\n  changes:\n', 1)[0]
    assert 'K_EXPR: ${{ needs.changes.outputs.k_expr }}' in audit
    assert '($K_EXPR) or test_registry_presets_fit_bed' in audit
    assert '-m "audit and not audit_full and not upstream"' in audit
    assert 'name: bd123-audit-rows\n' in audit
    assert 'BD_AUDIT_OUT: out/audit/rows.jsonl' in audit
    assert 'name: build123d audit\n' in audit
