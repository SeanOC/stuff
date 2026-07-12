# Gas City v1.3.4 pilot — stuff rig (st-qr2, July 2026)

Operator-approved pilot evaluating migration from Gas Town to Gas City
(github.com/gastownhall/gascity) using the stuff rig as the workload.
Everything below was measured on a live Gas City 1.3.4 city standing in
`~/gc-pilot` (outside `~/gt`), driving the real `SeanOC/stuff` GitHub
repo through PRs and its existing CI gates.

**Status: PILOT IN PROGRESS — this revision carries setup + partial
probe results. Sections marked ⏳ are pending.**

## TL;DR / recommendation

⏳ (final go/no-go written after both seeded beads land through the merge
step — see Probe results.)

Interim shape: Gas City's primitive-first model maps cleanly onto what
this repo needs (one on-demand worker pool, PR-only merge step, human
escalation mailbox — total custom pack: 2 small TOML files, 1 prompt, 2
shell scripts). The dangerous direct-push machinery of Gas Town exists in
Gas City only as one opt-in formula we simply don't use. The file beads
provider is NOT usable beyond demos (ID double-allocation observed); the
default managed-Dolt provider isolated itself correctly from production.

## Pilot setup log

| Step | Result |
| --- | --- |
| Source | `gastownhall/gascity` tag v1.3.4 (2026-07-10), shallow clone |
| Build | `go build ./cmd/gc` with go 1.26.2 — clean, ~1 min |
| Workspace | `gc init --template minimal --default-provider claude --no-start ~/gc-pilot/city` |
| Rig | fresh clone of `SeanOC/stuff` at `~/gc-pilot/rig-stuff` (main = `bc7c051`), `gc rig add --name stuff --prefix pst` |
| Store (attempt 1) | `GC_BEADS=file` — **abandoned, see file-provider findings** |
| Store (attempt 2) | default bd/Dolt provider — GC started its own `dolt sql-server` on port **26092**, `data_dir=~/gc-pilot/city/.beads/dolt`. Production Dolt (3307, `~/gt/.dolt-data`) never touched. |
| Supervisor | `gc start` installs a **user systemd unit** `gascity-supervisor.service` (machine-wide supervisor; reversible, but worth knowing it outlives the shell) |
| Doctor | 75 checks pass on file backend; on bd backend the `custom-types` warnings persist even after `gc doctor --fix` (cosmetic) |

Dependency floors that matter to us: dolt ≥ 2.1.0 for the bd provider
(host has 2.1.10; the GT production server still runs 1.86.5 — a
managed-Dolt migration implies a Dolt upgrade), bd ≥ 1.0.0, and GC's
`bd_compatibility` config **defaults to `bd-1.0.4`** — exactly our pin,
deliberately avoiding withdrawn 1.0.5 semantics.

## The custom pack (committed under `pilot/gascity-pack/`)

Per the coming-from-gastown guide, intent re-expressed in primitives — no
Gas Town replica pack:

- `agents/worker/agent.toml` — one rig-scoped pool, `min_active_sessions
  = 0`, `max_active_sessions = 2`, claude provider, per-session git
  worktrees under `.gc/worktrees/` created by a `pre_start` script.
- `agents/worker/prompt.template.md` — claim → branch `gc-pilot/<bead>`
  from `origin/main` → fix → quality gates → **PR only**; explicit
  prohibitions on pushing main. Escalation to the built-in reserved
  `human` mailbox (`gc mail send human …`).
- `orders/merge-green-prs.toml` + `assets/scripts/merge-green-prs.sh` —
  the merge step as an **exec order** (controller-side, no LLM):
  every 3 min, merge `gc-pilot/*`-headed PRs into main iff
  `gh pr checks` reports all green. Squash merge, never `--admin`,
  non-pilot PRs untouched.

Roles census vs Gas Town: no deacon (controller health patrol), no
witness (event bus + session beads), no refinery (exec order), mayor
optional (the minimal template ships one always-on mayor session).

## Probe (a): bypass / direct-push audit

**Monitoring**: `git ls-remote` poll of every `refs/heads/*` on
`SeanOC/stuff` every 60 s for the whole pilot, cross-checking any main
movement against merged PRs (`monitor-main.sh`). Baseline `bc7c051`.

**Result so far**: ⏳ origin main has not moved except via the pilot's
own PR merges (final tally at pilot end).

**Source/config audit — every git-push-capable path in GC v1.3.4:**

| Path | What | Risk for us |
| --- | --- | --- |
| `core` pack formula `mol-polecat-commit`, terminal step | `git push origin HEAD:{{base_branch}}` with 3-attempt retry — direct commit to main, no PR. Self-described "for small installations where merge review is unnecessary". | The gt-pvx class lives HERE, but it is **opt-in**: only runs if you sling that formula or set it as an agent's `default_sling_formula`. Pilot pack never references it. Recommend a lint/policy ban in any real deployment. |
| `core` pack order `jsonl-export` (15 min cooldown) | `git push origin main` — but against a **separate bead-archive repo** (`.gc/runtime/packs/core/jsonl-archive`), and only if that archive has an `origin` remote configured (default: none → local-only). | Cannot touch the code repo unless someone points the archive's origin at it. Disable outright with `[orders] skip = ["jsonl-export"]`. |
| k8s runtime pod env | injects `GITHUB_TOKEN` from an optional `git-credentials` secret (capability, not an action) | k8s-only; secret absent → no credential. |
| **`gc rig add` (observed live)** | silently created commit `8c15300 "bd init: initialize beads issue tracking"` **on the rig's local main** (+4 lines to `.gitignore`), authored as the agent, no prompt or flag. Not pushed — but local main now diverges from origin, and any later direct push would carry it. | This is the sharpest finding: repo-mutating side effects from an infra command. Mitigations: workers must branch from `origin/main` (our prompt does); merge step is PR-only; keep rig clones disposable. |

