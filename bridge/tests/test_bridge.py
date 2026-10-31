from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from bridge.__main__ import build_parser, main, run_print
from bridge.app import create_app
from bridge.config import ConfigError, load_config, parse_pipelines
from bridge.core import params_sha12

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
        },
        {
            "id": 2,
            "name": "joey",
            "model": "Bambu Lab H2C",
            "state": "IDLE",
            "plate_detection_calibrated": True,
            "pipeline": "stuff-joey",
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
