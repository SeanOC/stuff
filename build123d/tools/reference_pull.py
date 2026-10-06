"""Pull + sha256-verify upstream reference files from the private GCS mirror.

Reads ``reference/source-manifest.json`` (schema 2, owned by
``tools/reference_publish.py``) and fetches each source record's ``current``
version (or ``--sha256 <hex>`` for one record) from
``gs://stuff-reference-upstream/`` into the gitignored, per-version path

    build123d/reference/upstream/<source_group_id>/<sha256[:12]>/<filename>

A file already present and verified is not re-fetched. A checksum mismatch
renames the file ``<filename>.unverified`` and exits 1. Every record is
validated (safe group id / filename, 64-hex sha256, bucket-confined gcs path)
BEFORE anything is copied, so a malformed record cannot escape upstream/.

Callers: the trusted push-to-main ``reference-measure`` workflow and developers
with bucket access (see reference/FETCH.md). PR CI never runs this.

    uv run tools/reference_pull.py                       # all current versions
    uv run tools/reference_pull.py --group multibuild-snaps
    uv run tools/reference_pull.py --only <source_file_id> [--sha256 <hex>]
    uv run tools/reference_pull.py --verify-only         # no network
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent  # build123d/
MANIFEST = ROOT / "reference" / "source-manifest.json"
UPSTREAM = ROOT / "reference" / "upstream"
BUCKET = "gs://stuff-reference-upstream/"
SCHEMA = 2

# Source-manifest licence string -> committed licence text, relative to ROOT.
# Shared by reference validation, publishing and measurement provenance.
# Keys preserve verbatim upstream spellings; do not collapse aliases.
LICENCE_TEXTS = {
    "Multiboard Licence (non-commercial)": "reference/LICENSES/Multiboard-Licence-2025-12-19.txt",
    "Creative Commons — Attribution": "reference/LICENSES/CC-BY-4.0.txt",
    "CC BY-NC-SA 4.0": "reference/LICENSES/CC-BY-NC-SA-4.0.txt",
    "Creative Commons — Attribution  — Noncommercial  —  Share Alike":
        "reference/LICENSES/CC-BY-NC-SA-4.0.txt",
}

GROUP_RE = re.compile(r"^[a-z0-9-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RECORD_KEYS = (
    "source_file_id", "source_group_id", "filename", "upstream_file_id",
    "url", "licence", "access", "current", "versions",
)
VERSION_KEYS = ("sha256", "size", "gcs", "published_on")


class ManifestError(ValueError):
    """A source record (or the manifest envelope) fails validation."""


class CopyError(RuntimeError):
    """``gcloud storage cp`` failed; ``status`` is the pull-table status."""

    def __init__(self, status: str, detail: str = ""):
        super().__init__(f"{status}: {detail}".rstrip(": "))
        self.status = status


# --- identity + layout -------------------------------------------------------

def filename_slug(filename: str) -> str:
    """Upstream filename lower-cased, non-[a-z0-9.] runs -> '-'."""
    return re.sub(r"[^a-z0-9.]+", "-", filename.lower())


def source_file_id(source_group_id: str, filename: str) -> str:
    """Stable per-file identity: survives re-publishes of changed bytes."""
    return f"{source_group_id}/{filename_slug(filename)}"


def gcs_path(source_group_id: str, sha256: str, filename: str) -> str:
    return f"{BUCKET}{source_group_id}/{sha256}/{filename}"


def local_path(record: dict, sha256: str, root: Path = UPSTREAM) -> Path:
    """Immutable per-version local path for one version of a record."""
    return root / record["source_group_id"] / sha256[:12] / record["filename"]


# --- validation --------------------------------------------------------------

def _fail(where: str, field: str, why: str) -> None:
    raise ManifestError(f"{where}: {field}: {why}")


def check_group(group: object, where: str = "record") -> None:
    if not isinstance(group, str) or not GROUP_RE.match(group):
        _fail(where, "source_group_id", f"{group!r} must match {GROUP_RE.pattern}")


def check_filename(filename: object, where: str = "record") -> None:
    ok = (
        isinstance(filename, str)
        and filename not in ("", ".", "..")
        and "/" not in filename
        and "\\" not in filename
        and "\0" not in filename
        and not any(c in filename for c in "*?[]")  # gcloud URL wildcards
        and filename == PurePosixPath(filename).name
    )
    if not ok:
        _fail(where, "filename", f"{filename!r} must be a bare filename "
              "(no separators, dot segments or gcloud wildcards *?[])")


def _check_sha(sha: object, where: str, field: str) -> None:
    if not isinstance(sha, str) or not SHA256_RE.match(sha):
        _fail(where, field, f"{sha!r} must be lowercase 64-hex")


def check_licence(licence: object, where: str = "record") -> None:
    if not isinstance(licence, str) or licence not in LICENCE_TEXTS:
        accepted = ", ".join(repr(key) for key in LICENCE_TEXTS)
        _fail(where, "licence", f"{licence!r} has no committed licence text; "
              f"accepted LICENCE_TEXTS keys: {accepted}")


def validate_record(record: object) -> None:
    """Raise ManifestError naming the offending field; return None if sound."""
    if not isinstance(record, dict):
        _fail("record", "record", "must be an object")
    where = str(record.get("source_file_id", "record"))
    for key in RECORD_KEYS:
        if key not in record:
            _fail(where, key, "missing")
    group, filename = record["source_group_id"], record["filename"]
    check_group(group, where)
    check_filename(filename, where)
    if record["source_file_id"] != source_file_id(group, filename):
        _fail(where, "source_file_id", f"must be {source_file_id(group, filename)!r}")
    if record["upstream_file_id"] is not None and not isinstance(record["upstream_file_id"], str):
        _fail(where, "upstream_file_id", "must be a string or null")
    if not isinstance(record["url"], str) or not record["url"].startswith("https://"):
        _fail(where, "url", "must be an https:// URL")
    check_licence(record["licence"], where)
    if record["access"] != "bucket":
        _fail(where, "access", f"{record['access']!r} must be 'bucket'")
    versions = record["versions"]
    if not isinstance(versions, list) or not versions:
        _fail(where, "versions", "must be a non-empty list")
    seen = set()
    for version in versions:
        if not isinstance(version, dict):
            _fail(where, "versions", "entries must be objects")
        for key in VERSION_KEYS:
            if key not in version:
                _fail(where, f"versions.{key}", "missing")
        sha = version["sha256"]
        _check_sha(sha, where, "versions.sha256")
        if sha in seen:
            _fail(where, "versions.sha256", f"{sha} appears twice")
        seen.add(sha)
        size = version["size"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            _fail(where, "versions.size", f"{size!r} must be an integer >= 0")
        expected = gcs_path(group, sha, filename)
        if not isinstance(version["gcs"], str) or not version["gcs"].startswith(BUCKET):
            _fail(where, "versions.gcs", f"{version['gcs']!r} must start with {BUCKET}")
        if version["gcs"] != expected:
            _fail(where, "versions.gcs", f"{version['gcs']!r} must be {expected!r}")
        if not isinstance(version["published_on"], str) or not version["published_on"]:
            _fail(where, "versions.published_on", "must be a non-empty date string")
    _check_sha(record["current"], where, "current")
    if record["current"] not in seen:
        _fail(where, "current", f"{record['current']} is not one of versions")


def validate_sources(records: list[dict]) -> None:
    ids = Counter()
    for record in records:
        validate_record(record)
        ids[record["source_file_id"]] += 1
    dupes = sorted(k for k, n in ids.items() if n > 1)
    if dupes:
        raise ManifestError(f"source_file_id: duplicated: {', '.join(dupes)}")


def load_sources(path: Path = MANIFEST) -> list[dict]:
    """Load + fully validate the source manifest; returns its source records."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ManifestError(f"manifest: schema: must be {SCHEMA}")
    records = data.get("sources")
    if not isinstance(records, list):
        raise ManifestError("manifest: sources: must be a list")
    validate_sources(records)
    return records


