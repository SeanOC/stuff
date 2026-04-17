---
date: 2026-04-16
status: active
topic: openscad-ai-workflow
origin: docs/brainstorms/2026-04-16-openscad-ai-workflow-requirements.md
spike: docs/brainstorms/2026-04-16-openscad-vision-spike-results.md
depth: standard
---

# feat: OpenSCAD AI Workflow Skills

Build four project-local Claude Code skills (`/scad-new`, `/scad-render`,
`/scad-export`, `/scad-lib`) that let Claude iteratively author parametric
OpenSCAD models with multi-angle visual feedback and pixel-measured
dimensional checks, plus STL export with `trimesh` watertight verification.
Libraries (NopSCADlib, threads-scad, MCAD) vendored under `libs/` and exposed
via `OPENSCADPATH`.

## Problem Frame

See origin. OpenSCAD is code-first and a strong fit for LLM-assisted design,
but a terminal agent needs visual feedback, render boilerplate abstracted
away, fast iteration, and library access. The vision spike
(`docs/brainstorms/2026-04-16-openscad-vision-spike-results.md`) validated
that multi-angle orthographic PNGs plus a pixel-measured dimensional probe
give Claude enough signal to converge in 2 substantive turns on a perturbed
motor mount, with zero hallucinated defects.

## Requirements Trace

Origin requirements R1-R16 map to implementation units below:

| Req | Unit(s) | Notes |
|-----|---------|-------|
| R1 (nightly AppImage) | U1 | AppImage already downloaded to `spike/OpenSCAD.AppImage`; U1 moves it and symlinks. |
| R2 (workspace layout) | U2 | Target dirs already exist empty. U2 adds `.claude/settings.json` and `.gitignore`. |
| R3 (`openscad` on PATH) | U1 | Symlink `~/.local/bin/openscad`. |
| R4 (vendored libs via OPENSCADPATH) | U3, U4 | Libs under `libs/`; path set per-invocation in render helper. |
| R5 (libs/README.md index) | U3 | Short capability index, 3-5 `use <>` lines per lib. |
| R6 (no BOSL2) | U3 | Explicitly excluded. |
| R7 (`/scad-new` skill) | U8 | SKILL.md instructs Claude to consult `libs/README.md`. |
| R8 (`/scad-render` multi-angle + dims) | U4, U5, U7 | Helper + SKILL wrapper. |
| R9 (`/scad-export` + trimesh) | U6, U9 | Watertight gate; non-zero exit on fail. |
| R10 (`/scad-lib`) | U10 | Clone + register pattern. |
| R11 (`-D` overrides) | U4, U7, U8, U9 | Pass-through in render/export helpers. |
| R12 (iteration loop) | U7, U8 | State-machine design (see §High-Level Design). |
| R13 (edit-in-place, opt-in versioning) | U8, U9 | Default edit; versioning via flag. |
| R14 (non-zero exit on failure) | U4, U6 | Parse OpenSCAD stderr + check PNG/STL non-empty. |
| R15 (trimesh post-export check) | U6 | bbox, triangle count, watertight. |
| R16 (confirm before export) | U9 | SKILL.md gate; `/scad-export` refuses without explicit user go-ahead. |

## Scope Boundaries

Carried from origin (see origin):
- No MCP server, no web UI, no Claude Desktop integration.
- No text-to-image seed step.
- No slicer / G-code / printer integration.
- No BOSL2, dotSCAD, or BOLTS by default (`/scad-lib` can add later).
- No benchmark or eval harness for OpenSCAD generation quality. (The spike
  covered the one-shot validation question.)

## Existing Patterns to Reuse

- `spike/render.sh` — proven headless render harness with the
  correct camera values. Port into `lib/render.py` (Python for JSON emit +
  dimensional probe integration).
- Gemini-imagegen SKILL.md
  (`~/.claude/plugins/cache/every-marketplace/compound-engineering/2.28.0/skills/gemini-imagegen/SKILL.md`)
  as a reference shape for "skill calls a script and presents structured
  output" — matches the script-first architecture learning.
