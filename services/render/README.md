# Native render service (Phase 1 spike — st-065)

A tiny containerized HTTP service that renders `models/*.scad` to STL
with **native** headless OpenSCAD, to replace the ~22 s
`openscad-wasm` render on `/api/export`'s cache-miss path (Phase 2,
tracked in st-rtb).

Native is ~3–4× faster on the corpus (ego blower mount: ~6.5 s vs ~22 s
WASM, warm) and immune to the WASM cold-start 504s.

**Phase 1 scope: build + validate entirely in a LOCAL container.** No
Cloud Run, no CI wiring, no `/api/export` proxy — those are Phase 2.

## Contract

`POST /render`

```jsonc
// request
{ "model": "models/ego_lb6500_blower_mount.scad",
  "params": { "mount_type": "opengrid" } }   // params optional; omitted → defaults
```

- **Success → `200`**, `content-type: application/sla`, body = **raw STL
  bytes**. The non-byte fields of `lib/wasm/render.ts`'s `RenderResult`
  ride in headers: `x-render-ok: true`, `x-render-ms`, `x-attempts`.
  Returning bytes (not a base64 JSON field) keeps a 6 MB STL from
  bloating to 8 MB and matches how `/api/export` already returns an STL,
  so the Phase-2 swap reads body + headers straight into a `RenderResult`.
- **Failure → `4xx`/`5xx`**, `content-type: application/json`,
  `{ ok: false, errorMessage, stderr?, attempts? }`.

`GET /health` → `200 {"ok":true}` (readiness probe).

### Status codes

| code | when |
|------|------|
| 200  | clean render (rc 0, no hard `ERROR`, no unresolved dep, non-empty STL) |
| 400  | invalid JSON, bad body shape, unknown param, or bad param value |
| 403  | model path fails the regex or escapes the baked model roots |
| 404  | path allowed but the model file isn't in the image |
| 413  | request body over 64 KiB |
| 500  | openscad failed, or produced a partial/empty STL |

## Parity (why outputs match the app)

The service **reuses `lib/scad-params/parse.ts`** — the exact
`parseScadParams` / `defaultsOf` / `formatScadLiteral` the app and WASM
path use — to turn params into `-D name=value` defines. It emits a define
for **every** declared param (defaults resolved), the same set the WASM
path's `applyParamOverrides` rewrites in-source, so the geometry (and the
st-uqk content-addressed cache key, which hashes the resolved params) is
equivalent. The bundler inlines the real `parse.ts`, so there is no second
copy to drift.

Validation guards mirror `app/api/export/route.ts` (path regex + root
confinement, param existence + kind/enum coercion) and the correctness
rules from `lib/wasm/render.ts`:

- exit 0 **with** a hard `ERROR:` logged → partial geometry, treat as
  failure (st-7x7);
- `WARNING: Can't open include/library/import '…'` → a dependency
  rendered silently absent, fail (st-zph);
- empty STL → fail; a failed render **never** returns bytes.

## Determinism

Given the same `(model, params)`, the service is **byte-deterministic**
run-to-run (verified). One caveat worth knowing for Phase 2: OpenSCAD's
STL tessellation is sensitive to the model's **absolute path** — the same
source at a different path yields a different (but still deterministic and
watertight) triangle ordering. Models are baked at a fixed `/app/models`
path, so this is stable across restarts; keep that mount point constant
across deploys.

## Build & run (local)

```bash
# from the repo root (build context = repo root)
docker build -f services/render/Dockerfile -t stuff-render .

docker run --rm -p 8080:8080 stuff-render
# → render service listening on :8080

# default (multiconnect) variant
curl -sX POST localhost:8080/render \
  -H 'content-type: application/json' \
  -d '{"model":"models/ego_lb6500_blower_mount.scad"}' \
  -o ego.stl -D -

# opengrid variant
curl -sX POST localhost:8080/render \
  -H 'content-type: application/json' \
  -d '{"model":"models/ego_lb6500_blower_mount.scad","params":{"mount_type":"opengrid"}}' \
  -o ego-opengrid.stl
```

### End-to-end validation

`services/render/validate.sh` builds the image, boots the container,
renders both ego variants + a couple of sanity models, runs the model
invariants (`scripts/check-invariants.py`) against the **service** output,
records the latency win, and exercises the error paths. It exits non-zero
on any failure.

```bash
services/render/validate.sh
```

## Local dev without Docker

The service is plain Node + stdlib; run the bundle directly against the
working tree (uses your host `openscad`):

```bash
node services/render/build.mjs      # bundle → dist/server.mjs
RENDER_REPO_ROOT="$PWD" OPENSCADPATH="$PWD/libs" RENDER_XVFB=0 \
  PORT=8099 node services/render/dist/server.mjs
```

## Env

| var | default | meaning |
|-----|---------|---------|
| `PORT` | `8080` | listen port |
| `RENDER_REPO_ROOT` | `cwd` | root that `models/` + `tests/fixtures/` resolve under |
| `OPENSCADPATH` | `<root>/libs` | vendored-library search path |
| `RENDER_XVFB` | on (`!=0`) | wrap openscad in `xvfb-run`; set `0` where headless export works |

## Phase 2 (st-d32): deploy + app wiring

Built and flag-gated; goes live once the operator's WIF infra exists.

- **CI deploy**: `.github/workflows/deploy-render-service.yml` builds this
  image and deploys to Cloud Run (auth-required, `--min-instances 1`)
  keylessly via GitHub OIDC → Workload Identity Federation. The job skips
  until the `GCP_WIF_PROVIDER` repo variable is set.
- **App wiring**: `/api/export` calls `POST /render` on a cache miss when
  `RENDER_SERVICE_URL` is set, authenticating with a Vercel-OIDC → WIF ID
  token (`lib/render-service/`). Any service failure falls back to the
  in-process WASM render. Native output is cached under a distinct
  `rendererVersion` (`native:<RENDER_SERVICE_RENDERER_VERSION>`) so it
  never shares an entry with WASM bytes — bump that env in lockstep with
  this image's openscad base pin. Details in `app/api/export/README.md`.

Runtime end-to-end verification (live WIF + Cloud Run) is a follow-up
once the operator setup in st-d32 lands. See st-rtb for the full phasing.
