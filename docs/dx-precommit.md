# Pre-commit gotcha gate

`.githooks/pre-commit` catches this repo's known model-pipeline
gotchas at commit time, with feedback that names the fix instead of
just failing. One-time setup per clone (same script that installs the
commit-trailer hook):

```bash
./scripts/setup-git-hooks.sh
```

## What it checks

Only runs when the staged diff touches `models/` or
`lib/models/catalog.ts`; every other commit pays ~5 ms. All checks
read the **index** (what you're about to commit), not the worktree.

| # | Check | Severity |
| - | ----- | -------- |
| 1 | `models/<stem>.scad` with no `CATALOG` key in `lib/models/catalog.ts` | blocks |
| 2 | `CATALOG` key with no matching `models/<stem>.scad` (dangling entry) | blocks |
| 3 | `models/<stem>.scad` with no `models/<stem>.invariants.py` sidecar | blocks |
| 4 | staged `.scad` missing a `PRINT_ANCHOR_BBOX` assignment | warns |
| 5 | staged `.scad` fails `openscad` AST parse (syntax error) | blocks; skipped with a notice if `openscad` isn't installed |

Check 4 is warn-only because vendored third-party models
(`disney_ear_hanger`) legitimately omit the header. Check 5 uses AST
export, which parses without evaluating: ~0.1 s per file, and
unresolvable `include <BOSL2/...>` lines only warn — so it works even
when `libs/` hasn't been vendored yet.

## Server-side backstop

Bypassing the hook doesn't dodge the checks — it just moves the
failure to CI with a slower feedback loop:

- Checks 1–3 are asserted exactly by `lib/models/catalog.test.ts`
  (vitest, `npm test`, runs in the `unit` CI job).
- Check 5 (and much more) is covered by the CI `render` job, which
  renders and exports every touched model.

The escape hatch exists for emergencies only:

```bash
git commit --no-verify   # discouraged — CI fails instead, minutes later
```

## Demo transcript

Each gotcha exercised with a real `git commit` attempt against a
scratch `models/demo_widget.scad` (output verbatim; demo files never
landed).

### 1. `.scad` staged, no catalog entry

```
$ git commit -m "feat(models): demo widget"   # .scad staged, NO catalog entry

✗ models/demo_widget.scad has no entry in lib/models/catalog.ts.
  Why: listModels() throws on a missing key — vitest goes red AND the
       model silently never appears on the deployed site.
  Fix: add this inside CATALOG (key must equal the filename stem):

  demo_widget: {
    categoryId: "household",  // one of: storage|multiboard|toys|household
    blurb: "One-to-two line card blurb for the gallery tile.",
  },

pre-commit: commit blocked by the failures above.
Bypass with 'git commit --no-verify' only if you must — CI runs the
same checks (lib/models/catalog.test.ts + invariants gate) and will
fail there instead.
(exit 1)
```

### 2. Catalog key with no `.scad` (dangling entry)

```
$ git commit -m "chore: add ghost_model entry"   # catalog key, NO models/ghost_model.scad

✗ CATALOG key "ghost_model" has no models/ghost_model.scad (dangling entry).
  Why: dead entries mislead the next author and mask real parity bugs.
  Fix: delete the "ghost_model" block from lib/models/catalog.ts, or
       restore/rename models/ghost_model.scad to match.
(exit 1)
```

### 3. `.scad` staged, no invariants sidecar

```
$ git commit -m "feat(models): demo widget"   # .scad staged, NO invariants sidecar

✗ models/demo_widget.scad has no models/demo_widget.invariants.py sidecar.
  Why: every model ships one — CI's invariants gate imports it, and
       without it the model's structural claims go unchecked.
  Fix: create models/demo_widget.invariants.py (skeleton in AGENTS.md,
       'Per-model invariants'):

  from scripts.invariants import Failure, as_default_params

  def check(ctx):
      return []  # replace with the claims your model actually makes
(exit 1)
```

### 4. Missing `PRINT_ANCHOR_BBOX` (warning, doesn't block)

```
⚠ models/demo_widget.scad has no PRINT_ANCHOR_BBOX assignment.
  Why: the invariants driver checks exported STL bbox against it;
       without one, bbox drift goes undetected.
  Expected shape (near the top of the file, values at default params):

  // PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at defaults.
  PRINT_ANCHOR_BBOX = [width, depth, height];

  (Warning only — vendored third-party models may omit it.)
```

### 5. Syntax error in a staged `.scad`

```
$ git commit ...   # cube([10, 10 10]); — missing comma

✗ models/demo_widget.scad fails to parse (openscad AST export):
  ERROR: Parser error: syntax error in file .../demo_widget.scad, line 3
  Can't parse file '/tmp/tmp.jg4K6D1VZC/demo_widget.scad'!
  Why: a .scad that doesn't parse breaks CI's render + export jobs.
  Fix: correct the syntax error above and re-stage the file.
(exit 1 — commit blocked)
```

### Fast path

```
$ time ./.githooks/pre-commit    # nothing model-related staged
0.00s user 0.00s system — 0.004 total
```
