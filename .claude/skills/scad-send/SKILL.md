---
name: scad-send
description: Send a sliced 3MF (or slice an STL/SCAD first) to a Bambu Lab X1C via Bambu Cloud and start the print. Wraps Bambu Studio CLI for slicing and the unofficial coelacant1/Bambu-Lab-Cloud-API Python lib for upload + cloud print start. Cloud path (not LAN) — keeps Bambu Handy usable. Phase 1 scaffold: dry-run works end-to-end; live send requires one-time auth setup documented in the runbook.
---

# scad-send

End-point of the iteration loop: once an STL has been exported and the
user has physically decided to print it, this skill slices and triggers
the print on a bound Bambu X1C over Bambu Cloud.

## Human-in-the-loop gate — MANDATORY

**Do not invoke this skill without explicit user approval.** This is the
point where bytes become filament. The approval handshake is a
behavioral contract, not something the script enforces.

Before running `scripts/send.py` against a real printer:

1. The STL must already exist (produced by `scad-export`) and the user
   must have confirmed visually it's the thing they intend to print.
2. Ask explicitly: *"Send `<name>.stl` to printer `<alias>` and start
   print?"*
3. Proceed **only** on an affirmative reply in the user's next message.
4. If unsure about slicer profile or printer target, ask — don't guess.

`--dry-run` does not need approval; it never talks to a printer or the
cloud.

## Why cloud, not LAN?

Researched in beads st-5zs / st-qxt / st-g7x / st-98m:

- LAN-send works (`bambulabs-api` over FTPS + signed MQTT) but requires
  **LAN-Only Mode** on the printer, which disables **Bambu Handy**.
- Cloud send keeps Handy working. US region is confirmed; only real
  region split is global (`api.bambulab.com`) vs China
  (`api.bambulab.cn`), which are mutually exclusive endpoints.
- Post-Jan-2025 firmware Authorization Control requires cloud
  reachability for third-party print dispatch anyway, LAN or cloud.
- Bambu Studio CLI has no cloud-send flag; Bambu Connect is GUI-only.
  The unofficial [`coelacant1/Bambu-Lab-Cloud-API`] Python library is
  the only headless cloud-send path today.

## Architecture

```
SCAD ─▶ openscad ─▶ STL ─▶ bambu-studio CLI ─▶ 3MF ─▶ cloud upload ─▶ start_cloud_print
                                                        └─── coelacant1/Bambu-Lab-Cloud-API
```

Pieces:

- `scripts/send.py` — CLI entry. Takes one of `--model` (slice from
  SCAD), `--stl` (slice from existing STL), or `--3mf` (skip slicing),
  plus `--printer <alias>`. Emits a single JSON verdict to stdout.
  Exits non-zero on any failure.
- `scripts/login.py` — one-time interactive auth. Walks the user
  through Bambu Cloud email + password + 2FA OTP, persists the bearer
  token to `~/.config/bambu-send/token.json` (chmod 600).
