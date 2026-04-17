---
name: scad-render
description: Render an OpenSCAD .scad file to multi-angle PNGs with pixel-measured dimensions. Orthographic top/front/side + perspective iso. Returns JSON with render paths, plate bbox, scale_mm_per_px, and detected circles (holes + counterbore rings).
---

# scad-render

Render a parametric OpenSCAD model to four PNGs (top/front/side/iso) and
emit dimensional measurements alongside the image paths. Designed for the
iteration loop: the model gets edited, this skill runs, you read the
numbers and the images, decide what to change, repeat.

## When to use

- After writing or editing a `.scad` file in `models/`
- To re-render with parametric overrides (e.g. `-D plate_t=8`) without
  editing source
- Before `/scad-export` so you can confirm the model is what you intend

## Inputs

The skill wraps `python3 .claude/skills/scad-render/scripts/render.py`.
The script accepts:

| Flag                 | Purpose                                              |
|----------------------|------------------------------------------------------|
| `--model PATH`       | Path to the `.scad` file (required).                 |
| `--name NAME`        | Subdir under `renders/`. Default: model stem.        |
| `-D key=value`       | Parametric override, repeatable. Passed to openscad. |
| `--angles a,b,c`     | Subset of {top,front,side,iso}. Default: all four.   |
| `--known-bbox-mm X,Y`| Override the plate bbox used for scale calibration.  |

## Output contract

Prints one JSON object to stdout. Exits non-zero on any failure.

```json
{
  "verdict": "rendered_ok",
  "model": "models/motor_mount.scad",
  "renders": {"top": "...", "front": "...", "side": "...", "iso": "..."},
  "measurements": {
    "bbox_mm": [60.0, 40.0],
    "scale_mm_per_px": 0.072,
    "circles_top": [
      {"diameter_mm": 20.05, "center_mm": [0.0, 0.0], "kind": "hole",
       "area_px": 60312}
    ]
  },
  "warnings": []
}
```

`verdict` is `rendered_ok` on success, `render_failed` on any error (with
a populated `warnings` or `error` field).

## PRINT_ANCHOR_BBOX convention

The dimensional probe calibrates pixel→mm scale against a known plate
bbox. Every model should declare a top-level constant:

```scad
PRINT_ANCHOR_BBOX = [60, 40, 5];  // outermost plate: x, y, z in mm
```

The render script parses this from the model source. If absent and
`--known-bbox-mm` is not supplied, the script falls back to a warning and
skips `measurements` (PNGs still produced).

## Example

```bash
python3 .claude/skills/scad-render/scripts/render.py \
  --model models/motor_mount.scad \
  -D plate_t=8
```

After reading the JSON, look at the four PNGs to judge overall shape and
proportions. Use the `circles_top` list to confirm feature counts and
diameters — vision alone is weak at detecting ~10% dimensional drift.
