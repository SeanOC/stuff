#!/usr/bin/env bash
# End-to-end smoke test: /scad-new → /scad-render → /scad-export against
# a motor mount. Asserts verdicts + bbox tolerance vs. expected values.
#
# This bypasses the skill wrappers and invokes scripts/*.py directly for
# determinism. Run from repo root.
#
# Exit 0 on full loop success; non-zero with diagnostic on any failure.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

NAME="smoke_motor_mount"
MODEL_PATH="models/${NAME}.scad"
RENDER_DIR="renders/${NAME}"
STL_PATH="exports/${NAME}.stl"

NEW_SCRIPT=".claude/skills/scad-new/scripts/new.py"
RENDER_SCRIPT=".claude/skills/scad-render/scripts/render.py"
EXPORT_SCRIPT=".claude/skills/scad-export/scripts/export.py"

JQ() { python3 -c "import json,sys; print(json.load(sys.stdin)$1)"; }

fail() {
    echo "SMOKE FAIL: $*" >&2
    exit 1
}

# Clean slate — delete any prior smoke artifacts.
rm -f "$MODEL_PATH" "$STL_PATH"
rm -rf "$RENDER_DIR"

# ---------------------------------------------------------------------------
# Step 1: author model via /scad-new (SCAD body piped via stdin).
# ---------------------------------------------------------------------------
echo "[1/3] authoring $MODEL_PATH via scad-new..."
NEW_OUT=$(python3 "$NEW_SCRIPT" --name "$NAME" --angles "top,front,side,iso" <<'SCAD'
$fn = 96;
PRINT_ANCHOR_BBOX = [60, 40, 5];

plate_w = 60; plate_d = 40; plate_t = 5;
bore = 20; boss = 2;
hole_d = 3.2; hole_dx = 48; hole_dy = 28;
cb_d = 6; cb_depth = 2;

difference() {
    union() {
        translate([-plate_w/2, -plate_d/2, 0])
            cube([plate_w, plate_d, plate_t]);
        cylinder(h = plate_t + boss, d = bore + 6);
    }
    translate([0, 0, -1]) cylinder(h = plate_t + boss + 2, d = bore);
    for (sx = [-1, 1]) for (sy = [-1, 1]) {
        translate([sx * hole_dx/2, sy * hole_dy/2, -1])
            cylinder(h = plate_t + boss + 2, d = hole_d);
        translate([sx * hole_dx/2, sy * hole_dy/2, plate_t - cb_depth])
            cylinder(h = cb_depth + 0.1, d = cb_d);
    }
}
SCAD
)

VERDICT=$(printf '%s' "$NEW_OUT" | JQ '["verdict"]')
[ "$VERDICT" = "authored_ok" ] || fail "new.py verdict=$VERDICT, expected authored_ok. payload: $NEW_OUT"
[ -f "$MODEL_PATH" ] || fail "$MODEL_PATH not written"

RENDER_VERDICT=$(printf '%s' "$NEW_OUT" | JQ '["render"]["verdict"]')
[ "$RENDER_VERDICT" = "rendered_ok" ] || fail "render verdict=$RENDER_VERDICT"

for view in top front side iso; do
    [ -f "$RENDER_DIR/$view.png" ] || fail "missing $RENDER_DIR/$view.png"
done
echo "    authored + rendered 4 angles."

# ---------------------------------------------------------------------------
# Step 2: re-render with -D plate_t=8 override (verifies parametric loop).
# ---------------------------------------------------------------------------
echo "[2/3] re-rendering with -D plate_t=8 override..."
OVERRIDE_OUT=$(python3 "$RENDER_SCRIPT" \
    --model "$MODEL_PATH" \
    --name "${NAME}_thick" \
    -D "plate_t=8" \
    --angles "top,front")
OVERRIDE_VERDICT=$(printf '%s' "$OVERRIDE_OUT" | JQ '["verdict"]')
[ "$OVERRIDE_VERDICT" = "rendered_ok" ] || fail "override render verdict=$OVERRIDE_VERDICT"
[ -f "renders/${NAME}_thick/front.png" ] || fail "override front.png missing"
# Sanity: the default and override front PNGs should differ.
if cmp -s "$RENDER_DIR/front.png" "renders/${NAME}_thick/front.png"; then
    fail "override front.png identical to default — -D plate_t=8 did not reach openscad"
fi
echo "    override produced distinct geometry."

# ---------------------------------------------------------------------------
# Step 3: export STL (simulated user approval).
# ---------------------------------------------------------------------------
echo "[3/3] exporting STL via scad-export (approval simulated)..."
EXPORT_OUT=$(python3 "$EXPORT_SCRIPT" --model "$MODEL_PATH" --name "$NAME")
EXPORT_VERDICT=$(printf '%s' "$EXPORT_OUT" | JQ '["verdict"]')
[ "$EXPORT_VERDICT" = "export_ok" ] || fail "export verdict=$EXPORT_VERDICT. payload: $EXPORT_OUT"
WATERTIGHT=$(printf '%s' "$EXPORT_OUT" | JQ '["is_watertight"]')
[ "$WATERTIGHT" = "True" ] || fail "STL not watertight"
[ -f "$STL_PATH" ] || fail "$STL_PATH missing"

# bbox tolerance check: (60, 40, 7) ±1 mm.
python3 - "$EXPORT_OUT" <<'PY' || fail "bbox outside tolerance"
import json, sys
payload = json.loads(sys.argv[1])
lo, hi = payload["bbox_mm"]
sz = tuple(hi[i] - lo[i] for i in range(3))
tol = 1.0
exp = (60.0, 40.0, 7.0)
for got, want, axis in zip(sz, exp, "XYZ"):
    if abs(got - want) > tol:
        print(f"bbox {axis}={got:.2f} outside {want}±{tol}", file=sys.stderr)
        sys.exit(1)
print(f"    bbox OK: ({sz[0]:.2f}, {sz[1]:.2f}, {sz[2]:.2f}) mm")
PY

echo ""
echo "SMOKE OK: $MODEL_PATH → $RENDER_DIR/ → $STL_PATH"

# ---------------------------------------------------------------------------
# Step 4: artifact browser server smoke (starts on ephemeral port, asserts /).
# ---------------------------------------------------------------------------
echo "[4/4] smoke-testing scripts/serve.py..."
python3 scripts/serve_smoke.py || fail "serve_smoke.py failed"