No auto-save/checkpoint/auto-commit push mechanism exists in the source
beyond the above (grepped `internal/` + `cmd/` for push/autosave/
checkpoint; the "checkpoint" hits are formula-recovery DB rows, and the
PreCompact handoff hook writes a bead, not a git object).

**End-to-end result**: ⏳ (both beads through the PR merge step; final
`ls-remote` diff vs PR-merge SHAs.)

## Probe (b): lifecycle — PASS

Planned test, executed live at 13:56 local: with **both** pool sessions
mid-task on separate beads (worker-1 had uncommitted model edits on
branch `gc-pilot/pst-4tv`; diff sha256 recorded), ran
`gc session kill stuff/worker-1`.

- **No cross-session kill**: worker-2 stayed `active` and kept working;
  mayor unaffected. (The hq-m95y class did not reproduce.)
- **No worktree interference**: worker-1's uncommitted diff hashed
  bit-identical after the kill; branch untouched.
- **Work preserved end-to-end**: the reconciler restarted worker-1
  **86 s** later (same session bead, `claude --resume`), and it picked
  up where it left off in the same worktree.

Unplanned bonus datum: earlier, both sessions failed creation due to
stale `git worktree` registrations left by a torn-down city
(`worktree-setup.sh` lacks a `git worktree prune` guard); health patrol
retried with backoff and recovered once registrations were pruned.

## Probe (c): tokens / census ⏳

Observed so far: worker sessions launch as
`claude --dangerously-skip-permissions --effort max` — effort is pinned
at max for pool workers by the claude provider template, which materially
affects tokens per bead. Standing LLM sessions in the minimal template:
**1** (mayor; `mode = "always"`) vs Gas Town's 4 per rig
(mayor/deacon/witness/refinery). Everything else is the Go controller,
a `gc` control-dispatcher process, and GC's own dolt server.

Numbers: ⏳ (per-bead transcript tokens + priming sizes at pilot end.)

## Probe (d): ops feel — running log

Positives:
- `gc doctor` (75+ real checks), `gc status`, `gc events --follow`,
  `gc session peek/attach` are genuinely useful; the event bus answers
  "what just happened" better than anything in Gas Town.
- Health patrol restart-with-backoff worked unattended (see probe b).
- Managed Dolt self-provisioned on a private port with sane paths;
  `gc maintenance dolt-gc` + `gc dolt-cleanup` exist for store hygiene
  (the "gc dolt compact/restart"-shaped tooling the bead asked about).
- Config layering (`gc config show/explain`) makes the resolved state
  inspectable — big step over GT's implicit role tree.

Friction (each of these cost real time):
- **File provider is demo-grade**: `gc bd` refuses it; text-slings
  always create beads in the *city* store even when run from a rig
  (cross-rig routing then demands `--force`); rig-scoped agents query
  the *rig* store so routed work is invisible to them; and we observed
  **bead-ID double allocation** (a convoy and the mayor's session bead
  both `gc-5`; our seeded bug bead's ID later reissued to an
  order-tracking bead). Several core-pack orders (beads-health,
  nudge-mail-sweep, order-tracking-sweep) fail exit-127 under it.
- The minimal template's always-on **mayor freelances**: unprompted, it
  created "superseding" duplicate beads and typed a steering prompt into
  a worker session. Had to be stood down by mail. Any real deployment
  needs the mayor prompt hardened or the named_session dropped.
- `gc rig add` local-main commit (see probe a).
- `worktree-setup.sh` needs a `git worktree prune` guard.
- Cosmetic: `bd 1.0.4` schema-drift warnings on rig add
  ("repairing dependencies.id default"), `custom-types` doctor warning
  survives `--fix`.

Portability notes for ia_next/coauthor (not implemented here): nothing
in the pack is stuff-specific except the repo URL, quality-gate commands
and the branch prefix; Vercel/RunPod/Neon access would ride on the same
pattern (env into sessions via provider config / `[order.env]`,
secrets stay in the environment, exec orders for non-LLM automation).
K8s runtime exists if ia_next wants cluster isolation.

## Migration-relevant deltas from Gas Town

- Roles are config, not law: our whole GT role tree collapsed into one
  pool + one order + one mailbox for this repo's actual needs.
- The merge queue is replaced by whatever you write: our merge step is
  40 lines of shell behind `gh pr checks`, running on the controller.
- Formulas compile in-process (v2); the control-dispatcher executes
  control beads deterministically — no witness LLM in the loop.
- Beads stay beads (`bd` 1.0.4-compatible), so issue data migrates
  as-is if we adopt GC's managed store; the pilot deliberately did NOT
  import history.

## Evidence locations (pilot host)

- City: `~/gc-pilot/city` (config, pack, `.gc/events.jsonl`)
- Rig clone: `~/gc-pilot/rig-stuff`
- Bypass monitor: `~/gc-pilot/monitor-main.{sh,log}`, baseline in
  `monitor-baseline.txt`
- Merge-order log: `~/gc-pilot/city/.gc/runtime/merge-green-prs.log`
- GC source at v1.3.4: `~/gc-pilot/src`
