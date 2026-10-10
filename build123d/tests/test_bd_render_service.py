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
import re
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = REPO_ROOT / "services" / "bd-render" / "server.py"


def test_dockerfile_copies_registered_model_packages(monkeypatch):
    """Every local package loaded by the registry must ship in the image."""
    build_root = REPO_ROOT / "build123d"
    monkeypatch.syspath_prepend(str(build_root))
    from holders.registry import all_models

    all_models()
    imported_packages = set()
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        try:
            relative = Path(filename).resolve().relative_to(build_root)
        except ValueError:
            continue
        # Keep regular and namespace packages (scripts has no __init__.py),
        # excluding the virtualenv and pytest's top-level test modules.
        package = relative.parts[0]
        # Full-suite collection also imports helpers as tests.mount_contracts
        # and tests.print_audit; these are not service runtime dependencies.
        if package == "tests":
            continue
        if len(relative.parts) > 1 and module.__name__.split(".")[0] == package:
            imported_packages.add(package)

    dockerfile = (SERVER_PATH.parent / "Dockerfile").read_text()
    copied_packages = set(re.findall(
        r"^COPY\s+build123d/(\w+)/?\s+\./\1/?\s*$", dockerfile, re.MULTILINE
    ))
    missing = imported_packages - copied_packages
    assert not missing, f"bd-render image is missing local packages: {sorted(missing)}"


def test_capture_encoding_imports_without_opencv():
    """The render image can load capture's wire contract without OpenCV."""
    subprocess.run(
        [sys.executable, "-c", "import sys; sys.modules['cv2'] = None; import capture.encoding"],
        cwd=REPO_ROOT / "build123d",
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


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


@pytest.mark.parametrize("slug", [
    "holder-spray-can", "holder-cup-lid", "holder-bottle-500ml", "holder-spool-cradle",
])
def test_render_stl_format(base_url, slug):
    status, headers, body = _post(
        base_url, "/render?format=stl", {"slug": slug, "params": {}}
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


def test_cup_lid_pointed_pins_export_watertight(base_url):
    import io
    import trimesh
    status, headers, body = _post(
        base_url, "/render?format=stl", {"slug": "holder-cup-lid", "params": {}}
    )
    assert status == 200, body
    assert headers["content-type"] == "application/sla"
    mesh = trimesh.load_mesh(io.BytesIO(body), file_type="stl")
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert mesh.volume > 0


# --- multi-colour 3MF + build-time rejections (labels L4, pst-egc3j) ------

def test_render_3mf_is_one_object_with_inlay_on_extruder_2(base_url):
    import io
    import zipfile
    status, headers, body = _post(
        base_url, "/render?format=3mf",
        {"slug": "holder-label-card", "params": {"text": "PETG-CF"}},
    )
    assert status == 200, body
    assert headers["content-type"] == "model/3mf"
    with zipfile.ZipFile(io.BytesIO(body)) as package:
        model = package.read("3D/3dmodel.model").decode()
        settings = package.read("Metadata/model_settings.config").decode()
    assert model.count("<item ") == 1
    extruders = re.findall(
        r'<part id="\d+".*?key="name" value="(\w+)".*?key="extruder" value="(\d)"',
        settings, re.S)
    assert extruders == [("base", "1"), ("inlay", "2")]


@pytest.mark.parametrize("style, materials", [("inlaid", 2), ("raised", 0)])
def test_live_label_glb_is_two_colour_for_inlaid_only(base_url, style, materials):
    """pst-5b83s: the live GLB matches the bake (export_glb + preview parts)."""
    import struct
    status, _, body = _post(
        base_url, "/render?format=glb",
        {"slug": "holder-label-card", "params": {"text": "PETG", "text_style": style}},
    )
    assert status == 200, body
    (length,) = struct.unpack("<I", body[12:16])
    doc = json.loads(body[20:20 + length])
    assert len(doc.get("materials", [])) == materials


def test_3mf_for_a_single_colour_model_is_400(base_url):
    status, _h, body = _post(
        base_url, "/render?format=3mf", {"slug": "holder-spray-can"}
    )
    assert status == 400
    assert "not a multi-colour model" in json.loads(body)["errorMessage"]


@pytest.mark.parametrize("fmt", ["glb", "3mf"])
def test_text_below_the_stroke_floor_is_400_with_the_models_message(base_url, fmt):
    # 24 characters pass the param contract but not the inlay stroke floor:
    # the ValueError comes from spec.build(), not resolve_values.
    status, _h, body = _post(
        base_url, f"/render?format={fmt}",
        {"slug": "holder-label-card", "params": {"text": "W" * 24}},
    )
    assert status == 400, body
    message = json.loads(body)["errorMessage"]
    assert "below the" in message and "the longest that fits is" in message


def _run_worker(monkeypatch, slug: str, fmt: str, params: dict, out) -> int:
    import io
    worker_path = REPO_ROOT / "services" / "bd-render" / "render_worker.py"
    spec = importlib.util.spec_from_file_location("bd_render_worker", worker_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["render_worker.py", slug, fmt, str(out)])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(params)))
    return module.main()


@pytest.mark.parametrize("fault", [
    FileNotFoundError("label font missing: /app/fonts/Inter-Bold.ttf"),
    RuntimeError("no font faces in /app/fonts/Inter-Bold.ttf"),
])
def test_a_font_fault_stays_a_5xx(monkeypatch, tmp_path, capsys, fault):
    """Only the model's own input rejections become 400; a broken deploy is 500."""
    import labels.label_text as label_text

    def broken(*_args, **_kwargs):
        raise fault

    monkeypatch.setattr(label_text, "load_font", broken)
    out = tmp_path / "out.glb"
    assert _run_worker(monkeypatch, "holder-label-card", "glb", {"text": "PETG"}, out) == 6
    assert str(fault) in capsys.readouterr().err
    assert not out.exists()
