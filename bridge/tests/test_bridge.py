from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from bridge.__main__ import build_parser, main, run_print
from bridge.app import create_app
from bridge.config import ConfigError, load_config, parse_pipelines
from bridge.core import name_nozzle, params_sha12

from .conftest import API_KEY, BAMBUDDY, LOGIN, STUFF

BD_PRESET = {
    "source": "bd",
    "slug": "holder-bench-width-saddle",
    "preset": "width_clearance1",
    "printer_id": 1,
}


def test_health(client):
    assert client.get("/health").json() == {"ok": True, "bambuddy_reachable": True}


def test_printers_never_forward_secrets(client):
    body = client.get("/printers").json()
    assert body == [
        {
            "id": 1,
            "name": "crushinator",
            "model": "H2S",
            "state": "IDLE",
            "plate_detection_calibrated": False,
            "pipeline": "stuff-crushinator",
            "nozzle_mm": [0.4],
        },
        {
            "id": 2,
            "name": "joey",
            "model": "Bambu Lab H2C",
            "state": "IDLE",
            "plate_detection_calibrated": True,
            "pipeline": "stuff-joey",
            "nozzle_mm": [0.4, 0.4],
        },
    ]
    raw = json.dumps(body)
    for secret in ("AC1", "SN1", "access_code", "serial", API_KEY):
        assert secret not in raw


def test_print_bd_preset_happy_path(client, fake):
    r = client.post("/print", json={**BD_PRESET, "copies": 2})
    assert r.status_code == 202
    body = r.json()
    run_id = body["run_id"]
    assert body == {"library_file_id": 500, "run_id": run_id, "status_url": f"/runs/{run_id}"}

    (geo,) = fake.stuff_calls()
    assert geo.method == "GET"
    assert geo.url.path == "/api/bd-asset/holder-bench-width-saddle/width_clearance1"
    assert dict(geo.url.params) == {"format": "stl"}  # printer 1 is not an H2C

    # stuff/<slug> folder created on first use, file uploaded into it.
    assert [(f["name"], f["parent_id"]) for f in fake.folders] == [
        ("stuff", None),
        ("holder-bench-width-saddle", 100),
    ]
    (upload,) = fake.bambuddy_calls("POST", "/api/v1/library/files")
    assert upload.url.params["folder_id"] == "101"
    assert b'filename="holder-bench-width-saddle-width_clearance1.stl"' in upload.content
    meta = fake.files[500]
    assert meta["external_url"] == (
        f"{STUFF}/models/holder-bench-width-saddle?preset=width_clearance1"
    )
    assert meta["notes"] == "{}"

    assert fake.runs[run_id]["pipeline_id"] == 11
    assert fake.runs[run_id]["copies"] == 2
    assert fake.bambuddy_calls("POST", r"/api/v1/slicer-pipelines/11/check-eligibility")


def test_print_reuses_existing_folder(client, fake):
    client.post("/print", json=BD_PRESET)
    client.post("/print", json={**BD_PRESET, "preset": "other"})
    assert len(fake.folders) == 2
    assert len(fake.bambuddy_calls("POST", "/api/v1/library/folders")) == 2


def test_print_bd_params_h2c_multicolour_gets_3mf(client, fake):
    params = {"text": "Hi", "size": 12}
    r = client.post(
        "/print", json={"source": "bd", "slug": "label-card", "params": params, "printer_id": 2}
    )
    assert r.status_code == 202, r.text
    (geo,) = fake.stuff_calls()
    assert (geo.method, geo.url.path) == ("POST", "/api/bd-render")
    assert dict(geo.url.params) == {"format": "3mf", "profile": "bambu-h2c-0.4"}
    assert json.loads(geo.content) == {"slug": "label-card", "params": params}
    (upload,) = fake.bambuddy_calls("POST", "/api/v1/library/files")
    assert f'filename="label-card-{params_sha12(params)}.3mf"'.encode() in upload.content
    meta = fake.files[500]
    assert meta["notes"] == '{"size":12,"text":"Hi"}'
    assert meta["external_url"] == f"{STUFF}/models/label-card?text=Hi&size=12"
    assert fake.runs[r.json()["run_id"]]["pipeline_id"] == 12


