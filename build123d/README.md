# build123d PoC — "manufacturing as code" experiment

Parametric models in **Python + [build123d](https://github.com/gumyr/build123d)**, consuming **published
parametric libraries as dependencies** — evaluated against our OpenSCAD workflow (see repo root).

> **Design guidelines:** every model in this directory follows [docs/design-guidelines.md](docs/design-guidelines.md) (printability for the Bambu H2S in PLA/PCTG, edge treatment, material efficiency, structural integration, mount parametrics). The reviewer checks PRs against §6.

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

### Mount parametrics (design-guidelines §5)

A mount exposes what changes its **robustness**, never what the spec fixes. The
C-ring holder's Multiconnect slot back plate carries four tunables (group
`mount`), all 100% library geometry — the plate derives from them:

| param | kind | range | default | effect |
| --- | --- | --- | --- | --- |
| `slot_count` | integer | 1–3 | today's width heuristic (1 for both presets) | slots at the fixed 28 mm pitch, centred; sets plate width |
| `slot_travel` | number (mm) | `SLOT_TRAVEL_MIN`(=head bottom-radius + overshoot = 12) – 45 | 28 (== `MULTICONNECT_SLOT_LENGTH`) | slide length the wall head rides to the seat; sets plate height |
| `snap_notches` | boolean | — | true | library snap detent (robust) vs plain slot channel + seat (lighter/looser) |
| `plate_margin` | number (mm) | 2–6 | 3 | solid material around the slot envelope |

The `slot_travel` **floor is derived from the library constants**, not guessed:
below `MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS + overshoot` a seated `RoundHead`
pokes back out the bottom aperture instead of seating within the plate
(`test_cylindrical.test_slot_travel_floor_is_derived_from_library_constants`).
**Spec constants stay fixed and unexposed**: the 28 mm pitch, the head/slot
cross-section profile, all clearances, and the ~4.15 mm pocket depth are library
constants. Defaults reproduce today's geometry exactly (volume + bbox equal), so
the shipped `spray_can` / `bottle_500ml` presets are unchanged; each model also
ships a `*_light` (1 slot, min travel, no notches) and `*_robust` (2 slots, full
travel, notches) preset. The mount contract suite runs over the whole
`slot_count × slot_travel × snap_notches` grid
(`test_mount_contracts.test_mount_contract_over_robustness_grid`).

Tall, thick collars receive a localized plate-top gusset when `wall` exceeds
half the panel thickness and the collar extends more than one panel thickness
above the plate. The full-wall-wide web overlaps the plate by one wall and
rises at 45° toward the collar, with chamfered ramp edges, 1 mm vertical
junction fillets, and the bore kept clear. The all-max spray-can corner
(`h=120`, `wall=4`, two slots, 45 mm travel)
passes the print audit with registered cutter exclusions. All six shipped
presets bypass this reinforcement and retain their original geometry.

**Adding a NEW mount contract** (e.g. an opengrid-snap contract later):
1. add the name to `registry.KNOWN_MOUNTS`;
2. write `verify_<mount>(part, fx)` in `tests/mount_contracts.py` (raise
   `AssertionError` on violation) and register it in `CONTRACTS` — the module
   asserts at import that every `KNOWN_MOUNTS` entry has a contract;
3. add an advisory rubric for it in `scripts/render_review.py` `RUBRICS`;
4. tag the models that carry it and implement their `mount_fixtures` hook.

## Print audit — deterministic printability checks (design-guidelines §1)

A watertight, contract-passing part can still be unprintable. `tests/print_audit.py`
turns the [design-guidelines §1](docs/design-guidelines.md) rules into a standing,
deterministic check for the target machine (**Bambu H2S, 0.4 mm nozzle, PLA/PCTG,
no supports**) instead of a reviewer eyeball. Given a `Part` and its declared print
orientation it returns a typed `PrintAuditReport`:

- **overhang** — steepest downward face from vertical (threshold **45°**);
- **bridge** — widest unsupported flat span (threshold **10 mm**), measured by a
  sampled local-span scan (solid-above/void-below raster + shortest through-run),
  so a thin annular or arc ledge is scored by its narrow real width, not its
  bounding-box diameter;
- **min wall** — thinnest wall, sampled by inward normal marching (threshold **0.9 mm**;
  load-bearing 1.6 mm deferred until faces can be tagged);
