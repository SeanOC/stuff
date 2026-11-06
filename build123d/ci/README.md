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

Rebased by pst-bnya8 onto the current three-job workflow (see the marker
contract section below), preserving the capture dependency group and live
timeouts. The step sits in the `fast` job, right after the export it reviews,
and the file is still byte-identical to `.github/workflows/bd123.yml` apart from the header
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

# Trusted reference-mirror measurement (pst-m9k6) — ACTIVE

`.github/workflows/reference-measure.yml` (activated by the mayor 2026-10-20;
staged here first because the worker policy forbids editing `.github/workflows/`)
pulls the private upstream reference mirror (see `build123d/reference/FETCH.md`)
and runs the `upstream`-marked tests. Triggers: push to `main` touching
`build123d/{reference,tools,multibuild,tests}/**`, `pyproject.toml`, `uv.lock`,
or the workflow itself; and `workflow_dispatch`. Never on `pull_request`: the
reader SA's WIF binding is pinned to `repo:SeanOC/stuff:ref:refs/heads/main`,
and PR CI (`bd123.yml`) stays offline (`pyproject` addopts deselect `upstream`).

Prerequisites (mayor, 2026-09-29): repo variables `GCP_WIF_PROVIDER` and
`GCP_REFERENCE_READER_SA`, and the read-only SA's WIF binding above. To run
the three tests locally, from `build123d/` with bucket access as described in
[`reference/FETCH.md`](../reference/FETCH.md):

```bash
uv run tools/reference_pull.py && uv run pytest tests/ -q -m upstream
```

The workflow pulls every source in `source-manifest.json` (214 at the time of
writing), verifies its SHA256, then runs these 13 upstream cases:

- `test_reference_upstream.py::test_every_manifest_source_is_present_and_verified`
  checks that every manifest source is present and verified (1 case).
- `test_fixpoint.py::test_rebuild_equals_original` compares our Fix-Point
  slot/head with the original MultiBuild STEP (2 cases).
- `test_reference_provenance.py::test_artifacts_regenerate` rebuilds the
  committed `reference/measured/` JSON/SVG from the mirror (10 cases).

The [first activated run](https://github.com/SeanOC/stuff/actions/runs/39364677323)
verified all 214 sources and passed all 221 then-selected upstream cases.
The 207 per-source 30-second timing cases have since been removed: shared
runner wall-clock timing is not a reliable correctness check. A future
performance guard should use the existing serial `budget` pattern.

QuackWorks snap constants are checked in the ordinary offline suite against
[`reference/opengrid-snap-constants.json`](../reference/opengrid-snap-constants.json).
This table freezes 60 scalar values keyed by port constant name, each with its
pinned source locator; it stores no source text or SCAD argument identifiers.
It is deliberately unmanifested and outside `reference/measured/`, whose
artifacts follow the `measure_step/1` geometry command contract and source
manifest (which has no SCAD records). The former live-fetch test and its
FRONT/REAR argument-binding checks are removed; exact values, locators and
the complete key set are checked offline instead.

The mayor/operator runs the generator only for an explicit reference refresh,
from the repo root (it is not part of tests or CI):

```bash
uv run --project build123d python scripts/freeze-opengrid-snap-constants.py
```

The generator reads pinned commit `6123129` into memory, extracts numeric
literals by line/token position independently of the port constants, and
writes only measurements and provenance metadata, including the source hash.
Review and commit the resulting JSON; never commit fetched QuackWorks text.

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

# Staged CI change — change-scoped fast/audit selection (pst-3bga4)

`bd123.scoped.yml.proposed` is a FULL replacement for
`.github/workflows/bd123.yml`. It is not named `bd123.yml.proposed` because that
file is still the unactivated pst-ae3v proposal above, and the two activate
independently. Against the live workflow it changes:

- **`changes`** (`detect model/audit changes`, still pull_request only) gains a
  checkout, `uv sync --frozen` and `working-directory: build123d` (it had
  none), lists the PR's files (`list-files: shell`, an `any` filter) and runs
  `scripts/select-bd-tests.py`, which writes `mode` (`full|scoped|skip`) and
  `k_expr` to `$GITHUB_OUTPUT`. Timeout 5 → 10 min for the sync.
- **`fast`** and **`audit`** `needs: changes`. `mode=skip` skips them (a skipped
  check does not block a merge). `mode=scoped` appends `-k "$K_EXPR"` to the
  fast tests, the serial budget step and the audit step. `K_EXPR` comes in
  through `env`. On push to `main`, on schedule, or when `changes` fails, the
  outputs are empty and both jobs run in full (`!cancelled()`).
- **cradle filter**: only the `build123d/holders/**` entry is replaced. It now
  lists the five holder modules whose `audit_full` cases the sweep runs
  (spool_cradle, cartridge_holder, openconnect_drawer, gridfinity_capture_bin,
  tombstone_sign), the holders modules they import (label_card, sign_ghost,
  signs), and `registry.py` + `printer.py`. All five import the registry, and
  `tombstone_sign` sizes against the `printer.py` bed. Every other entry is
  the live filter's, `labels/**` and `test_honeycomb.py` included (the latter
  carries no `audit_full` case; it is a defensive sibling of the drawer
  entries). `tests/test_ci_filters.py` holds both this file and the live
  workflow to the rule that every `audit_full` carrier and its `tests/`
  helpers are listed.

