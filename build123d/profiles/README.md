# Printer profiles

A printer profile turns the generic multi-colour 3MF into a slicer project
for one printer (pst-jyey1). `scripts/export.py apply_printer_profile` copies
the generic file and adds:

- in `3D/3dmodel.model`: the Bambu Studio namespace, `requiredextensions="p"`,
  `Application` and `BambuStudio:3mfVersion` metadata, and a build-item
  transform that puts the part at the front of the plate (turned 90° about Z
  when only that leaves room for the prime tower behind it);
- `Metadata/project_settings.config`: the profile's template with
  `filament_colour[i]` set to part i's colour and `wipe_tower_x/y` moved
  behind the part.

Everything else, including `Metadata/model_settings.config` (part i on
filament i + 1), is byte-identical to the generic file. Bambu Studio only
reads the config when `Application` starts with `BambuStudio-`, and the
minimal file with only that tag crashes it, so the template must be a full
config saved by the slicer itself. The partial JSONs under Bambu Studio's
`resources/profiles/BBL/` do not load.

## Profiles

| id | Template provenance |
| --- | --- |
| `bambu-h2c-0.4` | Exported by Sean from Bambu Studio 02.08.02.61 on 2026-10-15: H2C 0.4 nozzle, 0.16mm Standard @BBL H2C, 8× Bambu PLA Basic @BBL H2C. `project_settings.json` is that project's `Metadata/project_settings.config`, unchanged (581 keys; no account or device keys). |

## Adding a printer

1. In the slicer, choose the printer, process and filament preset; add
   filaments until there are as many slots as the largest model needs
   (the tombstone sign uses 8); put any cube on the plate; File → Save
   Project As.
2. Copy the project's `Metadata/project_settings.config` to
   `profiles/<id>/project_settings.json`. Keep every key. Never commit the
   raw project: its `3D/3dmodel.model` carries the saver's
   `DesignerUserId`.
3. Register a `PrinterProfile` in `profiles/__init__.py`: `filament_slots`
   is the template's `filament_colour` length, and `application` is the
   project's own `Application` metadata (its version must equal the
   config's `version` key; `tests/test_printer_profiles.py` checks both).
4. Run `uv run python scripts/manifest.py` (the app reads `printerProfiles`
   from `manifest.json`) and the bake (`scripts/export.py --presets-only`),
   then check the result headless: `bambu-studio --export-3mf rt.3mf
   <file>` (the re-exported config must keep the printer and colours) and
   `bambu-studio --slice 0 --export-3mf sliced.3mf <file>`
   (`Metadata/slice_info.config` lists one `<filament>` per part with
   non-zero `used_g`). The Linux AppImage runs headless after
   `--appimage-extract`.
