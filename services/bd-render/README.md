# Live build123d render service (bead pst-so26)

The build123d analogue of [`services/render/`](../render/) (native
OpenSCAD): a tiny stdlib-only HTTP service that turns
`POST /render {slug, params}` into a freshly-built **GLB** (or STL) for the
app's live parametric preview. build123d is Python/OCP and cannot run in a
Vercel function or in the browser, so it lives behind **Cloud Run**.

This is **P2a** of the build123d integration epic (`pst-7srz`) — the render
**service** only. The app-side client, `/api/bd-render` route, and live-param
UI are separate beads (**P2b** `pst-6ugb`, **P2c**). Presets stay baked and
served from `build123d/baked/` (P1c); this service is for on-the-fly tweaks.

## Contract

`POST /render?format=glb|stl` (default `glb`)

```jsonc
// request
{ "slug": "holder-spray-can",
  "params": { "d": 70 } }        // params optional; omitted → registry defaults
```

- **Success → `200`**, body = **raw GLB bytes** (`content-type:
  model/gltf-binary`), or **raw STL bytes** (`application/sla`) when
  `?format=stl`. Bytes (not base64 JSON) mirror how `services/render` and
  `/api/bd-asset` already return geometry.
- **Failure → `4xx`/`5xx`**, `content-type: application/json`,
  `{ ok: false, errorMessage, ... }`.

`GET /health` | `/healthz` → `200 {"ok": true}` (Cloud Run readiness probe).

### Status codes

| code | when |
|------|------|
| 200  | clean build, non-empty mesh |
| 400  | invalid JSON / body shape, unknown-key or out-of-range param, unknown `?format` |
| 403  | unknown / non-app-listed slug (smoke artifacts are excluded) |
| 413  | request body over 64 KiB |
| 500  | build/export failure, or an empty/zero-volume mesh (fail-loud) |
| 504  | render exceeded the hard per-request timeout (`BD_RENDER_TIMEOUT`, 90 s) |

## Parity (why inputs match the app)

Params are validated through the **authoritative Python contract** —
`holders.registry.ModelSpec.resolve_values(overrides)`, the exact call the
preset bake uses. It fills defaults and raises `ValueError` on unknown keys
or out-of-range values, so the service accepts precisely the inputs the app
manifest (`build123d/manifest.json`) describes. This is the role
`lib/scad-params/parse.ts` plays for the SCAD service. Only **app-listed**
(non-smoke) models are buildable; anything else is `403`.

## Isolation & the hard timeout

The build + export runs in a one-shot **`render_worker.py` subprocess** so a
pathological (but in-range) parameter combo can't hang the server: OCP
builds run in C++ and can't be interrupted from a Python thread, so the
parent bounds the worker with `subprocess.run(timeout=…)` and kills it on
overrun (`→ 504`). Fast param validation (slug + `resolve_values`) runs in
the server process first, so `4xx` inputs never spawn a worker. The worker
also fails loud on a zero-volume mesh rather than writing an empty file.

## Build & run (local, Docker) — the container smoke (AC #6)

```bash
# from the repo root (build context = repo root)
services/bd-render/validate.sh
```

`validate.sh` builds the image, boots the container, and exercises the full
contract against the running service: `/health`, a **default GLB render**
(proves the holder builds to a non-empty binary glTF), an STL render, and
the `403`/`400` validation paths. Exits non-zero on any failure.

Manually:

```bash
docker build -f services/bd-render/Dockerfile -t stuff-bd-render .
docker run --rm -p 8080:8080 stuff-bd-render

curl -sX POST localhost:8080/render \
  -H 'content-type: application/json' \
  -d '{"slug":"holder-spray-can","params":{"d":70}}' -o out.glb
```

## Local dev without Docker

The service is plain Python + stdlib; run it on the build123d uv env so OCP
+ the registry import:

```bash
cd build123d
BD_RENDER_TIMEOUT=90 PORT=8099 \
  uv run python ../services/bd-render/server.py
```

## Tests

Integration tests live at
[`build123d/tests/test_bd_render_service.py`](../../build123d/tests/test_bd_render_service.py).
They boot the real server on an ephemeral port and hit it over HTTP, so the
full path (validation → worker subprocess → export) is covered end-to-end
(a holder builds in ~0.2 s):

```bash
cd build123d && uv run pytest tests/test_bd_render_service.py -q
```

They live in the build123d suite because `bd123.yml` is the only pytest job
wired into CI (and it carries the OCP env). A dedicated `services/` CI job —
and moving the deploy workflow into place (see below) — needs a
`.github/workflows/` edit that was **out of scope for the automation worker
that authored this**; tracked as a follow-up.

## Env

| var | default | meaning |
|-----|---------|---------|
| `PORT` | `8080` | listen port |
| `BD_BUILD123D_ROOT` | `<repo>/build123d` | root that `holders`/`scripts` import from (fixed to `/build123d` in the image) |
| `BD_RENDER_TIMEOUT` | `90` | hard per-request render timeout, seconds |

## Deploy (ships dark)

The deploy pipeline is staged at
[`deploy-bd-render-service.yml`](./deploy-bd-render-service.yml) and **must
be moved into `.github/workflows/` by a human** (the authoring worker can't
touch that directory):

```bash
git mv services/bd-render/deploy-bd-render-service.yml \
       .github/workflows/deploy-bd-render-service.yml
```

It mirrors `deploy-render-service.yml`: keyless GitHub-OIDC → WIF,
`--no-allow-unauthenticated`, **`--min-instances 0`** (scale-to-zero,
operator decision), `--max-instances 3`, `--cpu 2 --memory 4Gi`,
`--timeout 120`. It **ships dark** — gated on the `GCP_WIF_PROVIDER` repo
variable — so even once moved it is a no-op until the operator sets that
variable. It reuses the SCAD service's WIF infra; only the service name
(`BD_RENDER_SERVICE_NAME`, default `stuff-bd-render`) differs.
