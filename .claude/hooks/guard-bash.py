#!/usr/bin/env python3
"""PreToolUse(Bash) guard for gc-launched Claude Code worker sessions.

Deterministic blocks for the worker prompt templates' NEVER rules (mayor, 2026-10-20).
Exit 2 = block (stderr is fed back to the agent); exit 0 = allow. Hook JSON on stdin.

The command is tokenized with shlex (quoted prose is never mistaken for options),
split into simple statements on ; & | newlines ( ) and backticks, wrapper programs
(env, command, nohup, timeout, xargs, npx, pnpm dlx, bash -c, ...) are unwrapped, and
every statement is checked. Command substitutions ($(...) and backticks, including the
quoted forms echo "$(...)") are checked separately, once each. Comments and quoted
heredoc bodies are literal; unquoted heredocs are scanned for substitutions only.
Other shell expansions are NOT evaluated: an unparseable sleep
argument or a redirect to an expanded variable is treated conservatively (blocked).

Operator carve-outs: the mayor touches $GC_CITY/.gc/runtime/guard-allow/<marker>
(push-main, vercel-env, long-sleep, watch, workflow-edit-<rig>). force-push, sudo,
admin merges, status/protection API writes, secret reads and bead assignment have NO
carve-out: the matching permissions.deny rules apply regardless of a marker.
"""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CITY = Path(os.environ.get("GC_CITY") or Path.home() / "gc-pilot/city")
SEPARATORS = ";&|\n()`<>"
LITERAL_SEPARATORS = {"(": "\x00lparen\x00", ")": "\x00rparen\x00", ";": "\x00semicolon\x00"}  # quoted/escaped: arguments
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
    "nohup": set(), "command": set(), "builtin": set(), "exec": {"-a"}, "time": {"-f", "--format", "-o", "--output"},
    "chroot": {"--userspec", "--groups"}, "doas": {"-u", "-C"},
}
RUNNERS = {"pnpm", "npm", "yarn", "bun", "uv", "poetry", "pipx", "npx"}
RUNNER_OPT_ARITY = {  # package-runner options that take a SEPARATE value (so the value is never taken for the executable)
    "npx": {"-p", "--package", "-c", "--call", "--shell", "--node-options", "--loglevel", "--registry", "--cache", "--prefix",
            "-w", "--workspace", "--userconfig", "--script-shell"},
    "npm": {"-p", "--package", "-c", "--call", "-w", "--workspace", "--prefix", "-C", "--loglevel", "--registry", "--cache",
            "--userconfig", "--script-shell", "--node-options", "--shell"},
    "pnpm": {"--filter", "-F", "-C", "--dir", "--package", "-p", "--loglevel", "--reporter", "--shell-mode", "--config"},
    "yarn": {"--cwd", "-p", "--package", "--cache-folder", "--mutex"},
    "bun": {"--package", "-p", "--cwd", "--shell", "--config", "-c"},
    "uv": {"--with", "--with-requirements", "--with-editable", "--python", "-p", "--directory", "--project", "--from",
           "--index", "--extra", "--group", "--only-group", "--cache-dir", "--config-file", "--env-file", "--exclude-newer"},
    "pipx": {"--spec", "--python", "--pip-args", "--index-url", "-i"},
    "poetry": {"-C", "--directory", "-P", "--project"},
}
WRAPPER_OPT_ARITY.update({"npx": RUNNER_OPT_ARITY["npx"], "pnpx": RUNNER_OPT_ARITY["pnpm"], "bunx": RUNNER_OPT_ARITY["bun"],
                          "uvx": RUNNER_OPT_ARITY["uv"]})  # the *x runners are unwrapped as wrappers: same value-taking options
WRAPPER_READ_FILE_OPTIONS = {"xargs": {"-a", "--arg-file"}}  # wrapper options whose value is a file the wrapper READS
# … and every value a runner-wrapper option takes, in any spelling (`uvx --env-file .env`, `npx --userconfig=.env`)
WRAPPER_READ_FILE_OPTIONS.update({w: WRAPPER_OPT_ARITY[w] for w in ("npx", "pnpx", "bunx", "uvx")})
WRAPPER_WRITE_FILE_OPTIONS = {"time": {"-o", "--output"}}  # … or WRITES
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                       "--super-prefix", "--config-env", "--list-cmds"}
GREP_PROGRAMS = {"grep", "egrep", "fgrep", "rg", "ag", "ack"}
GREP_VALUE_OPTIONS = {"-A", "-B", "-C", "-m", "-e", "-f", "--include", "--exclude", "--exclude-dir", "-t", "-g",
                      "-j", "--type", "--type-not", "-d", "-D", "--max-count", "--context", "--regexp", "--file", "--glob",
                      "--iglob", "--max-depth", "--threads", "--encoding", "--pre", "--replace", "--max-filesize",
                      "--sort", "--sortr", "--after-context", "--before-context", "--max-columns", "--path-separator"}
RG_VALUE_OPTIONS = {"-T", "-M", "-E", "-r", "--color", "--colour", "--type-add", "--dfa-size-limit", "--regex-size-limit",
                    "--context-separator", "--field-context-separator", "--field-match-separator", "--ignore-file",
                    "--max-columns", "--engine", "--generate", "--hostname-bin", "--path-separator"}
