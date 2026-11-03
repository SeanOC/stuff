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
added. For future general-purpose rack panels, use `panel.finish`. The device
helper preserves existing sloping pad/ramp facets (including 60° facet turns)
and functional roof ridges, then chamfers the remaining right angles; it is
not a drop-in replacement for the general panel finish. Use PETG/PCTG for
loaded equipment in a warm rack; PLA fit prototypes
are useful, but the load calculation below uses PETG stiffness and does not
establish a PLA service rating.

### Cradle, pockets and clamp

`cradle(W,D,H,units,clearance)` checks `tray_dimensions` before construction.
The Steam Machine has 2 mm clearance on each side, a 160 mm inner width,
16 mm rails above its 16 mm perforated rib grid, and a bezel that leaves the complete
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
L-shaped ears connected by a floor strap. Thread zip ties through the
four peaked slots through the 9 mm floor and around the device, clear of connectors and
cooling openings. This does not assume screw holes in the switch housing.
The generic 210 mm body has positive clearance under the actual 222.25 mm
rail opening; 210 mm is the device width, not the mounting flange. The
front flange remains 254 mm. Clamp clearance is 1–2 mm, including for direct
library callers: the 1 mm root blends must stay outside the device envelope. All mounts have a 10 mm rear cable notch.

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
the inset device-zone grid targets 35% open area before reserving the cable-notch
border and applying edge relief.

The rule-of-thumb calculation is deliberately FEA-free. Use a 3 kg load
(29.43 N) at the device centre and PETG **E = 2000 N/mm²**, but transfer the
load through the **two pad rows**, not directly into the beam at the device
centroid. `pad_positions` returns the start of an 8 mm pad top; its centre is
4 mm farther back. For a conservative contact placement, use the front edge
of the front pads and the back edge of the rear pads. The statics are
`R_rear = F × (z_cg − a_front)/(a_rear − a_front)` and
`R_front = F − R_rear`. The symmetric contacts give 14.715 N per row.

The fore-aft section counts **every** internal 3 mm longitudinal web, plus
the two continuous solid side bands outside the vents. For the Amp this is
18 internal webs and two 16.0742 mm bands, after deducting 0.3 mm edge relief
at each side-band boundary. Subtract 0.6 mm from the 17 mm section depth:
`I = (18×3 + 2×16.0742) × 16.4³/12 = 31666.32 mm⁴` (rounded).
Cross ribs, flange, lip, pads and surplus internal-web width are excluded
from this fore-aft calculation. `longitudinal_sections` supplies the disjoint
rectangles, and endpoint tests intersect **all** of them with the actual
BREP to prove that the counted material exists and is not counted twice.

For a point reaction P at a, the cantilever deflection farther back at x is
`δ(x) = P a² (3x − a)/(6 E I)`. **Sum the front and rear reactions** and
report both the rear contact and the actual free deck tip. The separate
transverse case still uses only the two 20 mm cross ribs and the conservative
254 mm span: `δ = F L³/(48 E I_transverse)` with
`I_transverse = 2×20×16.4³/12`.

| Case | Front/rear contact Z | Deck tip Z | Rear-contact deflection | Tip deflection | Transverse |
| --- | --- | --- | --- | --- | --- |
| Sonos, stops on, D=217 | 6.167 / 220.833 | 236 | 0.835 mm | 0.921 mm | 0.342 mm |
| Longest/widest, stops off, W=217 D=220 | 6 / 224 | 239 | 0.892 mm | **0.981 mm** | 0.342 mm |

`beam_deflections` takes explicit keyword arguments for **device width and
depth, deck width and deck depth**; it rejects a deck depth that ends before
the rear contact. The tests cover the width/depth endpoints, middle examples
and both stop settings. The additional longest, widest, no-stops corner also
runs the production audit and the physical section probes. Both load cases
stay ≤1 mm in this model; the free-tip cantilever case governs. These are
elastic section estimates, not a tested load rating: layer adhesion, creep,
actual infill/perimeters, ear fasteners and equipment temperature remain part
of physical validation. Print load-bearing ribs solid and check sustained
deflection with a dummy load before installing equipment.

