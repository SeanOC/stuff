---
name: new-model
description: Add a new parametric model to models/ end-to-end. Scaffolds the four required artifacts (scad + invariants sidecar + sweep test + catalog entry) via scripts/new-model.py, then walks the repo's authoring conventions — openGrid snap/pitch/print-orientation rules, PRINT_ANCHOR_BBOX, wasm CGAL traps, export-path verification, DONE criteria. Use whenever creating or adding a model.
---

# new-model

Every convention below is derived from the shipped models (exemplars:
`opengrid_panel_aligner`, `opengrid_bin`, the `led_remote_holder` twins,
`ego_lb6500_blower_mount`, `gridfinity_bin`, `rv_ceiling_ap_adapter_235mm`).
Bead IDs in parentheses are provenance — grep the model comments for the
full story.

## Step 0: scaffold — don't hand-create the artifact set

```bash
python3 scripts/new-model.py <stem> --category <id> [--opengrid] [--blurb "..."]
```

Generates all four artifacts in one shot (idempotent; refuses to clobber):
`models/<stem>.scad`, `models/<stem>.invariants.py`,
`tests/sweep/<stem>.test.ts`, and the `lib/models/catalog.ts` entry.
`--opengrid` emits the full openGrid wall-mount skeleton (snap grid,
welded snap wrapper, snap-pitch invariant). Both skeletons render
watertight and pass the invariants pipeline as-generated.

## Why four artifacts — each is a hard gate

| Artifact | Missing it means |
|---|---|
| `models/<stem>.scad` | — |
| `lib/models/catalog.ts` entry | `listModels()` **throws**; the model silently never surfaces in the gallery. Blocked by pre-commit + `lib/models/catalog.test.ts`. |
| `models/<stem>.invariants.py` | Blocked by pre-commit + CI invariants gate. |
| `tests/sweep/<stem>.test.ts` | `tests/sweep/coverage.test.ts` fails. |

Valid `categoryId`s live in `MODEL_CATEGORIES` (`lib/models/catalog.ts`)
— currently `storage | multiboard | toys | household`. The blurb is the
gallery card text: 1–2 sentences, what it holds/mounts + key dimension +
print story.

## .scad checklist

- [ ] **Line 1 SPDX, line 2 Copyright.** `CC-BY-NC-SA-4.0` when anything
  QuackWorks/openGrid is used (it's NON-COMMERCIAL — also add the
  `// LICENSING:` attribution paragraph); match the consumed library's
  license otherwise (`gridfinity_bin` is MIT).
- [ ] **First prose `//` line = gallery title** (`deriveTitle()` in
  `lib/models/discover.ts` skips SPDX/Copyright and takes the next line).
- [ ] **`=== Print orientation ===` header section** documenting what
  touches the bed and why it's support-free (or the built-in breakaway
  story). House style: `opengrid_panel_aligner.scad`.
- [ ] **Libraries**: `use <...>` paths from `libs/README.md` only.
  BOSL2 is the exception: `include <BOSL2/std.scad>`.
  `opengrid-snap.scad` must be `use`d, never `include`d — it ends with a
  top-level demo call that would inject a stray snap into every render.
- [ ] **`$fn = 64`** default; 96–128 for revolved/round-dominant parts;
  gridfinity wrappers use the library's `$fa = 4; $fs = 0.25;` idiom.
- [ ] **Params under `// === User-tunable parameters ===`** — the parser
  (`lib/scad-params/parse.ts`) only scans inside that section and stops
  at the next `// === ... ===` header, so ALWAYS follow the block with
  another section header (e.g. `// === Derived ===`). Line grammar:
  `name = default; // @param <number|integer|boolean|string|enum> [min= max= step=] [unit=mm] [group=x] [label="..."] [choices=a|b|c]`.
  A bare `filename` flag on an enum expands one exported STL per choice.
- [ ] **`@preset` line(s)** after the params — every key must be a
  declared `@param` (the parser throws and CI fails otherwise).
