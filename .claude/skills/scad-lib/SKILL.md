---
name: scad-lib
description: List vendored OpenSCAD libraries or add a new one. 'list' parses libs/README.md and prints the capability table. 'add' shallow-clones a git repo into libs/ and appends a stub entry; Claude/user fills in the capability summary and 3-5 use<> examples.
---

# scad-lib

Manage the vendored library surface that `/scad-new` reads before
authoring SCAD. This skill is the one sanctioned path for introducing new
third-party geometry into the repo — do not hand-clone into `libs/`.

## Subcommands

### `list`

Parse `libs/README.md` and print the library table. Used by humans and
by `/scad-new` to pick the right primitive.

```bash
python3 .claude/skills/scad-lib/scripts/lib.py list
```

### `add`

Shallow-clone a git repo into `libs/<name>/` and insert a stub entry at
the top of `libs/README.md`. You (Claude) or the user must then edit the
stub to fill in the capability summary and 3-5 representative `use <>`
(or `include <>`) examples.

```bash
python3 .claude/skills/scad-lib/scripts/lib.py add \
  --name threads-scad \
  --url https://github.com/rcolyer/threads-scad
```

## Output contract

Both subcommands emit JSON to stdout. Exit non-zero on failure.

```json
// list
{
  "verdict": "listed_ok",
  "libs": [
    {"name": "NopSCADlib", "summary": "...", "use_examples": ["use <NopSCADlib/vitamins/...>;", "..."]}
  ]
}

// add
{
  "verdict": "added_ok",
  "name": "threads-scad",
  "path": "libs/threads-scad",
  "commit": "4ae9aeb...",
  "readme_updated": true
}
```

## Stub entry format

After `add`, `libs/README.md` gains a block like:

```markdown
## <name>

- Path: `libs/<name>`
- Commit: `<sha>`
- Upstream: `<url>`
- Summary: _TODO — fill in one-line capability summary._
- Use examples:
  - _TODO_
  - _TODO_
  - _TODO_
```

Fill in the TODOs before the library is discoverable to `/scad-new`.

## When not to use

- Do not use for OpenSCAD builtins — they live in openscad, not libs/.
- Do not use to pin a submodule to a newer commit. Delete and re-add, or
  edit the commit block manually and update with `git -C libs/<name>
  checkout <sha>`.
