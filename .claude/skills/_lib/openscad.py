"""OpenSCAD invocation helper used by the scad-* skills.

One entry point (`render`) that renders a `.scad` file to a PNG for a given
named view, composing:

- `xvfb-run -a openscad` (headless; DISPLAY unset on this host)
- `OPENSCADPATH=<repo>/libs` so vendored libraries resolve
- `-D name=value` pass-through for parametric overrides
- Orthographic projection for top/front/side; perspective for iso
- Stderr parsing: unresolved `use <>` warnings fail the call
- PNG existence + non-empty check

The function raises `OpenscadError` with a readable message on any failure so
callers can surface it to the user and exit non-zero.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2].parent
LIBS_DIR = REPO_ROOT / "libs"

VIEWS: dict[str, dict[str, object]] = {
    "top":   {"camera": "0,0,300,0,0,0",      "projection": "orthogonal"},
    "front": {"camera": "0,-300,0,0,0,0",     "projection": "orthogonal"},
    "side":  {"camera": "300,0,0,0,0,0",      "projection": "orthogonal"},
    "iso":   {"camera": "200,-200,150,0,0,0", "projection": "perspective"},
    # Underside/build-plate face — for models whose mounting interface
    # (e.g. Multiconnect slots) faces the plate. Not in the render-all
    # default set; opt in per model with --angles.
    "back":  {"camera": "0,0,-300,0,0,0",     "projection": "orthogonal"},
}

_UNRESOLVED_USE_RE = re.compile(
    r"WARNING:\s*Can't open (?:include|library) .*?'([^']+)'",
    re.IGNORECASE,
)


class OpenscadError(RuntimeError):
    pass


@dataclass
class RenderResult:
    view: str
    png_path: Path
    stderr: str
    warnings: list[str] = field(default_factory=list)

    @property
    def png_bytes(self) -> int:
        return self.png_path.stat().st_size if self.png_path.exists() else 0


def render(
    model: Path | str,
    out_png: Path | str,
    view: str,
    defines: dict[str, str | int | float] | None = None,
    imgsize: int = 1024,
    openscad_bin: str = "openscad",
    xvfb: bool = True,
    libs_dir: Path | str | None = None,
    full_render: bool = False,
) -> RenderResult:
    """Render one view. Raises OpenscadError on any failure.

    full_render forces `--render` (full geometry evaluation) instead of
    the default OpenCSG preview. Needed for import()-based models: the
    preview's CSG normalization explodes past its element limit on an
    imported mesh combined with BOSL2 trees and silently produces a
    blank PNG (st-f43).
    """
    if view not in VIEWS:
        raise OpenscadError(f"unknown view {view!r}; expected one of {list(VIEWS)}")
    model = Path(model).resolve()
    out_png = Path(out_png).resolve()
    if not model.exists():
        raise OpenscadError(f"model not found: {model}")
    out_png.parent.mkdir(parents=True, exist_ok=True)

    vcfg = VIEWS[view]
    cmd = _build_cmd(
        openscad_bin=openscad_bin,
        xvfb=xvfb,
        imgsize=imgsize,
        camera=vcfg["camera"],
        projection=vcfg["projection"],
        out_png=out_png,
        model=model,
        defines=defines or {},
        full_render=full_render,
    )

    env = os.environ.copy()
    libs = Path(libs_dir).resolve() if libs_dir else LIBS_DIR
    env["OPENSCADPATH"] = _prepend_path(env.get("OPENSCADPATH", ""), str(libs))

    proc = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    # openscad (AppImage 2025.06) emits WARNING/ERROR lines on stdout, not
    # stderr. Scan both streams so future packaging changes don't break us.
    stderr = (proc.stderr or "") + (proc.stdout or "")

    # The OpenCSG preview's CSG normalization can abort past its element
    # limit (big BOSL2 trees; historically import()-based models, st-f43,
    # but native models can trip it too, st-82o). openscad still exits 0
    # and writes a valid-but-blank PNG. The abort is announced in the
    # output, so detect it and redo this view with full --render.
    if not full_render and "CSG normalization resulted in an empty tree" in stderr:
        return render(
            model, out_png, view,
            defines=defines, imgsize=imgsize, openscad_bin=openscad_bin,
            xvfb=xvfb, libs_dir=libs_dir, full_render=True,
        )

    warnings = _UNRESOLVED_USE_RE.findall(stderr)
    if proc.returncode != 0:
        # Surface the full captured stream to our own stderr so callers
        # (render-all.py pipes child stdout to /dev/null) and CI logs see
        # openscad's actual diagnostic, not just `_first_line` truncated
        # into an exception message.
        sys.stderr.write(
            f"--- openscad rc={proc.returncode} rendering {view} of {model} ---\n"
            f"cmd: {' '.join(cmd)}\n"
            f"{stderr}"
            f"--- end openscad output ---\n"
        )
        raise OpenscadError(
            f"openscad exited {proc.returncode} rendering {view}: "
            f"{_first_line(stderr) or '(no stderr)'}"
        )
    if warnings:
        raise OpenscadError(
            f"unresolved use/include in {model.name}: {', '.join(sorted(set(warnings)))}"
        )
    if not out_png.exists():
        raise OpenscadError(f"openscad exited 0 but {out_png} was not written")
    if out_png.stat().st_size == 0:
        raise OpenscadError(f"openscad produced an empty PNG at {out_png}")

    return RenderResult(view=view, png_path=out_png, stderr=stderr, warnings=warnings)


def _build_cmd(
    *,
    openscad_bin: str,
    xvfb: bool,
    imgsize: int,
    camera: object,
    projection: object,
    out_png: Path,
    model: Path,
    defines: dict[str, str | int | float],
    full_render: bool = False,
) -> list[str]:
    cmd: list[str] = []
    if xvfb:
        if shutil.which("xvfb-run") is None:
            raise OpenscadError("xvfb-run not on PATH; pass xvfb=False if on a display")
        cmd += ["xvfb-run", "-a"]
    cmd += [openscad_bin]
    if full_render:
        # Must precede the positional model path: --render takes an
        # optional value and would otherwise swallow the path.
        cmd += ["--render"]
    cmd += [
        "--colorscheme=Tomorrow",
        f"--imgsize={imgsize},{imgsize}",
        f"--camera={camera}",
        f"--projection={projection}",
        "--viewall",
        "--autocenter",
        "-o", str(out_png),
    ]
    for k, v in defines.items():
        cmd += ["-D", f"{k}={_fmt_define(v)}"]
    cmd.append(str(model))
    return cmd


def _fmt_define(v: str | int | float) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return str(v)


def _prepend_path(existing: str, new: str) -> str:
    parts = [new] + [p for p in existing.split(":") if p and p != new]
    return ":".join(parts)


def _first_line(s: str) -> str:
    for line in s.splitlines():
        line = line.strip()
        if line:
            return line
    return ""
