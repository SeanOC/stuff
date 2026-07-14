# Continuous integration

CI lives in four workflows:

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — the
  `render`, `unit`, and `e2e` jobs (pushes to `main` + PRs).
- [`.github/workflows/param-sweep.yml`](../.github/workflows/param-sweep.yml)
  — the wasm param-sweep connectivity guard (pushes to `main` + PRs).
- [`.github/workflows/pr-automerge.yml`](../.github/workflows/pr-automerge.yml)
  — arms squash auto-merge on every PR the moment it opens.
- [`.github/workflows/pr-autoupdate.yml`](../.github/workflows/pr-autoupdate.yml)
  — on every push to `main`, updates all open PR branches so strict
  up-to-date mode can't strand them.

## The PR lifecycle: merges are fully autonomous (pst-2sb)

PRs against `main` run CI and merge entirely on their own — there is
no human or agent merge step:

1. **PR opened** (or reopened / marked ready) → `pr-automerge.yml`
   enables squash auto-merge on it.
2. **Checks run.** All four required contexts report a conclusion on
   *every* PR — that's what makes auto-merge safe to arm blindly:
   - `unit tests (vitest)` and `e2e tests (playwright)` always run.
   - `render preview images` always runs; a paths-filter step inside
     the job skips the heavy render/export work when nothing
     render-relevant changed, but the job still reports success.
   - `wasm param sweep` is a gate job in `param-sweep.yml` that
     reduces the sharded sweep matrix to one stable-named
     conclusion; on sweep-irrelevant PRs the select job's **skip**
     mode makes it pass in seconds.
3. **`main` moves** (another PR merged first) → strict up-to-date
   mode marks the PR out of date → `pr-autoupdate.yml` updates every
   open PR branch via the update-branch API, re-running their checks
   against the new base.
4. **All four checks green + branch up to date** → GitHub merges the
   PR itself (squash).

Consequences worth knowing:

- **The merge cascade is intentional.** With N armed PRs open, each
  merge re-updates the other N−1 and re-runs their CI, so merges
  serialize at roughly one per CI wall-clock. Accepted cost of
  strict mode + autonomy.
- **Token attribution matters.** Auto-merge's eventual merge is
  attributed to whoever *enabled* it, and pushes/merges made with
  `GITHUB_TOKEN` don't trigger workflows. Both new workflows
  therefore authenticate with the `THUMBNAIL_PUSH_TOKEN` PAT (and
  warn on fallback): with `GITHUB_TOKEN` the merge wouldn't fire
  `main`'s full sweep, render canonicalization, or the next
  auto-update round, and branch updates would strand PR runs in
  `action_required` (pst-dm9).
- **update-branch 422s can be transient.** Right after `main` moves,
  GitHub briefly reports PR mergeability as unknown and the
  update-branch API 422s even for genuinely-behind PRs (seen on the
  workflow's first live run, which silently skipped two BEHIND PRs).
  `pr-autoupdate.yml` retries each PR up to 3 times (20s apart),
  treats only the explicit "no new commits on the base branch" answer
  as terminal, and warns if a PR is still not updated — rerun via
  `workflow_dispatch` if one stays BEHIND.
- **Residual gap:** pushes to `main` made *with* `GITHUB_TOKEN` —
  notably the render job's thumbnail canonicalization commit — don't
  fire `pr-autoupdate.yml`. PRs stranded by such a bot-only main
  move get picked up on the next real push, or run the workflow
  manually (`workflow_dispatch`).
- **Fork PRs are excluded**: fork `pull_request` runs get no secrets
  and a read-only `GITHUB_TOKEN`, so arming fails soft and those PRs
  keep the manual merge path.
- **Never make a check required unless it reports on every PR.** A
  required context that sometimes doesn't run (e.g. behind a
  workflow-level `paths:` filter) hangs auto-merge forever. That's
  why neither `ci.yml` nor `param-sweep.yml` path-filters its
  `pull_request` trigger — cheap skipping happens *inside* jobs that
  still report.

Required status checks on `main` (strict mode, set via the branch
protection API): `unit tests (vitest)`, `e2e tests (playwright)`,
`render preview images`, `wasm param sweep`.

## Job / trigger matrix

