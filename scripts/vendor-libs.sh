#!/usr/bin/env bash
# Clone vendored OpenSCAD libraries into libs/ at the commits pinned
# in libs/README.md. Idempotent: skips if the target is already at the
# pinned SHA, a symlink (dev setup), or manually populated.
#
# Invoked from `prebuild` so Vercel/CI builds have the libraries
# available for Next.js file tracing and for /api/source at runtime.

set -euo pipefail

cd "$(dirname "$0")/.."

# Local patches under scripts/patches/<name>/*.patch are applied after
# checkout (see libs/README.md for why each exists). The vendor marker
# includes a fingerprint of the patch set so editing a patch re-vendors.
marker() {
  local name="$1" sha="$2"
  local pdir="scripts/patches/$name"
  if compgen -G "$pdir/*.patch" > /dev/null; then
    echo "$sha+patches-$(cat "$pdir"/*.patch | sha256sum | cut -c1-12)"
  else
    echo "$sha"
  fi
}

vendor() {
  local name="$1" url="$2" sha="$3"
  local dir="libs/$name"
  local want; want="$(marker "$name" "$sha")"

  if [ -L "$dir" ]; then
    echo "libs/$name is a symlink; skipping (dev setup)"
    return
  fi

  if [ -f "$dir/.vendor-sha" ] && [ "$(cat "$dir/.vendor-sha")" = "$want" ]; then
    echo "libs/$name already at $want"
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
  if compgen -G "scripts/patches/$name/*.patch" > /dev/null; then
    for p in "scripts/patches/$name"/*.patch; do
      echo "applying $p"
      # git apply, not patch(1): the CI image ships git but not patch.
      git apply --whitespace=nowarn --directory="$dir" -p1 "$p"
    done
  fi
  echo "$want" > "$dir/.vendor-sha"
}

vendor BOSL2                       https://github.com/BelfrySCAD/BOSL2.git                     456fcd8
vendor QuackWorks                  https://github.com/AndyLevesque/QuackWorks.git              6123129
vendor gridfinity-rebuilt-openscad https://github.com/kennetek/gridfinity-rebuilt-openscad.git 910e22d
