# Worker guard hooks (Claude Code PreToolUse)

Source of truth for the per-rig `.claude/hooks/guard-*.py` + `.claude/settings.json` that turn the worker
prompt templates' "NEVER …" prose into deterministic blocks (best-practices review 2026-10-20, hardened
2026-10-20 after the codex gates on ia-next #376 / co-author #862 / ghastly-show #37 reproduced bypasses).
Rolled out by mayor PRs to each rig; keep the copies IDENTICAL to these files (rigs gitignore `.claude/`,
so the files are `git add -f`ed). Self-test: `python3 guard-selftest.py` (472 cases; exit 0 = pass).

## Threat model
The hooks stop ACCIDENTAL and habitual rule-breaking by a cooperative agent (the forms workers have actually
typed: pushing main by reflex, `sudo apt`, `vercel env pull`, `--watch`, long sleeps, assigning beads,
cat-ing `.env`). They are not a sandbox against an agent trying to evade them: a shell-syntax deny-list
cannot be complete (scripts, `python -c`, runtime expansions, aliases). The backstops for the cases that
matter most are branch protection + required checks, `permissions.deny`, and the sanitized worktree env.
Gate reviewers: judge a change by whether it closes forms a cooperative agent would plausibly type, not
by whether an adversarial form still exists — the README's "not covered" list is the accepted boundary.

## What is blocked (guard-bash.py, tokenized with shlex — quoted prose never trips a rule)
- push to main/master in any spelling (positional, `HEAD:main`, `refs/heads/main`, `--all`/`--mirror`,
  matching `:` and wildcard `*` refspecs, `git -c …`/`-C …` global options, bare `git push` while the
  checkout is on main/master); force pushes (`-f`, `--force*`, combined `-fu`, `+refspec`).
- `gh pr merge --admin` (also `--admin=true` and with standalone `-R`/`--repo` root options anywhere); `gh api` writes (POST/PUT/PATCH/DELETE or `-f/-F/--input`) to `/statuses/`,
  `/check-runs`, `/protection`, `/rulesets`, and the GraphQL branch-protection / commit-status mutations
  (value-bearing options such as `-H`/`--hostname` are consumed before the endpoint is picked; `-XDELETE`
  and the old `gh api POST <endpoint>` forms count). `gh api graphql` with any `mutation`, `--input` or an
  `@file` value is blocked outright (opaque payloads fail closed).
- `sudo`/`doas` anywhere: direct, through `env`/`command`/`nohup`/`timeout`/`xargs`/`nice`/`ionice` (their
  value-taking options are parsed), inside `bash -c`/`sh -c`, `eval` (re-parsed recursively), `$(…)` and
  backticks in any position — including the quoted forms `echo "$(…)"` / `-m "… $(…)"` (substitutions are
  checked once each with independent quote context; single-quoted text, comments, and quoted-delimiter
  heredoc bodies are literal. Unquoted heredocs are checked for substitutions, not prose) —
  `find -exec`, `timeout 30 -- …`, a leading `--`, pipelines and `;`/`&&` chains; shell `-lc`/`-xc`
  clusters and `env -S "…"` payloads are re-parsed.
- `vercel env|logs|pull` (also via `npx`/`pnpm dlx`/`pnpm vercel`; global options such as `--scope team`/`--token` before the subcommand are consumed).
- secret reads: `.env`, `.env.<x>` and `<name>.env` (pulled prod envs such as `/tmp/prod.env`) by any read/write
  program, `dd if=`, `source`/`.`; templates `.example`/`.sample`/`.template`/`.dist` are allowed. The first
  operand of `grep`/`rg`/`ag`/`ack` is the PATTERN (not a path) unless `-e`/`-f` is given; values of text options
  (`--notes`, `--body`, `-m` on `git commit`, …) are never paths.
- workflow tree: besides direct writes, `rm`/`rmdir`/`mv`/`unlink`/`shred` and `git rm|mv|clean` on `.github`, the
  worktree root or any parent (they take `.github/workflows` with them), and `patch` without `--dry-run`
  (uninspectable contents, like `git apply`/`am`). Sibling files such as `.github/CODEOWNERS` stay editable.
- the Read tool is hooked too (guard-edit.py): env files, mayor memory and runtime secrets are unreadable;
  `.github/workflows/` stays READABLE. The native `permissions.deny` list is a fixed-name backstop
  (`./.env`, `./.env.local|production|development|prod`, `**/*.env`) chosen so it cannot catch the templates.
- waiting loops: `gh … --watch`, `gh run watch`, `watch`, `tail -f`/`--follow`, `journalctl -f`; `sleep`
  whose literal total in the command (all operands, all statements) is ≥ 30 s, non-literal sleep args (`$X`, `$((30))`), any sleep inside
  a `for`/`while`/`until` loop.
- `bd|gc bd create|update` with `-a`, `-aX`, `-a=X`, `--assignee[=…]` (text option values are skipped; `gc`
  global options such as `--rig X` and stray `--` separators are stripped first, as for `gh`).
- reads of secrets/memory by any program: `.env`, `.env.*` (except `.example/.sample/.template/.dist`),
  `~/.claude/projects/**`, `**/.gc/runtime/secrets/**` — paths are normalized (`..`, `~`, `$HOME`, cwd),
  so `src/../.env`, `--opt=path` values and quoted paths with spaces are caught when they are operands of a
  reader/writer program; `dd if=/of=` too. Prose values (`-m`, `--body`, `--notes`, `echo`) are never paths.
- writes into `.github/workflows/`: redirects (`>`, `>>`, `&>`, heredocs), `tee`, `cp/mv/install/rsync/ln`,
  `dd of=`, `truncate`, `sed -i`/`--in-place=`, `perl -i`, `rm`, `touch`, `tar -C`/`unzip`, `cp/mv/install -t`/
  `--target-directory=`, `git rm/mv/checkout/restore/clean/stash`, and `git apply`/`git am`
  (patch contents cannot be inspected; `--check`/`--stat` stay allowed); redirects to an unresolvable
  expansion (`> $OUT`) are blocked too. guard-edit.py covers Edit/Write/MultiEdit/NotebookEdit
  with the same normalization (plus realpath, so a symlink does not help).

Not covered (documented limits): commands hidden inside `python -c`/`node -e` strings, scripts executed
from files, process substitutions (`<(…)`), and anything a shell expansion produces at runtime.
Known CLI gaps include clustered `gh` root short flags (such as `-vR`), Vercel `-e`/`--env` globals,
and writes to the singular `/commits/<sha>/status` endpoint. The `permissions.deny` rules in
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
