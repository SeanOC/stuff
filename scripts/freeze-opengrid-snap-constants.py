#!/usr/bin/env python3
"""Operator-run scalar snapshot; upstream source stays in memory only.

From the repo root: uv run --project build123d python scripts/freeze-opengrid-snap-constants.py
This is an explicit reference refresh, never a test prerequisite. Numeric token
positions address the pinned file without copying SCAD argument identifiers.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen

TOOL = "freeze-opengrid-snap-constants/1"
COMMIT = "6123129"
SOURCE_URL = f"https://raw.githubusercontent.com/AndyLevesque/QuackWorks/{COMMIT}/openGrid/opengrid-snap.scad"
LOCATOR = f"https://github.com/AndyLevesque/QuackWorks/blob/{COMMIT}/openGrid/opengrid-snap.scad#L"
OUTPUT = Path(__file__).resolve().parents[1] / "build123d/reference/opengrid-snap-constants.json"
NUMBER = re.compile(r"(?<![\w.])[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")

# Port constant name -> (one-based source line, zero-based numeric token).
# Select literals independently of the port's current values and locators.
POSITIONS = {
    "CORE_WIDTH": (37, 0),
    "FULL_EXTRA": (38, 0),
    "LITE_HEIGHT": (39, 0),
    "CORE_HEIGHT": (42, 0),
    "TOP_HEIGHT": (43, 0),
    "TOP_NUB_HEIGHT": (44, 0),
    "TOP_CORNER": (48, 2),
    "CORE_CORNER": (50, 0),
    "TOP_NUB_OFFSET": (52, 0),
    "TOP_NUB_WIDTH": (55, 6),
    "OVERLAP": (26, 0),
    "NUB_TOP": (26, 1),
    "NUB_HEIGHT": (62, 0),
    "NUB_WIDTH": (63, 0),
    "NUB_DEPTH": (64, 0),
    "NUB_TOP_WEDGE": (65, 0),
    "NUB_BOTTOM_WEDGE": (66, 0),
    "NUB_ROUND_X": (67, 0),
    "NUB_ROUND_SCALE": (68, 0),
    "NUB_ROUND_RADIUS": (69, 0),
    "BOTTOM_WEDGE_DEPTH": (30, 3),
    "FRONT_HEIGHT": (77, 0),
    "FRONT_WIDTH": (78, 0),
    "FRONT_DEPTH": (79, 0),
    "FRONT_TOP_WEDGE": (80, 0),
    "FRONT_BOTTOM_WEDGE": (81, 0),
    "FRONT_ROUND_X": (82, 0),
    "FRONT_ROUND_SCALE": (83, 0),
    "FRONT_ROUND_RADIUS": (84, 0),
    "FRONT_BOTTOM_SHIFT": (85, 0),
    "REAR_HEIGHT": (91, 0),
    "REAR_WIDTH": (92, 0),
    "REAR_DEPTH": (93, 0),
    "REAR_TOP_WEDGE": (94, 0),
    "REAR_BOTTOM_WEDGE": (95, 0),
    "REAR_ROUND_X": (96, 0),
    "REAR_ROUND_SCALE": (97, 0),
    "REAR_ROUND_RADIUS": (98, 0),
    "CLICK_OFFSET": (105, 1),
    "CLICK_DEPTH": (107, 0),
    "CLICK_WIDTH": (107, 1),
    "CLICK_RADIUS": (107, 4),
    "CLICK_ROOF": (107, 2),
    "REAR_CLICK_START": (110, 4),
    "REAR_CLICK_HEIGHT": (110, 7),
    "REAR_CLICK_OFFSET": (111, 2),
    "REAR_CLICK_RISE": (111, 9),
    "REAR_CLICK_SHIFT": (111, 10),
    "REAR_RELIEF_OFFSET": (112, 2),
    "REAR_RELIEF_DEPTH": (112, 8),
    "REAR_RELIEF_WIDTH": (112, 9),
    "REAR_RELIEF_HEIGHT": (112, 14),
    "WALL_CLICK_HEIGHT": (117, 2),
    "WALL_CLICK_DEPTH": (119, 0),
    "WALL_CLICK_WIDTH": (119, 1),
    "WALL_CLICK_THICKNESS": (119, 2),
    "INDICATOR_X": (122, 0),
    "INDICATOR_BOTTOM_RADIUS": (122, 3),
    "INDICATOR_TOP_RADIUS": (122, 4),
    "INDICATOR_HEIGHT": (122, 5),
}


def main():
    with urlopen(SOURCE_URL, timeout=30) as response:
        source = response.read()
    lines = source.decode("utf-8").splitlines()
    constants = {}
    for name, (line, token) in POSITIONS.items():
        literals = NUMBER.findall(lines[line - 1].split("//", 1)[0])
        constants[name] = {"value": float(literals[token]), "locator": f"{LOCATOR}{line}"}
    table = {
        "note": "Measurements only; deliberately unmanifested and outside reference/measured/: not a measure_step/1 geometry artifact. No source text or SCAD argument identifiers.",
        "tool": TOOL,
        "build123d": version("build123d"),
        "source_url": SOURCE_URL,
        "source_commit": COMMIT,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
        "attribution": "Values derived from AndyLevesque/QuackWorks openGrid/opengrid-snap.scad @6123129, CC BY-NC-SA 4.0; numbers only, no source text",
        "constants": constants,
    }
    OUTPUT.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(constants)} scalar measurements to {OUTPUT}")


if __name__ == "__main__":
    main()
