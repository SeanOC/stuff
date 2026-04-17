# Spike Protocol

## Question
Can Claude, using only multi-angle orthographic PNGs + stated dimensions,
iterate an OpenSCAD model toward a target spec within 5 turns?

## Roles
- **Author** (Claude under test): writes v0 from the prompt, critiques renders
  turn by turn, edits, re-renders. MUST NOT peek at `ground_truth/`.
- **Evaluator** (Claude in evaluator mode): between turns, runs quantitative
  checks (bbox via `--export-format=off` vertices, feature count via regex of
  OpenSCAD console warnings + source inspection, visual spot-check vs. ground-
  truth renders). Scores each turn.

## Prompt the Author sees
> Design a parametric motor mount plate in OpenSCAD:
> - 60 mm x 40 mm rectangular base plate, 5 mm thick
> - central 20 mm diameter motor bore through the plate
> - raised boss around the bore: 25 mm outer diameter, 2 mm tall above the
>   plate top face
> - four M3 clearance mounting holes (3.2 mm diameter) on a
>   50 mm x 30 mm rectangular pattern centered on the bore
> - each mounting hole has a top-face counterbore for an M3 socket head:
>   6 mm diameter, 3 mm deep
> Output a clean parametric .scad file. Then iterate based on renders.

## Turn-by-turn

| Turn | Author action                           | Evaluator records                           |
|------|-----------------------------------------|---------------------------------------------|
| 0    | Write `iter/v0.scad` from the prompt    | bbox, hole count, counterbore count         |
| 1    | View renders of v0, critique, write v1  | defects-flagged (correct/hallucinated),     |
|      |                                         | dimensional delta per feature               |
| 2-5  | Repeat for v1..v5                       | same; track convergence vs. oscillation     |

## Scoring (final)

- **Dimensional fidelity**: max |actual - stated| in mm for bbox_x, bbox_y,
  bbox_z, bore diameter, boss diameter. Pass if all within 1 mm.
- **Feature count**: exact match on hole/counterbore count.
- **Visual-critique precision**: over 5 turns, what fraction of Claude's
  flagged defects were real vs. hallucinated? Target: >= 70% real.
- **Convergence**: did dimensional delta strictly decrease over turns? Any
  regressions?

## Decision gate

- **Pass** -> the current R7-R14 skill architecture holds. Proceed with
  `ce:plan`.
- **Partial** (visual critique weak but dims OK, or vice versa) -> architecture
  holds but add an explicit dimensional-assertion step to `/scad-render` output
  before committing the plan.
- **Fail** (hallucinated critiques OR >1 mm drift OR non-convergence) ->
  rework R7-R14. Introduce human-in-the-loop checkpoints earlier in the loop,
  OR add numeric dimension probes to every render.
