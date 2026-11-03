"""Offline provenance and license boundaries for the committed HomeRacker kit."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "libs/homeracker"


def test_reference_and_vendor_pins_agree():
    source = json.loads((VENDOR / "SOURCE.json").read_text())
    bosl = json.loads((VENDOR / "BOSL2/SOURCE.json").read_text())
    refs = json.loads((ROOT / "tests/fixtures/homeracker-reference.json").read_text())
    assert source["commit"].startswith("90556d1")
    assert source["commit"] == refs["upstream_commit"]
    assert bosl["tag"] == "v2.0.779"
    assert bosl["commit"] == refs["bosl2_commit"]
    assert "456fcd8" in (ROOT / "scripts/vendor-libs.sh").read_text()


def test_homeracker_cannot_resolve_the_global_bosl2():
    for path in (VENDOR / "models").rglob("*.scad"):
        assert not re.search(r"^\s*(?:include|use)\s*<BOSL2/", path.read_text(), re.M), path
    for path in (ROOT / "models").glob("homeracker_*.scad"):
        assert "include <homeracker/BOSL2/std.scad>" in path.read_text()
        assert path.read_text().startswith("// SPDX-License-Identifier: CC-BY-SA-4.0")


def test_licenses_and_attribution_are_committed():
    assert "Patrick Pötz" in (VENDOR / "NOTICE").read_text()
    assert "Permission is hereby granted, free of charge" in (VENDOR / "LICENSE").read_text()
    assert (VENDOR / "models/LICENSE").read_text().startswith("Attribution-ShareAlike 4.0 International")
    assert (VENDOR / "BOSL2/LICENSE").is_file()
    assert (ROOT / "models/homeracker-LICENSE.md").is_file()
    assert (ROOT / "build123d/reference/LICENSES/CC-BY-SA-4.0.txt").is_file()
    assert '"Attribution-ShareAlike 4.0 International": "reference/LICENSES/CC-BY-SA-4.0.txt"' in (
        ROOT / "build123d/tools/reference_pull.py"
    ).read_text()


def test_required_upstream_subset_is_present():
    for group in ("core", "foot", "panel", "bracket", "sleeve", "rackmount_ears", "keystone"):
        assert list((VENDOR / "models" / group).rglob("*.scad")), group
    assert (VENDOR / "models/core/presets/supports.scad").is_file()
    assert not list(VENDOR.rglob("*.png"))