def test_print_bd_h2c_single_colour_falls_back_to_stl(client, fake):
    r = client.post("/print", json={**BD_PRESET, "printer_id": 2})
    assert r.status_code == 202
    first, second = fake.stuff_calls()
    assert first.url.params["format"] == "3mf"
    assert dict(second.url.params) == {"format": "stl"}


def test_print_scad_happy_path(client, fake):
    r = client.post(
        "/print",
        json={
            "source": "scad",
            "model": "models/opengrid_bin.scad",
            "params": {"width_units": 2},
            "printer_id": 1,
        },
    )
    assert r.status_code == 202, r.text
    (geo,) = fake.stuff_calls()
    assert (geo.method, geo.url.path) == ("POST", "/api/export")
    assert json.loads(geo.content) == {
        "model": "models/opengrid_bin.scad",
        "params": {"width_units": 2},
    }
    assert [f["name"] for f in fake.folders] == ["stuff", "opengrid-bin"]
    assert fake.files[500]["external_url"] == f"{STUFF}/models/opengrid-bin?width_units=2"


def test_print_scad_bare_stem_becomes_model_path(client, fake):
    r = client.post("/print", json={"source": "scad", "model": "opengrid_bin", "printer_id": 1})
    assert r.status_code == 202, r.text
    assert json.loads(fake.stuff_calls()[0].content)["model"] == "models/opengrid_bin.scad"


def test_print_duplicate_reuses_library_file(client, fake):
    fake.duplicate_of = 42
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 202
    assert r.json()["library_file_id"] == 42
    assert fake.bambuddy_calls("PUT", "/api/v1/library/files/42")
    assert fake.runs[r.json()["run_id"]]["source_library_file_id"] == 42


def test_print_active_run_for_same_file_is_409(client, fake):
    fake.duplicate_of = 42
    first = client.post("/print", json=BD_PRESET).json()
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 409
    assert r.json()["run_id"] == first["run_id"]
    assert len(fake.runs) == 1
    # Once the first run is terminal the same file prints again.
    fake.runs[first["run_id"]]["status"] = "completed"
    assert client.post("/print", json=BD_PRESET).status_code == 202


def test_print_eligibility_issues_are_409_verbatim_and_never_forced(client, fake):
    report = {
        "ok": False,
        "target_kind": "specific_printer",
        "target_printer_id": 1,
        "issues": [
            {"kind": "filament_type_mismatch", "slot_index": 0, "expected": "PLA", "actual": "PETG"}
        ],
        "printer_reports": [],
    }
    fake.eligibility = report
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 409
    assert r.json()["report"] == report
    assert not fake.runs
    assert not fake.bambuddy_calls("POST", r"/api/v1/slicer-pipelines/\d+/run")


def test_print_ok_report_with_issues_is_still_409(client, fake):
    fake.eligibility = {"ok": True, "issues": [{"kind": "filament_unverified"}]}
    assert client.post("/print", json=BD_PRESET).status_code == 409
    assert not fake.runs


@pytest.mark.parametrize(
    "headers",
    [{}, {"Tailscale-User-Login": "someone@else.com"}, {"Tailscale-User-Login": LOGIN + "x"}],
)
def test_print_without_trusted_header_is_403(client, fake, headers):
    client.headers.pop("Tailscale-User-Login")
    r = client.post("/print", json=BD_PRESET, headers=headers)
    assert r.status_code == 403
    assert not fake.calls


def test_print_403_precedes_body_validation(client, fake):
    client.headers.pop("Tailscale-User-Login")
    assert client.post("/print", json={"nonsense": True}).status_code == 403


