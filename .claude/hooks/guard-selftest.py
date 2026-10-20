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
    "grep -T KEY .env", "grep -M KEY .env", "grep -r SECRET /tmp/prod.env", "rg --files .env", "rg --file pats.txt .env",
    "grep --color=always KEY .env", "rg -eKEY .env",
    "command cp ci.yml .github/workflows/ci.yml", "env FOO=1 rm -rf .github", "timeout 5 dd if=x of=.github/workflows/ci.yml", "git -C . rm -r .github",
    "nohup cp ci.yml .github/workflows/ci.yml", "FOO=1 rm -rf .github", "git -C sub rm -r ../.github", "env cat .env", "timeout 5 cat .env",
    "bd assign ia-123 worker-2", "gc bd assign ia-123 worker-2", "bd --db /tmp/test.db update x -a w", "bd -C . update x --assignee w",
    "git clean -fdx", "git clean -fd", "git clean -fdx -- .github",
    # round 7: directory copies into .github/, generic --watch, $PWD / unresolved destructive operands, grep path-valued options
    "cp -R workflows .github/", "mv workflows .github/", "rsync -a workflows .github/", "cp -r workflows .github", "cp -t .github workflows",
    "mv -t .github workflows", "install -d .github/workflows", "cp -r ci/workflows .github/",
    "pnpm test --watch", "vitest --watch", "pnpm vitest --watch", "jest --watchAll", "npx vitest --watch=true", "tsc --watch",
    'rm -r "$PWD"', 'rm -r "${PWD}"', 'git -C "$PWD" clean -fdx', 'rm -r "$OLDPWD"', "rm -rf $DIR", 'mv "$PWD" /tmp/x',
    "grep -f /tmp/prod.env x", "rg --pre /tmp/prod.env x", "grep -f .env README.md", "rg --file .env README.md", "rg --ignore-file .env x",
    "gh issue create --body-file /tmp/prod.env", "bd update co-x --body-file /tmp/prod.env", "gh pr comment 1 --body-file=.env",
    "echo foo # x\nsudo ls", 'echo "# x"; sudo ls', "echo foo # x\ngit push origin main",
    # round 10: runner option values keep the secret check when the payload is unwrapped (ghastly gs-18hj)
    "uv run --env-file .env gh pr comment 1 -b hi", "uv --env-file .env run git status", "pnpm exec --dir .env gh pr view 1",
    "npx --package vercel vercel env pull", "uv run --env-file ../.env git status",
    # codex on #387: the attached spellings (`--opt=value`, `-Xvalue`) and the *x runners' option values too
    "uv run --env-file=.env git status", "pnpm --dir=.env exec gh pr view 1", "pnpm exec --dir=.env gh pr view 1",
    "uv --env-file=../.env run git status", "pnpm -C.env exec gh pr view 1", "uvx --env-file .env gh pr view 1",
    "uvx --env-file=.env gh pr view 1", "npx --userconfig=.env gh pr view 1", "pnpx --dir .env gh pr view 1",
    "bunx --config=.env gh pr view 1",
    # round 10: worktree-updating git reset with a ref replaces .github/workflows wholesale
    "git reset --hard main", "git reset --hard origin/main", "git reset --merge main", "git reset --keep HEAD~1", "git reset --hard HEAD~2",
    # round 10: find -delete roots go through the workflow-ancestor policy
    "find .github -type f -delete", "find .github/workflows -mindepth 1 -delete", "find . -name '*.yml' -delete", "find . -delete",
    "find . -type f -delete", "find .. -name '*.yaml' -delete", "find . -name 'ci.yml' -delete", "find . -name '*~' -delete",
    "find -delete", "find . -path '*/workflows/*' -delete", "find .github -name '*.yml' -type f -delete",
    # codex on #387: the filter carve-out needs a plain conjunction with its tests before the first -delete; an
    # escaped/quoted ( ) ; is an argument, so grouping and `-exec … \;` no longer split the -delete off
    'find . -name "*.pyc" -o -delete', 'find . ! -name "*.pyc" -delete', "find . -not -name '*.pyc' -delete",
    "find . -name '*.pyc' -or -delete", "find . -name '*.pyc' , -delete", "find . -delete -name '*.pyc'",
    "find . -name '*.pyc' -delete -o -delete", r"find . \( -name '*.pyc' -o -true \) -delete", "find . '(' -true ')' -delete",
    r"find . \( -name '*.pyc' -o -name '*.pyo' \) -delete", r"find . -exec true {} \; -delete",
    r"find . -name '*.pyc' -exec echo {} \; -delete", r"find . -regex '.*\|.*\.pyc' -delete",
    r"find . -regextype posix-extended -regex '.*|x\.pyc' -delete", "cd .github && find . ! -name '*.pyc' -delete",
    "time ! sudo ls",
    # round 10 (gate round 11): if/while/until conditions are commands
    "if git push origin main; then echo ok; fi", "while sudo true; do echo x; done", "until gh pr merge --admin 1; do echo w; done",
    "if ! git push origin main; then echo x; fi", "if cat .env; then :; fi", "if true; then :; elif sudo ls; then :; fi",
    "while vercel env pull; do :; done", "if command -v x; then sudo ls; fi",
    # round 10 (gate round 11): attached / clustered grep -f reads the pattern FILE
    "grep -f.env pat", "rg -f.env", "grep -r -f.env .", "grep -rf.env .", "grep -rf .env .", "rg -if.env .", "grep -rnf .env src/",
    "grep -f./.env x", "fgrep -f.env.local x",
    # round 10: `command cd` / `builtin cd` change the cwd like cd (ghastly #41 advisory)
    "command cd .github/workflows && touch x.yml", "builtin cd .github && touch workflows/x.yml", "command cd .github; rm -rf workflows",
    "git restore --staged --worktree .github/workflows/ci.yml", "git restore -SW .github/workflows/ci.yml", "git restore .github/workflows/ci.yml",
    # ghastly #42 gate (gs-rtbb): an explicit source stages tree content instead of merely unstaging
    "git restore --source main --staged .github/workflows/ci.yml", "git restore -s main --staged .github/workflows/ci.yml",
    "git restore --staged --source=main .github/workflows/ci.yml", "git restore --staged -smain .github/workflows/ci.yml",
    "git restore --staged -qs main .github/workflows/ci.yml", "git restore -S --source main -- .github/workflows/ci.yml",
    "git -C . restore --staged --source=main .github/workflows/ci.yml",
    # ghastly #42 (gs-rtbb) + co-author #867 (co-jwz8z) extra find/-delete and runner-value cases
    "command find . ! -name '*.pyc' -delete", "! find . ! -name '*.pyc' -delete", "find . -name '*.pyc' -delete -o -name '*.yml' -delete",
    "find . -type d -empty -delete", "find . -empty -delete", "find . -name '*.pyc' -prune -o -delete", r"find . \! -name '*.pyc' -delete",
    "find . -path '*.pyc' -o -delete", "find .github -iname '*.orig' -or -delete",
    "npm exec --workspace=.env gh pr view 1", 'uv run --env-file="my dir/.env" git status', "pnpm --dir=../.env exec git status",
    'uv run --env-file "my dir/.env" git status', 'pnpm exec --dir="my dir/.env" gh pr view 1',
    # round 8: checkout/restore ancestor pathspecs, vitest/tsc -w aliases behind runners, mv -t source vs destination
    "git checkout main -- .", "git checkout main -- .github", "git restore --source main .", "git checkout main .",
    "git checkout -- .", "git restore .", "git checkout origin/main -- ./", "git restore --source=main -- .github/",
    "git -C . checkout main -- .", "git checkout .", "git restore --worktree --staged .", "git stash push -- .",
    "git stash push -- .github", "git checkout main -- src .github",
    "vitest watch", "vitest -w", "pnpm vitest -w", "pnpm exec vitest -w", "npx vitest -w", "tsc -w", "npx tsc -w",
    "pnpm exec tsc -w -p tsconfig.json", "vitest dev", "bun vitest -w", "yarn vitest watch", "tsc-alias -w", "npx --yes vitest -w",
    "mv -t /tmp .github", "mv -t .github/workflows x.yml", "mv --target-directory .github/workflows x.yml", "mv -t . .github",
    # round 9: a literal cd/pushd/env -C moves the cwd later relative operands resolve against; wrapper file operands;
    # package-runner options take values (`npx --package vercel vercel …`)
    "cd .github/workflows && touch evil.yml", "cd .github && touch workflows/evil.yml", "cd .github; rm -rf workflows",
    "env -C .github/workflows touch evil.yml", "env --chdir=.github/workflows touch evil.yml", "env -C.github/workflows touch evil.yml",
    "pushd .github/workflows && touch evil.yml", "cd .github/workflows\ntouch evil.yml", "cd .github && cd workflows && echo hi > evil.yml",
    "(cd .github/workflows && touch evil.yml)", "cd .github/workflows; cd -; cd -; touch evil.yml", "cd .github/workflows && pushd .. && popd && touch x.yml",
    "bash -c 'cd .github/workflows && touch evil.yml'", "cd .github/workflows && cp /tmp/x.yml .", "cd .github && mv /tmp/x.yml workflows/",
    "cd .github/workflows && sed -i s/a/b/ ci.yml", "cd .github/workflows && git rm ci.yml", "cd src && cat ../.env",
    "cd $DIR && rm -rf .", "cd $DIR && touch workflows/x.yml", "cd $DIR && rm -rf .github",
    "xargs -a .env echo", "xargs --arg-file=.env echo", "xargs --arg-file .env echo", "xargs -a.env echo", "xargs -a /tmp/prod.env echo",
    "/usr/bin/time -o .env true", "/usr/bin/time -o .github/workflows/timing.txt true", "time --output=.env true", "/usr/bin/time --output .github/workflows/t.txt true",
    "npx --package vercel vercel env pull", "npx -p vercel vercel env pull", "npm exec --package vercel -- vercel env pull",
    "npm exec --package=vercel -- vercel env pull", "npx --package vercel -- vercel env pull", "pnpm --filter web exec vercel env pull",
    "yarn dlx -p vercel vercel env pull", "npx --package vercel vercel logs app", "npm exec -w app -- vercel env pull", "npx -p vercel -- vitest -w",
    # retained from ghastly #40 (worker gs-28ql): =-form file options, mv forms, git clean exclusions are not pathspecs, false-ish watch values
    "cat x --design-file .gc/runtime/secrets/k", "gh pr comment 40 --body-file=.env", f"gh pr comment 40 --body-file={work}/.env",
    f"gh pr create --body-file={work}/.env.production", "bd update x --design-file=.env", f"gc bd update gs-1 --design-file={work}/.env",
    "gh release create v1 --body-file=prod.env", "gc bd update gs-1 --design-file=/tmp/prod.env",
    "gh pr create --body-file=~/.claude/projects/x/memory/MEMORY.md", "bd update x --design-file=.gc/runtime/secrets/k",
    "gh pr comment 40 --body-file=src/../.env", "grep --colour KEY .env", "grep --regexp SECRET prod.env", "grep --file patfile prod.env",
    "rg --regexp=SECRET .env", "grep --file=patfile prod.env",
    "mv . .", "mv .github .", "git mv . .", "mv x .github/workflows", "mv -t /tmp .github", "mv --target-directory /tmp .github",
    "mv --target-directory=/tmp .github", "mv -t/tmp .github", "mv -vt /tmp .github",
    "xargs -a .env cat", "xargs --arg-file=/tmp/prod.env echo", "command env timeout 5 xargs -a .env echo",
    "xargs -a ~/.claude/projects/x/memory/MEMORY.md echo", "xargs --arg-file=.gc/runtime/secrets/k echo", "env FOO=1 xargs -a .env echo",
    "xargs -a/tmp/prod.env echo",
    "git clean -fdx -e node_modules", "git clean -fdx --exclude node_modules", "git clean -fdx --exclude=*.log", "git clean -fdxe node_modules",
    "git clean -fdeignored", "git clean -fd -e -n", "git clean -fd --dry-run --no-dry-run", "git clean -fd -e build/ --exclude '*.log' -e '*.tmp'",
    "command git clean -fdx -e node_modules",
    "jest --watchAll=true", "vitest --watch=falsehood", "tsc --watch-all=1",
    # codex on #387 (gate round 11): a -regex / protected-dir-name find filter is never a safe -delete carve-out
    "find . -regextype posix-extended -regex '.+' -delete", "find . -regex '.+' -delete",
    "find . -name workflows -delete", "find . -iname WORKFLOWS -delete", "find . -name .github -delete",
    "find . -path '*/.github' -delete",
    # codex on #387 (gate round 11): git accepts unambiguous long-option abbreviations (--work==--worktree,
    # --har==--hard, --no-dry==--no-dry-run, --excl==--exclude)
    "git reset --har main", "git reset --mer origin/main", "git reset --kee HEAD~1",
    "git restore --staged --work .github/workflows/ci.yml",
    "git clean -fd --dry-run --no-dry", "git clean -fd --no-dry", "git clean -fd --excl node_modules",
    # codex on #387 (gate round 11): `command` options must not hide the cd from cwd tracking
    "command -p cd .github && touch workflows/x.yml", "command -- cd .github && touch workflows/x.yml",
    # codex on #387 (gate round 12): a value-taking short option BEFORE -f/-e in a grep cluster must consume its
    # value, so the real path operand is still checked (rg -r is --replace, grep -r is recursive: per-program arity)
    "rg -e SECRET -rabcde .env", "rg -nf.env .", "rg -if.env .", "grep -rnf.env .",
    # codex on #387 (gate round 12): a backslash in a find -name/-path pattern is a find escape (`ci.y\\ml` matches
    # `ci.yml`), so the fnmatch safe-filter proof is unsound — fail closed, no -delete carve-out
    r'find . -name "ci.y\\ml" -delete', r"find . -iname 'C\\I.yml' -delete", r"find . -path '*/workflo\\ws' -delete",
    # codex on #387 (gate round 12): `--` ends options, so a `--staged`/`--worktree` AFTER it is a pathspec and the
    # restore still rewrites the worktree copy
    "git restore -- --staged .github/workflows/ci.yml", "git restore -- --worktree .github/workflows/ci.yml",
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
    # round 7
    "rg -e .env README.md", "grep --regexp=.env README.md", "rg -T test .env README.md", "rg -M 200 .env README.md",
    "rg -E utf-8 .env README.md", "rg --color never .env README.md", "grep -E .env README.md", "rg -g '*.ts' .env src/",
    "rg -t ts .env src/", "mv x.yaml .github/", "cp ci.yml .github/CODEOWNERS", "cp -R src .github/scripts", "rsync -a docs/ build/docs/",
    "cp -r workflows docs/", "mv -t docs/ workflows", "pnpm test", "vitest run", "git commit -m 'watch mode'", "bd update x --notes '--watch'",
    "rm -rf node_modules/.cache", "rm -rf $HOME/tmp/x",
    # bash semantics: a # comment runs to END OF LINE, so ; and && inside it do not separate statements (co-author gate P1 was wrong)
    "echo foo # x; sudo ls", "echo foo # x && sudo ls",
    # round 10
    "uv run --env-file .env.example gh pr comment 1 -b hi", "uv --env-file .env.example run git status", "pnpm exec --dir app gh pr view 1",
    "uv run --env-file scratch/dev.env.example pytest", "npx --package typescript tsc --noEmit",
    "git reset", "git reset --soft HEAD~1", "git reset --mixed HEAD", "git reset HEAD -- src/x.ts", "git reset -- .github/workflows/ci.yml",
    "git reset --hard", "git reset --hard HEAD", "git reset --keep", "git reset HEAD~1", "git reset origin/main -- src/",
    "find . -name '*.pyc' -delete", "find build -delete", "find . -name '*.pyc' -type f -delete", "find src -type f -delete",
    "find . -name '*.yml'", "find .github -name '*.yml'", "find . -name __pycache__ -delete", "find . -iname '*.orig' -delete",
    "find node_modules -name '*.map' -delete", "find .github -name '*.yml' -exec cat {} \\;", "find /tmp/x -delete",
    # codex on #387
    "uv run --env-file=.env.example git status", "pnpm --dir=app exec gh pr view 1", "pnpm -Capp exec gh pr view 1",
    "uvx --env-file=.env.example gh pr view 1", "npx --userconfig=.npmrc gh pr view 1", "uvx --from=ruff ruff check .",
    "find . -name '*.pyc' -a -delete", "find . -type f -name '*.pyc' -and -delete", "find . -name '*.pyc' -print -delete",
    r"find build \( -name '*.o' -o -name '*.a' \) -delete", "find src ! -name '*.ts' -delete", "find . ! -name '*.ts' -print",
    r"find . -name '*.ts' -exec grep -l ';' {} \;", "if [ ! -f .env ]; then echo missing; fi", "time ! false",
    "printf '%s\\n' '(' ')' ';'",
    "if grep -q x README.md; then echo y; fi", "while read -r l; do echo $l; done < list.txt", "if git push origin gc-ia/x; then echo ok; fi",
    "until curl -sf http://localhost; do echo w; done", "if [ -f .env ]; then echo present; fi", "if test -e .env; then :; fi",
    "if ! grep -q x README.md; then echo n; fi", "while ! curl -sf http://localhost; do echo w; done",
    "grep -fpatterns.txt .", "grep -rf patterns.txt src/", "grep -ie KEY src/x.ts", "grep -rne KEY src/", "rg -f pats.txt src/",
    "grep -rif pats.txt .", "grep -c -e .env README.md", "grep -ie .env README.md", "grep -rn KEY src/", "grep -A3 KEY src/x.ts",
    "command cd src && touch x.ts", "builtin cd docs && cat README.md", "command cd .github && cat workflows/ci.yml",
    "git restore --staged .github/workflows/ci.yml", "git restore --staged -- .github/workflows/ci.yml", "git restore -S .github/workflows/ci.yml",
    # ghastly #42 (gs-rtbb): index-only ancestor and ordinary source restores stay as on main
    "git restore --source main --staged .", "git restore -s main --staged .", "git restore --staged --source=main -- .github",
    "git restore --staged --source=main src/x.ts",
    # ghastly #42 + co-author #867 extra allow cases
    "find . -name '*.pyc' -delete -print", "find build -type d -empty -delete", "find build ! -name '*.pyc' -delete", "find build -delete -name '*.pyc'",
    "find . -name '*.pyc' -and -type f -delete", "find . -path '*.pyc' -delete", "find . -name '*.pyc' -iname '*.pyc' -delete",
    r"find build \! -name '*.pyc' -delete", "find build -name '*.pyc' , -delete", "find . -name '*.pyc' -o -name '*.yaml'",
    "npm exec --workspace=app gh pr view 1", 'uv run --env-file="my dir/.env.example" git status', 'uv run --env-file "my dir/.env.example" git status',
    'pnpm exec --dir="my dir/app" gh pr view 1', "uv run --env-file= gh pr view 1",
    # round 8
    "git checkout main", "git checkout -b x", "git checkout -- src/", "git checkout main -- src/x.ts", "git restore src/x.ts",
    "git restore --source main src/", "git restore --staged .", "git checkout main -- .github/CODEOWNERS", "git checkout -b x main",
    "git switch main", "git checkout gc-ia/x", "git restore --staged -- .", "git stash list", "git stash pop", "git stash drop",
    "git stash", "git stash -u", "git stash push -m wip", "git stash push -- src/", "git stash save wip", "git stash show -p",
    "mv -t . /tmp/file", "mv --target-directory . /tmp/file", "mv --target-directory=. /tmp/file", "mv -t docs /tmp/file",
    "mv /tmp/file .", "mv -t . x.yml y.yml",
    "jest -w 2", "rg -w foo src/", "vitest run", "tsc -p tsconfig.json", "tsc --noEmit", "pnpm vitest run", "git commit -m 'vitest -w'",
    "pnpm exec vitest run", "npx tsc --noEmit", "pnpm vitest", "vitest --run", "curl -w '%{http_code}' x",
    # round 9
    "cd src && touch x.ts", "cd .github && cat workflows/ci.yml", "cd $DIR && npm test", "cd .github/workflows && cat ci.yml",
    "cd .github/workflows && cd ../.. && touch x.ts", "pushd .github/workflows && popd && touch x.ts", "env -C src touch x.ts",
    "env -C .github/workflows cat ci.yml", "env -C .github/workflows true && touch x.ts", "cd $DIR && touch x.ts", "cd $DIR && rm -rf build",
    "cd && touch x.ts", "cd .github/workflows && cd - && touch x.ts", "cd .github && ls workflows", "cd /tmp && rm -rf build",
    "cd .github/workflows && git status", "cd .github/workflows && grep -n on: ci.yml",
    "xargs -a list.txt echo", "/usr/bin/time -o /tmp/t.txt true", "xargs -a .env.example echo", "xargs -n 1 echo", "/usr/bin/time -f %e true",
    "npx --package typescript tsc --noEmit", "npm exec --package=prettier -- prettier --check .", "npx -p typescript tsc -p tsconfig.json",
    "pnpm --filter web exec tsc --noEmit", "npm exec --package vercel -- vercel build", "npx --package vercel vercel --version", "npm exec -w app -- tsc --noEmit",
    # retained from ghastly #40 (worker gs-28ql)
    "mv x .", "mv /tmp/layout.yaml .", "mv build/out.yaml ./", "mv /tmp/a .", "bd update x --design-file design.md",
    "gh pr comment 1 --body-file=notes.md", "bd update x --design-file=design.md", "gh pr comment 1 --body-file=.env.example",
    "bd update x --design-file=.env.template", "gh pr comment 1 --body=.env", "gc bd update x --description=prod.env",
    "grep -r .env README.md", "grep --color .env README.md", "rg --files-with-matches .env README.md", "grep --files-without-match .env README.md",
    "xargs -a paths.txt echo", "xargs --arg-file=.env.example echo", "xargs -apaths.txt echo", "env -u DEBUG id", "time -o timing.txt id",
    "timeout -k 1 5 id", "env rg .env README.md", "timeout 5 grep -e .env README.md", "command env timeout 5 rg --regexp=.env README.md",
    "env git commit -m .env", "env gh pr comment 40 --body=.env", "env -S 'rg .env README.md'", "env -S 'git commit -m .env'",
    "git clean -fdx -e node_modules src/", "git clean -fd --exclude '*.log' -- src/", "git clean -fdeignored src/", "git clean -fd -- -e",
    "git clean -fdn", "git clean -nd", "git clean -fdne node_modules", "git clean -fd -e node_modules -n", "git clean -fd --exclude node_modules --dry-run",
    "jest --watchAll=false", "vitest --watch=0", "pnpm test -- --watch=false", "jest --watchAll=OFF", "tsc --watch-all=no", "vitest -t --watch",
    "bd update x --notes '--watchAll=true'",
    # codex on #387 (gate round 11): abbreviations of index-only / safe git options stay allowed; so do
    # non-workflow find name filters and the abbreviated command-wrapper cd
    "git reset --sof HEAD~1", "git reset --mix HEAD", "git restore --stag .github/workflows/ci.yml",
    "git clean -fd --dry", "command -p cd src && touch x.ts", "find . -iname '*.ORIG' -delete",
    "find . -name 'readme.md' -delete",
    # codex on #387 (gate round 12): with the per-program arity, a value-taking short option that eats the `f`/`e`
    # means NO path is read — rg -r (replace) and grep -m (max-count) both swallow the cluster tail
    "rg -rf.env .", "grep -m5f.env x", "rg -tf.env src/",
    # the `--staged`/`-S` BEFORE `--` is the real mode: index-only restores stay allowed
    "git restore --staged -- .github/workflows/ci.yml", "git restore -S -- .github/workflows/ci.yml",]
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
# round 8: a PATHLESS stash is blocked only while .github/workflows has uncommitted changes (tracked dirty / untracked with -u)
def git_repo(name, commit_workflow, dirty_tracked, untracked):
    d = os.path.join(tmp, name)
    os.makedirs(os.path.join(d, ".github/workflows"))
    subprocess.run(["git", "-C", d, "init", "-q", "-b", "gc-pilot/demo"], check=True)
    if commit_workflow:
        open(os.path.join(d, ".github/workflows/ci.yml"), "w").write("name: ci\n")
        subprocess.run(["git", "-C", d, "add", "-A"], check=True)
        subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", "init"], check=True)
    if dirty_tracked:
        open(os.path.join(d, ".github/workflows/ci.yml"), "a").write("# edit\n")
    if untracked:
        open(os.path.join(d, ".github/workflows/new.yml"), "w").write("name: new\n")
    return d
