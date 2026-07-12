# Agent Instructions

Issue tracking, build commands, and architecture lives in
[CLAUDE.md](CLAUDE.md). This file covers the model-authoring pipeline
— render thumbnails, per-model invariants — and a couple of shell
conventions that have bitten agents before.

## Listing-page thumbnails (auto-rendered in CI)

The gallery (`/`) pulls tile thumbnails from `renders/<stem>/top.png`,
served by `app/api/thumbnail/route.ts`. Those PNGs are **tracked in
git** so Vercel deploys ship with them — `renders/*/` is intentionally
NOT in `.gitignore`.

The `render` job in `.github/workflows/ci.yml` regenerates them:

- On **push to main**: always runs; commits any diff back via
  `github-actions[bot]`.
- On **pull requests**: runs only when render-relevant paths changed
  (`models/**`, the `scad-render` skill, `.claude/skills/_lib/**`,
  `scripts/render-all.py`, `scripts/vendor-libs.sh`, or
  `libs/README.md`); commits back to the PR branch. The exact filter
  set, the scoped-vs-full render modes, and the engine pin are
  documented in [docs/ci.md](docs/ci.md).

If you edit a model locally and want thumbnails for preview before
pushing, run `python3 scripts/render-all.py` (needs `openscad` +
`xvfb-run` on PATH and `scripts/vendor-libs.sh` already run).
Otherwise, just open the PR and let CI do it.

## Pre-commit gotcha gate

`./scripts/setup-git-hooks.sh` (one-time per clone) installs a
pre-commit hook that blocks the classic model-pipeline mistakes with
feedback naming the exact fix: `.scad` without a catalog entry,
dangling catalog key, missing `.invariants.py` sidecar, and `.scad`
syntax errors (via a fast `openscad` AST parse — skipped with a
notice when the binary isn't installed). Missing `PRINT_ANCHOR_BBOX`
warns but doesn't block. Details + demo transcript:
[docs/dx-precommit.md](docs/dx-precommit.md).

The same hard rules are asserted server-side by
`lib/models/catalog.test.ts`, so `--no-verify` just trades a 1-second
local failure for a CI failure minutes later.

## Per-model invariants (auto-checked in CI)

Every model in `models/` ships with a sidecar
`models/<stem>.invariants.py` that asserts structural claims the model
makes — footprint aspect, clearance margins, single-body topology,
anything that's bitten us before. The driver
`scripts/check-invariants.py <stem>` loads the corresponding
`exports/<stem>.stl`, applies a small set of built-in checks
(watertight, orphan fragments, triangle ceiling, `PRINT_ANCHOR_BBOX`
drift), and then calls the sidecar's `check(ctx)`.

### Adding a model

Start with the `new-model` skill
([.claude/skills/new-model/SKILL.md](.claude/skills/new-model/SKILL.md)):
`python3 scripts/new-model.py <stem> --category <id>` scaffolds the
`.scad`, this sidecar, the sweep test, and the catalog entry in one shot.

Always create a sidecar. Minimum skeleton:

```python
# models/<stem>.invariants.py
from scripts.invariants import Failure, as_default_params, expect_connected_solids

def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    # Example claim — replace with whatever your model actually asserts:
    # if ctx["bbox_mm"][2] > 250:
    #     failures.append(Failure("envelope", "Z > 250mm; won't fit on X1C bed"))
    return failures
```

The sidecar may also call `expect_connected_solids(ctx, n)` to pin
topology (single-body models pass `n=1`; multi-body tray designs
pass the expected count).

### Running locally

```bash
python3 scripts/export-all.py            # openscad → exports/<stem>.stl
python3 scripts/check-invariants-all.py  # runs every sidecar + built-ins
```

Or one model: `python3 scripts/check-invariants.py spraycan_carrier_6x50mm`.

CI runs both steps on every PR that touches `models/**` or the
invariants infra, and on every push to `main`. Failures surface as a
GitHub check.

## Scope discipline: don't silently revert prior-bead work

If your bead's work exposes that a prior bead's change is broken
(fails a test, fails an invariant, fails a manual check), **stop and
file a new bead**. Do not revert the prior change as part of your
current PR. Your commit's stated scope is a contract — if the diff
does more, the commit history lies, bisects are poisoned, and
user-visible regressions look like they came from unrelated work.

Correct path:

1. Finish (or scope down) your current bead's intended change.
2. File a new bead describing what the prior work got wrong and what
   needs doing.
3. Submit your current bead as planned.
4. The new bead picks up in its own PR.

## Non-interactive shell commands

Shell commands like `cp`, `mv`, and `rm` are often aliased to `-i`
(interactive) mode on dev machines, which hangs an automated agent
waiting for y/n input. Prefer the non-interactive forms:

```bash
cp -f source dest        # not: cp source dest
mv -f source dest        # not: mv source dest
rm -f file               # not: rm file
rm -rf directory         # not: rm -r directory

ssh -o BatchMode=yes ... # fail instead of prompting
apt-get -y ...           # auto-confirm
```
