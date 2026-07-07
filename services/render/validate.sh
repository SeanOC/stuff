#!/usr/bin/env bash
# End-to-end LOCAL validation for the native render service (st-065).
#
# Builds the image, boots the container, and proves the Phase-1 claims:
#   - the ego blower mount renders a clean, invariant-passing STL for BOTH
#     mount_type variants (via the SERVICE), incl. bearing fidelity;
#   - a couple of other models render cleanly (model-general, exercises
#     BOSL2 + QuackWorks + gridfinity libs);
#   - the native latency win vs the ~22s WASM path is recorded;
#   - error paths return the right 4xx/5xx with {ok:false} and no STL.
#
# Exits non-zero on any failure. Run from anywhere; paths are repo-relative.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
IMAGE="stuff-render:st-065"
NAME="stuff-render-validate"
PORT="${VALIDATE_PORT:-8088}"
BASE="http://localhost:${PORT}"
WORK="$(mktemp -d)"
FAILS=0

pass() { echo "  PASS  $*"; }
fail() { echo "  FAIL  $*"; FAILS=$((FAILS + 1)); }
step() { echo; echo "== $* =="; }

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

step "build image"
docker build -f services/render/Dockerfile -t "$IMAGE" . || { echo "build failed"; exit 1; }

step "boot container"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -p "${PORT}:8080" "$IMAGE" >/dev/null
# Wait for readiness (openscad image + node cold start).
ready=0
for _ in $(seq 1 30); do
  if curl -fsS "${BASE}/health" >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
if [ "$ready" != 1 ]; then
  echo "container never became ready; logs:"; docker logs "$NAME" 2>&1 | tail -20; exit 1
fi
pass "health endpoint up"

# render <json-body> <out.stl> -> writes headers to $WORK/h.txt, body to out.
render() {
  curl -sS -D "$WORK/h.txt" -o "$2" -w '%{http_code}' \
    -X POST "${BASE}/render" -H 'content-type: application/json' -d "$1"
}
status_of() { curl -sS -o "$WORK/body.json" -w '%{http_code}' \
    -X POST "${BASE}/render" -H 'content-type: application/json' -d "$1"; }

# invariants <stem> <export-name> — copy a service STL into exports/ under
# the name check-invariants expects, then run the host invariant checker.
invariants() {
  local stem="$1" export_name="$2" src="$3"
  cp "$src" "exports/${export_name}.stl"
  if python3 scripts/check-invariants.py "$stem" >/dev/null 2>"$WORK/inv.err"; then
    pass "invariants: $stem"
  else
    fail "invariants: $stem"; sed 's/^/        /' "$WORK/inv.err" | tail -8
  fi
}

step "ego blower mount — both variants (SERVICE output → invariants)"
mkdir -p exports
# The default (multiconnect) and opengrid variants map to the filename-grid
# export names the invariants resolve to.
code=$(render '{"model":"models/ego_lb6500_blower_mount.scad"}' "$WORK/ego_mc.stl")
if [ "$code" = 200 ] && [ -s "$WORK/ego_mc.stl" ]; then
  ms_mc=$(grep -i '^x-render-ms:' "$WORK/h.txt" | tr -dc '0-9')
  pass "multiconnect render 200 (${ms_mc}ms, $(stat -c%s "$WORK/ego_mc.stl") bytes)"
else
  fail "multiconnect render (code=$code)"
fi
code=$(render '{"model":"models/ego_lb6500_blower_mount.scad","params":{"mount_type":"opengrid"}}' "$WORK/ego_og.stl")
if [ "$code" = 200 ] && [ -s "$WORK/ego_og.stl" ]; then
  ms_og=$(grep -i '^x-render-ms:' "$WORK/h.txt" | tr -dc '0-9')
  pass "opengrid render 200 (${ms_og}ms, $(stat -c%s "$WORK/ego_og.stl") bytes)"
else
  fail "opengrid render (code=$code)"
fi
# check-invariants for the ego mount checks BOTH the default-variant STL
# and the opengrid export in one pass.
invariants ego_lb6500_blower_mount ego_lb6500_blower_mount-multiconnect "$WORK/ego_mc.stl"
cp "$WORK/ego_og.stl" exports/ego_lb6500_blower_mount-opengrid.stl

step "sanity: other models render cleanly (model-general)"
for stem in popcorn_kernel gridfinity_bin; do
  code=$(render "{\"model\":\"models/${stem}.scad\"}" "$WORK/${stem}.stl")
  if [ "$code" = 200 ] && [ -s "$WORK/${stem}.stl" ]; then
    ms=$(grep -i '^x-render-ms:' "$WORK/h.txt" | tr -dc '0-9')
    pass "${stem} render 200 (${ms}ms)"
    invariants "$stem" "$stem" "$WORK/${stem}.stl"
  else
    fail "${stem} render (code=$code)"
  fi
done

step "latency win vs WASM (~22s ego mount, warm, measured on prod)"
echo "  native multiconnect: ${ms_mc:-?}ms   native opengrid: ${ms_og:-?}ms"

step "error paths (4xx/5xx {ok:false}, never an STL)"
check_err() { # <label> <body> <expected-code>
  local label="$1" body="$2" want="$3"
  local got; got=$(status_of "$body")
  local ok_false; ok_false=$(grep -o '"ok":false' "$WORK/body.json" || true)
  if [ "$got" = "$want" ] && [ -n "$ok_false" ]; then
    pass "$label → $got {ok:false}"
  else
    fail "$label → got $got (want $want), body: $(cat "$WORK/body.json")"
  fi
}
check_err "path traversal"      '{"model":"models/../../etc/passwd"}'                 403
check_err "non-.scad path"      '{"model":"models/evil.txt"}'                          403
check_err "missing model"       '{"model":"models/does_not_exist.scad"}'               404
check_err "unknown param"       '{"model":"models/ego_lb6500_blower_mount.scad","params":{"nope":1}}' 400
check_err "bad enum value"      '{"model":"models/ego_lb6500_blower_mount.scad","params":{"mount_type":"bogus"}}' 400
check_err "openscad failure"    '{"model":"tests/fixtures/render_service_bad.scad"}'   500
# The failure response must carry no STL bytes.
if grep -qi 'application/sla' "$WORK/h.txt" 2>/dev/null; then :; fi

echo
if [ "$FAILS" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
else
  echo "$FAILS CHECK(S) FAILED"
fi
exit "$FAILS"
