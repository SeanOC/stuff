# Print bridge (stuff → Bambuddy)

A small HTTP service and CLI that turn "print model X on printer Y" into
Bambuddy API calls. It fetches the geometry from stuff's own HTTP routes,
uploads it to the Bambuddy library, then starts the printer's slicer
pipeline. An optional spool pick replaces the recipe’s filament and colour,
then queues the sliced file with an explicit AMS mapping. Bambuddy handles
the plate-empty camera check
before the print auto-starts.

It runs on cubert and is reachable only on the tailnet. It has no dependency
on `build123d/` or the web app code; it only calls their public routes.

Bambuddy target: 1.2.5.7 (REST spec at `http://cubert:8000/openapi.json`,
auth header `X-API-Key`).

## Endpoints

All bodies are JSON.

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/health` | tailnet | `{ok, bambuddy_reachable}`. `bambuddy_reachable` is an authenticated `GET /api/v1/printers/`, so it also catches a bad key. |
| GET | `/printers` | tailnet | `[{id, name, model, state, plate_detection_calibrated, pipeline, nozzle_mm}]`. `state` and `nozzle_mm` (installed nozzle diameters in mm, parsed from `nozzles[].nozzle_diameter`; `[]` when unknown) come from `/printers/{id}/status`, calibration from `/printers/{id}/camera/plate-detection/status`. Either is `null` if Bambuddy can't answer. `access_code` and `serial_number` are never forwarded. |
| POST | `/print` | trusted login | `202 {library_file_id, run_id, status_url}` |
| GET | `/printers/{id}/spools` | tailnet | Loaded AMS trays with resolved filament presets; see below. |
| GET | `/queue/{id}` | tailnet | Same seven status keys as `/runs/{id}`, for one queue row. |
| GET | `/queue/batches/{id}` | tailnet | Same seven status keys, plus `batch_status`; derived from counts. |
| GET | `/runs/{id}` | tailnet | `{status, copies, copies_completed, copies_failed, error_message, sliced_library_file_id, jobs:[{queue_item_id, status, printer_id}]}` |

`status_url` is **relative** (`/runs/{run_id}`, `/queue/{item_id}` or
`/queue/batches/{batch_id}`). The caller prefixes it with
the bridge origin it already used for `POST /print`.

### `POST /print`

```json
{"source": "bd", "slug": "holder-bench-width-saddle", "preset": "width_clearance1",
 "printer_id": 2, "copies": 1}
{"source": "bd", "slug": "label-card", "params": {"text": "Hi"}, "printer_id": 2}
{"source": "scad", "model": "models/opengrid_bin.scad", "params": {"width_units": 2},
 "printer_id": 1}
