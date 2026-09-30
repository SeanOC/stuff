# Upstream reference files — private GCS mirror

Official upstream CAD files (Multiconnect / MultiBuild STEP, STL and PDF) are
used as measurement references. Their licences allow non-commercial *use* but
not redistribution. So they are **never committed**: they live in the private
bucket `gs://stuff-reference-upstream/`, and this repo commits only their
identities and checksums in [`source-manifest.json`](source-manifest.json).

## Pull (one line)

From `build123d/`, with bucket access (below):

```bash
uv run tools/reference_pull.py && uv run pytest -m upstream
```

This fetches every record's `current` version into the gitignored per-version
path `reference/upstream/<source_group_id>/<sha256[:12]>/<filename>` and
checks each file's sha256. A file that is already present and verified is not
fetched again. Selectors: `--group <source_group_id>`,
`--only <source_file_id>` (add `--sha256 <hex>` to get a specific older
version), and `--verify-only` (no network). Each file gets one of these
statuses:

| status | meaning |
|---|---|
| `verified` | on disk, sha256 matches the manifest |
| `missing-in-bucket` | the object does not exist in the bucket |
| `no-access` | gcloud was denied (no credentials / no role) |
| `mismatch` | the sha256 differs: the file is renamed `<filename>.unverified` |
| `missing` | `--verify-only` and the file was never pulled |

The command exits 0 only when every selected row is `verified`.

## Getting bucket access

- **Humans (dev):** the pull shells out to `gcloud storage cp`, so it uses your
  **gcloud user credentials** (`gcloud auth login`). Ask Sean or the mayor for
  `roles/storage.objectViewer` on `gs://stuff-reference-upstream` for your
  Google account. Check your access with
  `gcloud storage ls gs://stuff-reference-upstream/`.
- **CI:** only the trusted `reference-measure` workflow has access. It
  impersonates the read-only SA
  `reference-reader@stuff-prod-501716.iam.gserviceaccount.com`
  (repo variable `GCP_REFERENCE_READER_SA`) through Workload Identity
  Federation. That SA is **CI-only**: it is bound to the exact OIDC subject
  `repo:SeanOC/stuff:ref:refs/heads/main`, and humans never use it.

## Security rule

**Never add private-bucket auth to a `pull_request` workflow.** PR code is
untrusted: a PR job holding bucket credentials could exfiltrate the files. PR
CI (`bd123.yml`) stays offline, because `pyproject.toml`'s
`addopts = "-m 'not upstream'"` deselects the `upstream` tests there. Only
`reference-measure.yml` runs them. It triggers on `push: main` and
`workflow_dispatch` only, with `permissions: {contents: read, id-token: write}`.
Even if someone copied its auth step into a PR workflow, the WIF binding would
refuse the PR's OIDC subject. `gha-creds-*.json`, the credential file the auth
action writes, is gitignored.

## Two-manifest model

1. **`reference/source-manifest.json`: the upstream inputs.** It is owned by
   `tools/reference_publish.py` and follows schema 2:

   ```
   {schema: 2, sources: [{source_file_id, source_group_id, filename,
     upstream_file_id, url, licence, access: "bucket", current: <sha256>,
     versions: [{sha256, size, gcs, published_on}]}]}
   ```

   - **Identity is stable.**
     `source_file_id = <source_group_id>/<filename-slug>`, where the slug is
     the upstream filename lower-cased with every run of non-`[a-z0-9.]`
     characters replaced by `-`. Re-publishing the same upstream file keeps
     its id.
   - **Versions are immutable and append-only.** The sha256 is the version,
     and it is embedded in the bucket path
     `<group>/<sha256>/<filename>`. A changed checksum appends a version and
     moves `current`. Nothing is ever removed.
2. **The artefact manifest (pst-ff71): committed measured profiles.** Each
   committed artefact records the exact upstream version it was measured
   from, as the foreign key **`(source_file_id, source_sha256)`**. Because
   versions are never removed, an old artefact's FK keeps resolving after the
   source moves on.

The bucket-root `gs://stuff-reference-upstream/manifest.json` is the mayor's
provisioning inventory, used once to seed `source-manifest.json`. No tool
reads it.

## Publishing (OPERATOR-ONLY — never run by CI)

Publishing needs write access to the bucket, which the CI reader SA does not
have. From `build123d/`:

```bash
uv run tools/reference_publish.py <source_group_id> "<local file>" \
    --url https://<upstream page> --licence "<licence, verbatim>" \
    [--upstream-file-id <id>] [--update]
```

1. The script validates the group id and filename, computes the sha256, and
   derives the `source_file_id`.
2. How it handles each case:
   - **New file:** creates a new record.
   - **Same bytes as `current`:** does nothing.
   - **Changed bytes:** **refuses** unless you pass `--update`. With
     `--update`, it appends a version and moves `current`.
3. It uploads `<filename>`, `LICENSE.txt` and `SOURCE.json` to
   `<group>/<sha256>/` with `--no-clobber`, then rewrites
   `source-manifest.json`. Commit that file through a normal PR, which lets
   the trusted workflow verify the new version after the merge.

Both scripts validate every record **before** copying anything:

- the group id matches `^[a-z0-9-]+$`
- the filename is a bare name, with no separators or dot segments
- the sha256 is lowercase 64-hex
- the size is 0 or more
- `gcs` is exactly `gs://stuff-reference-upstream/<group>/<sha256>/<filename>`

A malformed record aborts with the name of the offending field.

## Validate the workflow

The staged/active workflow must pass pinned actionlint. Run it from the repo
root. PR CI does not run this check, so run it before pushing a workflow
change:

```bash
uvx --from actionlint-py==1.7.12.25 actionlint .github/workflows/reference-measure.yml
# while still staged: ... actionlint build123d/ci/reference-measure.yml
```
