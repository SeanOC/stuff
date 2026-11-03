"""Reproduce the built-in-support pad/audit contract conflict (pst-k4pan).

Run from build123d/: uv run python tools/probe_sacrificial_pad.py

Canonical rev 1 requires a 0.4–0.6 mm sacrificial pad, a one-layer tear-off
groove, and a clean audit retaining only the family's existing non-overhang
exclusions. Designed support is specified to relax overhang checks only.
The production wall audit nevertheless rejects the pad itself: its 0.9 mm
floor applies to horizontal sheets, including material touching the bed.

These rounded pads have a 0.95 mm fin, 5 mm end margins and one valid solid.
They deliberately omit the groove, which would make the wall still thinner.
The only blocking audit failure is the wall thickness. Bed chamfer absence
is a warning; adding a chamfer cannot thicken the horizontal sheet.

Resolved by CANONICAL rev 2: the opt-in audit contract applies a separate
thickness rule to explicitly declared sacrificial pad/groove regions. Fins
and retained geometry keep the 0.9 mm floor and all other checks. This
probe intentionally omits that declaration to preserve the original evidence.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Align, Box, Pos, RectangleRounded, extrude
from tests.print_audit import audit


def main():
    for thickness in (0.4, 0.6):
        pad = extrude(RectangleRounded(30, 30, 4), amount=thickness)
        fin = Pos(0, 0, thickness) * Box(
            0.95, 20, 5, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        part = pad.fuse(fin)
        report = audit(part, model=f"rounded-pad-{thickness}-with-fin")
        assert part.is_valid and len(part.solids()) == 1
        assert abs(report.min_wall_mm - thickness) < 0.001
        assert report.failures() == [
            f"wall {thickness:.2f} mm < 0.9 mm minimum"
        ]
        print(f"valid={part.is_valid}, solids={len(part.solids())}")
        print(report.format())


if __name__ == "__main__":
    main()