def test_trusted_header_is_case_insensitive(client):
    r = client.post("/print", json=BD_PRESET, headers={"Tailscale-User-Login": LOGIN.upper()})
    assert r.status_code == 202


def test_stuff_failure_is_502_with_upstream_message(client, fake):
    fake.stuff_status = 404
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 502
    assert r.json()["upstream"] == "stuff exploded"
    assert not fake.bambuddy_calls("POST", "/api/v1/library/files")


def test_unknown_printer_is_404_before_geometry(client, fake):
    r = client.post("/print", json={**BD_PRESET, "printer_id": 7})
    assert r.status_code == 404
    assert not fake.stuff_calls()


def test_printer_without_pipeline_is_409(client, fake):
    fake.printers.append({"id": 3, "name": "spare", "model": "A1"})
    r = client.post("/print", json={**BD_PRESET, "printer_id": 3})
    assert r.status_code == 409
    assert not fake.stuff_calls()


def test_missing_named_pipeline_is_409(client, fake):
    fake.pipelines.pop()
    assert client.post("/print", json={**BD_PRESET, "printer_id": 2}).status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"source": "bd", "printer_id": 1},
        {"source": "bd", "slug": "x", "preset": "p", "params": {"a": 1}, "printer_id": 1},
        {"source": "scad", "printer_id": 1},
        {"source": "scad", "model": "m", "preset": "p", "printer_id": 1},
    ],
)
def test_print_bad_body_is_400(client, fake, body):
    assert client.post("/print", json=body).status_code == 400
    assert not fake.calls


def test_print_zero_copies_rejected(client):
    assert client.post("/print", json={**BD_PRESET, "copies": 0}).status_code == 422


def test_runs_reduces_pipeline_run(client, fake):
    run_id = client.post("/print", json=BD_PRESET).json()["run_id"]
    fake.runs[run_id].update(
        status="in_progress",
        sliced_library_file_id=77,
        jobs=[
            {
                "id": 1,
                "pipeline_run_id": run_id,
                "copy_index": 0,
                "assigned_printer_id": 1,
                "assigned_printer_name": "crushinator",
                "queue_entry_id": 33,
                "status": "printing",
            }
        ],
    )
    assert client.get(f"/runs/{run_id}").json() == {
        "status": "in_progress",
        "copies": 1,
        "copies_completed": 0,
        "copies_failed": 0,
        "error_message": None,
        "sliced_library_file_id": 77,
        "jobs": [{"queue_item_id": 33, "status": "printing", "printer_id": 1}],
    }


def test_runs_unknown_is_404(client):
    assert client.get("/runs/12345").status_code == 404


def test_cors_allows_exactly_the_origin(client):
    pre = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    ok = client.options("/print", headers={"Origin": "https://stuff.seanoc.com", **pre})
    assert ok.headers["access-control-allow-origin"] == "https://stuff.seanoc.com"
    bad = client.options("/print", headers={"Origin": "https://evil.example", **pre})
    assert "access-control-allow-origin" not in bad.headers


# -- config / startup ------------------------------------------------------

ENV = {
    "STUFF_URL": STUFF,
    "BAMBUDDY_URL": BAMBUDDY,
    "BAMBUDDY_API_KEY": API_KEY,
    "PIPELINES": "2=stuff-joey,1=stuff-crushinator",
    "TRUSTED_LOGIN": LOGIN,
}


def test_load_config_from_env():
    cfg = load_config(ENV)
    assert cfg.pipelines == {2: "stuff-joey", 1: "stuff-crushinator"}
    assert cfg.allowed_origin == "https://stuff.seanoc.com"
    assert API_KEY not in repr(cfg)


@pytest.mark.parametrize("missing", sorted(ENV))
def test_startup_refused_without_required_env(monkeypatch, missing):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv(missing)
    with pytest.raises(ConfigError, match=missing):
        create_app()


