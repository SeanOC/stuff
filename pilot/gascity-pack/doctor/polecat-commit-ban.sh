#!/bin/sh
# Doctor check (co-8h7b): the direct-push formula mol-polecat-commit must be
# policy-banned — the city-local shadow must exist, carry the unsatisfiable
# formula_compiler requirement, and no config may reference it as a
# default_sling_formula.
#
# Exit protocol: 0=OK, 1=Warning, 2+=Error.
set -u

CITY="${GC_CITY:-$(cd "$(dirname "$0")/.." && pwd)}"
BAN_FILE="$CITY/formulas/mol-polecat-commit.toml"

if [ ! -f "$BAN_FILE" ]; then
    echo "ban shadow missing: $BAN_FILE (core pack's direct-push formula is slingable)"
    exit 2
fi

if ! grep -q 'formula_compiler *= *">=999' "$BAN_FILE"; then
    echo "ban shadow present but requirement not unsatisfiable — cook would succeed"
    exit 2
fi

# No agent/config may pin the banned formula as its default sling.
HITS=$(grep -rn 'default_sling_formula.*mol-polecat-commit' \
    "$CITY/city.toml" "$CITY/pack.toml" "$CITY/agents" "$CITY/overlays" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "default_sling_formula references banned mol-polecat-commit: $HITS"
    exit 2
fi

echo "mol-polecat-commit ban in place (cook fails closed; no default_sling_formula refs)"
exit 0