```

- `source: "bd"` needs `slug` plus either `preset` or `params`, not both.
  With neither, the bridge renders the model's default params.
- `source: "scad"` needs `model`, the repo-relative path `models/<stem>.scad`.
  `/api/export` returns 403 for any other path form. The bridge turns a bare
  `<stem>` into that path for you. SCAD models have no presets.
- `copies` defaults to 1 and must be at least 1.
- Optional `spool: {"ams_id": 0, "tray_id": 3}` selects a loaded AMS tray.
  Omit it to keep the original pipeline path (and its response) unchanged.

The steps:

1. **Printer and pipeline.** Look up the printer (404 if unknown), then map
   its id to a pipeline name through `PIPELINES` and resolve that name with
   `GET /api/v1/slicer-pipelines/`. A missing entry or name gives 409. All of
   this happens before any geometry is built.
2. **Nozzle check.** Still before any geometry or upload, the bridge compares
   the printer's installed nozzle(s) (`GET /printers/{id}/status` →
   `nozzles[].nozzle_diameter`, empty and non-numeric entries skipped) with the
   nozzle the pipeline slices for, and refuses a mismatch with
   `409 {"error": "nozzle mismatch", "installed": [0.6], "pipeline": 0.4}`.
   Bambuddy's eligibility check does not compare nozzles: a 0.4 pipeline on a
   0.6 printer was accepted, failed on the printer within a second with no HMS
   code, and was re-dispatched every few minutes (2026-10-31). The pipeline's
   nozzle comes from, in order:
   - `GET /api/v1/slicer/preset-values?source=…&id=…&slot=printer` for the
     pipeline's `printer_preset` (`nozzle_diameter`, else `printer_variant`).
     Read best effort: any error, 404 or missing field is unknown, never a 502.
     Bambuddy 1.2.5.7 serves only `slot=process` and answers 400, so today this
     is always unknown.
   - A nozzle token (`.4`, `0.4`, `0.4mm`) in the printer preset's name (a
     `standard` preset's id is its name; `cloud`/`local` ids are opaque), else
     in the pipeline name — used only when the name holds exactly one token
     (`PCTG-1.5x0.6` is ambiguous). For the live pipelines
     (`Crushinator - PCTG - .4`) the pipeline name is what carries the check,
     so keep the nozzle in it. A single decimal that is not a nozzle
     (`PETG - 0.2` meaning layer height) would be read as one and mis-refuse;
     every refusal logs both values at WARNING.

   Unknown on either side logs and proceeds. A match on any installed nozzle
   passes (dual-nozzle H2C). The H2C 3MF profile (`bambu-h2c-0.4`) is only
   cross-checked: a pipeline slicing for another size logs a warning.
3. **Geometry from stuff.**
   - bd + preset: `GET /api/bd-asset/{slug}/{preset}?format=…`
   - bd + params: `POST /api/bd-render?format=…` with `{slug, params}`
   - scad: `POST /api/export` with `{model, params}`

   The format is STL, with one exception for bd models. When the printer's
   Bambuddy `model` contains "h2c" (case-insensitive), the bridge first asks
   for `format=3mf&profile=bambu-h2c-0.4`. A single-colour model answers that
   with a 400 "… is not a multi-colour model" and the bridge falls back to
   STL. The bridge logs which branch it took. Any other non-2xx from stuff
   gives 502 with the upstream message.
4. **Library upload.** The file goes into folder `stuff/<slug>`, created on
   first use. Its name is `<slug>-<preset | sha12 of canonical params>.<stl|3mf>`.
   If the upload response carries `duplicate_of`, the bridge reuses that file
   id. It then calls `PUT /api/v1/library/files/{id}` with:
   - `external_url`: the stuff model page URL, with the preset or params in
     the query. stuff's model pages do not read `?preset=` or params from the
     query (they open on their defaults), so the link only finds the model.
   - `notes`: the canonical params JSON (sorted keys, no spaces). This is the
     record of what was printed.

   Bambuddy's `FileUpdate` names the link field `external_url`; it has no
   `source_url` field.
5. **Double-print guard.** If this library file already has a queued,
   slicing, dispatching or in-progress run on the same pipeline, the bridge
   returns 409 with that run's `run_id` and `status_url` and starts nothing.
   `duplicate_of` dedupes the file, not the run, so without this guard a
   double-clicked Print would print twice. Once the earlier run reaches a
   terminal state, the same file can print again.
6. **Eligibility.** `POST /slicer-pipelines/{id}/check-eligibility`. If the
   report is `ok: false` or lists any issue, the bridge returns 409 with the
   report verbatim. It never retries with `force`.
7. **Run.** `POST /slicer-pipelines/{id}/run {source_library_file_id, copies}`,
   then `202`.

With a spool pick, steps 1–6 still run, then the bridge follows the spool
path below. The bridge never calls `/library/files/{id}/print`, `add-to-queue`,
webhooks or printer-control endpoints, and never sends `force: true`.
Queue access is limited to GET list/item/batch and POST creation. It never
PATCHes/DELETEs rows or calls start/stop/cancel/reorder/bulk/batch dispatch.
Bambuddy's scheduler dispatches both pipeline and explicitly queued jobs.

Errors are `{"error": …}` plus context (`upstream`, `report`, `run_id`).
Bambuddy or stuff unreachable or non-2xx → 502. A 2xx Bambuddy body that is
not JSON or not the expected shape is also 502: `error` names the call and
upstream status, `upstream` quotes the first 200 characters of the body.
Bad request body → 400 or 422.

## Spool selection (Bambuddy 1.2.5.7)

`GET /printers/{id}/spools` returns one object per loaded AMS tray:

```json
{"ams_id": 0, "tray_id": 0, "slot": 0, "material": "PLA",
 "name": "Bambu PLA Glow", "colour": "#DCF478", "remain_pct": null,
 "preset": {"source": "standard", "id": "Bambu PLA Glow @BBL H2S"},
 "generic": false, "resolved": true}
