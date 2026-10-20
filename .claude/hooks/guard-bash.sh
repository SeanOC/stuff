#!/usr/bin/env bash
# PreToolUse(Bash) guard for gc-launched Claude worker sessions (mayor, 2026-10-20,
# Claude Code best-practices review item 1). Deterministic prohibitions that used
# to live as "NEVER …" prose in every worker prompt template. Exit 2 = block with
# the message as feedback; exit 0 = allow. Reads the hook JSON on stdin.
#
# Operator carve-outs (mayor touches a marker, hook honours it):
#   .gc/runtime/guard-allow/<marker>  where <marker> is one of:
#     push-main   force-push   sudo   vercel-env   long-sleep   watch
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
[ -n "$cmd" ] || exit 0
CITY="${GC_CITY:-$HOME/gc-pilot/city}"
allowed() { [ -e "$CITY/.gc/runtime/guard-allow/$1" ]; }
block() { printf 'BLOCKED by guard-bash (%s): %s\nIf this is genuinely required, mail the mayor; the mayor can grant a one-off carve-out.\n' "$1" "$2" >&2; exit 2; }

# 1. pushes to main / force pushes
if printf '%s' "$cmd" | grep -qE '(^|[;&|[:space:]])git[[:space:]]+push\b'; then
  if printf '%s' "$cmd" | grep -qE '(--force|-f\b|--force-with-lease|\+[a-zA-Z0-9_./-]+:)'; then
    allowed force-push || block force-push "force-pushing is never allowed from a worker"
  fi
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]:])(main|master)([[:space:]]|$)|HEAD:(main|master)\b'; then
    allowed push-main || block push-main "workers push feature branches only; main merges through the review gate"
  fi
fi
# 2. admin merges
printf '%s' "$cmd" | grep -qE 'gh[[:space:]]+pr[[:space:]]+merge.*--admin' && block admin-merge "never bypass branch protection"
# 3. sudo
printf '%s' "$cmd" | grep -qE '(^|[;&|[:space:]])sudo[[:space:]]' && { allowed sudo || block sudo "no privilege escalation in worker sessions"; }
# 4. production secrets
printf '%s' "$cmd" | grep -qE 'vercel[[:space:]]+(env|logs)\b' && { allowed vercel-env || block vercel-env "production env/logs are mayor-only; use the sanitized env the worktree setup provides"; }
# 5. waiting loops that burn context (poll with a bounded command instead)
printf '%s' "$cmd" | grep -qE 'gh[[:space:]]+(pr|run)[[:space:]]+(checks|watch|view).*--watch' && { allowed watch || block watch "no --watch loops; check once and end your turn (the mayor merges)"; }
printf '%s' "$cmd" | grep -qE '(^|[;&|[:space:]])sleep[[:space:]]+([3-9][0-9]|[1-9][0-9]{2,})\b' && { allowed long-sleep || block long-sleep "no sleeps ≥ 30 s; end your turn and let the next event resume you"; }
# 6. bead assignment games
printf '%s' "$cmd" | grep -qE 'bd[[:space:]]+(create|update)\b.*([[:space:]]-a[[:space:]]|--assignee)' && block bd-assignee "never set assignees; the claim hook owns assignment"
exit 0