def test_serve_exits_nonzero_without_key(monkeypatch, capsys):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("BAMBUDDY_API_KEY")
    assert main(["serve"]) == 2
    err = capsys.readouterr().err
    assert "BAMBUDDY_API_KEY" in err and "refusing to start" in err


def test_parse_pipelines_rejects_garbage():
    with pytest.raises(ConfigError):
        parse_pipelines("joey")


# -- CLI -------------------------------------------------------------------


def test_cli_print_polls_until_terminal(monkeypatch, fake, capsys):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    real_handle = fake.handle
    polls = {"n": 0}

    def handle(req: httpx.Request) -> httpx.Response:
        if req.method == "GET" and req.url.path.startswith("/api/v1/pipeline-runs/"):
            polls["n"] += 1
            (run,) = fake.runs.values()
            run["status"] = "in_progress" if polls["n"] < 3 else "completed"
        return real_handle(req)

    args = build_parser().parse_args(
        [
            "print",
            "--source",
            "bd",
            "--slug",
            "holder-bench-width-saddle",
            "--preset",
            "width_clearance1",
            "--printer-id",
            "1",
            "--copies",
            "1",
            "--poll-interval",
            "0",
        ]
    )
    assert asyncio.run(run_print(args, transport=httpx.MockTransport(handle))) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    accepted = json.loads("\n".join(lines[:5]))
    assert accepted["status_url"] == f"/runs/{accepted['run_id']}"
    assert [json.loads(line)["status"] for line in lines[5:]] == ["in_progress", "completed"]


def test_cli_param_parsing():
    args = build_parser().parse_args(
        [
            "print",
            "--source",
            "bd",
            "--slug",
            "s",
            "--printer-id",
            "1",
            "--param",
            "size=12",
            "--param",
            "text=Hi",
            "--param",
            "flag=true",
        ]
    )
    assert dict(args.param) == {"size": 12, "text": "Hi", "flag": True}


# -- pst-617aw hardening ---------------------------------------------------

CLI_PRINT = [
    "print",
    "--source",
    "bd",
    "--slug",
    "holder-bench-width-saddle",
    "--preset",
    "width_clearance1",
    "--printer-id",
    "1",
    "--poll-interval",
    "0",
]


def _cli(monkeypatch, fake, handle, *extra: str) -> int:
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    args = build_parser().parse_args([*CLI_PRINT, *extra])
    return asyncio.run(run_print(args, transport=httpx.MockTransport(handle)))


def _poll_hook(fake, on_poll):
    """Wrap fake.handle; on_poll(n) runs on the n-th GET of a pipeline run and
    may return a Response (or raise) to replace the fake's answer."""
    polls = {"n": 0}

    def handle(req: httpx.Request) -> httpx.Response:
        if req.method == "GET" and req.url.path.startswith("/api/v1/pipeline-runs/"):
            polls["n"] += 1
            if (resp := on_poll(polls["n"])) is not None:
                fake.calls.append(req)
                return resp
        return fake.handle(req)

    return handle


@pytest.mark.parametrize(
    "upstream",
    [
        lambda n: httpx.Response(500, json={"detail": "db locked"}) if n == 2 else None,
        lambda n: httpx.Response(200, text="<html>proxy</html>") if n == 2 else None,
    ],
    ids=["bambuddy-500", "non-json-200"],
)
def test_cli_poll_bambuddy_error_exits_4_with_message(monkeypatch, fake, capsys, upstream):
    def on_poll(n):
        (run,) = fake.runs.values()
        run["status"] = "in_progress"
        return upstream(n)

    assert _cli(monkeypatch, fake, _poll_hook(fake, on_poll)) == 4
    out, err = capsys.readouterr()
    assert "Traceback" not in err
    report = json.loads(err)
    assert report["error"].startswith("polling run 900 failed")
    assert report["cause"]["error"].startswith("Bambuddy GET /api/v1/pipeline-runs/900")
    assert report["last"]["status"] == "in_progress"


