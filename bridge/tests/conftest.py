"""Fake Bambuddy + fake stuff behind one httpx.MockTransport.

No test may reach http://cubert:8000 or stuff.seanoc.com: the hosts below are
.invalid, and any request the fakes do not route fails the test loudly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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

# Endpoints the bridge must never call (dispatch only through pipeline runs).
FORBIDDEN = re.compile(
    r"^/api/v1/(queue|library/files/\d+/print|library/files/add-to-queue|webhook|printers/\d+/"
    r"(?!status$|camera/plate-detection/status$))"
)


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
            {"id": 11, "name": "stuff-crushinator"},
            {"id": 12, "name": "stuff-joey"},
        ]
    )
    folders: list[dict[str, Any]] = field(default_factory=list)
    files: dict[int, dict[str, Any]] = field(default_factory=dict)
    runs: dict[int, dict[str, Any]] = field(default_factory=dict)
    multi_colour: set[str] = field(default_factory=lambda: {"label-card"})
    duplicate_of: int | None = None
    eligibility: dict[str, Any] = field(default_factory=lambda: {"ok": True, "issues": []})
    stuff_status: int = 200

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
        assert not FORBIDDEN.match(req.url.path), f"forbidden Bambuddy call {req.url.path}"
        if req.method == "POST" and req.url.path.endswith(("/check-eligibility", "/run")):
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
            return httpx.Response(200, json={"state": "IDLE", "connected": True})
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
