# Stuff Web

Next.js App Router frontend that exposes parametric OpenSCAD models with
a live in-browser WASM preview: model gallery, dynamic slug routing,
presets, and Vercel deploy.

## Prereqs

1. Node 22+
2. Vendored OpenSCAD libraries populated under `../libs/` (the WASM
   include closure walker fetches them through `/api/source`).
   `bash scripts/vendor-libs.sh` clones and pins all of them; it also
   runs as the npm `prebuild` hook, so `npm run build` does it for
   you. `npm run test:e2e` does not vendor — it assumes a prior
   `npm run build` (or an explicit script run). Pins and the BOSL2
   hold-back rationale live in [`../libs/README.md`](../libs/README.md).

## Run

```bash
npm install
npm run dev          # http://localhost:3000
npm test             # vitest (unit)
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
3. Wait for a render with `waitForRenderState(page, "ready")` from
   `tests/e2e/support/render.ts` — it keys on the viewer's
   `data-render-state` attribute (the render lifecycle itself), not a
   text pattern that future UI changes will outlive.
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
guard the original silent-override bug: the
class where the form reports new values but the render sees old ones.
It asserts the STL's X-extent shifts from 40mm (default) to 160mm
(override). If `applyParamOverrides` ever becomes a no-op, the
override render produces a 40mm plate and the assertion fails with a
numeric diff, not a timeout.

Open <http://localhost:3000/>. The gallery lists every `.scad` file in
`models/` with a thumbnail, title, and parameter count. Click a card to
land on `/models/<slug>`, twiddle a slider, and watch the in-browser
render swap in (a few seconds for a cold Manifold build).

## Architecture

- `app/page.tsx` — server-rendered gallery. Calls `listModels()` and
  emits a CSS grid of cards.
- `app/models/[slug]/page.tsx` — dynamic route with
  `generateStaticParams()` over every `.scad` file. Falls back to
  notFound() on unknown slugs. Renders `<DetailPage>`; the param rail
  shows a "No parameters in this model." note when `@param` count is
  zero.
- `app/api/thumbnail/route.ts` — serves the gallery thumbnail with a
  regex stem allowlist + path confinement; 403 on hostile slug, 404 on
  missing render. SCAD models resolve `renders/<stem>/iso.png`;
  build123d models resolve the build-time-baked
  `build123d/baked/<slug>/<preset>.png` (same source as the detail
  GLB, pst-1vi5).
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
  minimal lib-file set (avoids mounting the whole `libs/` tree).
- `lib/wasm/render.ts` — lazy-loaded openscad-wasm-prebuilt instance,
  mounts the closure under `/libraries/`, runs with `--backend Manifold`
  — CGAL OOMs on BOSL2.

## `@param` annotation grammar

```
<name> = <default>; // @param <type> [attrs] label="..."
```

Types: `number`, `integer`, `boolean`, `string`, `enum`. Numeric attrs:
`min=`, `max=`, `step=`. Enums require `choices=a|b|c`. Optional
display hints on any param: `unit=`, `group=`. Presets are
`// @preset id="…" label="…" <param>=<value>` lines; the parser scans
them anywhere in the file, with the convention of clustering them near
the parameter block. See `lib/scad-params/parse.test.ts` for the full
surface.

A model file without any `@param` annotations still appears in the
gallery and renders at compile-time defaults; the detail page shows a
"No parameters in this model." note in place of the form.

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

No environment variables required. The `models/` and `libs/` trees
ship as part of the build because the API routes read them from disk
at request time (Node.js runtime).