```

Only these fields are forwarded. Unknown remaining percentage (`-1`) becomes
null; missing/invalid colours become null. Empty trays and the external spool
(254) are excluded. An unresolved loaded tray stays visible with `preset:null`
and `resolved:false`; printing it returns 409 with the spool details.

Preset resolution, in order:

1. Optional `FILAMENT_PRESETS` override by `tray_info_idx` wins.
2. Resolve a filament name from `spool-defaults.slicer_filament_name`, then
   `/cloud/builtin-filaments`, then `/cloud/filament-id-map`.
3. Resolve the recipe's printer preset name P from the grouped `/slicer/presets`
   response, using its source and id. Prefer a `standard.filament` whose
   `compatible_printers` contains P and whose name starts with `<name> @`.
   Among matches choose the shortest name (then name/id to break ties).
4. Otherwise use the cloud filament named exactly `<name> @<P>`.
5. Otherwise use a compatible standard `Generic <tray_type> @BBL ...` entry
   (shortest), marked `generic:true`. An empty material never gets a generic.

The bridge locks each `(printer_id, source library file id)` across slice and
queue creation. Before slicing, `GET /queue/?printer_id=N` detects a pending
or printing row with `library_file_name == <source stem>.gcode.3mf`; a duplicate
returns 409 with `queue_item_id` and `/queue/{id}` as `status_url`. The existing
active pipeline-run guard and nozzle check also apply.

`POST /library/files/{id}/slice` uses the configured pipeline's `printer_preset`,
`process_preset` and `bed_type`, plus the resolved single `filament_presets`
entry and `filament_colours:["#RRGGBB"]` (first six digits of a six/eight-digit
hex tray colour, otherwise omitted). It polls `/slice-jobs/{job_id}` every
2 seconds for at most **4 minutes**, including HTTP waits, inside the UI's
5-minute POST deadline. Completed jobs supply `result.library_file_id`.
Failures, cancellations and timeouts return 502 with the job's error text;
no queue POST occurs. Upload/geometry time is separate from this slice budget.

The queue POST sends only `printer_id`, the sliced `library_file_id`,
`ams_mapping:[slot]`, `quantity:copies` and `use_ams:true`. Manual-start,
skip-filament-check and force-like settings retain Bambuddy defaults.
The AMS slot rule comes from Bambuddy **1.2.5.7**,
`backend/app/api/routes/printers.py::_slot_preset_key`, mirroring its frontend
`getGlobalTrayId`. Equivalent mapping snippet (the OpenAPI documents the id
spaces, not this arithmetic):

```python
if 128 <= ams_id <= 135:  # AMS-HT: its sole tray has id 0
    slot = ams_id
else:  # AMS ids 0–3, tray ids 0–3
    slot = ams_id * 4 + tray_id
```

The spool path returns:

```json
{"library_file_id": 500, "sliced_library_file_id": 800,
 "queue_item_id": 1000, "batch_id": null, "status_url": "/queue/1000"}
```

Multiple copies return a batch id and `/queue/batches/{batch_id}`. Item reads
preserve the row status (`pending`, `printing`, `completed`, `failed`, `skipped`,
`cancelled`), with copies=1 and completed/failed counters of 0 or 1. Batch reads
use quantity/completed_count/failed_count for counters, with `jobs:[]` and
`error_message:null`. The upstream bare status string is only `batch_status`;
the pollable status comes from this ordered table:

| First matching condition | Status |
|---|---|
| printing_count > 0 | printing |
| pending_count > 0 | pending |
| completed_count == quantity | completed |
| completed_count == 0 and failed_count == 0 | cancelled |
| completed_count == 0 | failed |
| otherwise | partial_failure |

If a queue id returned by this bridge disappears upstream, its read returns
200 with `status:"unknown"`, `error_message:"queue item not found"`, null
completed/failed counters and `jobs:[]`. Receipts are in memory for the bridge
process lifetime; an unrecognised missing id returns 404. A pipeline-run 404
retains its original behavior. Batch counts follow the deployed OpenAPI;
there is no live batch fixture, so the mayor's post-deploy copies=2 smoke
print must verify this mapping. Workers use only the sanitised mock fixtures.

## CLI

```bash
cd bridge
uv run --env-file ~/.config/stuff-bridge/env python -m bridge print \
  --source bd --slug holder-bench-width-saddle --preset width_clearance1 \
  --printer-id 2 --copies 1                      # + --param k=v (JSON values)
