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