def dump_sources(records: list[dict]) -> str:
    """Canonical manifest text (records sorted by source_file_id)."""
    ordered = [
        {**{k: r[k] for k in RECORD_KEYS},
         "versions": [{k: v[k] for k in VERSION_KEYS} for v in r["versions"]]}
        for r in sorted(records, key=lambda r: r["source_file_id"])
    ]
    return json.dumps({"schema": SCHEMA, "sources": ordered}, indent=2, ensure_ascii=False) + "\n"


# --- copy + verify -----------------------------------------------------------

def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, sha256: str) -> bool:
    return Path(path).is_file() and sha256_of(path) == sha256


def copy_object(src: str | Path, dst: str | Path, *, no_clobber: bool = False) -> None:
    """``gcloud storage cp`` one object; raises CopyError with a table status.

    The single network seam: offline tests replace this function."""
    cmd = ["gcloud", "storage", "cp", "--quiet"]
    if no_clobber:
        cmd.append("--no-clobber")
    proc = subprocess.run([*cmd, str(src), str(dst)], capture_output=True, text=True)
    if proc.returncode == 0:
        return
    err = proc.stderr.strip()
    low = err.lower()
    if "403" in err or "accessdenied" in low or "permission" in low or "does not have" in low:
        raise CopyError("no-access", err)
    if "404" in err or "notfound" in low or "no urls matched" in low or "not found" in low:
        raise CopyError("missing-in-bucket", err)
    raise CopyError("copy-failed", err)