- Script-first skill architecture pattern: deterministic mechanical work
  (rendering, measurement, watertight check) lives in bundled scripts that
  emit JSON. SKILL.md orchestrates and presents results (institutional
  learning, severity: high).

## High-Level Technical Design

*This illustrates the intended approach and is directional guidance for
review, not implementation specification. The implementing agent should treat
it as context, not code to reproduce.*

### Skill layout

```
.claude/skills/
  scad-new/
    SKILL.md              (frontmatter: name, description; orchestrates)
    scripts/new.py        (takes NL intent → writes .scad → calls render)
  scad-render/
    SKILL.md
    scripts/render.py     (the render+measure helper; emits JSON)
  scad-export/
    SKILL.md
    scripts/export.py     (STL + trimesh verify; emits JSON)
  scad-lib/
    SKILL.md
    scripts/lib.py        (list/add libs)
  _lib/                   (shared helpers, imported by the scripts above)
    openscad.py           (AppImage path, OPENSCADPATH assembly, subprocess)
    measure.py            (PIL+numpy pixel measurement against a known bbox)
    schema.py             (pydantic-lite dataclasses for JSON output)
settings.json             (allowed-tools for openscad, xvfb-run, python3)
```

### Iteration loop as state machine (R12)

```
┌─ WRITE ─┐   user intent
│         ▼
│     iter/v_N.scad ──► RENDER ──► {pngs, dims, bbox, circles}
│                          │
│                          ▼
│                       MEASURE against stated dims
│                          │
│            ┌──── dims+features match? ────┐
│            │                              │
│         no │                          yes │
│            ▼                              ▼
│         CRITIQUE ◄── Claude vision     CONVERGED
│         (defect list)                     │
│            │                              ▼
└────────────┘                    ask user → EXPORT
```

- Max iterations cap (suggested: 8) to prevent runaway loops.
- Explicit `CONVERGED` vs `NEEDS_REVISION` verdicts emitted by the render
  script; SKILL.md presents both the verdict and the numeric deltas.

### Render helper JSON output (shape sketch)

```json
{
  "model": "models/motor_mount.scad",
  "renders": {
    "top": "renders/motor_mount/top.png",
    "front": "renders/motor_mount/front.png",
    "side": "renders/motor_mount/side.png",
    "iso": "renders/motor_mount/iso.png"
  },
  "measurements": {
    "bbox_mm": [60.0, 40.0, 7.0],
    "scale_mm_per_px": 0.072,
    "circles_top": [{"d_mm": 20.05, "center_mm": [0, 0]}, ...]
  },
  "warnings": ["unresolved use <missing.scad>"],
  "verdict": "rendered_ok"
}
```

### Stakeholder and impact awareness

Single-user personal tooling. Impact scope is the workspace's author. No
shared infrastructure, no downstream consumers, no CI. Risk is bounded to
"skills don't work as expected" — local-only iteration.

## Implementation Units

### U1 — Install OpenSCAD nightly AppImage

- **Goal**: `openscad` binary on PATH, Manifold-capable.
- **Requirements**: R1, R3.
- **Dependencies**: None (AppImage already downloaded).
- **Files**:
  - move `spike/OpenSCAD.AppImage` → `libs/bin/openscad.AppImage`
  - symlink `~/.local/bin/openscad` → `libs/bin/openscad.AppImage`
  - `spike/` remains for spike artifacts; delete the binary from there
- **Approach**: `chmod +x`; verify `openscad --version` reports
  `2025.06.12.ai25773` or later. No test file — this is environment setup.
- **Verification**: `openscad --version` from a shell with `$HOME/.local/bin`
  on PATH.

### U2 — Workspace skeleton + Claude Code settings

- **Goal**: Conventional layout checked in; permissions pre-approved so the
  iteration loop doesn't prompt per `-D` variation (R12 success criterion).
- **Requirements**: R2; resolves origin deferred "Claude Code permissions
  posture" question.
