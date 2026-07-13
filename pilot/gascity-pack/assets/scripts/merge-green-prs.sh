#!/usr/bin/env bash
# Pilot merge step (st-qr2). Merges ONLY pilot PRs (head branch gc-pilot/*)
# into SeanOC/stuff main, and ONLY when all CI checks have completed
# successfully. Never uses --admin, never bypasses checks, never touches
# non-pilot PRs. Squash merge, delete branch after.
set -euo pipefail

REPO="${GH_REPO:?GH_REPO not set}"
PREFIX="${PILOT_BRANCH_PREFIX:-gc-pilot/}"
LOG="${GC_CITY:-$HOME/gc-pilot/city}/.gc/runtime/merge-green-prs.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "$(date -Is) $*" >> "$LOG"; }

prs=$(gh pr list --repo "$REPO" --state open --json number,headRefName,baseRefName \
  --jq ".[] | select(.headRefName | startswith(\"$PREFIX\")) | select(.baseRefName == \"main\") | .number")

[ -z "$prs" ] && exit 0

for pr in $prs; do
  # Every check must be concluded and successful. `gh pr checks` exits
  # non-zero if any check is failing or pending.
  if gh pr checks "$pr" --repo "$REPO" --required >> "$LOG" 2>&1 \
     && gh pr checks "$pr" --repo "$REPO" >> "$LOG" 2>&1; then
    log "PR #$pr: all checks green — merging (squash)"
    if gh pr merge "$pr" --repo "$REPO" --squash --delete-branch >> "$LOG" 2>&1; then
      log "PR #$pr: merged"
    else
      log "PR #$pr: merge FAILED (left open for human)"
    fi
  else
    log "PR #$pr: checks not green yet — skipping"
  fi
done
