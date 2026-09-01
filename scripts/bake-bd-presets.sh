#!/usr/bin/env bash
# Build-time preset bake for build123d models (bead pst-0um9).
#
# Chained into the `prebuild` npm hook (runs before `next build`), so it
# fires on Vercel and in any `npm run build`. Emits, for every app-listed
# build123d model, one STL + one GLB per preset into build123d/baked/
# (the fixed root the /api/bd-asset route serves and next.config.mjs
# file-tracing includes).
#
# Gated on BD_MODELS_ENABLED so ONE env var controls the whole feature:
# unset (the default everywhere except the Vercel prod project and local
# dev/e2e runs) → this is a no-op, the build is unchanged, and CI never
# pays the build123d install cost. To activate build123d models on the
# live site, set BD_MODELS_ENABLED=1 in the Vercel project env; that
# turns on both the bake here and the gallery/detail visibility.
#
# Fails HARD when enabled: a broken bake must surface at build time, not
# ship pages whose GLB/STL 404. To recover the SCAD-only site without a
# git revert, unset BD_MODELS_ENABLED (or set it to 0) and redeploy.
set -euo pipefail

if [ "${BD_MODELS_ENABLED:-}" != "1" ]; then
  echo "bake-bd-presets: BD_MODELS_ENABLED != 1 — skipping build123d preset bake."
  exit 0
fi

# Repo root = parent of this script's dir, regardless of CWD.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BD_DIR="$ROOT/build123d"

if [ ! -d "$BD_DIR" ]; then
  echo "bake-bd-presets: no build123d/ directory at $BD_DIR — nothing to bake." >&2
  exit 1
fi

# uv drives the pinned build123d env (build123d/uv.lock). Install the
# standalone binary if the build image doesn't ship it (Vercel doesn't).
if ! command -v uv >/dev/null 2>&1; then
  echo "bake-bd-presets: uv not found — installing the standalone binary…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # The installer drops uv in ~/.local/bin (or $XDG_BIN_HOME); add both.
  export PATH="$HOME/.local/bin:${XDG_BIN_HOME:-$HOME/.local/bin}:$PATH"
fi

# Keep the uv download/build cache in a stable, deploy-cacheable path so
# repeat builds reuse the (large) build123d/OCP wheels.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"

cd "$BD_DIR"
echo "bake-bd-presets: uv sync --frozen (cache: $UV_CACHE_DIR)…"
uv sync --frozen

echo "bake-bd-presets: baking presets into build123d/baked/…"
uv run python scripts/export.py --presets-only baked

echo "bake-bd-presets: done."
ls -R baked
