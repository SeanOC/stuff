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
    # Quieter, single-line request logging.
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, content_type: str, filename: str) -> None:
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
        parsed = urlparse(self.path)
        if parsed.path != "/render":
            return self._send_json(404, {"ok": False, "errorMessage": "not found"})

        fmt = (parse_qs(parsed.query).get("format", ["glb"])[0]).lower()
        if fmt not in CONTENT_TYPE:
            return self._send_json(
                400, {"ok": False, "errorMessage": f"unknown format {fmt!r}"}
            )

        length = int(self.headers.get("content-length") or 0)
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
