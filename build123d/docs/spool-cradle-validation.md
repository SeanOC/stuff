# Spool cradle validation — pst-zkd6 / pst-tskv

The v2.1 placement aids follow pst-tskv rev 5: finite guide crests, supported
cap transitions, and the existing standing print orientation. See the v2.1
validation results below; physical spool measurements remain in pst-m9xt.

One spool per holder; X is its axis along the board, +Y faces the user,
and +Z is up. Print standing on Z=0 in PETG/PCTG, three walls and 15%
gyroid/adaptive cubic infill. The 2.4 mm webs and front panel are solid
perimeters; the CAD does not model a slicer shell.

## v2 — what changed and why

Sean's three findings in the canonical bead were:

1. “two seats in one row at the plate bottom → the plate is a pry lever”.
   Two continuous channels now capture board heads at every row from the
   lowest to highest seat, with snap detents at those two extremes.
2. “two free-ended V webs per flange, nothing ties the cantilevered tips”.
   Each flange web now has triangular openings closed by a continuous
   bottom return chord. A full-width vertical front panel joins both webs.
3. “straight V at 40° under a round flange → two line contacts pushing outward”.
   Analytic circular saddles replace the V, at spool radius plus adjustable
   radial clearance (0.5 mm default, 0.25–1.5 mm).

The registry identity, presets, export paths, 70 mm plate, 75 mm cadence,
standing orientation and pending flange measurements are preserved.

## Dimensions and provenance

