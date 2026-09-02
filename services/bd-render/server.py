"""Live build123d render service (bead pst-so26, P2a of epic pst-7srz).

The build123d analogue of ``services/render/`` (native OpenSCAD): a tiny
stdlib-only HTTP server that turns ``POST /render {slug, params}`` into a
freshly-built GLB (or STL) for the app's live parametric preview. Unlike
the SCAD path, build123d is Python/OCP and cannot run in a Vercel function
or in the browser, so it lives behind Cloud Run (scale-to-zero — bd traffic
is tweak-only; presets stay baked).

Parity guarantee
----------------
Params are validated through the AUTHORITATIVE Python contract —
``holders.registry.ModelSpec.resolve_values(overrides)`` — exactly the call
the preset bake uses. It fills defaults and raises on unknown keys or
out-of-range values, so the service accepts precisely the inputs the app's
manifest describes (the role ``lib/scad-params/parse.ts`` plays for the
SCAD service).

Response contract (mirrors services/render/server.ts)
-----------------------------------------------------
``POST /render?format=glb|stl``  (default glb)

  request:  { "slug": "holder-spray-can", "params": { "d": 70 } }
  success:  200, body = raw GLB bytes (content-type model/gltf-binary),
            or raw STL bytes (application/sla) when ?format=stl.
  failure:  4xx/5xx, content-type application/json,
            { ok: false, errorMessage, ... }.

  GET /health | /healthz -> 200 {"ok": true}

Status codes
------------
  200  clean build, non-empty mesh
  400  invalid JSON / body shape, unknown-key or out-of-range param,
       unknown ?format
  403  unknown / non-app-listed slug
  413  request body over 64 KiB
  500  build/export failure, or an empty/zero-volume mesh (fail-loud)
  504  render exceeded the hard per-request timeout

Isolation & the hard timeout
-----------------------------
The actual build+export runs in a one-shot ``render_worker.py`` subprocess
so a pathological in-range combo cannot hang the server: the parent bounds
it with ``subprocess.run(timeout=…)`` and kills it on overrun. Param
validation (slug + resolve_values) happens in THIS process first, so 4xx
inputs never pay for a subprocess.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
BUILD123D_ROOT = Path(
    os.environ.get("BD_BUILD123D_ROOT") or (HERE.parents[1] / "build123d")
).resolve()
sys.path.insert(0, str(BUILD123D_ROOT))

WORKER = str(HERE / "render_worker.py")

# A {slug, params} body is tiny; anything large is a mistake or abuse.
MAX_BODY_BYTES = 64 * 1024
# Hard wall-clock cap on one render. In-range combos build in well under a
# second locally; the cap only guards a pathological OCP hang.
RENDER_TIMEOUT_S = float(os.environ.get("BD_RENDER_TIMEOUT", "90"))
PORT = int(os.environ.get("PORT", "8080"))

# Bound concurrent OCP renders. Each POST spawns a heavy build123d/OCP
# subprocess (hundreds of MB resident); ThreadingHTTPServer accepts
# connections without limit and the Cloud Run deploy sets no per-instance
# request concurrency (default 80), so an unguarded burst of concurrent
# renders could OOM a 4Gi instance. This semaphore caps how many renders run
# at once IN THIS PROCESS — excess requests queue as cheap blocked threads
# rather than stacking heavy subprocesses. Pair with `--concurrency` on the
# Cloud Run deploy for defence in depth (see services/bd-render/README.md).
RENDER_CONCURRENCY = max(1, int(os.environ.get("BD_RENDER_CONCURRENCY", "2")))
_RENDER_SLOTS = threading.BoundedSemaphore(RENDER_CONCURRENCY)

CONTENT_TYPE = {"glb": "model/gltf-binary", "stl": "application/sla"}

# Exit codes from render_worker.py that map to a 4xx rather than 5xx.
_WORKER_BADREQ = {3: 403, 4: 400}


def _app_slugs() -> set[str]:
    """App-listed (non-smoke) slugs the service will build."""
    from holders.registry import all_models

    return {m.slug for m in all_models() if not m.is_smoke}


def _resolve_or_error(slug: str, params: dict) -> str | None:
    """Return an error string if slug/params are invalid, else None.

    Runs the authoritative registry contract in-process so bad input gets
    the right 4xx before we ever spawn a worker.
    """
    from holders.registry import all_models

    spec = next(
        (m for m in all_models() if not m.is_smoke and m.slug == slug), None
    )
    if spec is None:
        return "slug"  # sentinel -> 403
    try:
        spec.resolve_values(params)
    except ValueError as e:
        return str(e)  # -> 400
    return None


class Handler(BaseHTTPRequestHandler):
    # Set once a response has started, so the last-resort 500 in do_POST
    # never tries to write a second response over a half-sent one (parity
    # with server.ts's `!res.headersSent` guard).
    _responded = False

    # Quieter, single-line request logging.
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status: int, payload: dict) -> None:
        self._responded = True
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, content_type: str, filename: str) -> None:
        self._responded = True
        self.send_response(200)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(data)))
        self.send_header(
            "content-disposition", f'attachment; filename="{filename}"'
        )
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/health", "/healthz"):
            return self._send_json(200, {"ok": True})
        self._send_json(404, {"ok": False, "errorMessage": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        # Last-resort guard: an unexpected error must return a structured 500,
        # never drop the connection (parity with services/render/server.ts).
        try:
            self._handle_post()
        except Exception:  # noqa: BLE001 - deliberately catch-all at the boundary
            sys.stderr.write(traceback.format_exc())
            if not self._responded:
                try:
                    self._send_json(
                        500, {"ok": False, "errorMessage": "internal error"}
                    )
                except Exception:  # noqa: BLE001 - the socket may already be gone
                    pass

    def _handle_post(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/render":
            return self._send_json(404, {"ok": False, "errorMessage": "not found"})

        fmt = (parse_qs(parsed.query).get("format", ["glb"])[0]).lower()
        if fmt not in CONTENT_TYPE:
            return self._send_json(
                400, {"ok": False, "errorMessage": f"unknown format {fmt!r}"}
            )

        # Guard the content-length parse: a non-numeric or negative header must
        # yield a structured 400, not a ValueError that drops the connection.
        raw_len = self.headers.get("content-length")
        if raw_len is None:
            length = 0
        else:
            try:
                length = int(raw_len)
            except ValueError:
                return self._send_json(
                    400, {"ok": False, "errorMessage": "invalid content-length header"}
                )
            if length < 0:
                return self._send_json(
                    400, {"ok": False, "errorMessage": "invalid content-length header"}
                )
        if length > MAX_BODY_BYTES:
            return self._send_json(
                413,
                {"ok": False, "errorMessage": f"body exceeds {MAX_BODY_BYTES} bytes"},
            )
        raw = self.rfile.read(length) if length else b""

        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send_json(400, {"ok": False, "errorMessage": "invalid JSON body"})
        if not isinstance(body, dict) or not isinstance(body.get("slug"), str):
            return self._send_json(
                400, {"ok": False, "errorMessage": "body.slug must be a string"}
            )
        params = body.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return self._send_json(
                400, {"ok": False, "errorMessage": "body.params must be an object"}
            )
        slug = body["slug"]

        # In-process validation → correct 4xx without spawning a worker.
        err = _resolve_or_error(slug, params)
        if err == "slug":
            return self._send_json(
                403, {"ok": False, "errorMessage": f"unknown model slug: {slug}"}
            )
        if err is not None:
            return self._send_json(400, {"ok": False, "errorMessage": err})

        self._render(slug, params, fmt)

    def _render(self, slug: str, params: dict, fmt: str) -> None:
        with tempfile.TemporaryDirectory(prefix="bd-render-") as d:
            out = os.path.join(d, f"out.{fmt}")
            # Hold a render slot only for the heavy OCP subprocess; the cheap
            # read/send below runs unbounded. A blocked caller waits here
            # rather than stacking another subprocess on a memory-tight box.
            with _RENDER_SLOTS:
                try:
                    proc = subprocess.run(
                        [sys.executable, WORKER, slug, fmt, out],
                        input=json.dumps(params).encode("utf-8"),
                        capture_output=True,
                        timeout=RENDER_TIMEOUT_S,
                    )
                except subprocess.TimeoutExpired:
                    return self._send_json(
                        504,
                        {
                            "ok": False,
                            "errorMessage": f"render exceeded {RENDER_TIMEOUT_S:.0f}s timeout",
                        },
                    )

            if proc.returncode != 0:
                status = _WORKER_BADREQ.get(proc.returncode, 500)
                return self._send_json(status, _worker_error(proc.stderr))

            try:
                with open(out, "rb") as f:
                    data = f.read()
            except OSError:
                return self._send_json(
                    500, {"ok": False, "errorMessage": "render produced no output"}
                )
            if not data:
                return self._send_json(
                    500, {"ok": False, "errorMessage": "render produced an empty file"}
                )

            self._send_bytes(data, CONTENT_TYPE[fmt], f"{slug}.{fmt}")


def _worker_error(stderr: bytes) -> dict:
    """Parse the worker's last JSON error line; fall back to raw stderr."""
    text = stderr.decode("utf-8", "replace").strip()
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "errorMessage" in obj:
                    obj.setdefault("ok", False)
                    return obj
            except json.JSONDecodeError:
                pass
    return {"ok": False, "errorMessage": text[-500:] or "render failed"}


def make_server(port: int = PORT) -> ThreadingHTTPServer:
    # Threading so a long render never blocks a health probe.
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


def main() -> int:
    # Fail fast if the registry can't be imported (bad env / missing bake).
    slugs = sorted(_app_slugs())
    httpd = make_server(PORT)
    print(
        f"bd-render service listening on :{PORT} "
        f"(build123d={BUILD123D_ROOT}, models={slugs}, timeout={RENDER_TIMEOUT_S:.0f}s)",
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
