---
date: 2026-04-16
topic: openscad-ai-workflow
---

# OpenSCAD AI Workflow

## Problem Frame
OpenSCAD is a programmatic 3D CAD tool whose code-first nature makes it a strong fit for LLM-assisted design, but there is friction: no visual feedback inside a terminal coding agent, boilerplate for library imports and rendering, and slow STL renders with the legacy CGAL engine. The goal is a local Claude Code workflow where a single prompt produces a parametric `.scad` file, renders it to images Claude can inspect, and iterates on the design until it matches intent — with curated OpenSCAD libraries pre-wired so generated code can use high-quality primitives rather than reinventing them.

## Requirements

**Environment**
- R1. OpenSCAD is installed as the nightly AppImage (2025+). The reason is the Manifold engine it ships with — the apt package on Ubuntu Noble is still `2021.01` and pre-dates Manifold (verified during review). Which render mode the skills use per call (OpenCSG preview vs full Manifold render) is a separate question, deferred to planning.
- R2. The workspace is `/home/seanoconnor/projects/stuff` with a conventional layout: `models/` (`.scad`), `renders/` (`.png`), `exports/` (`.stl`), `libs/` (vendored libraries), `.claude/skills/` (Claude Code skills, checked in).
- R3. Required CLI entry points are resolvable: `openscad` on PATH (symlink or wrapper around the AppImage). All skill scripts assume this.
- R15. Python `trimesh` is available in the environment (pip or system package) for post-export STL verification — used by `/scad-export` to check watertightness (manifold), triangle count, and bounding box in one call.

**Libraries**
- R4. The following libraries are vendored under `libs/` and exposed to OpenSCAD via the `OPENSCADPATH` environment variable set by the skill scripts: NopSCADlib, threads-scad, MCAD.
- R5. A short library index (`libs/README.md`) documents what each library is for and the 3–5 most useful `use <...>` entry points per library, so Claude can discover capabilities without scanning full library source.
- R6. BOSL2 is explicitly excluded from the default install (user chose a lighter footprint); adding it later is an opt-in step.

**Claude Code skills**
- R7. A `/scad-new` skill takes a natural-language description, writes a first-pass parametric `.scad` file to `models/`, and internally invokes `/scad-render` to produce multi-angle PNGs. Returns the file path and image paths so Claude can inspect them. The skill's SKILL.md explicitly instructs Claude to consult `libs/README.md` and prefer vendored library primitives over hand-rolled geometry before writing the file.
- R8. A `/scad-render` skill renders any `.scad` file to multiple angles (front, side, top, isometric) as PNGs under `renders/<model-name>/` so a single render call catches issues that one camera angle would hide. The three principal views are rendered with `--projection=orthogonal`; iso can stay perspective. The skill also emits a measurement block alongside the PNG paths: bounding box (mm), scale (mm/px), and detected circular features (diameters) derived by pixel measurement against a known anchor (plate bbox). Claude reads the numbers, not just the pixels, because the spike showed pure-vision judgment is weak for ~10% dimensional drift.
- R9. A `/scad-export` skill produces a full-render STL under `exports/`, then runs a Python `trimesh` post-export check. It reports triangle count, bounding box, and watertight (manifold) status in its output. Non-watertight STLs are flagged as an error (exit non-zero).
- R10. A `/scad-lib` skill lists vendored libraries and, on request, adds a new library (clone + register in `libs/README.md`).
- R11. Skills accept OpenSCAD variable overrides (`-D name=value`) so parametric files can be re-rendered with different values without editing source.

**Iteration loop**
- R12. The intended flow is: Claude writes/edits a `.scad` file → calls `/scad-render` → reads the returned PNG paths → evaluates against user intent and the quantitative rubric (see Success Criteria) → edits the file → re-renders. Claude relies on its own multimodal vision plus the numeric checks reported by the skills; no separate critique agent.
- R13. Files in `models/` are edited in place by default (git provides history). Versioned filenames (`part_001.scad`, `part_002.scad`) are available as an opt-in mode when the user wants to preserve intermediate designs for comparison.
- R14. Render and export scripts exit non-zero with a readable error on any failure: OpenSCAD parse/render failure, missing library, blank/empty output PNG, or (for `/scad-export`) a non-watertight STL as detected by `trimesh`. Claude can detect failure and respond rather than silently continuing.
- R16. Before STL export, Claude presents the current multi-angle PNGs to the user and asks for confirmation. `/scad-export` only proceeds after explicit approval. This keeps the human in the loop at the point where it matters most and guards against the loop converging on something Claude thinks matches while the user's mental model differs.

## Success Criteria
- `/scad-new` produces a rendered `.scad` + multi-angle PNGs in under a minute on first run (preview-mode rendering; full-render timing is looser and is a planning decision).
- Generated models pass automated checks on every render, reported by the skills in their output: bounding box within ±1mm of stated dimensions, parametric feature counts (holes, slots, threads, etc.) match the request, and the final STL from `/scad-export` is watertight per `trimesh`.
- Claude presents the multi-angle PNGs for user confirmation before `/scad-export` proceeds (see R16). The loop is not "done" until the user explicitly approves.
- Claude can iterate on a design for 3–5 turns without the user needing to run any shell commands manually.
- Generated code uses vendored libraries where appropriate (e.g. `threads-scad` for a threaded lid) rather than hand-rolling geometry that a library already provides, because `/scad-new`'s skill prompt surfaces `libs/README.md` before generation.

