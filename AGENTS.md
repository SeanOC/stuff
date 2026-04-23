# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd prime` for full workflow context.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work atomically
bd close <id>         # Complete work
bd dolt push          # Push beads data to remote
```

## Listing Page Thumbnails (auto-render in CI)

The gallery (`/`) pulls tile thumbnails from `renders/<stem>/top.png`, served
by `app/api/thumbnail/route.ts`. Those PNGs are **tracked in git** so Vercel
deploys ship with them — `renders/*/` is intentionally NOT in `.gitignore`.

The `render` job in `.github/workflows/ci.yml` regenerates them:

- On **push to main**: always runs; commits any diff back via `github-actions[bot]`.
- On **pull requests**: runs only when `models/**`, the scad-render skill,
  `scripts/render-all.{py,sh}`, or `libs/README.md` changed; commits back to
  the PR branch.

If you edit a model locally and want thumbnails for preview before pushing,
run `python3 scripts/render-all.py` (needs `openscad` + `xvfb-run` on PATH and
`scripts/vendor-libs.sh` already run). Otherwise, just open the PR and let CI
do it.

## Per-model invariants (auto-checked in CI)

Every model in `models/` ships with a sidecar `models/<stem>.invariants.py`
that asserts structural claims the model makes — footprint aspect,
clearance margins, single-body topology, anything that's bitten us
before. The driver `scripts/check-invariants.py <stem>` loads the
corresponding `exports/<stem>.stl`, applies a small set of built-in
checks (watertight, orphan fragments, triangle ceiling, `PRINT_ANCHOR_BBOX`
drift) and then calls the sidecar's `check(ctx)`.

### Adding a model

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
invariants infra, and on every push to `main`. Failures are visible
in the GitHub check.

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
