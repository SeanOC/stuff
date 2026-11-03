# Rack10 panels and trays

Original build123d geometry to the project's de facto 10-inch rack interface.
No formal 10-inch standard is claimed, and no upstream model geometry is
ported. `rack10/` provides reusable negative tools, panels and trays;
`holders/rack10_*.py` registers the three gallery models in Storage.

## Interface and provenance

**[C]** means a cited dimension, not a measurement of a physical print.
The controlling interface is task `pst-go6df.1`, **CANONICAL rev 1**
(2026-11-02). The named assignments in
[openRack's rack_units.scad](https://github.com/dduxx/openRack/blob/main/scad/lib/rack_units.scad)
corroborate the rack unit, hole pitch, boundary offset, panel width,
cage square and three-hole count. No upstream source is committed.

| Constant | Value (mm unless noted) | Provenance |
| --- | --- | --- |
| RACK_UNIT / HOLE_PITCH / HOLE_EDGE | 44.45 / 15.875 / 6.35 | [C] E1; openRack RACK_UNIT / RACK_UNIT_HOLE_SPACING / RACK_UNIT_HOLE_BOTTOM_EDGE_OFFSET |
| EAR_WIDTH / HOLE_SPAN | 254 / 236.525 | [C] E1; openRack TEN_INCH_STANDARD_WIDTH corroborates width only |
| CLEAR_OPENING / USABLE_WIDTH | 222.25 / 210 | [C] E1 |
| CAGE_SQUARE | 9.525 | [C] E1; openRack RACK_SQUARE_HOLE_XY |
| PANEL_SHORT / SCREW_CLEAR | 0.8 / 6.4 | [C] E1; SCREW_CLEAR is nominal M6 clearance, actual holes use EAR_HOLE_D |
| EAR_HOLE_D / MAX_SLOT_MM | 7 / 8 | [C] E1 rev 1 |
| PANEL_THICKNESS / EAR_THICKNESS | 3 / 4 | [C] E1 |
| HOLES_PER_UNIT | 3 (count) | [C] E1; openRack HOLES_PER_UNIT |
| TRAY_SIDE_MARGIN / TRAY_OUTER_WIDTH_LIMIT | 1 / 220.25 | [C] E1 fit cap and clear opening |
| KEYSTONE_WIDTH / KEYSTONE_HEIGHT / KEYSTONE_PITCH | 14.5 / 16 / 19 | [C] E1 |
| MAX_KEYSTONES | 11 (count) | [C] floor(210 / 19) |
| KEYSTONE_LATCH_WALL | 2.5 | [C] [rack-build, 1U keystone panel](https://github.com/davidwkeith/rack-build#3-1u--24-port-keystone-patch-panel) |
| KEYSTONE_RELIEF | 1.6 per end | [C] derived rear height: (19.2 − 16) / 2; [Delock 67068 port height](https://www.delock.com/produkt/67068/merkmale.html) |
| MIN_WALL_MM / EDGE_CHAMFER / PANEL_CORNER | 0.9 / 0.3 / 4 | [C] repository design guidelines §1 |
| RAIL_WALL / FLOOR / RAIL_HEIGHT | 2.4 / 3 / 8 | Original design dimensions, not hardware interface measurements |
| TIE_WIDTH / TIE_LENGTH | 3 / 8 | Original design dimensions; peaked ceiling rises at 45° |

The specified HOLE_SPAN is 236.525 mm (approximately 9.312 inches), whereas
9.3125 inches is 236.5375 mm. The explicit millimetre value is retained.
The eventual frame needs an ear fit check, particularly if a HomeRacker or
DeskPi frame is chosen instead of the proposed extrusion frame. Keystone
latch dimensions vary between products: the nominal front window and rear
clearance pocket are original geometry combining the cited dimensions;
verify the chosen jack with a fit print before printing the complete panel.

## Datum and generators

All parts use X across the rack, Y upwards from the **physical panel bottom**,
and Z rearwards from the front face. They print with the front face at Z=0.
The panel is centred in its U allocation, 0.4 mm inboard at each end.
Hole centres remain 6.35 / 22.225 / 38.1 mm from the **U boundary**, hence
5.95 / 21.825 / 37.7 mm from a 1U panel's bottom. `panel(1)` is 43.65 mm tall.
The default holes are round Ø7; `slot_mm=8` gives a vertical 7 × 8 slot
and symmetric 1.95 mm nominal end ligaments. `slot_mm=9` raises a named
`ear ligament` error. Zero selects round holes; nonzero values must be 7–8.
Every profile also checks the actual ligament against 0.9 mm.

- `ear_profile(units, slot_mm=0)` returns the negative sketch for both ears,
  three holes per U per ear. Hole span and overall width stay constant.
- `panel(units, width_between_ears=None, slot_mm=0)` returns the complete
  plate. The optional width controls the central 3 mm region between 4 mm
  ear pads (210–222.25 mm), leaving mounting datums fixed. The reusable
  generator accepts 1–7U; the registered blank exposes 1–2U.
- `vent_pattern((width, height), open_fraction)` returns a centred grid of
  through-cutters. Nominal open area equals the requested fraction before
  chamfering. Zero is solid; fractions up to 0.5 are accepted when all
  apertures are 2–10 mm and webs retain at least 1.8 mm after finishing.
  The registered panel uses 0.35 over an inset ventilation area.
- `keystone_cutout()` returns a 14.5 × 16 mm through-window with a rear latch
  relief; `keystone_row(n)` centres 1–11 of them at 19 mm pitch. Each port has
  a continuous opening. Mating edges retain their profile; bed entrances
  receive elephant-foot relief.
- `tray(device_w, device_d, device_h, units=None, clearance=1.0)` creates an
  open-rear tray with a floor, tapered side webs and front panel with ears.
  `units` defaults to `ceil((device_h + 2*clearance + FLOOR)/RACK_UNIT)`;
  the actual shortened panel must still enclose that height. Insufficient
  height raises `TrayFitError`. Optional `front_cutouts` contains
  `(x, y, width, height)` windows retaining a 3 mm frame inside the tray.
  `slot_mm` also applies to trays.

The tray fit rule is `device_w + 2*clearance + 2*RAIL_WALL <= 220.25`.
The cap is independent of clearance. Total width 220.24 passes and 220.26
raises `TrayFitError`. Clearance is 0.5–2 mm; the registered device envelope
is 40–213.45 mm wide, 40–200 mm deep and 10–72 mm high, subject to that fit
rule. In particular, maximum width plus maximum clearance is rejected;
211.45 mm is the reachable maximum width at 2 mm clearance.

## Presets and fit examples

| Model / preset | Device W × D × H (mm) | U | Tray outer width / print depth (mm) |
| --- | --- | ---: | --- |
| blank / 1u-solid | — | 1 | — |
| blank / 1u-vented | — | 1 | — |
| blank / 2u-vented | — | 2 | — |
| keystone / 1u-6-keystones | six ports | 1 | — |
| keystone / 1u-max | eleven ports | 1 | — |
| tray / apple-tv-4k | 98 × 98 × 31 | 1 | 104.8 / 103 |
| tray / switch-8-port | 160 × 100 × 28 | 1 | 166.8 / 105 |
| tray / mini-pc-nuc | 117 × 112 × 51 | 2 | 123.8 / 117 |

These are fit examples, not measured device-specific mounts or tested load
ratings. The shelf's worst load is gravity along −Y, bending the floor away
from its front panel. Side webs overlap the front by the full 3 mm panel
thickness and the floor by its full thickness; 1 mm root fillets blend the
front, floor and side junctions. The webs end 2 mm below the front rim to
permit robust edge treatment at the joint. PLA or PCTG is intended; choose
material for the equipment's temperature and load before service.

Every part prints front face down in one piece. Rounded outer corners and
0.3 mm bed chamfers finish the panel; the tray grows upwards from it.
Zip-tie slots have 45° peaked ceilings. Their functional aperture edges and
keystone latch edges are retained; other exposed sharp edges are chamfered.
No audit exclusions are declared. All presets fit the common 305 × 320 ×
320 mm single-nozzle volume shared by the H2S and H2C.

## Validation

From `build123d/`:

```sh
uv run python -m bd audit rack10-blank-panel --preset 2u-vented
uv run python -m bd audit rack10-keystone-panel --preset 1u-max
uv run python -m bd audit rack10-tray --preset mini-pc-nuc
uv run pytest tests/ -q -n 4 -k rack10
PYTHONPATH=. uv run python tools/rack10_ear_probe.py
```

`tests/test_rack10.py` tests datums, physical openings, fit boundaries,
watertight single-solid presets, shared printer envelope, and every numeric
endpoint plus each preset and the documented reachable corners. Its
`assert_finished_edges` classifies exposed edges and explicitly recognises
periodic surface seams and functional apertures. Production audit rows and
per-preset volumes are reported in the PR; geometry baselines record the new
presets with this task's plan-review provenance.
