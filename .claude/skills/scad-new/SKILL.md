---
name: scad-new
description: Author a new OpenSCAD model from natural-language intent. Writes to models/, enforces PRINT_ANCHOR_BBOX convention, then delegates to scad-render for multi-angle PNGs + pixel-measured dimensions. Edit-in-place by default; opt-in versioned snapshots.
---

# scad-new

Turn an intent ("4-hole motor mount, 60×40, M3 clearance with 6 mm
counterbores") into a rendered first draft. This skill is the entry point
to the iteration loop:

1. **You** (Claude) write the SCAD body from intent + library surface.
2. `scripts/new.py` persists the file and invokes `scad-render`.
3. You read the JSON + PNGs and decide what to edit.

## Before writing any SCAD — mandatory reading

Read these, in order, every time:

1. **`libs/README.md`** — the vendored library index. Prefer vendored
   primitives over hand-rolled geometry. If the intent involves threads,
   fasteners, or board-snap geometry, the library almost certainly has it.
2. **Existing file at the target path**, if re-authoring. Edit-in-place is
   the default; versioning is opt-in via `--versioned`.

## Invariants every model must satisfy

- **`PRINT_ANCHOR_BBOX = [x, y, z];`** declared at the top of the model,
  matching the outermost printed bbox in mm. The render skill parses this
  to calibrate pixel→mm scale. Without it, dimensions cannot be measured.
- **No `include <>` without a vendored path.** Use `use <lib/file.scad>;`
  referencing entries from `libs/README.md`. `BOSL2` is the one exception —
  it requires `include <BOSL2/std.scad>`.
- **No magic numbers where parameters belong.** Authored `.scad` files
  should expose tunable parameters at the top (plate dimensions, hole
  diameters, wall thicknesses) so the iteration loop can override via
  `-D name=value`.

## Inputs

Wraps `python3 .claude/skills/scad-new/scripts/new.py`. Script accepts:

| Flag                 | Purpose                                                    |
|----------------------|------------------------------------------------------------|
| `--name NAME`        | Stem for `models/<name>.scad` (required).                  |
| `--body-file PATH`   | File containing the SCAD body. If omitted, reads stdin.    |
| `--versioned`        | Append `_NNN` and increment on repeat; otherwise overwrite.|
| `--no-render`        | Skip invoking scad-render (write-only mode).               |
| `-D key=value`       | Forwarded to scad-render for this invocation.              |
| `--angles a,b,c`     | Forwarded to scad-render.                                  |

## Output contract

Prints one JSON object to stdout. Exits non-zero if the write fails or
render fails.

```json
{
  "verdict": "authored_ok",
  "model": "models/motor_mount.scad",
  "versioned": false,
  "render": {
    "verdict": "rendered_ok",
    "renders": { "top": "...", "front": "...", "side": "...", "iso": "..." },
    "measurements": { "...": "..." },
    "warnings": []
  }
}
```

If `--no-render` is set, `render` is `null`. If render fails, the outer
verdict is `render_failed` and exit code is non-zero.

## Versioning

- Default: edit-in-place. Re-running overwrites `models/<name>.scad`.
- `--versioned`: writes `models/<name>_001.scad`, then `_002.scad`, etc.
  Use when you want snapshots mid-iteration.

## Example session shape

```bash
# Claude authors motor_mount.scad body, pipes via stdin:
python3 .claude/skills/scad-new/scripts/new.py --name motor_mount <<'SCAD'
$fn = 96;
PRINT_ANCHOR_BBOX = [60, 40, 5];
plate_w = 60; plate_d = 40; plate_t = 5;
...
SCAD
```

After reading the returned JSON, look at `renders/motor_mount/*.png` to
judge shape, and the `measurements.circles_top` list to confirm feature
counts and diameters.
