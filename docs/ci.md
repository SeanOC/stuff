# Continuous integration

This repo's CI lives in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
and runs on every push to `main` and every pull request.

## Pipeline overview

Three independent jobs on `ubuntu-latest`:

1. **render** — regenerates `renders/<stem>/*.png` thumbnails,
   exports each model to `exports/<stem>.stl`, runs the per-model
   invariants, and executes the invariants-core pytest suite.
2. **unit** — `npm test` (vitest). Parser, discover, hook smoke
   tests, React component tests.
3. **e2e** — `npm run test:e2e` (Playwright against the production
   Next.js build). Requires `unit` to pass first.

The render job is the heaviest — it installs OpenSCAD, xvfb,
trimesh, and a couple of Python stdlib-adjacent packages. The unit
and e2e jobs stay pure Node / npm.

## File-change triggers

The render job is gated by [`dorny/paths-filter`](https://github.com/dorny/paths-filter)
on pull requests (it always runs on pushes to `main`). It only runs
when one of these changes:

- `models/**` — any `.scad` source or invariant sidecar
- `.claude/skills/scad-render/**` — the render skill itself
- `.claude/skills/_lib/**` — shared measurement / export helpers
- `scripts/render-all.py` — the batch render driver
- `scripts/vendor-libs.sh` — the BOSL2 / QuackWorks pin script
- `libs/README.md` — library pins

The `unit` and `e2e` jobs run on every PR regardless; both are cheap
enough that paths-filtering isn't worth the complexity.

## Rendering in detail

`scripts/render-all.py` iterates every `models/*.scad` and delegates
each one to `.claude/skills/scad-render/scripts/render.py` as a
separate subprocess — a single bad file doesn't abort the batch.
Each model produces four PNGs under `renders/<stem>/`:

```
renders/<stem>/top.png
renders/<stem>/front.png
renders/<stem>/side.png
renders/<stem>/iso.png
```

A stale-prune step removes `renders/<stem>/` directories whose
`.scad` source no longer exists, so the committed PNG set mirrors
the current model set exactly.

### Commit-back flow

The PNGs are tracked in git — Vercel's build pulls them directly for
the gallery tiles, so they need to be up to date on `main` at all
times. The render job handles this with a commit-back step:

- On **push to main**: regenerate, commit any diff back to `main`
  as `github-actions[bot]`.
- On **pull requests**: regenerate on the PR branch, commit any
  diff back to the PR's head ref. The next CI run on that PR sees
  the updated thumbnails and re-runs the downstream jobs.

The PR flow uses the head-ref env var carefully (forks can pick
attacker-controllable branch names — keep them out of shell
interpolation; pass through `git push "$PR_HEAD_REF"` only).

## Invariants in detail

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

### Built-in invariants

Apply to every model, no opt-in:

- **watertight** — the STL must be a closed manifold
  (`trimesh.is_watertight`). A non-watertight mesh breaks slicer
  compatibility in silent, nasty ways, so this is a hard gate.
- **orphan fragments** — any connected component ≤ 50 triangles is
  flagged. A legitimate multi-body design (tray + cups, baseplate +
  cradles) ships as N sizable watertight components and passes; a
  zero-thickness boolean bug typically leaves a tiny scrap next to
  the main body, and that's what this catches.
- **triangle ceiling** — ≥ 1,000,000 triangles fails the build.
  Usually means `$fn` crept up or a sweep stepped too finely.
- **anchor bbox drift** — if the `.scad` declares
  `PRINT_ANCHOR_BBOX = [x, y, z]` as a comment-level constant, the
  exported STL's bbox extents must match within ±1 mm per axis.
  Catches silent size regressions.

### Per-model sidecars

Each sidecar asserts claims the model makes beyond the built-ins —
the stuff you'd otherwise only notice when a print fails. Typical
claims include footprint aspect (X ≥ Y when the handle spans X),
clearance margins (apex ≥ can_height + grip-band), and strict
single-body topology for designs that should truly be one solid.

Minimum skeleton for a new model:

```python
# models/<stem>.invariants.py
from scripts.invariants import Failure, as_default_params, expect_connected_solids

def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    # if ctx["bbox_mm"][2] > 250:
    #     failures.append(Failure("envelope", "Z > 250mm; won't fit on X1C bed"))
    # failures.extend(expect_connected_solids(ctx, 1))
    return failures
```

`ctx` also gives you `ctx["stl"]` (a `trimesh.Trimesh`) if you need
mesh-level queries — face areas, volume, specific vertex positions.

## Local reproduction

The exact sequence a contributor runs to match CI:

```bash
# Render thumbnails (needs openscad + xvfb-run on PATH)
python3 scripts/render-all.py

# Export STLs + run invariants + pytest
python3 scripts/export-all.py
python3 scripts/check-invariants-all.py
python3 -m pytest scripts/invariants/

# Unit + e2e
npm install
npm test                  # vitest
npm run build             # prod build (Vercel does the same)
npm run test:e2e          # Playwright
```

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
ship as tracked files.

## Troubleshooting

- **`xvfb-run: command not found`** — install `xvfb` (`sudo apt-get
  install xvfb` on Debian/Ubuntu). Required because OpenSCAD needs a
  virtual display even in `-o out.stl` mode.
- **`openscad` not on PATH** — install from
  [openscad.org](https://openscad.org/). Needs v2021.01 or newer for
  the Manifold backend.
- **CGAL out-of-memory errors** — BOSL2's library is CGAL-hostile on
  large models. Pass `--backend Manifold` to `openscad` (the
  `_lib/export.py` wrapper does this by default).
- **Invariants fail on a model you think is fine** — run the driver
  locally with the single stem:
  `python3 scripts/check-invariants.py <stem>`. The output names the
  specific invariant(s) that failed and the values that failed them.
- **Thumbnails committed back but look the same** — the render
  pipeline is deterministic per OpenSCAD version; a no-op diff
  sometimes slips in when a library update re-meshes identically.
  The commit-back step already skips when `git diff --cached`
  reports nothing, so you won't see spurious commits in practice.
