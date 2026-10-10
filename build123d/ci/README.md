# Staged CI change — advisory VLM render review (pst-ae3v)

This directory holds a workflow change that the `stuff/worker` policy forbids
the agent from applying directly (no edits under `.github/workflows/`, no repo
settings changes). It is staged here for an operator to activate in **two
steps**.

## What it does

Wires the existing, offline-tested `build123d/scripts/render_review.py`
(Layer 2 of pst-3eun) into the **advisory** `bd123` CI job. A vision model
eyeballs the exported `out/*.png` renders and appends a Markdown summary to the
job step summary. It **never gates**: the script always exits `0`, the `bd123`
job is not a required status check, and the step carries `continue-on-error`.

Rebased by pst-bnya8 onto the current three-job workflow (see the last
section), preserving the capture dependency group and live timeouts. The step sits in the `fast` job, right after the export it reviews, and the file is
still byte-identical to `.github/workflows/bd123.yml` apart from the header
comment and the ADDED step. pst-ae3v is closed but this step was never
activated, so the proposal stays.

## Activate (operator, needs elevated access)

1. **Copy the proposed workflow into place** (the only change is the added
   `advisory VLM render review` step — everything else is byte-identical to the
   current workflow):

   ```bash
   cp build123d/ci/bd123.yml.proposed .github/workflows/bd123.yml
   git add .github/workflows/bd123.yml
   git commit -m "ops(bd123): activate advisory VLM render review (pst-ae3v)"
   ```

2. **Add the `OPENROUTER_API_KEY` repo secret** (Settings → Secrets and
   variables → Actions → New repository secret), or via CLI:

   ```bash
   gh secret set OPENROUTER_API_KEY --app actions   # paste the key when prompted
   ```

No branch-protection change is required: `bd123` is already advisory (not in
the required contexts on `main`), and this adds a step to it — the set of
required checks is unchanged. Confirm with:

```bash
gh api repos/:owner/:repo/branches/main/protection/required_status_checks/contexts
```

before and after (the list must not change).

## Toggle / disable

- **Off (soft):** delete the `OPENROUTER_API_KEY` secret. The step then prints
  `advisory review skipped: OPENROUTER_API_KEY not set.` and stays green.
- **Off (hard):** delete the `advisory VLM render review` step from the
  workflow.
- **Different model:** set a `RENDER_REVIEW_MODEL` repo variable/secret and add
  it to the step `env` (defaults to `qwen/qwen3-vl-235b-a22b-instruct`).

## Dry run (AC 4)

Once step 1 is on `main` (or the change is pushed to a PR branch that touches
`build123d/**`), open/refresh any PR that touches `build123d/**`; the `bd123`
job's **Summary** page shows the `## Advisory render review` section, which
names the exact model id and prompt version it used. AC 4's live dry run cannot
be performed by the worker (it can neither merge the workflow nor add the
secret) — it is the first thing to confirm after activation.

---

# Staged workflow — trusted reference-mirror measurement (pst-m9k6)

`reference-measure.yml` is the trusted push-to-main workflow for the private
upstream reference mirror (see `build123d/reference/FETCH.md`). The worker
policy forbids adding it under `.github/workflows/`, so it is staged here and
stays inert until an operator activates it.

## Activate (operator)

```bash
uvx --from actionlint-py==1.7.12.25 actionlint build123d/ci/reference-measure.yml   # exits 0
git mv build123d/ci/reference-measure.yml .github/workflows/reference-measure.yml
git commit -m "ops(reference-measure): activate trusted reference-mirror workflow (pst-m9k6)"
```

The file needs no edits when it moves. Its header comment still says STAGED,
so you can delete those first four lines as part of the move. Prerequisites
already exist (mayor, 2026-09-29):

- the repo variables `GCP_WIF_PROVIDER` and `GCP_REFERENCE_READER_SA`
- the read-only SA's WIF binding to `repo:SeanOC/stuff:ref:refs/heads/main`

The move itself matches the workflow's own path filter, so the activating push
to `main` triggers the first run. That run pulls every source in
`source-manifest.json` (210 at the time of writing) and runs
`pytest -m upstream`. The upstream tests are:

- `test_every_manifest_source_is_present_and_verified`
- pst-ff71's `test_runs_under_30s_on_every_measurable_source`, which covers
  every STEP/STL source
- `test_artifacts_regenerate`, which rebuilds the committed
  `reference/measured/` JSON/SVG from the mirror

**No `bd123.yml` change is needed.** The spec proposed adding
`-m 'not upstream'` to bd123's pytest line. Instead, `build123d/pyproject.toml`
now sets `addopts = "-m 'not upstream'"`, which deselects those tests in PR CI
and for plain local `pytest`. The trusted workflow's explicit `-m upstream`
wins because the last `-m` on the command line takes precedence.

# Staged workflows — docker layer cache + bd-render trigger paths (pst-l7c92)

`deploy-bd-render-service.yml.proposed` and `deploy-render-service.yml.proposed`
are FULL replacements for the two Cloud Run deploy workflows (CI P7). They
touch the deployer service-account path, so the mayor copies them into place on
the PR branch after codex passes the staged versions. Against the live files,
they change:

- **Both:** `docker build` + `docker push` become `docker/setup-buildx-action@v3`
  + `docker/build-push-action@v6` with `cache-from: type=gha` /
  `cache-to: type=gha,mode=max`. Tags, push target, Dockerfile, build context
  and the auth steps are unchanged. `IMAGE` moves from a `$GITHUB_ENV` export
  inside the old build step to the job `env:` block, because `gcloud run deploy
  --image "${IMAGE}:${GITHUB_SHA}"` still needs it. The type=gha backend uses
  the runner's own token, so `permissions:` is unchanged. Do not add
  `load: true`: nothing needs a local image.
- **bd-render only:** the trigger paths gain `build123d/multibuild/**` and
  `build123d/openconnect/**`. The Dockerfile COPYs both into the image, but a
  merge touching only those paths never redeployed (same class as pst-ubop).

## Activate (mayor, on the PR branch)

```bash
uvx --from actionlint-py==1.7.12.25 actionlint build123d/ci/deploy-*.proposed   # exits 0
git mv build123d/ci/deploy-bd-render-service.yml.proposed .github/workflows/deploy-bd-render-service.yml
git mv build123d/ci/deploy-render-service.yml.proposed .github/workflows/deploy-render-service.yml
git commit -m "ops(deploy): activate buildx gha cache + bd-render trigger paths (pst-l7c92)"
```

Each move matches its workflow's own path filter, so the merge to `main`
redeploys both services. That first run has a cold cache and does a full build.
Expect `importing cache manifest from gha` in the build log on the SECOND run,
which should finish in ≤ 2 min (`gh workflow run deploy-bd-render-service.yml`
gives you that second run). Then confirm the Cloud Run revision and a
`POST /render` smoke (the pst-ubop recipe).

# bd123 jobs and the marker contract (pst-24tr6)

`.github/workflows/bd123.yml` is split into three jobs, and pytest markers in
`build123d/pyproject.toml` decide which job runs each test. **fast** (`build123d
fast`) runs the manifest checks, every test that is neither `audit` nor
`budget`, then the `budget` tests serially (`-n 0`, because the 60 s per-model
budget measures serial CPU time), then the export. **audit** (`build123d
audit`) runs `audit and not audit_full`: every registry-sized print audit,
including each cradle style's presets, `PRINT_CORNER` and the reproducers,
plus the other registry-sized cradle checks that made `fast` 9m48s on the
runner: the mount-contract tests (20–130 s each), the dense-probe rear-knife
tests (outboard rear end and inboard cap) and the preset bake.
**audit_full** (`build123d audit (full sweep)`) runs the cradle corner sweep
(`audit_full`) as three `pytest-split` shards, balanced by the committed
`build123d/tests/.test_durations`. A PR runs it only when it touches
`holders/`, `multibuild/`, `openconnect/`, the audit/contract helpers,
`test_spool_cradle.py`, `tests/conftest.py`, `pyproject.toml` or `uv.lock`.
Every push to `main` and the nightly schedule (`17 9 * * *` UTC) run all three
jobs unconditionally. The contract: a test that builds a registry-sized model
and calls `audit()` gets `@pytest.mark.audit`; a cradle corner case also gets
`audit_full`; `tests/conftest.py` fails collection if an `audit_full` item lacks
`audit` or a `budget` item has it. Because a command-line `-m` replaces
`addopts`, every job's expression ends in `and not upstream`, which keeps PR CI
offline (`reference/FETCH.md`). Nightly failures are not filed as issues
(`issues: write` is outside this workflow's permissions); the mayor's heartbeat
checks `gh run list --workflow bd123 --event schedule`. The nightly also
re-measures each shard and uploads it as `bd123-test-durations-<n>`. To refresh
the balance, download the three files, merge them with
`jq -s add d1 d2 d3 > build123d/tests/.test_durations`, and commit the result
(optional: a stale file only skews shard balance, never coverage).


## Pending timeout fix (pst-bnya8)

`bd123-timeouts.patch` stages the timeout-only change against main `d696c91`.
It has **not** been applied to the live workflow: the bead still needs the
mayor-recorded WORKFLOW CARVE-OUT for `.github/workflows/bd123.yml`. The VLM
proposal above matches the current live workflow; after applying the timeout
patch, carry the same timeout changes into that proposal before opening a PR.

Timing evidence from GitHub Actions on 2026-10-10:

| Job | Observed duration | Staged limit | Rationale |
| --- | --- | --- | --- |
| fast | 24m57s before export, then cancelled | 40m | About 50% headroom on an estimated 26m complete job |
| audit | 22m53s complete | 35m | 50% headroom, rounded up to a whole minute |
| audit_full | Slowest shard 7m59s complete | 30m (unchanged) | Already exceeds the same headroom rule |

Sources: [PR run 38038626797](https://github.com/SeanOC/stuff/actions/runs/38038626797),
[main run 38019354675](https://github.com/SeanOC/stuff/actions/runs/38019354675),
and [successful run 38016264899](https://github.com/SeanOC/stuff/actions/runs/38016264899),
where export completed in 39s and artifact upload in 2s. The 26m estimate is
provisional: verify the new limit with a complete CI run and a nonempty
`bd123-models` artifact containing STL, GLB, and PNG files. Splitting export
is unnecessary based on these measurements.

After the carve-out is recorded, apply the patch with `git apply`, synchronize
the VLM proposal, and remove this patch and pending section. Run actionlint
on both workflow variants and the required full build123d test suite before
the PR push. Record PR and post-merge main timings; do not merge directly.
