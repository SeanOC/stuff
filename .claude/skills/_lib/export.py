"""STL export + watertight verification.

Runs `openscad -o out.stl model.scad` (full CGAL/Manifold render), loads the
resulting STL with `trimesh`, and reports bbox / triangle count / watertight
status. Non-watertight STLs raise `ExportError` so the caller can exit
non-zero (R9, R14, R15).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import trimesh

from .openscad import LIBS_DIR, OpenscadError, _fmt_define, _prepend_path

_WARNING_RE = re.compile(
    r"WARNING:\s*Can't open (?:include|library) .*?'([^']+)'",
    re.IGNORECASE,
)


class ExportError(RuntimeError):
    pass


@dataclass
class ExportResult:
    stl_path: Path
    bbox_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    triangle_count: int
    is_watertight: bool


def export(
    model: Path | str,
    out_stl: Path | str,
    defines: dict[str, str | int | float] | None = None,
    openscad_bin: str = "openscad",
    xvfb: bool = True,
    libs_dir: Path | str | None = None,
) -> ExportResult:
    model = Path(model).resolve()
    out_stl = Path(out_stl).resolve()
    if not model.exists():
        raise ExportError(f"model not found: {model}")
    out_stl.parent.mkdir(parents=True, exist_ok=True)
    if out_stl.exists():
        out_stl.unlink()

    cmd: list[str] = []
    if xvfb:
        if shutil.which("xvfb-run") is None:
            raise ExportError("xvfb-run not on PATH; pass xvfb=False if on a display")
        cmd += ["xvfb-run", "-a"]
    cmd += [openscad_bin, "-o", str(out_stl)]
    for k, v in (defines or {}).items():
        cmd += ["-D", f"{k}={_fmt_define(v)}"]
    cmd.append(str(model))

    env = os.environ.copy()
    libs = Path(libs_dir).resolve() if libs_dir else LIBS_DIR
    env["OPENSCADPATH"] = _prepend_path(env.get("OPENSCADPATH", ""), str(libs))

    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    combined = (proc.stderr or "") + (proc.stdout or "")
    warnings = _WARNING_RE.findall(combined)

    if proc.returncode != 0:
        raise ExportError(
            f"openscad exited {proc.returncode}: {_first_line(combined) or '(no output)'}"
        )
    if warnings:
        raise ExportError(
            f"unresolved use/include in {model.name}: {', '.join(sorted(set(warnings)))}"
        )
    if not out_stl.exists():
        raise ExportError(f"openscad exited 0 but {out_stl} was not written")
    if out_stl.stat().st_size == 0:
        raise ExportError(f"openscad produced an empty STL at {out_stl}")

    mesh = trimesh.load(out_stl, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ExportError(f"trimesh could not load {out_stl} as a single mesh")

    bounds = mesh.bounds
    bbox_mm = (
        (float(bounds[0, 0]), float(bounds[0, 1]), float(bounds[0, 2])),
        (float(bounds[1, 0]), float(bounds[1, 1]), float(bounds[1, 2])),
    )
    tri_count = int(len(mesh.faces))
    watertight = bool(mesh.is_watertight)

    result = ExportResult(
        stl_path=out_stl,
        bbox_mm=bbox_mm,
        triangle_count=tri_count,
        is_watertight=watertight,
    )

    if not watertight:
        raise ExportError(
            f"STL not watertight: {out_stl} (tri={tri_count}, "
            f"bbox={bbox_mm}) — fix the model before export"
        )

    return result


def _first_line(s: str) -> str:
    for line in s.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


# Re-export OpenscadError for callers that want to catch both transparently.
__all__ = ["export", "ExportError", "ExportResult", "OpenscadError"]
