# stuff

A small collection of 3D-printable parametric designs — mostly
[Multiboard](https://multiboard.io/) accessories — written in OpenSCAD
on top of [BOSL2](https://github.com/BelfrySCAD/BOSL2) and
[QuackWorks](https://github.com/AndyLevesque/QuackWorks), plus a
Next.js + WASM web UI that renders every model in the browser and
downloads STLs on demand.

## Models

Everything under `models/` is a single-file parametric design. Pop one
open in OpenSCAD, or visit its page in the web app (see below) to
twiddle sliders and grab a fresh STL.

| File | Description |
| --- | --- |
| `cylindrical_holder_slot.scad` | Multiboard-mounted parametric holder for any cylindrical item (42–77mm tested), Multiconnect slot backer. Consolidates four earlier fixed-diameter variants. |
| `smoke_motor_mount.scad` | Smoke-test plate: rectangular base with centered bore + boss and four counter-bored mounts. Used as the minimum end-to-end model for the pipeline. |
| `spraycan_holder_70mm.scad` | Multiboard-mounted spray-can holder (70mm), snap-connector backer variant. |

## Web app

`app/` is a Next.js App Router frontend that exposes every model as a
live parametric page: sliders for each `@param`, in-browser WASM render
driving a three.js preview, and a server-side STL export for download.
Deployed on Vercel. See [`app/README.md`](app/README.md) for
architecture, the `@param` annotation grammar, and the deploy flow.

## Libraries

`libs/` vendors the two OpenSCAD libraries the models depend on —
BOSL2 and QuackWorks — both pinned to specific commits that keep the
two compatible (newer BOSL2 commits break QuackWorks' vector-spin
syntax). See [`libs/README.md`](libs/README.md) for the exact pins
and the clone procedure.

## Development

Render a model directly via OpenSCAD (Manifold backend required; CGAL
OOMs on BOSL2):

```bash
openscad --backend Manifold -o out.stl models/smoke_motor_mount.scad
```

Run the web app locally (Next.js project is rooted at the repo root;
`app/` holds routes + the user-facing README):

```bash
npm install
npm run dev          # http://localhost:3000
```

`app/README.md` has the full picture, including the Playwright e2e
suite, CI workflow, and the Vercel deploy flow.