Job names are unchanged. `audit_full` and its gate are unchanged.

## What the selector scopes

`full` when a shared input changed: `holders/printer.py`,
`holders/registry.py`, `labels/**`, `multibuild/**`, `openconnect/**`,
`scripts/manifest.py`, `tests/{print_audit,audit_cache,mount_contracts,conftest}.py`,
`pyproject.toml`, `uv.lock`, the selector itself or the workflow. Any path it
cannot attribute is also `full`: holders helpers that register no model,
`drawer/`, `gridfinity/`, `underware/`, other `scripts/`, `README.md`. So is a
change that affects no model module (`manifest.json`, `tests/baselines/**`
or a non-model test file alone): there is nothing to scope to, and the
`budget` tier, whose ids name only models, would collect nothing and exit 5.
`scoped` when at least one model module is affected and every change is a
registered model module, its `tests/test_<stem>.py` (counts as that module's
change), another `tests/test_*.py`, `manifest.json` (→ `test_manifest`),
`tests/baselines/**` (→ the two baseline tests), a section golden
`docs/renders/sections/<slug>.svg` (→ that model), or a doc or test data file
named only by tests or model modules. `skip` when only
`ci/`, `tests/.test_durations`, render PNGs or docs nothing names changed.

The scoped `-k` is `(<mine>) or not (<others>)`. `<mine>` lists every registry
name and slug of each affected model module, its `test_<stem>`, and every
changed test file's stem. Module → models is 1:N: `smoke` and `cylindrical`
register 2 each, `underware_path_channels` 2 and `underware_junctions` 3. A
module is affected when it changed or when it, or its tests, import an
affected model module (`bench_width_saddle` and `bench_projector_mount` import
`bench_lip_clip`).
`<others>` lists the same terms for every unaffected module. The selection
drops only the tests of UNCHANGED models. Tests whose ids name no model always
run: the geometry baseline, presets bake, audit-cache determinism,
manifest/registry contracts and library tests. A plain `-k "(<mine>)"` would
drop them, and every geometry PR must update the geometry baseline. On the
model-scoped files of #247 (bench_lip_clip + its test, docs, manifest), the
audit tier collects 133 of 606 items. That includes all 34 of
`test_bench_lip_clip.py`, the dependent `test_bench_width_saddle.py`, and
`test_print_audit`'s two rows. The single `test_geometry_baseline` item
(~700 s on CI) bounds that job's wall time. The fast tier collects 948 of
1939. Library tests that import no model are kept, because they cannot be
told apart from registry-wide tests by name. The real #247 also touched
`registry.py`, so it would still be `full`. Known gap, in principle: a test in
an UNCHANGED model's file that checks the changed model without naming it in
its id is dropped with that file. The #249 review scanned all 20 model modules
in both tiers and found no instance (cross-model loops parametrize by model
name, so `<mine>` keeps them). The full main and nightly runs would catch one.

