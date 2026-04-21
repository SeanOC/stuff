# st-556 Phase 0 — WASM Feasibility Spike Findings

**Verdict: `go-hybrid`** — all probes pass. WASM can render the existing
library stack (BOSL2 + QuackWorks). Performance is acceptable for
moderate models; heaviest model in the repo (~12k facets) takes ~60 s
wall-clock and would benefit from a server-side fallback.

## Build used

| Field            | Value |
|------------------|-------|
| npm package      | `openscad-wasm-prebuilt@1.2.0` |
| Published        | 2025-01-22 |
| Source repo      | https://github.com/lorenzowritescode/openscad-wasm |
| OpenSCAD version | 2025.01.19 |
| Backend used     | Manifold (`--backend Manifold`) |
| Node host        | v20.20.0 |

The official `openscad/openscad-wasm` releases page is stale (last
release 2022.03.20), but `lorenzowritescode/openscad-wasm` packages a
2025 OpenSCAD build with both CGAL and Manifold backends. The 2022
build was tried first and immediately failed Probe 2a — the prebuilt
2025 build with `--backend Manifold` is the one that worked.

## Library-loading approach (worked)

OpenSCAD's built-in library search path is `/libraries`. Mount the
repo's `libs/` tree into the Emscripten virtual filesystem at
`/libraries/<libname>/...`. With that in place, source like
`include <BOSL2/std.scad>` resolves with zero extra flags — no `-I`,
no `OPENSCADPATH` env-var gymnastics.

Implementation: see `harness.mjs` `copyTreeIntoFS()`. We follow
symlinks (the repo's `libs/BOSL2` etc. are symlinks into a sibling
clone) and copy every `.scad` file recursively. 576 files mounted in
~30 ms.

## Per-probe results

All times are wall-clock from `process.hrtime` around `instance.callMain`.
"Internal" times in parentheses are OpenSCAD's own
`Total rendering time` line from stderr — i.e. CGAL/Manifold work,
excluding parse + include resolution.

| # | Probe | Result | Wall ms | Internal | STL bytes | Peak RSS | Notes |
|---|-------|--------|---------|----------|-----------|----------|-------|
| 1  | trivial cube                      | PASS | 54     | 12 ms   | 1 497      | 113 MB | sanity baseline |
| 2a | BOSL2-only synthetic (`cuboid` w/ rounding) | PASS | 1 221  | 57 ms   | 7 877      | 152 MB | confirms BOSL2 includes resolve, manifold backend works |
| 2  | `models/spraycan_holder_70mm.scad`| PASS | 62 799 | 993 ms  | 2 843 821 | 203 MB | 12 098 facets — heaviest model in repo |
| 3  | `models/cylinder_holder_46mm_slot.scad` | PASS | 8 992 | 374 ms | 781 394 | 180 MB | 2 892 facets — uses Multiconnect backer |

All four probes produced valid binary STL.

## Discrepancy with bead description

The bead lists Probe 2 as "pure BOSL2, no QuackWorks", but the actual
source of `models/spraycan_holder_70mm.scad` is:

```scad
include <BOSL2/std.scad>
use <QuackWorks/Modules/snapConnector.scad>
```

It does pull in QuackWorks/snapConnector. There is no truly
BOSL2-only model in the repo — `grep -L QuackWorks models/*.scad`
on BOSL2-using files returns empty. To still isolate BOSL2 cleanly,
the harness adds Probe 2a (synthetic inline `cuboid` with rounding).
Both Probe 2a and Probe 2 pass, so the BOSL2 path is confirmed
independently of QuackWorks.

## Performance characterization

OpenSCAD's own `Total rendering time` is sub-second for every probe.
Wall-clock dominance is in **parse + include resolution**, not CSG
work:

- Probe 2: 62 s wall, 1 s internal → 61 s spent parsing/resolving.
- Probe 3: 9 s wall, 0.4 s internal → 8.6 s parsing/resolving.

Likely cause: the include resolver scans the virtual FS for every
`include <...>` directive, and BOSL2's `std.scad` transitively
includes ~30 sub-files. Mounting only the closure of files actually
needed by the model (instead of the full 576-file tree) should cut
this dramatically. That's a Phase 1 optimization, not a blocker.

For live web preview:
- **Models in the cylinder-holder weight class (≤ 3k facets) are
  probably acceptable** at ~9 s with naive mounting, < 2 s with
  optimized include closure.
- **Heaviest models in the spraycan-holder class (~12k facets) are
  borderline.** Recommend a server-side render fallback for any model
  whose first preview takes > 10 s, with the WASM result cached for
  subsequent param tweaks.

## Memory

Peak RSS stayed under 250 MB for every probe, well within browser tab
budgets. (One earlier failure run hit 3.3 GB RSS — that was the
synthetic BOSL2 probe under the **CGAL** backend, which is the WASM
default. Switching the backend flag from CGAL to Manifold dropped RSS
by ~20× and turned the failure into a 1.2 s pass. **Manifold backend
is non-negotiable for WASM.**)

## Warnings / errors observed

- Probes 2 and 3 emit BOSL2 deprecation echoes (`align() has changed,
  May 1, 2024 ... $align_msg=false disables this message`). Cosmetic;
  not a failure.
- The `stderr_errors` field flagging "Status: NoError" is a
  regex false-positive in the harness — that's actually OpenSCAD's
  manifold status line saying success.
- No real errors, no missing-library warnings, no "WARNING: include
  file ... not found".

## Reproduction

```bash
cd experiments/wasm-spike
npm install         # installs openscad-wasm-prebuilt only
node harness.mjs    # ~75 s on this hardware (cold cache)
```

Output is a single JSON object on stdout listing per-probe results.

## Recommendation for Phase 1 (hq-? / st-1wf)

1. Pin `openscad-wasm-prebuilt@1.2.0` (or the next compatible patch).
2. Always pass `--backend Manifold`. CGAL is unusable in WASM.
3. Build a minimal include-closure mounter (parse `include`/`use`
   from the model, walk the dep graph in BOSL2/QuackWorks/etc., mount
   only that subset). This should bring spraycan_holder_70mm down
   from 60 s to a few seconds.
4. Hybrid render policy: try WASM first with a 5 s budget; if it's
   not done, hand off to the server route and stream STL back.
5. Keep CGAL build of OpenSCAD on the server for parity / fallback.