| Job | Runs on PR | Runs on push to `main` | Where |
| --- | --- | --- | --- |
| `render` (thumbnails + STL export + invariants) | Always reports; heavy steps run only when render-relevant paths changed (see below), full fallback if the filter fails | Always | `ci.yml`, containerized |
| `unit` (vitest) | Always | Always | `ci.yml` |
| `e2e` (Playwright, needs `unit`) | Always | Always | `ci.yml` |
| `sweep` shards (wasm param sweep) | Selective — only the models the PR touched, sharded across parallel jobs (see below); skipped entirely on sweep-irrelevant PRs | Full sweep whenever sweep-relevant paths changed (the coverage guard) | `param-sweep.yml` |
| `gate` (`wasm param sweep`, the required context) | Always reports — reduces shard results to one conclusion, passes immediately in skip mode | Same | `param-sweep.yml` |
| `arm` (enable auto-merge) | On open / reopen / ready-for-review | — | `pr-automerge.yml` |
| `update` (update open PR branches) | — | Always (+ manual dispatch) | `pr-autoupdate.yml` |

The `unit` and `e2e` jobs run on every PR regardless; both are cheap
enough that paths-filtering isn't worth the complexity.

## The render job

### Engine: pinned OpenSCAD 2025.06.12.ai25773 AppImage (st-mb1)

The job runs in the `openscad/openscad:dev.2025-09-06` container, but
**the container's bundled `openscad` is not the engine that renders**.
The container only supplies the runtime environment (EGL + Qt + GL
libs). An install step downloads the `2025.06.12.ai25773` AppImage —
preserved as a release asset on this repo (tag
`openscad-2025.06.12.ai25773`, sha256-pinned in the workflow) because
files.openscad.org's snapshot retention already dropped it — extracts
it (containers have no FUSE), and shadows `/usr/local/bin/openscad`
with it. A version smoke-check right after fails the job if the shadow
didn't take effect.

Why this exact build: the container's own `dev.2025-09-06` engine
exports non-watertight STLs for all five openGrid-snap models that
`2025.06.12.ai25773` (also the local dev pin, st-fgp) exports
watertight from identical sources. Same-engine-everywhere beats
closest-tag roulette.

**Timeout is 40 minutes** — the pinned engine evaluates geometry via
CGAL, much slower than the Manifold default in newer builds. A full
render+export pass over all models takes ~25 min; the old 10-minute
timeout truncated exports mid-run.

### Vendored libraries and local patches

`scripts/vendor-libs.sh` clones BOSL2, QuackWorks, and
gridfinity-rebuilt-openscad at the SHAs pinned in
[`libs/README.md`](../libs/README.md), then applies local patches from
`scripts/patches/<lib>/*.patch` with **`git apply`** (not `patch(1)` —
the CI image ships git but not patch, st-1uw), so patches must be
git-apply-compatible unified diffs. The `.vendor-sha` marker embeds a
fingerprint of the patch set, so editing a patch re-vendors.

### Python deps

Installed via apt (fallback: pip): numpy, pillow, trimesh, **rtree**
(trimesh's ray-query backend, required by `mesh.contains()` in
invariants sidecars — st-3r5), pytest, plus xvfb/xauth for headless
openscad.

### Smart-render: scoped vs full runs (st-mrt / st-a50)

A `dorny/paths-filter` step decides whether the render steps run at
all on PRs, and which models they process. It is
`continue-on-error` — paths-filter's git operations are flaky inside
the container, so a filter **failure falls back to rendering
everything** rather than failing CI (redesign to a non-container
filter job is filed as st-2nv). Render-relevant paths:

- `models/**` — any `.scad` source or invariant sidecar
- `.claude/skills/scad-render/**` — the render skill itself
- `.claude/skills/_lib/**` — shared measurement / export helpers
- `scripts/render-all.py` — the batch render driver
- `scripts/vendor-libs.sh` — the library pin script
- `libs/README.md` — library pins

The filter also emits the changed `models/*.scad` + `libs/**` file
list, passed to `render-all.py` / `export-all.py` as
`--changed-paths` (`CHANGED_PATHS` env var). Three modes result:

1. **Scoped** — filter succeeded and the list is non-empty: only the
   touched models re-render/re-export (a `libs/**` change forces the
   full set).
2. **Full** — `CHANGED_PATHS` is empty: every model renders and
   exports. This happens when the filter step failed (fallback) and on
   pushes to `main` that touched no model/lib paths (the render steps
   run unconditionally on push).
3. **Skipped** — PR touching no render-relevant paths: the render
   steps don't run at all.

