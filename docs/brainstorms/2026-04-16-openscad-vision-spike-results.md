---
date: 2026-04-16
topic: openscad-vision-spike-results
---

# OpenSCAD Vision Spike — Results

Executed in the same session as the requirements doc to resolve the blocking
question: **is Claude's multimodal vision on orthographic PNGs sufficient to
judge OpenSCAD geometry against a stated spec?**

## Setup

- Workspace: `/home/seanoconnor/projects/stuff/spike/`
- OpenSCAD 2021.01 (apt). Note: production plan still uses nightly AppImage for
  Manifold; for PNG rendering the engine choice is functionally irrelevant,
  only speed differs. AppImage download still in background.
- Headless path: `xvfb-run openscad` with `--camera=eye,center`,
  `--projection=orthogonal`, `--viewall`, 1024x1024 PNGs.
- Cameras: `top` (0,0,300 → origin), `front` (0,-300,0 → origin),
  `side` (300,0,0 → origin), `iso` (200,-200,150 → origin).
- Test model: parametric motor mount plate (60x40x5 plate, 20mm bore, 25mm x
  2mm raised boss, 4 M3 mounting holes on 50x30 pattern with 6mm x 3mm
  counterbores). Ground truth kept in `spike/ground_truth/`.

## Protocol

1. **Turn 0** — Author (Claude) writes `iter/v0.scad` from the prompt only.
   Result: v0 happened to match GT on first pass, making the iteration test
   trivial. **Pivoted** to a perturbed starting point.
2. **Perturbed v0** — evaluator introduces 3 hidden defects into a copy:
   - D1: bore diameter 22 (spec 20) — ~10% oversize, subtle
   - D2: hole_dx 60 (spec 50) — mounting holes pushed beyond plate edge
   - D3: counterbores omitted entirely
3. **Turn 1** — Author views PNGs, compares to spec (without looking at source).
4. **Turn 2** — quantitative check (pixel measurement) on remaining uncertainty.

## Turn 1 — Vision-only critique of perturbed v0

Author's observations from `renders/v0_perturbed/{top,iso,front}.png`:

| Defect | Author flag | Confidence | Correct? |
|--------|-------------|------------|----------|
| D2 (hole spacing too wide) | "Holes are cut into the plate's long edges, not interior positions" | high | yes |
| D3 (counterbores missing) | "No orange rings around holes in top view, top face looks bare" | high | yes |
| D1 (bore 10% oversize) | "Bore/boss proportion looks possibly off, needs measurement" | uncertain | partial (flagged, not confirmed) |
| *hallucinated defects* | none | -- | -- |

Fix D2 + D3 in `iter/v1.scad`; leave bore for measurement.

## Turn 2 — Quantitative check on bore diameter

Pixel-measured bore width vs known 60mm plate width in orthographic top view:

| Render | plate px | bore px | bore mm | vs spec |
|--------|----------|---------|---------|---------|
| GT | 832 | 278 | 20.05 | +0.05 mm |
| v1 (bore not yet fixed) | 832 | 304 | 21.92 | +1.92 mm |
| v2 (bore fixed to 20) | 832 | 278 | 20.05 | +0.05 mm |

Pixel measurement from orthographic projection is decisive and cheap. The
scale factor (60 mm / 832 px = 0.0721 mm/px) lets any linear feature be read
directly from the PNG.

## Findings

1. **Vision is strong for structural defects** — count, presence/absence,
   topology (edge vs interior), feature composition. Caught 2/3 defects with
   high confidence and zero hallucinations.
2. **Vision is weak for subtle dimensional drift (~10%)**. Correctly flagged
   as "uncertain, needs measurement" rather than hallucinating a value.
3. **Pixel measurement from an orthographic PNG is cheap and decisive.**
   One known anchor (plate width) gives mm/px; every other dimension follows.
4. **Convergence was fast**: 2 substantive iteration turns from a 3-defect
   starting point. No oscillation, no regressions.

## Decision

**Pass, with one architectural addition.**

The R7-R14 skill shape is sound. Add one requirement:

> **/scad-render must emit measured dimensions alongside PNG paths.**
> Use orthographic top/front/side views with the plate (or a known anchor)
> to establish a mm/px scale, then report bbox + all circular feature
> diameters. Claude reads the numbers, not just looks at the pixels.

This is cheaper than running full STL export on every iteration (which R9 /
R15 already cover for final verification), and it closes the single vision
weakness the spike exposed.

## Impact on requirements

- R8 (`/scad-render`): expand to include dimensional measurement output, not
  just PNGs. Skill output schema: `{angle: png_path}` plus
  `{bbox: [x,y,z], circles: [{d, center}, ...], scale_mm_per_px}`.
- Success criterion "bounding box within +/-1mm of stated dimensions" -
  now implementable via the pixel-scale approach; no full STL export needed
  per render.
- R16 (pre-export human confirmation) remains valuable — dimensional probes
  close the vision gap but don't replace user judgment on the overall design.

## Follow-through for planning

- `/scad-render` must render with `--projection=orthogonal` for the three
  principal views; iso can stay perspective for visualization.
- Measurement helper is a short Python script using PIL + numpy (both
  available via apt as `python3-pil` / `python3-numpy`). No pip required.
- A "known anchor" in each model — e.g. a parameter like `PRINT_ANCHOR_X`
  that matches the outermost bbox — is the cleanest way to calibrate scale.
  Alternative: parse the model source for the outer bbox and compute anchor
  automatically.
- The iteration loop terminates much faster when the render output includes
  numbers. Without numbers, the Author cannot resolve dimensional
  uncertainty and must either make speculative edits or ask the user.
