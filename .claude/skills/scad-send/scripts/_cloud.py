"""Thin adapter over coelacant1/Bambu-Lab-Cloud-API.

The upstream library is unofficial and currently marked "Big commit in
progress." Keeping its surface behind a small facade means that if the
lib rewrites its API (likely), only this file needs updating — send.py
and login.py speak to `CloudClient` and stay stable.

If the library is not installed, `CloudClient(...)` raises
`LibraryMissingError` with an install hint. send.py catches this and
emits a `lib_missing` verdict rather than a bare ImportError traceback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LibraryMissingError(RuntimeError):
    """Raised when bambulabs_cloud_api (or equivalent) is not importable."""


class AuthError(RuntimeError):
    """Raised on login failures or token rejection by the cloud."""


class CloudError(RuntimeError):
    """Raised on upload / print-start failures."""


@dataclass
class UploadResult:
    remote_name: str     # name the cloud knows the file as
    size_bytes: int


@dataclass
class PrintJob:
    job_id: str          # whatever identifier the cloud hands back
    raw: dict[str, Any]  # full response for debugging


def _import_lib():
    """Lazy import so --dry-run and --help work without the lib installed."""
    try:
        import bambulabs_cloud_api as _lib  # type: ignore[import-not-found]
    except ImportError as e:
        raise LibraryMissingError(
            "bambulabs_cloud_api is not installed. Install the pinned "
            "version from requirements.txt:\n"
            "  pip install -r .claude/skills/scad-send/requirements.txt"
        ) from e
    return _lib


class CloudClient:
    """Bambu Cloud facade.

    Constructed with a persisted token dict (see `login.save_token`).
    Every public method raises one of `LibraryMissingError` / `AuthError`
    / `CloudError` with a readable message.
    """

    def __init__(self, token: dict[str, Any], region: str = "global") -> None:
        self._lib = _import_lib()
        self._region = region
        self._token = token
        # The upstream lib's client class name and constructor shape are
        # expected to change (repo says "Big commit in progress"). Keep
        # this line the ONE place that binds to the lib's public API.
        self._client = self._lib.Client(
            access_token=token["access_token"],
            region=region,
        )

    def upload_3mf(self, path: Path, remote_name: str | None = None) -> UploadResult:
        name = remote_name or path.name
        if not path.exists():
            raise CloudError(f"3mf not found: {path}")
        size = path.stat().st_size
        try:
            self._client.upload_file(str(path), name)
        except Exception as e:  # noqa: BLE001 — lib raises diverse types
            raise CloudError(f"upload failed: {e}") from e
        return UploadResult(remote_name=name, size_bytes=size)

    def start_print(self, device_id: str, remote_name: str) -> PrintJob:
        try:
            resp = self._client.start_cloud_print(device_id, remote_name)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "401" in msg or "auth" in msg.lower() or "token" in msg.lower():
                raise AuthError(f"cloud auth rejected: {e}") from e
            raise CloudError(f"start_cloud_print failed: {e}") from e
        job_id = ""
        if isinstance(resp, dict):
            job_id = str(resp.get("job_id") or resp.get("id") or "")
        return PrintJob(job_id=job_id, raw=resp if isinstance(resp, dict) else {"raw": resp})


def load_token(token_path: Path) -> dict[str, Any]:
    """Read a token dict from disk. Raises AuthError on missing/malformed."""
    if not token_path.exists():
        raise AuthError(
            f"token not found at {token_path}. Run "
            "`python3 .claude/skills/scad-send/scripts/login.py` first."
        )
    try:
        data = json.loads(token_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise AuthError(f"token file unreadable: {e}") from e
    if not isinstance(data, dict) or "access_token" not in data:
        raise AuthError(f"token file at {token_path} is missing access_token")
    return data
