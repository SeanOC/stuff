"""pst-rir4i: machine-readable audit rows, published by CI for reviewers.

With BD_AUDIT_OUT unset (every local run) nothing here writes anything. When it
is set (bd123.yml's audit and audit_full jobs), each process appends JSON lines
to its own file: the path as given for the controller, `rows.<gwN>.jsonl` for
an xdist worker, so lines from parallel workers never interleave. Three kinds:

  session      one per process at startup (tests/conftest.py): -m, --group
  outcome      R1, one per audit/audit_full item (tests/conftest.py hook)
  measurement  R2, record(name, **fields) beside a test's measurement print

A write failure is a warning, never a test failure. The reader recipe is in
build123d/ci/README.md.
"""
import json
import os
import warnings
from pathlib import Path

ENV = 'BD_AUDIT_OUT'
# xdist workers and the controller share this cwd (bd123.yml: build123d/).
_BASE = Path.cwd()


class AuditRecordWarning(UserWarning):
    pass


def out_path():
    """This process's row file, or None when BD_AUDIT_OUT is unset."""
    raw = os.environ.get(ENV)
    if not raw:
        return None
    path = _BASE/raw
    worker = os.environ.get('PYTEST_XDIST_WORKER')
    return path.with_name(f'{path.stem}.{worker}{path.suffix}') if worker else path


def append(row):
    path = out_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Explicit encoding: lib3mf resets the locale to C mid-run (pst-0zfra).
        with path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(row, default=str, ensure_ascii=False)+'\n')
    except OSError as exc:
        warnings.warn(f'{ENV}: audit row not written to {path}: {exc}', AuditRecordWarning)


def record(name, **fields):
    """Mirror a test's measurement print line as one row for the running item."""
    current = os.environ.get('PYTEST_CURRENT_TEST', '')
    append({'kind': 'measurement', 'nodeid': current.rsplit(' (', 1)[0] or None,
            'name': name, 'fields': fields})