def _quarantine(path: Path) -> None:
    path.replace(path.with_name(path.name + ".unverified"))


def pull(record: dict, *, sha256: str | None = None, verify_only: bool = False,
         root: Path = UPSTREAM) -> str:
    """Fetch + verify one version of a record; return its table status.

    Statuses: verified | missing-in-bucket | no-access | mismatch |
    missing (verify-only, not on disk) | unknown-version | copy-failed."""
    sha = sha256 or record["current"]
    version = next((v for v in record["versions"] if v["sha256"] == sha), None)
    if version is None:
        return "unknown-version"
    dest = local_path(record, sha, root)
    if dest.exists():
        if verify(dest, sha):
            return "verified"
        _quarantine(dest)
        if verify_only:
            return "mismatch"
    elif verify_only:
        return "missing"
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        copy_object(version["gcs"], part)
    except CopyError as exc:
        part.unlink(missing_ok=True)
        return exc.status
    if not verify(part, sha):
        _quarantine(part.replace(dest))
        return "mismatch"
    part.replace(dest)
    return "verified"


# --- CLI ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", metavar="SOURCE_FILE_ID", help="exactly one record")
    ap.add_argument("--group", metavar="SOURCE_GROUP_ID", help="every record in one group")
    ap.add_argument("--sha256", help="pull this version instead of current (needs --only)")
    ap.add_argument("--verify-only", action="store_true", help="check local files; no network")
    ap.add_argument("--manifest", type=Path, default=MANIFEST, help=argparse.SUPPRESS)
    ap.add_argument("--root", type=Path, default=UPSTREAM, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.sha256 is not None:
        if not args.only:
            ap.error("--sha256 selects a version of ONE record: pass --only too")
        if not SHA256_RE.match(args.sha256):
            ap.error("--sha256 must be lowercase 64-hex")

    try:
        records = load_sources(args.manifest)
    except ManifestError as exc:
        print(f"source manifest invalid: {exc}", file=sys.stderr)
        return 2
    if args.only:
        records = [r for r in records if r["source_file_id"] == args.only]
    if args.group:
        records = [r for r in records if r["source_group_id"] == args.group]
    if not records:
        print("no source records match the selection", file=sys.stderr)
        return 2

    tally = Counter()
    width = max(len(r["source_file_id"]) for r in records)
    for record in records:
        sha = args.sha256 or record["current"]
        status = pull(record, sha256=args.sha256, verify_only=args.verify_only, root=args.root)
        tally[status] += 1
        print(f"{status:<17} {record['source_file_id']:<{width}} {sha[:12]}", flush=True)
    summary = ", ".join(f"{n} {s}" for s, n in sorted(tally.items()))
    print(f"\n{tally['verified']}/{len(records)} verified ({summary})")
    return 0 if tally["verified"] == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
