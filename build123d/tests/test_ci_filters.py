"""Pin the live workflow's PR/full tier routing and artifact contract.

The old cradle path filter is deliberately gone: promoting more carriers must
not accidentally run the extended sweep on every model PR. Staged historical
workflow proposals must be rebased before activation (see ci/README.md).
"""
import os
import json
import re
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

WORKFLOW = Path(__file__).resolve().parents[2]/'.github/workflows/bd123.yml'


def job(name):
    return re.split(r'\n  \w+:\n', WORKFLOW.read_text().split(f'\n  {name}:\n', 1)[1], maxsplit=1)[0]


def shell_step(job_text):
    """Execute the production shell, so gate tests exercise its actual logic."""
    return textwrap.dedent(job_text.split('        run: |\n', 1)[1].split('\n      - ', 1)[0])


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
    audit = text.split('\n  audit:\n', 1)[1].split('\n  audit_gate:\n', 1)[0]
    assert 'K_EXPR: ${{ needs.changes.outputs.k_expr }}' in audit
    assert '($K_EXPR) or test_registry_presets_fit_bed' in audit
    assert '-m "audit and not audit_full and not upstream"' in audit
    assert 'name: bd123-audit-rows-s${{ matrix.group }}' in audit
    assert 'BD_AUDIT_OUT: out/audit/rows.jsonl' in audit
    assert 'name: build123d audit (shard ${{ matrix.group }}/4)' in audit
    assert 'group: [1, 2, 3, 4]' in audit
    assert 'fail-fast: false' in audit
    assert '--splits 4 --group "$GROUP" --durations-path tests/.test_durations' in audit
    assert "github.event_name == 'schedule' && '--store-durations --clean-durations'" in audit
    assert 'name: bd123-test-durations-s${{ matrix.group }}' in audit
    assert 'include-hidden-files: true' in audit
    assert 'if-no-files-found: error' in audit
    assert '}}-s${{ matrix.group }}-${{ github.run_id }}' in audit
    assert '}}-s${{ matrix.group }}-\n' in audit
    gate = job('audit_gate')
    assert 'name: build123d audit\n' in gate
    assert 'needs: [changes, audit]' in gate
    assert 'if: always()' in gate
    for group in range(1, 5):
        assert f'collected_{group}: ${{{{ steps.audit.outputs.collected_{group} }}}}' in audit
        assert f'COLLECTED_{group}: ${{{{ needs.audit.outputs.collected_{group} }}}}' in gate


@pytest.mark.parametrize('event,select,mode,audit,collected,expected', [
    ('pull_request', 'success', 'full', 'success', ['true'] * 4, 0),
    ('pull_request', 'success', 'scoped', 'success', ['false', 'true', 'false', 'false'], 0),
    ('pull_request', 'success', 'scoped', 'success', ['false'] * 4, 1),
    ('pull_request', 'success', 'full', 'success', [''] * 4, 1),
    ('pull_request', 'success', 'full', 'failure', ['true'] * 4, 1),
    ('pull_request', 'success', 'full', 'cancelled', ['true'] * 4, 1),
    ('pull_request', 'failure', '', 'success', ['true'] * 4, 1),
    ('pull_request', 'cancelled', 'skip', 'skipped', [''] * 4, 1),
    ('pull_request', 'success', 'skip', 'skipped', [''] * 4, 0),
    ('pull_request', 'success', 'full', 'skipped', [''] * 4, 1),
    ('push', 'skipped', '', 'success', ['true'] * 4, 0),
    ('schedule', 'skipped', '', 'success', ['true'] * 4, 0),
    ('push', 'skipped', '', 'skipped', [''] * 4, 1),
])
def test_aggregate_reduces_shards(tmp_path, event, select, mode, audit, collected, expected):
    env = {**os.environ, 'EVENT': event, 'SELECT_RESULT': select, 'MODE': mode,
           'AUDIT_RESULT': audit, 'GITHUB_STEP_SUMMARY': str(tmp_path / 'summary')}
    env.update({f'COLLECTED_{i}': value for i, value in enumerate(collected, 1)})
    run = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', shell_step(job('audit_gate'))],
                         env=env, text=True, capture_output=True, timeout=10)
    assert run.returncode == expected, run.stdout + run.stderr


@pytest.mark.parametrize('status', [0, 1, 2, 3, 4, 5])
def test_shard_preserves_errors_except_empty_collection(tmp_path, status):
    uv = tmp_path / 'uv'
    uv.write_text(f'#!/bin/sh\nexit {status}\n')
    uv.chmod(0o755)
    output, summary = tmp_path / 'output', tmp_path / 'summary'
    env = {**os.environ, 'PATH': f'{tmp_path}:{os.environ["PATH"]}',
           'K_EXPR': 'small_model', 'GROUP': '3', 'STORE': '',
           'GITHUB_OUTPUT': str(output), 'GITHUB_STEP_SUMMARY': str(summary)}
    audit = job('audit').split('      - name: print audits', 1)[1]
    run = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', shell_step(audit)],
                         env=env, text=True, capture_output=True, timeout=10)
    assert run.returncode == (0 if status == 5 else status), run.stderr
    if status in (0, 5):
        assert output.read_text() == f'collected_3={"true" if status == 0 else "false"}\n'
    else:
        assert not output.exists()
    if status == 5:
        assert 'no tests collected (exit 5)' in summary.read_text()


def test_scoped_split_keeps_unknown_durations_once_and_allows_empty_shards(tmp_path):
    """Exercise pytest's real -k/-m hooks before splitting, without geometry."""
    source = tmp_path / 'test_models.py'
    source.write_text('import pytest\npytestmark = pytest.mark.audit\n'
                      'def test_small_model(): pass\n'
                      'def test_registry_presets_fit_bed(): pass\n'
                      'def test_other_model(): pass\n')
    durations = tmp_path / '.test_durations'
    durations.write_text(json.dumps({'test_models.py::test_small_model': 1.0}))
    selections = []
    for _ in range(2):
        shards = []
        for group in range(1, 5):
            run = subprocess.run(
                [sys.executable, '-m', 'pytest', '--collect-only', '-q',
                 '-m', 'audit and not audit_full and not upstream',
                 '-k', '(small_model) or test_registry_presets_fit_bed',
                 '--splits', '4', '--group', str(group), '--durations-path', str(durations)],
                cwd=tmp_path, text=True, capture_output=True, timeout=30,
            )
            assert run.returncode in (0, 5), run.stdout + run.stderr
            ids = [line for line in run.stdout.splitlines() if line.startswith('test_models.py::')]
            assert (run.returncode == 5) == (not ids)
            shards.append(ids)
        selections.append(shards)
    assert selections[0] == selections[1]
    assert sum(not shard for shard in selections[0]) == 2
    assert sorted(node for shard in selections[0] for node in shard) == [
        'test_models.py::test_registry_presets_fit_bed', 'test_models.py::test_small_model']
