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
  blurb/categoryId/params/presets in the app's `Param`/`Preset` shapes.
  The web app ingests it directly (lib/models/bd-manifest.ts); BD models
  are gallery-flag-gated (BD_MODELS_ENABLED, default off) until the
  detail view lands (P1c). Their catalog entries live in
  BUILD123D_CATALOG (lib/models/catalog.ts)
- `scripts/export.py` — STL (print) + GLB (viewer) + PNG (3-view review
  render) per model → `out/`; `--presets-only TARGET_DIR` bakes
  `TARGET_DIR/<slug>/<preset-id>.{stl,glb,png}` for every app-listed
  preset (the `.png` is the single-view gallery thumbnail; see below)
- `docs/renders/` — review renders (3-view PNGs) of shipped presets,
  tracked for PR review only (embed them in the PR body via commit-SHA
  raw URLs, see PR conventions). These do **not** feed the gallery.
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

## Mount contracts — deterministic geometry checks per mount type

A watertight, sane-looking render is not a working mount: the v2 Multiconnect
slot shipped upside-down and sealed (no way in) yet passed watertight export,
codex review, and the render audit. `tests/mount_contracts.py` adds a
**gating, deterministic** layer that verifies a mount's *function* with
boolean geometry, using the opengrid library's own parts as fixtures. For
`multiconnect-slot` it asserts: an entry **aperture** through the plate's
bottom face, the opening **orientation** faces −Z (not the top), a library
`RoundHead` **seats** with clearance, and a collision-free **entry travel**
from the aperture to the seat. `tests/test_mount_contracts.py` auto-runs the
contract over every registered model tagged with a mount — like the
build/watertight suite, a new model inherits it for free — and includes a
negative fixture proving the aperture check can fail.

A model **declares** its mounts and supplies the fixtures:
- add `mounts=("multiconnect-slot",)` to the `ModelSpec`, and
- expose `mount_fixtures(mount_type, values) -> registry.MountFixtures` in the
  model's module (the placed library cutters + each seated-head `Location`).

An unknown mount tag is rejected at registration.

**Adding a NEW mount contract** (e.g. an opengrid-snap contract later):
1. add the name to `registry.KNOWN_MOUNTS`;
2. write `verify_<mount>(part, fx)` in `tests/mount_contracts.py` (raise
   `AssertionError` on violation) and register it in `CONTRACTS` — the module
   asserts at import that every `KNOWN_MOUNTS` entry has a contract;
3. add an advisory rubric for it in `scripts/render_review.py` `RUBRICS`;
4. tag the models that carry it and implement their `mount_fixtures` hook.

### Advisory render review (Layer 2, not a gate)
`scripts/render_review.py` sends each model's 3-view PNG plus the mount rubric
to a vision model via OpenRouter and prints a Markdown summary. It is
**advisory only** — always exits 0, and degrades gracefully (a skip note)
when `OPENROUTER_API_KEY` is absent. Wiring it into CI needs a workflow edit
and the `OPENROUTER_API_KEY` secret — tracked as a follow-up (see the PR).

## PR conventions
**Embed renders via commit-SHA raw URLs, never branch-relative ones.**
A PR that shows off `docs/renders/*.png` must link them through a
**permanent** `raw.githubusercontent.com/<owner>/<repo>/<commit-sha>/...`
URL (a real 40-char commit SHA, not a branch name). Branch-relative GitHub
links (`.../blob/<branch>/...` or `.../raw/<branch>/...`) 404 the moment the
branch is deleted on merge — which is exactly when reviewers and future
readers open the PR (this bit us on #75). Example:

```markdown
![spray can holder](https://raw.githubusercontent.com/<owner>/stuff/<sha>/build123d/docs/renders/holder_spray_can.png)
```

Grab `<sha>` from `git rev-parse HEAD` after your final push.

## Gallery thumbnails — single source of truth (pst-1vi5)
The gallery card for a build123d model is served straight from the
build-time bake, not from a separately committed image:

- `scripts/bake-bd-presets.sh` (chained into the app's `prebuild` npm
  hook, gated on `BD_MODELS_ENABLED`) runs `export.py --presets-only
  build123d/baked`, which now emits, per preset, a single-view iso
  thumbnail `build123d/baked/<slug>/<preset>.png` **rendered from the
  same built part as that preset's GLB and STL**.
- `/api/thumbnail?model=<slug>` (app/api/thumbnail/route.ts) serves that
  PNG for build123d models — the first preset's — exactly as
  `/api/bd-asset` serves the baked GLB/STL. SCAD models are unchanged
  (`renders/<stem>/iso.png`).

Because the thumbnail, the viewer GLB, and the download STL are all
outputs of one bake of one part, a geometry or preset change can never
leave the listing card showing stale geometry. There is no image to
hand-commit or hand-refresh, and no CI mirror step to fall out of sync
(the earlier `render-all.py` docs-render mirror was removed — it went
stale on `build123d/**`-only PRs that don't trigger the render job).
The bake contract (`tests/test_presets_bake.py`) asserts the PNG is
produced alongside the STL/GLB for every app-listed preset. When
`BD_MODELS_ENABLED` is unset the bake is skipped and BD cards aren't
listed, so no thumbnail is requested; a stale-build 404 degrades to a
blank tile just like a missing GLB.

## Eval dimensions (vs OpenSCAD)
agent workability · geometry/output quality (real fillets) · CI fit · preview experience
