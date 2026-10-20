#!/usr/bin/env python3
"""PreToolUse(Bash) guard for gc-launched Claude Code worker sessions.

Deterministic blocks for the worker prompt templates' NEVER rules (mayor, 2026-10-20).
Exit 2 = block (stderr is fed back to the agent); exit 0 = allow. Hook JSON on stdin.

The command is tokenized with shlex (quoted prose is never mistaken for options),
split into simple statements on ; & | newlines ( ) and backticks, wrapper programs
(env, command, nohup, timeout, xargs, npx, pnpm dlx, bash -c, ...) are unwrapped, and
every statement is checked. Shell expansions are NOT evaluated: an unparseable sleep
argument or a redirect to an expanded variable is treated conservatively (blocked).

Operator carve-outs: the mayor touches $GC_CITY/.gc/runtime/guard-allow/<marker>
(push-main, vercel-env, long-sleep, watch, workflow-edit-<rig>). force-push, sudo,
admin merges, status/protection API writes, secret reads and bead assignment have NO
carve-out: the matching permissions.deny rules apply regardless of a marker.
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CITY = Path(os.environ.get("GC_CITY") or Path.home() / "gc-pilot/city")
SEPARATORS = ";&|\n()`<>"
WRAPPERS = {"command", "builtin", "exec", "nohup", "time", "nice", "ionice", "env", "xargs",
            "timeout", "eval", "npx", "pnpx", "bunx", "uvx", "doas", "chroot"}
WRAPPER_OPT_ARITY = {
    "timeout": {"-k", "--kill-after", "-s", "--signal"},
    "ionice": {"-c", "--class", "-n", "--classdata", "-p", "--pid", "-P", "--pgid", "-u", "--uid"},
    "nice": {"-n", "--adjustment"},
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string", "--block-signal", "--default-signal",
            "--ignore-signal", "-a", "--argv0"},
    "xargs": {"-I", "-n", "-P", "-L", "-s", "-d", "-a", "-E", "--max-args", "--max-procs", "--replace",
              "--delimiter", "--arg-file", "--eof", "--max-chars", "--max-lines"},
    "nohup": set(), "command": set(), "builtin": set(), "exec": {"-a"}, "time": {"-f", "-o"},
    "chroot": {"--userspec", "--groups"}, "doas": {"-u", "-C"},
}
RUNNERS = {"pnpm", "npm", "yarn", "bun", "uv", "poetry", "pipx", "npx"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                       "--super-prefix", "--config-env", "--list-cmds"}
PUSH_OPTS_WITH_ARG = {"-o", "--push-option", "--repo", "--receive-pack", "--exec", "--recurse-submodules"}
WRITE_PROGRAMS = {"cp", "mv", "install", "rsync", "scp", "ln", "tee", "truncate", "dd", "touch", "rm",
                  "sed", "perl", "chmod", "chown", "shred", "unlink", "rmdir", "mkdir", "patch", "git"}
TEXT_OPTIONS = {"--notes", "--append-notes", "--description", "-d", "--title", "-t", "--body-file",
                "--design", "--design-file", "--acceptance", "--reason", "-r", "--close-reason",
                "-m", "--message", "--body", "-b", "--comment", "-c", "--label", "-l", "--labels",
                "--set-metadata", "--unset-metadata", "--defer", "--subject", "-s"}
ALLOWED_ENV_SUFFIXES = (".example", ".sample", ".template", ".dist")
cwd = os.getcwd()
blocked = []  # (rule, message, carveout)


def marker(name):
    return CITY / ".gc/runtime/guard-allow" / name


def block(rule, message, carveout=True):
    if carveout and marker(rule).exists():
        return
    blocked.append((rule, message, carveout))


def rig_name():
    rig = os.environ.get("GC_RIG") or os.environ.get("RIG")
    if rig:
        return rig
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    m = re.search(r"/\.gc/worktrees/([^/]+)/", root)
    if m:
        return m.group(1)
    return re.sub(r"^rig-", "", os.path.basename(root.rstrip("/")))


def expand(token):
    t = token.replace("$HOME", str(Path.home())).replace("${HOME}", str(Path.home()))
    if t == "~" or t.startswith("~/"):
        t = str(Path.home()) + t[1:]
    return t


def norm(token):
    """Normalized absolute path for a path-looking token (expansions left as-is)."""
    t = expand(token)
    if not t or t.startswith("-"):
        return ""
    if not os.path.isabs(t):
        t = os.path.join(cwd, t)
    return os.path.normpath(t)


def is_env_file(path):
    base = os.path.basename(path)
    if base == ".env":
        return True
    return base.startswith(".env.") and not base.endswith(ALLOWED_ENV_SUFFIXES)


def is_secret_path(path):
    if not path:
        return False
    if is_env_file(path):
        return True
    if "/.claude/projects/" in path + "/" or path.endswith("/.claude/projects"):
        return True
    return "/.gc/runtime/secrets" in path + "/"


def is_workflow_path(path):
    return bool(path) and ("/.github/workflows/" in path + "/" or path.endswith("/.github/workflows"))


def statements(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=SEPARATORS)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    words, out = [], []
    for word in lexer:
        if word and all(ch in SEPARATORS for ch in word):
            if ">" in word:  # redirection operator: keep it in the statement, target follows
                words.append(word)
            elif "<" in word:
                words.append("<")
            else:
                if words:
                    out.append(words)
                words = []
        else:
            words.append(word)
    if words:
        out.append(words)
    return out


def check_paths(words, rig):
    """Secret reads anywhere; writes (redirects + write programs) into .github/workflows."""
    program = os.path.basename(words[0]) if words else ""
    if program == "git" and any(a in words[1:] for a in ("apply", "am")) and \
            not any(a in words[1:] for a in ("--check", "--stat", "--numstat", "--summary", "--show-current-patch")):
        block(f"workflow-edit-{rig}", "git apply/am can rewrite .github/workflows from patch contents the guard "
              "cannot inspect; use --check/--stat to inspect, or edit files directly")
    i = 0
    while i < len(words):
        w = words[i]
        if ">" in w and all(ch in SEPARATORS for ch in w):
            target = words[i + 1] if i + 1 < len(words) else ""
            if w.endswith("&") and target.isdigit():
                i += 2
                continue
            p = norm(target)
            if is_secret_path(p):
                block("secret-write", f"never write {target} from a worker session", carveout=False)
            elif is_workflow_path(p):
                block(f"workflow-edit-{rig}", ".github/workflows/ is mayor-owned; a bead with an explicit "
                      "workflow-edit authorization gets a carve-out marker from the mayor")
            elif "$" in target or "`" in target:
                block("secret-write", f"redirect target '{target}' is a shell expansion the guard cannot "
                      "resolve; write to a literal path", carveout=False)
            i += 2
            continue
        p = norm(w)
        if is_secret_path(p) and program not in {"echo", "printf", "test", "["}:
            block("secret-read", f"'{w}' is a protected secret/memory path (env files, ~/.claude/projects, "
                  ".gc/runtime/secrets); workers use the sanitized env the worktree setup provides", carveout=False)
        elif is_workflow_path(p) and program in WRITE_PROGRAMS:
            if program == "git" and not any(s in words[1:] for s in ("rm", "mv", "checkout", "restore", "apply", "am")):
                pass
            elif program in {"sed", "perl"} and not any(a == "--in-place" or (a.startswith("-") and not a.startswith("--") and "i" in a[1:]) for a in words[1:]):
                pass
            else:
                block(f"workflow-edit-{rig}", ".github/workflows/ is mayor-owned; a bead with an explicit "
                      "workflow-edit authorization gets a carve-out marker from the mayor")
        elif program == "dd" and w.startswith(("of=", "if=")):
            q = norm(w[3:])
            if is_secret_path(q):
                block("secret-write" if w.startswith("of=") else "secret-read",
                      f"dd {w[:3]}{w[3:]} touches a protected secret path", carveout=False)
            elif is_workflow_path(q) and w.startswith("of="):
                block(f"workflow-edit-{rig}", ".github/workflows/ is mayor-owned (dd of=)")
        i += 1


def unwrap(words):
    """Strip env assignments and wrapper programs so the real program is words[0]."""
    changed = True
    while changed and words:
        changed = False
        while words and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", words[0]):
            words = words[1:]
        if not words:
            return words
        program = os.path.basename(words[0])
        if program in {"sudo", "doas"}:
            block("sudo", "no privilege escalation in worker sessions", carveout=False)
            words = [a for a in words[1:] if not a.startswith("-")]
            changed = True
        elif program in WRAPPERS:
            rest = words[1:]
            arity = WRAPPER_OPT_ARITY.get(program, set())
            while rest and rest[0].startswith("-") and rest[0] != "--":
                opt = rest.pop(0)
                if "=" in opt and opt.startswith("--"):
                    continue
                if opt in arity and rest:
                    rest.pop(0)
                elif program == "nice" and re.fullmatch(r"-\d+", opt):
                    pass
                elif len(opt) > 2 and not opt.startswith("--") and opt[:2] in arity:
                    pass  # -k1 / -n10 style: value attached
            if rest and rest[0] == "--":
                rest.pop(0)
            if program == "timeout" and rest:
                rest = rest[1:]  # the duration operand
            words = rest
            changed = True
        elif program in RUNNERS and len(words) > 1:
            rest = words[1:]
            if rest and rest[0] in {"dlx", "exec", "x", "run"}:
                rest = rest[1:]
            while rest and rest[0].startswith("-"):
                rest.pop(0)
            if rest and rest[0] in {"vercel", "gh", "git", "bd", "gc", "sleep", "sudo"}:
                words = rest
                changed = True
    return words


def current_branch(path):
    try:
        out = subprocess.run(["git", "-C", path, "symbolic-ref", "--short", "-q", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip()
    except Exception:
        return ""


def check_git(args):
    repo = cwd
    while args and args[0].startswith("-"):
        opt = args.pop(0)
        if opt in GIT_GLOBAL_WITH_ARG and args:
            val = args.pop(0)
            if opt == "-C":
                repo = os.path.join(repo, expand(val))
        elif opt.startswith("-C") and len(opt) > 2:
            repo = os.path.join(repo, expand(opt[2:]))
    if not args or args[0] not in {"push", "send-pack"}:
        return
    refspecs, remote = [], None
    rest = args[1:]
    while rest:
        a = rest.pop(0)
        if a == "--":
            refspecs.extend(rest)
            break
        if a.startswith("-"):
            if a in {"-f", "--force", "--force-with-lease", "--force-if-includes"} or \
                    a.startswith(("--force-with-lease=", "--force-if-includes=")) or \
                    (not a.startswith("--") and "f" in a[1:]):
                block("force-push", "force-pushing is never allowed from a worker", carveout=False)
            if a in {"--all", "--mirror", "--branches"}:
                block("push-main", "pushing every branch (--all/--mirror) includes main; push your feature branch")
            if a in PUSH_OPTS_WITH_ARG and rest:
                rest.pop(0)
            if a in {"-d", "--delete"}:
                pass  # the following refspecs are checked as destinations below
            continue
        if remote is None:
            remote = a
        else:
            refspecs.append(a)
    for spec in refspecs:
        if spec in {":", "+:"} or "*" in spec:
            block("push-main", f"matching/wildcard refspec '{spec}' can advance main; push one named feature branch")
            continue
        if spec.startswith("+"):
            block("force-push", "a '+' refspec is a force push", carveout=False)
            spec = spec[1:]
        dst = spec.rsplit(":", 1)[-1] if ":" in spec else spec
        dst = re.sub(r"^refs/(heads|tags|remotes/[^/]+)/", "", dst)
        if dst == "HEAD":
            dst = current_branch(repo)
        if dst in {"main", "master"}:
            block("push-main", "workers push feature branches only; main merges through the review gate")
    if not refspecs:
        if current_branch(repo) in {"main", "master"}:
            block("push-main", "you are on main; workers push feature branches only")


def check_gh(args):
    if args[:2] == ["pr", "merge"] and "--admin" in args:
        block("admin-merge", "never bypass branch protection", carveout=False)
    if args[:1] in (["pr"], ["run"]) and ("--watch" in args or args[:2] == ["run", "watch"]):
        block("watch", "no --watch loops; check once and end your turn (the mayor merges)")
    if args[:1] == ["api"]:
        method = "GET"
        endpoint = ""
        value_opts = {"-H", "--header", "--hostname", "-p", "--preview", "-q", "--jq", "-t", "--template",
                      "--cache", "-i", "--include"} - {"-i", "--include"}
        it = iter(args[1:])
        for a in it:
            if a in {"-X", "--method"}:
                method = (next(it, "") or "").upper()
            elif a.startswith("--method="):
                method = a.split("=", 1)[1].upper()
            elif a in {"-f", "-F", "--field", "--raw-field", "--input"}:
                next(it, None)
                method = method if method != "GET" else "POST"
            elif a.startswith(("-f", "-F", "--field=", "--raw-field=", "--input=")) and method == "GET":
                method = "POST"
            elif a in value_opts:
                next(it, None)
            elif a.startswith("-") and not a.startswith("--") and len(a) > 2 and a[:2] in value_opts:
                pass  # -Hvalue attached form
            elif not a.startswith("-") and not endpoint:
                endpoint = a
        if method != "GET" and re.search(r"/statuses/|/check-runs|/protection|/rulesets", endpoint):
            block("protected-api", "never POST commit statuses/check-runs or edit branch protection "
                  "(it pollutes the SHA / bypasses the gate)", carveout=False)
        if endpoint == "graphql" and any(re.search(r"(create|update|delete)BranchProtectionRule|createCommitStatus", a)
                                         for a in args):
            block("protected-api", "never edit branch protection or post statuses via GraphQL", carveout=False)


def check_sleep(args, total):
    for a in args:
        if a.startswith("-"):
            continue
        m = re.fullmatch(r"\+?(\d+(?:\.\d*)?|\.\d+)([smhd]?)", a)
        if not m:
            block("long-sleep", f"sleep '{a}' is not a literal number the guard can bound; use a literal "
                  "under 30 s or end your turn and let the next event resume you")
            continue
        total += float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
    return total


def check_bd(args):
    if args[:1] not in (["create"], ["update"]):
        return
    it = iter(args[1:])
    for a in it:
        if " " in a:
            continue
        if a in TEXT_OPTIONS:
            next(it, None)
        elif a == "--":
            return
        elif a == "--assignee" or a.startswith(("--assignee=", "-a")) and not a.startswith("--a"):
            block("bd-assignee", "never set assignees; the claim hook owns assignment", carveout=False)
        elif a.startswith("--assignee"):
            block("bd-assignee", "never set assignees; the claim hook owns assignment", carveout=False)


def check_find(words):
    for key in ("-exec", "-execdir", "-ok", "-okdir"):
        while key in words:
            i = words.index(key)
            tail = words[i + 1:]
            end = next((j for j, a in enumerate(tail) if a in {";", "+"}), len(tail))
            check_statement(tail[:end])
            words = tail[end:]


def check_statement(words, state=None):
    state = state if state is not None else {"sleep": 0.0, "loop": False}
    rig = rig_name()
    if any(w in {"for", "while", "until"} for w in words[:1]):
        state["loop"] = True
    check_paths(words, rig)
    words = [w for w in words if w not in {"!", "{", "}", "then", "do", "else", "elif", "fi", "done", "esac", "in"}]
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", words[0]):
        words = words[1:]
    if words and os.path.basename(words[0]) in {"eval", "source", "."} and len(words) > 1:
        if os.path.basename(words[0]) == "eval":
            for st in statements(" ".join(words[1:])):
                check_statement(st, state)
            return
    words = unwrap(list(words))
    if not words:
        return
    program = os.path.basename(words[0])
    args = words[1:]
    if program in SHELLS and "-c" in args:
        script = args[args.index("-c") + 1] if args.index("-c") + 1 < len(args) else ""
        for st in statements(script):
            check_statement(st, state)
        return
    if program in {"git", "git-push"}:
        check_git(["push"] + args if program == "git-push" else list(args))
    elif program == "gh":
        check_gh(list(args))
    elif program == "vercel" and args[:1] in (["env"], ["logs"], ["pull"]):
        block("vercel-env", "production env/logs are mayor-only; use the sanitized env the worktree setup provides")
    elif program == "sleep":
        state["sleep"] = check_sleep(args, state["sleep"])
        if state["loop"]:
            block("long-sleep", "no sleep inside a shell loop; end your turn and let the next event resume you")
    elif program == "watch":
        block("watch", "no watch loops; check once and end your turn")
    elif program in {"tail", "journalctl"} and any(a in {"-f", "-F"} or a.startswith("--follow") or (a.startswith("-") and not a.startswith("--") and ("f" in a[1:] or "F" in a[1:])) for a in args):
        block("watch", "no follow loops; read a bounded slice and end your turn")
    elif program == "find":
        check_find(list(args))
    elif program == "gc" and args[:1] == ["bd"]:
        check_bd(list(args[1:]))
    elif program == "bd":
        check_bd(list(args))
    if state["sleep"] >= 30:
        block("long-sleep", f"total literal sleep in this command is {state['sleep']:.0f} s (limit 30); "
              "end your turn and let the next event resume you")
        state["sleep"] = -1e9


def main():
    global cwd
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    except Exception:
        print("BLOCKED by guard-bash (parse): hook payload unreadable", file=sys.stderr)
        sys.exit(2)
    if not isinstance(command, str) or not command.strip():
        return
    try:
        parsed = statements(command)
    except ValueError as e:
        print(f"BLOCKED by guard-bash (parse): could not tokenize the command ({e}); fix the quoting", file=sys.stderr)
        sys.exit(2)
    state = {"sleep": 0.0, "loop": False}
    for st in parsed:
        check_statement(st, state)
    if blocked:
        seen = set()
        for rule, message, carveout in blocked:
            if rule in seen:
                continue
            seen.add(rule)
            print(f"BLOCKED by guard-bash ({rule}): {message}", file=sys.stderr)
            if carveout:
                print(f"  Genuinely required? Mail the mayor; a one-off carve-out marker is {marker(rule)}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