- **Dependencies**: U1.
- **Files**:
  - `models/.gitkeep`, `renders/.gitkeep`, `exports/.gitkeep`, `libs/.gitkeep`
    (dirs already exist empty, just ensure they're tracked)
  - `.claude/settings.json` — allowed-tools patterns for `openscad`,
    `xvfb-run`, `python3 .claude/skills/**/scripts/*.py`
  - `.gitignore` — `renders/*/`, `exports/*.stl`, `libs/bin/*.AppImage`,
    `libs/NopSCADlib/`, `libs/threads-scad/`, `libs/MCAD/` (vendored libs)
- **Approach**: Check in the shell; no tests.
- **Verification**: Manually triggering `xvfb-run openscad ...` under a fresh
  Claude Code session should not prompt for approval.

### U3 — Vendor libraries and index

- **Goal**: NopSCADlib, threads-scad, MCAD cloned under `libs/`, with a
  library index (`libs/README.md`) documenting 3-5 most useful `use <>`
  entry points per library.
- **Requirements**: R4, R5, R6.
- **Dependencies**: None (independent of U1/U2).
- **Files**:
  - `libs/NopSCADlib/` (git clone, shallow)
  - `libs/threads-scad/` (git clone, shallow)
  - `libs/MCAD/` (git clone, shallow)
  - `libs/README.md` (index; hand-written)
- **Approach**: `git clone --depth=1` for each; write README by inspecting
  each library's own README + its top-level `.scad` files and pulling the
  3-5 highest-value entries per library. R6 excludes BOSL2.
- **Verification**: `openscad -D 'dummy=1' <<<'use <NopSCADlib/core.scad>;'`
  resolves without warning when `OPENSCADPATH=libs/` is set.

### U4 — Shared OpenSCAD invocation helper

- **Goal**: `_lib/openscad.py` — centralizes `xvfb-run` + AppImage path +
  `OPENSCADPATH` + `-D` pass-through + stderr/warning parsing + exit code
  discipline (R14).
- **Requirements**: R4, R8 (partial), R11, R14.
- **Dependencies**: U1, U2, U3.
- **Files**:
  - `.claude/skills/_lib/openscad.py` — `render(model, out_dir, view=..., defines=...) → RenderResult`
  - `.claude/skills/_lib/_tests/test_openscad.py` — mocks xvfb-run, asserts
    OPENSCADPATH assembly, `-D` formatting, detects empty-PNG and
    `unresolved use <>` warnings.
- **Approach**: Subprocess `xvfb-run -a openscad ...`. Parse stderr for
  `WARNING: Can't open include file` / `Can't find library`. Non-zero exit
  if PNG missing, zero-length, or warnings present that indicate unresolved
  `use <>`.
- **Test scenarios** (for `_tests/test_openscad.py`):
  - T1: render a trivial `cube([10,10,10])` — produces non-empty PNG, exit 0.
  - T2: render a `.scad` with `use <missing.scad>;` — non-zero exit, stderr
    contains the missing reference.
  - T3: pass `-D x=5` and verify helper forwards it verbatim.
  - T4: OPENSCADPATH covers `libs/` — `use <NopSCADlib/core.scad>` resolves.
  - T5: empty-PNG case (simulated) — non-zero exit.

### U5 — Shared measurement helper

- **Goal**: `_lib/measure.py` — orthographic-PNG pixel measurement against
  a known plate bbox; emits bbox_mm, scale_mm_per_px, circles_top.
- **Requirements**: R8 dim probe, origin Success Criteria rubric.
- **Dependencies**: U2 (python3-pil, python3-numpy via apt; already installed
  for the spike).
- **Files**:
  - `.claude/skills/_lib/measure.py` — `measure(top_png, front_png, side_png, known_bbox_mm) → Measurement`
  - `.claude/skills/_lib/_tests/test_measure.py`
- **Approach**: Port the spike's pixel-measurement Python into a reusable
  function. Input: orthographic top PNG + known outermost bbox in mm (the
  model must declare this, see U8). Output: scale mm/px, circle detection
  on top view (simple thresholding — plate fill vs holes/bore), bbox of the
  plate from threshold mask.
- **Test scenarios**:
  - T1: feed `spike/renders/gt/top.png` with plate_bbox=(60,40) — returns
    bore diameter ≈20.0 mm, detects 4 counterbore rings + 1 central bore.
  - T2: feed `spike/renders/v0_perturbed/top.png` — returns bore ≈22.0 mm,
    detects 4 clearance holes but no counterbore rings.
  - T3: blank PNG — raises `MeasurementError`.

### U6 — Shared export/verify helper

- **Goal**: `_lib/export.py` — renders STL via `openscad --render -o`;
  post-export uses `trimesh` for watertight + bbox + triangle count.
  Non-zero exit if not watertight (R9, R14, R15).
- **Requirements**: R9, R14, R15.
- **Dependencies**: U1, U2, U4.
- **Files**:
  - `.claude/skills/_lib/export.py` — `export(model, out_stl, defines=...) → ExportResult`
  - `.claude/skills/_lib/_tests/test_export.py`
- **Approach**: Invoke `openscad --render -o out.stl` through the U4 helper.
  Load with `trimesh.load(out_stl)`. Report `mesh.is_watertight`,
  `mesh.bounds`, `len(mesh.triangles)`. Exit non-zero on non-watertight.
- **Note on trimesh**: not in apt (`python3-trimesh` doesn't exist on Noble).
  Install via `pip install --user --break-system-packages trimesh numpy-stl`
  in U2's settings or document as a setup step. Alternative if pip is
  unavailable: use `openscad --export-format=3mf` and a lightweight
  watertight check (Euler characteristic on the mesh) — flag as a fallback
  option during implementation.
- **Test scenarios**:
  - T1: `spike/ground_truth/motor_mount.scad` exports a watertight STL;
    returns bbox ≈(60, 40, 7), tri count > 0.
  - T2: A deliberately-non-manifold `.scad` (two overlapping cubes with
    coplanar faces and no union) produces a non-watertight STL; helper
    exits non-zero.
  - T3: STL missing after openscad run — non-zero exit.

### U7 — `/scad-render` skill

- **Goal**: Skill that renders a model to multi-angle PNGs + dimensional
  report.
- **Requirements**: R8, R11, R14.
- **Dependencies**: U4, U5.
- **Files**:
  - `.claude/skills/scad-render/SKILL.md` — frontmatter
    `{name: scad-render, description: ...}`. Body orchestrates: reads args
    (model path, optional `-D` overrides), calls `scripts/render.py`,
    presents JSON.
  - `.claude/skills/scad-render/scripts/render.py` — composes U4 + U5,
    writes PNGs into `renders/<model-stem>/`, prints JSON per the shape
    in §High-Level Design.
  - `.claude/skills/scad-render/_tests/test_render.py`
- **Approach**: The skill body (SKILL.md prose) is thin — it explains
  inputs, outputs, and the render→measure convention. Python does the work
  and emits JSON. Claude reads the JSON, not the PNG pixels directly
  (script-first learning).
- **Test scenarios**:
  - T1: render `spike/ground_truth/motor_mount.scad` via the skill path
    (invoke `scripts/render.py` in the test) — JSON verdict `rendered_ok`,
    4 PNGs present, bore ≈20 mm in measurements.
  - T2: render with `-D plate_t=8` override — bbox_mm Z axis reflects the
    override (≈10 mm accounting for boss).
  - T3: model with unresolved `use <>` — JSON verdict `render_failed`,
    warnings populated, non-zero exit.

### U8 — `/scad-new` skill

- **Goal**: NL-to-SCAD first pass; writes `models/<name>.scad`, invokes
  `/scad-render` internally, returns file path + JSON render output so
  Claude can inspect and iterate.
- **Requirements**: R7, R12 (loop), R13 (edit-in-place default, versioning
  opt-in).
- **Dependencies**: U7.
- **Files**:
  - `.claude/skills/scad-new/SKILL.md` — frontmatter + instructions. Must
    include the library-surfacing directive (R7): "Before writing the .scad
    file, read libs/README.md and prefer vendored primitives for threads,
    fasteners, common shapes. Prefer `use <threads-scad/threads.scad>` for
    ISO threads over hand-rolled helix geometry." Also: "Every model must
    declare a top-level `PRINT_ANCHOR_BBOX = [x, y, z];` constant that
    matches the outermost bbox in mm — the render skill uses this to
    calibrate pixel→mm scale."
  - `.claude/skills/scad-new/scripts/new.py` — takes `--intent`, `--name`,
    optional `--versioned` flag; writes file and shells out to the render
    skill.
  - `.claude/skills/scad-new/_tests/test_new.py`
- **Approach**: The prompt-to-SCAD step is Claude itself (SKILL.md
  instructs), not a script. The script handles: write-file-with-name,
  optional `_NNN.scad` suffix if `--versioned`, then invoke render and
  return combined JSON.
- **Test scenarios**:
  - T1: `--intent` "simple parametric box 20x20x10" `--name=test_box` —
    file exists at `models/test_box.scad`, render verdict `rendered_ok`.
  - T2: `--versioned` flag writes `test_box_001.scad` and increments on
    repeat calls.
  - T3: Re-invoke without `--versioned` on existing name — overwrites
    (edit-in-place default).

### U9 — `/scad-export` skill with confirmation gate

- **Goal**: Export STL with watertight check. Refuses to proceed without
  explicit user confirmation (R16).
- **Requirements**: R9, R14, R15, R16.
- **Dependencies**: U6.
- **Files**:
  - `.claude/skills/scad-export/SKILL.md` — frontmatter + instructions.
    Body explicitly tells Claude: "Before invoking this skill, present the
    current multi-angle PNGs to the user and obtain explicit approval. Do
    not invoke without an approval message."
  - `.claude/skills/scad-export/scripts/export.py` — calls U6; writes to
    `exports/<name>.stl`; emits JSON with watertight status, bbox, tri
    count. Non-zero exit on non-watertight.
  - `.claude/skills/scad-export/_tests/test_export.py`
- **Approach**: The human-in-the-loop gate (R16) lives in SKILL.md prose —
  Claude Code does not have a structured pre-condition API, so we rely on
  the skill's instructions to Claude. The script itself does not attempt to
  verify "was the user asked" — that is a behavior-shaping directive.
- **Test scenarios**:
  - T1: export GT model — JSON verdict `export_ok`, watertight=true, bbox
    near (60, 40, 7).
  - T2: export a deliberately broken model — verdict `not_watertight`,
    exit non-zero.

### U10 — `/scad-lib` skill

- **Goal**: List vendored libraries with capability summary; add a new
  library (clone + register in `libs/README.md`).
- **Requirements**: R10.
- **Dependencies**: U3.
- **Files**:
  - `.claude/skills/scad-lib/SKILL.md`
  - `.claude/skills/scad-lib/scripts/lib.py` — subcommands `list`, `add`
    (args: git URL, short name); clones shallow and appends README entry.
  - `.claude/skills/scad-lib/_tests/test_lib.py`
- **Approach**: `list` reads `libs/README.md` and emits the table. `add`
  does `git clone --depth=1 <url> libs/<name>`, then asks the caller to
  supply 3-5 `use <>` entries (the human/Claude authors the readme entry;
  the script just registers placeholders).
- **Test scenarios**:
  - T1: `list` after U3 shows NopSCADlib, threads-scad, MCAD.
  - T2: `add` with a known small test repo clones to `libs/<name>/` and
    inserts a stub README entry.

### U11 — End-to-end smoke test

- **Goal**: Exercise the full loop against a real model; verify each skill
  contract.
- **Requirements**: Overall success criteria from origin.
- **Dependencies**: U1-U10.
- **Files**:
  - `scripts/smoke.sh` (repo root) — runs `/scad-new` → inspects JSON → 
    optionally `/scad-render` with `-D` override → `/scad-export` after 
    simulated approval.
  - `scripts/smoke.expected.json` — golden output snippet.
- **Approach**: A bash script that invokes each `scripts/*.py` helper
  directly (bypassing the skill wrappers for determinism), exercising the
  motor mount flow from the spike. Compares key JSON fields (verdicts,
  bbox within tolerance) against golden output.
- **Test scenarios**:
  - T1: run `smoke.sh` — exits 0, writes `models/motor_mount.scad`,
    `renders/motor_mount/*.png`, `exports/motor_mount.stl`, reports
    watertight STL with bbox (60, 40, 7) ±1 mm.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `trimesh` unavailable via apt on Noble; pip-install may need `--break-system-packages` | Medium | Fallback documented in U6 (3MF + Euler check). |
| `/scad-new`'s NL→SCAD output occasionally omits `PRINT_ANCHOR_BBOX`, breaking U5 measurement | Medium | SKILL.md for `/scad-new` must mandate this; U7 render script checks for the declaration and fails fast if absent. |
| AppImage FUSE sandbox issue on this host | Low | Already verified AppImage runs (spike). If it breaks in a production environment, extract with `--appimage-extract` and call the unpacked binary. |
| Library vendoring drift (upstream changes) | Low | Pinning via shallow clone of a specific tag, not main. U3 should commit a note with the commit SHA pulled. |
| OPENSCADPATH leaking into ad-hoc shells | Low | Set per-invocation only inside U4 helper. Documented in `.claude/settings.json`. |

## Dependencies / Assumptions

- AppImage FUSE works on this host (verified in spike).
- `python3-pil` and `python3-numpy` available via apt (already installed
  during spike).
- `trimesh` installable (apt package absent; pip with
  `--break-system-packages` is the current path).
- `git` available for library cloning (assumed standard on the host).
- User accepts that `/scad-export` writes to `exports/` without further
  confirmation once they have explicitly said "go" — the R16 gate is a
  single approval, not per-call.

## Verification Strategy

- Per-unit: tests under each skill's `_tests/` directory, runnable with
  `python3 -m pytest .claude/skills/`.
- End-to-end: `scripts/smoke.sh` exercising the motor mount flow.
- Manual UX: `claude code` session → `/scad-new "simple washer 20mm OD, 8mm
  ID, 3mm thick"` → inspect PNGs → approve → `/scad-export`. Checks that
  the iteration loop works without permission prompts and produces a
  watertight STL.

## Sequencing

```
U1 ─► U2 ─► U3
                \
                 ├─► U4 ─► U5 ─► U7 ─► U8 ─► U11
                 │           │          │
                 └─► U6 ─────┘          └─► U9
                            │
                            └─► U10
```

U1-U3 are setup (any order after U1). U4 and U6 depend on U1/U2 but are
independent of each other. U5 has no runtime dep on U4 but logically fits
after (it consumes rendered PNGs). U7 needs U4+U5, U9 needs U6, U8 needs
U7. U10 can land anytime after U3. U11 gates the whole thing.

## Deferred to Implementation

These are runtime decisions the plan does NOT prescribe — they depend on
empirical behavior:

- Whether `/scad-render` defaults to preview (OpenCSG) or full `--render`
  (Manifold). Time both on a realistic model in U4/U7; pick the faster
  that still gives clean orthographic output. (Origin deferred question.)
- Exact trimesh installation path (pip `--break-system-packages` vs
  fallback 3MF+Euler check). Decide in U6 based on whether pip is
  available.
- Exact camera distances if `--viewall` does not fit complex models
  cleanly. The spike values (300 mm) work for ~100 mm models; scale up if
  U11 surfaces issues.
- Whether `/scad-new` should default to `$fn=96` in a shared header or
  leave it to the authored model. Decide when writing the U8 SKILL.md
  instructions.

## Outstanding Questions

None that block implementation. All origin "Resolve Before Planning"
questions are resolved. All origin "Deferred to Planning" items are either
resolved above or explicitly moved to "Deferred to Implementation".

## Next Steps

→ `/ce:work` to begin implementation at U1.
