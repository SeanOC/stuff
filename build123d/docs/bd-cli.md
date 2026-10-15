# bd: build a part once, query it many times

This is NOT the beads issue tracker's `bd`. Always invoke it as `uv run python -m bd ...` from build123d/; there is no `bd` executable.

`bd` builds a registered model (any slug in `manifest.json`, or its
`ModelSpec.name`) into a cached BREP once. Every later query reads that BREP
and does not rebuild the part. It resolves models the same way
`build123d/scripts/manifest.py` does (`holders/registry.py` `all_models()`), and
it audits with the same arguments as the registry print-audit gate
(`tests/test_print_audit.py`). Its verdicts are the gate's verdicts.

Bead pst-ptl41, stage 2a: `build`, `audit`, `extent`. Stage 2b adds `section`,
`parity` and `export`.

## Commands

```bash
cd build123d

# Build into the part cache and print the key (a second run is a HIT).
uv run python -m bd build openconnect-drawer --preset container
uv run python -m bd build underware-l --param channel_total_height=30
uv run python -m bd build underware-l --rebuild        # ignore the cache

# The registry print audit (overhang / bridge / wall / fillets / bed).
uv run python -m bd audit 0d447f0c…b755b               # a key from bd build
uv run python -m bd audit underware-l --preset L-tall  # or a slug: builds first, hit when cached

# Print-frame extent (after the model's print_frame) and the bed verdict.
uv run python -m bd extent holder-tombstone-sign --preset small --json
```

Every query takes either a 64-hex cache key or a slug with optional
`--preset` / `--param` / `--rebuild`. A slug runs `build` first, which is a hit
when the part is already cached. `--preset` and `--param` stack: the preset
sets its values first, then each `--param k=v` overrides one value.

**Output.** Each command prints a one-line summary. `audit` prints its
`PrintAuditReport.format()` block after the summary line. With `--json`, each
command prints exactly one JSON object instead: `build` gives
`{key, hit, brep, slug, model, preset, params, versions, source_hash, bbox,
volume, build_s}`, `audit` gives `{key, model, ok, failures, report}` and
`extent` gives `{key, model, extent_mm, bed_mm, fits, failure}`. An error gives
`{error}`.

**Exit codes.** `0` means success. `1` means the verdict failed: the audit is
not ok, or the part does not fit the bed. `2` means a usage or param error:
an unknown model, preset, param or key; a value the param's kind, range or
charset rejects; or a `ValueError` raised by the model's own `build(values)`.
The error message is the model's own text, never a traceback.

## The cache and its key

Entries live in `build123d/.cache/parts/` (gitignored). `BD_PART_CACHE=<dir>`
moves the store. Each entry is `<key>.brep`, which holds the part in model
coordinates (exactly what `spec.build(values)` returned), and `<key>.json`,
which holds slug, params, versions, source hash, bbox, volume and build
seconds. Writes are atomic. To clear the cache, run
`rm -rf build123d/.cache/parts`.

The BREP cache `build123d/.cache/parts/` is NOT the mesh bake `build123d/baked/`
written by `scripts/export.py --presets-only` (contract `tests/test_presets_bake.py`).

**Key** = sha256 over the model name, the resolved param values (defaults,
then preset, then `--param`), the audit cache's version tuple
(`tests/audit_cache.py` `_versions()`: build123d, OCP, python) and a **source
hash**. The source hash covers the relative path and bytes of every file of
any extension under `build123d/`, except these two lists:

1. **Non-geometry trees** (top level): `bd/`, `tests/`, `scripts/`, `ci/`,
   `reference/`, `viewer/`, `tools/`, `docs/`.
2. **Generated trees**: every `__pycache__/` directory and every `*.pyc` and
   `*.pyo` file; `baked/`, `.cache/` (where `bd` writes the BREPs this key
   names) and `out/` (the `scripts/export.py` output); and any dot-directory
   (`.venv/`, `.pytest_cache/`). All of these are gitignored or are tool and
   environment caches. The dependency versions that `.venv` would contribute
   are covered by the version tuple and by the hashed `uv.lock`.

Everything else is hashed, including `assets/` (fonts and meshes),
`labels/nominal_strokes.json`, `capture/sheets.json`, `manifest.json`,
`pyproject.toml` and `uv.lock`. Builders read non-Python files at runtime, and
they import across trees (`underware/` imports `labels/`, `cartridge_holder`
reads `opengrid_snap` constants), so no hand-picked list is safe. Editing or
regenerating any hashed file changes the key, and a stale BREP is never served
after a model or data edit. `--rebuild` is an escape hatch, not the defence.

Why the excluded trees cannot hide a build input:

- `reference/*.json` and `tests/fixtures/*.json` are provenance locators and
  verification-oracle inputs, never build inputs. The values builders use are
  inlined in hashed `.py` files (`multibuild/constants.py`,
  `multibuild/fixpoint.py` cite `reference/` only as provenance).
- `capture/synth.py` is the one hashed module that reaches an excluded tree.
  It imports `scripts.thumbnail` and the `tests/fixtures` oracles, and it is on
  no build path today. If a builder ever imports it, revisit these lists.
- `scripts/` holds view and plane metadata (`scripts.thumbnail.PlaneSpec`,
  imported by `registry.py` and the tombstone models). That metadata
  deliberately tracks the current code, not the key. Queries apply the
  model's `print_frame` and orientation from live code at query time, so
  they are never frozen into a cached BREP.

The audit has its own cache below this one (`build123d/.cache/audit/`,
`docs/print-audit-profile.md` "Cache"). A reloaded BREP has the same audit-cache
key as a fresh build (`test_cached_part_audits_like_a_fresh_build`), so
`bd audit` and the registry audit tests share entries.

## Before you write a probe script

If the question is "does this preset or param set build, pass the audit, fit
the bed, how big is it, what does it weigh", don't write a one-off
`probe.py` that rebuilds the part. Run `uv run python -m bd build` once, then
query the key: `audit` for the gate verdict, and `extent` for the
print-frame size and bed fit. A sweep over param endpoints is a shell loop over
`uv run python -m bd audit <slug> --param k=v --json`. Each endpoint builds
once, and a re-run is all hits. Write a script only when no subcommand answers
the question. If the question recurs, propose it as a subcommand rather than
leaving a probe behind.
