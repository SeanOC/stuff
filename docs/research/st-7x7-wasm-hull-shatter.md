# st-7x7: hex stylus shattered in the site preview at hex_width=9 — RCA and fix

**Symptom (operator report, 2026-07-03):** on the live site, setting the
`lcd_stylus_hex_8mm` "Body width" param to 9 mm made the preview break
into disjoint pieces — a rounded bar plus three separated rectangular
posts, one fully detached. Desktop OpenSCAD rendered the same param
intact (both CGAL and Manifold backends), so the model itself was
suspected innocent and the wasm pipeline guilty. Both turned out to be
true, with a twist.

## Root cause

Two independent bugs stacked:

1. **Engine (openscad-wasm-prebuilt 1.2.0, OpenSCAD 2025.01.19):**
   `hull()` goes through CGAL's `convex_hull_3` even under
   `--backend Manifold`. The wasm build ships a CGAL version whose
   quickhull has a robustness bug on *degenerate* input: the stylus
   body is one hull of thirteen spheres, and the twelve corner spheres
   were exact translated copies of a single tessellated mesh — so the
   hull faces bridging corresponding vertices of two copies are
   exactly-coplanar quads by construction. On such input the border
   walk can fail its `it != border.end()` assertion:

   ```
   ERROR: CGAL error in applyHull(): CGAL ERROR: assertion violation!
   Expr: it != border.end()
   File: .../CGAL/convex_hull_3.h  Line: 684
   ```

   Crucially, `convex_hull_3` is a *randomized* incremental algorithm,
   so only some insertion orders trip the assertion — the same source
   bytes shattered in one render and passed in the next (reproduced
   both ways in `renderToStl` under Node: e.g. one full-range sweep
   failed at hex_width 9, 10 and 12; byte-identical re-runs later
   passed). Desktop OpenSCAD (2025.06 snapshot) ships a newer CGAL and
   never trips. No newer `openscad-wasm-prebuilt` exists on npm
   (1.2.0, Jan 2025, is the latest), so the engine could not be
   upgraded.

2. **Pipeline (`lib/wasm/render.ts`):** when the hull node failed,
   OpenSCAD logged the `ERROR:` line, *dropped the hull's geometry,
   and still exited 0* with a non-empty STL of whatever remained — the
   breakaway support fin and its three ribs, which is exactly the
   operator's screenshot (568 triangles, 2 components, vs the healthy
   ~18,400 triangles, 1 component). `renderToStl` treated exit 0 +
   non-empty STL as success and the UI displayed the shattered partial
   mesh as a completed render.

## Fix (three layers)

1. **Model** (`models/lcd_stylus_hex_8mm.scad`): every hull sphere now
   gets a distinct tiny z-rotation ("tessellation phase"). A sphere is
   rotation-invariant, so the designed shape is untouched — but no two
   sphere meshes are translated copies anymore, the exactly-coplanar
   quads disappear, and the hull input is in generic position, which
   the randomized quickhull handles at every insertion order. Verified
   at the previously-failing widths and across the whole param range;
   desktop output stays watertight, single-component, same bbox
   (90 × 10.08 × 9 at hex_width=9).

2. **Renderer** (`lib/wasm/render.ts`): a hard `ERROR:` line in stderr
   now fails the render even when OpenSCAD exits 0 — partial geometry
   is never shown as success (the error surfaces through the normal
   error strip instead). CGAL-class errors get one retry with a fresh
   wasm instance, because a fresh randomized insertion order usually
   succeeds — turning this whole class of intermittent engine failure
   into a self-healing hiccup for *every* model.

3. **Systemic guard** (`tests/sweep/`, `npm run test:sweep`,
   `.github/workflows/param-sweep.yml`): every catalog model is
   rendered through the exact site pipeline at the min/mid/max of
   every numeric `@param`, both boolean states, and every enum choice
   (one param at a time from defaults). Each render must succeed, be
   watertight (every edge shared by exactly two triangles), and have
   the expected connected-component count
   (`tests/sweep/expectations.ts` mirrors the invariants sidecars for
   the legitimately multi-body models). ~350 renders per run also act
   as a statistical fuzzer for the randomized-failure class. The unit
   suite additionally pins the operator's exact repro
   (`lib/wasm/render.test.ts`) and an e2e spec drives it in the real
   preview (`tests/e2e/hex-stylus-connectivity.spec.ts`).

## Before / after evidence

Before (site pipeline in Node, pre-fix model, one sweep run):

```
hex_width=8:  ok=true tris=18380 comps=1
hex_width=9:  ok=true tris=568   comps=2  ERROR: CGAL error in applyHull()
hex_width=10: ok=true tris=568   comps=2  ERROR: CGAL error in applyHull()
hex_width=12: ok=true tris=572   comps=1  ERROR: CGAL error in applyHull()
```

(`ok=true` on the failing rows is pipeline bug #2 — those are the
renders the preview displayed as success.)

After (fixed model, same pipeline — full sweep green, spot rows):

```
hex_width=9:  ok=true tris=18506 comps=1 watertight
hex_width=10: ok=true tris=18488 comps=1 watertight
hex_width=12: ok=true tris=18380 comps=1 watertight
```

Desktop parity after fix: `openscad --backend=manifold -D hex_width=9`
→ watertight, 1 component, bbox [90, 10.08, 9], 18,446 triangles.

## What the guard found on its first run

The initial full sweep (424 renders) flagged 122 cases. Triage split
them into:

- **93 false positives from the first watertight definition** (strict
  every-edge-exactly-twice parity). Legitimate CSG output has two
  solids meeting along a shared edge (4 uses — e.g. goblu's zero-gap
  dovetailed pods), which is printable and fine. The check was
  recalibrated to flag *open* edges only (an edge used exactly once is
  a hole — the actual shatter signature).
- **28 genuine pre-existing model bugs at `@param` extremes** across six
  models — hard `exit=1` BOSL2 assertions, a `rotate_extrude`
  X-coordinate-sign error, and assemblies splitting into more bodies
  than designed. Filed as st-dlu (aquor), st-ti3 (blu_black), st-38y
  (blu_flow), st-344 (goblu), st-1us (cylindrical_holder_slot), st-9hn
  (spraycan); skipped with bead references in
  `tests/sweep/known-failures.ts` so the guard lands green and gates
  new regressions. Removing an entry re-arms its case.
- **1 wrong expectation** (blu_flow `assembly_with_meter` renders 3
  bodies, not 4 — the meter dummy merges with the saddle caps).

## Notes for the future

- If `openscad-wasm-prebuilt` ever ships a newer OpenSCAD/CGAL, the
  retry in `render.ts` and the model's phase jitter both stay valid
  (they're conservative), but the param-sweep suite is the thing to
  trust when evaluating the upgrade.
- The failure being randomized means "it rendered fine when I tried
  it" is not evidence of absence for this bug class — the sweep suite
  exists precisely because single spot-checks can't catch it.