dirty = git_repo("dirty-tracked", True, True, False)
untracked = git_repo("dirty-untracked", True, False, True)
for c in ("git stash", "git stash -u", "git stash --include-untracked", "git stash push", "git stash push -m x", "git stash -a", "git checkout ."):
    expect("guard-bash.py", {"command": c}, 2, c + " [workflows dirty]", cwd=dirty, extra_env={"CLAUDE_PROJECT_DIR": dirty})
for c in ("git stash list", "git stash push -- src/", "git stash save wip", "git stash pop", "git status"):
    expect("guard-bash.py", {"command": c}, 0, c + " [workflows dirty]", cwd=dirty, extra_env={"CLAUDE_PROJECT_DIR": dirty})
for c in ("git stash -u", "git stash --include-untracked", "git stash --all", "git stash -a", "git stash push -u"):
    expect("guard-bash.py", {"command": c}, 2, c + " [workflow untracked]", cwd=untracked, extra_env={"CLAUDE_PROJECT_DIR": untracked})
for c in ("git stash", "git stash push", "git stash push -m x"):
    expect("guard-bash.py", {"command": c}, 0, c + " [workflow untracked only]", cwd=untracked, extra_env={"CLAUDE_PROJECT_DIR": untracked})
for c in ("git reset --hard HEAD", "git reset --hard", "git reset --merge", "git reset --keep HEAD", "git reset --har HEAD"):
    expect("guard-bash.py", {"command": c}, 2, c + " [workflows dirty]", cwd=dirty, extra_env={"CLAUDE_PROJECT_DIR": dirty})
