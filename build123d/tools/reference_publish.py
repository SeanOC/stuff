"""OPERATOR-ONLY: publish one upstream reference file to the private GCS mirror.

    uv run tools/reference_publish.py <source_group_id> <local file> \\
        --url https://... --licence "..." [--upstream-file-id ID] [--update]

Never invoked by CI (the CI reader SA is read-only; this needs an operator's
write access to gs://stuff-reference-upstream/). See reference/FETCH.md.

Identity: ``source_file_id = <source_group_id>/<filename-slug>`` is derived
from the group + filename, so it is STABLE across re-publishes; the file's
sha256 is the VERSION. Versions are immutable and append-only:

* new file                -> new record, one version, ``current`` = it
* same sha256 as current  -> no-op
* changed sha256          -> REFUSED unless ``--update``; with ``--update`` the
                             new version is appended and ``current`` moves.
                             Old versions are never removed, so artefact FKs
                             ``(source_file_id, source_sha256)`` keep resolving.

Upload layout (the sha256 is in the path, so objects are never overwritten):
``<source_group_id>/<sha256>/{<filename>, LICENSE.txt, SOURCE.json}``. The
record is validated before any copy and the manifest is written only after
the upload succeeds, so it never points at a missing object.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

import reference_pull
from reference_pull import (
    MANIFEST, CopyError, ManifestError, check_filename, check_group, check_licence, dump_sources,
    gcs_path, load_sources, sha256_of, source_file_id, validate_sources,
)

__all__ = ["sha256_of", "source_record", "upload", "publish", "main"]


class PublishRefused(RuntimeError):
    """The publish would violate the immutable-version contract."""


def source_record(sid: str, manifest: Path = MANIFEST) -> dict | None:
    """The record for one source_file_id, or None if it is not published."""
    return next((r for r in load_sources(manifest) if r["source_file_id"] == sid), None)


def upload(local_file: Path, record: dict, version: dict) -> None:
    """Copy the file + LICENSE.txt + SOURCE.json under <group>/<sha256>/."""
    prefix = version["gcs"].rsplit("/", 1)[0] + "/"
    sidecar = {
        "source_file_id": record["source_file_id"],
        "url": record["url"],
        "upstream_file_id": record["upstream_file_id"],
        "filename": record["filename"],
        "sha256": version["sha256"],
        "size": version["size"],
        "licence": record["licence"],
        "published_on": version["published_on"],
        "published_by": "build123d/tools/reference_publish.py",
    }
    licence_txt = (
        f"{record['filename']}\n{record['url']}\nLicence: {record['licence']}\n"
        f"Mirrored {version['published_on']} for non-commercial use; not redistributed.\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "LICENSE.txt").write_text(licence_txt)
        (Path(tmp) / "SOURCE.json").write_text(json.dumps(sidecar, indent=1, ensure_ascii=False) + "\n")
        reference_pull.copy_object(local_file, version["gcs"], no_clobber=True)
        for name in ("LICENSE.txt", "SOURCE.json"):
            reference_pull.copy_object(Path(tmp) / name, prefix + name, no_clobber=True)


def publish(group: str, local_file: Path, *, url: str, licence: str,
            upstream_file_id: str | None = None, update: bool = False,
            manifest: Path = MANIFEST, today: str | None = None) -> str:
    """Upload (if needed) and upsert one source record; returns a status line."""
    local_file = Path(local_file)
    check_group(group, "publish")
    check_filename(local_file.name, "publish")
    check_licence(licence, "publish")  # also reject invalid input for unchanged bytes
    sid = source_file_id(group, local_file.name)
    sha = sha256_of(local_file)
    records = load_sources(manifest)
    record = next((r for r in records if r["source_file_id"] == sid), None)
    known = {v["sha256"] for v in record["versions"]} if record else set()

    if record and record["filename"] != local_file.name:
        raise PublishRefused(
            f"{sid}: filename {local_file.name!r} slugs onto existing {record['filename']!r}")
    if record and sha == record["current"]:
        return f"unchanged {sid} {sha[:12]} (already current)"
    if record and not update:
        raise PublishRefused(
            f"{sid}: sha256 {sha[:12]} differs from current {record['current'][:12]}; "
            "re-run with --update to append it as a new version")

    if record is None:
        record = {"source_file_id": sid, "source_group_id": group, "filename": local_file.name,
                  "upstream_file_id": upstream_file_id, "url": url, "licence": licence,
                  "access": "bucket", "current": sha, "versions": []}
        records.append(record)
    else:
        record.update(url=url, licence=licence)
        if upstream_file_id is not None:
            record["upstream_file_id"] = upstream_file_id

    version = None
    if sha not in known:
        version = {"sha256": sha, "size": local_file.stat().st_size,
                   "gcs": gcs_path(group, sha, local_file.name),
                   "published_on": today or dt.datetime.now(dt.UTC).date().isoformat()}
        record["versions"].append(version)
    record["current"] = sha
    validate_sources(records)  # before any copy

    if version is not None:
        upload(local_file, record, version)
    Path(manifest).write_text(dump_sources(records))
    action = "published" if len(record["versions"]) == 1 else (
        "appended" if version is not None else "re-pointed")
    return f"{action} {sid} {sha[:12]} ({len(record['versions'])} version(s))"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OPERATOR-ONLY: publish one reference file.")
    ap.add_argument("source_group_id")
    ap.add_argument("local_file", type=Path)
    ap.add_argument("--url", required=True, help="upstream page the file came from")
    ap.add_argument("--licence", required=True, help="upstream licence, verbatim")
    ap.add_argument("--upstream-file-id", help="upstream's own file id, if it has one")
    ap.add_argument("--update", action="store_true",
                    help="allow a changed sha256: append a version and move current")
    ap.add_argument("--manifest", type=Path, default=MANIFEST, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        print(publish(args.source_group_id, args.local_file, url=args.url, licence=args.licence,
                      upstream_file_id=args.upstream_file_id, update=args.update,
                      manifest=args.manifest))
    except (PublishRefused, ManifestError, CopyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
