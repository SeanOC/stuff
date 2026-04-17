---
name: scad-export
description: Export an OpenSCAD model to STL and verify watertightness via trimesh. Emits bbox, triangle count, and watertight status as JSON; exits non-zero on non-watertight output. Must be invoked only after the user has reviewed renders and explicitly approved export.
---

# scad-export

Produce a printable STL and verify it is manifold. STL export is the
commit point of the iteration loop — once the file lands in `exports/` it
is the intended-to-print artifact.

## Human-in-the-loop gate (R16) — MANDATORY

**Do not invoke this skill without explicit user approval.** The approval
handshake is a behavioral contract, not a technical pre-condition the
script can verify.

Before running `scripts/export.py`:

1. Ensure the model has just been rendered (fresh PNGs in `renders/<name>/`).
2. Present the four multi-angle PNGs and the latest measurement summary
   to the user inline.
3. Ask explicitly: *"Export `<name>` to `exports/<name>.stl`?"*
4. Proceed **only** on an affirmative reply from the user in their next
   message. Do not assume. Do not infer. Do not batch with other actions.

If the user has not approved in the immediately preceding turn, stop and
ask first.

## Inputs

Wraps `python3 .claude/skills/scad-export/scripts/export.py`. Script
accepts:

| Flag                 | Purpose                                             |
|----------------------|-----------------------------------------------------|
| `--model PATH`       | Path to the `.scad` file (required).                |
| `--name NAME`        | Output stem: `exports/<name>.stl`. Default: model stem. |
| `-D key=value`       | Parametric overrides, forwarded to openscad.        |

## Output contract

Prints one JSON object to stdout. Exits non-zero on any failure.

```json
{
  "verdict": "export_ok",
  "model": "models/motor_mount.scad",
  "stl": "exports/motor_mount.stl",
  "bbox_mm": [[-30.0, -20.0, 0.0], [30.0, 20.0, 7.0]],
  "triangle_count": 2048,
  "is_watertight": true,
  "warnings": []
}
```

Verdicts:

- `export_ok` — STL written, trimesh confirms watertight.
- `not_watertight` — STL written but fails the manifold check. **Exit
  non-zero.** Do not treat this output as printable.
- `export_failed` — openscad error, unresolved `use <>`, missing STL, or
  empty STL. Exit non-zero.

## Example

```bash
# After user approval:
python3 .claude/skills/scad-export/scripts/export.py \
  --model models/motor_mount.scad
```

A non-watertight STL means the model has ambiguous geometry — most often
overlapping but unioned solids, coplanar faces on a boolean subtract, or
a zero-thickness wall. Fix the model, re-render, re-ask for approval.
