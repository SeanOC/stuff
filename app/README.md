# Stuff Web

Next.js App Router frontend that exposes parametric OpenSCAD models with
a live in-browser WASM preview. Phase 3 ships the model gallery, dynamic
slug routing, and Vercel deploy config.

## Prereqs

1. Node 22+
2. Vendored OpenSCAD libraries populated under `../libs/` (the WASM
   include closure walker fetches them through `/api/source`):

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
npm test             # vitest, 33 tests
npm run build        # production build
```

Open <http://localhost:3000/>. The gallery lists every `.scad` file in
`models/` with a thumbnail, title, and parameter count. Click a card to
land on `/models/<slug>`, twiddle a slider, and watch the in-browser
render swap in (~250ms debounce, then a few seconds for Manifold).

## Architecture

- `app/page.tsx` — server-rendered gallery. Calls `listModels()` and
  emits a CSS grid of cards.
- `app/models/[slug]/page.tsx` — dynamic route with
  `generateStaticParams()` over every `.scad` file. Falls back to
  notFound() on unknown slugs. Renders `<ModelStudio>` always; shows a
  "parameters not yet annotated" note when `@param` count is zero.
- `app/api/thumbnail/route.ts` — serves `renders/<stem>/top.png` with
  regex stem allowlist + path confinement; 403 on hostile slug, 404 on
  missing render.
- `app/api/source/route.ts` — read-only file server scoped to `libs/`
  and `models/`; same path-confinement pattern.
- `app/api/export/route.ts` — server-side STL render. Validates
  body shape, coerces values to declared `@param` kinds, applies
  overrides via `applyParamOverrides()`, and runs `renderToStl()`.
- `lib/models/discover.ts` — filesystem scan that backs the gallery and
  the dynamic route. Title derives from the first non-blank comment line
  with a stem-derived fallback.
- `lib/scad-params/parse.ts` — pure parser for the
  `// === User-tunable parameters ===` block.
- `lib/scad-params/parse.ts#applyParamOverrides` — rewrites each
  `@param`-annotated assignment line in source. Required because
  `openscad-wasm-prebuilt` silently ignores `-D` flags and a prepended
  prelude gets clobbered by OpenSCAD's last-assignment-wins scoping.
- `lib/wasm/closure.ts` — BFS over `include`/`use` to collect the
  minimal lib-file set (avoids the 60s mount of all 576 lib files seen
  in Phase 0 spike).
- `lib/wasm/render.ts` — lazy-loaded openscad-wasm-prebuilt instance,
  mounts the closure under `/libraries/`, runs with
  `--backend Manifold` (CGAL OOMs at 3.3GB on BOSL2; non-negotiable).

## `@param` annotation grammar

```
<name> = <default>; // @param <type> [attrs] label="..."
```

Types: `number`, `integer`, `boolean`, `string`, `enum`. Numeric attrs:
`min=`, `max=`, `step=`. Enums require `choices=a|b|c`. See
`lib/scad-params/parse.test.ts` for the full surface.

A model file without any `@param` annotations still appears in the
gallery and renders at compile-time defaults; the model page shows a
"parameters not yet annotated" note in place of the form.

## Vercel deploy

Project config lives in `vercel.ts` (the typed replacement for
`vercel.json`). Per-route concerns — `runtime`, `maxDuration` — are
declared as `export const` in each route file rather than centrally.

```bash
# one-time link
vercel link

# preview
vercel deploy

# promote to production once the preview smoke-tests
vercel deploy --prod
```

No environment variables required for Phase 3. The `models/` and
`libs/` trees ship as part of the build because the API routes read
them from disk at request time (Fluid Compute, Node.js runtime).

## Loopback artifact server

`scripts/serve.py` is a stdlib HTTP browser for the rendered PNG +
exported STL artifacts on a headless print rig. Independent of this
Next.js app — see top-level `CLAUDE.md` for usage.
