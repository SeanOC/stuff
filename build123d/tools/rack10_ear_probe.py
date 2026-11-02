"""Reproduce E1's ear-wall contradiction before implementing registered models.

From build123d/: PYTHONPATH=. uv run python tools/rack10_ear_probe.py
Exit 1 is the expected blocked-spec result, not a waived model audit.
This deliberately unchamfered plate isolates the specified slot/edge spacing:
edge treatment can only remove more material from the failing ligament.
"""
from build123d import Align, Box, Pos, SlotOverall, extrude

from rack10 import constants as c
from tests.print_audit import audit


def main():
    height = c.RACK_UNIT - c.PANEL_SHORT
    part = Box(c.EAR_WIDTH, height, c.EAR_THICKNESS,
               align=(Align.CENTER, Align.MIN, Align.MIN))
    for x in (-c.HOLE_SPAN / 2, c.HOLE_SPAN / 2):
        for i in range(c.HOLES_PER_UNIT):
            y = c.HOLE_EDGE + i * c.HOLE_PITCH
            slot = SlotOverall(c.EAR_SLOT_HEIGHT, c.EAR_SLOT_WIDTH, rotation=90)
            part -= Pos(x, y, -1) * extrude(slot, amount=c.EAR_THICKNESS + 2)
    report = audit(part, model='rack10-ear-spec-probe')
    print(report.format())
    top_center = c.HOLE_EDGE + (c.HOLES_PER_UNIT - 1) * c.HOLE_PITCH
    print(f'Analytic top ligament: {height - top_center - c.EAR_SLOT_HEIGHT / 2:.3f} mm')
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
