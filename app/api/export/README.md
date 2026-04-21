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
x-render-ms: 4321
x-libs-mounted: 18
```

Errors return JSON `{ "error": "...", ...detail }` with a 4xx/5xx code.

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
