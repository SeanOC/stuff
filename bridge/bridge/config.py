"""Bridge configuration — environment only, never a file in the repo."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_ALLOWED_ORIGIN = "https://stuff.seanoc.com"
REQUIRED = ("STUFF_URL", "BAMBUDDY_URL", "BAMBUDDY_API_KEY", "PIPELINES", "TRUSTED_LOGIN")


class ConfigError(RuntimeError):
    """The environment cannot start the bridge. Never carries a secret value."""


@dataclass(frozen=True)
class Config:
    stuff_url: str
    bambuddy_url: str
    # repr=False: a logged or printed Config must never show the key.
    bambuddy_api_key: str = field(repr=False)
    pipelines: dict[int, str]  # printer_id -> Bambuddy slicer-pipeline name
    trusted_login: str
    allowed_origin: str = DEFAULT_ALLOWED_ORIGIN


def parse_pipelines(raw: str) -> dict[int, str]:
    """`2=stuff-joey,1=stuff-crushinator` -> {2: "stuff-joey", 1: "stuff-crushinator"}."""
    out: dict[int, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        pid, sep, name = item.partition("=")
        if not sep or not pid.strip().isdigit() or not name.strip():
            raise ConfigError(f"PIPELINES entry {item!r} is not <printer_id>=<pipeline name>")
        out[int(pid)] = name.strip()
    if not out:
        raise ConfigError("PIPELINES names no printer")
    return out


def load_config(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    missing = [k for k in REQUIRED if not env.get(k, "").strip()]
    if missing:
        raise ConfigError(f"missing required environment: {', '.join(missing)}")
    return Config(
        stuff_url=env["STUFF_URL"].strip().rstrip("/"),
        bambuddy_url=env["BAMBUDDY_URL"].strip().rstrip("/"),
        bambuddy_api_key=env["BAMBUDDY_API_KEY"].strip(),
        pipelines=parse_pipelines(env["PIPELINES"]),
        trusted_login=env["TRUSTED_LOGIN"].strip(),
        allowed_origin=(env.get("ALLOWED_ORIGIN") or DEFAULT_ALLOWED_ORIGIN).strip(),
    )