`tests/test_select_bd_tests.py` runs in fast. It checks a path table → mode and
`<mine>`, and runs `pytest --collect-only` in a subprocess (~2 s each, not a
hang) to check the selected file set for #247's files, and that every tier
(fast, budget, audit) collects at least one item for a scoped selection.

## Activate (mayor, on a PR branch)

```bash
gh api repos/:owner/:repo/branches/main/protection/required_status_checks/contexts > /tmp/ctx-before.json
uvx --from actionlint-py==1.7.12.25 actionlint build123d/ci/bd123.scoped.yml.proposed
#   two findings, both pre-existing on main: matrix.group in the non-matrix audit job's cache key
git mv build123d/ci/bd123.scoped.yml.proposed .github/workflows/bd123.yml   # git mv -f: the target exists
# delete the PROPOSED header block (the first 9 lines) from the moved file
git commit -m "ops(bd123): activate change-scoped fast/audit selection (pst-3bga4)"
```

That PR changes the workflow file, so its own run is `full`. Test `scoped` and
`skip` on throwaway PRs (one model module edit; a `build123d/ci/` edit), then
check the `Decide fast/audit scope` step summary. After merge:

```bash
gh api repos/:owner/:repo/branches/main/protection/required_status_checks/contexts > /tmp/ctx-after.json
diff /tmp/ctx-before.json /tmp/ctx-after.json   # must be empty: job names are unchanged
```

If the pst-ae3v proposal is activated later, rebase its one ADDED step onto
the then-live file. Do not copy it over this one.

# bd123 jobs and the marker contract

The live `.github/workflows/bd123.yml` partitions tests with pytest markers:

| Tier | Expression (also excludes `upstream`) | When |
| --- | --- | --- |
| fast | `not audit and not budget` | scoped PRs, main, schedule |
| budget | `budget` (serial step in fast) | scoped PRs, main, schedule |
| audit | `audit and not audit_full` | scoped PRs, main, schedule |
| audit_full | `audit_full`, six pytest-split shards | main and schedule |

## PR audit tier

`tests/audit_tiers.py` classifies existing rows once: a preset, the defaults, or one
numeric parameter at its declared min/max with all other values at defaults
belongs in the PR tier. Compare resolved values, so an explicitly spelled-out
default does not turn an endpoint into a corner. Hardware-mode combinations,
interior values, corners, reproducers and other expensive checks run in the
full sweep. Existing test bodies, assertions and node IDs are retained. Missing
endpoint rows are not synthesized, and explicit-rejection guard tests stay in
the fast tier unchanged.

Generators expose their model and values using `@audit_cases(spec, resolver)`.
The resolver reads pytest parameter data, never builds geometry. The collection
hook classifies items **before** marker deselection and shard selection. This
also promotes previously full-only presets into the PR tier. Registry defaults
and the bed-fit checks use `audit_pr`. Every other `audit` item receives
`audit_full`; unknown new cases therefore remain covered on main and schedule.
An `audit_full` item without `audit`, or an audit marked `budget`, fails collection.

The old `cradle` path filter is removed: more full-tier test carriers cannot
accidentally bring the full sweep back onto model PRs. The audit job uses the
existing changed-model `k_expr` for print audits,
while `test_registry_presets_fit_bed` checks every registered preset (and
defaults for models without presets) even when its model is unchanged. All
expressions exclude `upstream` because
a command-line `-m` replaces pytest addopts. The full sweep's six shards use
`tests/.test_durations`; durations were refreshed from the 1,227 successful
outcome rows in main run 42076796470. Main and schedule retain every old audit
item across the two disjoint tiers. `tests/test_audit_tiers.py` checks their
union and representative routing, including large tile corners and presets
that used to run only in the full sweep. `tests/test_ci_filters.py` pins the
live workflow routing and artifact contract. Historical `.proposed` workflows
must be rebased before activation; copying their old cradle filter is unsafe.