### Cradle, clamp and hub stiffness

`rack10/stiffness.py` pins these four **[C]** load constants. The two hub
values are explicitly substituted design loads, not measured equipment
masses (mayor, stiffness task rev 2, 2026-11-03).

| Device | Load input | Provenance |
| --- | --- | --- |
| Steam Machine | [C] 2.6 kg | Original device-mount task equipment list, Sean 2026-11-02 23:25Z; also specified by the stiffness task. |
| USW-Lite-16-PoE | [C] 1.2 kg | [Ubiquiti technical specifications](https://techspecs.ui.com/unifi/switching/usw-lite-16-poe), Mechanical → Weight. |
| Lutron L-BDG2 | [C] 0.5 kg | Mayor substitute design load, pst-3fob4 rev 2. |
| Aqara Hub M3 | [C] 0.5 kg | Mayor substitute design load, pst-3fob4 rev 2. |

The generic cradle uses the same 2.6 kg test load; the wide-box clamp uses
1.2 kg. Both remain fit examples rather than separately weighed equipment.
All estimates assume the equipment's centre of gravity at its geometric
centre, level front rails providing an ideal clamp, and symmetric loading
left/right. Cable forces, mount self-weight, fastener compliance, impact and
asymmetric centres of gravity are not included in this shelf-style proxy.

For material sensitivity, [Extrudr's PCTG technical data sheet](https://s3.extrudr.com/extrudr-media/datasheets/tds/tds-en/pctg-TDS-en.pdf)
(2025-06-26, section 3) lists a flexural modulus of 1650 MPa. This is a
short-term material input, not a measured modulus for these
front-down prints or a sustained-load rating. The shelf's 2000 MPa PETG
assumption remains unchanged. The calculation accepts either modulus and
tests both; PCTG governs because it is the lower value.

**Sections and reactions.** The cradle uses a 16 mm perforated deck and
32 mm total side rails. Its open fraction and four pads are retained. The
clamp uses a 9 mm floor and 21 mm total side rails; its tie slots extend
through the thicker floor. The hubs use a 3.8 mm floor and three 20 mm rails.
Their front faces and rear cable access remain open. The hub bezel's top
beam is 2.2 mm thick, preserving the M3's original 1.15 mm nominal head
clearance as the floor rises. These changes leave the Sonos geometry/helpers untouched.

As for the shelf, `R_rear = mg (z_cg-a_front)/(a_rear-a_front)` and
`R_front = mg-R_rear`. The cradle uses the outer edges of its actual 8 mm
pad tops. The clamp and each hub use the outer front/rear device edges as
conservative contact lines, because their feet are not specified. Each
row carries half the load and each side carries half the row reaction:
6.3765 N per cradle pad, 2.943 N per clamp corner, and 1.22625 N per hub
corner. These are modelled reactions, not measured foot forces.

For longitudinal bending, the cradle counts the continuous webs and side
bands between the vent cutters, plus its two side rails. The clamp counts
the floor bands remaining after excluding tie-slot and rear-notch X ranges
along the **entire** length, plus its side rails. Both remove 0.3 mm edge
relief on each boundary and discard any residual floor band narrower than
the 1.6 mm load-bearing minimum. The composite neutral axis is area-weighted:
`y_bar = sum(A_i y_i)/sum(A_i)` and
`I = sum(b_i h_i^3/12 + A_i (y_i-y_bar)^2)`.
The hubs count **only** their rails; each pocket owns one outside rail and
half the centre divider, so unequal depths do not borrow the other's
stiffness. The half-divider rectangles are accounting partitions of a
2.4 mm physical wall, not thin manufactured ribs.
The divider is probed through the rear contact, where bending moment ends;
the rear notch can interrupt it farther back in the unloaded cable tail.
The outside rail is probed all the way to the tip and carries that tail at
the rear contact's slope. No divider material in the tail is credited.

The point-load formula is the shelf's, summed over both contact rows:
`delta(x) = sum(P a^2 (3x-a)/(6 E I))` for `x >= a`. Report the rear
contact and the actual free deck tip, including the hubs' cable-comb tail.
`test_endpoint_audit_and_edges` intersects every credited longitudinal
rectangle with the finished BREP and verifies full volume and no overlap.

Transverse bending is checked separately. The cradle's solid front/rear
cross bands include the two contact lines; the clamp uses 20 mm strips at
its contact rows. The rear notch interrupts these bands, so each half is
treated as a side-rail cantilever, with half the row load at the centreline:
`delta = (R_row/2) (inner_width/2)^3/(3 E I_strip)`. This is more severe
than corner pads/feet. The hubs use two 19.4 mm cross strips before their
cable apertures; for each pocket, `delta = mg L^3/(48 E I_strips)` between
its rail centres. Every transverse strip is also BREP-probed.

| Preset / pocket | Front / rear contact Z, mm | Tip Z, mm | PETG tip, mm | PCTG rear / tip / transverse, mm |
| --- | --- | --- | --- | --- |
| Steam Machine | 6.075 / 166.325 | 169.4 | 0.388 | 0.457 / 0.470 / 0.337 |
| Generic 3U cradle | 6 / 164 | 167 | 0.357 | 0.421 / 0.433 / 0.366 |
| USW-Lite-16 | 4 / 189 | 190 | 0.486 | 0.585 / 0.589 / 0.549 |
| Wide 210 mm clamp | 4 / 174 | 175 | 0.356 | 0.428 / 0.432 / 0.717 |
| Lutron pocket | 4 / 74 | 142 | 0.241 | 0.123 / 0.292 / 0.241 |
| Aqara pocket | 4 / 109 | 142 | 0.469 | 0.391 / 0.569 / 0.765 |

The parameter-corner calculation stays below the copied **1 mm** criterion
for both materials. Governing PCTG cases are the narrow/deep cradle
(W=140, D=200, clearance=1): **0.883 mm** tip; narrow/deep clamp
(W=140, D=200, clearance=2): **0.927 mm** tip; and widest hub pocket
(W=110): **0.875 mm** transverse. The widest/deepest cradle at minimum
clearance has 0.811 mm transverse deflection, and is a separate BREP/audit
case. Presets, numeric endpoints, asymmetric hub pockets and named corners
run both the production print audit and exposed-edge classifier.

The hub's centred rear notch stays at least 10 mm wide. Where a pocket
divider approaches it, the notch widens only in the unloaded tail to avoid
a thin remnant of the divider's root blend; the loaded rail interval and
device pockets remain intact. Two additional widths exercise the notch
transition, and the wide/deep pocket case exercises the widened notch.

| Preset | Previous volume, mm³ | Stiffened volume, mm³ | Change |
| --- | ---: | ---: | ---: |
| Steam Machine | 108015.029 | 324956.039 | +200.8% |
| Generic 3U cradle | 94213.836 | 314759.236 | +234.1% |
| USW-Lite-16 | 138286.326 | 367301.406 | +165.6% |
| Wide 210 mm clamp | 127553.155 | 357288.235 | +180.1% |
| Two-hub tray | 97555.390 | 128778.958 | +32.0% |

The cradle's deeper open grid supplies transverse stiffness while taller
side rails avoid a still thicker floor. The clamp's continuous floor keeps
support under unspecified device feet and the tie slots; its thickness
governs the transverse check. The hubs retain a thin floor and gain most of
their longitudinal stiffness from the three narrow rails. The increases
replace the earlier fit-only sections with sections meeting the stated
elastic criterion; they are not claims of an optimised structural design.

**Physical validation remains pending.** These are instantaneous elastic
predictions for solid counted sections, using nominal material properties;
the front-down layer stack has not been mechanically characterised. Neither
a datasheet HDT nor these moduli establish a permissible rack temperature,
creep duration, or sustained load rating. Print the counted sections solid.
Before installing equipment, record filament/lot, slicer settings, actual
contact positions and rack temperature, then measure rear-contact and tip
sag under dummy loads initially, after sustained loading, and after unloading.
Use the <=1 mm criterion and inspect for residual deformation. Test duration
and maximum service temperature need to be set and recorded for the actual
rack. Alternatively, the task permits explicit acceptance of these predicted
values and their limitations; no such acceptance or prototype result is
recorded yet.

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