GREP_PATH_VALUE_OPTIONS = {"-f", "--file", "--pre", "--ignore-file"}  # these values ARE files (checked); the rest are text
# value-taking SHORT options per program, so a short cluster can be parsed left-to-right: the first one consumes the
# rest of the cluster (or the next word) as its value, and an `f`/`e` sitting INSIDE that value is not a fresh flag
# (codex on #387: rg `-rabcde` is --replace=abcde, so `.env` after it is a path operand, not -e's pattern file).
# `f` is the pattern-FILE option (its value is a path), `e` the pattern (text); every other letter here is a
# text/number value that is consumed and ignored. For grep/ag/ack the set is the letters that take a value in BOTH
# GNU grep and ugrep (the worker shell's `grep`), so a letter only one of them consumes still lets the scan reach a
# real `f` and fail closed (e.g. ugrep's `-Xf.env` reads .env; GNU's `-X` would eat it — the guard blocks).
GREP_SHORT_VALUE = {
    "rg": set("ABCdEefgjMmrtT"),
    "grep": set("ABCDdefm"), "egrep": set("ABCDdefm"), "fgrep": set("ABCDdefm"),
    "ag": set("ABCdefm"), "ack": set("ABCdefm"),
}
COPY_PROGRAMS = {"cp", "mv", "rsync", "install"}
WATCH_W_PROGRAMS = {"vitest", "tsc", "tsc-alias"}  # programs whose `-w` means --watch (jest's -w is --maxWorkers: NOT here)
CHECKOUT_VALUE_OPTIONS = {"-b", "-B", "--orphan", "-s", "--source", "--conflict", "--pathspec-from-file"}
# git accepts any UNAMBIGUOUS prefix of a long option (`--work`==`--worktree`, `--har`==`--hard`,
# `--no-dry`==`--no-dry-run`), so the restore/reset/clean/checkout security checks below must compare against
# the canonical name, not the exact spelling (codex on #387). Each set lists the subcommand's real long options
# so a prefix git itself would call ambiguous stays ambiguous (and therefore unexpanded) here too.
GIT_SUBCOMMAND_OPTIONS = {
    "reset": {"--quiet", "--soft", "--mixed", "--hard", "--merge", "--keep", "--patch",
              "--intent-to-add", "--recurse-submodules", "--pathspec-from-file", "--pathspec-file-nul"},
    "restore": {"--source", "--staged", "--worktree", "--quiet", "--progress", "--ours", "--theirs",
                "--merge", "--conflict", "--ignore-unmerged", "--ignore-skip-worktree-bits",
                "--recurse-submodules", "--overlay", "--no-overlay", "--pathspec-from-file",
                "--pathspec-file-nul"},
    "clean": {"--force", "--interactive", "--dry-run", "--no-dry-run", "--quiet", "--exclude"},
    "checkout": {"--quiet", "--detach", "--force", "--merge", "--conflict", "--orphan", "--ours", "--theirs",
                 "--track", "--guess", "--overlay", "--no-overlay", "--patch", "--ignore-skip-worktree-bits",
                 "--ignore-other-worktrees", "--recurse-submodules", "--overwrite-ignore", "--progress",
                 "--pathspec-from-file", "--pathspec-file-nul"},
}
STASH_READONLY = {"list", "show", "drop", "clear", "branch", "create", "store", "apply", "pop"}
BD_GLOBAL_WITH_ARG = {"--db", "-C", "--config", "--actor", "--rig", "-r", "--city"}
DESTRUCTIVE_PROGRAMS = {"rm", "rmdir", "mv", "unlink", "shred"}
VERCEL_GLOBAL_WITH_ARG = {"--scope", "-S", "--token", "-t", "--cwd", "--local-config", "-A", "-e", "--env", "-b", "--build-env",
                          "--global-config", "-Q", "--team", "-T"}
GH_ROOT_WITH_ARG = {"-R", "--repo", "--hostname"}
PUSH_OPTS_WITH_ARG = {"-o", "--push-option", "--repo", "--receive-pack", "--exec", "--recurse-submodules"}
READ_PROGRAMS = {"cat", "head", "tail", "less", "more", "grep", "rg", "awk", "cut", "sort", "xxd", "od", "strings",
                 "base64", "source", ".", "python3", "python", "node", "wc", "jq", "yq", "diff", "file", "stat", "ls",
                 "find", "sed", "perl", "vim", "vi", "nano", "code", "open", "xdg-open", "curl", "wget", "env"}
WRITE_PROGRAMS = {"cp", "mv", "install", "rsync", "scp", "ln", "tee", "truncate", "dd", "touch", "rm",
                  "sed", "perl", "chmod", "chown", "shred", "unlink", "rmdir", "mkdir", "patch", "git", "tar", "unzip", "zip"}
FILE_VALUE_OPTIONS = {"--body-file", "--design-file", "--notes-file", "--template-file", "-F", "--field"}
TEXT_OPTIONS = {"--notes", "--append-notes", "--description", "-d", "--title", "-t",
                "--design", "--acceptance", "--reason", "-r", "--close-reason",
                "-m", "--message", "--body", "-b", "--comment", "-c", "--label", "-l", "--labels",
                "--set-metadata", "--unset-metadata", "--defer", "--subject", "-s"}
ALLOWED_ENV_SUFFIXES = (".example", ".sample", ".template", ".dist")
cwd = os.getcwd()
ROOT = cwd  # the worktree root the hook was invoked for (git -C changes cwd for path resolution, never ROOT)
SPLIT_STRINGS = []  # env -S payloads, re-parsed as commands
CWD_UNKNOWN = False  # a literal `cd $X` happened earlier in the command: relative operands cannot be resolved
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
    t = t.replace("${PWD}", cwd).replace("$PWD", cwd)
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
    """`.env`, `.env.<anything>` and `<name>.env` (pulled prod envs such as /tmp/prod.env) are secret;
    the template suffixes (.example/.sample/.template/.dist) are not."""
    base = os.path.basename(path)
    if base == ".env" or base.endswith(".env"):
        return True
    return base.startswith(".env.") and not base.endswith(ALLOWED_ENV_SUFFIXES)


def workflows_dirty(include_untracked):
    """True when the protected worktree has uncommitted changes under .github/workflows (a pathless `git stash`
    would take them out of the worktree). Any failure to ask git (not a repo, timeout) counts as clean."""
    args = ["git", "-C", cwd, "status", "--porcelain", "--untracked-files=" + ("all" if include_untracked else "no"),
            "--", os.path.join(ROOT, ".github/workflows")]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=5)
    except Exception:
        return False
    return out.returncode == 0 and bool(out.stdout.strip())


def restore_is_staged_only(words):
    """Whether restore targets only the index; an explicit source may still change index content.
    Only options BEFORE the first `--` count: a `--staged` after it is a pathspec, not the mode (codex on #387)."""
    pre = []
    for a in words[2:]:
        if a == "--":
            break
        if a.startswith("-"):
            pre.append(a)
    opts = set(pre)
    return words[:2] == ["git", "restore"] and bool(opts & {"-S", "--staged"}) \
        and not opts & {"-W", "--worktree"}


def git_pathspecs(words, git_sub):
    """Indices of the operands that are PATHSPECS of git checkout/restore/stash (the ones that rewrite the worktree).
    checkout: operands after `--`, every operand after the first, and a first operand that cannot be a ref (starts with
    `.`, `/` or `~`). restore: every operand (unless --staged without --worktree: index only). stash push/bare: operands
    after `--` or after `push`; `save` takes a message, the read-only subcommands take none."""
    ops, after, skip = [], False, False
    for j in range(2, len(words)):
        a = words[j]
        if skip:
            skip = False
            continue
        if not after and a == "--":
            after = True
            continue
        if not after and a.startswith("-"):
            if a in CHECKOUT_VALUE_OPTIONS or (git_sub == "stash" and a in {"-m", "--message"}):
                skip = True
            continue
        ops.append((j, a, after))
    if git_sub == "restore":
        if restore_is_staged_only(words):
            return set()
        return {j for j, _, _ in ops}
    if git_sub == "checkout":
        if any(a in {"-b", "-B", "--orphan", "--detach", "-d"} for a in words[2:]):
            return set()
        idx = {j for j, _, aft in ops if aft}
        plain = [(j, a) for j, a, aft in ops if not aft]
        idx.update(j for j, _ in plain[1:])
        if plain and plain[0][1].startswith((".", "/", "~")):
            idx.add(plain[0][0])
        return idx
    # stash
    if ops and not ops[0][2] and ops[0][1] in STASH_READONLY | {"save", "push"}:
        sub_, ops = ops[0][1], ops[1:]
        if sub_ in STASH_READONLY or sub_ == "save":
            return None  # read-only / message operand: nothing to check, and no dirty-tree check either
    return {j for j, _, _ in ops}


