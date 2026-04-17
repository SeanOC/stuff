#!/usr/bin/env python3
"""List or add vendored OpenSCAD libraries.

`list`: parses libs/README.md and emits the library catalog as JSON.
`add`:  shallow-clones a git repo into libs/<name>, appends a stub
         entry to libs/README.md for the caller to fill in.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3].parent
LIBS_DIR = REPO_ROOT / "libs"
README = LIBS_DIR / "README.md"

_H2_SPLIT_RE = re.compile(r"^## ", re.MULTILINE)
_USE_LINE_RE = re.compile(r"`(use\s+<[^>]+>;?|include\s+<[^>]+>;?)`")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.cmd == "list":
        return _cmd_list()
    if args.cmd == "add":
        return _cmd_add(args.name, args.url)
    raise SystemExit(f"unknown subcommand: {args.cmd!r}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Manage libs/")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List vendored libraries")

    add = sub.add_parser("add", help="Clone a new library and stub README")
    add.add_argument("--name", required=True, help="short name; becomes libs/<name>/")
    add.add_argument("--url", required=True, help="git clone URL")

    return p.parse_args(argv)


def _cmd_list() -> int:
    if not README.exists():
        _emit({"verdict": "list_failed", "error": f"{README} not found"})
        return 2
    libs = _parse_readme(README.read_text())
    _emit({"verdict": "listed_ok", "libs": libs})
    return 0


def _parse_readme(text: str) -> list[dict]:
    parts = _H2_SPLIT_RE.split(text)
    libs: list[dict] = []
    for chunk in parts[1:]:  # skip preamble
        first_line, _, body = chunk.partition("\n")
        name = first_line.split("—")[0].split("(")[0].strip().rstrip("`").strip()
        if not name:
            continue
        summary = _extract_summary(body)
        examples = _USE_LINE_RE.findall(chunk)
        libs.append({
            "name": name,
            "summary": summary,
            "use_examples": examples[:5],
        })
    return libs


def _extract_summary(body: str) -> str:
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("-", "*", "#", "|")):
            continue
        # First prose paragraph's first line.
        return s
    return ""


def _cmd_add(name: str, url: str) -> int:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        _emit({"verdict": "add_failed", "error": f"invalid name: {name!r}"})
        return 2

    dest = LIBS_DIR / name
    if dest.exists():
        _emit({"verdict": "add_failed", "error": f"{dest} already exists"})
        return 2

    LIBS_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--depth=1", url, str(dest)],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        _emit({
            "verdict": "add_failed",
            "error": f"git clone exited {proc.returncode}: {proc.stderr.strip()[:200]}",
        })
        return 3

    sha = _head_sha(dest)
    _append_stub(name, url, sha)

    _emit({
        "verdict": "added_ok",
        "name": name,
        "path": str(dest.relative_to(REPO_ROOT)) if dest.is_relative_to(REPO_ROOT) else str(dest),
        "commit": sha,
        "readme_updated": README.exists(),
    })
    return 0


def _head_sha(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _append_stub(name: str, url: str, sha: str) -> None:
    stub = (
        f"\n## {name}\n\n"
        f"- Path: `libs/{name}`\n"
        f"- Commit: `{sha}`\n"
        f"- Upstream: {url}\n"
        f"- Summary: _TODO — fill in one-line capability summary._\n"
        f"- Use examples:\n"
        f"  - _TODO_\n"
        f"  - _TODO_\n"
        f"  - _TODO_\n"
    )
    existing = README.read_text() if README.exists() else "# Vendored OpenSCAD Libraries\n"
    if not existing.endswith("\n"):
        existing += "\n"
    README.write_text(existing + stub)


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