- **downward fillets** — any downward-facing *curved* face (use a 45° chamfer) → fail;
- **bed chamfer** — plate-contact edge chamfer present (0.3–0.5 mm) → advisory *warn*.

Faces inside a registered library cutter's envelope are excluded (the slot profile
is spec, not our overhang). `report.format()` emits a compact block to paste into a
PR (design-guidelines §6 items 1–3).

**Print orientation** is a unit vector on the `ModelSpec` — `print_orientation`, the
model-frame direction that points UP (away from the bed) in the print pose. Default
`(0, 0, 1)` ("printed as modelled"); a holder printed back-plate-down on its −Y face
would declare `(0, 1, 0)`. The field is additive (backward-compatible default) and is
**not** serialized into `manifest.json`. A production model declares a non-default
orientation only once it passes the audit at that orientation (design-guidelines §6
items 1–3) — see the advisory note below.

`tests/test_print_audit.py` has two layers, like the mount contracts:
- **synthetic self-tests** (always gating): a 50° overhang fails / 40° passes, a 12 mm
  bridge fails / 8 mm passes, a 0.8 mm wall fails / 1.2 mm passes, a bottom fillet fails
  / bottom chamfer passes, a wide-bbox thin annular ledge is *not* read as a bridge, and
  a library cutter pocket is excluded;
- **registry-driven run** (**hard gate for production models**): every registered model
  is audited at its declared orientation and the report printed. With
  `PRINT_AUDIT_REQUIRED = True` (the current setting), a failure on a **production** model
  is a hard failure (design-guidelines §6); a **smoke** scaffolding tile (`_is_production`
  is `False`) stays an advisory `xfail`. Set the flag back to `False` to make the whole
  registry run advisory again.

The C-ring holders now **pass** §1 at their declared `print_orientation = (0, 0, 1)`
(upright, floor on the bed): overhang 45.0°, 0 downward fillets, 0 mm bridge, min wall
2.15 mm (`pst-xz3m`, "holder v5"). Two fixes made this honest: the bore re-carve now
spans the whole part height so it no longer leaves a 90° downward ledge at its end cap,
and the audit's downward-fillet check now distinguishes a constant-45° **conical chamfer**
on a round bed edge (a legitimate elephant-foot relief — the CONE it produces is not a
rolled fillet) from a real bottom fillet whose slope sweeps past 45°. The one remaining
audit miss is `smoke_opengrid_tile_1x1` (0.80 mm wall < 0.9 mm) — and that 0.80 mm is the
**openGrid snap-fit retention dent**, a published-spec mating feature that cannot be
thickened without breaking cross-tool compatibility. It is therefore a **permanent spec
exemption** (kept advisory via the smoke exemption), not a bug to fix (`pst-saf9`); the
exemption is kept narrow and self-policing by `test_smoke_tile_wall_miss_is_openGrid_spec`
(the tile must still fail, and fail *only* on that spec wall), so a future audit change
cannot silently void it or let it excuse a new, real defect.

### Advisory render review (Layer 2, not a gate)
`scripts/render_review.py` sends each model's 3-view PNG plus the mount rubric
to a vision model via OpenRouter and prints a Markdown summary (naming the exact
model id and prompt version it used). It is **advisory only** — always exits 0,
and degrades gracefully (a skip note) when `OPENROUTER_API_KEY` is absent.

**CI wiring (pst-ae3v):** the review runs as an added step in the advisory
`bd123` job, after the export step, against the just-rendered `out/*.png`. It
never gates — the `bd123` job is not a required check, the step carries
`continue-on-error`, and the script always exits 0. It runs once per PR head
(the `bd123` job runs once per push to a `build123d/**` PR) and writes its
Markdown straight to the job step summary.

**Toggle:** delete the `OPENROUTER_API_KEY` repo secret to disable the review
(the step prints a skip note and stays green); delete the step for a hard off;
set `RENDER_REVIEW_MODEL` to change the vision model.

Activating it requires a `.github/workflows/` edit plus the `OPENROUTER_API_KEY`
secret — both outside the worker's access — so the exact change is **staged for
an operator** in [`ci/`](ci/README.md): the proposed workflow
(`ci/bd123.yml.proposed`) and the two activation steps.

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
