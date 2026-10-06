"""pst-24tr6: bd123.yml partitions the suite into jobs by marker.

fast       -m 'not audit and not budget and not upstream'
budget     -m 'budget and not upstream'                (serial, in fast)
audit      -m 'audit and not audit_full and not upstream'
audit_full -m 'audit_full and not upstream'            (3 pytest-split shards)

The partition only holds if audit_full is a subset of audit (else an item runs
in fast AND audit_full) and budget is disjoint from audit (else it runs, and
skips under xdist, in the audit job instead of the serial step).
"""
import locale

import pytest


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
