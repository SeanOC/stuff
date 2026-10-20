#!/usr/bin/env bash
# PreToolUse(Edit|Write|MultiEdit) guard: protected paths for worker sessions.
# Operator carve-out: .gc/runtime/guard-allow/workflow-edit-<rig>  (the mayor
# touches it when a bead carries an explicit workflow-edit authorization).
set -u
input=$(cat)
path=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin).get("tool_input",{}); print(d.get("file_path") or d.get("path") or "")' 2>/dev/null || true)
[ -n "$path" ] || exit 0
CITY="${GC_CITY:-$HOME/gc-pilot/city}"
# rig = from gc env if present, else from the worktree path (.gc/worktrees/<rig>/...), else the repo dir name
rig="${GC_RIG:-${RIG:-}}"
if [ -z "$rig" ]; then
  case "${CLAUDE_PROJECT_DIR:-$PWD}" in
    */.gc/worktrees/*) rig=$(printf '%s' "${CLAUDE_PROJECT_DIR:-$PWD}" | sed -E 's#.*/\.gc/worktrees/([^/]+)/.*#\1#') ;;
    *) rig=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}" | sed -E 's/^rig-//') ;;
  esac
fi
case "$path" in
  */.github/workflows/*|.github/workflows/*)
    [ -e "$CITY/.gc/runtime/guard-allow/workflow-edit-$rig" ] || { printf 'BLOCKED: .github/workflows/ is mayor-owned. If your bead carries an explicit workflow-edit authorization, mail the mayor to set the carve-out marker.\n' >&2; exit 2; } ;;
  */.env|*/.env.*|.env|.env.*) printf 'BLOCKED: never write env files from a worker session.\n' >&2; exit 2 ;;
esac
exit 0