for c in ("git reset --soft HEAD~1", "git reset HEAD -- src/x", "git reset", "git reset --mixed", "git reset --sof HEAD~1"):
    expect("guard-bash.py", {"command": c}, 0, c + " [workflows dirty]", cwd=dirty, extra_env={"CLAUDE_PROJECT_DIR": dirty})
STASH_CASES = 7 + 5 + 5 + 3 + 5 + 5
for p in EDIT_BLOCK:
    expect("guard-edit.py", {"file_path": p}, 2, "edit " + p)
for p in EDIT_ALLOW:
    expect("guard-edit.py", {"file_path": p}, 0, "edit " + p)
# Read tool: secrets blocked (incl. suffix .env), templates + workflows readable
READ_BLOCK = [".env", ".env.local", "/tmp/prod.env", "scratch/runpod.env", "~/.claude/projects/x/MEMORY.md", ".gc/runtime/secrets/x", "$PWD/.env", "${PWD}/.env.local"]
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
total = len(BASH_BLOCK) + len(BASH_ALLOW) + len(EDIT_BLOCK) + len(EDIT_ALLOW) + len(READ_BLOCK) + len(READ_ALLOW) + len(GREP_BLOCK) + len(GREP_ALLOW) + STASH_CASES + 8 + 9
print(f"{total - fails}/{total} guard cases pass")
sys.exit(1 if fails else 0)