The audit job's **35-minute cap** is based on four successful main runs:

| Run | Old audit job elapsed | Replayed PR selection, four workers |
| --- | ---: | ---: |
| 42076796470 | 56.5 min | 17.9 min |
| 42001797960 | 39.6 min | 18.4 min |
| 41806835769 | 66.6 min | 22.1 min |
| 41692429964 | 44.6 min | 18.7 min |

These estimates replay the final **572-item** PR tier by assigning each
selected item's recorded `outcome.duration_s` to the earliest available of four
workers in collection order. The latest CI run supplies all 466 existing
selected audit durations. For each older run, use its 454 recorded rows and
fill the 12 subsequently added rows from the latest run. Add the 106 bed-check
durations from the local combined run below (264.1 task-seconds in total).
These are estimates, not observed full CI runs of this PR: bed timings are
local, and xdist batching, cache state, setup and contention can differ.
The slowest estimate times 1.5 is 33.2 minutes, rounded to **35**. Audit sharding
is separate work.

The local combined saddle/bed run used the production PR marker expression,
`-n 4` and `-k 'bench_width_saddle or test_registry_presets_fit_bed'`:
**130 passed in 84.74 seconds** (24 existing saddle audits: 23 preset/endpoint
rows plus its registry default; and 106 bed checks). Four module-level skips
are unrelated optional dependencies. This used the existing cache while the
required full suite was also running. The standalone bed gate passed all 106
items in 86.16 seconds. Main/schedule now collect **1,333** audit-marked items:
all 1,227 original IDs plus 106 lightweight bed checks, partitioned into 572 PR
and 761 full-tier items. No new print-audit or guard cases were added.
Geometry, print thresholds and exception inventories are unchanged.

PRs still upload **`bd123-audit-rows`**. Main/schedule additionally upload
`bd123-audit-rows-1` through `-6`. The download and reading recipe below is
unchanged; inspect session marker expressions to identify each tier. A PR
artifact is evidence only for its selected items, not for the full matrix.

