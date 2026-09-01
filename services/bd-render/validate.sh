#!/usr/bin/env bash
# End-to-end container smoke for the build123d render service (bead pst-so26).
#
# Builds the image, boots the container, and exercises the full contract
# against the RUNNING service: health, a default GLB render (proves the
# holder builds to a non-empty binary glTF — AC #6), an STL render, and the
# 403/400 validation paths. Exits non-zero on any failure.
#
# Run from the repo root (build context = repo root):
#   services/bd-render/validate.sh
set -euo pipefail

IMAGE="${IMAGE:-stuff-bd-render:validate}"
NAME="bd-render-validate-$$"
PORT="${PORT:-8091}"
ROOT="$(git rev-parse --show-toplevel)"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "==> build image ($IMAGE)"
docker build -f "$ROOT/services/bd-render/Dockerfile" -t "$IMAGE" "$ROOT"

echo "==> run container ($NAME on :$PORT)"
docker run -d --rm --name "$NAME" -p "$PORT:8080" "$IMAGE" >/dev/null

BASE="http://127.0.0.1:$PORT"
echo -n "==> wait for /health"
for _ in $(seq 1 60); do
  if curl -fsS "$BASE/health" >/dev/null 2>&1; then echo " ok"; break; fi
  echo -n "."; sleep 1
done
curl -fsS "$BASE/health" | grep -q '"ok": *true' || { echo "health FAILED"; exit 1; }

fail() { echo "FAIL: $1"; exit 1; }

echo "==> default GLB render (holder-spray-can)"
curl -fsS -X POST "$BASE/render" \
  -H 'content-type: application/json' \
  -d '{"slug":"holder-spray-can"}' -o /tmp/bd-out.glb
[ -s /tmp/bd-out.glb ] || fail "empty GLB"
head -c 4 /tmp/bd-out.glb | grep -q 'glTF' || fail "not a binary glTF (bad magic)"
echo "    GLB bytes: $(wc -c < /tmp/bd-out.glb)"

echo "==> STL render (?format=stl)"
curl -fsS -X POST "$BASE/render?format=stl" \
  -H 'content-type: application/json' \
  -d '{"slug":"holder-spray-can","params":{"d":70}}' -o /tmp/bd-out.stl
[ -s /tmp/bd-out.stl ] || fail "empty STL"
echo "    STL bytes: $(wc -c < /tmp/bd-out.stl)"

check_status() { # method url body expected
  local got
  got=$(curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" \
    -H 'content-type: application/json' -d "$3")
  [ "$got" = "$4" ] || fail "$1 $2 expected $4 got $got"
  echo "    $2 [$3] -> $got"
}

echo "==> validation paths"
check_status POST /render '{"slug":"no-such-model"}' 403
check_status POST /render '{"slug":"holder-spray-can","params":{"nope":1}}' 400
check_status POST /render '{"slug":"holder-spray-can","params":{"d":999}}' 400
check_status POST '/render?format=obj' '{"slug":"holder-spray-can"}' 400

echo "==> ALL CHECKS PASSED"
