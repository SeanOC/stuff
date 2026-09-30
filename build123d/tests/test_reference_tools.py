"""Offline tests for the reference-mirror tooling (pst-m9k6).

No network and no gcloud: ``reference_pull.copy_object`` (the single network
seam) is replaced by a stub backed by a temp-dir "bucket", so publish -> pull
round-trips run end to end against the real manifest/validation code.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent  # build123d/
sys.path.insert(0, str(ROOT / "tools"))

import reference_publish  # noqa: E402
import reference_pull  # noqa: E402
from reference_publish import PublishRefused, publish  # noqa: E402
from reference_pull import (  # noqa: E402
    BUCKET, CopyError, ManifestError, dump_sources, load_sources, local_path, pull,
    sha256_of, validate_record, verify,
)

GROUP = "test-group"
UPSTREAM_SUFFIXES = {".step", ".stp", ".stl", ".3mf", ".pdf", ".zip"}


class _Bucket(type(Path())):
    """A temp dir standing in for the bucket; ``calls`` logs every copy."""


@pytest.fixture
def bucket(tmp_path, monkeypatch):
    """Stub copy_object with a directory standing in for gs://stuff-reference-upstream/."""
    root = _Bucket(tmp_path / "bucket")
    calls = root.calls = []

    def fake_copy(src, dst, *, no_clobber=False):
        calls.append((str(src), str(dst)))
        src, dst = str(src), str(dst)
        if dst.startswith(BUCKET):  # upload
            target = root / dst[len(BUCKET):]
            if no_clobber and target.exists():
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(Path(src).read_bytes())
        else:  # download
            obj = root / src[len(BUCKET):]
            if not obj.exists():
                raise CopyError("missing-in-bucket", src)
            Path(dst).write_bytes(obj.read_bytes())

    monkeypatch.setattr(reference_pull, "copy_object", fake_copy)
    return root


@pytest.fixture
def manifest(tmp_path):
    path = tmp_path / "source-manifest.json"
    path.write_text(dump_sources([]))
    return path


def _file(tmp_path, name, data: bytes) -> Path:
    path = tmp_path / "src" / f"{len(data)}-{abs(hash(data))}" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _publish(path, manifest, **kw):
    return publish(GROUP, path, url="https://example.com/m/1", licence="CC-BY",
                   manifest=manifest, today="2026-09-29", **kw)


def _sample_record():
    sha = "a" * 64
    return {
        "source_file_id": f"{GROUP}/part-a.step", "source_group_id": GROUP,
        "filename": "Part A.step", "upstream_file_id": "42",
        "url": "https://example.com/m/1", "licence": "CC-BY", "access": "bucket",
        "current": sha,
        "versions": [{"sha256": sha, "size": 3, "gcs": f"{BUCKET}{GROUP}/{sha}/Part A.step",
                      "published_on": "2026-09-29"}],
    }


# --- verify / pull -------------------------------------------------------------

def test_sha256_verify(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"hello")
    good = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert sha256_of(path) == good
    assert verify(path, good)
    assert not verify(path, "0" * 64)
    assert not verify(tmp_path / "absent", good)


def test_pull_mismatch_leaves_unverified(tmp_path, bucket, manifest):
    src = _file(tmp_path, "Part A.step", b"v1")
    _publish(src, manifest)
    (record,) = load_sources(manifest)
    # Corrupt the bucket object: the download no longer matches the manifest.
    (bucket / record["versions"][0]["gcs"][len(BUCKET):]).write_bytes(b"tampered")
    root = tmp_path / "upstream"
    assert pull(record, root=root) == "mismatch"
    dest = local_path(record, record["current"], root)
    assert not dest.exists()
    assert dest.with_name(dest.name + ".unverified").read_bytes() == b"tampered"
    # CLI exits 1 on any non-verified row.
    assert reference_pull.main(["--manifest", str(manifest), "--root", str(root)]) == 1


def test_pull_skips_present(tmp_path, bucket, manifest):
    src = _file(tmp_path, "Part A.step", b"v1")
    _publish(src, manifest)
    (record,) = load_sources(manifest)
    root = tmp_path / "upstream"
    assert pull(record, root=root) == "verified"
    downloads = [c for c in bucket.calls if c[0].startswith(BUCKET)]
    assert pull(record, root=root) == "verified"
    assert [c for c in bucket.calls if c[0].startswith(BUCKET)] == downloads  # no re-fetch
    assert pull(record, root=root, verify_only=True) == "verified"
    assert reference_pull.main(["--manifest", str(manifest), "--root", str(root)]) == 0


