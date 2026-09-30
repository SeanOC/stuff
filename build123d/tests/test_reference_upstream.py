"""Upstream-marked tests: need the mirrored files on disk (pst-m9k6).

Deselected by default (pyproject addopts ``-m 'not upstream'``) so PR CI and
plain ``pytest`` stay offline. The trusted push-to-main ``reference-measure``
workflow runs ``tools/reference_pull.py`` and then ``pytest -m upstream``;
developers with bucket access do the same (see reference/FETCH.md).
pst-ff71 adds its measurement tests under this same marker.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from reference_pull import load_sources, pull  # noqa: E402


@pytest.mark.upstream
def test_every_manifest_source_is_present_and_verified():
    records = load_sources()
    assert records
    statuses = {r["source_file_id"]: pull(r, verify_only=True) for r in records}
    bad = {sid: status for sid, status in statuses.items() if status != "verified"}
    assert not bad, f"{len(bad)}/{len(records)} not verified: {bad}"
