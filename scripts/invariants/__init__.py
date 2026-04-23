"""Shared types + helpers for the per-model invariants sidecar system.

Each model ships a `models/<stem>.invariants.py` sidecar that exports a
`check(ctx)` function returning a list of `Failure`s. The core driver
(`scripts/check-invariants.py`) assembles `ctx`, calls the sidecar, and
also runs the built-in invariants in this module.

`ctx` shape (dict):
  stem             : str
  source           : str         — raw .scad text
  params           : dict[name → ParamSpec] — parsed @param annotations
  stl              : trimesh.Trimesh
  bbox_mm          : tuple[float, float, float]     — x, y, z extents
  anchor_bbox_mm   : tuple[float, float, float] | None — from PRINT_ANCHOR_BBOX
  connected_solids : int         — total connected component count
  component_sizes  : list[int]   — triangle count per component, descending
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Failure:
    """One invariant that didn't hold.

    `kind` is a short slug (footprint/clearance/topology/…) used for
    grouping in reports. `detail` is a human-readable explanation with
    the concrete numbers that failed.
    """

    kind: str
    detail: str

    def format(self) -> str:
        return f"[{self.kind}] {self.detail}"


def as_default_params(params: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Flatten a parsed param map down to `{name: default}` for cheap access.

    Per-model sidecars only care about the defaults when validating
    structural claims like "apex ≥ can_height + 10". Min/max/unit stay
    accessible on `ctx["params"]` for invariants that need them.
    """
    return {name: spec["default"] for name, spec in params.items()}


def expect_connected_solids(ctx: dict[str, Any], n: int) -> list[Failure]:
    """Sidecar helper: assert the STL has exactly `n` connected bodies.

    The built-in topology check only flags tiny orphan fragments, since
    legitimate designs (tray + cups) ship as multi-body STLs. A sidecar
    that wants stricter count discipline — "this model is a single
    monolithic solid" — calls this from its `check()`.
    """
    actual = ctx["connected_solids"]
    if actual == n:
        return []
    return [Failure(
        "connected_solids",
        f"STL has {actual} connected component(s), sidecar expected {n}",
    )]


# ---------------------------------------------------------------------------
# Built-in invariants
# ---------------------------------------------------------------------------
#
# These run for every model regardless of the sidecar. Keep them cheap and
# deterministic; anything model-specific belongs in the sidecar.


_TRIANGLE_HARD_LIMIT = 1_000_000
_ANCHOR_BBOX_TOLERANCE_MM = 1.0
# Legitimate multi-body designs (e.g. a tray with coplanar-stacked cups)
# ship as N separate connected components. A broken model typically
# produces ONE big body plus a tiny scrap of a few dozen triangles.
# Flag the latter; allow the former.
_ORPHAN_FRAGMENT_MAX_TRIS = 50


def run_builtins(ctx: dict[str, Any]) -> list[Failure]:
    """Invariants that apply to every model."""
    failures: list[Failure] = []
    failures.extend(_check_topology(ctx))
    failures.extend(_check_watertight(ctx))
    failures.extend(_check_triangle_count(ctx))
    failures.extend(_check_anchor_bbox(ctx))
    failures.extend(_check_presets(ctx))
    return failures


def _check_topology(ctx: dict[str, Any]) -> list[Failure]:
    # st-v7k class: a truly floating body (zero-thickness union gone
    # wrong) shows up as a small scrap component next to the main
    # body. Legitimate multi-part designs (baseplate + cradles) land
    # at N × (reasonably large) components, which we don't want to
    # punish here — sidecars can tighten to an exact count.
    sizes = ctx.get("component_sizes") or []
    orphans = [n for n in sizes if n <= _ORPHAN_FRAGMENT_MAX_TRIS]
    if not orphans:
        return []
    return [Failure(
        "topology",
        f"{len(orphans)} orphan fragment(s) in STL "
        f"(each ≤ {_ORPHAN_FRAGMENT_MAX_TRIS} tris: {orphans}) — "
        "a tiny stray body usually means a zero-thickness boolean (st-v7k class)",
    )]


def _check_watertight(ctx: dict[str, Any]) -> list[Failure]:
    mesh = ctx["stl"]
    if not bool(mesh.is_watertight):
        return [Failure(
            "watertight",
            f"STL is not watertight (tri={len(mesh.faces)}) — "
            "fix coplanar boolean subtracts or zero-thickness walls",
        )]
    return []