def test_pull_missing_in_bucket_and_verify_only_missing(tmp_path, bucket, manifest):
    src = _file(tmp_path, "Part A.step", b"v1")
    _publish(src, manifest)
    (record,) = load_sources(manifest)
    root = tmp_path / "upstream"
    assert pull(record, root=root, verify_only=True) == "missing"
    for obj in bucket.rglob("*"):
        if obj.is_file():
            obj.unlink()
    assert pull(record, root=root) == "missing-in-bucket"
    assert not any(p.is_file() for p in root.rglob("*"))  # no .part left behind


# --- publish -------------------------------------------------------------------

def test_publish_refuses_changed_sha_without_update(tmp_path, bucket, manifest):
    _publish(_file(tmp_path, "Part A.step", b"v1"), manifest)
    before = manifest.read_text()
    uploads = list(bucket.calls)
    with pytest.raises(PublishRefused, match="--update"):
        _publish(_file(tmp_path, "Part A.step", b"v2-changed"), manifest)
    assert manifest.read_text() == before
    assert bucket.calls == uploads  # nothing copied
    # Re-publishing identical bytes is a no-op, not a refusal.
    assert _publish(_file(tmp_path, "Part A.step", b"v1"), manifest).startswith("unchanged")


def test_publish_v1_then_v2_same_file_keeps_both_versions(tmp_path, bucket, manifest):
    v1 = _file(tmp_path, "Part A.step", b"version one")
    v2 = _file(tmp_path, "Part A.step", b"version two!")
    _publish(v1, manifest)
    _publish(v2, manifest, update=True)
    (record,) = load_sources(manifest)
    sha1, sha2 = sha256_of(v1), sha256_of(v2)
    assert record["source_file_id"] == f"{GROUP}/part-a.step"  # stable identity
    assert [v["sha256"] for v in record["versions"]] == [sha1, sha2]
    assert record["current"] == sha2  # current moved

    # Both bucket objects exist independently (sha256 is in the path) ...
    for sha, data in ((sha1, b"version one"), (sha2, b"version two!")):
        assert (bucket / GROUP / sha / "Part A.step").read_bytes() == data
        assert (bucket / GROUP / sha / "LICENSE.txt").exists()
        assert json.loads((bucket / GROUP / sha / "SOURCE.json").read_text())["sha256"] == sha
    # ... and pull to independent, individually verifiable local paths.
    root = tmp_path / "upstream"
    assert pull(record, root=root) == "verified"  # current = v2
    assert pull(record, sha256=sha1, root=root) == "verified"
    p1, p2 = local_path(record, sha1, root), local_path(record, sha2, root)
    assert p1 != p2 and verify(p1, sha1) and verify(p2, sha2)

    # An artefact FK (source_file_id, source_sha256) on v1 still resolves.
    fk = {"source_file_id": f"{GROUP}/part-a.step", "source_sha256": sha1}
    hits = [(r, v) for r in load_sources(manifest) if r["source_file_id"] == fk["source_file_id"]
            for v in r["versions"] if v["sha256"] == fk["source_sha256"]]
    assert len(hits) == 1


def test_two_files_one_group_roundtrip(tmp_path, bucket, manifest):
    a = _file(tmp_path, "Part A.step", b"aaa")
    b = _file(tmp_path, "Part B.step", b"bbb")
    _publish(a, manifest, upstream_file_id="1")
    _publish(b, manifest, upstream_file_id="2")
    records = load_sources(manifest)
    assert [r["source_file_id"] for r in records] == [f"{GROUP}/part-a.step", f"{GROUP}/part-b.step"]
    assert {r["source_group_id"] for r in records} == {GROUP}
    root = tmp_path / "upstream"
    assert reference_pull.main(["--manifest", str(manifest), "--root", str(root),
                                "--group", GROUP]) == 0
    assert reference_pull.main(["--manifest", str(manifest), "--root", str(root),
                                "--only", f"{GROUP}/part-b.step", "--verify-only"]) == 0
    assert all(verify(local_path(r, r["current"], root), r["current"]) for r in records)


# --- manifest ------------------------------------------------------------------

