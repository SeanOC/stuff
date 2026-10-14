"""pst-24tr6: bd123.yml partitions the suite into jobs by marker.

fast       -m 'not audit and not budget and not upstream'
budget     -m 'budget and not upstream'                (serial, in fast)
audit      -m 'audit and not audit_full and not upstream'
audit_full -m 'audit_full and not upstream'            (6 pytest-split shards)

The partition only holds if audit_full is a subset of audit (else an item runs
in fast AND audit_full) and budget is disjoint from audit (else it runs, and
skips under xdist, in the audit job instead of the serial step).

pst-rir4i: with BD_AUDIT_OUT set, every audit/audit_full item also leaves one
JSON outcome row (tests/audit_record.py; reader recipe in ci/README.md).
"""
import locale
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# The test modules add the build123d root themselves, after this conftest
# loads; import the helper as `tests.audit_record` so there is one module.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests import audit_record


@pytest.fixture(autouse=True)
def _restore_locale():
    """lib3mf (Mesher read/write) resets the process locale to C; never let that
    leak into a later test's default-encoding file read (pst-0zfra)."""
    saved = locale.setlocale(locale.LC_ALL)
    yield
    locale.setlocale(locale.LC_ALL, saved)


def pytest_addoption(parser):
    parser.addoption('--run-slow', action='store_true', default=False,
                     help='run explicitly gated expensive geometry contracts')


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--run-slow'):
        skip = pytest.mark.skip(reason='requires --run-slow')
        for item in items:
            if item.get_closest_marker('slow'):
                item.add_marker(skip)
    bad = [item.nodeid for item in items
           if (item.get_closest_marker('audit_full')
               and not item.get_closest_marker('audit'))
           or (item.get_closest_marker('budget')
               and item.get_closest_marker('audit'))]
    assert not bad, f'bd123 marker partition broken (see tests/conftest.py): {bad}'


def pytest_configure(config):
    # The directory exists (and holds a session row) whenever BD_AUDIT_OUT is
    # set, so the CI upload never sees a missing path even if no item ran.
    audit_record.append({'kind': 'session', 'markexpr': config.getoption('markexpr', default=None),
                         'group': config.getoption('group', default=None),
                         'started_at': datetime.now(UTC).isoformat()})


def _audited(item):
    return item.get_closest_marker('audit') or item.get_closest_marker('audit_full')


def pytest_collection_finish(session):
    # Each xdist worker collects the whole selection (the controller none), so
    # every worker file carries the same counts: the job's collected total and
    # how many outcome rows it owes.
    audit_record.append({'kind': 'collection', 'collected': len(session.items),
                         'audited': sum(1 for item in session.items if _audited(item))})


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    # One row per item: its call phase, or the setup phase that stopped it
    # (skip/error); a failing teardown adds a row with when='teardown'.
    if (_audited(item)
            and (report.when == 'call' or (report.when == 'setup' and not report.passed)
                 or (report.when == 'teardown' and report.failed))):
        audit_record.append({
            'kind': 'outcome', 'nodeid': report.nodeid, 'when': report.when,
            'outcome': report.outcome, 'xfail': hasattr(report, 'wasxfail'),
            'duration_s': round(report.duration, 3),
            'group': item.config.getoption('group', default=None),
            'started_at': datetime.fromtimestamp(call.start, UTC).isoformat()})
    return report