## Scope Boundaries
- Not building an MCP server, a web UI, or integration with Claude Desktop. Claude Code only.
- Not bundling image generation (e.g. Gemini/Venice for text-to-image seeds). Claude writes OpenSCAD directly from text.
- Not targeting 3D printer integration (network discovery, slicing, G-code). STL export is the terminal artifact.
- Not covering BOSL2, dotSCAD, or BOLTS out of the box. `scad-lib` can add them later.
- Not building a benchmark or eval harness for OpenSCAD generation quality.

## Key Decisions
- **Claude Code skills over MCP server**: lower friction, no daemon, works out of the box with this agent. Reason the user explicitly chose this shape.
- **Project-local skills (`.claude/skills/`)**: the workspace *is* the OpenSCAD project; skills ride with it under version control and can be extended without affecting other projects.
- **Nightly AppImage over apt**: verified during review that Ubuntu Noble still ships `openscad 2021.01` (pre-Manifold), so the AppImage's delta is real. The AI loop benefits disproportionately from Manifold's speed and boolean reliability.
- **NopSCADlib + threads-scad + MCAD, no BOSL2**: lighter footprint per user choice; covers mechanical/project work, ISO threads, and common utilities without pulling in the very large BOSL2 attachment system.
- **Multi-angle rendering as default**: one camera angle regularly hides overhangs, gaps, or wrong-axis extrusions. Cheap to generate four PNGs; expensive to debug a hidden flaw later.
- **Edit-in-place with git, versioning opt-in**: avoids directory clutter for the normal case while preserving the compare-across-iterations mode when the user wants it.
- **`/scad-new` internally invokes `/scad-render`**: one user intent ("make me a part") maps to one skill. Avoids ambiguity over what "preview images" meant in the original R7.
- **Python `trimesh` for post-export verification**: single dependency replaces both "non-manifold detection method" and "triangle-count / bbox source" — one tool gives watertight check, triangle count, and bbox.
- **Measurable success criteria with human checkpoint before export**: automated numeric checks on every render (bbox, feature counts, watertight), plus explicit user approval before STL is written. Replaces the original "recognizably the requested part" which had no evaluator.
- **Pre-planning vision-quality spike**: resolved 2026-04-16 (see `docs/brainstorms/2026-04-16-openscad-vision-spike-results.md`). Ran 3-defect perturbed motor mount through the loop; vision caught 2/3 defects with high confidence and zero hallucinations, and correctly flagged the third (subtle ~10% dimensional drift) as uncertain. Adding pixel-measured dimensions to `/scad-render` output (now reflected in R8) closes the remaining gap. Architecture holds.

## Dependencies / Assumptions
- OpenSCAD nightly AppImage is available for download and the user can run it on their Linux system (no sandbox blocking AppImage FUSE).
- Python `trimesh` installs cleanly on the target system.
- This workspace will be placed under git for history; skills will not attempt their own versioning of `.scad` files beyond optional numeric suffixes.
- Claude's multimodal vision, combined with the quantitative rubric reported by the skills (measured dimensions in R8), is sufficient for the quality of judgment this loop needs. **Validated 2026-04-16 by the spike (see `docs/brainstorms/2026-04-16-openscad-vision-spike-results.md`).**

## Outstanding Questions

### Deferred to Planning
- [Affects R1][Technical] Exact AppImage URL and install path. Planning should pick the latest 2026 nightly at implementation time rather than pinning a version in the requirements doc.
- [Affects R3][Technical] Whether to install via a symlink to `~/.local/bin/openscad` (already on PATH) or a small wrapper script that sets `OPENSCADPATH`. Either works; decide during implementation based on what plays nicest with the skills.
- [Affects R8][Needs research] Whether Manifold-engine preview-mode PNGs (OpenCSG) are acceptable for iteration or whether `--render` (full CGAL/Manifold) should be the default. Tradeoff is seconds-per-render vs. fidelity. Planning should time both on a realistic model.
- [Affects R8][Technical] Headless rendering path — OpenSCAD PNG export needs a GL/display context. Options: `xvfb-run` wrapper, `--render` (software path), or offscreen EGL. Planning must verify which works with the chosen AppImage on this host (`DISPLAY` is typically empty under ssh/tty).
- [Affects R2, R7][Technical] Claude Code skill format — SKILL.md frontmatter (name, description, allowed-tools), script invocation pattern, how one skill invokes another (shell out to a shared script vs skill-to-skill), and how skill output exposes generated image paths to the model.
- [Affects R4, R12][Technical] `OPENSCADPATH` scoping — set per-invocation inside wrapper scripts only, or persisted in shell rc / `.claude/settings.json` env so that ad-hoc `openscad` calls outside the skill wrappers resolve vendored libraries.
- [Affects R8, R14][Technical] Post-render validation — beyond checking the OpenSCAD exit code, also verify PNG exists and is non-empty, and surface unresolved `use <>` warnings (OpenSCAD logs them but still exits 0).
- [Affects R12][Technical] Claude Code permissions posture — the success criterion "iterate 3–5 turns without manual shell commands" requires Bash patterns for `openscad`, `xvfb-run`, etc. to be pre-approved in `.claude/settings.json` or declared via skill `allowed-tools`. Without this, each varying `-D` argument triggers a permission prompt.
- [Affects R9][Technical] Parametric feature-count verification — the rubric in Success Criteria requires checking that hole/slot/thread counts match the request. `trimesh` doesn't know which features were requested; this likely means the skills parse `-D`-overridden parameters out of the `.scad` source or the user's prompt and Claude compares them against its own intent. Planning should decide the exact mechanism.

## Next Steps
→ `/ce:plan` for structured implementation planning. Spike resolved; architecture confirmed.
