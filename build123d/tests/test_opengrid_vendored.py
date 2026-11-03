"""Offline guards for the mirrored, pinned openGrid Python dependency."""

import hashlib
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "opengrid"
COMMIT = "eea2b4154a10d2909e5edece567cbe0563aaf955"
ARCHIVE_SHA256 = "336247b93ca79ff68c4969e628dacf8fbc321b4c29e70bb0162a350183affaad"
# Computed from the verified mirror archive after the documented pruning,
# before adding our SOURCE.json. This is NOT the compressed archive's hash.
TREE_SHA256 = "7ad73228945bfc53f8c81dd4b90f77b0709117248fde8c706902b883509a6a7d"


def test_dependency_uses_local_source():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["tool"]["uv"]["sources"]["opengrid"] == {"path": "vendor/opengrid"}
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    package = next(p for p in lock["package"] if p["name"] == "opengrid")
    assert package["source"] == {"directory": "vendor/opengrid"}
    for name in ("pyproject.toml", "uv.lock"):
        assert "makerrepo.com" not in (ROOT / name).read_text(), name


def test_pruned_vendor_tree_matches_pin():
    # Ignore only local Python/setuptools build products and our provenance
    # record. Include paths as well as contents to detect additions/removals.
    files = [
        p for p in sorted(VENDOR.rglob("*"))
        if p.is_file() and p != VENDOR / "SOURCE.json"
        and not any(part in {"__pycache__", "build"} or part.endswith(".egg-info")
                    for part in p.relative_to(VENDOR).parts)
    ]
    rows = "".join(
        f"{p.relative_to(VENDOR).as_posix()}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\n"
        for p in files
    )
    assert hashlib.sha256(rows.encode()).hexdigest() == TREE_SHA256


def test_mirror_archive_and_vendor_provenance_match_pin():
    manifest = json.loads((ROOT / "reference/source-manifest.json").read_text())
    source_id = f"opengrid-lib/opengrid-{COMMIT}.tar.gz"
    record = next(s for s in manifest["sources"] if s["source_file_id"] == source_id)
    assert record["source_group_id"] == "opengrid-lib"
    assert record["upstream_file_id"] == COMMIT
    assert record["current"] == ARCHIVE_SHA256
    version = next(v for v in record["versions"] if v["sha256"] == ARCHIVE_SHA256)
    assert json.loads((VENDOR / "SOURCE.json").read_text()) == {
        "upstream_url": record["url"],
        "commit": COMMIT,
        "licence": "MIT (Launch Platform 2026)",
        "gcs": version["gcs"],
        "published_on": version["published_on"],
        "archive_sha256": ARCHIVE_SHA256,
    }
    assert record["licence"] == "MIT (Launch Platform 2026)"
    assert (VENDOR / "LICENSE").read_bytes() == (
        ROOT / "reference/LICENSES/MIT-Launch-Platform-2026.txt"
    ).read_bytes()
