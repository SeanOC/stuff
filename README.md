# stuff

3D-printable parts written by [Claude Code](https://claude.com/claude-code)
and previewed live in the browser. Every model is a single-file
parametric OpenSCAD design on top of
[BOSL2](https://github.com/BelfrySCAD/BOSL2) and
[QuackWorks](https://github.com/AndyLevesque/QuackWorks); a Next.js
+ WASM UI at **[stuff.seanoc.com](https://stuff.seanoc.com)** exposes
each one with live sliders and an STL download.

The interesting part isn't the models — it's the authoring loop.

![Detail page — cylindrical holder with live WASM render, grouped param rail, and render log](docs/screenshots/cylindrical-holder-preview.png)

## How it works

1. Describe the part to Claude Code: *"parametric holder for X, fits
   Y range, mounts to Z."*
2. Claude writes the `.scad`, annotates each `@param`, seeds a
   `<stem>.invariants.py` sidecar (watertight / bbox / single-body
   claims), a param-sweep test, and a catalog entry.
3. Push. CI regenerates thumbnails and runs the invariants gate.
4. Vercel deploys on merge to `main`.
5. Open the model's page at
   [stuff.seanoc.com](https://stuff.seanoc.com) to tweak sliders and
   download an STL.

A minimal first prompt worth copy-pasting:

> *Add a new model: a parametric wall-mounted hook for hanging a bike
> helmet. Parameters: hook diameter (30–80 mm), mount plate size,
> Multiboard backer. Annotate with `@param`, add an invariants
> sidecar, add a catalog entry, render thumbnails.*

See [AGENTS.md](AGENTS.md) for the agent-facing spec (param grammar,
invariants, render pipeline) and [`app/README.md`](app/README.md) for
web-app architecture.

## Models

Every `.scad` under [`models/`](models/) ships with a gallery card at
[stuff.seanoc.com](https://stuff.seanoc.com). The catalog —
category and blurb per model — lives in
[`lib/models/catalog.ts`](lib/models/catalog.ts), which is the single
source of truth (CI fails on a model without an entry, so the site
listing is always complete).

Adapting an externally-authored STL for openGrid wall mounting? Follow
[`docs/imported-model-opengrid-playbook.md`](docs/imported-model-opengrid-playbook.md)
— the step-by-step recipe (import, snap orientation, supportless
printability, blending, verification) distilled from the
`ego_powerhead_mount` series.

## Development

After cloning:

```bash
./scripts/setup-git-hooks.sh   # one-time — commit-trailer + pre-commit gotcha
                               # gate (see docs/dx-precommit.md)
npm install
npm run dev                    # http://localhost:3000
```

Render a model directly via OpenSCAD (the project pins engine snapshot
`2025.06.12.ai25773` — downloadable from this repo's
`openscad-2025.06.12.ai25773` release tag; other builds can disagree
about watertightness, see [`docs/ci.md`](docs/ci.md)):

```bash
openscad -o out.stl models/cylindrical_holder_slot.scad
```

`libs/` vendors BOSL2, QuackWorks, and gridfinity-rebuilt-openscad
pinned to compatible commits — newer BOSL2 breaks QuackWorks'
vector-spin syntax. See [`libs/README.md`](libs/README.md) for the
pins and [`docs/deps-review-2026-07.md`](docs/deps-review-2026-07.md)
for the July 2026 dependency review.

## Continuous integration

Every push and PR runs vitest unit tests and Playwright end-to-end
tests. Model-touching changes additionally run render-thumbnail
regeneration, STL export with per-model invariants (watertight,
single-body, triangle ceiling, `PRINT_ANCHOR_BBOX` drift), and a wasm
param sweep that renders every model at each parameter's extremes
through the site's real browser pipeline. Renders happen on a pinned
OpenSCAD engine (`2025.06.12.ai25773`) for watertightness parity. See
[`docs/ci.md`](docs/ci.md) for the full pipeline and the job/trigger
matrix.

## License

- **Code** — [MIT](LICENSE).
- **Models** (`models/*.scad`) — [![CC BY-NC-SA 4.0](https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
  (see also [`models/LICENSE`](models/LICENSE))
- Bundled libraries keep their own licenses:
  [`libs/BOSL2/LICENSE`](libs/BOSL2/LICENSE) (BSD-2-Clause) and
  [`libs/QuackWorks/LICENSE`](libs/QuackWorks/LICENSE) (CC BY-NC-SA 4.0).

---

*Built with [Claude Code](https://claude.com/claude-code) using a
multi-agent authoring workflow.*
