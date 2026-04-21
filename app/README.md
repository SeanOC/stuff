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
npm test             # vitest, 33 unit tests
npm run build        # production build
```

## Tests

Two tiers:

```bash
npm test              # vitest (unit)
npm run test:e2e      # playwright (e2e, boots its own server on :3111)
npm run test:e2e:ui   # playwright UI mode — interactive debugging
npm run test:all      # unit + e2e
```

The e2e run boots `next dev` locally (faster feedback) and `next start`
in CI (post-build fidelity). Both bind to 127.0.0.1:3111 so they don't
collide with a developer's `next dev` on :3000. Set `PLAYWRIGHT_PORT`
to override.

### Adding a new e2e test

1. Drop a `tests/e2e/<name>.spec.ts`. Playwright auto-discovers.
2. Hit pages via `page.goto("/models/…")` — `baseURL` is already set.
3. Lean on the status-line text pattern (`/rendered in \d+ms · [\d,]+ bytes/`)
   when you need to wait for a WASM render to complete — it's the most
   stable signal the coordinator exposes.
4. For anything that might vary by render (byte counts, bboxes), assert
   on deltas between two states, not absolute values — keeps the test
   robust across OpenSCAD version bumps.

### Debugging a CI failure

CI uploads `playwright-report/` and `test-results/` as workflow
artifacts on failure (including trace + screenshot + video). Download
from the Actions run, then:

```bash
npx playwright show-report playwright-report/
```

Local repro: `CI=1 npm run test:e2e` runs in CI mode (prod build, 1
retry, 2 workers). Add `--headed` to watch it run.

### Silent-override regression

`tests/fixtures/bug_regression.scad` + `tests/e2e/bug-regression.spec.ts`
exist specifically to guard the Phase 1/2 silent-override bug: the
class where the form reports new values but the render sees old ones.
Test asserts the STL's X-extent shifts from 40mm (default) to 160mm
(override). If `applyParamOverrides` ever becomes a no-op, the
override render produces a 40mm plate and the assertion fails with a
numeric diff, not a timeout.

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
