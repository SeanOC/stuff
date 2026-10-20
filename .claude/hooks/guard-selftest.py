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
# carve-outs
open(os.path.join(city, ".gc/runtime/guard-allow/workflow-edit-demo"), "w").close()
expect("guard-edit.py", {"file_path": ".github/workflows/ci.yml"}, 0, "workflow edit with marker")
expect("guard-bash.py", {"command": "cp ci.yml .github/workflows/ci.yml"}, 0, "workflow cp with marker")
open(os.path.join(city, ".gc/runtime/guard-allow/push-main"), "w").close()
expect("guard-bash.py", {"command": "git push origin main"}, 0, "push-main with marker")
open(os.path.join(city, ".gc/runtime/guard-allow/sudo"), "w").close()
expect("guard-bash.py", {"command": "sudo ls"}, 2, "sudo has no carve-out")
expect("guard-bash.py", {"command": "git push -f origin x"}, 2, "force-push has no carve-out")
total = len(BASH_BLOCK) + len(BASH_ALLOW) + len(EDIT_BLOCK) + len(EDIT_ALLOW) + 8
print(f"{total - fails}/{total} guard cases pass")
sys.exit(1 if fails else 0)
