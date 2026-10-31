# Print bridge (stuff → Bambuddy)

A small HTTP service and CLI that turn "print model X on printer Y" into
Bambuddy API calls. It fetches the geometry from stuff's own HTTP routes,
uploads it to the Bambuddy library, then starts the printer's slicer
pipeline. Bambuddy handles slicing, queueing and the plate-empty camera check
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
| GET | `/printers` | tailnet | `[{id, name, model, state, plate_detection_calibrated, pipeline}]`. `state` comes from `/printers/{id}/status`, calibration from `/printers/{id}/camera/plate-detection/status`. Either is `null` if Bambuddy can't answer. `access_code` and `serial_number` are never forwarded. |
| POST | `/print` | trusted login | `202 {library_file_id, run_id, status_url}` |
| GET | `/runs/{id}` | tailnet | `{status, copies, copies_completed, copies_failed, error_message, sliced_library_file_id, jobs:[{queue_item_id, status, printer_id}]}` |

`status_url` is **relative** (`/runs/{run_id}`). The caller prefixes it with
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

The steps:

1. **Printer and pipeline.** Look up the printer (404 if unknown), then map
   its id to a pipeline name through `PIPELINES` and resolve that name with
   `GET /api/v1/slicer-pipelines/`. A missing entry or name gives 409. All of
   this happens before any geometry is built.
2. **Geometry from stuff.**
   - bd + preset: `GET /api/bd-asset/{slug}/{preset}?format=…`
   - bd + params: `POST /api/bd-render?format=…` with `{slug, params}`
   - scad: `POST /api/export` with `{model, params}`

   The format is STL, with one exception for bd models. When the printer's
   Bambuddy `model` contains "h2c" (case-insensitive), the bridge first asks
   for `format=3mf&profile=bambu-h2c-0.4`. A single-colour model answers that
   with a 400 "… is not a multi-colour model" and the bridge falls back to
   STL. The bridge logs which branch it took. Any other non-2xx from stuff
   gives 502 with the upstream message.
3. **Library upload.** The file goes into folder `stuff/<slug>`, created on
   first use. Its name is `<slug>-<preset | sha12 of canonical params>.<stl|3mf>`.
   If the upload response carries `duplicate_of`, the bridge reuses that file
   id. It then calls `PUT /api/v1/library/files/{id}` with:
   - `external_url`: the stuff page URL, with the preset or params in the query
   - `notes`: the canonical params JSON (sorted keys, no spaces)

   Bambuddy's `FileUpdate` names the link field `external_url`; it has no
   `source_url` field.
4. **Double-print guard.** If this library file already has a queued,
   slicing, dispatching or in-progress run on the same pipeline, the bridge
   returns 409 with that run's `run_id` and `status_url` and starts nothing.
   `duplicate_of` dedupes the file, not the run, so without this guard a
   double-clicked Print would print twice. Once the earlier run reaches a
   terminal state, the same file can print again.
5. **Eligibility.** `POST /slicer-pipelines/{id}/check-eligibility`. If the
   report is `ok: false` or lists any issue, the bridge returns 409 with the
   report verbatim. It never retries with `force`.
6. **Run.** `POST /slicer-pipelines/{id}/run {source_library_file_id, copies}`,
   then `202`.

The bridge never calls `POST /api/v1/queue/`, `/library/files/{id}/print`,
`add-to-queue`, webhook start/stop or any printer-control endpoint, and never
sends `force: true`. Prints are dispatched only through the pipeline run.

Errors are `{"error": …}` plus context (`upstream`, `report`, `run_id`).
Bambuddy or stuff unreachable or non-2xx → 502. Bad body → 400 or 422.

## CLI

```bash
cd bridge
uv run --env-file ~/.config/stuff-bridge/env python -m bridge print \
  --source bd --slug holder-bench-width-saddle --preset width_clearance1 \
  --printer-id 2 --copies 1                      # + --param k=v (JSON values)
uv run --env-file ~/.config/stuff-bridge/env python -m bridge serve   # 127.0.0.1:8787
```

`print` calls the same `Bridge.start_print` as `POST /print`. It prints the
202 body, then polls the run (`--poll-interval`, default 10 s) and prints
each status change until the run is terminal. It exits 0 on `completed` and 1
otherwise. `--no-wait` stops after the 202 body.

## Environment

The bridge reads its configuration from the environment only.

| Var | Required | Meaning |
|---|---|---|
| `STUFF_URL` | yes | e.g. `https://stuff.seanoc.com`. Geometry source and the base of the library file's link. |
| `BAMBUDDY_URL` | yes | e.g. `http://cubert:8000` |
| `BAMBUDDY_API_KEY` | yes | Bambuddy API key. Never logged, echoed or returned. |
| `PIPELINES` | yes | `printer_id=pipeline name` list, e.g. `2=stuff-joey,1=stuff-crushinator` |
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
  `/printers` and `/runs/{id}` need no login header, so any tailnet peer can
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
