"""pst-rir4i: BD_AUDIT_OUT rows (tests/audit_record.py + the tests/conftest.py hook).

Each case runs an inner pytest session (pytester, in-process) with this suite's
conftest loaded as a plugin, so the hooks under test are the real ones.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest_plugins = ['pytester']

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests import audit_record

_spec = importlib.util.spec_from_file_location('bd123_conftest', Path(__file__).parent/'conftest.py')
HOOKS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HOOKS)

INNER = '''
import pytest
from tests.audit_record import record

@pytest.mark.audit
@pytest.mark.parametrize('name', ['a', 'b'])
def test_marked(name):
    print(f'AUDIT | {name} | wall 1.000')
    record(name, wall=1.0)

@pytest.mark.audit
@pytest.mark.audit_full
def test_marked_full():
    pass

@pytest.mark.audit
def test_marked_fails():
    record('boom', error='named error: boom')
    assert False

@pytest.mark.audit
@pytest.mark.skip(reason='stopped at setup')
def test_marked_skipped():
    pass

def test_unmarked():
    pass
'''


@pytest.fixture
def inner(pytester, monkeypatch):
    monkeypatch.delenv('PYTEST_XDIST_WORKER', raising=False)
    monkeypatch.delenv(audit_record.ENV, raising=False)
    pytester.makeini('[pytest]\nmarkers =\n    audit\n    audit_full\n    slow\n    budget\n')
    pytester.makepyfile(test_inner=INNER)
    return pytester


def run(pytester):
    return pytester.runpytest('-p', 'no:cacheprovider', plugins=[HOOKS])


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def test_marked_items_get_one_outcome_row_and_record_appends(inner, tmp_path, monkeypatch):
    out = tmp_path/'nested'/'audit'/'rows.jsonl'
    monkeypatch.setenv(audit_record.ENV, str(out))
    run(inner).assert_outcomes(passed=4, failed=1, skipped=1)
    got = rows(out)
    assert [r['kind'] for r in got if r['kind'] == 'session'] == ['session']
    assert [r for r in got if r['kind'] == 'collection'] == [
        {'kind': 'collection', 'collected': 6, 'audited': 5}]
    outcomes = {r['nodeid'].split('::')[-1]: r for r in got if r['kind'] == 'outcome'}
    # One row per audited item (the unmarked test has none): the call phase,
    # or the setup phase that skipped it.
    assert len(outcomes) == 5 == len([r for r in got if r['kind'] == 'outcome'])
    assert sorted(outcomes) == ['test_marked[a]', 'test_marked[b]', 'test_marked_fails',
                                'test_marked_full', 'test_marked_skipped']
    assert outcomes['test_marked_fails']['outcome'] == 'failed'
    assert (outcomes['test_marked_skipped']['when'], outcomes['test_marked_skipped']['outcome']) == (
        'setup', 'skipped')
    assert {r['when'] for n, r in outcomes.items() if n != 'test_marked_skipped'} == {'call'}
    assert all(r['duration_s'] >= 0 and r['started_at'] for r in outcomes.values())
    measured = [r for r in got if r['kind'] == 'measurement']
    assert [(r['nodeid'].split('::')[-1], r['name'], r['fields']) for r in measured] == [
        ('test_marked[a]', 'a', {'wall': 1.0}), ('test_marked[b]', 'b', {'wall': 1.0}),
        ('test_marked_fails', 'boom', {'error': 'named error: boom'})]


def test_xdist_worker_writes_its_own_file(tmp_path, monkeypatch):
    monkeypatch.setenv(audit_record.ENV, str(tmp_path/'rows.jsonl'))
    monkeypatch.setenv('PYTEST_XDIST_WORKER', 'gw3')
    monkeypatch.setenv('PYTEST_CURRENT_TEST', 'tests/test_x.py::test_y[a b] (call)')
    audit_record.record('a b', wall=.9)
    assert not (tmp_path/'rows.jsonl').exists()
    assert rows(tmp_path/'rows.gw3.jsonl') == [
        {'kind': 'measurement', 'nodeid': 'tests/test_x.py::test_y[a b]',
         'name': 'a b', 'fields': {'wall': .9}}]


def test_unset_env_writes_nothing(inner, tmp_path):
    run(inner).assert_outcomes(passed=4, failed=1, skipped=1)
    assert audit_record.out_path() is None
    assert not list(inner.path.rglob('*.jsonl'))


def test_unwritable_path_warns_not_fails(inner, tmp_path, monkeypatch):
    blocker = tmp_path/'file'
    blocker.write_text('not a directory')
    monkeypatch.setenv(audit_record.ENV, str(blocker/'rows.jsonl'))
    with pytest.warns(audit_record.AuditRecordWarning):   # the session row, at configure
        result = run(inner)
    result.assert_outcomes(passed=4, failed=1, skipped=1, warnings=result.parseoutcomes()['warnings'])
    assert result.parseoutcomes()['warnings'] >= 1
    result.stdout.fnmatch_lines(['*AuditRecordWarning: BD_AUDIT_OUT: audit row not written*'])
