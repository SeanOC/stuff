#!/bin/sh
# One-time setup: point this clone's git at the repo's tracked hooks.
# Safe to re-run — `git config` overwrites the same key idempotently.

set -e

cd "$(dirname "$0")/.."

git config core.hooksPath .githooks

echo "✓ core.hooksPath set to .githooks"
echo "  The prepare-commit-msg hook will now append the Claude Code"
echo "  attribution trailer to every authored commit in this clone."
