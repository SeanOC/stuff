# Worker guard hooks (Claude Code PreToolUse)

Source of truth for the per-rig `.claude/hooks/guard-*.py` + `.claude/settings.json` that turn the worker
prompt templates' "NEVER …" prose into deterministic blocks (best-practices review 2026-10-20, hardened
2026-10-20 after the codex gates on ia-next #376 / co-author #862 / ghastly-show #37 reproduced bypasses).
Rolled out by mayor PRs to each rig; keep the copies IDENTICAL to these files (rigs gitignore `.claude/`,
so the files are `git add -f`ed). Self-test: `python3 guard-selftest.py` (936 cases; exit 0 = pass).

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
- the path policy runs on the EFFECTIVE argv: after `command`/`env`/`nohup`/`timeout`/… wrappers, `FOO=1` assignments,
  `gc` globals and `git -C <dir>` (paths resolve relative to that dir; the protected tree is the worktree's).
  Package-runner options that take a value are parsed (`npx --package vercel vercel env pull`, `npx -p vercel …`,
  `npm exec --package vercel -- vercel …`, `pnpm --filter web exec …`, `-w`/`--workspace`, `--`), so the value is
  never mistaken for the executable. Wrapper options whose value is a FILE are checked by effect before the wrapper
  is stripped: `xargs -a|--arg-file <f>` is a read of f (`.env` blocks), `time -o|--output <f>` is a write (`.env`
  and `.github/workflows/…` block).
- a statement led by `if`/`elif`/`while`/`until`/`!` is checked as its condition command (`if git push origin main;
  then …`, `while sudo true; do …`, `until gh pr merge --admin 1; do …`); `for` is not a command.
- the cwd is tracked through the command: a literal `cd`/`pushd`/`popd`/`cd -` (also `command cd`/`builtin cd`) statement changes the directory the
  FOLLOWING statements resolve relative paths against (`cd .github/workflows && touch evil.yml`, `cd .github; rm -rf
  workflows`, `pushd .github/workflows && …`), and `env -C|--chdir <dir> cmd` resolves that one command's operands in
  dir. Conservatively a `cd` inside `( … )` carries too; `bash -c '…'` does not (a subprocess). After an unresolvable
  `cd $DIR`, write/destructive operands that name `.github`/`workflows` (or `rm -rf .`/`..`) are blocked while
  `cd $DIR && npm test` / `rm -rf build` stay allowed.
- `bd assign`, and `-a`/`--assignee` on `bd`/`gc bd` create|update after any bd globals (`--db`, `-C`, `--config`).
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
  operand of `grep`/`rg`/`ag`/`ack` is the PATTERN (not a path) unless `-e`/`-f` is given; grep/rg option values are text
  (patterns, globs, types, colours; rg's `-T`/`-M`/`-E`/`-r` take values, grep's do not) except `-f`/`--file`/`--pre`/`--ignore-file`,
  which are files and are checked — including the attached and clustered spellings `grep -f.env`, `grep -rf.env .`,
  `grep -rf .env .`, `rg -if.env` (a cluster's first `-f`/`-e` takes the rest of the cluster, or the next word, as its
  value); values of text options
  (`--notes`, `--body`, `-m` on `git commit`, …) are never paths; FILE-valued options (`--body-file`, `--design-file`,
  `-F body=@file`) are, so `gh pr comment --body-file .env` blocks.
- workflow tree: besides direct writes, `rm`/`rmdir`/`mv`/`unlink`/`shred` and `git rm|mv|clean` on `.github`, the
  worktree root or any parent, `find <root> … -delete` whose root is `.github`, the worktree root or a parent — unless
  every `-name`/`-path` test is a literal or carries a non-yml/yaml extension (`find . -name '*.pyc' -delete` passes,
  `find . -delete` and `find . -name '*.yml' -delete` block), the worktree-updating `git reset --hard|--merge|--keep <ref>`
  (any ref other than HEAD replaces the workflow tree with that commit's) and the same modes without a ref while
  `.github/workflows` is dirty (`--soft`/`--mixed`/`git reset HEAD -- path` touch the index only), and
  `git restore --staged <workflow path>` is ALLOWED (index only; `--staged --worktree` still blocks). These take
  `.github/workflows` with them (`mv`'s destination is exempt). Also blocked: a directory
  copied/moved INTO `.github/` whose effective path is the workflow tree (`cp -R workflows .github/`), destructive operands
  that are unresolved shell expansions (`rm -r "$OLDPWD"`; `$PWD`/`$HOME` are resolved), pathspec-less
  `git clean` (exclusion patterns `-e`/`--exclude` are not pathspecs; dry-run flags are honoured inside clusters such as
  `-fdn`), and `patch` without `--dry-run`
  (uninspectable contents, like `git apply`/`am`). Sibling files such as `.github/CODEOWNERS` stay editable.
  `git checkout`/`git restore` with an ANCESTOR pathspec (`git checkout main -- .`, `git checkout -- .github`,
  `git restore --source main .`, `git checkout .`) rewrite the workflow tree through the ancestor and are blocked
  the same way (branch switches, `-b`, `--staged`-only restores and pathspecs outside `.github/workflows` stay
  allowed; a first checkout operand counts as a path only when it cannot be a ref: `.`, `/…`, `~…`). A PATHLESS
  `git stash`/`stash push` (and `-u`/`-a`/`--include-untracked`/`--all`) is blocked ONLY while `.github/workflows`
  has uncommitted changes (`git status --porcelain -- .github/workflows`, untracked files counted only with `-u`/`-a`;
  if git cannot answer, the stash is allowed) — on a clean workflow tree a stash is harmless; `stash list|show|drop|
  pop|apply|save <msg>` are not checked. `mv -t <dir>`'s target value is a destination (never a destructive source),
  so `mv -t . /tmp/file` is allowed while `mv -t .github/workflows x` still blocks on the effective destination.
- the Read, Grep and Glob tools are hooked too (guard-edit.py, on their `path`): env files, mayor memory and runtime secrets are unreadable;
  `.github/workflows/` stays READABLE. The native `permissions.deny` list is a fixed-name backstop
  (`./.env`, `./.env.local|production|development|prod`, `**/*.env`) chosen so it cannot catch the templates.
- waiting loops: `gh … --watch`, `gh run watch`, `watch`, any program's enabled `--watch`/`--watchAll`/`--watch-all`
  (false-ish values `=false`/`=0`/`=no`/`=off` pass; anything else, such as `=falsehood`, blocks), the
  program-specific spellings `vitest watch`/`vitest dev`/`vitest -w` and `tsc -w`/`tsc-alias -w` (direct or behind
  `pnpm`/`npm`/`npx`/`yarn`/`bun` [`exec`/`dlx`/`x`]; `-w` is NOT generic — `jest -w` is `--maxWorkers`, `rg -w` is
  word-match), `tail -f`/`--follow`, `journalctl -f`; `sleep`
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
Known gaps include clustered `gh` root short flags (such as `-vR`), a native Grep over a DIRECTORY that contains an
env file (only the `path` operand is checked),
writes to the singular `/commits/<sha>/status` endpoint, `git stash pop|apply` re-creating a workflow change that an
earlier (pre-guard) stash holds, and the stash dirty-check being scoped to the hook's own worktree (`git -C <other> stash`). The `permissions.deny` rules in
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
