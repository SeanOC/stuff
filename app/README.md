# Stuff Web (Phase 1)

Next.js App Router frontend that exposes parametric OpenSCAD models with
a live in-browser WASM preview. Phase 1 ships a single hardcoded model
page (`cylinder_holder_46mm_slot.scad`) wired to the inline `@param`
annotation parser.

## Prereqs

1. Node 22+
2. Vendored OpenSCAD libraries populated under `../libs/` (the WASM
   include closure walker fetches them through `/api/source`). Phase 1
   only needs `BOSL2` and `QuackWorks`:

   ```bash
   cd libs
   git clone https://github.com/BelfrySCAD/BOSL2.git BOSL2
   ( cd BOSL2 && git checkout 456fcd8 )
   git clone https://github.com/AndyLevesque/QuackWorks.git QuackWorks
   ( cd QuackWorks && git checkout 6123129 )
   ```

   Both pins match `libs/README.md`. BOSL2 is held back from HEAD because
   newer commits break QuackWorks' vector-spin syntax (st-kls).

## Run

```bash
npm install
npm run dev          # http://localhost:3000
npm test             # vitest, 23 tests across param parser + closure walker
npm run build        # production build
```

Open <http://localhost:3000/models/cylinder-holder-46>. Twiddle a slider —
the WASM render kicks off ~250ms after the last keystroke and the STL
swaps in once Manifold finishes (typically a few seconds on a warm page).

## Architecture

- `app/models/cylinder-holder-46/page.tsx` — server component reads the
  `.scad` source, parses params, hands them to `<ModelStudio>`.
- `components/ModelStudio.tsx` — client coordinator. Holds form state,
  debounces, drives `renderToStl`, swaps STL bytes into the viewer.
- `components/ParamForm.tsx` — auto-generates one control per parsed
  `@param` (slider+number, checkbox, select, text).
- `components/StlViewer.tsx` — three.js scene with ResizeObserver and
  iso camera fit-to-bbox.
- `lib/scad-params/parse.ts` — pure function that scans the
  `// === User-tunable parameters ===` block for `@param` annotations.
- `lib/wasm/closure.ts` — BFS over `include`/`use` to collect the
  minimal lib-file set (avoids the 60s mount of all 576 lib files seen
  in Phase 0 spike).
- `lib/wasm/render.ts` — lazy-loaded openscad-wasm-prebuilt instance,
  mounts the closure under `/libraries/`, runs with
  `--backend Manifold` (CGAL OOMs at 3.3GB on BOSL2; non-negotiable).
- `app/api/source/route.ts` — read-only file server scoped to
  `libs/` and `models/` with path-confinement + regex allowlist.

## `@param` annotation grammar

```
<name> = <default>; // @param <type> [attrs] label="..."
```

Types: `number`, `integer`, `boolean`, `string`, `enum`. Numeric attrs:
`min=`, `max=`, `step=`. Enums require `choices=a|b|c`. See
`lib/scad-params/parse.test.ts` for the full surface.

## Out of scope (Phase 1)

- STL download button (Phase 2)
- Gallery / multi-model routing (Phase 3)
- Vercel deploy config (Phase 3)
