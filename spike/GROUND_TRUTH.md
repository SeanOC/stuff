# Spike Ground Truth — Motor Mount v0

Claude will NOT see this file during the iteration loop. It is the evaluator's
reference for scoring dimensional fidelity and feature-count accuracy.

## Stated dimensions (what a "prompt" would ask for)

- Rectangular base plate: 60 mm (X) x 40 mm (Y) x 5 mm (Z)
- Central motor bore: through-hole, 20 mm diameter, centered on the plate
- Raised boss around the bore: 25 mm outer diameter, 2 mm tall above the plate top surface
- Four mounting holes for M3 bolts: 3.2 mm diameter clearance holes
  - arranged in a 50 mm (X) x 30 mm (Y) rectangular pattern
  - centered on the motor bore
  - pass fully through the plate
- Counterbores for M3 socket heads: coaxial with each mounting hole
  - 6 mm diameter, 3 mm deep
  - opened from the top face

## Expected feature counts

- through-holes: 5 (1 bore + 4 mounting)
- counterbores: 4
- bosses: 1
- outer primitives unioned: plate + boss

## Bounding box (expected)

- X: 60 mm
- Y: 40 mm
- Z: 7 mm  (5 mm plate + 2 mm boss)

## Evaluator rubric per turn

For each iteration turn Claude sees only the renders and the stated dimensions
above. After Claude critiques and edits, re-render and score:

1. **Dimensional fidelity** — do apparent dimensions match stated within ~1 mm?
2. **Feature count** — holes, counterbores, boss all present and correct count?
3. **Judgment accuracy** — did Claude's critique identify a real defect or
   hallucinate one? Score: correct / partial / hallucinated.
4. **Convergence** — does each turn move closer to ground truth or oscillate?