To refresh the shard balance, each nightly shard re-measures its own tests and
uploads them as `bd123-test-durations-<group>` (1–6), the file
`build123d/tests/.test_durations`. The step sets `include-hidden-files: true`:
`actions/upload-artifact@v4` skips dotfiles by default (v4.4.0+), so before
pst-mv1b9 it found nothing and only warned. It also sets
`if-no-files-found: error`, so a shard that dies before pytest-split writes
durations shows a second red X on the upload. That's the fix working, not a
new failure. Each artifact is PARTIAL (`--clean-durations` keeps only that
shard's tests), so merge all six. From the repo root:

```bash
run=$(gh run list --workflow bd123 --event schedule --status success \
  --limit 1 --json databaseId -q '.[0].databaseId')
gh run download "$run" -p 'bd123-test-durations-*' -D /tmp/durations
jq -s add /tmp/durations/bd123-test-durations-*/.test_durations \
  > build123d/tests/.test_durations
jq length build123d/tests/.test_durations   # >= the committed key count
```

Commit the file with the run id in the PR body. If no recent nightly is
green, refresh by a LOCAL measurement on a named `main` SHA, from
`build123d/`:

```bash
uv run pytest tests/ -q -n 4 --dist load -m "audit_full and not upstream" \
  --store-durations --clean-durations --durations-path tests/.test_durations
```

Then check that every `audit_full` id has an entry, and commit the file with the
SHA and command in the PR body. A stale or missing entry only skews shard
balance, never coverage. pst-2z9ng measured all 193 cases on `a84da775`.

# Audit rows artefact (pst-rir4i)

The `-q` job log swallows the per-case `AUDIT |` / `AUDIT_ROW |` / `BED EXTENT`
print lines on a pass. So the **audit** and **audit_full** jobs set
`BD_AUDIT_OUT=out/audit/rows.jsonl`, and each job uploads `build123d/out/audit/`
(14 days; `if: always()`, so red runs upload too). Download it instead of
re-running a sweep. The audit job's artefact is `bd123-audit-rows` and each
shard's is `bd123-audit-rows-<group>` (1–6):

```bash
gh run download <run-id> -n bd123-audit-rows -D rows/audit
gh run download <run-id> -p 'bd123-audit-rows-*' -D rows/full   # sweep shards, if they ran
```

Once pst-3bga4's scoped selection is active, a PR run's `bd123-audit-rows`
covers the selected models only (`Decide fast/audit scope` in the
`detect model/audit changes` job prints the `-k`). A missing row there means the
model was not selected, not that a measurement regressed. Main and nightly runs
are always full.

## Upstream bump: numerical baselines (pst-6dhmb)

This is the baseline/tolerance hand-off from
[`docs/bake-repeatability.md` §6](../docs/bake-repeatability.md).
There is **one in-CI gate**, the BREP geometry test. It builds every non-smoke
registry preset (the 65 app presets in the initial manifest), records volume,
face/solid counts, raw and print-frame bounds, print-frame centre, and
containment at all 125 combinations of normalized 0.1/0.3/0.5/0.7/0.9
bounding-box coordinates. It never re-runs a bake.

Run the other comparisons **offline**, from `build123d/`, after the selected
CI jobs finish. Use fresh, empty directories for each run:

```bash
gh run download <run-id> -p 'bd123-audit-rows*' -D ../.tmp-upgrade/rows
uv run python scripts/compare_audit_rows.py ../.tmp-upgrade/rows
uv run python scripts/export.py --presets-only ../.tmp-upgrade/bake
uv run python scripts/compare_bake.py ../.tmp-upgrade/bake
uv run python scripts/geometry_baseline.py
```

**Do not use `bd123-models` as the bake input.** That artifact contains models
at defaults (including smoke), not the app-preset bake with its 3MF outputs.
`compare_bake` compares the complete file inventory, welded STL metrics,
GLB scene/material/accessor/transform structure, and 3MF mesh metrics,
build items, components, material assignments and printer-profile settings.
GLB primitives are grouped per mesh by material/mode/attribute schema, with
exact primitive counts, accessor-count inventories and aggregate bounds; the
baseline does not pin per-face primitive/accessor ordering or per-face bounds.
PNG signature/dimensions are checked; pixels and GLB binary attributes are
outside this numerical comparison. Byte ordering, buffer packing and ZIP
timestamps are not semantic differences. The STL classification column uses
the existing raw oriented-triangle/vertex diagnostic from
`scripts/bake_repeatability.py`; it does **not** use the welded copy to infer
coordinate identity. A changed connectivity/coordinate diagnostic still needs
surface review even if the numerical comparator passes: equal volume and
counts do not prove equivalent surfaces. See the repeatability contract.

All three tools use **only** `scripts/baseline_common.py:TOLERANCES`:

| Fields | Mode | Tolerance |
| --- | --- | --- |
| BREP volume | relative to baseline | 1e-6 |
| Bounds, centres and other geometry/bake floating measurements | absolute, native units (mm for BREP/STL/3MF; glTF units for GLB) | 1e-6 |
| Baked STL/3MF volume and audit floating measurements (including volumes) | absolute, native units (the spike join) | 1e-6 |
| Counts/inventories, containment, booleans, strings and types | exact | 0 |

Baselines have sorted keys and floats formatted to nine decimal places.
Diffs name the preset/file or `(nodeid, name)`, the field's JSON pointer,
old/new values and tolerance mode. Exit **0** is a numerical/structural pass,
**1** is a difference or invalid input. Audit exit **2**, **NOT COMPARABLE**,
means a declared job/shard never supplied a session: e.g. an upstream PR
without the conditional `audit_full` job. The audit baseline header declares
the exact marker expressions and shard groups (initially audit plus all six
full-sweep shards), source run and SHA. Extra jobs outside that scope are
ignored. Within scope, a missing measurement row fails unless explicitly
waived; duplicate rows and malformed sessions fail. Sessions are read from
every `rows*.jsonl`, regardless of directory names or worker assignment.
The numerical baseline joins **measurement** rows by `(nodeid, name)`, matching
the spike. Collection/outcome rows validate capture completeness and reject
failed tests; adding infrastructure tests (such as the BREP gate itself)
does not add numerical rows. An incomplete/failed capture is invalid input,
not a waivable measurement difference. Times/durations are excluded; shard
balancing may move tests without changing the globally joined measurements.

The initial geometry/bake source is main `0e749904`, after the 0.13 migration
PR #231's **merge** `8d17fbe504bb8010ed9acaf26d67fe358338ca7d` (its branch head
`456e3e0c` is not a main ancestor). Initial audit rows come from successful
run `39403041801` at `b38d60c5`; the intervening #238 is documentation and the
bake diagnostic, with no model/audit change.

