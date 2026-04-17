#!/usr/bin/env python3
"""Persist an authored .scad body and delegate to scad-render.

NL→SCAD is Claude's job; this script only handles file I/O, versioning,
and orchestration. Reads SCAD from --body-file or stdin.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3].parent
MODELS_DIR = REPO_ROOT / "models"
RENDER_SCRIPT = REPO_ROOT / ".claude" / "skills" / "scad-render" / "scripts" / "render.py"

_VERSION_RE = re.compile(r"^(?P<stem>.+)_(?P<num>\d{3})$")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    body = _read_body(args.body_file)
    if not body.strip():
        _emit_fail("empty SCAD body")
        return 2

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = _resolve_path(args.name, versioned=args.versioned)
    model_path.write_text(body if body.endswith("\n") else body + "\n")

    render_payload = None
    outer_verdict = "authored_ok"
    rc = 0
    if not args.no_render:
        render_rc, render_payload = _invoke_render(
            model_path, defines=args.defines, angles=args.angles
        )
        if render_rc != 0:
            outer_verdict = "render_failed"
            rc = render_rc

    out = {
        "verdict": outer_verdict,
        "model": str(model_path.relative_to(REPO_ROOT))
        if model_path.is_relative_to(REPO_ROOT)
        else str(model_path),
        "versioned": args.versioned,
        "render": render_payload,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return rc


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Author .scad + render")
    p.add_argument("--name", required=True)
    p.add_argument("--body-file", dest="body_file")
    p.add_argument("--versioned", action="store_true")
    p.add_argument("--no-render", action="store_true", dest="no_render")
    p.add_argument("-D", dest="defines", action="append", default=[])
    p.add_argument("--angles")
    return p.parse_args(argv)


def _read_body(body_file: str | None) -> str:
    if body_file:
        return Path(body_file).read_text()
    return sys.stdin.read()


def _resolve_path(name: str, versioned: bool) -> Path:
    if not versioned:
        return MODELS_DIR / f"{name}.scad"
    next_num = _next_version(name)
    return MODELS_DIR / f"{name}_{next_num:03d}.scad"


def _next_version(name: str) -> int:
    existing = list(MODELS_DIR.glob(f"{name}_[0-9][0-9][0-9].scad"))
    nums: list[int] = []
    for p in existing:
        m = _VERSION_RE.match(p.stem)
        if m and m.group("stem") == name:
            nums.append(int(m.group("num")))
    return (max(nums) + 1) if nums else 1


def _invoke_render(
    model: Path, defines: list[str], angles: str | None
) -> tuple[int, dict]:
    cmd = [sys.executable, str(RENDER_SCRIPT), "--model", str(model)]
    for d in defines:
        cmd += ["-D", d]
    if angles:
        cmd += ["--angles", angles]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {
            "verdict": "render_failed",
            "error": f"render.py emitted non-JSON stdout: {proc.stdout[:200]!r}",
            "stderr": proc.stderr[:500],
        }
    return proc.returncode, payload


def _emit_fail(error: str) -> None:
    out = {"verdict": "authoring_failed", "error": error}
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
