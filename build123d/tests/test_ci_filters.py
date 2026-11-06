"""Pin the live workflow's PR/full tier routing and artifact contract.

The old cradle path filter is deliberately gone: promoting more carriers must
not accidentally run the extended sweep on every model PR. Staged historical
workflow proposals must be rebased before activation (see ci/README.md).
"""
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2]/'.github/workflows/bd123.yml'


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