def _check_triangle_count(ctx: dict[str, Any]) -> list[Failure]:
    n = len(ctx["stl"].faces)
    if n >= _TRIANGLE_HARD_LIMIT:
        return [Failure(
            "triangle_count",
            f"STL has {n:,} triangles (≥ {_TRIANGLE_HARD_LIMIT:,} hard limit) — "
            "check $fn and sweep step counts",
        )]
    return []


def _check_anchor_bbox(ctx: dict[str, Any]) -> list[Failure]:
    anchor = ctx.get("anchor_bbox_mm")
    if anchor is None:
        return []
    actual = ctx["bbox_mm"]
    failures: list[Failure] = []
    for axis, a, b in zip("xyz", anchor, actual):
        drift = abs(a - b)
        if drift > _ANCHOR_BBOX_TOLERANCE_MM:
            failures.append(Failure(
                "anchor_bbox",
                f"{axis}-extent {b:.2f}mm drifted {drift:.2f}mm from "
                f"PRINT_ANCHOR_BBOX {a:.2f}mm (> {_ANCHOR_BBOX_TOLERANCE_MM}mm tol)",
            ))
    return failures


_PRESET_RE = re.compile(r"^\s*//\s*@preset\s+(.*)$")
_ATTR_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def _check_presets(ctx: dict[str, Any]) -> list[Failure]:
    """Every @preset key must be a declared @param; values must coerce.

    Phase 3 (st-1j9) — unknown keys and type mismatches are author bugs
    that would crash the TS parser and break the webapp load. CI
    surfaces them as invariant failures so a PR that ships a bad
    preset fails loudly. Out-of-range values are allowed (param
    bounds are advisory, not authoritative — phase 1 explicitly
    allows typed out-of-range user input).
    """
    source = ctx.get("source") or ""
    params = ctx.get("params") or {}
    failures: list[Failure] = []
    for line_no, raw in enumerate(source.splitlines(), start=1):
        m = _PRESET_RE.match(raw)
        if not m:
            continue
        attrs: dict[str, str] = {}
        for am in _ATTR_RE.finditer(m.group(1)):
            key, value = am.group(1), am.group(2)
            if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            attrs[key] = value
        preset_id = attrs.get("id", f"<line {line_no}>")
        if "id" not in attrs:
            failures.append(Failure(
                "preset",
                f"line {line_no}: @preset missing id=",
            ))
            continue
        for key, raw_value in attrs.items():
            if key in ("id", "label"):
                continue
            param = params.get(key)
            if param is None:
                failures.append(Failure(
                    "preset",
                    f'line {line_no}: preset "{preset_id}" references unknown param "{key}"',
                ))
                continue
            err = _check_preset_value(param, raw_value)
            if err is not None:
                failures.append(Failure(
                    "preset",
                    f'line {line_no}: preset "{preset_id}" value for {key}: {err}',
                ))
    return failures


def _check_preset_value(param: dict[str, Any], raw: str) -> str | None:
    kind = param.get("kind")
    if kind in ("number", "integer"):
        try:
            float(raw)
        except ValueError:
            return f"not numeric: {raw!r}"
        return None
    if kind == "boolean":
        if raw.lower() not in ("true", "false"):
            return f"expected true/false, got {raw!r}"
        return None
    if kind == "enum":
        choices = param.get("choices") or []
        if raw not in choices:
            return f"{raw!r} not in choices [{'|'.join(choices)}]"
        return None
    # strings accept anything
    return None


# ---------------------------------------------------------------------------
# Source parsing helpers
# ---------------------------------------------------------------------------


_ANCHOR_RE = re.compile(
    r"PRINT_ANCHOR_BBOX\s*=\s*\[\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\]"
)


def parse_anchor_bbox(source: str) -> tuple[float, float, float] | None:
    """Extract the `PRINT_ANCHOR_BBOX = [x, y, z]` constant from a .scad file.

    Returns `None` if the constant isn't declared or doesn't parse. Only
    literal numeric triples are supported — expressions (`[3, x+y, 9]`)
    silently yield `None` so the anchor invariant degrades to a no-op.
    """
    m = _ANCHOR_RE.search(source)
    if not m:
        return None
    try:
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)))
    except ValueError:
        return None
