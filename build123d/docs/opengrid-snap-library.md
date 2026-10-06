# Positive openGrid snap library

`opengrid_snap.snap(lite=True, directional=False)` returns one watertight
build123d Part. This is the CC BY-NC-SA 4.0 port of David D's openGrid design,
OpenSCAD by metasyntactic, from QuackWorks `openGrid/opengrid-snap.scad` at
`6123129` plus local patch `0001-opengrid-snap-linear-extrude-click-holes.patch`.
The patch replaces click-hole cuboids with equivalent extruded rectangles;
vendor fingerprint `6123129+patches-0244598ecb92`. Sean's 2026-10-05 HARD-RULE
exception permits this port because the pinned `opengrid` library has no
positive snap. See [provenance and licence](provenance.md).

## Coordinates and consumption

The 24.8 × 24.8 mm **core** is centred in XY. Z=0 is the click-nub side,
the bed when printed snaps-down; +Z points into the body it mounts.
The four click nubs stand 0.4 mm outside the core: overall dimensions are
25.6 × 25.6 × 3.4 mm (lite), or 25.6 × 25.6 × 6.8 mm (full).
Directional lite is 26.0 × 25.6 × 3.4 mm, with +X the front. Its front nub
stands 0.8 mm proud, so the overall box is asymmetric about X=0.
Both flags may be combined. The four committed parity references are lite,
full, directional lite and directional full (26.0 × 25.6 × 6.8 mm).

A consumer puts its back face at `z = h - 0.02` and fuses the snap into it,
as used by `build123d/holders/cartridge_holder.py` (the OC4b port):

```python
from build123d import Align, Box, Pos
from opengrid_snap import snap

h = 3.4  # lite; 6.8 for full
body = Pos(0, 0, h - 0.02) * Box(30, 30, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
part = snap() + body
```

The port fuses the nub roots directly. It needs none of the SCAD consumer's
0.3 mm weld shims. The isolated-snap fit helper in `tests/mount_contracts.py`
is deliberately unregistered; OC4b supplies consumer fixtures and registration.
The pinned `opengrid` @`eea2b41` `BaseSnapSlotCutter` (`base.py:92`) constructs
the minimum opening as 28 − 2 × (1.1 + 0.4) = 25.0 mm. `Base` (:214) subtracts
it and `base_1x1` (:399) uses the default Base. The core therefore has 0.10 mm
clearance on each side; this is derived, not a published clearance constant.

## Constants [C]

All locators below refer to the patched, line-stable
[upstream file](https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad).
Dimensions are millimetres unless the name denotes a scale. Rounding values
are BOSL2 corner chamfers with `$fn=2`, not smooth corner fillets.

| Constant | Value | Line |
| --- | ---: | ---: |
| `CORE_WIDTH` | 24.8 | 37 |
| `FULL_EXTRA` | 3.4 | 38 |
| `LITE_HEIGHT` | 3.4 | 39 |
| `CORE_HEIGHT` | 3.0 | 42 |
| `TOP_HEIGHT` | 0.4 | 43 |
| `TOP_NUB_HEIGHT` | 1.1 | 44 |
| `TOP_CORNER` | 3.262743 | 48 |
| `CORE_CORNER` | 4.81837 | 50 |
| `TOP_NUB_OFFSET` | 2.02 | 52 |
| `TOP_NUB_WIDTH` | 6.817 | 55 |
| `OVERLAP` | 0.01 | 26 |
| `NUB_TOP` | 2.0 | 26 |
| `NUB_HEIGHT` | 0.2 | 62 |
| `NUB_WIDTH` | 11.0 | 63 |
| `NUB_DEPTH` | 0.4 | 64 |
| `NUB_TOP_WEDGE` | 0.6 | 65 |
| `NUB_BOTTOM_WEDGE` | 0.6 | 66 |
| `NUB_ROUND_X` | -12.36 | 67 |
| `NUB_ROUND_SCALE` | 1.36 | 68 |
| `NUB_ROUND_RADIUS` | 13.025 | 69 |
| `BOTTOM_WEDGE_DEPTH` | 0.4 | 30 |
| `FRONT_HEIGHT` | 0.0 | 77 |
| `FRONT_WIDTH` | 14.0 | 78 |
| `FRONT_DEPTH` | 0.8 | 79 |
| `FRONT_TOP_WEDGE` | 1.0 | 80 |
| `FRONT_BOTTOM_WEDGE` | 0.4 | 81 |
| `FRONT_ROUND_X` | -11.75 | 82 |
| `FRONT_ROUND_SCALE` | 1.26 | 83 |
| `FRONT_ROUND_RADIUS` | 13.025 | 84 |
| `FRONT_BOTTOM_SHIFT` | -0.4 | 85 |
| `REAR_HEIGHT` | 0.65 | 91 |
| `REAR_WIDTH` | 10.8 | 92 |
| `REAR_DEPTH` | 0.4 | 93 |
| `REAR_TOP_WEDGE` | 0.6 | 94 |
| `REAR_BOTTOM_WEDGE` | 0.6 | 95 |
| `REAR_ROUND_X` | -12.41 | 96 |
| `REAR_ROUND_SCALE` | 1.37 | 97 |
| `REAR_ROUND_RADIUS` | 13.025 | 98 |
| `CLICK_OFFSET` | 1.0 | 105 |
| `CLICK_DEPTH` | 0.6 | 107 |
| `CLICK_WIDTH` | 12.4 | 107 |
| `CLICK_RADIUS` | 0.3 | 107 |
| `CLICK_ROOF` | 2.8 | 107 |
| `REAR_CLICK_START` | 0.599 | 110 |
| `REAR_CLICK_HEIGHT` | 2.2 | 110 |
| `REAR_CLICK_OFFSET` | 1.2 | 111 |
| `REAR_CLICK_RISE` | 0.6 | 111 |
| `REAR_CLICK_SHIFT` | 0.2 | 111 |
| `REAR_RELIEF_OFFSET` | 0.1 | 112 |
| `REAR_RELIEF_DEPTH` | 0.2 | 112 |
| `REAR_RELIEF_WIDTH` | 20.0 | 112 |
| `REAR_RELIEF_HEIGHT` | 0.6 | 112 |
| `WALL_CLICK_HEIGHT` | 2.2 | 117 |
| `WALL_CLICK_DEPTH` | 1.4 | 119 |
| `WALL_CLICK_WIDTH` | 12.0 | 119 |
| `WALL_CLICK_THICKNESS` | 0.4 | 119 |
| `INDICATOR_X` | 9.5 | 122 |
| `INDICATOR_BOTTOM_RADIUS` | 2.0 | 122 |
| `INDICATOR_TOP_RADIUS` | 1.5 | 122 |
| `INDICATOR_HEIGHT` | 0.4 | 122 |

