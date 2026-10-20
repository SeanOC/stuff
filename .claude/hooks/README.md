# Worker guard hooks (Claude Code PreToolUse)

Source of truth for the per-rig `.claude/hooks/guard-*.py` + `.claude/settings.json` that turn the worker
prompt templates' "NEVER …" prose into deterministic blocks (best-practices review 2026-10-20, hardened
2026-10-20 after the codex gates on ia-next #376 / co-author #862 / ghastly-show #37 reproduced bypasses).
Rolled out by mayor PRs to each rig; keep the copies IDENTICAL to these files (rigs gitignore `.claude/`,
so the files are `git add -f`ed). Self-test: `python3 guard-selftest.py` (229 cases; exit 0 = pass).

## What is blocked (guard-bash.py, tokenized with shlex — quoted prose never trips a rule)
- push to main/master in any spelling (positional, `HEAD:main`, `refs/heads/main`, `--all`/`--mirror`,
  `git -c …`/`-C …` global options, bare `git push` while the checkout is on main/master); force pushes
  (`-f`, `--force*`, combined `-fu`, `+refspec`).
- `gh pr merge --admin`; `gh api` writes (POST/PUT/PATCH/DELETE or `-f/-F/--input`) to `/statuses/`,
  `/check-runs`, `/protection`, `/rulesets`, and the GraphQL branch-protection / commit-status mutations.
- `sudo`/`doas` anywhere: direct, through `env`/`command`/`nohup`/`timeout`/`xargs`/`nice`, inside
  `bash -c`/`sh -c`, `$(…)`, backticks, `find -exec`, pipelines and `;`/`&&` chains.
- `vercel env|logs|pull` (also via `npx`/`pnpm dlx`/`pnpm vercel`).
- waiting loops: `gh … --watch`, `gh run watch`, `watch`, `tail -f`/`--follow`, `journalctl -f`; `sleep`
  whose literal total in the command is ≥ 30 s, non-literal sleep args (`$X`, `$((30))`), any sleep inside
  a `for`/`while`/`until` loop.
- `bd|gc bd create|update` with `-a`, `-aX`, `-a=X`, `--assignee[=…]` (text option values are skipped).
- reads of secrets/memory by any program: `.env`, `.env.*` (except `.example/.sample/.template/.dist`),
  `~/.claude/projects/**`, `**/.gc/runtime/secrets/**` — paths are normalized (`..`, `~`, `$HOME`, cwd),
  so `src/../.env` is caught; `echo`/`printf` are exempt.
- writes into `.github/workflows/`: redirects (`>`, `>>`, `&>`, heredocs), `tee`, `cp/mv/install/rsync/ln`,
  `dd of=`, `truncate`, `sed -i`/`perl -i`, `rm`, `touch`, `git rm/mv/checkout/restore`; redirects to an
  unresolvable expansion (`> $OUT`) are blocked too. guard-edit.py covers Edit/Write/MultiEdit/NotebookEdit
  with the same normalization (plus realpath, so a symlink does not help).

Not covered (documented limits): commands hidden inside `python -c`/`node -e` strings, scripts executed
from files, and anything a shell expansion produces at runtime. The `permissions.deny` rules in
settings.worker.json are the backstop for the worst cases (force push, sudo, admin merge, secret Reads).

## Carve-outs (mayor touches `.gc/runtime/guard-allow/<marker>`, removes it after the bead lands)
`push-main`, `vercel-env`, `long-sleep`, `watch`, `workflow-edit-<rig>` (rig = `GC_RIG`/`RIG`, else the
`.gc/worktrees/<rig>/` segment of `CLAUDE_PROJECT_DIR`). force-push, sudo, admin merge, status/protection
API writes, secret reads and bead assignment have NO carve-out — the deny rules apply whatever the marker.

## Codex pools are NOT covered
`.claude/settings.json` hooks run only in Claude Code sessions (ia-next workers today; stuff/coauthor/
ghastly workers only after a quota REVERT flips a pool to providers.claude). Codex CLI reads its own
hooks file, which Gas City generates per session (`.codex/hooks.json`), so a repo-level `.codex/` entry
is not loaded (verified by the ghastly worker on PR #37 via `hooks/list` → `[]`). Covering Codex pools
needs gc to merge rig-provided hooks into what it generates — an upstream gascity change, same class as
best-practices item 4; Sean's call whether to raise it.