def is_workflow_ancestor(path):
    """True when removing/moving `path` would take .github/workflows with it (cwd, .github, or any parent)."""
    if not path:
        return False
    workflows = os.path.normpath(os.path.join(ROOT, ".github/workflows"))
    return path != workflows and workflows.startswith(path.rstrip("/") + "/")


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


def literal_separators(command):
    """An escaped or quoted `(`, `)`, `;` is an ARGUMENT (find's grouping and -exec terminator), never an operator,
    but shlex's punctuation_chars splits on it all the same, so `find . \\( … \\) -delete` reached check_find as
    `find .` (codex on ia-next #387). Swap it for a placeholder word that statements() restores."""
    out, quote, i = [], "", 0
    while i < len(command):
        ch = command[i]
        if ch == "\\" and quote != "'" and i + 1 < len(command):
            nxt = command[i + 1]
            out.append(LITERAL_SEPARATORS[nxt] if not quote and nxt in LITERAL_SEPARATORS else command[i:i + 2])
            i += 2
            continue
        if ch in "'\"" and (not quote or quote == ch):
            quote = "" if quote else ch
        elif quote and ch in LITERAL_SEPARATORS:
            ch = LITERAL_SEPARATORS[ch]
        out.append(ch)
        i += 1
    return "".join(out)


def statements(command):
    lexer = shlex.shlex(literal_separators(command), posix=True, punctuation_chars=SEPARATORS)
    lexer.commenters = ""  # shell_parts already removed comments at shell word boundaries
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
            for sep, placeholder in LITERAL_SEPARATORS.items():
                word = word.replace(placeholder, sep)
            words.append(word)
    if words:
        out.append(words)
    return out


def heredoc_word(text, start):
    """Read a heredoc delimiter with quote removal, retaining whether it was quoted."""
    i = start
    while i < len(text) and text[i] in " \t":
        i += 1
    begin, quote, quoted = i, "", False
    while i < len(text):
        ch = text[i]
        if not quote and ch in " \t\r\n;&|()<>":
            break
        if ch == "\\" and quote != "'":
            quoted = True
            i += 2
            continue
        if ch in "'\"" and (not quote or quote == ch):
            quoted = True
            quote = "" if quote else ch
        i += 1
    words = shlex.split(text[begin:i])
    if not words:
        raise ValueError("missing heredoc delimiter")
    return i, words[0], quoted


def shell_parts(text, *, heredoc=False):
    """Separate executable shell text from literal text and command substitutions.

    Each substitution gets its own quote context. Replace its occurrence in the
    parent with an opaque expansion so shlex cannot inspect/count the body again,
    while redirect targets and sleep operands still fail closed on unknown values.
    This is a lexer for the guard's supported forms, not a complete shell parser.
    """
    n = len(text)

    def scan(i, closing=False, literal=False):
        command, children, pending = [], [], []
        quote, depth, word_start = "", 0, True
        while i < n:
            ch = text[i]
            if quote == "'":
                command.append(ch)
                if ch == "'":
                    quote = ""
                i += 1
                continue
            if ch == "\\" and (not (quote or literal) or text[i + 1:i + 2] in "$`\\\"\n"):
                escaped = text[i:i + 2]
                if escaped != "\\\n":
                    command.append(escaped)
                    word_start = False
                i += 2
                continue
            if text.startswith("$(", i):
                parts, i = scan(i + 2, closing=True)
                children.extend(parts)
                command.append("${__guard_substitution__}")
                word_start = False
                continue
            if ch == "`":
                j = i + 1
                while j < n and text[j] != "`":
                    j += 2 if text[j] == "\\" else 1
                if j >= n:
                    raise ValueError("unclosed backtick substitution")
                body = re.sub(r"\\([$`\\])", r"\1", text[i + 1:j])
                children.extend(shell_parts(body))
                command.append("${__guard_substitution__}")
                word_start = False
                i = j + 1
                continue
            if not literal:
                if ch in "'\"" and (not quote or quote == ch):
                    quote = "" if quote else ch
                elif not quote:
                    if ch == "#" and word_start:
                        end = text.find("\n", i)
                        i = n if end == -1 else end
                        continue
                    if text.startswith("<<<", i):  # here-string, not a heredoc
                        command.append("<<<")
                        i += 3
                        word_start = True
                        continue
                    if text.startswith("<<", i):
                        strip_tabs = text.startswith("<<-", i)
                        end, delimiter, quoted = heredoc_word(text, i + 2 + strip_tabs)
                        pending.append((delimiter, quoted, strip_tabs))
                        command.append(text[i:end])
                        i = end
                        word_start = False
                        continue
                    if ch == "\n" and pending:
                        command.append(ch)
                        i += 1
                        for delimiter, quoted, strip_tabs in pending:
                            body = []
                            while i < n:
                                end = text.find("\n", i)
                                end = n if end == -1 else end
                                line = text[i:end]
                                i = min(end + 1, n)
                                # In expanding heredocs, join escaped newlines
                                # before checking for the closing delimiter.
                                while (not quoted and end < n
                                       and (len(line) - len(line.rstrip("\\"))) % 2):
                                    end = text.find("\n", i)
                                    end = n if end == -1 else end
                                    line = line[:-1] + text[i:end]
                                    i = min(end + 1, n)
                                if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                                    break
                                body.append(line + "\n")
                            if not quoted:
                                children.extend(shell_parts("".join(body), heredoc=True))
                        pending.clear()
                        word_start = True
                        continue
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        if closing and depth == 0:
                            return ["".join(command)] + children, i + 1
                        depth -= 1
            command.append(ch)
            word_start = not quote and ch in " \t\r\n;&|()<>"
            i += 1
        if closing:
            raise ValueError("unclosed command substitution")
        return ([] if literal else ["".join(command)]) + children, i

    return scan(0, literal=heredoc)[0]