## Verification and published print inventory

The four unmodified derived meshes and their generation commands, engine
version and SHA256 hashes are committed in
[`assets/opengrid-snap/NOTICE`](../../assets/opengrid-snap/NOTICE). No QuackWorks
source is committed. Those SCAD meshes are non-manifold at the nub roots;
tests check their bounds, volume and surface distances, never watertightness.
The port must be one valid watertight solid with deterministic STL bytes.
Its unchanged analytic faces are sewn in geometric order so boolean traversal
order cannot change native STL triangle ordering.

Parity limits: bounds within 0.05 mm, volume within 1%, sampled surface distance
within 0.15 mm. Port → reference is raw. Reference → port excludes only samples
whose ±0.05 mm normal offsets both lie inside the port. The excluded fraction
must be <12% with fixed 15,000 area-weighted samples and seed 1. Every excluded
point must lie within 0.05 mm of |X|=12.4, |Y|=12.4, or one of the four
diagonal core planes |X|+|Y|=19.98163 (source :50, :52–56).
This removes the source's internal contact surfaces without hiding outer errors.

The production per-face wall, overhang, bridge and downward-fillet primitives
run snaps-down on all four flag combinations. These published mating features cannot be
thickened or chamfered without breaking fit with the openGrid tile and the
author's own snaps. Generic holder thresholds do not apply to the whole snap.
The inventory is exact in both directions: neither extra misses nor removal
of a published feature is permitted. Thickness tolerance is 0.01 mm; no sampled
face may be thinner than 0.40 mm. Reference ray probes check the same buckets. The following two tables describe
the nondirectional variants; directional inventories follow separately.

| Thin-wall region | Thickness | Lite faces | Full faces | Source lines |
| --- | ---: | ---: | ---: | --- |
| Top-plate underside ledges | 0.41 | 8 | 8 | 43, 48 (0.4 + 0.01 overlap) |
| Click-hole roofs to top | 0.60 | 4 | 4 | 103–107 |
| Outer ligaments, 11.7 to 12.4; full adds lower hole faces | 0.70 | 4 | 8 | 103–107 |
| Wall click-hole roofs to top | 0.80 | 4 | 4 | 115–119 |

| Downward face set | Lite/full count | Angle | Lite Z (full adds 3.4) | Source lines |
| --- | ---: | ---: | ---: | --- |
| Bottom click-nub undersides | 4 / 4 | 90° | 0.19 | 26–30, 58–72 |
| Click-hole roofs | 4 / 4 | 90° | 2.8 | 103–107 |
| Wall click-hole roofs | 4 / 4 | 90° | 2.6 | 115–119 |
| Top-plate underside ledges | 8 / 8 | 90° | 2.99 | 43, 48, 50 |

The production audit measures a maximum local bridge of 0.5 mm and zero
downward fillets for both nondirectional variants. These are source-compatible inventories,
not a claim that the snap passes the holder's generic 0.9 mm / 45° thresholds.

### Directional mating exceptions

The directional contract preserves the pinned front/rear nubs, rear relief,
click holes and indicator. The exceptions below apply only to the exact face
sets in [`tests/opengrid_snap_inventory.py`](../tests/opengrid_snap_inventory.py),
not an enclosing box or a four-quadrant symmetry fold. Every listed face must
exist exactly once with its measured wall/angle/local-bridge result; every
unlisted face must meet 0.9 mm / 45° and have no sampled local bridge. The tests
also require zero downward curved faces. Geometry and fit are unchanged.