def test_source_manifest_roundtrip():
    """The committed manifest validates and is in canonical (dump) form."""
    text = reference_pull.MANIFEST.read_text()
    records = load_sources(reference_pull.MANIFEST)
    assert records
    assert dump_sources(records) == text


def test_source_file_ids_unique():
    ids = [r["source_file_id"] for r in load_sources(reference_pull.MANIFEST)]
    assert len(ids) == len(set(ids))


def _mut(path, value):
    def apply(record):
        target = record
        for key in path[:-1]:
            target = target[key]
        if value is KeyError:
            del target[path[-1]]
        else:
            target[path[-1]] = value
    return apply


MALFORMED = {
    "group-traversal": ("source_group_id", _mut(["source_group_id"], "../etc")),
    "group-uppercase": ("source_group_id", _mut(["source_group_id"], "Test-Group")),
    "filename-separator": ("filename", _mut(["filename"], "sub/Part A.step")),
    "filename-backslash": ("filename", _mut(["filename"], "..\\Part A.step")),
    "filename-dotdot": ("filename", _mut(["filename"], "..")),
    "filename-wildcard": ("filename", _mut(["filename"], "Part [A].step")),
    "id-not-derived": ("source_file_id", _mut(["source_file_id"], f"{GROUP}/other.step")),
    "sha-uppercase": ("versions.sha256", _mut(["versions", 0, "sha256"], "A" * 64)),
    "sha-short": ("versions.sha256", _mut(["versions", 0, "sha256"], "a" * 63)),
    "size-negative": ("versions.size", _mut(["versions", 0, "size"], -1)),
    "gcs-other-bucket": ("versions.gcs", _mut(["versions", 0, "gcs"],
                                              f"gs://elsewhere/{GROUP}/{'a' * 64}/Part A.step")),
    "gcs-wrong-object": ("versions.gcs", _mut(["versions", 0, "gcs"],
                                              f"{BUCKET}{GROUP}/{'a' * 64}/Other.step")),
    "current-unknown": ("current", _mut(["current"], "b" * 64)),
    "access-public": ("access", _mut(["access"], "public")),
    "url-missing": ("url", _mut(["url"], KeyError)),
}


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_rejects_malformed_record(case, tmp_path, bucket):
    field, mutate = MALFORMED[case]
    record = _sample_record()
    validate_record(copy.deepcopy(record))  # the baseline is sound
    mutate(record)
    with pytest.raises(ManifestError, match=rf": {field}: "):
        validate_record(record)
    # pull aborts on load, before any copy.
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema": 2, "sources": [record]}))
    assert reference_pull.main(["--manifest", str(path), "--root", str(tmp_path / "up")]) == 2
    assert bucket.calls == []


def test_rejects_duplicate_source_file_id(tmp_path):
    path = tmp_path / "dup.json"
    path.write_text(json.dumps({"schema": 2, "sources": [_sample_record(), _sample_record()]}))
    with pytest.raises(ManifestError, match="source_file_id: duplicated"):
        load_sources(path)


def test_publish_rejects_unsafe_group_before_copy(tmp_path, bucket, manifest):
    src = _file(tmp_path, "Part A.step", b"x")
    with pytest.raises(ManifestError, match="source_group_id"):
        publish("../up", src, url="https://example.com", licence="CC-BY", manifest=manifest)
    assert bucket.calls == []


def test_publish_is_never_invoked_by_ci():
    """OPERATOR-ONLY: no workflow (live or staged) may call the publish script."""
    repo = ROOT.parent
    workflows = [*(repo / ".github" / "workflows").glob("*.y*ml"), *(ROOT / "ci").glob("*.y*ml")]
    assert workflows
    for wf in workflows:
        assert "reference_publish" not in wf.read_text(), wf


def test_no_upstream_file_committed():
    """No mirrored upstream file is committed under build123d/reference/.

    A SUFFIX check over committed paths (git ls-files), not a text grep:
    source-manifest.json and FETCH.md legitimately name .step/.stl files."""
    repo = ROOT.parent
    out = subprocess.run(["git", "ls-files", "-z", "--", "build123d/reference"], cwd=repo,
                         capture_output=True, check=True).stdout.decode()
    committed = [p for p in out.split("\0") if p]
    assert "build123d/reference/source-manifest.json" in committed
    offenders = [p for p in committed
                 if Path(p).suffix.lower() in UPSTREAM_SUFFIXES or "/upstream/" in p]
    assert offenders == []