def strip_condition_keywords(words):
    """`if git push origin main; then …` / `while sudo true; do …` / `until gh pr merge --admin 1; do …`: the
    condition IS a command — drop the leading keyword(s) so it is checked like any other statement (gate round 11).
    `for` keeps its word: `for i in …` names no command."""
    while words and words[0] in {"if", "elif", "while", "until", "!", "{"}:
        words = words[1:]
    return words


def check_script(text, state):
    """Check every statement of a shell text plus every command substitution it executes."""
    try:
        parts = shell_parts(text)
    except ValueError as e:
        block("parse", f"could not tokenize '{text[:40]}' ({e}); fix the quoting", carveout=False)
        return
    for part in parts:
        try:
            parsed = statements(part)
        except ValueError as e:
            block("parse", f"could not tokenize '{part[:40]}' ({e}); fix the quoting", carveout=False)
            continue
        for st in parsed:
            check_statement(st, state)
            apply_chdir(st, state)


def apply_chdir(words, state):
    """A literal `cd`/`pushd`/`popd` statement changes the cwd that LATER statements resolve relative paths
    against (ia-next gate round 9: `cd .github/workflows && touch evil.yml`). Conservative: a cd inside `( … )`
    carries too. An unresolvable target (`cd $DIR`) marks the cwd unknown for the rest of the command."""
    global cwd, CWD_UNKNOWN
    words = [w for w in words if w not in {"!", "{", "}", "then", "do", "else", "elif", "fi", "done", "esac"}]
    words = strip_condition_keywords(words)
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", words[0]):
        words = words[1:]
    while len(words) > 1 and os.path.basename(words[0]) in {"command", "builtin"}:
        # `command [-p] [--] cd …` / `builtin cd …` change the cwd exactly like `cd`; consume the wrapper's
        # options and `--` the way unwrap does, so `command -p cd` is still recognized (codex on #387)
        words = words[1:]
        while words and words[0].startswith("-") and words[0] != "--":
            words = words[1:]
        while words and words[0] == "--":
            words = words[1:]
    if not words:
        return
    program = os.path.basename(words[0])
    if program not in {"cd", "pushd", "popd"}:
        return
    stack = state.setdefault("dirs", [])
    if program == "popd":
        if stack:
            cwd, CWD_UNKNOWN = stack.pop()
        return
    target = next((a for a in words[1:] if not a.startswith("-") or a == "-"), None)
    prev = state.get("prev_dir")
    if program == "pushd":
        stack.append((cwd, CWD_UNKNOWN))
    else:
        state["prev_dir"] = (cwd, CWD_UNKNOWN)
    if target is None:
        if program == "cd":
            cwd, CWD_UNKNOWN = str(Path.home()), False
        return
    if target == "-":
        if prev is not None:
            cwd, CWD_UNKNOWN = prev
        return
    t = expand(target)
    if "$" in t or "`" in t:
        cwd, CWD_UNKNOWN = os.path.normpath(os.path.join(cwd, t)), True
        return
    cwd = os.path.normpath(t if os.path.isabs(t) else os.path.join(cwd, t))


def git_expand_opts(words, subcommand):
    """Expand git's unambiguous long-option abbreviations to the canonical spelling for `subcommand`
    (git accepts `--work` for `--worktree`, `--har` for `--hard`), so the security checks match real
    behavior. Short options, `--opt=value`, `--`, and ambiguous/unknown prefixes are returned unchanged;
    token count never changes, so pathspec indices stay valid."""
    candidates = GIT_SUBCOMMAND_OPTIONS.get(subcommand)
    if not candidates:
        return list(words)
    out, after_sep = [], False
    for w in words:
        if after_sep:  # everything past `--` is a pathspec, never an option to expand (codex on #387)
            out.append(w)
            continue
        if w == "--":
            after_sep = True
            out.append(w)
            continue
        if w.startswith("--") and "=" not in w and w not in candidates:
            matches = [c for c in candidates if c.startswith(w)]
            if len(matches) == 1:
                out.append(matches[0])
                continue
        out.append(w)
    return out


