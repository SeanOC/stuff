# build123d PoC — "manufacturing as code" experiment

Parametric models in **Python + [build123d](https://github.com/gumyr/build123d)**, consuming **published
parametric libraries as dependencies** — evaluated against our OpenSCAD workflow (see repo root).

## Hard rule
openGrid / Multiconnect geometry comes **only** from the pinned
[`opengrid` library](https://makerrepo.com/r/fangpenlin/opengrid/) (MIT, build123d-native) or other
existing build123d ecosystem libraries. **No home-grown mount geometry. No porting from our SCAD.**
If a library can't do something, that's a *finding for the eval*, not an invitation to work around it.

## Layout
- `holders/registry.py` — model registry with typed params + presets (mirrors
  `lib/scad-params/parse.ts` exactly); registering a model buys it export,
  manifest entry, and tests automatically
- `holders/smoke.py` — library-provided smoke artifacts (tile, MC round head);
  smoke-tagged models are excluded from the app-facing manifest + bake
- `holders/cylindrical.py` — the PoC parametric C-ring holder (lands via its bead)
- `scripts/manifest.py` — deterministic emitter + strict validator for
  `manifest.json` (the app-facing catalog; CI gates freshness via
  `git diff --exit-code`)
- `manifest.json` — committed, app-facing: models with slug/engine/title/
  blurb/categoryId/params/presets in the app's `Param`/`Preset` shapes
- `scripts/export.py` — STL (print) + GLB (viewer) + PNG (3-view review
  render) per model → `out/`; `--presets-only TARGET_DIR` bakes
  `TARGET_DIR/<slug>/<preset-id>.{stl,glb}` for every app-listed preset
- `docs/renders/` — review renders (3-view PNGs) of shipped presets, tracked for PR review
- `viewer/index.html` — drag-drop GLB viewer (model-viewer, static, no build)
- `tests/` — registry-driven: every model must build, be watertight, have volume; library dims pinned

## Commands
```bash
uv sync              # env (Python ≥3.13, uv.lock pinned, opengrid pinned by commit)
uv run pytest tests/ # registry-driven checks (incl. manifest schema + bake)
uv run python scripts/export.py   # build everything → out/
uv run python scripts/export.py --presets-only out/presets  # bake presets
uv run python scripts/manifest.py # regenerate manifest.json (run after model changes)
```

Adding a model: register a `ModelSpec` with `params`, `presets` (at least
one), `title`, and `category_id` (an id from `lib/models/catalog.ts`), then
run the manifest emitter. The registry rejects spec/preset errors at
registration time (unknown params, out-of-range defaults, enum values not
in choices, duplicate slugs/ids).

## Eval dimensions (vs OpenSCAD)
agent workability · geometry/output quality (real fillets) · CI fit · preview experience
