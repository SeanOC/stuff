---
date: 2026-04-23
bead: st-ryj
status: research-only (not committed per bead `review_only: true`)
---

# AI model-QA workflow — catching geometric defects before user review

## 1. Defect taxonomy (the 5 shipped misses)

| Bead   | Symptom                                      | Class                            | Catchable by                                                          |
|--------|----------------------------------------------|----------------------------------|-----------------------------------------------------------------------|
| st-v7k | Handle posts floated detached in preview     | Topology (preview-only)          | Manifold/CSG mismatch probe; iso-render vision                        |
| st-8ac | Handle clashed with tall cans                | Geometric invariant (clearance)  | Explicit `arch_z ≥ can_height` assertion; side-render vision          |
| st-l2z | Session death lost work                      | Process (not CAD)                | N/A — out of scope                                                    |
| st-3ta | Uniform base margin wastes Y plastic         | Wasted-material invariant        | Aspect-ratio / per-axis margin assertion; top-render vision           |
| st-hnd | Fillet discontinuity at post→arch junction   | Visual/C¹ continuity             | Multi-angle vision (subtle); structural — `path_sweep` instead        |

Four of five are CAD defects. Of those: 2 are crisp numeric invariants (st-8ac, st-3ta), 1 is topological (st-v7k), 1 is a visual-continuity subtlety (st-hnd). The spike's claim — "vision strong for structural, weak for 10% dimensional drift" — holds: st-hnd is the one that vision alone struggles with.

## 2. Capability inventory

Already in repo:

- **Render pipeline** — `scripts/render-all.py` + `.claude/skills/scad-render/` (`SKILL.md:40–60`) emit orthographic top/front/side + iso PNGs and a JSON block with `bbox_mm`, `scale_mm_per_px`, and detected `circles_top`. Anchored by the `PRINT_ANCHOR_BBOX` convention. CI regenerates on push/PR (`AGENTS.md:17–26`, `.github/workflows/ci.yml`).
- **Export verification** — `.claude/skills/scad-export/SKILL.md:41–60` runs `trimesh` and reports bbox, triangle count, `is_watertight`. Exits non-zero on non-watertight.
- **OpenSCAD Manifold** — `--backend Manifold` is default; Manifold's output already fails closed on many topology errors that OpenCSG preview hides (exactly the st-v7k class).
- **Vitest + Playwright** — harness exists; no invariant-oriented suite yet.
- **BOSL2** — ships geometry tests under `libs/BOSL2/tests/` but they validate the library, not user models.

Not in repo: any CAD-aware compound-engineering plugin. Closest adjacents (`design-implementation-reviewer`, `design-iterator`) are Figma-only and don't transfer. `gemini-imagegen` generates, doesn't diff. No CAD skill exists upstream that we'd just install.

**Spike conclusions** (`docs/brainstorms/2026-04-16-openscad-vision-spike-results.md:66–75`, `…-ai-workflow-requirements.md:26`): multi-angle orthographic PNGs + pixel-measured anchor dimensions are decisive; the missing piece is that this loop is skill-invocable but not *mandatory* before `gt done`.

## 3. Gap analysis

- **Pre-submit gate**: None. `gt done` pushes without re-rendering. Nothing forces a polecat to look at its own output.
- **Topology invariants**: watertight is checked on export, but st-v7k was a *preview* mismatch — nothing currently compares OpenCSG vs Manifold output, nor asserts `num_connected_solids == 1` on the preview path.
- **Per-model invariants**: no place to declare `arch_z_start ≥ can_height` or `base_d ≤ base_w * 0.9`. `PRINT_ANCHOR_BBOX` is the only machine-readable claim a model makes about itself.
- **Visual-continuity class (st-hnd)**: no idiom short of a vision pass or a structural rewrite to `path_sweep`. Invariants can't express C¹ smoothness cheaply.

## 4. Three proposals, ranked effort → payoff

**P1 — Pre-`gt done` vision self-review (LOW effort).** Polecat runs `scripts/render-all.py` on changed models, opens iso + top + side PNGs, and silently critiques against a 5-line checklist ("single body? footprint tight? proportions match spec? seams? clearances?"). Add to `CLAUDE.local.md` completion protocol. Catches st-v7k (iso), st-3ta (top). Misses st-hnd (too subtle) and st-8ac (needs clearance number, not vision).

**P2 — Invariants sidecar (MEDIUM).** Per-model `models/<stem>.invariants.py` (or `.json`) declares machine-checkable claims: bbox range, `num_connected_solids`, free-form lambdas over STL bbox + parsed params (`arch_z_start(params) >= params.can_height`). New `scripts/check-invariants.py` runs on the Manifold-export STL + source-parsed params, exits non-zero on fail. Wire into CI alongside the render job and as a mandatory pre-`gt done` step. Catches st-v7k (connected-body), st-8ac (clearance), st-3ta (per-axis margin). **Does not** catch st-hnd.

**P3 — `/review-scad` skill + sub-agent (HIGH).** On any modified `.scad`: render → export → invariants → vision pass → structured PASS/FAIL. Blocks `gt done`. Catches all four CAD classes. Bundles P1 + P2 plus LLM judgment.

## 5. Recommendation

**Prototype P2 as the next bead.** Rationale: (a) closes three of four defect classes with deterministic, reviewable truth — no LLM drift; (b) composes with P1 cheaply later (add the vision checklist to the same pre-`gt done` hook); (c) each invariant is a one-liner against already-available outputs (trimesh STL, parsed params, `PRINT_ANCHOR_BBOX`). Initial scope sketch:

- `scripts/check-invariants.py <model.scad>` — reads source, parses `@param`s and constants, loads STL from `exports/`, asserts claims.
- Per-model `models/<stem>.invariants.py` with a single `def check(model, stl): -> list[Failure]`.
- Seed invariants: `connected==1`, `bbox ≈ PRINT_ANCHOR_BBOX ±1mm`, `base_d ≤ base_w` (catches st-3ta once seeded), `arch_z_start ≥ can_height` (st-8ac).
- CI: run on PR; block `gt done` locally via a hook in `CLAUDE.local.md`'s Completion Protocol.

Fold P1 (vision checklist) in the same hook for the st-hnd class, but ship P2 first — the invariants are what stop the bleeding.
