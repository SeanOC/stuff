# `/api/export` — server-side STL export

`POST /api/export` runs OpenSCAD on the server with the user's parameter
overrides and streams back a binary STL.

## Request

```http
POST /api/export
content-type: application/json

{
  "model": "models/cylindrical_holder_slot.scad",
  "params": { "can_diameter": 50, "ring_height": 60 }
}
```

- `model` must match `^models/[A-Za-z0-9._/-]+\.scad$` and resolve under
  the repo's `models/` directory after `path.resolve` confinement check.
- `params` keys must each appear in that model's parsed `@param`
  manifest. Unknown keys → 400. Type mismatches (e.g. boolean param
  given a number) → 400.

## Response

```
200 OK
content-type: application/sla
content-disposition: attachment; filename="cylindrical_holder_slot.stl"
x-cache: MISS
x-render-ms: 4321
x-libs-mounted: 18
```

Errors return JSON `{ "error": "...", ...detail }` with a 4xx/5xx code.

## STL cache (st-uqk)

Hull-heavy models (the Ego blower mount) take ~22s to render even warm,
risking cold-start 504s. To avoid re-rendering identical requests, the
route caches successful renders in a durable **Vercel Blob** store keyed
by content:

```
key = sha256( closureHash + normalizedParams + rendererVersion )
```

- **`closureHash`** — sha256 of the entry `.scad` plus every file in its
  `include`/`use` closure (walked by `lib/wasm/closure.ts`) and every
  `import()`ed binary asset. Content, never mtime/version strings, so any
  edit to the model **or a shared lib it pulls in** busts the cache. Files
  are sorted by path before hashing, so include-walk order can't shift it.
- **`normalizedParams`** — every declared param with defaults resolved,
  keys sorted, values formatted stably. An omitted param and its explicit
  default collide to the same key; param order never matters; any value
  change differs. (`-0` collapses to `0`.)
- **`rendererVersion`** — the `openscad-wasm-prebuilt` pin. A renderer
  upgrade can change output, so it must bust the cache.

