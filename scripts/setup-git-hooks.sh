#!/bin/sh
# One-time setup: point this clone's git at the repo's tracked hooks.
# Safe to re-run — `git config` overwrites the same key idempotently.

set -e

cd "$(dirname "$0")/.."

git config core.hooksPath .githooks

echo "✓ core.hooksPath set to .githooks"
echo "  prepare-commit-msg: appends the Claude Code attribution trailer"
echo "  to every authored commit in this clone."
echo "  pre-commit: catches model-pipeline gotchas (scad<->catalog"
echo "  parity, invariants sidecar, PRINT_ANCHOR_BBOX, scad syntax)"
echo "  with actionable feedback — see docs/dx-precommit.md."