- [ ] **`PRINT_ANCHOR_BBOX = [x, y, z];`** — literal numbers only
  (expressions are invisible to the driver's regex), preceded by the
  arithmetic-derivation comment. The invariants gate fails on >1mm drift
  vs the exported STL; the render skill uses it for pixel→mm scale.
- [ ] **No hull-backed rounding** (BOSL2 `cuboid(rounding=/edges=)` on
  3D ops): the wasm engine's CGAL `applyHull()` asserts on some swept
  dimensions (st-7x7/st-560). Round vertical edges as extruded 2D
  `rect(rounding=)` footprints; chamfer exposed rims with explicit 45°
  prisms that overshoot past the faces they cut (st-n4v: coplanar cut
  faces are degenerate booleans).
- [ ] **No face-kissing unions** (st-v7k: detached shells / non-manifold
  tangent edges): sink parts `bury = 0.6` into each other; snaps weld
  `0.02` into their plate.
- [ ] **No `import()` of meshes.** The one import()-based model was
  rebuilt from primitives (st-82o): a 13k-triangle mesh union cost ~23s
  per wasm render, and a wasm CSG failure can silently drop part of the
  tree yet exit 0 with partial geometry. Remodel natively; keep a
  reference STL in-repo for the sidecar only if needed
  (`ego_lb6500_blower_mount.stl` precedent).

## openGrid models (`--opengrid` scaffolds all of this)

- **28mm tile pitch**, snap footprint 24.8mm, snap depth 6.8 (3.4 lite).
  Size plates/footprints in whole tiles so the part aligns with the grid.
- **Never re-derive snap geometry.** The snap is the vendored
  `openGridSnap()` (`QuackWorks/openGrid/opengrid-snap.scad`) wrapped in
  a per-model `welded_*_snap()` module that adds 0.3mm root-fillet shims
  (openGridSnap's click nubs are face-touching solids; the shims fuse
  them into one watertight body on both CGAL and Manifold, st-v7k).
  There is deliberately **no shared project-side module** — the browser
  render pipeline can only resolve vendored `libs/`, so the wrapper is
  kept textually identical across models. Fix a bug in one → apply to
  the siblings (`opengrid_bin`, `ego_lb6500_blower_mount`, the
  `led_remote_holder` twins, `opengrid_panel_aligner`).
- **Directional snaps, strong front nub UP the wall** (`zrot(90)`) for
  cantilevered loads — lever-out bears on the rigid 0.8mm hook, the
  flexy click side faces down (st-0of). Use `directional = false` for
  tools that click in and pull straight out (`opengrid_panel_aligner`).
- **Prints snaps-down, support-free**: snap faces are the first layers;
  every body overhang is a 45° chamfer, never a flat span; nothing may
  put geometry (or need support) in the channels between snaps.

## Gridfinity models

Wrap `gridfinity-rebuilt-openscad` v2's object API (`new_bin` →
`bin_render`); override library spec constants by redeclaring after the
`include` (last-write-wins). Keep the wrapper param set small and
document the wrapper→library mapping table in the header
(`gridfinity_bin.scad`).

## Invariants sidecar

Built-ins run for every model automatically (watertight, orphan
fragments, triangle ceiling, PRINT_ANCHOR_BBOX drift, preset validity).
The sidecar asserts what THIS model claims: start with
`expect_connected_solids(ctx, 1)` (or the computed count for multi-body
— and mirror that logic in `tests/sweep/expectations.ts`), then pin the
model's reason-to-exist: footprint/grid alignment, bed-contact span
(openGrid: `(units-1)*28 + 24.8`), shell-thickness bounds, cavity/void
probes via `ctx["stl"].contains(...)`. Docstring = numbered claims.

## Param sweep

The generated `tests/sweep/<stem>.test.ts` is complete — the runner
sweeps min/mid/max of every numeric param, both booleans, every enum
choice through the real browser wasm pipeline. Two registries:

- `tests/sweep/expectations.ts` — only for multi-body exceptions.
- `tests/sweep/known-failures.ts` — wasm CGAL edge cases at param
  extremes (st-79a class: vendored-lib hull geometry that desktop
  OpenSCAD renders clean). File a bead, register
  `"<param>=<value>": "<bead>: reason"` at model introduction, remove
  when the bead closes (the case re-arms itself). Don't paper over
  failures in the MODEL — fix those.

## Verify the export path — do NOT trust invariants alone

```bash
bash scripts/vendor-libs.sh                  # once per clone; sweep/render need it
python3 scripts/export-all.py && python3 scripts/check-invariants.py <stem>
npm run test:sweep -- tests/sweep/<stem>.test.ts
```

Render representative param combos (not just defaults) to manifold
STLs and check the actual download artifact — a wasm CSG failure can
silently drop meshes and still exit 0. Eyeball renders via the
`scad-render` skill or `python3 scripts/render-all.py`.

## DONE criteria

- [ ] All four artifacts committed; pre-commit gate passes (run
  `./scripts/setup-git-hooks.sh` once per clone).
- [ ] No `TODO(<stem>)` left: real title line, print-orientation story,
  catalog blurb, invariants claims.
- [ ] `exports/<stem>.stl` watertight; `check-invariants.py <stem>` green.
- [ ] Sweep green, or failing extremes registered in `known-failures.ts`
  with a tracking bead.
- [ ] Renders eyeballed (top/front/side/iso) and dimensions confirmed
  against `PRINT_ANCHOR_BBOX`.
- [ ] Detail page loads: `npm run dev` → `/models/<stem>`.
