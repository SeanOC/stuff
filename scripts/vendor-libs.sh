#!/usr/bin/env bash
# Clone BOSL2 and QuackWorks into libs/ at the commits pinned in
# libs/README.md. Idempotent: skips if the target is already at the
# pinned SHA, a symlink (dev setup), or manually populated.
#
# Invoked from `prebuild` so Vercel/CI builds have the libraries
# available for Next.js file tracing and for /api/source at runtime.

set -euo pipefail

cd "$(dirname "$0")/.."

vendor() {
  local name="$1" url="$2" sha="$3"
  local dir="libs/$name"

  if [ -L "$dir" ]; then
    echo "libs/$name is a symlink; skipping (dev setup)"
    return
  fi

  if [ -f "$dir/.vendor-sha" ] && [ "$(cat "$dir/.vendor-sha")" = "$sha" ]; then
    echo "libs/$name already at $sha"
    return
  fi

  if [ -d "$dir" ] && [ -z "$(ls -A "$dir" 2>/dev/null)" ] || [ ! -e "$dir" ]; then
    : # empty or missing — ok to populate
  elif [ ! -f "$dir/.vendor-sha" ]; then
    echo "libs/$name is non-empty without a vendor marker; skipping"
    return
  else
    rm -rf "$dir"
  fi

  mkdir -p libs
  git clone "$url" "$dir"
  ( cd "$dir" && git checkout "$sha" && rm -rf .git )
  echo "$sha" > "$dir/.vendor-sha"
}

vendor BOSL2      https://github.com/BelfrySCAD/BOSL2.git    456fcd8
vendor QuackWorks https://github.com/AndyLevesque/QuackWorks.git 6123129