| Input | Defaults / domain | Evidence |
| --- | --- | --- |
| Spool diameter | 200; 190–205 mm | The [Bambu AMS 2 Pro specification](https://eu.store.bambulab.com/en-ch/products/ams-2-pro) gives 197–202 mm compatibility. The wider model range includes this interval. |
| Spool width | 66; 50–70 mm | The same first-party specification gives 50–68 mm. The Bambu preset uses 67 mm; the generic preset uses the bead's nominal 66 mm. |
| Bambu reusable envelope | Ø200 × 67 mm | [Bambu's reusable-spool listing](https://au.store.bambulab.com/products/bambu-reusable-spool) lists **packing size** 200 × 200 × 67 mm; [the community dimensional report](https://forum.bambulab.com/t/bambu-spool-dimensions/123480/2) separately reports an approximate Ø200 × 67 mm spool. This is nominal sizing, not a toleranced manufacturer drawing. |
| Flange height above full winding | 8; 4–15 mm | Operator-specified default in pst-ir0v canonical rev 5. No published full-winding diameter was established. Both presets explicitly retain 8 mm. |
| Axial flange rim land | 3; 1.5–6 mm | Operator-specified default in pst-ir0v canonical rev 5. No published rim-land measurement was established. Both presets explicitly retain 3 mm. |
| Contact tangent angle from vertical (v1 rays) | 40°; 25–45° | Approved design domain. |
| Front rise above saddle endpoint | 5; 0–15 mm | Approved adjustable access gesture; 0 preserves the front tangent edge for lift-out. |
| Plate | 70 × 102.85 × 7 mm at defaults | Width 68–70; thickness 6.6–9 mm. Height follows the channel spine plus its backing thickness. |
| Board pitch / cutter depth | 25 / 4.15 mm | [Pinned library and provenance](multibuild-library.md). |

Flange dimensions are **design inputs pending measurement**, not measurements
inferred from AMS compatibility. The clearance tests establish the result for
the declared envelope. Before printing for a particular spool, measure its
rim land and the radial difference between flange and full winding. The
physical print-check follow-up **pst-m9xt** must resolve these two preset assumptions.

## Geometry and clearance

For spool radius `R`, saddle radius `Rs = R + saddle_clearance`, angle `a`,
plate thickness `t`, and wall clearance `c`:

- Saddle centre: `(Y,Z) = (t+c+R, 18+Rs)`.
- Arc endpoints: `Y = centreY ± Rs*cos(a)`, `Z = centreZ − Rs*sin(a)`.
  This preserves the v1 endpoint rays; the angular span is `180° − 2a`.
  The UI calls the retained parameter “Contact tangent angle from vertical”.
- Front panel begins beyond the front endpoint by
  `max(1.5 mm, lip_height*tan(a))`; its height is endpoint Z + lip height.
  The minimum landing allows an R1 junction even at zero lip rise.
- Rear extension meets the plate on the endpoint tangent.
- Winding fixture: radius `R − flange_height`, axial length
  `spool_width − 2*flange_rim_width`.

The circular cut is an exact cylinder, not a polyline approximation. Tests
probe material immediately below and air above it on both rim lands,
check both flange envelopes for collisions, and require >0.5 mm winding
clearance. Every numeric endpoint and the combined narrow-plate/wide-spool
corner receive these checks. Radial clearance describes the nominal mating
envelopes; the physical spool settles into the saddle under its own weight.

Each 2.4 mm flange web contains three triangular openings with 45° roofs.
A continuous 6 mm bed chord returns to the plate. The material above and
between openings closes the load paths; no arm tip terminates unsupported.
Both web/panel interfaces overlap by one full wall. R1 vertical blends join
webs to the plate and panel. Narrow-plate/wide-spool roots retain their plate
margins. Their transition length is `max(2.4 mm, 2 × lateral offset)`, limiting the flare to a 1:2
slope and avoiding the thin tip left by a fixed 12 mm transition.

## Mount and row spacing

Two channels lie at X=−12.5/+12.5 mm, on large-hole columns when the plate
centre is on a small-hole column. Channel length is the rear root height
rounded up to a 25 mm multiple. The plate rises one backing thickness above
that spine. Backing is `plate_thickness − POCKET_DEPTH`, at least 2.45 mm
in the declared parameter domain (the requirement is ≥2.4 mm).

At defaults the spine runs Z=0…100, on-ramps are at Z=12.5, 37.5, 62.5,
and seated rows are Z=25, 50, 75. Snap seats are at the lowest and highest
rows; all intermediate board heads remain captured by the continuous
T profile. Installation enters along +Y and drops the holder 12.5 mm.
The actual head/opening envelopes need end clearance; the highest seated
head is below the closed top, not centred at the spine endpoint.

The registered `multibuild-multiconnect-channel` contract verifies every
head's insertion and drop, retention, the full lowest-to-highest sweep,
local backing behind every pocket-back face, and closed-top material.
The same library cutter is copied for both channels. No mount profile or
board pitch is reimplemented. The fixed two-channel layout is the explicit
operator-approved exception to the usual mount tunables.

At 75 mm cadence, 70 mm plates have equal 5 mm gaps. At 100 mm cadence,
they have 30 mm gaps. Tests place three finished solids, check non-overlap,
map all seats to the board lattice, and compare every on-ramp row across
all three holders. Empty the holder before removing it. Retain 225 mm
vertical spool-centre spacing for the declared Ø190–205 mm domain.

## Load calculation and material basis

Use **30 N downward at the front flange contact**, conservatively shared
between the two webs. This is 2.55 times a 1.2 kg spool's weight. The
[Prusament PETG TDS](https://prusament.com/wp-content/uploads/2022/10/PETG_Prusament_TDS_2021_10_EN.pdf)
basis retained from v1 is 45 MPa yield, with a 15 MPa working limit.
This assumes the selected PETG/PCTG process can achieve that yield.
PLA remains excluded by operator approval for sustained-load creep/heat.

For horizontal root-to-contact distance `L` and contact height `H`, take
an envelope diagonal at `atan(H/L)` and a force per web of
`F = 15*sqrt(L²+H²)/H`. This bounds the tension/compression demand for
the overall triangular return path. The tests cut the **finished solid**
at each opening apex and measure the two lower chords and two upper
members. Each actual section area is conservatively projected by `1/sqrt(2)`
for a 45° member; every resulting `F/A` must stay below 15 MPa. No plate
infill is counted as a load-bearing web section.

The front-panel spreading demand is conservatively `30*cot(a)`.
Its actual section at X=0 includes its top and bed chamfers; demand divided
by measured area must also remain below 15 MPa. The panel carries tension
along X, and the bed chords along Y, within the printed XY layers.
Inclined members and the plate also transmit Z shear/compression; this is
an axial hand calculation, not a buckling, fatigue or layer-bond rating.
The physical validation bead **pst-m9xt** remains necessary.

Per-preset measured forces, sections and stresses are recorded after running
`test_truss_and_panel_hand_calc` (see validation results below).

## Print and edge audit

The saddle is the upward-facing top edge of a standing web. It has no
hanging curved underside: triangular void ceilings are straight 45° roofs.
The front panel starts on the bed and is a vertical wall through the full
spool width; it is not an unsupported crossbar. Tests inspect both actual
web loops and panel continuity, in addition to the production print audit.
Only registered library channel pockets receive the existing support
exception. No structural face is excluded.

| Edge class | Treatment |
| --- | --- |
| Plate top / exterior vertical edges | 0.4 mm chamfer |
| Front panel top / exterior vertical edges | 0.4 mm chamfer |
| Triangular opening rims | 0.4 mm chamfer |
| Bed perimeter including channel apertures | 0.4 mm 45° relief |
| Web/plate and web/panel vertical junctions | R1 fillets |
| Circular saddle and tangent extensions | Functional contact edges |
| Internal triangular roof/floor intersections | Functional 45° opening profile; no flat roof bevel |
| Library channel profile | Functional, unchanged above bed relief |

## CAD renders and exports

![Front, saddle section, and three-holder row](renders/holder_spool_cradle.png)

[Default STL](exports/holder_spool_cradle.stl) ·
[Bambu preset STL](exports/holder_spool_cradle_bambu_reusable_200.stl) ·
[Generic AMS preset STL](exports/holder_spool_cradle_ams_generic_200.stl)

The middle view cuts through the near flange web to expose its closed
triangular openings and the front panel. These are CAD views; no reference
photos were supplied.

## Validation results and material use

| Preset | v1 volume (mm³) | v2 volume (mm³) | Change |
| --- | ---: | ---: | ---: |
| `bambu_reusable_200` | 134,709.073 | 72,798.919 | −45.96% |
| `ams_generic_200` | 134,696.164 | 72,672.428 | −46.05% |

The lower arc envelope, shorter plate, removal of mount/transverse ribs,
and triangular openings outweigh the added front panel. All thin members
remain 2.4 mm perimeter sections; volume is the exact CAD `part.volume`.

Both presets have the same conservative member force of **52.287 N** and
minimum projected actual section of **9.956 mm²**: **5.252 MPa**, below
15 MPa. The actual panel section is **141.040 mm²**, giving **0.253 MPa**
under **35.753 N** spreading force.

The default production audit reports **45.0°** maximum overhang, **0 mm** bridge,
**2.40 mm** minimum wall, **zero** downward fillets, and present bed relief.
All 49 spool-cradle tests pass. The suite checks watertight connected meshes,
all numeric endpoints,
clearance, truss closure, actual sections, board alignment, bed edges, and
the registered mount contract for both presets and minimum backing.
The combined print-audit corner (Ø205 × 70 mm spool, 4 mm flange height,
1.5 mm rim, 25° contact tangent, 0.25 mm saddle clearance, 15 mm lip,
68 × 6.6 mm plate and 6 mm wall clearance) passes with **2.15 mm** minimum
wall, **45°** overhang and no bridges or downward fillets. Its root transition
uses the bounded 1:2 flare described above.
The Bambu preset with its shallower flare is also audited: **2.35 mm**
minimum wall, with the other print checks passing.
This regression catches the thin transition missed by the default audit.

Web-app validation: 291 tests pass; manifest validation: 24 tests pass.
The shared mount-parameter assertion also passes with the v2 channel type.

## Reproduce

```sh
uv run --project build123d pytest build123d/tests/test_spool_cradle.py -s
uv run --project build123d python build123d/scripts/manifest.py
uv run --project build123d python build123d/scripts/render_spool_cradle.py
npm test
```

## v2.1 — placement aids (pst-tskv)

The saddle lands widen **inboard** from each flange's outer face. `rail_width`
is 10 mm by default (6–14 mm). Their contact surface remains the exact
`R + saddle_clearance` arc. The inner edge has a 2.4 mm radial section;
a 45° XZ transition returns the overhang to the standing web. The winding
clearance checks include the widest rail, narrowest spool, smallest flange
height, and narrowest rim together.

The guides sit **outboard** of the flange, so their raised faces stay away
from the winding. `guide_height` is 15 mm by default (12–30 mm).
`guide_gap` is the half-gap to the next holder, 0.5 mm by default (0.5–2 mm).
The guide's vertical outer face is at `±(75/2 − guide_gap)`. Thus enabled
guides occupy 74 mm at defaults and leave 1 mm between holders on the
75 mm cadence. The cap adds no outboard width.

| Spool width | Outboard envelope per side | Sloping lead-in run | Default overall width |
| --- | ---: | ---: | ---: |
| Generic AMS, 66 mm | 4.0 mm | 0.7 mm | 74 mm |
| Bambu reusable, 67 mm | 3.5 mm | 0.2 mm | 74 mm |
| Wide endpoint, 70 mm | 2.0 mm available; guide omitted | — | 70 mm |
| Narrow endpoint, 50 mm | 12.0 mm | 8.7 mm | 74 mm |

Rev 5 replaces the knife edge with a **2.4 mm flat crest**. The blank crest
is 2.8 mm wide; its outer 0.4 mm chamfer leaves the full 2.4 mm land.
The inner face starts at the flange outer face plus `saddle_clearance`.
Its horizontal run is therefore `guide_reach − saddle_clearance − 2.8 mm`.
The outboard envelope in the table is not a measured placement tolerance:
the flat crest and clearance consume part of that envelope.

A guide and its entire outboard ramp are omitted when this run is not
positive. This includes rev 4's `reach < 1.6 mm` case and also the wide-spool
settings where the rev 5 crest cannot fit outside the flange. The unchanged
mount plate may then set the overall width, still within `75 − 2*guide_gap`.

The underside runs from `(Xw, Zs − reach)` to `(Xo, Zs)` at 45° and continues
inward through a full web thickness. The cap, root and guide form one solid
block. Analytic curtain cuts form its underside chamfers without separate
pointed ribs. The cap retains a 2.4 mm radial inner land. Its panel junction
has an additional inclined transition and R1 vertical blend.

The guide has flat end lands so its rising profile cannot feather into the
vertical end faces. It continues across the front panel's 2.4 mm thickness,
letting the panel and guide share one finished end face. The nominal height
is retained along the central arc; the flat end lands are locally lower.
Oblique extrusion of the analytic arc preserves the 45° XZ underside;
a rotating sweep would change that section.

The three original truss openings and their 1.6 mm core remain. Outside the
web, relief reaches below each opening so it leaves no thin cap tails at the
opening floor. Its 1.6 mm lateral runouts return to the original roof apex,
avoiding new sharp ridges. Exposed guide, panel and relief ends are checked
on the finished solid by the unchanged edge-class gate. The mount cutters,
plate, panel and truss layout are retained.

At default diameter and cradle angle, the front exposed rim is
`2*R*sin(angle) − lip_height − guide_height = 108.56 mm`. At the maximum
30 mm guide height it is 93.56 mm, above the 20 mm grip requirement.
The guides bound sideways placement; removal is up and forward.

### Added section and print review

The original 30 N downward front-rim load and PETG/PCTG basis still apply.
The caps add material to the rail section. Tests measure the finished upper
members and bed chords and retain the 15 MPa working limit; the new guide
is not credited as necessary to carry that load. The panel and library
mount contract retain their v2 checks.

The revised review sheet includes front, side section, three-holder row,
and the requested −X end view. The widened caps and guide ramps must pass
the BRep audit in the standing orientation; only the two registered mount
pockets are excluded. These CAD artifacts do not replace the physical print
check in pst-m9xt.

| Preset | v2 volume (mm³) | v2.1 volume (mm³) | Added material |
| --- | ---: | ---: | ---: |
| `bambu_reusable_200` | 72,798.919 | 104,255.752 | 31,456.833 (+43.21%) |
| `ams_generic_200` | 72,672.428 | 105,923.164 | 33,250.736 (+45.75%) |

These are measured CAD `part.volume` values, including the support ramps
and junction blends. The increase buys a 10 mm nominal placement land
instead of the 2.4 mm web edge, plus outboard lead-in guides with printable
2.4 mm crests and supported end lands. The narrower
generic spool has the larger guide reach, so it adds more guide material.
The mount plate and truss layout do not grow. Three-wall slicer settings
still apply; the wider ramp sections should not be described as uniformly
2.4 mm walls.

### Validation results

The five required production audits and the additional narrow-crest corner
have these results on the final rev 5 solid:

| Case | Sampled minimum wall | Maximum overhang | Bridge | Downward fillets |
| --- | ---: | ---: | ---: | ---: |
| Default / generic | 1.18 mm | 45° | 0 mm | 0 |
| Bambu preset | 1.02 mm | 45° | 0 mm | 0 |
| Original combined corner | 1.02 mm | 45° | 0 mm | 0 |
| Maximum reach / minimum height | 1.18 mm | 45° | 0 mm | 0 |
| Guides and ramps omitted | 1.18 mm | 45° | 0 mm | 0 |
| 70 mm spool / 1.5 mm clearance / 30 mm height | 1.10 mm | 45° | 0 mm | 0 |

All report bed relief present. Only the two registered library pockets are
excluded. The minimum-wall floor, overhang limits and exposed-edge
exemptions are unchanged. The additional corner omits the guide and ramp;
geometry tests also measure the 2.4 mm crest on enabled guides.

The original 74 CAD tests plus the added crest-clearance regression were
run locally across five groups covering the entire 75-test suite. These
include meshes, every numeric endpoint, flange/winding clearance, actual
cap/ramp probes, crest width, guide/ramp omission, 75 mm placement, truss
sections, the unchanged exposed-edge gate and mount contracts.
Web tests: **291 pass**. Manifest tests: **24 pass**. All three regenerated
STLs are watertight single bodies and 74 mm wide. The four-view render was
inspected, including the 75 mm holder row and −X view.

The earlier v2 measurements above remain the baseline. CAD checks do not
replace the physical print check in pst-m9xt.
