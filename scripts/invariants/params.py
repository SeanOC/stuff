"""Minimal Python port of lib/scad-params/parse.ts.

Only what the invariants script needs: recognize the user-tunable block,
extract each `@param` declaration's name, kind, default, and a handful
of common attrs (min, max, step, unit, group, label). Warnings aren't
surfaced here — the TS parser already covers that path for anything the
webapp consumes; if an invariant needs stricter parsing in the future,
this module is the place to extend.
"""

from __future__ import annotations

import re
from typing import Any

_SECTION_RE = re.compile(r"^\s*//\s*={2,}\s*(.*?)\s*={2,}\s*$")
_USER_TUNABLE_RE = re.compile(r"user[-_ ]tunable", re.IGNORECASE)
_PARAM_LINE_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);\s*//\s*(.*)$"
)
_ANNOTATION_RE = re.compile(r"^@param\s+(\w+)\b\s*(.*)$")
_ATTR_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def parse_params(source: str) -> dict[str, dict[str, Any]]:
    """Return `{name: {kind, default, min?, max?, step?, unit?, group?, label?, choices?}}`.

    Integers get `kind="integer"` with a truncated default; numbers stay
    float. Booleans resolve to Python bools. Enum defaults that aren't in
    the `choices=` list are accepted — the TS parser warns about this
    case and so would we, but invariants don't need a strict check.
    """
    params: dict[str, dict[str, Any]] = {}
    in_block = False
    for line in source.splitlines():
        section = _SECTION_RE.match(line)
        if section:
            if not in_block and _USER_TUNABLE_RE.search(section.group(1)):
                in_block = True
            elif in_block:
                break
            continue
        if not in_block:
            continue
        m = _PARAM_LINE_RE.match(line)
        if not m:
            continue
        name, raw_default, comment = m.group(1), m.group(2).strip(), m.group(3).strip()
        ann = _ANNOTATION_RE.match(comment)
        if not ann:
            continue
        kind = ann.group(1)
        attrs = _parse_attrs(ann.group(2))
        spec = _build_param(kind, raw_default, attrs)
        if spec is not None:
            params[name] = spec
    return params


def _build_param(
    kind: str,
    raw_default: str,
    attrs: dict[str, str],
) -> dict[str, Any] | None:
    base: dict[str, Any] = {"kind": kind}
    for key in ("label", "group", "unit"):
        if key in attrs:
            base[key] = attrs[key]

    if kind in ("number", "integer"):
        try:
            default = float(raw_default)
        except ValueError:
            return None
        base["default"] = int(default) if kind == "integer" else default
        for key in ("min", "max", "step"):
            if key in attrs:
                try:
                    base[key] = float(attrs[key])
                except ValueError:
                    pass
        return base

    if kind == "boolean":
        lower = raw_default.lower()
        if lower not in ("true", "false"):
            return None
        base["default"] = lower == "true"
        return base

    if kind == "string":
        base["default"] = _unquote(raw_default)
        return base

    if kind == "enum":
        choices_raw = attrs.get("choices")
        if not choices_raw:
            return None
        choices = [c.strip() for c in choices_raw.split("|") if c.strip()]
        if not choices:
            return None
        base["default"] = _unquote(raw_default)
        base["choices"] = choices
        return base

    return None


def _parse_attrs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _ATTR_RE.finditer(text):
        out[m.group(1)] = _unquote(m.group(2))
    return out


def _unquote(s: str) -> str:
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return re.sub(r"\\(.)", r"\1", s[1:-1])
    return s