All source locators in these tables refer to
[`opengrid-snap.scad@6123129`](https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad),
with the line-neutral local patch recorded in NOTICE. +X is front, −X rear,
±Y the two standard sides. Each count is a BRep face count, not an STL triangle
count. Wall values are the production normal-ray proxy with a 3 mm cap.

| Thin-wall face set | Production mm, lite / full | Lite / full count | Reference first-hit mm | Source lines |
| --- | ---: | ---: | ---: | --- |
| Top-plate underside ledges | 0.41 / 0.41 | 8 / 8 | 0.41 | 43, 48, 50 |
| Side click-hole roofs | 0.60 / 0.60 | 2 / 2 | 0.60 | 103–107 |
| Rear click-hole roof | 0.601 / 0.601 | 1 / 1 | 0.601 | 110 (0.599 + 2.2) |
| Side upper ligaments | 0.70 / 0.70 | 2 / 2 | 0.70 | 103–107 |
| Side lower ligaments | — / 0.70 | 0 / 2 | 0.70 (full) | 103–107 |
| Rear upper ligament | 0.70 / 0.70 | 1 / 1 | 0.70 | 110, 119 |
| Rear lower ligament | 0.88666 / 0.70 | 1 / 1 | 0.70 / 0.70 | 110–112 |
| Rear sloped ligament | 0.56920 / 0.56920 | 1 / 1 | 0.56921 | 111–112 |
| Side and rear wall click-hole roofs | 0.80 / 0.80 | 3 / 3 | 0.80 | 115–119 |
| **Total thin faces** | | **19 / 21** | | |

The lite rear lower ligament illustrates the audit proxy's limitation: its
bisection can step across the neighbouring void, whereas the independent mesh
ray stops at the first exit (0.70 mm). Both results are locked separately; the
0.88666 mm proxy is not a claim of physical minimum thickness. The sloped
ligament reference probe starts at (−11.56, −2.36, 0.18) along normalized
(−3, 0, −1); its first-hit thickness is 0.56921 mm in both variants.

Every ceiling below measures 90°. Reference triangles independently confirm
each complete face bounding box and downward normal within 0.01 mm. For full,
add 3.4 mm to the listed lite Z **except** the indicator, which stays at 0.4 mm.

| Downward face set | Lite / full count | Lite Z (mm) | Maximum local bridge (mm) | Source lines |
| --- | ---: | ---: | ---: | --- |
| Top-plate underside ledges | 8 / 8 | 2.99 | 0.5 | 43, 48, 50 |
| Side bottom click nubs | 2 / 2 | 0.19 | 0 | 26–30, 58–70 |
| Rear bottom click nub | 1 / 1 | 0.64 | 0 | 26–30, 89–99 |
| Side click-hole roofs | 2 / 2 | 2.8 | 0.5 | 103–107 |
| Rear click-hole roof | 1 / 1 | 2.799 | 0.5 | 110 |
| Side and rear wall click-hole roofs | 3 / 3 | 2.6 | 0.5 | 115–119 |
| Triangular indicator roof | 1 / 1 | 0.4 (fixed) | 1.5 | 122 (`$fn=2` clamps to 3) |
| Front nub underside | 0 / 1 | bed-contact; full Z=3.4 | 0 / 0.5 | 26–30, 75–85 |
| **Total downward faces above bed** | **18 / 19** | | | |

The front underside spans X=12.4…12.8, Y=−7…7; the lite face is on the bed
and excluded by the production audit. The rear nub spans X=−12.8…−12.4,
Y=−5.4…5.4. The indicator ceiling spans X=8.75…11, Y=±1.29904 at Z=0.4.
These distinguish the directional geometry from the symmetric inventory.

| Variant (snaps-down) | Minimum wall proxy (mm) | Worst overhang | Maximum local bridge (mm) | Downward fillets | Published inventory |
| --- | ---: | ---: | ---: | ---: | --- |
| Lite | 0.41 | 90° | 0.5 | 0 | Pass |
| Full | 0.41 | 90° | 0.5 | 0 | Pass |
| Directional lite | 0.41 | 90° | 1.5 | 0 | Pass |
| Directional full | 0.41 | 90° | 1.5 | 0 | Pass |

The local-bridge column is measured by the production raster primitive on the
port, whose external surface parity is independently checked against the SCAD
mesh. It is not an STL bounding-box span. The 90° mating ceilings are explicit
published exceptions to the generic holder angle limit; 1.5 mm remains below
the generic 10 mm bridge limit. No geometry was modified to pass those limits.

Run `uv run pytest tests/test_opengrid_snap.py -q -s` from `build123d/` to emit
parity and audit tables. The tests require neither OpenSCAD nor vendored libs.

To verify the `[C]` values and directional argument names against the pinned
upstream source, run `uv run pytest tests/test_opengrid_snap.py -m upstream -q`.
This opt-in test fetches the source into memory; ordinary PR tests stay offline.