def test_cli_poll_transport_error_exits_4(monkeypatch, fake, capsys):
    def on_poll(n):
        raise httpx.ConnectError("boom")

    assert _cli(monkeypatch, fake, _poll_hook(fake, on_poll)) == 4
    report = json.loads(capsys.readouterr().err)
    assert report["cause"] == {"error": "Bambuddy unreachable: ConnectError"}
    assert report["last"] is None


def test_cli_poll_catches_raw_httpx_error(monkeypatch, fake, capsys):
    """Belt and braces: an httpx error that escapes Bridge.run still exits 4."""

    async def raising_run(self, run_id):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr("bridge.__main__.Bridge.run", raising_run)
    assert _cli(monkeypatch, fake, fake.handle) == 4
    assert json.loads(capsys.readouterr().err)["cause"] == {"error": "ReadTimeout"}


def test_cli_max_wait_prints_last_status_and_exits_3(monkeypatch, fake, capsys):
    def on_poll(n):
        (run,) = fake.runs.values()
        run["status"] = "slicing" if n == 1 else "in_progress"

    assert _cli(monkeypatch, fake, _poll_hook(fake, on_poll), "--max-wait", "0") == 3
    out, err = capsys.readouterr()
    report = json.loads(err)
    assert report["error"] == "--max-wait 0s elapsed"
    assert report["last"]["status"] == "slicing"
    assert json.loads(out.strip().splitlines()[-1])["status"] == "slicing"


def test_cli_max_wait_not_hit_when_run_finishes(monkeypatch, fake, capsys):
    def on_poll(n):
        (run,) = fake.runs.values()
        run["status"] = "in_progress" if n < 3 else "failed"

    assert _cli(monkeypatch, fake, _poll_hook(fake, on_poll), "--max-wait", "60") == 1
    assert capsys.readouterr().err == ""


def test_cli_max_wait_defaults_to_none():
    assert build_parser().parse_args(CLI_PRINT).max_wait is None


@pytest.mark.parametrize(
    "model", ["opengrid_bin", "models/opengrid_bin", "models/opengrid_bin.scad"]
)
def test_scad_model_forms_normalise_to_one_path(client, fake, model):
    r = client.post("/print", json={"source": "scad", "model": model, "printer_id": 1})
    assert r.status_code == 202, r.text
    assert json.loads(fake.stuff_calls()[0].content)["model"] == "models/opengrid_bin.scad"
    assert [f["name"] for f in fake.folders] == ["stuff", "opengrid-bin"]


def _bambuddy_override(fake, method, path, response):
    real = fake.handle

    def handle(req: httpx.Request) -> httpx.Response:
        if req.method == method and req.url.path == path:
            fake.calls.append(req)
            return response
        return real(req)

    fake.handle = handle


@pytest.mark.parametrize(
    "method,path,response,why",
    [
        (
            "GET",
            "/api/v1/slicer-pipelines/",
            httpx.Response(200, text="<html>" + "x" * 400),
            "response is not JSON",
        ),
        (
            "GET",
            "/api/v1/library/folders",
            httpx.Response(200, json={"id": 1, "name": "stuff"}),
            "expected a list of folders",
        ),
        (
            "GET",
            "/api/v1/printers/",
            httpx.Response(200, json=["not", "objects"]),
            "expected a list of printers",
        ),
        (
            "POST",
            "/api/v1/library/files",
            httpx.Response(200, json={"filename": "x"}),
            "response has no id",
        ),
        (
            "POST",
            "/api/v1/slicer-pipelines/11/check-eligibility",
            httpx.Response(200, json=[{"ok": True}]),
            "expected a JSON object",
        ),
        (
            "POST",
            "/api/v1/slicer-pipelines/11/run",
            httpx.Response(202, json={"status": "queued"}),
            "response has no id",
        ),
    ],
    ids=[
        "non-json",
        "folders-dict",
        "printers-scalars",
        "upload-no-id",
        "report-list",
        "run-no-id",
    ],
)
def test_misshaped_bambuddy_body_is_502_not_traceback(client, fake, method, path, response, why):
    _bambuddy_override(fake, method, path, response)
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 502, r.text
    body = r.json()
    assert body["error"] == f"Bambuddy {method} {path} -> HTTP {response.status_code}: {why}"
    assert body["upstream"] == response.text[:200]
    assert len(body["upstream"]) <= 200


