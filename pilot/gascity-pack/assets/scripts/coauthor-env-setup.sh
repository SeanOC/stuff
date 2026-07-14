#!/bin/sh
# coauthor-env-setup.sh — provision a coauthor worker worktree with the env
# the app needs (Neon DATABASE_URL/DATABASE_URL_UNPOOLED, Vercel/RunPod
# creds), same pattern GT polecats use: vercel link metadata + `vercel env
# pull` with the machine's vercel auth. Secrets land ONLY in gitignored
# .env.local inside the worktree — never committed, never in city config.
#
# Usage: coauthor-env-setup.sh <worktree-dir>
set -eu

WT="${1:?usage: coauthor-env-setup.sh <worktree-dir>}"

[ -d "$WT" ] || { echo "coauthor-env-setup: worktree missing: $WT" >&2; exit 1; }

# Vercel project link (ids are not secrets; the token lives in the machine's
# vercel CLI auth). Matches ~/gt/coauthor mayor/refinery link.
mkdir -p "$WT/.vercel"
if [ ! -f "$WT/.vercel/project.json" ]; then
    cat > "$WT/.vercel/project.json" <<'EOF'
{"projectId":"prj_MUwzETb6kZDihi9KaGsUQLKZdzMq","orgId":"team_T0YjTdP6Yrxps9ZdpnATj5hE","projectName":"co-author"}
EOF
fi

# Idempotent: skip the pull if a non-empty .env.local already exists.
if [ ! -s "$WT/.env.local" ]; then
    cd "$WT"
    if ! vercel env pull --environment=development --yes .env.local >/dev/null 2>&1; then
        echo "coauthor-env-setup: vercel env pull failed (auth? network?)" >&2
        exit 1
    fi
fi

# Sanity: the two variables everything else depends on. Neon POOLED endpoint
# kills LISTEN/NOTIFY — realtime code must use DATABASE_URL_UNPOOLED, so both
# must be present.
for VAR in DATABASE_URL DATABASE_URL_UNPOOLED; do
    if ! grep -q "^$VAR=" "$WT/.env.local"; then
        echo "coauthor-env-setup: $VAR missing from pulled .env.local" >&2
        exit 1
    fi
done

exit 0