uv run --env-file ~/.config/stuff-bridge/env python -m bridge spools --printer-id 2
# Add --spool 128/0 to print with Joey's AMS-HT spool.
uv run --env-file ~/.config/stuff-bridge/env python -m bridge serve   # 127.0.0.1:8787
```

`print` calls the same `Bridge.start_print` as `POST /print`. It prints the
202 body, then follows `status_url` (`--poll-interval`, default 10 s) and prints
each status change until the run is terminal. `--no-wait` stops after the 202
body. `--max-wait SECONDS` stops polling after that long; by default it waits
until the run is terminal. `--model` takes `x`, `models/x` or
`models/x.scad` and always sends `models/x.scad`.

| Exit | Meaning |
|---|---|
| 0 | run `completed`, or `--no-wait` and the start was accepted |
| 1 | start rejected, or the run ended `failed`, `partial_failure`, `cancelled` or `skipped` |
| 2 | bad config (missing environment) |
| 3 | `--max-wait` elapsed first; the last status goes to stderr |
| 4 | polling failed (Bambuddy errored or was unreachable); the run's outcome is unknown. The error and last status go to stderr |

## Environment

The bridge reads its configuration from the environment only.

| Var | Required | Meaning |
|---|---|---|
| `STUFF_URL` | yes | e.g. `https://stuff.seanoc.com`. Geometry source and the base of the library file's link. |
| `BAMBUDDY_URL` | yes | e.g. `http://cubert:8000` |
| `BAMBUDDY_API_KEY` | yes | Bambuddy API key. Never logged, echoed or returned. |
| `PIPELINES` | yes | `printer_id=pipeline name` list, e.g. `2=stuff-joey,1=stuff-crushinator` |
| `FILAMENT_PRESETS` | no | Comma-separated `<tray_info_idx>=<source>:<id>` overrides, e.g. `GFA12=standard:Bambu PLA Glow @BBL H2S,P9e57294=cloud:PFUS4ab9490cde01cf`. Sources: standard, cloud, local, orca_cloud. Absent means no overrides. |
| `TRUSTED_LOGIN` | yes | The tailnet login allowed to start prints |
| `ALLOWED_ORIGIN` | no | CORS origin, default `https://stuff.seanoc.com` |

If any required variable is missing, the process refuses to start
(`refusing to start: missing required environment: …`, exit 2).

## Auth model

- **The service binds `127.0.0.1` only.** The bind address is hard-coded in
  `bridge/__main__.py` and is not configurable. `tailscale serve` is the only
  way in, and it sets `Tailscale-User-Login` for tailnet users. The header
  can be trusted only because of this. If anything ever proxies port 8787
  some other way, a client can spoof the header and print.
- **`POST /print` requires `Tailscale-User-Login` to equal `TRUSTED_LOGIN`.**
  The comparison is exact and case-insensitive. Anything else gets 403, and
  that check runs before body validation.
- **The read-only endpoints are tailnet-enumerable by design.** `/health`,
  `/printers`, `/printers/{id}/spools`, `/runs/{id}` and queue status reads
  need no login header, so any tailnet peer can
  list the printers and run states. They expose no access codes, serials or
  keys.
- **CORS** allows exactly `ALLOWED_ORIGIN`, methods GET and POST, and the
  `content-type` header.

## Deploy (the mayor runs this; the bead does not deploy)

```bash
cd ~/<stuff checkout>/bridge && uv sync

install -d -m 700 ~/.config/stuff-bridge
install -m 600 /dev/null ~/.config/stuff-bridge/env    # outside the repo, 0600
$EDITOR ~/.config/stuff-bridge/env                     # the six vars above, KEY=value lines

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/stuff-bridge.service <<'EOF'
[Unit]
Description=stuff -> Bambuddy print bridge
After=network-online.target

[Service]
WorkingDirectory=%h/<stuff checkout>/bridge
EnvironmentFile=%h/.config/stuff-bridge/env
ExecStart=%h/.local/bin/uv run --frozen python -m bridge serve --port 8787
Restart=on-failure

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now stuff-bridge
loginctl enable-linger "$USER"        # keep running without a login session

tailscale serve --bg --https=8443 http://127.0.0.1:8787
```

Smoke test from another tailnet host:

```bash
curl https://cubert.<tailnet>.ts.net:8443/health
curl https://cubert.<tailnet>.ts.net:8443/printers
```

Then run one `print` per source: bd preset, bd params and scad. The scad run
proves the `models/<stem>.scad` path form against the real `/api/export`,
which the tests can only fake.

## Development

```bash
cd bridge
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

The tests use a fake Bambuddy and a fake stuff behind one `httpx.MockTransport`
(`tests/conftest.py`), on `.invalid` hosts. No test can reach cubert or
stuff.seanoc.com. The fake fails any test that calls a forbidden Bambuddy
endpoint or sends `force`.

No CI job runs these tests yet. Adding one needs a `.github/workflows/` change,
which workers can't make (follow-up pst-0hykt).
