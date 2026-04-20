#!/usr/bin/env python3
"""Send a sliced 3MF (or slice an STL/SCAD first) to a Bambu X1C via cloud.

Single JSON object to stdout. Non-zero exit on any failure. The
human-in-the-loop approval gate lives in SKILL.md prose — this script
trusts that Claude has already obtained approval before invoking it
without --dry-run.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3].parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
sys.path.insert(0, str(SKILLS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_CONFIG = Path("~/.config/bambu-send/printers.yaml").expanduser()
DEFAULT_TOKEN = Path("~/.config/bambu-send/token.json").expanduser()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # 1. Resolve source file + kind.
    source = _resolve_source(args)
    if source is None:
        _emit({
            "verdict": "config_missing",
            "error": "exactly one of --model, --stl, --3mf is required",
        })
        return 2
    src_kind, src_path = source
    if not src_path.exists():
        _emit({
            "verdict": "config_missing",
            "error": f"{src_kind} not found: {src_path}",
        })
        return 2

    # 2. Load printer config (skip token until we actually send).
    try:
        config = _load_config(Path(args.config).expanduser())
    except ConfigError as e:
        _emit({"verdict": "config_missing", "error": str(e)})
        return 2

    alias = args.printer or config.get("default_printer")
    if not alias:
        _emit({
            "verdict": "config_missing",
            "error": "no --printer given and no default_printer in config",
        })
        return 2

    try:
        printer, profiles = _resolve_printer(config, alias, args.profile_set)
    except ConfigError as e:
        _emit({"verdict": "config_missing", "error": str(e)})
        return 2

    name = args.name or src_path.stem
    warnings: list[str] = []

    with tempfile.TemporaryDirectory(prefix="scad-send-") as tmp:
        tmp_dir = Path(tmp)

        # 3. Get to a 3MF.
        if src_kind == "3mf":
            mf_path = src_path
        else:
            # SCAD → STL (only when --model)
            if src_kind == "model":
                try:
                    stl_path = _scad_to_stl(src_path, tmp_dir / f"{name}.stl")
                except SliceError as e:
                    _emit({"verdict": "slice_failed", "error": str(e)})
                    return 3
            else:
                stl_path = src_path

            # STL → 3MF via bambu-studio CLI.
            try:
                mf_path = _slice_stl(stl_path, tmp_dir / f"{name}.3mf", profiles)
            except SliceError as e:
                _emit({"verdict": "slice_failed", "error": str(e)})
                return 3

        # 4. Dry-run stops here, just before any cloud activity.
        if args.dry_run:
            _emit({
                "verdict": "dry_run_ok",
                "printer": alias,
                "device_id": printer["device_id"],
                "source": {"kind": src_kind, "path": str(src_path)},
                "sliced_3mf": str(mf_path),
                "would_upload_name": f"{name}.3mf",
                "warnings": warnings,
            })
            return 0

        # 5. Live send: load token, instantiate cloud client.
        try:
            from _cloud import (  # type: ignore[import-not-found]
                AuthError,
                CloudClient,
                CloudError,
                LibraryMissingError,
                load_token,
            )
        except ImportError as e:
            _emit({"verdict": "lib_missing", "error": f"_cloud import failed: {e}"})
            return 4

        token_path = Path(args.token).expanduser()
        try:
            token = load_token(token_path)
        except AuthError as e:
            _emit({"verdict": "token_missing", "error": str(e)})
            return 4

        try:
            client = CloudClient(token, region=printer.get("region", "global"))
        except LibraryMissingError as e:
            _emit({"verdict": "lib_missing", "error": str(e)})
            return 4

        # 6. Upload.
        try:
            up = client.upload_3mf(mf_path, remote_name=f"{name}.3mf")
        except CloudError as e:
            _emit({"verdict": "upload_failed", "error": str(e)})
            return 5
        except AuthError as e:
            _emit({"verdict": "upload_failed", "error": str(e)})
            return 5

        # 7. Start print.
        try:
            job = client.start_print(printer["device_id"], up.remote_name)
        except AuthError as e:
            _emit({"verdict": "start_failed", "error": str(e)})
            return 6
        except CloudError as e:
            _emit({"verdict": "start_failed", "error": str(e)})
            return 6

        _emit({
            "verdict": "sent_ok",
            "printer": alias,
            "device_id": printer["device_id"],
            "source": {"kind": src_kind, "path": str(src_path)},
            "sliced_3mf": str(mf_path),
            "uploaded_name": up.remote_name,
            "job_id": job.job_id,
            "warnings": warnings,
        })
        return 0


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

class ConfigError(RuntimeError):
    pass


class SliceError(RuntimeError):
    pass


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Slice + cloud-send to Bambu X1C")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--model", help="Path to .scad source")
    src.add_argument("--stl", help="Path to pre-exported STL")
    src.add_argument("--3mf", dest="threemf", help="Path to pre-sliced 3MF")
    p.add_argument("--printer", help="Printer alias from printers.yaml")
    p.add_argument("--profile-set", dest="profile_set",
                   help="Override the printer's default profile set")
    p.add_argument("--config", default=str(DEFAULT_CONFIG),
                   help=f"Config path (default: {DEFAULT_CONFIG})")
    p.add_argument("--token", default=str(DEFAULT_TOKEN),
                   help=f"Token path (default: {DEFAULT_TOKEN})")
    p.add_argument("--name", help="Basename for uploaded file (default: source stem)")
    p.add_argument("--dry-run", action="store_true",
                   help="Resolve config + slice, but never touch the cloud")
    return p.parse_args(argv)


def _resolve_source(args: argparse.Namespace) -> tuple[str, Path] | None:
    if args.model:
        return "model", Path(args.model).resolve()
    if args.stl:
        return "stl", Path(args.stl).resolve()
    if args.threemf:
        return "3mf", Path(args.threemf).resolve()
    return None


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(
            f"config not found at {path}. See "
            ".claude/skills/scad-send/printers.example.yaml"
        )
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as e:
        raise ConfigError(
            "PyYAML not installed. Install with "
            "`pip install -r .claude/skills/scad-send/requirements.txt`"
        ) from e
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as e:
        raise ConfigError(f"config unreadable: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"config at {path} is not a YAML mapping")
    return data


def _resolve_printer(
    config: dict[str, Any], alias: str, profile_set_override: str | None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    printers = config.get("printers") or {}
    if alias not in printers:
        raise ConfigError(f"printer alias {alias!r} not found in config")
    printer = printers[alias]
    if "device_id" not in printer:
        raise ConfigError(f"printer {alias!r} is missing device_id")

    profile_set_name = profile_set_override or printer.get("profile_set")
    if not profile_set_name:
        raise ConfigError(
            f"printer {alias!r} has no profile_set and none given via --profile-set"
        )

    sets = config.get("profile_sets") or {}
    if profile_set_name not in sets:
        raise ConfigError(f"profile_set {profile_set_name!r} not found in config")

    raw = sets[profile_set_name]
    profiles: dict[str, Path] = {}
    for key in ("machine", "process", "filament"):
        if key not in raw:
            raise ConfigError(
                f"profile_set {profile_set_name!r} is missing {key!r} path"
            )
        p = Path(raw[key]).expanduser()
        if not p.exists():
            raise ConfigError(
                f"profile_set {profile_set_name!r} {key} path does not exist: {p}"
            )
        profiles[key] = p
    return printer, profiles


def _scad_to_stl(scad: Path, out_stl: Path) -> Path:
    """Reuse scad-export's openscad helper so SCAD→STL is one code path."""
    try:
        from _lib import export as _exp  # type: ignore[import-not-found]
    except ImportError as e:
        raise SliceError(f"scad-export _lib not importable: {e}") from e
    try:
        _exp.export(scad, out_stl)
    except _exp.ExportError as e:
        raise SliceError(f"scad → stl failed: {e}") from e
    if not out_stl.exists() or out_stl.stat().st_size == 0:
        raise SliceError(f"openscad produced no STL at {out_stl}")
    return out_stl


def _slice_stl(stl: Path, out_3mf: Path, profiles: dict[str, Path]) -> Path:
    """Invoke bambu-studio CLI to slice an STL into a 3MF."""
    bin_path = shutil.which("bambu-studio") or shutil.which("BambuStudio")
    if not bin_path:
        raise SliceError(
            "bambu-studio CLI not found on PATH. Install Bambu Studio "
            "(see SKILL.md runbook step 1)."
        )
    settings = f"{profiles['machine']};{profiles['process']}"
    cmd = [
        bin_path,
        "--load-settings", settings,
        "--load-filaments", str(profiles["filament"]),
        "--slice", "0",
        "--export-3mf", str(out_3mf),
        str(stl),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SliceError(f"bambu-studio invocation failed: {e}") from e
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").splitlines()[-10:]
        raise SliceError(
            f"bambu-studio exited {result.returncode}. Last output:\n"
            + "\n".join(tail)
        )
    if not out_3mf.exists() or out_3mf.stat().st_size == 0:
        raise SliceError(f"bambu-studio produced no 3MF at {out_3mf}")
    return out_3mf


def _emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
