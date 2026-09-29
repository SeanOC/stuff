# Multibuild compatibility library

`multibuild/` is a thin adapter over the pinned `opengrid` Multiconnect
cutters (`eea2b4154a10d2909e5edece567cbe0563aaf955`). It ships our own
compatibility code and demo geometry; no official tile or connector assets
are bundled. Source attribution and the publication/licence caveats are in
[research §1](multibuild-research.md#1-system-names-catalogue-and-publication).

## API and mounting datum

```python
from multibuild import slot_cutter, SmallHoleConePin
from multibuild.constants import large_hole_center, small_hole_center

negative = slot_cutter(25, snap=True)
alignment_pin = SmallHoleConePin(fit_per_side=0, tip_diameter=1.8, half_angle=45)
```

`slot_cutter(travel=25, *, snap=False)` accepts positive multiples of 25 mm.
Travel is injected through a `Slot` factory; no dependency globals change.
All head geometry and cutter allowances stay pinned: radii 10/7.5 mm,
axial heights 1+2.5+0.5 mm, radial allowance 0.15 mm, full slot width allowance
0.3 mm, axial corrections +0.212132034/−0.062132034 mm, depth 4.15 mm.
The no-snap form retains the library's paired round seat cutters.

**Datum:** the consumer's back face is Y=0, material is at +Y, and the
negative extends from Y=0 to Y=4.15. The seated head's library transform is
`Pos(x, 4.15, seat_z) * Rot(90, 0, 0)`. The consumer slides **down** onto
flush heads: in the consumer frame the heads enter along +Z from below the
open ends. The seat is above the opening. Standoff is zero. Sean selected
flush connectors threaded into the large holes and offset snap wall mounts;
no extra wall-clearance provision or anti-lift trial is required by this task.
The research's earlier open connector/retention questions are superseded by
those decisions (2026-09-28); the mount contract tests normal pull-off capture,
not release force or load capacity.

Mounts declare `multibuild-multiconnect-slot` and provide
`mount_fixtures(mount_type, values) -> MountFixtures` with cutters, head seat
locations, face normal `(0,-1,0)` and entry axis `(0,0,1)`. Every production
preset inherits insertion, seating and capture checks. See
`multibuild/demo_plate.py` for a minimal example.

`SmallHoleConePin` is optional alignment geometry, independent of the cup-lid
fixture. Positive fit means **interference per side**: base diameter is
7.5 + 2×fit. Fit is −0.3…+0.3 mm, half-angle 30…60°, and the positive tip
must be smaller than the base. Length is `(base-tip)/(2*tan(half_angle))`.
Base is at Z=0, tip at +Z. The conservative cavity inequality includes
2×fit; it does not claim the pin clears the unexpanded mouth with positive
interference. Consumers must choose a printable tip (at least 1.8 mm) and
validate physical fit.

## Provenance

[C] cited claim; [V] checked source arithmetic/implementation; [U] unresolved.
None certifies measured official hardware. Source keys below resolve in
[research §2–3](multibuild-research.md#2-board-dimensions-and-seam-rules).
`constants.PROVENANCE` accompanies every scalar; `LARGE_HOLE_PROFILE`
contains value/status/source/locator records for each field.

| Primitive | Value (mm) | Status and source locator |
| --- | --- | --- |
| Grid pitch | 25 | [C] Core, Measurement System; §1 L29,42 |
| Tile thickness | 6.4 | [C] SCAD L56–61 |
| Small mouth / throat / band | 7.5 / 6 / 2.9 | [C] SCAD L96–104,237–265 |
| Taper depth per face | 1.75 | [V] arithmetic (6.4−2.9)/2, SCAD L270–280 |
| Large octagon mouth / central flats, band | 23.4 / 21.4, 2.4 | [C] SCAD L68–83,218–224,270–280 |
| Large helix outer / inner diameter | 22.6 / 21.4 | [C] SCAD L85–94,228–233 |
| Helix outer / inner axial width, pitch | 0.5 / 1.583, 2.5 | [C] SCAD L85–94,228–233 |
| Large grid phase | (25i+12.5, 25j+12.5) | [V] SCAD L135–162,167–193 |
| Small grid phase, where holes exist | (25i+25, 25j+25) | [V] same coordinate arithmetic |
| Head and cutter allowances above | pinned Python implementation | [V] Python constants L11–15; multiconnect L62–108,188–254 |
| Small-hole thread (not implemented) | pitch 3, outer/inner Ø7/6, axial widths 0.77/2.5 | [C] SCAD L100–104,257–265 |
| Tile edges | Core teeth on two sides, side on one, corner on neither; tooth-side size cells×25+8 | [C] SCAD README, Usage / Tile Stack Sizing |
| Joining and wall offset | Dual Snaps; offset snap mounts 6.25 | [C] Mounting L46–50; Core §2.2 L88 |
| Installed seam clearance | no global allowance established | [U] Mounting steps/images; Core connections |
| Snap seat details | head spacing 0.795, triangle base 8, inset 0.6 | [V] Python multiconnect L260–332; spacing is not board pitch |
| Official head equality / production thread fit | unqualified | [U] research §2–3 |
| Fix-Point variants | Regular mates with hole; Lite with Rail and is 1 mm thinner | [C] Core §11 L238–251 |
| Fix-Point profile / release force | not established | [U] Core §11; sliding removal alone proves no force threshold |

The board records describe a reconstructed **female** hole. Octagonal flats
are not circular thread diameters. `LargeHoleThreadCutter` raises
`NotImplementedError` pending a qualified male/female thread specification;
`FixPointCutter` raises because Multiconnect was selected and Fix-Point's
profile is unresolved. See [research §5](multibuild-research.md).

## Demo and verification

The unregistered 70×100×7 mm plate has two snap slots at x=±12.5, seat Z=24,
with 25 mm channels opening through its bottom. It stands on Z=0, with
0.4 mm 45° relief on all bed edges, including the apertures. Finite wedges
and conical corner joins construct the relief because OCCT's general
chamfer operation fails at the short slot-lip edges. The library pocket
profile above that first-layer relief remains unchanged.

Backing is 7−4.15 = **2.85 mm** (minimum 2.4). Volume before: **N/A (new
artifact)**; final: **44,255.325 mm³**. Thickness is set by the backing rule.
This test artifact has no service-load rating or fused load-bearing joint.
It changes no manifest, baked STL, thumbnail or gallery entry.

Run `uv run --project build123d pytest build123d/tests/test_multibuild.py`.
Tests cover provenance, pin containment at 0.05 mm steps, profile and
allowance drift, watertightness, simultaneous insertion, normal capture,
and the production print audit. **Only the Multiconnect slot pockets** may
require supports in the standing orientation (Sean's accepted exception).
The rest passes the PLA/PCTG audit; the bed relief remains mandatory.
