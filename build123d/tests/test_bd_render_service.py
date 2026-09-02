"""Integration tests for the live build123d render service (bead pst-so26).

The service lives in ``services/bd-render/`` (sibling tree) but is tested
from the build123d suite because that is the only pytest job wired into CI
(``.github/workflows/bd123.yml``) and it carries the OCP env the service
builds against. Adding a dedicated ``services/`` CI job needs a workflow
edit that is out of scope for this bead — see services/bd-render/README.md.

Each test boots the real ThreadingHTTPServer on an ephemeral port and hits
it over HTTP, so the full path (validation → worker subprocess → export)
is exercised end-to-end. A holder builds in ~0.2 s, so this stays fast.
"""
from __future__ import annotations

import importlib.util
import json
import socket
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = REPO_ROOT / "services" / "bd-render" / "server.py"


def _load_server():
    spec = importlib.util.spec_from_file_location("bd_render_server", SERVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def _running(module):
    """Boot a given server module on an ephemeral port; yield its base URL."""
    httpd = module.make_server(0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def base_url():
    with _running(_load_server()) as url:
        yield url


def _post(base_url: str, path: str, body):
    data = json.dumps(body).encode("utf-8") if body is not None else b""
    req = urllib.request.Request(
        base_url + path, data=data, method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def _get(base_url: str, path: str):
    try:
        with urllib.request.urlopen(base_url + path) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# --- health -------------------------------------------------------------

@pytest.mark.parametrize("path", ["/health", "/healthz"])
def test_health(base_url, path):
    status, body = _get(base_url, path)
    assert status == 200
    assert json.loads(body) == {"ok": True}


# --- happy path ---------------------------------------------------------

def test_render_glb_default_format(base_url):
    status, headers, body = _post(
        base_url, "/render", {"slug": "holder-spray-can"}
    )
    assert status == 200, body
    assert headers["content-type"] == "model/gltf-binary"
    # Binary glTF magic — proves it's a real GLB, not an error page.
    assert body[:4] == b"glTF"
    assert len(body) > 1000


def test_render_stl_format(base_url):
    status, headers, body = _post(
        base_url, "/render?format=stl", {"slug": "holder-spray-can", "params": {}}
    )
    assert status == 200, body
    assert headers["content-type"] == "application/sla"
    assert len(body) > 1000


def test_render_accepts_in_range_override(base_url):
    # d has a declared range (30–120); 70 is in-range and must build.
    status, _headers, body = _post(
        base_url, "/render", {"slug": "holder-spray-can", "params": {"d": 70.0}}
    )
    assert status == 200, body
    assert body[:4] == b"glTF"


# --- validation (4xx) ---------------------------------------------------

def test_unknown_slug_is_403(base_url):
    status, _h, body = _post(base_url, "/render", {"slug": "no-such-model"})
    assert status == 403
    assert json.loads(body)["ok"] is False


def test_smoke_model_is_not_app_listed_403(base_url):
    # Smoke artifacts are registered but excluded from the app manifest;
    # the service must not build them.
    status, _h, _body = _post(
        base_url, "/render", {"slug": "smoke-opengrid-tile-1x1"}
    )
    assert status == 403


def test_unknown_param_is_400(base_url):
    status, _h, body = _post(
        base_url, "/render", {"slug": "holder-spray-can", "params": {"nope": 1}}
    )
    assert status == 400
    assert "nope" in json.loads(body)["errorMessage"]


def test_out_of_range_param_is_400(base_url):
    # d max is 120; 999 is out of range → registry.resolve_values raises.
    status, _h, body = _post(
        base_url, "/render", {"slug": "holder-spray-can", "params": {"d": 999.0}}
    )
    assert status == 400
    assert json.loads(body)["ok"] is False


def test_unknown_format_is_400(base_url):
    status, _h, _body = _post(
        base_url, "/render?format=obj", {"slug": "holder-spray-can"}
    )
    assert status == 400


def test_missing_slug_is_400(base_url):
    status, _h, _body = _post(base_url, "/render", {"params": {}})
    assert status == 400


def test_invalid_json_is_400(base_url):
    req = urllib.request.Request(
        base_url + "/render", data=b"{not json", method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    assert status == 400


def test_oversize_body_is_413(base_url):
    big = {"slug": "holder-spray-can", "params": {"pad": "x" * (64 * 1024 + 10)}}
    status, _h, _body = _post(base_url, "/render", big)
    assert status == 413


# --- hardening (bead pst-mmxw) ------------------------------------------

def _raw_post(base_url: str, headers: str, body: bytes = b"") -> str:
    """Send a hand-built request so we control the exact header bytes (urllib
    would recompute Content-Length). Returns the response's status line."""
    u = urlparse(base_url)
    with socket.create_connection((u.hostname, u.port), timeout=5) as s:
        s.sendall(headers.encode("ascii") + b"\r\n" + body)
        chunk = s.recv(1024)
    return chunk.decode("latin-1").splitlines()[0]


def test_malformed_content_length_is_400(base_url):
    """A non-numeric Content-Length must return a structured 400, not drop the
    connection on a ValueError (bead pst-mmxw AC#2)."""
    status_line = _raw_post(
        base_url,
        "POST /render HTTP/1.0\r\n"
        "Host: x\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: not-a-number\r\n"
        "Connection: close\r\n",
    )
    assert "400" in status_line, status_line


def test_negative_content_length_is_400(base_url):
    status_line = _raw_post(
        base_url,
        "POST /render HTTP/1.0\r\n"
        "Host: x\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: -5\r\n"
        "Connection: close\r\n",
    )
    assert "400" in status_line, status_line


def test_unexpected_error_returns_structured_500(monkeypatch):
    """An unexpected error inside handling must yield a generic 500 with a JSON
    body (parity with services/render/server.ts), not a dropped connection
    (bead pst-mmxw AC#3)."""
    module = _load_server()
    # Inject a fault on the in-process validation path (a non-ValueError the
    # handler does not expect) so the top-level do_POST guard is exercised.
    def boom(_slug, _params):
        raise RuntimeError("injected fault")

    monkeypatch.setattr(module, "_resolve_or_error", boom)
    with _running(module) as url:
        status, headers, body = _post(url, "/render", {"slug": "holder-spray-can"})
    assert status == 500
    assert headers["content-type"] == "application/json"
    doc = json.loads(body)
    assert doc["ok"] is False and doc["errorMessage"] == "internal error"


def test_concurrent_renders_are_bounded_and_all_succeed(base_url):
    """The render semaphore must serialize heavy renders without deadlocking or
    dropping any — every concurrent request still returns a valid GLB (bead
    pst-mmxw AC#1)."""
    results: list[int] = []
    lock = threading.Lock()

    def fire():
        status, _h, body = _post(base_url, "/render", {"slug": "holder-spray-can"})
        with lock:
            results.append((status, body[:4]))

    threads = [threading.Thread(target=fire) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert len(results) == 6
    assert all(status == 200 and magic == b"glTF" for status, magic in results), results
