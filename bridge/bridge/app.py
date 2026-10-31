"""HTTP surface. Binds 127.0.0.1 only; `tailscale serve` fronts it and injects
Tailscale-User-Login, which is why that header can be trusted at all."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import Config, load_config
from .core import Bridge, BridgeError

LOGIN_HEADER = "Tailscale-User-Login"


class PrintRequest(BaseModel):
    source: Literal["bd", "scad"]
    slug: str | None = None
    model: str | None = None
    preset: str | None = None
    params: dict[str, Any] | None = None
    printer_id: int
    copies: int = Field(default=1, ge=1)


def trusted(request: Request, config: Config) -> bool:
    # Exact match, case-insensitive (logins are email-shaped).
    login = request.headers.get(LOGIN_HEADER, "")
    return login.strip().casefold() == config.trusted_login.casefold()


def create_app(
    config: Config | None = None, transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    """Missing config raises ConfigError here, so the process refuses to start."""
    config = config or load_config()
    bridge = Bridge(config, transport=transport)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await bridge.aclose()

    app = FastAPI(title="stuff print bridge", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.allowed_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    @app.exception_handler(BridgeError)
    async def bridge_error(_: Request, exc: BridgeError) -> JSONResponse:
        return JSONResponse(exc.payload, status_code=exc.status)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return await bridge.health()

    @app.get("/printers")
    async def printers() -> list[dict[str, Any]]:
        return await bridge.printers()

    def require_trusted(request: Request) -> None:
        # A dependency, so the 403 fires before body validation can 422.
        if not trusted(request, config):
            raise BridgeError(403, {"error": f"{LOGIN_HEADER} is not the trusted login"})

    @app.post("/print", status_code=202, dependencies=[Depends(require_trusted)])
    async def start_print(body: PrintRequest) -> dict[str, Any]:
        return await bridge.start_print(**body.model_dump())

    @app.get("/runs/{run_id}")
    async def run(run_id: int) -> dict[str, Any]:
        return await bridge.run(run_id)

    return app
