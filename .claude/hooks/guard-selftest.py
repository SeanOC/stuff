#!/usr/bin/env python3
"""Self-test for guard-bash.py / guard-edit.py. Run: python3 guard-selftest.py  (exit 0 = all pass).
Uses a temp GC_CITY so operator markers never influence the result; cwd = a temp dir on a feature branch."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp()
city = os.path.join(tmp, "city")
os.makedirs(os.path.join(city, ".gc/runtime/guard-allow"))
work = os.path.join(tmp, ".gc/worktrees/demo/worker/demo/worker-1")
os.makedirs(work)
subprocess.run(["git", "-C", work, "init", "-q", "-b", "gc-pilot/demo"], check=True)
main_wt = os.path.join(tmp, "onmain")
os.makedirs(main_wt)
subprocess.run(["git", "-C", main_wt, "init", "-q", "-b", "main"], check=True)
env = dict(os.environ, GC_CITY=city, CLAUDE_PROJECT_DIR=work)
env.pop("GC_RIG", None); env.pop("RIG", None)

BASH_BLOCK = [
    "git push origin main", "git push origin HEAD:main", "git push origin refs/heads/main",
    "git push --all origin", "git push --mirror origin", "git push origin +gc-ia/x:main",
    "git -c push.default=current push origin main", "git -C . push origin master",
    "git push --force origin gc-ia/x", "git push -f origin gc-ia/x", "git push origin --force-with-lease gc-ia/x",
    "git push -fu origin gc-ia/x", "git push origin +gc-ia/x", "git push origin gc-ia/x --force",
    "gh pr merge 1 --admin", "gh pr merge --admin 1 --squash", "gh pr checks 1 --watch", "gh run watch 123",
    "gh pr view 1 --watch", "watch -n 5 gh pr checks 1",
    "sudo apt install x", "sudo -u root ls", "command sudo ls", "env sudo ls", "nohup sudo ls",
    "xargs -I{} sudo rm {}", r"find . -name x -exec sudo rm {} \;", "bash -c 'sudo ls'", "sh -c \"sudo ls\"",
    "timeout 5 sudo ls", "doas ls", "`sudo ls`", "echo $(sudo ls)", "ls; sudo ls", "ls && sudo ls", "ls | sudo tee x",
    "vercel env pull .env.prod", "vercel logs app", "npx vercel env ls", "pnpm dlx vercel env ls", "pnpm vercel env pull",
    "vercel env ls --environment=production",
    "sleep 30", "sleep 030", "sleep 300", "sleep 1m", "sleep 0.5h", "sleep $((30))", "sleep $X", "sleep 20; sleep 15",
    "sleep 20 && sleep 10", "for i in 1 2 3; do sleep 5; done", "while true; do sleep 5; done", "sleep 45 || true",
    "tail -f log.txt", "tail -F log.txt", "tail --follow=name x", "journalctl -f",
    "bd update x -a worker", "bd update x --assignee worker", "bd update x -aworker", "bd update x -a=worker",
    "bd create -t x -a me", "gc bd update x -a worker", "bd update x --assignee=worker", "bd update x -s open -a ''",
    "cat .env", "cat ./.env", "cat ../.env", "cat src/../.env", "cat .env.production", "cat .env.local",
    "cat ~/.claude/projects/x/memory/MEMORY.md", "cat $HOME/.claude/projects/x/MEMORY.md", "ls .gc/runtime/secrets/",
    "cat /home/u/gc-pilot/city/.gc/runtime/secrets/x", "grep KEY .env", "source .env", ". .env", "cp .env /tmp/x",
    "echo X=1 > .env", "echo X=1 >> .env.local", "cat x > ./sub/../.env", "echo hi > $OUT",
    "echo hi > .github/workflows/ci.yml", "echo hi >> .github/workflows/ci.yml", "cat x | tee .github/workflows/ci.yml",
    "cp ci.yml .github/workflows/ci.yml", "mv ci.yml .github/workflows/", "install -m 644 ci.yml .github/workflows/ci.yml",
    "rsync ci.yml .github/workflows/", "ln -s x .github/workflows/ci.yml", "dd if=x of=.github/workflows/ci.yml",
    "truncate -s 0 .github/workflows/ci.yml", "sed -i s/a/b/ .github/workflows/ci.yml", "perl -pi -e s/a/b/ .github/workflows/ci.yml",
    "rm .github/workflows/ci.yml", "rm -rf .github/workflows", "touch .github/workflows/new.yml",
    "git rm .github/workflows/ci.yml", "git checkout main -- .github/workflows/ci.yml", "git restore --source x .github/workflows/ci.yml",
    "cat > ./x/../.github/workflows/ci.yml <<EOF\nname: x\nEOF",
    "gh api -X POST repos/o/r/statuses/abc -f state=success", "gh api repos/o/r/statuses/abc -f state=success -f context=x",
    "gh api --method PUT repos/o/r/branches/main/protection --input x.json", "gh api -X PATCH repos/o/r/rulesets/1 -f x=y",
    "gh api -X DELETE repos/o/r/branches/main/protection", "gh api graphql -f query='mutation { updateBranchProtectionRule(input:{}) }'",
    "gh api -X POST repos/o/r/check-runs -f name=x",
    "gh api --hostname github.com -X POST repos/o/r/statuses/abc -f state=success",
    "gh api -H 'Accept: application/vnd.github+json' -X POST repos/o/r/statuses/abc -f state=success",
    "git push origin :", "git push origin 'refs/heads/*:refs/heads/*'", "git push origin '*:*'",
    "timeout -k 1 5 sudo id", "ionice -c 3 sudo id", "nice -n 10 sudo id", "nice -10 sudo id", "env -u X sudo id",
    "env -i PATH=/bin sudo id", "timeout --kill-after=2 5 sudo id", "xargs -n 1 sudo rm",
    "cat '.gc/runtime/secrets/my secret'", "rm '.github/workflows/my check.yml'", "cat 'my dir/.env'",
    "sleep 20 15", "sleep 10 10 10", "sleep -- 45",
    "eval \"sudo ls\"", "eval 'git push origin main'", "eval \"gh pr merge 1 --admin\"", "eval cat .env",
    "dd if=x of=.env", "dd if=.env of=/tmp/x", "dd if=x of=./sub/../.env.local",
    "git apply patch.diff", "git am 0001.patch", "git apply --index x.patch",
    "bash -lc 'sudo id'", "sh -lc 'git push origin main'", "bash -xc 'sudo id'",
    "env -S 'sudo id'", "env --split-string='git push origin main'", "env -S'sudo id'",
    "git push --repo=origin main", "git push --repo origin main", "git push --repo=origin HEAD:main",
    "gh api -XDELETE repos/o/r/branches/main/protection", "gh api -XPOST repos/o/r/statuses/abc -f state=success",
    "gh api POST repos/o/r/statuses/abc -f state=success",
    "gh api graphql --input payload.json", "gh api graphql -F query=@mutation.graphql", "gh api graphql -f query='mutation M { x }'",
    "git clean -fd .github/workflows", "sed --in-place=.bak s/a/b/ .github/workflows/ci.yml", "cp --target-directory=.github/workflows ci.yml",
    "cp -t .github/workflows ci.yml", "install ci.yml --target-directory=.github/workflows", "tar -xf x.tar -C .github/workflows",
    "timeout 30 -- sudo id", "timeout 5 -- git push origin main", "timeout 5 -- sleep 400", "-- sudo id",
    "gc --rig co-author bd create -t x -a worker", "gc --city X bd update x --assignee worker", "gc --rig=x bd update x -a w",
    "gc bd -- create -a worker", "gh pr merge -- 1 --admin", "gh pr -- view 1 --watch", "bd -- update x -a w",
    "cat 'my dir/.env'", "head -n 1 '.gc/runtime/secrets/my secret'", "cp 'ci file.yml' '.github/workflows/ci file.yml'",
    "echo hi > '.github/workflows/my check.yml'",
    'echo "$(sudo ls)"', 'printf "%s\\n" "$(cat .env)"', 'git commit -m "$(cat .env)"', 'X="$(sudo id)"; echo $X',
    'echo "`sudo ls`"', 'echo "$(echo "$(sudo ls)")"', 'echo "it\'s $(sudo ls)"', 'bd update x --notes "$(cat .env.local)"',
    "gh -R SeanOC/ia-next pr merge 376 --admin", "gh pr merge 376 --admin=true", "gh --repo o/r pr merge 1 --admin",
    "gh pr -R o/r merge 1 --admin", "gh -Ro/r pr merge 1 --admin", "gh pr checks 1 --watch=true", "gh -R o/r run watch 1",
    "vercel --scope team env pull", "vercel -S team logs app", "vercel --scope=team env ls", "vercel --token x --scope team env pull",
    "npx vercel --scope team env pull",
    # Substitutions still execute in double quotes, word-internal # text, and
    # unquoted heredocs (where quote and comment characters are just data).
    'echo "# $(sudo ls)"', 'echo prefix#$(sudo ls)', r'echo \#$(sudo ls)',
    "cat <<MSG\n`sudo ls`\nMSG", "cat <<MSG\n'$(sudo ls)'\nMSG",
    "cat <<MSG\n# $(sudo ls)\nMSG",
    "cat <<'MSG'\n$(sudo ls)\nMSG\nsudo ls",
    "cat <<'FIRST' <<SECOND\n$(sudo ls)\nFIRST\n$(sudo ls)\nSECOND",
    'echo "$(cat <<MSG\n$(sudo ls)\nMSG\n)"',
    'echo "$(echo "# $(sudo ls)")"',
    "echo \"<<'MSG'\"\nsudo ls\nMSG",
    'echo "<<\'MSG\'\n$(sudo ls)\nMSG"',
    "cat <<MSG\nMS\\\nG\nsudo ls",
    "cat <<MSG\nMSG \n$(sudo ls)\nMSG",
    "cat <<MSG\n\\$(echo ok) $(sudo ls)\nMSG",
    'cat <<<"$(sudo ls)"',
    "echo $(sleep 15); sleep 15", "echo `sleep 15`; sleep 15",
    'echo "$(sleep 15)"; echo "$(sleep 15)"', 'echo "$(echo $(sleep 30))"',
    "echo hi > $(printf out)", 'sleep "$(printf 1)"',
    # Malformed executable text must still fail closed through recursive paths.
    'echo "$(echo hi"', "eval \"echo '\"", "bash -c \"echo '\"", "env -S \"echo '\"",
    # round 5 (ia-next gate): suffix-form env files, destructive parents, patch, grep pattern vs path
    "cat /tmp/prod.env", "head -n 1 /tmp/runpod.env", "source scratch/prod.env", "cp ~/x.env .",
    "rm -rf .github", "git rm -r .github", "mv .github saved-github", "rm -rf .", "rm -rf ./x/..", "git clean -fdx .github",
    "patch -p1 < changes.diff", "patch -p1 -i x.diff", "patch .github/workflows/ci.yml x.diff",
    "grep KEY .env", "rg KEY .env", "grep -e KEY .env", "grep -n KEY -- .env", "rg -t py KEY .env", "grep -A 3 KEY .env.local",
    "vercel -e X=1 env pull", "vercel --env X=1 logs app",
    # round 6: file-valued options, grep flag classification, wrappers before the path policy, bd globals/assign, git clean
    "gh pr comment 1 --body-file .env", "gh pr create --body-file=.env.local", "gh pr create --body-file ~/.claude/projects/x/memory/MEMORY.md",
    "bd update x --design-file .env", "gh release create v1 --body-file prod.env", "gh api -X POST repos/o/r/issues/1/comments -F body=@.env",
    "grep -r KEY .env", "grep -R KEY .env", "grep -E KEY .env", "grep -r SECRET .env.local", "rg --regexp SECRET .env", "grep --color KEY .env",
    "grep -T KEY .env", "grep -M KEY .env", "grep -r SECRET /tmp/prod.env", "rg -E KEY prod.env", "rg --files .env", "rg --file pats.txt .env",
    "grep --color=always KEY .env", "rg -eKEY .env",
    "command cp ci.yml .github/workflows/ci.yml", "env FOO=1 rm -rf .github", "timeout 5 dd if=x of=.github/workflows/ci.yml", "git -C . rm -r .github",
    "nohup cp ci.yml .github/workflows/ci.yml", "FOO=1 rm -rf .github", "git -C sub rm -r ../.github", "env cat .env", "timeout 5 cat .env",
    "bd assign ia-123 worker-2", "gc bd assign ia-123 worker-2", "bd --db /tmp/test.db update x -a w", "bd -C . update x --assignee w",
    "git clean -fdx", "git clean -fd", "git clean -fdx -- .github",
]
BASH_ALLOW = [
    "git push -u origin gc-pilot/gs-1234", "git push origin gc-ia/worker-guards", "git push", "git push origin HEAD",
    "git add -A && git commit -m \"gs-1: main loop cleanup\" && git push -u origin gc-pilot/gs-1234",
    "git commit -m 'force-push the main idea: never'", "git log origin/main..HEAD", "git fetch origin main",
    "git rebase origin/main", "git merge origin/main", "git push origin gc-ia/x:refs/heads/gc-ia/x", "git push --tags origin",
    "git diff main -- .github/workflows/ci.yml", "cat .github/workflows/ci.yml", "grep -n sudo .github/workflows/ci.yml",
    "git push origin --delete gc-ia/old", "git push -o ci.skip origin gc-ia/x",
    "gh pr merge 1 --squash", "gh pr checks 1", "gh run view 123 --log", "gh pr view 1 --json state",
    "gh api repos/o/r/commits/abc/status", "gh api repos/o/r/branches/main/protection", "gh api repos/o/r/statuses/abc",
    "gh api -X POST repos/o/r/issues/1/comments -f body=hi", "gh api -X PATCH repos/o/r/pulls/1 -f draft=false",
    "gh api graphql -f query='query { repository(owner:\"o\", name:\"r\") { id } }'",
    "sleep 5", "sleep 29", "sleep 10; sleep 10", "sleep 0.5", "timeout 60 pnpm test", "sleep 1 && echo ok",
    "tail -n 50 log.txt", "tail log.txt", "journalctl -u x -n 20", "head -c 100 x",
    "bd update x --notes 'never use --assignee or -a; the hook owns it'", "bd update x --append-notes \"--assignee worker\"",
    "bd update x -s open --force", "bd update x -d \"$(cat f)\"", "bd show x", "bd update x --reason '-a is banned'",
    "gc bd create -t 'x' -d 'uses -a in notes' --type task", "bd update x --labels plan-reviewed",
    "cat .env.example", "cp .env.example .env.local.example", "cat .envrc", "ls -la", "grep -n 'DATABASE_URL' src/db.ts",
    "echo hi > out.txt", "echo hi >> notes.md", "cat > scratch/x.mjs <<'EOF'\nconsole.log(1)\nEOF", "ls > /dev/null 2>&1",
    "pnpm test 2>&1 | tail -20", "pnpm tsx scripts/x.ts > out.log 2>&1", "echo .env", "grep -rn '\\.env' src/",
    "rg 'sudo' docs/", "echo 'sudo is banned'", "echo \"git push origin main is banned\"", "man sudo",
    "vercel build", "npx vercel --help", "pnpm run build", "pnpm vercel build", "uv run pytest -q",
    "find . -name '*.ts' -exec grep -l x {} +", "python3 -c 'print(1)'", "node -e 'console.log(1)'",
    "sed -i s/a/b/ src/x.ts", "perl -pi -e s/a/b/ src/x.ts", "cp a.yml b.yml", "mv x y", "rm -rf node_modules",
    "cat ~/.claude/settings.json", "ls .gc/runtime/", "cat .gc/runtime/session.json", "env | sort", "export FOO=1",
    "FOO=1 pnpm test", "command -v node", "nice -n 10 pnpm test", "nohup pnpm build &", "xargs -n1 echo < list.txt",
    "watchexec --help", "gh workflow list", "git apply --check x.patch", "git apply --stat x.patch",
    "gh api -H 'Accept: x' repos/o/r/commits/abc/status", "gh api --hostname github.com repos/o/r/pulls/1",
    "timeout -k 1 5 pnpm test", "nice -n 10 pnpm build", "env -u X pnpm test", "sleep 10 15", "eval echo hi",
    "bd update x --notes 'see .env handling in the README'", "dd if=/dev/zero of=/tmp/x bs=1M count=1",
    "git push origin gc-ia/x:gc-ia/x", "git push --repo=origin gc-ia/x",
    "git commit -m 'docs: guard for ~/.claude/projects/ and .gc/runtime/secrets paths'",
    "gh pr comment 1 --body 'never read .env or /.gc/runtime/secrets from a worker'",
    "bd update x --notes 'protects .github/workflows/ci.yml and ~/.claude/projects/'",
    "git commit -m 'sudo is banned; git push origin main is banned'", "gh api graphql -f query='query { viewer { login } }'",
    "timeout 30 -- pnpm test", "env -S 'pnpm test'", "gc --rig x bd show y", "gc bd update x --notes 'x'",
    "bash -lc 'pnpm test'", "git clean -fd src/", "sed --in-place=.bak s/a/b/ src/x.ts", "cp -t dist/ x.js", "git -c core.pager=cat log -1", "git -C .. status", "curl -s https://x/y",
    'echo "$(git status)"', 'git commit -m "built at $(date)"', 'echo "price (approx) \\$5"', "bd update x --notes 'run $(sudo ls) never'",
    "git commit -m 'see `gc` docs'", 'echo "use \\`gc\\` here"', 'bd update x --notes "$(cat notes.md)"',
    "gh pr merge 1 --admin=false", "gh -R o/r pr view 1 --json state", "gh -R o/r pr merge 1 --squash", "gh --repo o/r pr checks 1",
    "vercel --scope team build", "vercel -S team --help", "vercel --cwd . build",
    # Review F1: comments and quoted heredocs are literal, including when they
    # occur inside a substitution used for a PR body or commit message.
    'echo hi  # `sudo ls`',
    'echo hi;# $(gh pr merge 1 --admin)\necho ok',
    'echo hi\n# `cat .env`\necho ok',
    "echo hi # unmatched ' $( and `",
    'gh pr comment 39 --body "$(cat <<\'MSG\'\nNEVER run `sudo chmod 777 /`\nMSG\n)"',
    'gh pr comment 39 --body "$(cat <<\'MSG\'\nNEVER run `gh pr merge 1 --admin`\nMSG\n)"',
    'git commit -m "$(cat <<\'MSG\'\nunmatched ( here\nMSG\n)"',
    "cat <<'MSG'\nsudo ls\ncat .env\nunmatched ' \" (`\nMSG",
    'cat <<"MSG"\n$(sudo ls)\nMSG',
    "cat <<\\MSG\n`sudo ls`\nMSG",
    "cat <<M'S'G\n$(sudo ls)\nMSG",
    "cat <<-'MSG'\n\t$(sudo ls)\n\tMSG",
    "cat <<'MSG' # $(sudo ls)\n`sudo ls`\nMSG",
    "cat <<'FIRST' <<'SECOND'\n$(sudo ls)\nFIRST\n`cat .env`\nSECOND",
    "cat <<MSG\nsudo ls\n' \" ( # prose\n\\$(sudo ls)\nMSG",
    'cat <<<"literal ( # text"',
    # Quoted markers in ordinary prose must not hide later executable text.
    "echo \"<<'MSG'\"\necho ok",
    'echo "$(echo ok # unmatched ) \'\n)"',
    # Review F2: parentheses inside quotes belong to the argument, not to the
    # surrounding command substitution's depth.
    'echo "$(sed \'s/(//\' f)"', 'echo "$(sed \'s/)//\' f)"',
    'echo "$(awk \'{print "("}\' f)"',
    'echo "$(printf "%s" "(")"', 'echo "$(printf "%s" ")")"',
    'echo "$(echo "$(printf \'(\')")"',
    # Review F3: each executable sleep contributes once, at every nesting level.
    'echo `sleep 29`', 'echo "`sleep 29`"', 'echo $(sleep 29)',
    'echo "$(sleep 29)"', 'echo "$(echo $(sleep 29))"',
    'echo "$(sleep 10)"; echo `sleep 19`',
    'cat <<MSG\n$(sleep 29)\nMSG',
    # round 5: literal text / pattern operands are not paths; non-mutating patch; sibling files under .github
    "bd update x --notes '.env'", "gh pr comment 1 --body '.env'", "git commit -m '.env'", "git tag -m .env v1",
    "bd update x --notes=.env", "gc bd update x -d .env", "rg .env README.md", "grep -n .env README.md", "grep -rn '\\.env' src/",
    "rg -n 'process.env' src/", "grep -c .env.local docs.md", "patch --dry-run -p1 < x.diff", "rm -rf .github/CODEOWNERS",
    "rm -f .github/dependabot.yml", "rm -rf node_modules", "mv .github/CODEOWNERS .github/OWNERS", "cat .env.example",
    "cat config.envrc", "ls .github", "cat .github/workflows/ci.yml", "git rm .github/CODEOWNERS",
    # round 6
    "mv /tmp/x.yaml .", "mv x.yaml .github/", "git clean -fdx src/", "git clean -n", "git clean -fd -- src/", "grep -r KEY src/",
    "grep -E 'a|b' README.md", "rg --files src/", "gh pr comment 1 --body-file notes.md", "bd --db /tmp/test.db show x",
    "grep --color=always TODO src/x.ts", "rg -e TODO src/", "git -C sub status", "env FOO=1 cat README.md",
]
EDIT_BLOCK = [".env", ".env.local", "./.env", "sub/../.env", "/abs/.env.production", ".github/workflows/ci.yml",
              "./x/../.github/workflows/ci.yml", "~/.claude/projects/x/memory/MEMORY.md", "$HOME/.claude/projects/x/y.md",
              ".gc/runtime/secrets/x", ".github/workflows"]
EDIT_ALLOW = ["src/x.ts", ".env.example", ".env.local.example", ".envrc", ".github/CODEOWNERS", ".github/dependabot.yml",
              "docs/.github/workflows.md", "build123d/ci/reference-measure.yml", ".claude/settings.json", "README.md"]


def run(script, tool_input, cwd=work, extra_env=None):
    e = dict(env, **(extra_env or {}))
    p = subprocess.run([sys.executable, os.path.join(HERE, script)], input=json.dumps({"tool_input": tool_input, "cwd": cwd}),
                       capture_output=True, text=True, env=e)
    return p.returncode, p.stderr.strip()


fails = 0
def expect(script, ti, want, label, **kw):
    global fails
    rc, err = run(script, ti, **kw)
    if rc != want:
        fails += 1
        print(f"FAIL {label!r}: rc={rc} want={want} :: {err.splitlines()[0] if err else ''}")

for c in BASH_BLOCK:
    expect("guard-bash.py", {"command": c}, 2, c)
for c in BASH_ALLOW:
    expect("guard-bash.py", {"command": c}, 0, c)
expect("guard-bash.py", {"command": "git push"}, 2, "bare push while on main", cwd=main_wt)
expect("guard-bash.py", {"command": "git push origin"}, 2, "push origin while on main", cwd=main_wt)
expect("guard-bash.py", {"command": "git push origin HEAD"}, 2, "push HEAD while on main", cwd=main_wt)
for p in EDIT_BLOCK:
    expect("guard-edit.py", {"file_path": p}, 2, "edit " + p)
for p in EDIT_ALLOW:
    expect("guard-edit.py", {"file_path": p}, 0, "edit " + p)
# Read tool: secrets blocked (incl. suffix .env), templates + workflows readable
READ_BLOCK = [".env", ".env.local", "/tmp/prod.env", "scratch/runpod.env", "~/.claude/projects/x/MEMORY.md", ".gc/runtime/secrets/x"]
READ_ALLOW = [".env.example", ".env.local.example", ".envrc", ".github/workflows/ci.yml", "src/x.ts", "README.md"]
def expect_read(path, want):
    global fails
    e = dict(env)
    p = subprocess.run([sys.executable, os.path.join(HERE, "guard-edit.py")],
                       input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": path}, "cwd": work}),
                       capture_output=True, text=True, env=e)
    if p.returncode != want:
        fails += 1
        print(f"FAIL 'Read {path}': rc={p.returncode} want={want} :: {p.stderr.strip().splitlines()[0] if p.stderr.strip() else ''}")
for p_ in READ_BLOCK:
    expect_read(p_, 2)
for p_ in READ_ALLOW:
    expect_read(p_, 0)
GREP_BLOCK = [("Grep", ".env"), ("Grep", "~/.claude/projects/x"), ("Glob", ".gc/runtime/secrets"), ("Grep", "/tmp/prod.env")]
GREP_ALLOW = [("Grep", "src"), ("Grep", ".github/workflows"), ("Glob", "src/**"), ("Grep", ".env.example")]
def expect_grep(tool, path, want):
    global fails
    p = subprocess.run([sys.executable, os.path.join(HERE, "guard-edit.py")],
                       input=json.dumps({"tool_name": tool, "tool_input": {"pattern": "x", "path": path}, "cwd": work}),
                       capture_output=True, text=True, env=dict(env))
    if p.returncode != want:
        fails += 1
        print(f"FAIL '{tool} {path}': rc={p.returncode} want={want}")
for tool_, p_ in GREP_BLOCK:
    expect_grep(tool_, p_, 2)
for tool_, p_ in GREP_ALLOW:
    expect_grep(tool_, p_, 0)
# settings-level regression: the native deny backstop must not catch the allowed templates, and Read must be hooked
import fnmatch
settings_path = next((p for p in (os.path.join(HERE, "settings.worker.json"), os.path.join(HERE, "..", "settings.json")) if os.path.exists(p)), None)
with open(settings_path) as fh:
    cfg = json.load(fh)
deny_reads = [d[5:-1] for d in cfg["permissions"]["deny"] if d.startswith("Read(")]
for tpl in ("./.env.example", "./.env.local.example", "./.env.sample", "./.env.template", "./.env.dist", "./.envrc"):
    if any(fnmatch.fnmatch(tpl, pat) or fnmatch.fnmatch(tpl[2:], pat) for pat in deny_reads):
        fails += 1
        print(f"FAIL settings deny catches allowed template {tpl}")
for tool_ in ("Read", "Grep", "Glob"):
    if not any(tool_ in h["matcher"].split("|") for h in cfg["hooks"]["PreToolUse"]):
        fails += 1
        print(f"FAIL settings: {tool_} is not routed to guard-edit.py")
# carve-outs
open(os.path.join(city, ".gc/runtime/guard-allow/workflow-edit-demo"), "w").close()
expect("guard-edit.py", {"file_path": ".github/workflows/ci.yml"}, 0, "workflow edit with marker")
expect("guard-bash.py", {"command": "cp ci.yml .github/workflows/ci.yml"}, 0, "workflow cp with marker")
open(os.path.join(city, ".gc/runtime/guard-allow/push-main"), "w").close()
expect("guard-bash.py", {"command": "git push origin main"}, 0, "push-main with marker")
open(os.path.join(city, ".gc/runtime/guard-allow/sudo"), "w").close()
expect("guard-bash.py", {"command": "sudo ls"}, 2, "sudo has no carve-out")
expect("guard-bash.py", {"command": "git push -f origin x"}, 2, "force-push has no carve-out")
total = len(BASH_BLOCK) + len(BASH_ALLOW) + len(EDIT_BLOCK) + len(EDIT_ALLOW) + len(READ_BLOCK) + len(READ_ALLOW) + len(GREP_BLOCK) + len(GREP_ALLOW) + 8 + 9
print(f"{total - fails}/{total} guard cases pass")
sys.exit(1 if fails else 0)