### Deliberate re-baselining and waivers

One command regenerates **all three** committed files, using fresh local
BREPs, a fresh production presets-only bake, and a completed downloaded audit
capture. It refuses an empty reason/provenance, an incomplete outcome capture,
failed outcomes, or registry/manifest preset drift:

```bash
uv run python scripts/rebaseline.py \
  --audit-rows ../.tmp-upgrade/rows \
  --audit-source 'GitHub bd123 run <run-id> at <source-sha>; audit + full shards 1-6' \
  --why 'pst-xxxxx: deliberate old -> new kernel baseline; reviewed changes ...'
git diff -- tests/baselines/
```

`--why`, source SHA, engine versions and preset scope are written into every
baseline header; audit provenance/scope are additionally written in the rows
header. All three measurements complete before any baseline is replaced.
Commit the generated JSON, inspect the numerical/structural changes and explain
them in the PR. A re-baseline is deliberate acceptance, never a silent fallback.

For an approved audit-only change confined to one test file, capture that
file's complete audit selection in a fresh directory, then refresh its existing
measurement rows without rebuilding geometry or bake artifacts:

```bash
BD_AUDIT_OUT=../.tmp-shelf-rows/rows.jsonl uv run pytest \
  tests/test_gridfinity_shelf.py -q -m 'audit and not upstream'
uv run python scripts/rebaseline.py \
  --audit-test-file tests/test_gridfinity_shelf.py \
  --audit-rows ../.tmp-shelf-rows \
  --audit-source 'local completed shelf audit capture at <source-sha>' \
  --why 'pst-0q595: mayor-approved exception #2 enlargement, PR #281'
```

This mode requires successful, complete outcomes and exactly the baseline's
existing measurement keys for that test file. Missing or extra rows fail before
writing. Other rows and the original full-job provenance remain intact; a
`scoped_updates` header records the new reason, source SHA, engine versions,
capture provenance and selection. It cannot be combined with `--geometry-only`.

Fields or entire rows may be waived **only** in the committed
`tests/baselines/waivers.json`. Each entry requires `kind` (`geometry`, `bake`,
`audit-rows`), an exact JSON-pointer `path` copied from the diff, a `reason`
and a `bead` id; no wildcard paths. For example, a row named `holder/foo`
has pointer `/holder~1foo`. A field waiver adds `/volume`. Waived paths are
reported explicitly. The mayor proposes, the PR body names every waiver, and
**Sean's merge is the approval**. The initial waiver list is empty.

To read the CI timing after a run completes:

