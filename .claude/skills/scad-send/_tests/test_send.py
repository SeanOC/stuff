"""Tests for scad-send/scripts/send.py.

Coverage is dry-run-shaped: no network, no real bambu-studio invocation
(we shim it on PATH with a tmp script that copies the input). The cloud
library is never imported in these paths.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3].parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "scad-send" / "scripts" / "send.py"


def _load_send():
    spec = importlib.util.spec_from_file_location("scad_send_script", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(mod, *argv: str) -> tuple[int, dict]:
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        rc = mod.main(list(argv))
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        pytest.fail(f"non-JSON stdout: {out!r}")
    return rc, payload


def _write_yaml(path: Path, profiles_dir: Path) -> None:
    """Write a printers.yaml pointing at three real (empty) profile files."""
    machine = profiles_dir / "machine.json"
    process = profiles_dir / "process.json"
    filament = profiles_dir / "filament.json"
    for p in (machine, process, filament):
        p.write_text("{}")
    path.write_text(textwrap.dedent(f"""
        default_printer: testbox
        printers:
          testbox:
            device_id: "TEST-DEV-001"
            region: global
            profile_set: pla
        profile_sets:
          pla:
            machine:  {machine}
            process:  {process}
            filament: {filament}
    """).lstrip())


def _shim_bambu_studio(bin_dir: Path) -> Path:
    """Install a fake `bambu-studio` on PATH that writes a tiny 3MF."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "bambu-studio"
    shim.write_text(textwrap.dedent("""
        #!/usr/bin/env bash
        # Walk argv to find --export-3mf <path>, write a stub there.
        out=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --export-3mf) out="$2"; shift 2 ;;
                *) shift ;;
            esac
        done
        if [ -z "$out" ]; then
            echo "shim: no --export-3mf path" >&2
            exit 2
        fi
        printf 'PK\\x03\\x04stub-3mf' > "$out"
    """).lstrip())
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim


def test_T1_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    """`--help` exits 0 cleanly, no traceback, no missing-lib error."""
    mod = _load_send()
    with pytest.raises(SystemExit) as ei:
        mod.main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--dry-run" in out
    assert "--printer" in out


def test_T2_no_source_fails(tmp_path: Path) -> None:
    """Missing all of --model/--stl/--3mf is a config error, not a crash."""
    mod = _load_send()
    cfg = tmp_path / "p.yaml"
    _write_yaml(cfg, tmp_path)
    rc, out = _run(mod, "--config", str(cfg), "--dry-run")
    assert rc != 0
    assert out["verdict"] == "config_missing"
    assert "exactly one" in out["error"]


def test_T3_dry_run_with_3mf_skips_slicing(tmp_path: Path) -> None:
    """3MF input goes straight through dry-run without invoking the slicer."""
    mod = _load_send()
    cfg = tmp_path / "p.yaml"
    _write_yaml(cfg, tmp_path)
    mf = tmp_path / "thing.3mf"
    mf.write_bytes(b"PK\x03\x04stub")
    rc, out = _run(
        mod, "--3mf", str(mf), "--printer", "testbox",
        "--config", str(cfg), "--dry-run",
    )
    assert rc == 0, f"rc={rc} payload={out}"
    assert out["verdict"] == "dry_run_ok"
    assert out["printer"] == "testbox"
    assert out["device_id"] == "TEST-DEV-001"
    assert out["source"]["kind"] == "3mf"
    assert out["would_upload_name"] == "thing.3mf"


def test_T4_dry_run_with_stl_invokes_slicer(tmp_path: Path, monkeypatch) -> None:
    """STL input runs the slicer (shimmed) and reports the produced 3MF."""
    mod = _load_send()
    cfg = tmp_path / "p.yaml"
    _write_yaml(cfg, tmp_path)
    bin_dir = tmp_path / "bin"
    _shim_bambu_studio(bin_dir)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    stl = tmp_path / "widget.stl"
    stl.write_bytes(b"solid widget\nendsolid widget\n")

    rc, out = _run(
        mod, "--stl", str(stl), "--printer", "testbox",
        "--config", str(cfg), "--dry-run",
    )
    assert rc == 0, f"rc={rc} payload={out}"
    assert out["verdict"] == "dry_run_ok"
    assert out["source"]["kind"] == "stl"
    assert out["sliced_3mf"].endswith("widget.3mf")


def test_T5_unknown_printer_alias(tmp_path: Path) -> None:
    mod = _load_send()
    cfg = tmp_path / "p.yaml"
    _write_yaml(cfg, tmp_path)
    mf = tmp_path / "thing.3mf"
    mf.write_bytes(b"x")
    rc, out = _run(
        mod, "--3mf", str(mf), "--printer", "ghost",
        "--config", str(cfg), "--dry-run",
    )
    assert rc != 0
    assert out["verdict"] == "config_missing"
    assert "ghost" in out["error"]


def test_T6_missing_profile_file(tmp_path: Path) -> None:
    """If a profile path doesn't exist, fail before even trying to slice."""
    mod = _load_send()
    cfg = tmp_path / "p.yaml"
    cfg.write_text(textwrap.dedent("""
        default_printer: testbox
        printers:
          testbox:
            device_id: "X"
            region: global
            profile_set: pla
        profile_sets:
          pla:
            machine:  /nope/machine.json
            process:  /nope/process.json
            filament: /nope/filament.json
    """).lstrip())
    stl = tmp_path / "widget.stl"
    stl.write_bytes(b"x")
    rc, out = _run(mod, "--stl", str(stl), "--config", str(cfg), "--dry-run")
    assert rc != 0
    assert out["verdict"] == "config_missing"
    assert "machine" in out["error"]


def test_T7_missing_config(tmp_path: Path) -> None:
    mod = _load_send()
    mf = tmp_path / "thing.3mf"
    mf.write_bytes(b"x")
    rc, out = _run(
        mod, "--3mf", str(mf), "--config", str(tmp_path / "no.yaml"),
        "--dry-run",
    )
    assert rc != 0
    assert out["verdict"] == "config_missing"
    assert "not found" in out["error"]
