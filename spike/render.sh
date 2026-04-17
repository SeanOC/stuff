#!/usr/bin/env bash
# Spike-only render harness. Renders a .scad file to 4 PNGs (front/side/top/iso).
# Usage: ./render.sh <model.scad> <output-dir> [-D name=val ...]
set -euo pipefail

MODEL="$1"; shift
OUTDIR="$1"; shift
mkdir -p "$OUTDIR"

OPENSCAD="${OPENSCAD:-/usr/bin/openscad}"
IMG=1024

# Use eye,center camera format (6 values). Eye positions are far enough to
# comfortably frame a ~100mm model; --viewall auto-fits regardless.
declare -A CAMS=(
  [top]="0,0,300,0,0,0"       # looking straight down -Z
  [front]="0,-300,0,0,0,0"    # looking along +Y (front face toward camera)
  [side]="300,0,0,0,0,0"      # looking along -X (right face toward camera)
  [iso]="200,-200,150,0,0,0"  # classic isometric
)

for name in top front side iso; do
  cam="${CAMS[$name]}"
  xvfb-run -a "$OPENSCAD" \
    --colorscheme=Tomorrow \
    --imgsize="$IMG,$IMG" \
    --camera="$cam" \
    --viewall --autocenter --projection=orthogonal \
    -o "$OUTDIR/$name.png" \
    "$@" \
    "$MODEL" 2>&1 | tail -5 || { echo "FAILED rendering $name"; exit 1; }
  [[ -s "$OUTDIR/$name.png" ]] || { echo "EMPTY png: $name"; exit 1; }
  echo "rendered $name.png ($(stat -c %s "$OUTDIR/$name.png") bytes)"
done