```bash
python3 - ../.tmp-upgrade/rows <<'PY'
import json, sys
from pathlib import Path
for path in Path(sys.argv[1]).rglob('rows*.jsonl'):
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row.get('kind') == 'outcome' and 'test_app_preset_geometry_baseline' in row['nodeid']:
            print(row['nodeid'], row['outcome'], row['duration_s'], 'seconds')
PY
```

### Audit row schema and inspection

Each process writes its own file: `rows.jsonl` for the pytest controller, which
holds just its `session` row, and `rows.gw0.jsonl`…`rows.gw3.jsonl` for the
xdist workers. **Always glob `rows*.jsonl`.** Every line is JSON with a `kind`:

- `session`: `markexpr`, `group` (the pytest-split `--group`; null in the audit
  job) and `started_at`, one per process.
- `collection`: `collected` (this job's or shard's selected items) and `audited`
  (how many of them carry `audit`/`audit_full`, which is the number of outcome
  rows owed). Every xdist worker collects the whole selection, so each worker
  file has one and they agree.
- `outcome`: one per `audit`/`audit_full` item, written by the
  `tests/conftest.py` hook. Fields are `nodeid`, `when`, `outcome`
  (`passed`/`failed`/`skipped`; an xfail is `skipped` with `xfail: true`),
  `duration_s`, `group` and `started_at`. The row is the call phase, or the
  setup phase when setup stopped the item. A failing teardown adds a second
  row with `when: "teardown"`.
- `measurement`: written by `tests.audit_record.record(name, **fields)` beside
  each per-case measurement print. Fields are `nodeid`, `name` and `fields`,
  and the `fields` keys follow that print line's own labels. A named-error case
  records its error text (`named_error` / `rejected`). The two parity tests
  record one row per case, with both directions under `fields.directions`. A
  case that fails an assert before its print line has an `outcome` row but no
  `measurement` row.

Point this at ONE job's directory. It prints the 10 slowest cases, every row for
one case or preset (a substring of the nodeid), the counts, and, per test
function that records measurements, its outcome rows against its measurement
rows. Those two must be equal in a green run:

```bash
python3 - rows/audit 'standard' <<'PY'
import json, sys
from collections import Counter
from pathlib import Path
rows = [json.loads(l) for f in sorted(Path(sys.argv[1]).rglob('rows*.jsonl'))
        for l in f.read_text(encoding='utf-8').splitlines()]
out = [r for r in rows if r['kind'] == 'outcome']
meas = [r for r in rows if r['kind'] == 'measurement']
for r in sorted(out, key=lambda r: -r['duration_s'])[:10]:
    print(f"{r['duration_s']:8.1f} s  {r['outcome']:7}  {r['nodeid']}")
for r in out + meas:
    if sys.argv[2] in r['nodeid']:
        print(json.dumps(r))
col = next(r for r in rows if r['kind'] == 'collection')
print(sum(r['when'] != 'teardown' for r in out), 'outcome rows for', col['audited'], 'audited of',
      col['collected'], 'collected;', len(meas), 'measurement rows;',
      sum(r['outcome'] != 'passed' for r in out), 'not passed')
fn = lambda r: r['nodeid'].split('[')[0]
m = Counter(map(fn, meas))
o = Counter(fn(r) for r in out if r['when'] != 'teardown' and fn(r) in m)
for f in sorted(m):
    print(f"{o[f]:4} outcome {m[f]:4} measurement  {'ok' if o[f] == m[f] else 'MISMATCH'}  {f}")
PY
```

The `outcome` rows (excluding `when: "teardown"`) must equal `collection.audited`,
and in the audit jobs that equals `collected`. The `-q` log prints no item
count. Its summary's `4 skipped` are the whole-module skips of
`tests/test_capture_*.py`, which have no items. Count per artefact directory,
never summed across jobs. One test function can split across the audit job and the shards
(the drawer endpoint test, per-param marks). Rows are written only when
`BD_AUDIT_OUT` is set, so local runs write nothing. A write failure is an
`AuditRecordWarning`, never a failed test.
