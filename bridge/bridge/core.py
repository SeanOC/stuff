"""The one code path behind both the HTTP routes and the CLI.

Bambuddy (1.2.5.7) is only ever asked to store a file and to run a slicer
pipeline. Never call POST /api/v1/queue/, /library/files/{id}/print, webhook
start/stop or any printer-control endpoint, and never send force=true:
dispatch happens only through the pipeline run, gated by Bambuddy's own
eligibility check and plate-empty camera check.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from .config import Config

log = logging.getLogger("bridge")

# Printer profile the stuff 3MF routes bake for an H2C (build123d/manifest.json
# printerProfiles). Only multi-colour models have a 3MF at all.
H2C_PROFILE = "bambu-h2c-0.4"
# Exact wording of the 400 both stuff routes return for a single-colour model
# asked for a 3MF (app/api/bd-asset/[slug]/[preset]/route.ts,
# app/api/bd-render/route.ts). Matching it is how the bridge learns a model is
# single-colour without a manifest of its own; any other 400 stays an error.
NOT_MULTI_COLOUR = "is not a multi-colour model"

LIBRARY_ROOT = "stuff"
ACTIVE_RUN_STATES = frozenset({"queued", "slicing", "dispatching", "in_progress"})
TERMINAL_RUN_STATES = frozenset({"completed", "failed", "partial_failure", "cancelled"})

# bd-render and /api/export build geometry on demand; give them minutes.
STUFF_TIMEOUT = httpx.Timeout(30.0, read=300.0)
BAMBUDDY_TIMEOUT = httpx.Timeout(30.0)
# How much of an unparseable/mis-shaped 2xx Bambuddy body a 502 quotes. Tighter
# than _upstream_message's 500: a success-path surprise is usually a proxy's
# HTML page, and its first line or two is all an operator needs.
BODY_EXCERPT = 200


class BridgeError(Exception):
    """An error with the HTTP status and JSON body the caller should see."""

    def __init__(self, status: int, payload: dict[str, Any], upstream_status: int | None = None):
        super().__init__(payload.get("error", status))
        self.status = status
        self.payload = payload
        self.upstream_status = upstream_status


def canonical_params(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


def params_sha12(params: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_params(params).encode()).hexdigest()[:12]


def is_h2c(printer_model: str | None) -> bool:
    # Bambuddy's model string is not pinned anywhere we control, so match
    # loosely ("H2C", "Bambu Lab H2C", "h2c") rather than by equality.
    return "h2c" in (printer_model or "").casefold()


def scad_model_path(model: str) -> str:
    """/api/export only accepts models/<stem>.scad (403 otherwise). Accept x,
    models/x and models/x.scad alike and always send models/x.scad."""
    stem = model.removeprefix("models/").removesuffix(".scad")
    return f"models/{stem}.scad"


def scad_slug(model_path: str) -> str:
    stem = model_path.rsplit("/", 1)[-1].removesuffix(".scad")
    return stem.replace("_", "-")


def _upstream_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:500] or resp.reason_phrase
    if isinstance(body, dict):
        msg = body.get("error") or body.get("detail")
        if msg is not None:
            return msg if isinstance(msg, str) else json.dumps(msg)
    return json.dumps(body)[:500]


def _bad_body(method: str, path: str, resp: httpx.Response, why: str) -> BridgeError:
    return BridgeError(
        502,
        {
            "error": f"Bambuddy {method} {path} -> HTTP {resp.status_code}: {why}",
            "upstream": resp.text[:BODY_EXCERPT],
        },
        upstream_status=resp.status_code,
    )


def _probe(resp: httpx.Response | BaseException, key: str) -> Any:
    if not isinstance(resp, httpx.Response) or not resp.is_success:
        return None
    try:
        body = resp.json()
    except ValueError:
        return None
    return body.get(key) if isinstance(body, dict) else None


class Bridge:
    def __init__(self, config: Config, transport: httpx.AsyncBaseTransport | None = None):
        self.config = config
        self.stuff = httpx.AsyncClient(
            base_url=config.stuff_url, timeout=STUFF_TIMEOUT, transport=transport
        )
        self.bambuddy = httpx.AsyncClient(
            base_url=config.bambuddy_url,
            headers={"X-API-Key": config.bambuddy_api_key},
            timeout=BAMBUDDY_TIMEOUT,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self.stuff.aclose()
        await self.bambuddy.aclose()

    # -- Bambuddy plumbing -------------------------------------------------

    async def _bb(self, method: str, path: str, **kw: Any) -> httpx.Response:
        try:
            resp = await self.bambuddy.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise BridgeError(502, {"error": f"Bambuddy unreachable: {type(e).__name__}"}) from e
        if resp.is_error:
            raise BridgeError(
                502,
                {
                    "error": f"Bambuddy {method} {path} -> HTTP {resp.status_code}",
                    "upstream": _upstream_message(resp),
                },
                upstream_status=resp.status_code,
            )
        return resp

    async def _bb_json(
        self,
        method: str,
        path: str,
        *,
        items: str | None = None,
        need: tuple[str, ...] = (),
        **kw: Any,
    ) -> Any:
        """The one way to read a 2xx Bambuddy body. With items=, a listing:
        either a bare list or {items: [...]}, returned as a list of objects.
        Otherwise an object holding every key in need. Non-JSON or any other
        shape is a BridgeError -> 502 with the upstream status and body excerpt."""
        resp = await self._bb(method, path, **kw)
        try:
            body = resp.json()
        except ValueError:
            raise _bad_body(method, path, resp, "response is not JSON") from None
        if items is not None:
            rows = body.get(items) if isinstance(body, dict) else body
            if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
                raise _bad_body(method, path, resp, f"expected a list of {items}")
            return rows
        if not isinstance(body, dict):
            raise _bad_body(method, path, resp, "expected a JSON object")
        if missing := [k for k in need if k not in body]:
            raise _bad_body(method, path, resp, f"response has no {', '.join(missing)}")
        return body

    async def _printers_raw(self) -> list[dict[str, Any]]:
        return await self._bb_json("GET", "/api/v1/printers/", items="printers")

    async def _pipeline_id(self, name: str) -> int:
        for p in await self._bb_json("GET", "/api/v1/slicer-pipelines/", items="pipelines"):
            if p.get("name") == name:
                return p["id"]
        raise BridgeError(409, {"error": f"Bambuddy has no slicer pipeline named {name!r}"})

    async def _folder_id(self, slug: str) -> int:
        """Folder stuff/<slug>, created on first use."""
        tree = await self._bb_json("GET", "/api/v1/library/folders", items="folders")
        flat: list[dict[str, Any]] = []
        stack = list(tree)
        while stack:
            node = stack.pop()
            flat.append(node)
            children = node.get("children")
            if isinstance(children, list):
                stack.extend(c for c in children if isinstance(c, dict))

        async def ensure(name: str, parent_id: int | None) -> int:
            for f in flat:
                if f.get("name") == name and f.get("parent_id") == parent_id:
                    return f["id"]
            created = await self._bb_json(
                "POST",
                "/api/v1/library/folders",
                need=("id",),
                json={"name": name, "parent_id": parent_id},
            )
            log.info("created library folder %r (id %s)", name, created["id"])
            flat.append(created)
            return created["id"]

        return await ensure(slug, await ensure(LIBRARY_ROOT, None))

    # -- stuff geometry ----------------------------------------------------

    async def _stuff(self, method: str, path: str, **kw: Any) -> httpx.Response:
        try:
            return await self.stuff.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise BridgeError(502, {"error": f"stuff unreachable: {type(e).__name__}"}) from e

    @staticmethod
    def _stuff_failed(resp: httpx.Response, what: str) -> BridgeError:
        return BridgeError(
            502,
            {
                "error": f"stuff {what} -> HTTP {resp.status_code}",
                "upstream": _upstream_message(resp),
            },
        )

    async def _fetch_bd(
        self, slug: str, preset: str | None, params: dict[str, Any], h2c: bool
    ) -> tuple[bytes, str]:
        if preset is not None:
            path = f"/api/bd-asset/{quote(slug, safe='')}/{quote(preset, safe='')}"
            what = f"bd-asset {slug}/{preset}"

            def send(query: dict[str, str]) -> Any:
                return self._stuff("GET", path, params=query)
        else:
            path = "/api/bd-render"
            what = f"bd-render {slug}"

            def send(query: dict[str, str]) -> Any:
                return self._stuff(
                    "POST", path, params=query, json={"slug": slug, "params": params}
                )

        if h2c:
            resp = await send({"format": "3mf", "profile": H2C_PROFILE})
            if resp.is_success:
                log.info("%s: H2C printer, multi-colour model -> 3mf (%s)", what, H2C_PROFILE)
                return resp.content, "3mf"
            if not (resp.status_code == 400 and NOT_MULTI_COLOUR in _upstream_message(resp)):
                raise self._stuff_failed(resp, what)
            log.info("%s: H2C printer, single-colour model -> stl", what)
        else:
            log.info("%s: non-H2C printer -> stl", what)
        resp = await send({"format": "stl"})
        if not resp.is_success:
            raise self._stuff_failed(resp, what)
        return resp.content, "stl"

    async def _fetch_scad(self, model_path: str, params: dict[str, Any]) -> bytes:
        resp = await self._stuff(
            "POST", "/api/export", json={"model": model_path, "params": params}
        )
        if not resp.is_success:
            raise self._stuff_failed(resp, f"export {model_path}")
        return resp.content

    def _page_url(self, slug: str, preset: str | None, params: dict[str, Any]) -> str:
        if preset is not None:
            query = {"preset": preset}
        else:
            query = {k: v if isinstance(v, str) else json.dumps(v) for k, v in params.items()}
        url = f"{self.config.stuff_url}/models/{quote(slug, safe='')}"
        return f"{url}?{urlencode(query)}" if query else url

    # -- public operations -------------------------------------------------

    async def health(self) -> dict[str, Any]:
        try:
            resp = await self.bambuddy.get("/api/v1/printers/")
            reachable = resp.is_success
        except httpx.HTTPError:
            reachable = False
        return {"ok": True, "bambuddy_reachable": reachable}

    async def printers(self) -> list[dict[str, Any]]:
        raw = await self._printers_raw()

        async def one(p: dict[str, Any]) -> dict[str, Any]:
            pid = p["id"]
            plate, status = await asyncio.gather(
                self.bambuddy.get(f"/api/v1/printers/{pid}/camera/plate-detection/status"),
                self.bambuddy.get(f"/api/v1/printers/{pid}/status"),
                return_exceptions=True,
            )
            # Best effort: a failed or mis-shaped probe shows as None, not an error.
            calibrated = _probe(plate, "calibrated")
            state = _probe(status, "state")
            # Built field by field: access_code and serial_number never leave.
            return {
                "id": pid,
                "name": p.get("name"),
                "model": p.get("model"),
                "state": state,
                "plate_detection_calibrated": calibrated,
                "pipeline": self.config.pipelines.get(pid),
            }

        return list(await asyncio.gather(*(one(p) for p in raw)))

    async def start_print(
        self,
        *,
        source: str,
        printer_id: int,
        slug: str | None = None,
        model: str | None = None,
        preset: str | None = None,
        params: dict[str, Any] | None = None,
        copies: int = 1,
    ) -> dict[str, Any]:
        params = params or {}
        if copies < 1:
            raise BridgeError(400, {"error": "copies must be >= 1"})
        if source == "bd":
            if not slug:
                raise BridgeError(400, {"error": "source bd needs slug"})
            if preset is not None and params:
                raise BridgeError(400, {"error": "give preset or params, not both"})
        elif source == "scad":
            if not model:
                raise BridgeError(400, {"error": "source scad needs model"})
            if preset is not None:
                raise BridgeError(400, {"error": "source scad has no presets; use params"})
        else:
            raise BridgeError(400, {"error": f"source must be bd or scad, got {source!r}"})

        # Fail fast on printer + pipeline before building any geometry.
        printer = next((p for p in await self._printers_raw() if p.get("id") == printer_id), None)
        if printer is None:
            raise BridgeError(404, {"error": f"Bambuddy has no printer {printer_id}"})
        pipeline_name = self.config.pipelines.get(printer_id)
        if pipeline_name is None:
            raise BridgeError(
                409, {"error": f"PIPELINES names no pipeline for printer {printer_id}"}
            )
        pipeline_id = await self._pipeline_id(pipeline_name)

        if source == "bd":
            assert slug is not None
            data, ext = await self._fetch_bd(slug, preset, params, is_h2c(printer.get("model")))
        else:
            assert model is not None
            model_path = scad_model_path(model)
            slug = scad_slug(model_path)
            data, ext = await self._fetch_scad(model_path, params), "stl"

        folder_id = await self._folder_id(slug)
        filename = f"{slug}-{preset if preset is not None else params_sha12(params)}.{ext}"
        content_type = "model/3mf" if ext == "3mf" else "model/stl"
        uploaded = await self._bb_json(
            "POST",
            "/api/v1/library/files",
            need=("id",),
            params={"folder_id": folder_id},
            files={"file": (filename, data, content_type)},
        )
        file_id = uploaded.get("duplicate_of") or uploaded["id"]
        if uploaded.get("duplicate_of"):
            log.info("%s duplicates library file %s; reusing it", filename, file_id)
        # Bambuddy's FileUpdate calls the link field external_url (no source_url).
        await self._bb(
            "PUT",
            f"/api/v1/library/files/{file_id}",
            json={
                "external_url": self._page_url(slug, preset, params),
                "notes": canonical_params(params),
            },
        )

        # duplicate_of dedupes the file, not the run: a double-clicked Print
        # would otherwise slice and print the same file twice.
        runs = await self._bb_json(
            "GET",
            "/api/v1/pipeline-runs",
            items="runs",
            params={"pipeline_id": pipeline_id, "limit": 100},
        )
        for run in runs:
            if (
                run.get("source_library_file_id") == file_id
                and run.get("status") in ACTIVE_RUN_STATES
            ):
                raise BridgeError(
                    409,
                    {
                        "error": f"{filename} already has an active run on printer {printer_id}",
                        "run_id": run["id"],
                        "status_url": f"/runs/{run['id']}",
                    },
                )

        report = await self._bb_json(
            "POST",
            f"/api/v1/slicer-pipelines/{pipeline_id}/check-eligibility",
            json={"source_library_file_id": file_id},
        )
        if not report.get("ok") or report.get("issues"):
            raise BridgeError(409, {"error": "pipeline eligibility check failed", "report": report})

        run = await self._bb_json(
            "POST",
            f"/api/v1/slicer-pipelines/{pipeline_id}/run",
            need=("id",),
            json={"source_library_file_id": file_id, "copies": copies},
        )
        log.info("pipeline %r run %s: %s x%d", pipeline_name, run["id"], filename, copies)
        return {
            "library_file_id": file_id,
            "run_id": run["id"],
            "status_url": f"/runs/{run['id']}",
        }

    async def run(self, run_id: int) -> dict[str, Any]:
        try:
            r = await self._bb_json("GET", f"/api/v1/pipeline-runs/{run_id}")
        except BridgeError as e:
            if e.upstream_status == 404:
                raise BridgeError(404, {"error": f"no pipeline run {run_id}"}) from e
            raise
        return {
            "status": r.get("status"),
            "copies": r.get("copies"),
            "copies_completed": r.get("copies_completed"),
            "copies_failed": r.get("copies_failed"),
            "error_message": r.get("error_message"),
            "sliced_library_file_id": r.get("sliced_library_file_id"),
            "jobs": [
                {
                    "queue_item_id": j.get("queue_entry_id"),
                    "status": j.get("status"),
                    "printer_id": j.get("assigned_printer_id"),
                }
                for j in r.get("jobs") or []
                if isinstance(j, dict)
            ],
        }
