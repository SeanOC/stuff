"""pst-24tr6: bd123.yml partitions the suite into jobs by marker.

fast       -m 'not audit and not budget and not upstream'
budget     -m 'budget and not upstream'                (serial, in fast)
audit      -m 'audit and not audit_full and not upstream'
audit_full -m 'audit_full and not upstream'            (3 pytest-split shards)

The partition only holds if audit_full is a subset of audit (else an item runs
in fast AND audit_full) and budget is disjoint from audit (else it runs, and
skips under xdist, in the audit job instead of the serial step).
"""


def pytest_collection_modifyitems(items):
    bad = [item.nodeid for item in items
           if (item.get_closest_marker('audit_full')
               and not item.get_closest_marker('audit'))
           or (item.get_closest_marker('budget')
               and item.get_closest_marker('audit'))]
    assert not bad, f'bd123 marker partition broken (see tests/conftest.py): {bad}'