def test_bambuddy_listings_accept_bare_list_or_wrapped(client, fake):
    """List-or-dict: the fake wraps pipelines/runs and bares printers/folders;
    the flipped shapes must work too."""
    pipelines = httpx.Response(200, json=fake.pipelines)
    printers = httpx.Response(200, json={"printers": fake.printers})
    _bambuddy_override(fake, "GET", "/api/v1/slicer-pipelines/", pipelines)
    _bambuddy_override(fake, "GET", "/api/v1/printers/", printers)
    assert client.post("/print", json=BD_PRESET).status_code == 202


def test_run_non_json_is_502(client, fake):
    _bambuddy_override(fake, "GET", "/api/v1/pipeline-runs/7", httpx.Response(200, text="oops"))
    r = client.get("/runs/7")
    assert r.status_code == 502
    assert r.json() == {
        "error": "Bambuddy GET /api/v1/pipeline-runs/7 -> HTTP 200: response is not JSON",
        "upstream": "oops",
    }


def test_printers_probe_non_json_is_none(client, fake):
    _bambuddy_override(fake, "GET", "/api/v1/printers/1/status", httpx.Response(200, text="?"))
    r = client.get("/printers")
    assert r.status_code == 200
    assert [p["state"] for p in r.json()] == [None, "IDLE"]


# -- nozzle check (pst-0y0w4) ----------------------------------------------

INCIDENT_PIPELINE = "Crushinator - PCTG - .4"


def _name_pipeline(fake, config, printer_id, name):
    """Point printer_id at a pipeline called name, as Bambuddy lists it."""
    pid = {1: 11, 2: 12}[printer_id]
    pipelines = [{**p, "name": name} if p["id"] == pid else p for p in fake.pipelines]
    _bambuddy_override(
        fake, "GET", "/api/v1/slicer-pipelines/", httpx.Response(200, json={"pipelines": pipelines})
    )
    config.pipelines[printer_id] = name


def _no_upload(fake):
    assert not fake.stuff_calls()
    assert not fake.bambuddy_calls("POST", r"/api/v1/library/(files|folders)")
    assert not fake.bambuddy_calls("POST", r"/api/v1/slicer-pipelines/\d+/.*")


def test_nozzle_mismatch_is_409_before_any_fetch_or_upload(client, fake, config):
    """The 2026-10-31 incident: a 0.6 nozzle on a pipeline slicing for .4."""
    fake.nozzles[1] = ["0.6", ""]
    _name_pipeline(fake, config, 1, INCIDENT_PIPELINE)
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 409
    assert r.json() == {"error": "nozzle mismatch", "installed": [0.6], "pipeline": 0.4}
    _no_upload(fake)


def test_cli_nozzle_mismatch_exits_1_with_both_values(monkeypatch, fake, capsys):
    fake.nozzles[1] = ["0.6", ""]
    fake.pipelines[0]["printer_preset"] = {"source": "standard", "id": "Bambu Lab H2S 0.4 nozzle"}
    assert _cli(monkeypatch, fake, fake.handle) == 1
    err = json.loads(capsys.readouterr().err)
    assert err == {"status": 409, "error": "nozzle mismatch", "installed": [0.6], "pipeline": 0.4}
    _no_upload(fake)


def test_nozzle_match_prints(client, fake, config):
    _name_pipeline(fake, config, 1, INCIDENT_PIPELINE)
    assert client.post("/print", json=BD_PRESET).status_code == 202


