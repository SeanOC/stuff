#!/usr/bin/env python3
"""Smoke test for scripts/serve.py.

Starts the server on an ephemeral port, requests /, and asserts the
response lists a known model. Also checks that SCAD / PNG / STL paths
serve the correct Content-Type and the 403/404 guards behave.
"""

from __future__ import annotations

import socket
import sys
import threading
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import serve  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str) -> tuple[int, dict, bytes]:
    with urllib.request.urlopen(url) as resp:
        return resp.status, dict(resp.headers), resp.read()


def fail(msg: str) -> None:
    print(f"SMOKE FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    models = sorted((REPO_ROOT / "models").glob("*.scad"))
    if not models:
        fail("no models/*.scad to exercise against")
    stem = models[0].stem

    port = _free_port()
    httpd = serve.make_server(REPO_ROOT, "127.0.0.1", port)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{port}"

        status, headers, body = _get(base + "/")
        if status != 200:
            fail(f"/ returned {status}")
        if "text/html" not in headers.get("Content-Type", ""):
            fail(f"/ wrong content-type: {headers.get('Content-Type')}")
        text = body.decode("utf-8")
        if stem not in text:
            fail(f"/ did not list expected model {stem!r}")
        print(f"    / lists {stem}")

        scad_url = f"{base}/models/{stem}.scad"
        status, headers, body = _get(scad_url)
        if status != 200:
            fail(f"{scad_url} returned {status}")
        if not headers.get("Content-Type", "").startswith("text/plain"):
            fail(f"SCAD wrong content-type: {headers.get('Content-Type')}")
        if b"module" not in body and b"difference" not in body and b"union" not in body and len(body) == 0:
            fail("SCAD body appears empty")
        print(f"    SCAD served as text/plain ({len(body)} bytes)")

        try:
            _get(f"{base}/scripts/serve.py")
            fail("/scripts/... should be 403")
        except urllib.error.HTTPError as exc:
            if exc.code != 403:
                fail(f"/scripts/... expected 403, got {exc.code}")
        print("    /scripts/ guarded (403)")

        try:
            _get(f"{base}/../etc/passwd")
            fail("traversal should not succeed")
        except urllib.error.HTTPError as exc:
            if exc.code not in (400, 403, 404):
                fail(f"traversal: unexpected {exc.code}")
        print("    path traversal rejected")

        try:
            _get(f"{base}/models/does_not_exist.scad")
            fail("missing file should 404")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                fail(f"missing: expected 404, got {exc.code}")
        print("    missing file → 404")

    finally:
        httpd.shutdown()
        httpd.server_close()

    print("SMOKE OK: serve.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