def check_paths(words, rig):
    """Secret reads anywhere; writes (redirects + write programs) into .github/workflows."""
    program = os.path.basename(words[0]) if words else ""
    if program == "git" and any(a in words[1:] for a in ("apply", "am")) and \
            not any(a in words[1:] for a in ("--check", "--stat", "--numstat", "--summary", "--show-current-patch")):
        block(f"workflow-edit-{rig}", "git apply/am can rewrite .github/workflows from patch contents the guard "
              "cannot inspect; use --check/--stat to inspect, or edit files directly")
    if program == "patch" and not any(a in {"--dry-run", "--check"} or a.startswith("--dry-run") for a in words[1:]):
        block(f"workflow-edit-{rig}", "patch applies contents the guard cannot inspect (it can rewrite .github/workflows); "
              "use --dry-run to inspect, or edit files directly")
    git_sub = ""
    if program == "git":
        rest, base = words[1:], cwd
        while rest and rest[0].startswith("-"):
            opt = rest.pop(0)
            if opt in GIT_GLOBAL_WITH_ARG and rest:
                val = rest.pop(0)
                if opt == "-C":
                    base = os.path.join(base, expand(val))
            elif opt.startswith("-C") and len(opt) > 2:
                base = os.path.join(base, expand(opt[2:]))
        git_sub = rest[0] if rest else ""
        if os.path.normpath(base) != os.path.normpath(cwd):
            saved = cwd
            globals()["cwd"] = os.path.normpath(base)
            try:
                return check_paths(["git"] + rest, rig)
            finally:
                globals()["cwd"] = saved
        words = ["git"] + rest
        if git_sub:  # normalize unambiguous long-option abbreviations before the restore/reset/clean checks
            words = ["git", git_sub] + git_expand_opts(rest[1:], git_sub)
    destructive = program in DESTRUCTIVE_PROGRAMS or (program == "git" and git_sub in {"rm", "mv", "clean"})
    # git checkout/restore/stash WITH an ancestor pathspec (., .github, ..) rewrite .github/workflows the way rm/mv
    # would; a PATHLESS stash takes an uncommitted workflow change out of the worktree, so it is blocked only while
    # the workflow tree is dirty (ia-next gate round 8)
    restore_idx = set()
    if program == "git" and git_sub in {"checkout", "restore", "stash"}:
        spec = git_pathspecs(words, git_sub)
        if spec is not None:
            restore_idx = spec
        if git_sub == "stash" and spec is not None and not spec and \
                workflows_dirty(any(a in {"-u", "--include-untracked", "-a", "--all"} or
                                    (a.startswith("-") and not a.startswith("--") and ("u" in a[1:] or "a" in a[1:]))
                                    for a in words[2:])):
            block(f"workflow-edit-{rig}", "git stash without a pathspec would take your uncommitted .github/workflows "
                  "change out of the worktree (mayor-owned); stash the paths you mean, e.g. git stash push -- src/")
    # Only the default HEAD source merely unstages a named workflow (ghastly #42 gate): `--source`/`-s` writes THAT
    # commit's version into the index. The worktree-only ancestor policy in git_pathspecs is unchanged.
    unstage_only = restore_is_staged_only(words) and not any(
        a == "--source" or a.startswith("--source=") or
        (a.startswith("-") and not a.startswith("--") and "s" in a[1:])
        for a in words[2:]
    )
    if program == "git" and git_sub == "reset":
        # worktree-updating reset modes rewrite .github/workflows: from another commit when a ref is named, or by
        # discarding an uncommitted workflow change (ia-next gate round 10). --soft/--mixed touch the index only.
        mode = next((a for a in words[2:] if a in {"--hard", "--merge", "--keep"}), None)
        if mode:
            ops = []
            for a in words[2:]:
                if a == "--":
                    break
                if not a.startswith("-"):
                    ops.append(a)
            if ops and ops[0] != "HEAD":
                block(f"workflow-edit-{rig}", f"git reset {mode} {ops[0]} replaces .github/workflows with that commit's "
                      "version (mayor-owned); use --soft/--mixed, or restore the paths you mean")
            elif workflows_dirty(False):
                block(f"workflow-edit-{rig}", f"git reset {mode} discards your uncommitted .github/workflows change "
                      "(mayor-owned); commit it, or stash the paths you mean")
    grep_values = GREP_VALUE_OPTIONS | (RG_VALUE_OPTIONS if program == "rg" else set())
    # mv: with -t/--target-directory the last operand is a source, not the destination (gs-geb1)
    mv_positional_destination = program == "mv" and not any(
        a == "--target-directory" or a.startswith("--target-directory=")
        or (a.startswith("-") and not a.startswith("--") and "t" in a[1:]) for a in words[1:])
    if program in COPY_PROGRAMS:
        # a directory copied/moved INTO .github/ lands at dest/basename(src): that is where the policy applies
        positional, target = [], None
        it = iter(words[1:])
        for a in it:
            if a in {"-t", "--target-directory"}:
                target = next(it, None)
            elif a.startswith("--target-directory="):
                target = a.split("=", 1)[1]
            elif a.startswith("-") or (">" in a and all(ch in SEPARATORS for ch in a)):
                continue
            else:
                positional.append(a)
        if target is None and len(positional) >= 2:
            target, positional = positional[-1], positional[:-1]
        if target is not None:
            for src in positional:
                eff = os.path.join(norm(target), os.path.basename(src.rstrip("/")))
                if is_workflow_path(eff):
                    block(f"workflow-edit-{rig}", f"'{src}' would land at {os.path.relpath(eff, cwd)} (.github/workflows is mayor-owned)")
    git_prose = program == "git" and git_sub in {"commit", "tag", "notes", "merge"}
    pattern_pending = program in GREP_PROGRAMS and not any(
        a in {"-e", "-f", "--files", "--type-list", "--file", "--regexp"} or a.startswith(("--regexp=", "--file="))
        or (a.startswith("-") and not a.startswith("--") and len(a) > 2 and ("e" in a[1:] or "f" in a[1:]))
        for a in words[1:])
    if program == "git" and git_sub == "clean":
        # exclusion patterns (-e/--exclude) are NOT pathspecs; dry-run may sit inside a cluster (-fdn) — ghastly gs-28ql
        rest, dry_run = [], False
        options = iter(words[2:])
        for opt in options:
            if opt == "--":
                rest.extend(options)
                break
            if opt in {"-e", "--exclude"}:
                next(options, None)
            elif opt == "--dry-run":
                dry_run = True
            elif opt == "--no-dry-run":
                dry_run = False
            elif opt.startswith("-") and not opt.startswith("--"):
                for j, flag in enumerate(opt[1:], 1):
                    if flag == "e":
                        if j == len(opt) - 1:
                            next(options, None)
                        break  # the rest of the cluster is the exclusion pattern
                    if flag == "n":
                        dry_run = True
            elif not opt.startswith("-"):
                rest.append(opt)
        if not rest and not dry_run:
            block(f"workflow-edit-{rig}", "git clean without a pathspec defaults to the worktree root (it reaches "
                  ".github/workflows); name the path you mean, e.g. git clean -fd src/")
    i, grep_next = 0, None
    while i < len(words):
        w = words[i]
        prev = words[i - 1] if i > 0 else ""
        if grep_next is not None:
            kind, grep_next = grep_next, None
            if kind == "text":
                i += 1
                continue
            if is_secret_path(norm(w)):
                block("secret-read", f"'{w}' is a protected secret/memory path (grep -f reads it as the pattern file)",
                      carveout=False)
            i += 1
            continue
        if program in GREP_PROGRAMS and w.startswith("-") and not w.startswith("--") and len(w) > 2:
            # parse the short cluster left-to-right with this program's value-option arity: the FIRST value-taking
            # option takes the rest of the cluster (or, if it is the last char, the next word) as its value and ends
            # the scan, so an `f`/`e` inside another option's value is not mistaken for the pattern-file/pattern flag
            # (codex on #387: rg `-rf.env` is --replace=f.env and reads nothing; grep `-rf.env` is -r -f.env and reads
            # .env — `r` takes a value in rg but not in grep, so the arity is per-program). A cluster of pure boolean
            # flags matches nothing here and falls through: its next word is handled as an ordinary operand.
            arity = GREP_SHORT_VALUE.get(program, set("ABCdefm"))
            cluster = w[1:]
            for k, ch in enumerate(cluster):
                if ch in arity:
                    value = cluster[k + 1:]
                    if value:
                        if ch == "f" and is_secret_path(norm(value)):
                            block("secret-read", f"'{w}' reads a protected secret/memory path as the pattern file", carveout=False)
                    else:
                        grep_next = "file" if ch == "f" else "text"
                    break
            i += 1
            continue
        text_value = prev in TEXT_OPTIONS and prev not in FILE_VALUE_OPTIONS and (prev.startswith("--") or program in {"bd", "gc", "gh"} or git_prose)
        prose = (" " in w or "\t" in w) and ((program not in READ_PROGRAMS and program not in WRITE_PROGRAMS)
                                              or prev in TEXT_OPTIONS or git_prose)
        if (prose or text_value) and not (i > 0 and ">" in prev and all(ch in SEPARATORS for ch in prev)):
            i += 1
            continue
        if "=" in w and w.startswith("--") and w.split("=", 1)[0] in TEXT_OPTIONS:
            i += 1
            continue
        if program in GREP_PROGRAMS and ((i > 0 and prev in grep_values - GREP_PATH_VALUE_OPTIONS and not w.startswith("-"))
                                         or w.startswith(("--regexp=", "--glob=", "--iglob=", "--type=", "--include=", "--exclude="))):
            i += 1  # a text value (pattern, glob, type, colour, separator…), never a file
            continue
        if pattern_pending and i > 0 and not w.startswith("-") and prev not in grep_values \
                and not (">" in prev and all(ch in SEPARATORS for ch in prev)):
            pattern_pending = False  # grep/rg: the first operand is the PATTERN, not a file
            i += 1
            continue
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
        if "=" in w and not p.startswith(os.path.join(cwd, "-")):
            q = norm(w.split("=", 1)[1])
            if is_secret_path(q) and program not in {"echo", "printf", "test", "[", "export"}:
                block("secret-read", f"'{w}' names a protected secret/memory path", carveout=False)
            elif is_workflow_path(q) and program in WRITE_PROGRAMS:
                block(f"workflow-edit-{rig}", ".github/workflows/ is mayor-owned (option value)")
        if is_secret_path(p) and program not in {"echo", "printf", "test", "["}:
            block("secret-read", f"'{w}' is a protected secret/memory path (env files, ~/.claude/projects, "
                  ".gc/runtime/secrets); workers use the sanitized env the worktree setup provides", carveout=False)
        elif i in restore_idx and is_workflow_ancestor(p):
            block(f"workflow-edit-{rig}", f"git {git_sub} of '{w}' rewrites .github/workflows with it (mayor-owned); "
                  "name the paths you mean, e.g. src/")
        elif destructive and is_workflow_ancestor(p) and not (mv_positional_destination and i == len(words) - 1 and i > 1) \
                and not (program == "mv" and prev in {"-t", "--target-directory"}):
            block(f"workflow-edit-{rig}", f"removing/moving '{w}' takes .github/workflows with it (mayor-owned)")
        elif destructive and "$" in expand(w) and not w.startswith("-"):
            block(f"workflow-edit-{rig}", f"destructive operand '{w}' is a shell expansion the guard cannot resolve; "
                  "use a literal path")
        elif CWD_UNKNOWN and (destructive or program in WRITE_PROGRAMS) and not w.startswith("-") and \
                (re.search(r"(^|/)(\.github|workflows)(/|$)", w) or (destructive and w.rstrip("/") in {".", ".."})):
            block(f"workflow-edit-{rig}", f"'{w}' is relative to a cwd the guard cannot resolve (an earlier `cd $…`) and "
                  "names a protected tree; cd to a literal path or use an absolute path")
        elif is_workflow_path(p) and program in WRITE_PROGRAMS:
            if program == "git" and not any(s in words[1:] for s in ("rm", "mv", "checkout", "restore", "apply", "am", "clean", "stash")):
                pass
            elif unstage_only:
                pass  # `git restore --staged <workflow path>` resets the index entry to HEAD
            elif program in {"sed", "perl"} and not any(a.startswith("--in-place") or (a.startswith("-") and not a.startswith("--") and "i" in a[1:]) for a in words[1:]):
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
        # `time ! sudo ls`: the pipeline after the reserved word `time` may carry its own `!`
        while words and (words[0] == "!" or re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", words[0])):
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
            reads, writes = WRAPPER_READ_FILE_OPTIONS.get(program, set()), WRAPPER_WRITE_FILE_OPTIONS.get(program, set())
            while rest and rest[0].startswith("-") and rest[0] != "--":
                opt = rest.pop(0)
                if program == "env" and (opt.startswith("--split-string=") or opt.startswith("-S")) and len(opt) > 2:
                    SPLIT_STRINGS.append(opt.split("=", 1)[1] if opt.startswith("--") else opt[2:])
                    continue
                if program == "env" and opt.startswith("--chdir="):
                    wrapper_chdir(opt.split("=", 1)[1])
                    continue
                if "=" in opt and opt.startswith("--"):
                    name, val = opt.split("=", 1)
                    if name in reads or name in writes:
                        wrapper_file(name, val, name in writes)
                    continue
                if opt in arity and rest:
                    val = rest.pop(0)
                    if program == "env" and opt in {"-S", "--split-string"}:
                        SPLIT_STRINGS.append(val)
                    elif program == "env" and opt in {"-C", "--chdir"}:
                        wrapper_chdir(val)
                    elif opt in reads or opt in writes:
                        wrapper_file(opt, val, opt in writes)
                elif program == "nice" and re.fullmatch(r"-\d+", opt):
                    pass
                elif len(opt) > 2 and not opt.startswith("--") and opt[:2] in arity:
                    if program == "env" and opt[:2] == "-C":
                        wrapper_chdir(opt[2:])
                    elif opt[:2] in reads or opt[:2] in writes:
                        wrapper_file(opt[:2], opt[2:], opt[:2] in writes)
            if rest and rest[0] == "--":
                rest.pop(0)
            if program == "timeout" and rest:
                rest = rest[1:]  # the duration operand
                if rest and rest[0] == "--":
                    rest.pop(0)
            while rest and rest[0] == "--":
                rest.pop(0)
            words = rest
            changed = True
        elif program in RUNNERS and len(words) > 1:
            rest = strip_runner(program, words[1:])
            if rest and rest[0] in {"vercel", "gh", "git", "bd", "gc", "sleep", "sudo"}:
                words = rest
                changed = True
    return words


def strip_runner(program, rest):
    """Drop a package runner's options (with their separate values: `npx --package vercel`, `npm exec -w app`),
    its `dlx`/`exec`/`x`/`run` subcommand and the `--` separator, so rest[0] is the executable it runs."""
    arity = RUNNER_OPT_ARITY.get(program, set())
    rest = list(rest)
    seen_sub = False
    while rest:
        a = rest[0]
        if a == "--":
            rest.pop(0)
            break
        if a.startswith("-"):
            rest.pop(0)
            # unwrapping may replace argv: inspect the value before it is discarded, in every spelling (ghastly
            # gs-18hj: `uv run --env-file .env gh …` passed once the runner was unwrapped to gh; codex on ia-next
            # #387: the attached `--env-file=.env` / `pnpm --dir=.env` / `-C.env` did too)
            if a.startswith("--") and "=" in a:
                name, value = a.split("=", 1)
                if name in arity:
                    wrapper_file(name, value, False)
            elif a in arity and rest:
                wrapper_file(a, rest.pop(0), False)
            elif not a.startswith("--") and len(a) > 2 and a[:2] in arity:
                wrapper_file(a[:2], a[2:], False)
            continue
        if not seen_sub and a in {"dlx", "exec", "x", "run"}:
            rest.pop(0)
            seen_sub = True
            continue
        break
    return rest


def wrapper_chdir(target):
    """`env -C dir cmd …` runs cmd in dir: resolve this statement's relative operands against it (restored by
    check_statement when the statement is done)."""
    global cwd, CWD_UNKNOWN
    t = expand(target)
    if "$" in t or "`" in t:
        cwd, CWD_UNKNOWN = os.path.normpath(os.path.join(cwd, t)), True
    else:
        cwd = os.path.normpath(t if os.path.isabs(t) else os.path.join(cwd, t))


def wrapper_file(opt, value, write):
    """A wrapper option whose value is a file the wrapper itself reads (`xargs -a`) or writes (`time -o`)."""
    p = norm(value)
    if is_secret_path(p):
        block("secret-write" if write else "secret-read", f"'{opt} {value}' {'writes' if write else 'reads'} a protected "
              "secret/memory path", carveout=False)
    elif write and is_workflow_path(p):
        block(f"workflow-edit-{rig_name()}", f"'{opt} {value}' writes into .github/workflows/ (mayor-owned)")


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
    if any(a == "--repo" or a.startswith("--repo=") for a in rest):
        remote = "(--repo)"
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


def flag_on(args, flag):
    """True when a boolean flag is given, including the --flag=true spelling the CLI accepts."""
    for a in args:
        if a == flag:
            return True
        if a.startswith(flag + "=") and a.split("=", 1)[1].lower() not in {"false", "0", "f", "no", "n", "off"}:
            return True
    return False


def check_gh(args):
    raw = [a for a in args if a != "--"]
    args = []  # root options (-R/--repo/--hostname, accepted anywhere) removed so the subcommand is args[0]
    it = iter(raw)
    for a in it:
        if a in GH_ROOT_WITH_ARG:
            next(it, None)
        elif a.startswith("--repo=") or a.startswith("--hostname=") or (a.startswith("-R") and len(a) > 2 and not a.startswith("--")):
            pass
        else:
            args.append(a)
    if args[:2] == ["pr", "merge"] and flag_on(args, "--admin"):
        block("admin-merge", "never bypass branch protection", carveout=False)
    if args[:1] in (["pr"], ["run"]) and (flag_on(args, "--watch") or args[:2] == ["run", "watch"]):
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
            elif a.startswith("--method=") or (a.startswith("-X") and len(a) > 2):
                method = a.split("=", 1)[1].upper() if a.startswith("--") else a[2:].upper()
            elif not a.startswith("-") and not endpoint and a.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                method = a.upper()
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
        if endpoint == "graphql":
            opaque = any(a in {"--input"} or a.startswith("--input=") or "=@" in a or a.startswith("@") for a in args)
            if opaque or any(re.search(r"\bmutation\b", a) for a in args):
                block("protected-api", "GraphQL mutations and opaque GraphQL payloads (--input / @file) are not "
                      "allowed from a worker (they can post statuses or edit protection)", carveout=False)


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
    while args and args[0].startswith("-"):
        opt = args.pop(0)
        if opt in BD_GLOBAL_WITH_ARG and args:
            args.pop(0)
    if args[:1] == ["assign"]:
        block("bd-assignee", "never set assignees (bd assign = update --assignee); the claim hook owns assignment", carveout=False)
        return
    if args[:1] not in (["create"], ["update"]):
        return
    it = iter(args[1:])
    for a in it:
        if " " in a:
            continue
        if a in TEXT_OPTIONS:
            next(it, None)
        elif a == "--assignee" or a.startswith(("--assignee=", "-a")) and not a.startswith("--a"):
            block("bd-assignee", "never set assignees; the claim hook owns assignment", carveout=False)
        elif a.startswith("--assignee"):
            block("bd-assignee", "never set assignees; the claim hook owns assignment", carveout=False)


FIND_NAME_TESTS = {"-name", "-iname", "-path", "-ipath", "-wholename", "-iwholename", "-regex", "-iregex"}
# anything but a plain conjunction: a `*.pyc` test then proves nothing about what reaches -delete (an -exec's own
# arguments are not parsed, and its `+` ends it only right after `{}`)
FIND_NOT_CONJUNCTION = {"!", "-not", "-o", "-or", ",", "(", ")", "-exec", "-execdir", "-ok", "-okdir"}


def find_filter_excludes_workflows(test, pattern):
    """True when a -name/-path test can never match a workflow file OR the protected directory itself. A
    regex is NEVER proven safe: operators like `+`, `.` or alternation match far more than their literal
    characters, and `re.search(r"[*?[]")` treats them as literals (codex on #387: `-regex '.+'` and
    `-regex '.*|x.pyc'` both slipped through). A -name/-path glob is safe only when it carries a literal
    non-yml/yaml extension (`*.pyc`) or is a non-workflow literal, AND cannot match the `.github`/`workflows`
    directory names — whose -delete removes the whole tree (codex on #387: `-name workflows`, incl. -iname)."""
    if test in {"-regex", "-iregex"}:
        return False
    if "\\" in pattern:
        # find treats a backslash as an escape (`ci.y\ml` matches `ci.yml`); Python fnmatch treats it as a literal
        # char, so a "can't match" proof here is unsound — fail closed on any backslash (codex on #387).
        return False
    icase = test in {"-iname", "-ipath"}
    probes = ["workflows", ".github"]
    if test in {"-path", "-ipath"}:  # -path matches the whole path: a trailing /workflows or /.github counts
        probes += [f"{d}/{n}" for n in ("workflows", ".github") for d in (".", "x", "/a")]
    for probe in probes:
        pats = [pattern, pattern.lower()] if icase else [pattern]
        if any(fnmatch.fnmatchcase(probe, pat) for pat in pats):
            return False
    ext = re.search(r"\.([A-Za-z0-9_]+)$", pattern)
    if ext and ext.group(1).lower() not in {"yml", "yaml"}:
        return True
    if not re.search(r"[*?\[]", pattern):
        return not pattern.lower().endswith((".yml", ".yaml")) and not is_workflow_path(norm(pattern))
    return False


def check_find(words):
    if "-delete" in words:
        # the built-in action deletes everything under the roots the tests let through (ia-next gate round 10)
        roots = []
        for a in words:
            if a.startswith("-") or a in {"(", "!", ")"}:
                break
            roots.append(a)
        # the filter carve-out holds for a plain conjunction only, and only the tests BEFORE the first -delete gate
        # it (codex on ia-next #387: `find . -name '*.pyc' -o -delete`, `! -name '*.pyc'`, `-delete -name '*.pyc'`)
        filters, it = [], iter(words)
        for a in it:
            if a == "-delete":
                break
            if a in FIND_NAME_TESTS:
                filters.append((a, next(it, "")))
        plain = not any(a in FIND_NOT_CONJUNCTION for a in words)
        if not (plain and filters and all(find_filter_excludes_workflows(t, f) for t, f in filters)):
            for r in roots or ["."]:
                q = norm(r)
                if is_workflow_ancestor(q) or is_workflow_path(q) or \
                        (CWD_UNKNOWN and re.search(r"(^|/)(\.github|workflows)(/|$)", r)):
                    block(f"workflow-edit-{rig_name()}", f"find {r} … -delete reaches .github/workflows (mayor-owned); "
                          "put a -name filter with a non-workflow extension (e.g. '*.pyc') before -delete in a plain "
                          "conjunction (no !/-not, -o/-or, ',', ( ), -exec: one find per pattern) or start below .github")
    for key in ("-exec", "-execdir", "-ok", "-okdir"):
        while key in words:
            i = words.index(key)
            tail = words[i + 1:]
            end = next((j for j, a in enumerate(tail) if a in {";", "+"}), len(tail))
            check_statement(tail[:end])
            words = tail[end:]


def check_statement(words, state=None):
    """Check one statement; the cwd an `env -C` set for it is restored afterwards (a literal `cd` statement is
    applied by check_script AFTER this returns, so it carries to the following statements)."""
    global cwd, CWD_UNKNOWN
    saved = (cwd, CWD_UNKNOWN)
    try:
        _check_statement(words, state)
    finally:
        cwd, CWD_UNKNOWN = saved


def _check_statement(words, state=None):
    state = state if state is not None else {"sleep": 0.0, "loop": False}
    rig = rig_name()
    if any(w in {"for", "while", "until"} for w in words[:1]):
        state["loop"] = True
    # a `!` stays inside the statement (find's negation: `find . ! -name '*.pyc' -delete`, codex on ia-next #387);
    # strip_condition_keywords drops a leading one
    words = [w for w in words if w not in {"{", "}", "then", "do", "else", "elif", "fi", "done", "esac", "in"}]
    words = strip_condition_keywords(words)
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", words[0]):
        words = words[1:]
    if words and os.path.basename(words[0]) in {"eval", "source", "."} and len(words) > 1:
        if os.path.basename(words[0]) == "eval":
            check_script(" ".join(words[1:]), state)
            return
    while words and words[0] == "--":
        words = words[1:]
    words = unwrap(list(words))
    while SPLIT_STRINGS:
        check_script(SPLIT_STRINGS.pop(), state)
    while words and words[0] == "--":
        words = words[1:]
    if not words:
        return
    program = os.path.basename(words[0])
    args = words[1:]
    if program == "gc":
        rest = list(args)
        while rest and rest[0].startswith("-"):
            opt = rest.pop(0)
            if opt in {"--rig", "-r", "--city", "-C", "--config", "--profile", "--as"} and rest:
                rest.pop(0)
        while rest and rest[0] == "--":
            rest.pop(0)
        check_paths(["gc"] + rest, rig)
    else:
        check_paths(words, rig)
    if program in SHELLS:
        for i, a in enumerate(args):
            if a == "--":
                break
            if a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
                script = args[i + 1] if i + 1 < len(args) else ""
                check_script(script, state)
                return
    if program == "gc":
        rest = list(args)
        while rest and rest[0].startswith("-"):
            opt = rest.pop(0)
            if opt in {"--rig", "-r", "--city", "-C", "--config", "--profile", "--as"} and rest:
                rest.pop(0)
        while rest and rest[0] == "--":
            rest.pop(0)
        args = rest
        program = "gc"
    if program in {"git", "git-push"}:
        check_git(["push"] + args if program == "git-push" else list(args))
    elif program == "gh":
        check_gh(list(args))
    elif program == "vercel":
        rest = list(args)
        while rest and rest[0].startswith("-"):
            opt = rest.pop(0)
            if opt in VERCEL_GLOBAL_WITH_ARG and rest:
                rest.pop(0)
        if rest[:1] in (["env"], ["logs"], ["pull"]):
            block("vercel-env", "production env/logs are mayor-only; use the sanitized env the worktree setup provides")
    elif program == "sleep":
        state["sleep"] = check_sleep(args, state["sleep"])
        if state["loop"]:
            block("long-sleep", "no sleep inside a shell loop; end your turn and let the next event resume you")
    elif program == "watch":
        block("watch", "no watch loops; check once and end your turn")
    if program != "gh" and any(flag_on([a], flag) and not (i > 0 and args[i - 1] in TEXT_OPTIONS)
                               for i, a in enumerate(args) for flag in ("--watch", "--watchAll", "--watch-all")):
        block("watch", "no --watch loops (test runners/bundlers); run once and end your turn")
    # program-specific watch spellings: vitest `watch`/`dev`/`-w`, tsc/tsc-alias `-w` — direct or behind a package runner
    tool, targs = program, list(args)
    if program in RUNNERS:
        rest = strip_runner(program, args)
        if rest:
            tool, targs = os.path.basename(rest[0]), rest[1:]
    if (tool in WATCH_W_PROGRAMS and "-w" in targs) or \
            (tool == "vitest" and next((a for a in targs if not a.startswith("-")), "") in {"watch", "dev"}):
        block("watch", f"{tool} watch mode never ends; run once (`vitest run` / `tsc` without -w) and end your turn")
    if program in {"tail", "journalctl"} and any(a in {"-f", "-F"} or a.startswith("--follow") or (a.startswith("-") and not a.startswith("--") and ("f" in a[1:] or "F" in a[1:])) for a in args):
        block("watch", "no follow loops; read a bounded slice and end your turn")
    elif program == "find":
        check_find(list(args))
    elif program == "gc" and args[:1] == ["bd"]:
        check_bd([a for a in args[1:] if a != "--"])
    elif program == "bd":
        check_bd([a for a in args if a != "--"])
    if state["sleep"] >= 30:
        block("long-sleep", f"total literal sleep in this command is {state['sleep']:.0f} s (limit 30); "
              "end your turn and let the next event resume you")
        state["sleep"] = -1e9


def main():
    global cwd, ROOT
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    except Exception:
        print("BLOCKED by guard-bash (parse): hook payload unreadable", file=sys.stderr)
        sys.exit(2)
    if not isinstance(command, str) or not command.strip():
        return
    state = {"sleep": 0.0, "loop": False}
    check_script(command, state)
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
