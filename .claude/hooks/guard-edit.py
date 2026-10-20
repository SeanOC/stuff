#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit) guard: protected paths for worker sessions.

Blocks writes to env files, ~/.claude/projects (mayor memory), .gc/runtime/secrets, and
.github/workflows/ (mayor-owned; carve-out = $GC_CITY/.gc/runtime/guard-allow/workflow-edit-<rig>,
touched by the mayor when a bead carries an explicit workflow-edit authorization).
Paths are normalized (.. segments, ~ and $HOME, relative to the hook's cwd) before matching.
"""
import json
import os
import re
import sys
from pathlib import Path

CITY = Path(os.environ.get("GC_CITY") or Path.home() / "gc-pilot/city")
ALLOWED_ENV_SUFFIXES = (".example", ".sample", ".template", ".dist")


def rig_name(cwd):
    rig = os.environ.get("GC_RIG") or os.environ.get("RIG")
    if rig:
        return rig
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    m = re.search(r"/\.gc/worktrees/([^/]+)/", root)
    return m.group(1) if m else re.sub(r"^rig-", "", os.path.basename(root.rstrip("/")))


def main():
    try:
        payload = json.load(sys.stdin)
        ti = payload.get("tool_input", {})
        raw = ti.get("file_path") or ti.get("path") or ti.get("notebook_path") or ""
        cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    except Exception:
        print("BLOCKED by guard-edit (parse): hook payload unreadable", file=sys.stderr)
        sys.exit(2)
    if not raw:
        return
    p = raw.replace("$HOME", str(Path.home())).replace("${HOME}", str(Path.home()))
    if p == "~" or p.startswith("~/"):
        p = str(Path.home()) + p[1:]
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    p = os.path.normpath(p)
    try:
        real = os.path.realpath(p)
    except Exception:
        real = p
    base = os.path.basename(p)
    for cand in {p, real}:
        b = os.path.basename(cand)
        if b == ".env" or (b.startswith(".env.") and not b.endswith(ALLOWED_ENV_SUFFIXES)):
            print("BLOCKED by guard-edit: never write env files from a worker session.", file=sys.stderr)
            sys.exit(2)
        if "/.claude/projects/" in cand + "/" or "/.gc/runtime/secrets" in cand + "/":
            print("BLOCKED by guard-edit: mayor memory and runtime secrets are not writable from a worker.", file=sys.stderr)
            sys.exit(2)
        if "/.github/workflows/" in cand + "/" or cand.endswith("/.github/workflows"):
            rig = rig_name(cwd)
            if not (CITY / ".gc/runtime/guard-allow" / f"workflow-edit-{rig}").exists():
                print("BLOCKED by guard-edit: .github/workflows/ is mayor-owned. If your bead carries an explicit "
                      "workflow-edit authorization, mail the mayor to set the carve-out marker "
                      f"(guard-allow/workflow-edit-{rig}).", file=sys.stderr)
                sys.exit(2)


if __name__ == "__main__":
    main()
