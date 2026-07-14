#!/usr/bin/env bash
# Merge step for rigs whose repos carry advisory (non-required) checks that
# must NOT gate merges (co-8h7b: coauthor's verifier-preview is a known
# flaky-timeout jammer). Merges ONLY PRs whose head branch matches
# $BRANCH_PREFIX into main, and ONLY when all REQUIRED checks have concluded
# successfully (`gh pr checks --required`). Advisory checks are logged but
# never block. Never uses --admin, never bypasses required checks, never
# touches other PRs. Squash merge, delete branch after.
set -euo pipefail

REPO="${GH_REPO:?GH_REPO not set}"
PREFIX="${BRANCH_PREFIX:?BRANCH_PREFIX not set}"
LOG="${GC_CITY:-$HOME/gc-pilot/city}/.gc/runtime/merge-green-required-prs-${REPO##*/}.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "$(date -Is) $*" >> "$LOG"; }

prs=$(gh pr list --repo "$REPO" --state open --json number,headRefName,baseRefName \
  --jq ".[] | select(.headRefName | startswith(\"$PREFIX\")) | select(.baseRefName == \"main\") | .number")

[ -z "$prs" ] && exit 0

for pr in $prs; do
  # Gate on REQUIRED checks only. `gh pr checks --required` exits non-zero
  # if any required check is failing or still pending.
  if gh pr checks "$pr" --repo "$REPO" --required >> "$LOG" 2>&1; then
    # Advisory-check state is recorded for the log, never gated on.
    gh pr checks "$pr" --repo "$REPO" >> "$LOG" 2>&1 || \
      log "PR #$pr: advisory checks not all green (ignored — required are green)"
    log "PR #$pr: required checks green — merging (squash)"
    if gh pr merge "$pr" --repo "$REPO" --squash --delete-branch >> "$LOG" 2>&1; then
      log "PR #$pr: merged"
    else
      # Branch protection is strict (branch must be up to date with main), so
      # a PR that went BEHIND after a sibling merged fails here. Update its
      # branch (a merge commit on the PR's own branch — never main) so CI
      # re-runs and the next cycle merges it. Anything else stays for a human.
      if gh pr update-branch "$pr" --repo "$REPO" >> "$LOG" 2>&1; then
        log "PR #$pr: merge failed — branch updated, retrying next cycle"
      else
        log "PR #$pr: merge FAILED and update-branch failed (left open for human)"
      fi
    fi
  else
    log "PR #$pr: required checks not green yet — skipping"
  fi
done
