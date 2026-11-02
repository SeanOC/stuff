"""Bambuddy 1.2.5.7 spool identifiers and deterministic filament resolution."""

from __future__ import annotations

import re
from typing import Any


def global_slot(ams_id: int, tray_id: int) -> int | None:
    if type(ams_id) is not int or type(tray_id) is not int:
        return None
    if 0 <= ams_id <= 3 and 0 <= tray_id <= 3:
        return ams_id * 4 + tray_id
    if 128 <= ams_id <= 135 and tray_id == 0:
        return ams_id
    return None  # includes the external spool (254)


def colour(raw: Any) -> str | None:
    if isinstance(raw, str) and re.fullmatch(r"[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", raw):
        return "#" + raw[:6]
    return None


def resolve(
    tray: dict[str, Any],
    name: str | None,
    printer_ref: dict[str, str],
    presets: dict[str, Any],
    overrides: dict[str, dict[str, str]],
) -> tuple[dict[str, str] | None, bool]:
    if override := overrides.get(tray.get("tray_info_idx")):
        return override, False
    printer_name = next(
        (
            p["name"]
            for p in presets.get(printer_ref["source"], {}).get("printer", [])
            if p.get("id") == printer_ref["id"]
        ),
        None,
    )
    if not printer_name:
        return None, False
    standard = [
        p
        for p in presets.get("standard", {}).get("filament", [])
        if printer_name in (p.get("compatible_printers") or [])
    ]

    def first(rows, source):
        # Stable tie-breakers even if Bambuddy changes listing order.
        if not rows:
            return None
        p = min(rows, key=lambda p: (len(p["name"]), p["name"], p["id"]))
        return {"source": source, "id": p["id"]}

    if name:
        if ref := first([p for p in standard if p["name"].startswith(name + " @")], "standard"):
            return ref, False
        if ref := first(
            [
                p
                for p in presets.get("cloud", {}).get("filament", [])
                if p["name"] == f"{name} @{printer_name}"
            ],
            "cloud",
        ):
            return ref, False
    material = tray.get("tray_type")
    if material:
        if ref := first(
            [p for p in standard if p["name"].startswith(f"Generic {material} @BBL ")], "standard"
        ):
            return ref, True
    return None, False
