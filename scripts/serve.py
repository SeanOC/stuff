#!/usr/bin/env python3
"""Read-only artifact browser for OpenSCAD workflow outputs.

Serves a list of models from models/<stem>.scad alongside their render
thumbnails (renders/<stem>/*.png) and STL download (exports/<stem>.stl).

Stdlib only. Bind 127.0.0.1 by default — the operator is expected to
forward a port over SSH. No writes, no regen triggers.

    python3 scripts/serve.py                # 127.0.0.1:8765
    python3 scripts/serve.py --port 9000
"""

from __future__ import annotations

import argparse
import html
import http.server
import mimetypes
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

VIEW_ORDER = ("top", "front", "side", "iso")

MIME_OVERRIDES = {
    ".stl": "model/stl",
    ".scad": "text/plain; charset=utf-8",
    ".png": "image/png",
}


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n} B"


def _fmt_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def collect_models(root: Path) -> list[dict]:
    models_dir = root / "models"
    if not models_dir.is_dir():
        return []
    entries = []
    for scad in sorted(models_dir.glob("*.scad")):
        stem = scad.stem
        stl = root / "exports" / f"{stem}.stl"
        render_dir = root / "renders" / stem
        renders: list[dict] = []
        if render_dir.is_dir():
            present = {p.stem: p for p in render_dir.glob("*.png")}
            ordered_stems = list(VIEW_ORDER) + sorted(s for s in present if s not in VIEW_ORDER)
            for v in ordered_stems:
                if v in present:
                    p = present[v]
                    renders.append(
                        {"view": v, "rel": p.relative_to(root).as_posix(), "size": p.stat().st_size}
                    )
        entries.append(
            {
                "stem": stem,
                "scad": {
                    "rel": scad.relative_to(root).as_posix(),
                    "size": scad.stat().st_size,
                    "mtime": scad.stat().st_mtime,
                },
                "stl": (
                    {
                        "rel": stl.relative_to(root).as_posix(),
                        "size": stl.stat().st_size,
                        "mtime": stl.stat().st_mtime,
                    }
                    if stl.is_file()
                    else None
                ),
                "renders": renders,
            }
        )
    return entries


def render_index(root: Path) -> bytes:
    models = collect_models(root)
    parts: list[str] = []
    parts.append(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Artifact browser</title>"
        "<style>"
        "body{font:14px/1.4 system-ui,sans-serif;max-width:1100px;margin:2em auto;padding:0 1em;color:#222}"
        "h1{font-size:1.3em;margin-bottom:.2em}"
        ".meta{color:#666;font-size:.9em;margin-bottom:2em}"
        ".model{border-top:1px solid #ddd;padding:1.2em 0}"
        ".model h2{font-size:1.1em;margin:.2em 0 .6em;font-family:ui-monospace,monospace}"
        ".thumbs{display:flex;flex-wrap:wrap;gap:.6em;margin:.5em 0}"
        ".thumbs a{display:inline-block;text-align:center;font-size:.8em;color:#555;text-decoration:none}"
        ".thumbs img{display:block;max-width:180px;max-height:180px;border:1px solid #ccc;background:#fafafa}"
        ".files{margin:.4em 0;font-size:.92em}"
        ".files a{font-family:ui-monospace,monospace}"
        ".missing{color:#a33;font-style:italic}"
        ".sz{color:#888;font-size:.85em}"
        "</style></head><body>"
    )
    parts.append("<h1>Artifact browser</h1>")
    parts.append(f"<div class='meta'>{len(models)} model(s) under <code>{html.escape(str(root))}</code></div>")

    if not models:
        parts.append("<p class='missing'>No models found in <code>models/</code>.</p>")

    for m in models:
        parts.append("<div class='model'>")
        parts.append(f"<h2>{html.escape(m['stem'])}</h2>")

        if m["renders"]:
            parts.append("<div class='thumbs'>")
            for r in m["renders"]:
                href = "/" + urllib.parse.quote(r["rel"])
                parts.append(
                    f"<a href='{href}' target='_blank'>"
                    f"<img src='{href}' alt='{html.escape(r['view'])}' loading='lazy'>"
                    f"{html.escape(r['view'])}</a>"
                )
            parts.append("</div>")
        else:
            parts.append("<p class='missing'>no renders yet</p>")

        scad = m["scad"]
        scad_href = "/" + urllib.parse.quote(scad["rel"])
        parts.append(
            f"<div class='files'>SCAD: <a href='{scad_href}'>{html.escape(scad['rel'])}</a> "
            f"<span class='sz'>({_fmt_size(scad['size'])}, {_fmt_mtime(scad['mtime'])})</span></div>"
        )

        if m["stl"]:
            stl = m["stl"]
            stl_href = "/" + urllib.parse.quote(stl["rel"])
            parts.append(
                f"<div class='files'>STL: <a href='{stl_href}'>{html.escape(stl['rel'])}</a> "
                f"<span class='sz'>({_fmt_size(stl['size'])}, {_fmt_mtime(stl['mtime'])})</span></div>"
            )
        else:
            parts.append("<div class='files missing'>STL: not exported yet</div>")

        parts.append("</div>")

    parts.append("</body></html>")
    return "".join(parts).encode("utf-8")


class ArtifactHandler(http.server.BaseHTTPRequestHandler):
    server_version = "ArtifactBrowser/1.0"
    root: Path = REPO_ROOT

    ALLOWED_DIRS = ("models", "renders", "exports")

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[serve] %s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        rel = urllib.parse.unquote(parsed.path).lstrip("/")

        if rel == "" or rel == "index.html":
            body = render_index(self.root)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        target = (self.root / rel).resolve()
        try:
            target.relative_to(self.root.resolve())
        except ValueError:
            self.send_error(403, "outside repo root")
            return

        if not target.is_file():
            self.send_error(404, "not found")
            return

        top = rel.split("/", 1)[0]
        if top not in self.ALLOWED_DIRS:
            self.send_error(403, "path not served")
            return

        ext = target.suffix.lower()
        ctype = MIME_OVERRIDES.get(ext) or mimetypes.guess_type(target.name)[0] or "application/octet-stream"

        try:
            data = target.read_bytes()
        except OSError as exc:
            self.send_error(500, f"read failed: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if ext in (".stl", ".scad"):
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
        self.end_headers()
        self.wfile.write(data)


def make_server(root: Path, host: str, port: int) -> http.server.HTTPServer:
    handler = type("BoundHandler", (ArtifactHandler,), {"root": root})
    return http.server.HTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--root", type=Path, default=REPO_ROOT, help="repo root (default: script's repo)")
    args = p.parse_args(argv)

    root = args.root.resolve()
    if not (root / "models").is_dir():
        print(f"warning: {root}/models does not exist", file=sys.stderr)

    httpd = make_server(root, args.host, args.port)
    host, port = httpd.server_address[:2]
    print(f"serving {root} at http://{host}:{port}/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
