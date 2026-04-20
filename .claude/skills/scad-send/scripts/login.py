#!/usr/bin/env python3
"""One-time interactive Bambu Cloud login.

Walks the user through email + password (+ email-OTP if 2FA is enabled)
and persists the bearer token to `~/.config/bambu-send/token.json` with
mode 0600 so send.py can read it later.

This is interactive by design — it should not be invoked by automation.
Run it manually whenever the persisted token expires (empirically every
~7 days).
"""

from __future__ import annotations

import getpass
import json
import os
import sys
from pathlib import Path

CONFIG_DIR = Path("~/.config/bambu-send").expanduser()
TOKEN_PATH = CONFIG_DIR / "token.json"


def main() -> int:
    print("Bambu Cloud login (one-time setup, refresh on token expiry).")
    print(f"Token will be persisted to {TOKEN_PATH} (chmod 600).")
    print()

    region = _ask("Region [global/china]", default="global").strip().lower()
    if region not in ("global", "china"):
        print(f"  unsupported region: {region!r}", file=sys.stderr)
        return 2

    email = _ask("Bambu Cloud email").strip()
    if not email:
        print("  email required", file=sys.stderr)
        return 2

    password = getpass.getpass("Bambu Cloud password: ")
    if not password:
        print("  password required", file=sys.stderr)
        return 2

    # OTP is only prompted if the lib reports 2FA is required. Asking
    # unconditionally would confuse single-factor accounts.
    try:
        from _cloud import LibraryMissingError, _import_lib  # type: ignore[import-not-found]
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        lib = _import_lib()
    except LibraryMissingError as e:
        print(f"  {e}", file=sys.stderr)
        return 3
    except ImportError as e:
        print(f"  _cloud import failed: {e}", file=sys.stderr)
        return 3

    try:
        token = lib.login(email=email, password=password, region=region)
    except Exception as e:  # noqa: BLE001 — lib raises diverse types
        msg = str(e).lower()
        if "2fa" in msg or "otp" in msg or "verification" in msg:
            otp = _ask("Email OTP code").strip()
            try:
                token = lib.login(
                    email=email, password=password, region=region, otp=otp,
                )
            except Exception as e2:  # noqa: BLE001
                print(f"  login failed after OTP: {e2}", file=sys.stderr)
                return 4
        else:
            print(f"  login failed: {e}", file=sys.stderr)
            return 4

    if not isinstance(token, dict) or "access_token" not in token:
        # Lib may return a token object instead of a dict — coerce.
        access = getattr(token, "access_token", None)
        if not access:
            print(f"  unexpected token shape: {type(token).__name__}", file=sys.stderr)
            return 5
        token = {"access_token": access, "region": region}
    else:
        token.setdefault("region", region)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2))
    os.chmod(TOKEN_PATH, 0o600)
    print(f"OK — token written to {TOKEN_PATH}")
    return 0


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ")
    if not answer and default is not None:
        return default
    return answer


if __name__ == "__main__":
    raise SystemExit(main())
