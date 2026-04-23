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
   claims), and adds a catalog entry.
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

| File | Description |
| --- | --- |
| `cylindrical_holder_slot.scad` | Multiboard-mounted holder for any cylindrical item (42–77 mm tested), Multiconnect slot backer. |
| `popcorn_kernel.scad` | Cartoonish popped popcorn kernel — replacement piece for a Disney toddler-toy popcorn stand. |
| `spraycan_carrier_6x50mm.scad` | 2×3 spray-can tote carrier for 50 mm cans: six open-front C-ring cradles, drainage base plate, semicircular-arched handle. Kid-safe, wet-safe, tall-can (195 mm) clearance. |

## Development

After cloning:

```bash
./scripts/setup-git-hooks.sh   # one-time — attaches the commit-trailer hook
npm install
npm run dev                    # http://localhost:3000
```

Render a model directly via OpenSCAD (Manifold backend required —
CGAL OOMs on BOSL2):

```bash
openscad --backend Manifold -o out.stl models/cylindrical_holder_slot.scad
```

`libs/` vendors BOSL2 and QuackWorks pinned to compatible commits —
newer BOSL2 breaks QuackWorks' vector-spin syntax. See
[`libs/README.md`](libs/README.md) for the pins.

## Continuous integration

Every push and PR runs render-thumbnail regeneration, per-model
invariants (watertight, single-body, triangle ceiling,
`PRINT_ANCHOR_BBOX` drift), Playwright end-to-end tests, and vitest
unit tests. Thumbnails and invariants are mandatory gates. See
[`docs/ci.md`](docs/ci.md) for the full pipeline.

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
