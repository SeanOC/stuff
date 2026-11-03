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

## Device mounts

The four device families are original geometry for `pst-go6df.2` (plan
review PASS). Dimensions marked **[C]** are cited, not physical fit tests.

| Model / preset | Device W × D × H mm | Allocation | Source |
| --- | --- | --- | --- |
| rack10-cradle / steam-machine | 156 × 162.4 × 152 with feet (148 without) | 4U | [C] task equipment list; [Valve hardware](https://store.steampowered.com/hardware/steammachine) |
| rack10-cradle / generic-3u | 160 × 160 × 100 | 3U | Original parametric example |
| rack10-shelf / sonos-amp | 217 × 217 × 64 | 2U | [C] task equipment list; [Sonos Amp guide](https://www.sonos.com/en-us/guides/amp) |
| rack10-shelf / 2u-plain | 180 × 180 × 50 | 2U | Original parametric example |
| rack10-hub-tray / caseta-aqara-m3 | 70 × 70 × 30.23; 105 × 105 × 36.5 | 1U | [C] [Lutron specifications, dimensions](https://www.lutron.com/TechnicalDocumentLibrary/369816_Smart_Bridge_Pro_Spec.pdf); [Aqara M3 specifications](https://www.aqara.com/us/product/hub-m3-specs/) |
| rack10-ears / usw-lite-16 | 192 × 185 × 44 | **2U** | [C] [Ubiquiti specifications, dimensions](https://techspecs.ui.com/unifi/switching/usw-lite-16-poe) |
| rack10-ears / wide-box-210 | 210 × 170 × 31 | 1U | Original wide-box example; not a USW-Lite-16-PoE |

The two initially approximate equipment sizes were checked against vendor
specifications on 2026-11-03. The M3 is wider and shorter than the initial
estimate; its corrected envelope fits 1U. The switch is narrower and taller:
Ubiquiti's older datasheet gives 191.7 × 185 × 43.7, rounded to 192 × 185 ×
44 on the current specification page. Both heights require **2U** once the
3 mm support floor and clearance are included. The 210 mm generic preset
remains available separately. Lutron's 69.9 mm width/depth are rounded up to
70 mm for the pocket; its 30.23 mm height fits the same 1U envelope.

All four generators use the shared EIA panel/ear datums and slot option.
They print **front face down**, with +Z pointing to the rear of the rack.
Their floors, pocket rails and ribs grow from the face already on the bed.
Vents and enclosed cable slots have 45-degree peaked ceilings. The vent
areas derive from `vent_pattern`; stretching the grid to roughly 40 mm row spacing in the depth direction produces fewer, longer
slots; a peaked ceiling preserves the requested area fraction. The roof ridges are functional and remain sharp because
chamfering them would introduce horizontal ceilings. Other exposed right
angles receive 0.3 mm chamfers; device pads have sloping sides, and continuous
floor/rail joints receive 1 mm root blends (fillets on the cradle/clamp,
45-degree chamfers on the hub dividers). No print-audit exceptions are
added. Use PETG/PCTG for loaded equipment in a warm rack; PLA fit prototypes
are useful, but the load calculation below uses PETG stiffness and does not
establish a PLA service rating.

### Cradle, pockets and clamp

`cradle(W,D,H,units,clearance)` checks `tray_dimensions` before construction.
The Steam Machine has 2 mm clearance on each side, a 160 mm inner width,
8 mm low rails above its 3 mm floor, and a bezel that leaves the complete
front face exposed. The rear remains open. Four 1 mm pads support the device
with or without its own feet; the fit envelope includes its feet. Pad seats
and the rear cable notch are reserved from the vents. The test measures the
actual through-area under the device, requiring at least 40% after pad seats
and finishing. The same geometry supports the smaller 3U preset.

`hub_tray(left_w,left_d,right_w,right_d)` provides 1 mm clearance on each
pocket side, an independent rear stop and peaked cable opening behind each
hub, and a rear comb with 7 mm slots. The pockets open at the front; put the
M3 there with its IR/status face pointing out. Keep RF devices outside metal
enclosures and route their cables behind the pockets. Heights are the fixed
30.23 mm Lutron and 36.5 mm Aqara envelopes; width/depth are adjustable.

`ears(W,D,H,units,clearance)` implements the **clamp-style** option: two low
L-shaped ears connected by a floor strap. Thread retaining ties through the
four peaked floor slots and around the device, clear of connectors and
cooling openings. This does not assume screw holes in the switch housing.
The generic 210 mm body has positive clearance under the actual 222.25 mm
rail opening; 210 mm is the device width, not the mounting flange. The
front flange remains 254 mm. All mounts have a 10 mm rear cable notch.

### Sonos shelf and rib calculation

A Sonos Amp cannot use the cradle: `217 + 2×1 + 2×2.4 = 223.8 mm`, above the
220.25 mm tray limit. The shelf has no continuous tall side rails. Its front
flange spans the 254 mm ear width; behind the flange the deck fits the rail
opening. Optional **5 mm side stops** have 1.6 mm walls and 219 mm between
them for the Amp. Their outside width is 222.2 mm, just inside the 222.25 mm
opening. This is deliberately a tighter fit than the tray margin: measure
or print a short fit section for the chosen rails, or disable `side_stops`.
With stops disabled the deck is 220.25 mm wide. Four 1 mm pads raise the Amp
above the deck, and a split rear lip leaves the cable notch open. The 2.1 kg
Amp's front, back and top remain unobstructed.

The shelf uses a 3 mm perforated deck over a **14 mm deep rib grid**. The openings continue through the ribs, leaving continuous webs in
both bending directions. This avoids suspended underside ribs and keeps
printing support-free. A full solid slab of this height is unnecessary:
vent cells remove 35% of the inset device-zone area before edge relief.

The rule-of-thumb calculation is deliberately FEA-free. Use a 3 kg point
load (29.43 N), PETG elastic modulus **E = 2000 N/mm²**, and ignore the front
flange, pad seats, rear lip and surplus ribs. At every exposed width/depth,
there are at least eight longitudinal webs, each conservatively 3.0 mm wide
after finishing, and two unperforated 20 mm cross ribs at the front and rear
(the rear rib ends before the notch). Subtract 0.6 mm from the 17 mm depth
for edge relief. Thus:

- Fore-aft section: `I = 8 × 3.0 × 16.4³ / 12` mm⁴. The front rails support
  a cantilever; for a device-centre arm `a = D/2 + 5`, use
  `δ = F a³ / (3 E I)`.
- Transverse section: `I = 2 × 20 × 16.4³ / 12` mm⁴. Conservatively use the
  complete **254 mm** ear span and `δ = F L³ / (48 E I)`.

`beam_deflections` evaluates both and the tests require ≤1 mm, including
D=220 mm. The cantilever case governs this conservative calculation. These
are elastic section estimates, not a tested load rating: layer adhesion,
creep, actual infill/perimeters, ear fasteners and equipment temperature
remain part of the physical validation. Print load-bearing ribs solid and
check sustained deflection with a dummy load before installing equipment.

### Proposed corrected 12U elevation and cables

The corrected switch height uses the former U9 vent allocation. This keeps
the same 12U overall height and the hubs/keystone at their planned positions.

| Bottom → top | Part |
| --- | --- |
| U1 | Selected 10-inch PDU; bracket deferred until the PDU is chosen |
| U2–U5 | rack10-cradle / steam-machine |
| U6 | rack10-blank-panel / 1u-vented |
| U7–U8 | rack10-shelf / sonos-amp |
| U9–U10 | rack10-ears / usw-lite-16 (corrected 2U envelope) |
| U11 | rack10-hub-tray / caseta-aqara-m3 |
| U12 | rack10-keystone-panel / 1u-6-keystones |

Power and incoming network enter from the **back** through the mounts'
notches. HDMI and the TV network cable leave along the **right inside wall**:
use the Underware I-channel in the approximately 30 mm side gap. Keep
connector bend radii clear behind the devices. The shelf reaches 236 mm
behind its front face, so the chosen 240 mm frame leaves very little rear
cable room for the Amp; connectors must exit into the rear/side channel,
not against a closed back panel. Frame, rail strips, PDU bracket and planner
remain outside these models.

Device validation lives in `tests/test_rack10_devices.py`: preset topology
and STL watertightness, device-envelope intersections, cradle open fraction,
fit rejection, the two load cases, and production audits plus an exposed-edge
classifier at every numeric endpoint and documented corner. Unbuildable
1U switch/3U full-height Steam Machine combinations and over-wide hub pockets
raise named fit errors. No geometry baseline is reused from a different
model; new preset rows carry this task's plan-review provenance.
