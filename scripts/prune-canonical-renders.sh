#!/usr/bin/env bash
# prune-canonical-renders.sh <base-commit>
#
# Drop staged changes whose staged content byte-matches the same path
# at <base-commit>, restoring those paths to HEAD. Run inside a git
# repo after `git add`.
#
# Why (pst-dm9): CI regenerates render PNGs on model PRs and commits
# them back to the PR branch. Renders are engine-deterministic but not
# cross-machine-deterministic, so an author's locally rendered PNG for
# an *unchanged* model differs byte-wise from CI's — CI would "fix" it
# back to the canonical bytes with a push that changes nothing anyone
# can see, cancelling the in-flight param sweep and stranding PR checks
# in action_required. If CI's regenerated PNG matches what the base
# (main) already has, the model's render didn't really change: skip it
# and let the push-to-main flavour canonicalize after merge.
set -euo pipefail

base="${1:?usage: prune-canonical-renders.sh <base-commit>}"

staged_list=$(mktemp)
trap 'rm -f "$staged_list"' EXIT
git diff --cached --name-only -z > "$staged_list"

pruned=0
kept=0
while IFS= read -r -d '' path; do
  staged_blob=$(git rev-parse -q --verify ":$path" || true)
  base_blob=$(git rev-parse -q --verify "$base:$path" || true)
  if [ -n "$staged_blob" ] && [ "$staged_blob" = "$base_blob" ]; then
    if git cat-file -e "HEAD:$path" 2>/dev/null; then
      git checkout -q HEAD -- "$path"
    else
      # Path matches base but is absent from HEAD (deleted on the PR
      # branch): drop the staged re-add, keep the PR's deletion.
      git rm -q --cached -- "$path"
      rm -f -- "$path"
    fi
    echo "pruned (byte-matches $base): $path"
    pruned=$((pruned + 1))
  else
    kept=$((kept + 1))
  fi
done < "$staged_list"

echo "prune-canonical-renders: pruned=$pruned kept=$kept"
