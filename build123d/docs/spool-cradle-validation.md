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

Rev 6 sets guide and outboard-ramp omission at
`guide_reach < WEB + saddle_clearance` (2.9 mm with default clearance).
At equality the lead-in face is vertical. Between this threshold and the
full-crest threshold, the blank crest fills the available width and its
0.4 mm outer bevel leaves a 2.0–2.4 mm land. The vertical inner rim
receives a further 0.2 mm bevel, leaving at least 1.8 mm of flat crest. This interprets the
rev 6 threshold as superseding rev 5's 2.4 mm *finished* land at these
narrow settings; it retains a 2.4 mm blank and exceeds the 1.6 mm structural
minimum and meets the 1.8 mm standalone-feature minimum. Default and Bambu crests stay unchanged at 2.4 mm finished.
The 70 mm endpoint omits both guide and ramp. The unchanged
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
| `bambu_reusable_200` | 72,798.919 | 104,215.208 | 31,416.289 (+43.16%) |
| `ams_generic_200` | 72,672.428 | 105,882.620 | 33,210.192 (+45.70%) |

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
geometry tests measure the 2.4 mm finished crest on the original enabled
guide cases. Rev 6 adds the narrow-guide boundary cases described above.

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


### Rev 6 audit runtime

Bed-relief wedges and unique corner cones are subtracted in one operation,
instead of rebuilding the whole body for every edge and repeated vertex.
After this change, a profiled default run took 74.96 seconds: construction
was 2.86 seconds and the unchanged physical audit was 71.80 seconds.
Point-inside queries account for 64.83 seconds, chiefly wall-thickness
sampling over the channel, truss, cap and guide faces. Construction alone
cannot remove the remaining gap to 60 seconds. Following the authorized
fallback, this model has a 120-second budget (CI previously measured
93.2 seconds); all other models retain the 60-second budget. Physical
thresholds, sampling and mount exclusions are unchanged.

The rev 6 boundary regression builds reach 2.90 mm (present), 2.85 mm
(absent), and 3.00 mm (present). All three pass the physical print audit,
flange/winding-clearance checks, cadence limit, and the unchanged exposed-edge
classifier. Near the threshold, the rear relief uses a smaller bevel to
retain wall thickness, the vertical inner crest gets a 0.2 mm bevel, and
the guide/panel end intersections get 0.1–0.2 mm finishing bevels. The
guide-omitted panel's exposed side rims get a 0.4 mm chamfer.

The complete non-cradle suite passes: 426 passed, one expected smoke-model
failure. The cradle's registry budget check took 74.35 seconds (120-second
model budget); its separate production audit passed in 76.86 seconds.

Final rev 6 validation covers the full build123d suite in complementary
runs: **426 + 75 + 3 = 504 passed**, with one expected smoke-model failure.
The 75 original cradle checks pass, and the three new boundary cases pass.
Web tests: **291 passed**. All three regenerated exports are watertight
single bodies at 74 mm overall width; preset volumes remain unchanged from
rev 5. The four-view render was regenerated and inspected.


### Review round 5: rear guide bevel at maximum clearance

The combined input `spool_width=66, saddle_clearance=1.5, cradle_angle=45`
exposed a construction failure: the rear-edge group requested a 0.375 mm
bevel while the guide's already-finished inner rim left only 0.2 mm of
horizontal land at its upper endpoint. Saddle clearance does not measure
that local land.

The two inner guide edges are now selected separately. Their bevel is
limited to half the shortest adjacent horizontal edge run, capped by the
existing rear bevel. The cap/web rear edges use the same local bound: the
previous larger bevel also left a 0.87 mm cap section at the 25° corner.
A second geometric bound limits the vertical reach of any rear bevel to
0.4 mm using `bevel <= 0.4 * tan(cradle_angle)`. This prevents the same
cap thinning on the wide-guide 25° corner (initially measured at 0.85 mm).
All rear edges remain finished. Short sloping intersections at the feet of these bevels are finished using
a bevel limited by their own edge lengths. This preserves the exposed-edge
gate without a parameter-specific fallback or an exception to that gate.