**Know which mode you're in** (a "Smart-render mode summary" step
writes it to the workflow summary). The failure class this hides:
`check-invariants-all` only analyzes what `exports/` contains, and in
a fresh CI workspace that's just the models exported *this run*
(`exports/*.stl` is gitignored). In scoped mode, an engine- or
lib-caused watertight regression in *untouched* models is invisible;
it only surfaces on the next full run. That's exactly how the
dev.2025-09-06 engine's non-watertight exports were masked for days
before st-mb1 pinned the engine.

### Invariants

Each model carries a `<stem>.invariants.py` sidecar next to its
`.scad` source. The driver `scripts/check-invariants.py <stem>`:

1. Loads `models/<stem>.scad` and `exports/<stem>.stl` (produced by
   `scripts/export-all.py` earlier in the pipeline).
2. Parses `@param` annotations via a minimal Python port of
   `lib/scad-params/parse.ts`, so CI doesn't need a Node runtime to
   probe model defaults.
3. Computes context: bbox, parsed params, connected-component sizes,
   `PRINT_ANCHOR_BBOX` triple from the `.scad` source if declared.
4. Runs the built-in invariants, then dynamically imports the
   sidecar and calls its `check(ctx) -> list[Failure]`.
5. Exits non-zero with a per-invariant failure report if any
   invariant fails.

Built-in invariants (every model, no opt-in):

- **watertight** — the STL must be a closed manifold
  (`trimesh.is_watertight`). A non-watertight mesh breaks slicer
  compatibility in silent, nasty ways, so this is a hard gate.
- **orphan fragments** — any connected component ≤ 50 triangles is
  flagged. A legitimate multi-body design ships as N sizable
  watertight components and passes; a zero-thickness boolean bug
  typically leaves a tiny scrap next to the main body.
- **triangle ceiling** — ≥ 1,000,000 triangles fails the build.
  Usually means `$fn` crept up or a sweep stepped too finely.
- **anchor bbox drift** — if the `.scad` declares
  `PRINT_ANCHOR_BBOX = [x, y, z]`, the exported STL's bbox extents
  must match within ±1 mm per axis. Catches silent size regressions.

Sidecar conventions, the minimum skeleton, and the scaffold that
generates them live in the `new-model` skill
([.claude/skills/new-model/SKILL.md](../.claude/skills/new-model/SKILL.md))
and [AGENTS.md](../AGENTS.md).

### Commit-back flow

The render PNGs are tracked in git — Vercel's build serves them
directly — so the render job commits regenerated thumbnails back:

- On **push to main**: commit any diff back to `main` as
  `github-actions[bot]`.
- On **pull requests**: commit back to the PR's head branch.

Implementation notes that have each bitten before:

- Both steps are **`continue-on-error`** (st-491): engine renders are
  not bit-deterministic and `main` is protected, so a commit-back
  failure must not take down an otherwise-green run. A proper
  redesign is filed as st-fqc.
- The steps push from a **fresh shallow clone in `/tmp`** (st-qfv):
  the container's workspace mount has no usable `.git`.
- A **tree-hash comparison** (st-tiu) skips the commit when renders
  are byte-identical — `git diff --cached --quiet` false-positives on
  mode/mtime-only changes from `cp -r`.
