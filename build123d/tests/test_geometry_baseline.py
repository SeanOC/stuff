"""Only the BREP comparison is an in-CI baseline gate; no bake or rows needed."""
import time

import pytest

from scripts.baseline_common import compare, load_waivers, read_baseline
from scripts.geometry_baseline import collect


@pytest.mark.baseline
@pytest.mark.audit
def test_app_preset_geometry_baseline():
    start = time.monotonic()
    actual = collect()
    failures, waived = compare("geometry", read_baseline("geometry")["rows"],
                               actual, load_waivers())
    print(f"geometry baseline: {len(actual)} presets; {time.monotonic() - start:.3f}s")
    assert not failures, "\n".join(waived + failures)