- `scripts/_cloud.py` — thin adapter over the unofficial library.
  Isolates the lib's surface to a small `CloudClient` facade so if the
  upstream API changes (it's marked "Big commit in progress") only
  this file needs updating.
- `requirements.txt` — pinned to the upstream git URL plus `PyYAML`.

## Config

`~/.config/bambu-send/printers.yaml` (not in repo):

```yaml
default_printer: garage-x1c

printers:
  garage-x1c:
    device_id: "01S00A0B1234567"       # "Serial Number" on printer → Settings
    region: global                     # global | china
    profile_set: x1c-pla

profile_sets:
  x1c-pla:
    # Absolute paths to FULL config JSONs exported from Bambu Studio.
    # NOT the partials under resources/profiles/BBL/. See runbook step 3.
    machine:  /home/you/.config/bambu-send/profiles/x1c-machine.json
    process:  /home/you/.config/bambu-send/profiles/0.20mm-standard.json
    filament: /home/you/.config/bambu-send/profiles/bambu-pla-basic.json
```

An example file ships at `.claude/skills/scad-send/printers.example.yaml`.

## Inputs

`python3 .claude/skills/scad-send/scripts/send.py`:

| Flag | Purpose |
|------|---------|
| `--model PATH` | `.scad` source; openscad-exported to STL, then sliced. |
| `--stl PATH` | Pre-exported STL. Slice → 3MF → send. |
| `--3mf PATH` | Pre-sliced 3MF. Upload → send. |
| `--printer ALIAS` | Alias from `printers.yaml`. Default: `default_printer`. |
| `--profile-set NAME` | Override the printer's default profile set. |
| `--config PATH` | Override config path (default `~/.config/bambu-send/printers.yaml`). |
| `--token PATH` | Override token path (default `~/.config/bambu-send/token.json`). |
| `--name NAME` | Basename used for uploaded file. Default: model/STL stem. |
| `--dry-run` | Resolve config + slice (if applicable), but never touch the cloud. |

Exactly one of `--model`, `--stl`, `--3mf` is required.

## Output contract

Single JSON object to stdout. Non-zero exit on any failure.

```json
{
  "verdict": "sent_ok",
  "printer": "garage-x1c",
  "device_id": "01S00A0B1234567",
  "source": {"kind": "stl", "path": "exports/motor_mount.stl"},
  "sliced_3mf": "/tmp/scad-send-xxx/motor_mount.3mf",
  "uploaded_name": "motor_mount.3mf",
  "job_id": "cloud-print-job-identifier",
  "warnings": []
}
```

Verdicts:

- `sent_ok` — sliced (if needed), uploaded, print started.
- `dry_run_ok` — `--dry-run` passed every non-network check. No upload
  happened.
- `config_missing` — `~/.config/bambu-send/printers.yaml` missing /
  malformed, or printer alias not found, or profile JSON missing.
- `token_missing` — token file absent or malformed; live send only,
  never raised under `--dry-run`.
- `slice_failed` — `bambu-studio` CLI exited non-zero or produced no 3MF.
- `upload_failed` — cloud upload rejected (network, auth, file format).
- `start_failed` — upload ok but `start_cloud_print` rejected.
- `lib_missing` — `bambulabs_cloud_api` not installed; points at
  `requirements.txt`.

## Dry-run mode

`--dry-run` short-circuits before any network or cloud library call.
Verifies:

- Config loads, printer alias resolves, profile files exist (when
  slicing is required).
- Input file exists and can be read.
- If `--model` or `--stl`, performs a real slice into a tmp dir and
  checks the 3MF was produced.
- Reports what **would** have been uploaded and started.

Dry-run is safe to run without Bambu Cloud credentials or a printer.
Use it to smoke-test a new profile set or a new printer alias.

## Runbook (first-time setup)

**You only do this once per machine, then every subsequent print is
just `scad-send`.**

### 1. Install dependencies

```bash
# Bambu Studio CLI (official slicer, required for headless slice)
sudo apt install bambu-studio    # or download AppImage from bambulab.com

# Python deps
pip install -r .claude/skills/scad-send/requirements.txt
```

The Bambu-Lab-Cloud-API Python package is **unofficial** and pulled
from a git URL (see `requirements.txt`). It is not on PyPI under that
name — `pip install` against the git URL is expected.

### 2. Authenticate once against Bambu Cloud

```bash
python3 .claude/skills/scad-send/scripts/login.py
```

Prompts for email, password, and (if your account has 2FA) the email
OTP. Persists a bearer token to `~/.config/bambu-send/token.json` with
`chmod 600`.

Notes:

- The token expires (empirically ~7 days, sometimes less). On expiry
  `send.py` emits `upload_failed` / `start_failed` with a 401-style
  error; re-run `login.py` to refresh.
- The token file must be kept out of version control and out of beads
  notes. `~/.config/bambu-send/` is outside the repo by construction.

### 3. Export a slicer profile set from Bambu Studio GUI

The Bambu Studio CLI requires **full** config JSONs, not the partials
shipped under `resources/profiles/BBL/…`. Easiest way to get full
configs:

1. Open Bambu Studio.
2. Pick your printer, your filament, your process (e.g. 0.20mm
   Standard).
3. Save each as a **User Preset** (preset gear icon → "Save as new").
4. Export each user preset to JSON: gear icon → "Export preset".
5. Copy the three files to `~/.config/bambu-send/profiles/` and note
   the paths in `printers.yaml` under a `profile_sets.<name>` entry.

### 4. Bind printer to your cloud account

- Printer touchscreen → Settings → Network → **NOT** LAN-Only Mode
  (LAN-Only disables cloud; see st-98m).
- In Bambu Handy or Bambu Studio, bind the printer to your cloud
  account. Confirm it shows up green/online.
- Grab the **Serial Number** from Settings → About. That is the
  `device_id` in `printers.yaml`.

### 5. Create `printers.yaml`

Copy `.claude/skills/scad-send/printers.example.yaml` to
`~/.config/bambu-send/printers.yaml` and fill in the device_id, region
(`global` unless you're on a Chinese Bambu account), and the three
profile paths from step 3.

### 6. Smoke test

```bash
# Dry-run against an already-exported STL:
python3 .claude/skills/scad-send/scripts/send.py \
  --stl exports/your_model.stl \
  --printer garage-x1c \
  --dry-run
```

Expected: `verdict: dry_run_ok`, a valid `sliced_3mf` path in a tmp
dir, a summary of what would have been uploaded.

### 7. First live send

After dry-run passes:

```bash
python3 .claude/skills/scad-send/scripts/send.py \
  --stl exports/your_model.stl \
  --printer garage-x1c
```

Watch the printer — prep filament, clear the bed, etc. The skill
**only triggers the print start**; it does not babysit the job. Use
Handy / Studio to monitor.

### First-live-test one-liner

```bash
python3 .claude/skills/scad-send/scripts/login.py && \
python3 .claude/skills/scad-send/scripts/send.py \
  --stl exports/cylindrical_holder_slot.stl \
  --printer garage-x1c --dry-run
```

If the dry-run passes, remove `--dry-run` and send for real.

## Failure modes worth knowing

| Symptom | Cause | Fix |
|---------|-------|-----|
| `lib_missing` | Python lib not installed | `pip install -r .../requirements.txt` |
| `config_missing` | Missing `printers.yaml` or alias unknown | Re-run runbook step 5 |
| `token_missing` | No `token.json` for live send | Run `login.py` (runbook step 2) |
| `slice_failed` with "load_filaments" error | Profile JSONs are partials, not full configs | Re-export from Studio user presets (step 3) |
| `upload_failed` with 401 / "token expired" | Stale bearer | Re-run `login.py` |
| `start_failed` with "device offline" | Printer unbound or in LAN-Only Mode | Re-bind; disable LAN-Only |
| `start_failed` with 403 / "authorization" | Jan-2025 Auth Control bit | Ensure firmware is current; printer must be in your cloud account |

## Out of scope (deferred follow-ups)

- **H2S support.** Protocol is almost certainly compatible per st-5zs.
  Smoke test when hardware is available; most likely `printers.yaml`
  just gets a second entry.
- **LAN fallback.** Not wiring this; one path, one code path.
- **Print monitoring.** This skill triggers; Handy/Studio monitor.
- **Profile generation from scratch.** Users bring their own profiles
  from Studio.

## References

- Library: <https://github.com/coelacant1/Bambu-Lab-Cloud-API>
- AUTH doc: <https://github.com/coelacant1/Bambu-Lab-Cloud-API/blob/main/API_AUTHENTICATION.md>
- FILES+PRINTING doc: <https://github.com/coelacant1/Bambu-Lab-Cloud-API/blob/main/API_FILES_PRINTING.md>
- Bambu Studio CLI wiki: <https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage>
- Prior research beads: st-5zs, st-qxt, st-g7x, st-98m
