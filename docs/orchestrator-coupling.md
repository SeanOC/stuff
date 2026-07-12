# Gas Town / orchestrator coupling inventory (st-438)

Everything in this repo that assumes the Gas Town multi-agent
orchestrator (its `gt` CLI, the beads/`bd` issue tracker, Dolt, polecat
worktrees), catalogued ahead of the fresh-workspace migration (Gas City
pilot). **Inventory only — nothing here has been decoupled.** Each item
is classified:

- **repo-intrinsic** — part of how this project works regardless of
  orchestrator; keep as-is.
- **orchestrator-coupling** — assumes Gas Town is present; flag for the
  fresh workspace (adapt, replace, or accept the dependency).

Verified against the tree at the time of writing: no tracked file
invokes the `gt` CLI, no CI/deploy config keys on `polecat/*` branch
names, and no tracked file hardcodes `~/gt/` paths. The coupling that
exists is beads-shaped, not gt-shaped.

## Tracked files

| Where | What | Classification |
| --- | --- | --- |
| `CLAUDE.md` — "Issue tracking — beads (`bd`)" | Instructs agents to use `bd prime` / `bd ready` / `bd update --claim` / `bd close`. Assumes the beads CLI is installed and a beads DB is reachable (in Gas Town: Dolt on port 3307, provisioned by the rig). Also links `github.com/steveklabnik/beads`, which does not match the workspace-level docs (`gastownhall/beads`). | **orchestrator-coupling** — the *practice* of using an issue tracker is intrinsic; the provisioning of `bd`+Dolt is Gas Town's. A fresh workspace needs `bd` installed + DB bootstrapped, or this section rewritten. |
| `.claude/settings.json` — `SessionStart` + `PreCompact` hooks | Both run `bd prime`. In a workspace without the beads CLI the hook command fails at session start. | **orchestrator-coupling** — flag. Either guarantee `bd` in the fresh workspace or make the hook `command -v bd && bd prime`-style tolerant. |
| `AGENTS.md` — "Scope discipline" section | Process language: "file a new bead", "your bead's work". | **orchestrator-coupling** (vocabulary only) — the policy itself (don't revert prior work silently; file follow-up issues) is intrinsic. |
| `tests/sweep/known-failures.ts` | Registry values are `"<bead-id>: reason"`; the documented lifecycle is "remove entries as their beads close". | **repo-intrinsic mechanism, beads-flavored keys** — works with any tracker; entries reference `st-*` beads today. Keep; new entries just need *some* tracker ID. |
| `.github/workflows/ci.yml`, `models/*.scad`, `models/*.invariants.py`, `.claude/skills/**`, `docs/**` | Pervasive `st-xxx` bead IDs in comments as provenance (~114 tracked files). Two invariants sidecars (`blu_black_tank_valve_mount`, `blu_flow_meter_mount_80mm`) also say "polecat" meaning "the next agent". | **repo-intrinsic** — archaeology. The IDs only *resolve* with access to the `st-*` beads DB; without it they still serve as stable change-reason markers. Keep. |
| `.claude/skills/scad-send/SKILL.md` | References research beads (st-5zs, st-qxt, st-g7x, st-98m) and says the printer token must stay "out of beads". | **repo-intrinsic** — archaeology + a security note; no runtime dependency. |
| `docs/plans/`, `docs/brainstorms/`, `docs/research/` | Historical planning docs referencing beads workflows and old worktree paths. | **repo-intrinsic** — archive; not load-bearing. |
| `.gitignore` — `.dolt/`, `*.db`, `.beads-credential-key`, `.beads/`, `CLAUDE.local.md`, `.claude/commands/{done,handoff}.md` | Defensive ignores for orchestrator runtime state so it can never be committed from an agent worktree. | **repo-intrinsic** — harmless everywhere, essential under Gas Town. Keep. |
| `.githooks/prepare-commit-msg` | Appends the Claude Code attribution trailer. Claude-Code-coupled, not Gas-Town-coupled. | **repo-intrinsic**. |

## Untracked worktree state (exists under Gas Town only)

These live in a polecat's worktree but are gitignored — a fresh clone
does not have them. Listed so nobody hunts for "missing" files in the
new workspace:

| Where | What |
| --- | --- |
| `CLAUDE.local.md` | The polecat runbook (gt done contract, mail addresses, formula workflow). Pure Gas Town. |
| `.claude/commands/done.md`, `.claude/commands/handoff.md` | Slash-command wrappers around `gt done` / `gt handoff`. Pure Gas Town. |
| `.beads/redirect` | Points `bd` at the rig-level beads DB (`../../../mayor/rig/.beads`). Pure Gas Town. |

## Process couplings with no in-repo artifact

- **Merge flow**: polecats push `polecat/<name>/<bead>@<suffix>`
  branches; the Refinery merges via the merge queue. Nothing in CI or
  Vercel config keys on these branch names (verified: `ci.yml`,
  `param-sweep.yml`, `vercel.ts`, `playwright.config.ts`) — GitHub PR
  merges from any branch name work identically.
- **Issue lifecycle**: DONE-criteria in the `new-model` skill and the
  known-failures contract say "file a bead". In a fresh workspace,
  read as "file an issue in whatever tracker is active".

## Fresh-workspace checklist (derived, not yet actioned)

1. Decide the issue tracker; if it's still beads, provision `bd` + DB
   before the first agent session (else the `.claude/settings.json`
   hooks fail).
2. Rewrite `CLAUDE.md`'s issue-tracking section (and fix or drop the
   `steveklabnik/beads` link) to match whatever was decided in (1).
3. Port or drop the local-only runbook files (`CLAUDE.local.md`,
   `.claude/commands/*`) — they are orchestrator-supplied, not
   repo-supplied.
4. Everything else ships as-is: CI, skills, hooks, models, and tests
   have no runtime dependency on Gas Town.
