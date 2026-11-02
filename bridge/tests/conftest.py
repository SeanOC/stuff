"""Fake Bambuddy + fake stuff behind one httpx.MockTransport.

No test may reach http://cubert:8000 or stuff.seanoc.com: the hosts below are
.invalid, and any request the fakes do not route fails the test loudly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from bridge.app import create_app
from bridge.config import Config

STUFF = "https://stuff.invalid"
BAMBUDDY = "http://bambuddy.invalid:8000"
API_KEY = "test-key-not-a-secret"
LOGIN = "sean@example.com"

# Method + full path allowlist: an added read must never enable queue controls.
ALLOWED = {
    "GET": re.compile(
        r"/api/v1/(printers/|printers/\d+/(status|camera/plate-detection/status|"
        r"slots/\d+/\d+/spool-defaults)|slicer/preset-values|slicer/presets|"
        r"cloud/(builtin-filaments|filament-id-map)|slicer-pipelines/|library/folders|"
        r"pipeline-runs(/\d+)?|slice-jobs/\d+|queue/|queue/\d+|queue/batches/\d+)"
    ),
    "POST": re.compile(
        r"/api/v1/(library/folders|library/files|library/files/\d+/slice|"
        r"slicer-pipelines/\d+/(check-eligibility|run)|queue/)"
    ),
    "PUT": re.compile(r"/api/v1/library/files/\d+"),
}


def spool_fixtures():
    return json.loads((Path(__file__).parent / "fixtures/spools.json").read_text())


@dataclass
class Fake:
    calls: list[httpx.Request] = field(default_factory=list)
    printers: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {
                "id": 1,
                "name": "crushinator",
                "model": "H2S",
                "serial_number": "SN1",
                "access_code": "AC1",
                "ip_address": "10.0.0.1",
            },
            {
                "id": 2,
                "name": "joey",
                "model": "Bambu Lab H2C",
                "serial_number": "SN2",
                "access_code": "AC2",
                "ip_address": "10.0.0.2",
            },
        ]
    )
    pipelines: list[dict[str, Any]] = field(
        default_factory=lambda: [
            # Real Bambuddy pipelines carry a cloud printer preset id (opaque).
            {
                "id": 11,
                "name": "stuff-crushinator",
                "printer_preset": {"source": "cloud", "id": "GM037"},
                "process_preset": {"source": "cloud", "id": "GP158"},
                "bed_type": "High Temp Plate",
            },
            {
                "id": 12,
                "name": "stuff-joey",
                "printer_preset": {"source": "cloud", "id": "GM041"},
                "process_preset": {"source": "cloud", "id": "GP252"},
                "bed_type": "Engineering Plate",
            },
        ]
    )
    # Printer id -> status nozzles[].nozzle_diameter ("" = no second nozzle).
    nozzles: dict[int, list[str]] = field(
        default_factory=lambda: {1: ["0.4", ""], 2: ["0.4", "0.4"]}
    )
    # Resolved printer-preset values; None = Bambuddy 1.2.5.7's answer for
    # slot=printer (400, process only).
    preset_values: dict[str, Any] | None = None
    folders: list[dict[str, Any]] = field(default_factory=list)
    files: dict[int, dict[str, Any]] = field(default_factory=dict)
    runs: dict[int, dict[str, Any]] = field(default_factory=dict)
    multi_colour: set[str] = field(default_factory=lambda: {"label-card"})
    duplicate_of: int | None = None
    eligibility: dict[str, Any] = field(default_factory=lambda: {"ok": True, "issues": []})
    stuff_status: int = 200
    spool_data: dict[str, Any] = field(default_factory=spool_fixtures)
    queue: dict[int, dict[str, Any]] = field(default_factory=dict)
    batches: dict[int, dict[str, Any]] = field(default_factory=dict)
    slice_jobs: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"job_id": 6, "status": "completed", "result": {"library_file_id": 800}}
        ]
    )

    # -- helpers for assertions -------------------------------------------
    def bambuddy_calls(self, method: str, path_re: str) -> list[httpx.Request]:
        return [
            r
            for r in self.calls
            if r.url.host == "bambuddy.invalid"
            and r.method == method
            and re.fullmatch(path_re, r.url.path)
        ]

    def stuff_calls(self) -> list[httpx.Request]:
        return [r for r in self.calls if r.url.host == "stuff.invalid"]

    # -- transport --------------------------------------------------------
    def handle(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        if req.url.host == "stuff.invalid":
            return self._stuff(req)
        assert req.url.host == "bambuddy.invalid", f"unexpected host {req.url}"
        assert req.headers.get("x-api-key") == API_KEY
        allowed = ALLOWED.get(req.method)
        assert allowed and allowed.fullmatch(req.url.path), (
            f"forbidden Bambuddy call {req.method} {req.url.path}"
        )
        if req.method == "POST" and req.url.path.endswith(
            ("/check-eligibility", "/run", "/queue/")
        ):
            assert json.loads(req.content).get("force") in (None, False), "never force"
        return self._bambuddy(req)

    def _stuff(self, req: httpx.Request) -> httpx.Response:
        if self.stuff_status != 200:
            return httpx.Response(self.stuff_status, json={"error": "stuff exploded"})
        path, q = req.url.path, req.url.params
        if m := re.fullmatch(r"/api/bd-asset/([^/]+)/([^/]+)", path):
            slug = m.group(1)
        elif path == "/api/bd-render":
            slug = json.loads(req.content)["slug"]
        elif path == "/api/export":
            model = json.loads(req.content)["model"]
            if not re.fullmatch(r"models/[A-Za-z0-9._/-]+\.scad", model):
                return httpx.Response(403, json={"error": "model path not allowed"})
            return httpx.Response(
                200, content=b"solid scad", headers={"content-type": "application/sla"}
            )
        else:
            raise AssertionError(f"unrouted stuff call {req.method} {path}")
        if q.get("format") == "3mf":
            if slug not in self.multi_colour:
                return httpx.Response(
                    400, json={"error": f"{slug} is not a multi-colour model; 3mf is not available"}
                )
            assert q.get("profile") == "bambu-h2c-0.4"
            return httpx.Response(200, content=b"PK3mf")
        assert q.get("format") == "stl"
        return httpx.Response(200, content=b"solid bd")

    def _bambuddy(self, req: httpx.Request) -> httpx.Response:
        m, path = req.method, req.url.path
        if (m, path) == ("GET", "/api/v1/printers/"):
            return httpx.Response(200, json=self.printers)
        if mm := re.fullmatch(r"/api/v1/printers/(\d+)/camera/plate-detection/status", path):
            return httpx.Response(200, json={"available": True, "calibrated": mm.group(1) == "2"})
        if mm := re.fullmatch(r"/api/v1/printers/(\d+)/status", path):
            nozzles = [
                {"nozzle_type": "hardened_steel", "nozzle_diameter": d}
                for d in self.nozzles.get(int(mm.group(1)), [])
            ]
            return httpx.Response(
                200,
                json={
                    "state": "IDLE",
                    "connected": True,
                    "nozzles": nozzles,
                    **self.spool_data["statuses"][mm.group(1)],
                },
            )
        if (m, path) == ("GET", "/api/v1/slicer/presets"):
            return httpx.Response(200, json=self.spool_data["presets"])
        if (m, path) == ("GET", "/api/v1/cloud/builtin-filaments"):
            return httpx.Response(200, json=self.spool_data["builtin"])
        if (m, path) == ("GET", "/api/v1/cloud/filament-id-map"):
            return httpx.Response(200, json=self.spool_data["custom"])
        if mm := re.fullmatch(r"/api/v1/printers/(\d+)/slots/(\d+)/(\d+)/spool-defaults", path):
            return httpx.Response(
                200, json=self.spool_data["defaults"].get("/".join(mm.groups()), {})
            )
        if m == "POST" and re.fullmatch(r"/api/v1/library/files/\d+/slice", path):
            return httpx.Response(
                202, json={"job_id": 6, "status": "pending", "status_url": "/api/v1/slice-jobs/6"}
            )
        if (m, path) == ("GET", "/api/v1/slice-jobs/6"):
            job = self.slice_jobs[0]
            if len(self.slice_jobs) > 1:
                self.slice_jobs.pop(0)
            return httpx.Response(200, json=job)
        if (m, path) == ("GET", "/api/v1/queue/"):
            pid = int(req.url.params["printer_id"])
            return httpx.Response(
                200, json=[r for r in self.queue.values() if r["printer_id"] == pid]
            )
        if (m, path) == ("POST", "/api/v1/queue/"):
            body = json.loads(req.content)
            qid = 1000 + len(self.queue)
            row = {
                "id": qid,
                "status": "pending",
                "error_message": None,
                "printer_id": body["printer_id"],
                "library_file_id": body["library_file_id"],
                "library_file_name": "holder-bench-width-saddle-width_clearance1.gcode.3mf",
                "ams_mapping": body["ams_mapping"],
                "batch_id": 2000 if body["quantity"] > 1 else None,
            }
            for i in range(body["quantity"]):
                self.queue[qid + i] = {**row, "id": qid + i}
            if row["batch_id"]:
                self.batches[2000] = {
                    "id": 2000,
                    "quantity": body["quantity"],
                    "status": "opaque",
                    "pending_count": body["quantity"],
                    "printing_count": 0,
                    "completed_count": 0,
                    "failed_count": 0,
                    "cancelled_count": 0,
                    "skipped_count": 0,
                    "library_file_id": 800,
                }
            return httpx.Response(200, json=row)
        if mm := re.fullmatch(r"/api/v1/queue/(batches/)?(\d+)", path):
            row = (self.batches if mm[1] else self.queue).get(int(mm[2]))
            return (
                httpx.Response(200, json=row)
                if row
                else httpx.Response(404, json={"detail": "not found"})
            )
        if (m, path) == ("GET", "/api/v1/slicer/preset-values"):
            if self.preset_values is None:
                return httpx.Response(400, json={"detail": "Only the 'process' slot is supported"})
            return httpx.Response(
                200, json={"resolved": True, "values": self.preset_values, "reason": "ok"}
            )
        if (m, path) == ("GET", "/api/v1/slicer-pipelines/"):
            return httpx.Response(200, json={"pipelines": self.pipelines})
        if (m, path) == ("GET", "/api/v1/library/folders"):
            return httpx.Response(200, json=self._tree(None))
        if (m, path) == ("POST", "/api/v1/library/folders"):
            body = json.loads(req.content)
            folder = {
                "id": 100 + len(self.folders),
                "name": body["name"],
                "parent_id": body.get("parent_id"),
            }
            self.folders.append(folder)
            return httpx.Response(200, json=folder)
        if (m, path) == ("POST", "/api/v1/library/files"):
            fid = 500 + len(self.files)
            self.files[fid] = {
                "folder_id": int(req.url.params["folder_id"]),
                "content": req.content,
            }
            return httpx.Response(
                200,
                json={
                    "id": fid,
                    "filename": "x",
                    "file_type": "stl",
                    "file_size": 1,
                    "thumbnail_path": None,
                    "duplicate_of": self.duplicate_of,
                },
            )
        if m == "PUT" and (mm := re.fullmatch(r"/api/v1/library/files/(\d+)", path)):
            self.files.setdefault(int(mm.group(1)), {}).update(json.loads(req.content))
            return httpx.Response(200, json={"id": int(mm.group(1))})
        if (m, path) == ("GET", "/api/v1/pipeline-runs"):
            pid = int(req.url.params["pipeline_id"])
            return httpx.Response(
                200, json={"runs": [r for r in self.runs.values() if r["pipeline_id"] == pid]}
            )
        if mm := re.fullmatch(r"/api/v1/slicer-pipelines/(\d+)/check-eligibility", path):
            return httpx.Response(200, json=self.eligibility)
        if mm := re.fullmatch(r"/api/v1/slicer-pipelines/(\d+)/run", path):
            body = json.loads(req.content)
            rid = 900 + len(self.runs)
            self.runs[rid] = {
                "id": rid,
                "pipeline_id": int(mm.group(1)),
                "status": "queued",
                "source_library_file_id": body["source_library_file_id"],
                "copies": body["copies"],
                "copies_completed": 0,
                "copies_failed": 0,
                "error_message": None,
                "sliced_library_file_id": None,
                "jobs": [],
            }
            return httpx.Response(202, json=self.runs[rid])
        if mm := re.fullmatch(r"/api/v1/pipeline-runs/(\d+)", path):
            run = self.runs.get(int(mm.group(1)))
            if run is None:
                return httpx.Response(404, json={"detail": "Pipeline run not found"})
            return httpx.Response(200, json=run)
        raise AssertionError(f"unrouted Bambuddy call {m} {path}")

    def _tree(self, parent_id: int | None) -> list[dict[str, Any]]:
        return [
            {**f, "children": self._tree(f["id"])}
            for f in self.folders
            if f["parent_id"] == parent_id
        ]


@pytest.fixture
def config() -> Config:
    return Config(
        stuff_url=STUFF,
        bambuddy_url=BAMBUDDY,
        bambuddy_api_key=API_KEY,
        pipelines={1: "stuff-crushinator", 2: "stuff-joey"},
        trusted_login=LOGIN,
    )


@pytest.fixture
def fake() -> Fake:
    return Fake()


@pytest.fixture
def client(config: Config, fake: Fake):
    # Late-bound so a test may swap fake.handle to override one route.
    app = create_app(config, transport=httpx.MockTransport(lambda req: fake.handle(req)))
    with TestClient(app, headers={"Tailscale-User-Login": LOGIN}) as c:
        yield c