Flow: compute key → `store.get`. **HIT** → stream the stored STL with
`cache-control: public, max-age=31536000, immutable` and `x-cache: HIT`
(sub-second; also rides Vercel's edge/browser cache). **MISS** → run the
existing render path → **only on `result.ok`** store the bytes → serve
with `x-cache: MISS` and `cache-control: no-store`. A failed/partial
render is never cached (the st-zph/st-7x7 class).

Configuration & fallbacks:

- Requires `BLOB_READ_WRITE_TOKEN` (set automatically when a Vercel Blob
  store is linked to the project). **Without it, caching is disabled** and
  the route live-renders every request exactly as before — no `x-cache`
  header. Local dev and CI need no Blob credentials.
- Cache faults are swallowed: a `get`/`put` error logs a warning and falls
  through to a live render rather than failing the export.
- The store has no auto-eviction — the `export-cache/` namespace grows
  unbounded. Acceptable short-term for a content-addressed cache (dead keys
  are simply never read again); a TTL/LRU sweep can come later.
- Concurrent misses for the same key both render (thundering herd) and
  re-`put` byte-identical bytes (`allowOverwrite`). Not deduped; a
  single-flight lock is a possible later refinement.

Key composition and hit/miss/invalidation are covered by
`lib/wasm/export-cache.test.ts` (unit) and `app/api/export/route.test.ts`
(end-to-end with an in-memory blob mock).

## Native render service path (st-d32)

When `RENDER_SERVICE_URL` is set, a cache **MISS** renders via the native
OpenSCAD Cloud Run service (`services/render/`, ~3–4× faster than WASM)
instead of in-process WASM:

```
key(native) → store.get → HIT? serve
  → MISS → POST <service>/render (keyless WIF auth)
      → ok    → store.put(key(native)) → serve  (x-renderer: native)
      → error → key(wasm) → store.get → HIT? serve
                  → WASM render → store.put(key(wasm))  (x-renderer: wasm)
```

- **Flag-gated, ships dark**: `RENDER_SERVICE_URL` unset (or the WIF vars
  missing/malformed — warned once) means this section doesn't exist; the
  route behaves exactly as documented above, WASM-only, no `x-renderer`
  header.
- **Graceful degradation**: any service failure — missing OIDC token,
  token exchange, network, timeout (45s), non-200, empty body — logs a
  warning and falls back to the WASM render. `renderViaService` never
  throws (`lib/render-service/client.ts`).
- **Distinct cache keys**: native and WASM tessellate differently, so the
  native path keys with `rendererVersion = "native:" +
  RENDER_SERVICE_RENDERER_VERSION` (default `"1"`; bump in lockstep with
  the service image's openscad pin) while WASM keeps the
  `openscad-wasm-prebuilt` semver. The two output spaces can never share
  an entry; WASM fallback bytes are stored under the WASM key only.
- **Keyless auth (operator-locked)**: no stored secrets. Each miss
  exchanges the request's Vercel OIDC token (`x-vercel-oidc-token` header;
  `VERCEL_OIDC_TOKEN` env for `vercel env pull` local dev) for a
  Google-signed ID token via Workload Identity Federation
  (`lib/render-service/auth.ts`), impersonating the render-invoker SA.
  Cloud Run is deployed auth-required, so only that SA can invoke it.

Vercel env:

| var | meaning |
|-----|---------|
| `RENDER_SERVICE_URL` | Cloud Run service URL; unset = feature off |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name (`projects/…/providers/…`) |
| `GCP_RENDER_INVOKER_SA` | render-invoker SA email (`roles/run.invoker`) |
| `RENDER_SERVICE_RENDERER_VERSION` | cache-busting suffix tracking the service's openscad pin |

Deploys of the service are keyless too: `.github/workflows/
deploy-render-service.yml` (GitHub OIDC → WIF), gated on the
`GCP_WIF_PROVIDER` repo variable so it no-ops until the operator's WIF
infra exists.

Known limitation: the closure hash comes from the **app deployment's**
model/lib files, while the service renders its **image's baked copies**.
Deploy both from the same commit (the deploy workflow's paths filter
covers models/libs changes) or a skewed window can cache bytes rendered
from older sources.

## OpenSCAD packaging

We **don't** ship a native `openscad` binary. The route reuses the
WASM driver (`lib/wasm/render.ts`) used by the browser preview —
openscad-wasm-prebuilt@1.2.0 (OpenSCAD 2025.01.19), `--backend Manifold`
mandatory. Same closure walker mounts only the include set the model
needs, so cold renders stay bounded.

Trade-off: WASM is ~2× slower than native for large CSG, but it keeps
one rendering codepath, dodges the ~50MB binary in the function bundle,
and avoids per-version binary maintenance. Revisit if Phase 3+ needs
sub-second exports on heavy models — the path forward is dropping a
Linux openscad into `app/api/export/bin/` and shelling out via
`child_process.spawn` (the existing `scripts/export.py` shows the
arg layout).

## Param overrides under WASM

Two override mechanisms don't work with `openscad-wasm-prebuilt@1.2.0`:

1. **`-D name=value` CLI flags** — silently ignored by this WASM build.
   Native `openscad -D` works; the WASM port doesn't honour it.
2. **Prepending `name = value;` lines** — clobbered by the file's own
   declarations because OpenSCAD is last-assignment-wins per scope.

So `applyParamOverrides` (in `lib/scad-params/parse.ts`) rewrites the
matching `<name> = ...;` line in-source before handing it to WASM.
Whitespace alignment around `=` is preserved. Only the first match
per param is replaced — variable reuse inside module bodies stays
intact.

## Vercel runtime config

```ts
export const runtime = "nodejs";   // Fluid Compute Node.js
export const maxDuration = 120;    // CSG headroom; default is 300s
```

WASM modules need the Node runtime — Edge can't load them. Fluid
Compute reuses instances across requests so the cached
`openscad-wasm-prebuilt` import survives between calls.

`next.config.mjs` lists `openscad-wasm-prebuilt` under
`serverExternalPackages` to keep the bundler from trying to walk its
binary assets.

## Lib resolution

The closure walker fetches `include`/`use` targets through a
filesystem-backed fetcher (`fsLibFetcher` in `route.ts`) that reads
from `<repo>/libs/`. Same `BOSL2 + QuackWorks` pins as the browser
side — see top-level `app/README.md` for setup.

## Validation walkthrough

| Input                                          | Result          |
|-----------------------------------------------|-----------------|
| `model: "../scripts/serve.py"`                | 403 path        |
| `model: "models/missing.scad"`                | 404             |
| `params: { unknown_key: 1 }`                  | 400 unknown     |
| `params: { can_diameter: "not-a-number" }`    | 400 invalid     |
| Default params, valid model                   | 200 + STL bytes |