def test_nozzle_match_on_second_nozzle_with_first_empty(client, fake, config):
    fake.nozzles[2] = ["", "0.4"]
    _name_pipeline(fake, config, 2, "Joey - PCTG - 0.4mm")
    r = client.post("/print", json={**BD_PRESET, "printer_id": 2})
    assert r.status_code == 202, r.text


def test_nozzle_dual_mismatch_lists_every_installed(client, fake, config):
    fake.nozzles[2] = ["0.6", "0.2"]
    _name_pipeline(fake, config, 2, "Joey - PCTG - .4")
    r = client.post("/print", json={**BD_PRESET, "printer_id": 2})
    assert r.status_code == 409
    assert r.json()["installed"] == [0.6, 0.2]


def test_nozzle_two_token_name_is_unknown_and_proceeds(client, fake, config):
    fake.nozzles[1] = ["0.6"]
    _name_pipeline(fake, config, 1, "PCTG-1.5x0.4")
    assert client.post("/print", json=BD_PRESET).status_code == 202


def test_nozzle_unknown_installed_proceeds(client, fake, config):
    fake.nozzles[1] = ["", "n/a"]
    _name_pipeline(fake, config, 1, INCIDENT_PIPELINE)
    assert client.post("/print", json=BD_PRESET).status_code == 202


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, json={"detail": "Not Found"}),
        httpx.Response(502, text="bad gateway"),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"resolved": False, "values": {}, "reason": "preset_unresolved"}),
    ],
)
def test_nozzle_preset_values_failure_is_unknown_and_proceeds(client, fake, response):
    """No name token and an unreadable preset: unknown, never a 502."""
    fake.nozzles[1] = ["0.6"]
    _bambuddy_override(fake, "GET", "/api/v1/slicer/preset-values", response)
    assert client.post("/print", json=BD_PRESET).status_code == 202
    (q,) = fake.bambuddy_calls("GET", "/api/v1/slicer/preset-values")
    assert dict(q.url.params) == {"source": "cloud", "id": "GM037", "slot": "printer"}


def test_nozzle_from_preset_values_beats_the_name(client, fake, config):
    fake.nozzles[1] = ["0.6"]
    fake.preset_values = {"nozzle_diameter": ["0.4"], "printer_variant": "0.4"}
    _name_pipeline(fake, config, 1, "Crushinator - PCTG - .6")
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 409
    assert r.json() == {"error": "nozzle mismatch", "installed": [0.6], "pipeline": 0.4}
    _no_upload(fake)


def test_nozzle_preset_variant_when_diameters_disagree(client, fake):
    fake.nozzles[1] = ["0.4"]
    fake.preset_values = {"nozzle_diameter": ["0.4", "0.6"], "printer_variant": "0.6"}
    r = client.post("/print", json=BD_PRESET)
    assert r.json() == {"error": "nozzle mismatch", "installed": [0.4], "pipeline": 0.6}


def test_nozzle_standard_preset_name_is_read(client, fake, config):
    fake.nozzles[1] = ["0.6"]
    fake.pipelines[0]["printer_preset"] = {"source": "standard", "id": "Bambu Lab H2S 0.4 nozzle"}
    r = client.post("/print", json=BD_PRESET)
    assert r.status_code == 409
    assert r.json()["pipeline"] == 0.4


def test_printers_nozzle_mm_unknown_is_empty(client, fake):
    fake.nozzles[1] = ["", "x"]
    assert [p["nozzle_mm"] for p in client.get("/printers").json()] == [[], [0.4, 0.4]]


@pytest.mark.parametrize(
    ("name", "mm"),
    [
        ("Crushinator - PCTG - .4", 0.4),
        ("Crushinator - PCTG - 0.4mm", 0.4),
        ("Crushinator PCTG 0.6", 0.6),
        ("bambu-h2c-0.4", 0.4),
        ("PCTG-1.5x0.6", None),
        ("stuff-crushinator", None),
        ("v1.2.3", None),
        (None, None),
    ],
)
def test_name_nozzle_token(name, mm):
    assert name_nozzle(name) == mm