The new corner sweep combines 1.5 mm saddle clearance, enabled guides on
50 mm and 66 mm spools, and both cradle-angle endpoints (25° and 45°).
It checks construction, single-body validity, cadence and spool clearance;
the exact reported reproducer also runs the full exposed-edge classifier.
Each of the four corners runs the physical print audit.

The default and Bambu preset geometry is unchanged by this fix: measured
volumes remain 105,923.164 mm³ and 104,255.752 mm³ respectively (zero change
from rev 6); the tracked preset exports and render remain current.

Additional exposed-edge findings away from this rear-edge fix were first
tracked in `pst-qzx6d`; review round 6 below fixes them on this branch. On the preceding commit `4b7efed`, the wide-guide cases
(width 50 mm, clearance 1.5 mm, angles 25°/45°) already fail the full edge
classifier. The 25° front cap/panel and relief terminations also need that
separate follow-up. No classifier exemptions were added for these findings.


Round-5 validation: all **86 cradle checks** pass across the existing
78-case run and the eight new corner checks. The final geometry rerun
passes all 73 non-audit checks; the affected angle/clearance endpoints,
threshold audits and guide-omitted audit were rechecked after the bevel
bounds changed. All 13 physical audit cases pass. Manifest tests: **24
passed**. Web tests: **291 passed**. No audit limits, samples or functional
edge exemptions were relaxed.


### Review round 6: shallow-angle and wide-rail exposed edges (pst-7q2kz)

The round-5 corner sweep built all four maximum-clearance corners but ran
the exposed-edge classifier only on the 66 mm / 45° reproducer. That
condition is removed, so every corner now runs the unchanged classifier.
Three of the four failed. A wider sweep with the classifier unchanged (32
cases: presets, all four corners, widths 50–70 at 25°/33°/45°, rail
widths 6 and 14, guide height/gap and lip endpoints, minimum flange)
also failed at rail width 14. There were five geometric causes. All are
fixed in geometry; the classifier and its exemptions are byte-identical.

1. **Cap/panel groove at shallow angles.** The cap underside's last
   millimetre dropped a fixed √2 mm. That only falls toward the panel
   while the lip slope is below √2 (angle ≳ 35°). At 25° it still rose,
   leaving a 63° groove at the panel face (117° edge). The drop is now
   `max(√2, lip_slope + 0.2)`, so the last millimetre always falls at
   least 0.2 mm. Preset angles (40°) keep √2.
2. **Rear bevel feet on wide guides.** The short sloping intersections at
   the feet of the rear bevels were finished only on narrow guides. They
   are now finished whenever a guide is present (90° edges at
   x = ±spool_width/2 on 50 mm spools).
3. **Outboard relief runout vs guide root.** The relief roof fell 0.57 mm
   over 1.6 mm outboard of the web. That tilted it against the guide
   root's 45° underside, giving a 90.1° rim at 50 mm / 25°. The runout now
   tapers across the whole root to `CADENCE/2 + 1`.
4. **Inboard relief runout vs cap underside.** This is the same effect
   inboard: a 91.1° rim at rail width 14. The short flat run left a
   0.13 mm apex-ridge fragment at 25°, below the classifier's 1 mm ridge
   length. The runout now tapers from the cap's inboard end to the web
   face, so no flat ridge fragment remains.
5. **Deep cap tail at rail width 14.** A 14 mm rail's cap underside dips
   below the middle opening's floor. The deep cutter used to grow toward
   the web, so it met the web's inner face in a 91.7° crevice. The deep
   cutter (applied only to the added cap/guide before fusion) now grows
   inboard, so that corner opens. The final shallow cutter and its
   0.4 mm web-rim mitre are unchanged.

A new fast regression runs the classifier on the five previously failing
non-corner combinations. Preset geometry changes slightly because the
inboard taper and deep cutter trim a little more cap around each opening:

| Preset | Rev 6 volume (mm³) | Round 6 volume (mm³) | Change |
| --- | ---: | ---: | ---: |
| `bambu_reusable_200` | 104,255.752 | 104,215.208 | −40.544 (−0.04%) |
| `ams_generic_200` | 105,923.164 | 105,882.620 | −40.544 (−0.04%) |

The three exports are regenerated as watertight single bodies, 74 mm
wide. The four-view render and review tile are regenerated. The X=0
section golden is unchanged.