- On PRs, a **merge-base prune** (pst-dm9,
  [`scripts/prune-canonical-renders.sh`](../scripts/prune-canonical-renders.sh))
  runs before that tree check: any regenerated PNG that byte-matches
  the PR base (`pull_request.base.sha` — main's canonical copy) is
  dropped from the commit. Renders are engine-deterministic but not
  cross-machine-deterministic, so an author's locally rendered PNG for
  an *unchanged* model always differs byte-wise from CI's; without the
  prune, every model PR got a semantically empty bot push that
  cancelled the in-flight param sweep (shared concurrency group) and
  re-triggered `pull_request` runs into `action_required`. Post-merge,
  the push-to-main flavour canonicalizes the bytes anyway. If fetching
  the base SHA fails, the step keeps everything (old behavior). The
  script has a pytest (`scripts/test_prune_canonical_renders.py`; run
  locally — the CI pytest step only covers `scripts/invariants/`).
- When a PR push *is* warranted, it authenticates with the
  **`THUMBNAIL_PUSH_TOKEN`** repo secret (a PAT with `contents:write`)
  so the re-triggered `pull_request` runs execute normally instead of
  stranding in `action_required` (pushes made with `GITHUB_TOKEN`
  don't start normal runs). If the secret is absent the step falls
  back to `GITHUB_TOKEN` and logs a warning — behavior then matches
  the pre-pst-dm9 state.
- `PR_HEAD_REF` is attacker-controllable on forks; it stays in an env
  var and is only ever passed as an argument to `git push` / `git
  clone`, never interpolated into shell text.

## The param-sweep workflow (st-7x7)

`param-sweep.yml` renders every catalog model through the site's real
wasm pipeline at the min/mid/max of every `@param` (plus both booleans
and every enum choice) and asserts each result is a watertight mesh
with the expected number of connected components. It catches param
values that shatter a model in the browser preview — wasm engine CSG
failures that desktop OpenSCAD doesn't reproduce.

It's a separate workflow because it's minutes of wasm rendering. On
pushes to `main` it's path-gated to inputs that can change render
outcomes: `models/**`, `libs/README.md`, `lib/wasm/**`,
`lib/scad-params/**`, `tests/sweep/**`, `vitest.sweep.config.ts`,
`scripts/vendor-libs.sh`, `scripts/select-sweep-tests.py`,
`package-lock.json`, and the workflow file itself. The
`pull_request` trigger deliberately has **no** paths filter
(pst-2sb): `wasm param sweep` is a required status check, and a
required check that never reports hangs auto-merge — so every PR
runs the ~20-second `select` job, and the script's skip mode makes
sweep-irrelevant PRs pass in seconds via the `gate` job instead of
not reporting at all.

### Selective scope + sharding on PRs (pst-776)

A full sweep is ~587 renders and took **~42 minutes** as a single
job — paid on every model PR, for every model in the catalog. Two
changes cut that (before/after timings measured on the pst-776 PR):

1. **Selective scope.** A cheap `select` job feeds the PR's changed
   file list (dorny/paths-filter, fail-soft like ci.yml's) to
   [`scripts/select-sweep-tests.py`](../scripts/select-sweep-tests.py),
   which picks one of three modes:
   - **full** — a sweep-global input changed (`lib/wasm/`,
     `lib/scad-params/`, `libs/`, sweep infra under `tests/sweep/`,
     `vitest.sweep.config.ts`, `scripts/vendor-libs.sh`, the selection
     script, `package-lock.json`, the workflow file), the change list
     is unavailable (push, dispatch, filter failure), **or** a
     non-`.scad` file under `models/` changed (assets like `import()`ed
     STLs can affect any model — widen, don't guess).
   - **selective** — only `models/<stem>.scad` and/or
     `tests/sweep/<stem>.test.ts` files changed: run exactly those
     models' sweeps, plus the coverage meta-guard (which is also what
     fails a PR adding a model without a sweep file).
     Invariants-sidecar-only changes don't count — they're a render-job
     input, not a sweep input.
   - **skip** — nothing sweep-relevant changed: no sweep jobs at all
     (docs-only PRs pay ~20 seconds of `select`, not 40 minutes of
     sweep).
2. **Sharding.** The selected files are split into ≤ 4 cost-balanced
   shards (greedy LPT binning on the measured per-file durations
   hardcoded in the script — case count is a poor time proxy: 25
   `opengrid_bin` cases take ~1000s while 61 `rv_ceiling` cases take
   61s; models without a measurement fall back to an `@param`-count
   estimate) and run as parallel matrix jobs with `fail-fast: false`.
   Hosted runners are 4-vCPU, so extra runners beat extra vitest
   workers (`maxWorkers` stays capped at 4 per job for wasm-heap
   memory). The full-sweep wall clock is floor-bound by the single
   slowest test file (~17 min for `opengrid_bin`) — going lower means
   splitting cases within a file, not more shards. Refresh the
   duration table from a full run's per-file times when balance
   drifts; staleness skews balance, never correctness.

**Coverage guard:** pushes to `main` and `workflow_dispatch` always
run the FULL sweep (empty change list ⇒ full). A selective PR can
therefore never *permanently* mask a param-extreme regression in an
untouched model: it surfaces on the merge commit's full run on
`main`. That mirrors the smart-render trade-off documented above —
scoped PR runs, full canonical runs on `main`. `workflow_dispatch`
doubles as a re-fuzz button: wasm-CGAL failures are randomized, so a
manual full pass has value even on an unchanged tree.

**Injection note:** shard file lists are interpolated into a `run:`
line, so the selection script regex-sanitizes every stem and drops
paths that don't exist in the tree; an unsanitizable path (hostile
filename on a fork PR) degrades to a full sweep, never into the
shell line. The script has a pytest
(`scripts/test_select_sweep_tests.py`; run locally — the CI pytest
step only covers `scripts/invariants/`, widening it is pst-u6t).

### known-failures.ts

[`tests/sweep/known-failures.ts`](../tests/sweep/known-failures.ts)
registers sweep cases that are allowed to fail, each tagged with a
tracking bead. Two classes have used it:

- **Pre-existing param-extreme model bugs** discovered when the guard
  first ran (2026-07-03). These are still registered — currently ~28
  cases across six models, tracked by open beads st-dlu, st-ti3,
  st-38y, st-1us, st-344, st-9hn. The guard gates *new* regressions
  without blocking on this old debt.
- **wasm-CGAL library edge cases** (st-79a class). The opengrid_bin
  entries of this class were removed on 2026-07-10 when the QuackWorks
  click-hole patch fixed the underlying geometry — removing an entry
  **re-arms the case**, so a regression now fails the sweep again.

The contract: don't paper over failures in the *model* — fix those.
Register a case only with a filed bead, and remove the entry when the
bead closes.

## Local reproduction

The exact sequence a contributor runs to match CI:

```bash
# One-time per clone: vendor libraries (also runs as npm prebuild)
bash scripts/vendor-libs.sh

# Render thumbnails (needs openscad + xvfb-run on PATH)
python3 scripts/render-all.py

# Export STLs + run invariants + pytest
python3 scripts/export-all.py
python3 scripts/check-invariants-all.py
python3 -m pytest scripts/invariants/

# Unit + sweep + e2e
npm install
npm test                  # vitest
npm run test:sweep        # wasm param sweep (full; ~40 min)
npm run test:sweep -- tests/sweep/<stem>.test.ts   # sweep one model
npm run build             # prod build (Vercel does the same)
npm run test:e2e          # Playwright
```

For engine parity with CI, use the same pinned snapshot
(`2025.06.12.ai25773`) locally — it's downloadable from this repo's
`openscad-2025.06.12.ai25773` release tag. A different engine build
can disagree with CI about watertightness (that's the whole reason
the pin exists).

`render-all.py` will error early if `openscad` or `xvfb-run` aren't
on `PATH`. On a headless dev host you need both; on macOS with
OpenSCAD.app installed, add the Contents/MacOS directory to `PATH`
and skip xvfb (the render script detects the display).

## Vercel deploy

Pushes to `main` trigger a Vercel production deploy to
[stuff.seanoc.com](https://stuff.seanoc.com). Each PR also gets a
Vercel preview URL, useful for eyeballing UI changes before merge.

Vercel builds pull the committed `renders/<stem>/*.png` directly;
there's no Python in the Vercel build environment, so all
OpenSCAD-touching work happens in GitHub Actions and the outputs
ship as tracked files. `scripts/vendor-libs.sh` runs as the npm
`prebuild` hook so the Vercel build has `libs/` for file tracing and
`/api/source`.

## Troubleshooting

- **`xvfb-run: command not found`** — install `xvfb` (`sudo apt-get
  install xvfb` on Debian/Ubuntu). Required because OpenSCAD needs a
  virtual display even in `-o out.stl` mode.
- **`openscad` not on PATH** — install the pinned snapshot (see Local
  reproduction above) rather than whatever openscad.org currently
  ships; engine drift is a real failure mode here.
- **A model is watertight locally but not in CI (or vice versa)** —
  almost always an engine-version mismatch. Check `openscad
  --version` against the pin before debugging the model.
- **Invariants fail on a model you think is fine** — run the driver
  locally with the single stem:
  `python3 scripts/check-invariants.py <stem>`. The output names the
  specific invariant(s) that failed and the values that failed them.
- **"Why did everything re-render?"** — read the "Smart-render mode
  summary" in the workflow run summary: the paths-filter step failed
  (fallback = full render) or the push touched no model paths
  (`CHANGED_PATHS` empty = full render).
- **Sweep failure on a case listed in known-failures.ts** — the entry
  was removed or the label changed; re-check the tracking bead before
  re-registering.
