# Rack10 interface — E1 checkpoint

This package is original geometry to the project's de facto 10-inch rack
interface, not a port of another project's mounts. No formal 10-inch
standard is claimed. Constants currently implement the E1 task's specified
numbers; generators and registered models are pending the decision below.

## Interface provenance

All values below are **[C] cited**, not physical measurements. The controlling
source is task `pst-go6df.1`, description invariants 1, 3 and 4, dated
2026-11-02. The named assignments in
[openRack's rack_units.scad](https://github.com/dduxx/openRack/blob/main/scad/lib/rack_units.scad)
also corroborate the rack unit, hole pitch, bottom offset, full width,
cage square and three-hole count. No upstream source is committed.

| Constants | mm unless otherwise indicated | Provenance |
| --- | --- | --- |
| RACK_UNIT / HOLE_PITCH / HOLE_EDGE | 44.45 / 15.875 / 6.35 | [C] E1; openRack RACK_UNIT / RACK_UNIT_HOLE_SPACING / RACK_UNIT_HOLE_BOTTOM_EDGE_OFFSET |
| EAR_WIDTH / HOLE_SPAN | 254 / 236.525 | [C] E1; openRack TEN_INCH_STANDARD_WIDTH corroborates width only |
| CLEAR_OPENING / USABLE_WIDTH | 222.25 / 210 | [C] E1 |
| CAGE_SQUARE | 9.525 | [C] E1; openRack RACK_SQUARE_HOLE_XY |
| PANEL_SHORT / SCREW_CLEAR | 0.8 / 6.4 | [C] E1 |
| EAR_SLOT_WIDTH / EAR_SLOT_HEIGHT | 7 / 10 | [C] E1; overall slot dimensions |
| PANEL_THICKNESS / EAR_THICKNESS | 3 / 4 | [C] E1 |
| HOLES_PER_UNIT | 3 (count) | [C] E1; openRack HOLES_PER_UNIT |
| TRAY_SIDE_MARGIN / TRAY_OUTER_WIDTH_LIMIT | 1 / 220.25 | [C] derived from E1's fit cap and clear opening |
| KEYSTONE_WIDTH / KEYSTONE_HEIGHT / KEYSTONE_PITCH | 14.5 / 16 / 19 | [C] E1; latch relief dimensions still need an interface source |
| MAX_KEYSTONES | 11 (count) | [C] derived from E1: floor(210 / 19) |

The requested HOLE_SPAN is 236.525 mm (approximately 9.312 inches), whereas
9.3125 inches is 236.5375 mm. The explicit millimetre value is retained.
The eventual frame choice needs a physical ear fit check, especially if a
HomeRacker or DeskPi frame is chosen instead of the proposed extrusion frame.

## Blocking ear-ligament decision

E1 simultaneously requires:

- A 1U panel height of 43.65 mm.
- Hole centres at 6.35, 22.225 and 38.1 mm **from the panel bottom edge**.
- 7 × 10 mm vertical slots, three per U on each ear.
- Minimum walls of 0.9 mm everywhere and no new audit exceptions.

At the upper slot's apex, the remaining material is
`43.65 - (38.1 + 10 / 2) = 0.55 mm`. Adding units leaves this last-slot
ligament unchanged. The prescribed 4 mm ear thickness does not increase
this in-plane wall. Bed-edge chamfers remove material and cannot cure it.

Reproduce from `build123d/`:

```sh
PYTHONPATH=. uv run python tools/rack10_ear_probe.py
```

The probe constructs an unchamfered 4 mm plate with the exact six rounded
slots and calls the production `tests.print_audit.audit` without exclusions.
Observed result: minimum wall **0.55 mm, FAIL**; overhang **0°**, bridge
**0 mm**, downward fillets **0**, extent **254 × 43.65 × 4 mm**. The absent
bed chamfer is an expected warning on this diagnostic, not a proposed
production exception. The command exits 1 on the audit failure.

The operator/mayor must revise the contract before modelling continues:
which may change — the slot length, the panel/rail datum for hole centres,
or the panel height? Moving the centres down by half PANEL_SHORT would
balance the nominal top/bottom ligament at 0.95 mm, but changes invariant 4
and still requires checking edge treatment and load-bearing thickness.
Shortening slots while preserving the specified centres is another option;
the nominal 0.9 mm floor alone requires a total length no greater than
9.3 mm, before adding finishing and structural margin.

No registered model, manifest entry, baseline or print-ready artifact has
been produced at this checkpoint. The constants tests only verify the
specified numbers; they do not claim the contradictory geometry is printable.
