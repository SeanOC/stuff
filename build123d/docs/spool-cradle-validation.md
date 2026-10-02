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


## Measured MultiBuild constants (pst-ozpae)

pst-ozpae adopted the measured MultiBuild board constants (tile thickness
6.2, small-hole mouth Ø8, large-hole band and helix values; see
[provenance.md](provenance.md#measured-vs-cited-values-multibuild)). The
cradle imports only `PITCH` from `multibuild.constants`, directly and via
`multibuild.multiconnect`, and pitch is unchanged at 25 mm. Its geometry is
therefore unchanged. `part.volume` before and after:

| Preset | Before (mm³) | After (mm³) |
| --- | ---: | ---: |
| `bambu_reusable_200` | 104,215.208 | 104,215.208 |
| `ams_generic_200` | 105,882.620 | 105,882.620 |

No fit changes, so no re-print is implied. The print audit is re-run and
still passes.


## Point pockets: `mount_style='points'` (pst-93yd5)

> **Superseded by pst-7shtl** ([below](#points--fix-point-slots-what-changed-and-why-pst-7shtl)):
> the pockets are now MultiBuild Fix Point slots, not Multiconnect segments.

`mount_style` is an enum param, `channel` (default) or `points`. Default
geometry and both channel presets are unchanged. `points` replaces the two
full-height channels with four discrete Multiconnect pockets: columns at
x = ±12.5, two rows 50 mm (two board rows) apart. The body above the
plate, the plate outline, the guides and the 75 mm cadence are the same.

Each pocket is `multibuild.point_cutter()`: one on-ramp plus one seat,
built with the channel's own library features. It is the shortest channel
segment that holds them. The on-ramp is 12.5 mm above the pocket floor,
as on a channel's lowest on-ramp, which leaves 1.5 mm below the Ø22
opening. The seat is 12.5 mm above the on-ramp. The pocket ends one library
head-cutter radius (10.15 mm) above the seat, so it is **35.15 mm** long.
`channel_cutter` still requires 25 mm multiples, so this is a separate
entry point. A 50 mm channel segment (the shortest multiple holding both
features) would make the two pockets abut at 50 mm row spacing. They would
be one spine, and the contract rejects that layout (no cap over the lower
pocket). Rows 75 mm apart need a ≥130 mm plate, taller than any plate in
the parameter range.

The upper pocket ends where the channel spine would, under the same closed
cap (plate thickness − 4.15 mm, 2.85 mm at default). That keeps the upper
heads as high as the plate allows, for pull-out leverage. The lower pocket
is 50 mm below it. A root height of 75 mm or less (channel length 75) would
put the lower floor under the 2.9 mm bed margin (WEB + 0.5 mm) and raises
`ValueError`. Every root height in the declared ranges gives a 100 or
125 mm channel length.

| Channel length | Lower pocket Z | Upper pocket Z | Seats Z | On-ramps Z | Solid between |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 (both presets) | 14.85–50.00 | 64.85–100.00 | 39.85, 89.85 | 27.35, 77.35 | 14.85 mm |
| 125 (e.g. 25° cradle) | 39.85–75.00 | 89.85–125.00 | 64.85, 114.85 | 52.35, 102.35 | 14.85 mm |

The bed edge is solid under each column, with no bottom opening. Backing
behind every pocket is plate thickness − 4.15, at least 2.45 mm. Both
styles declare the one mount type `multibuild-multiconnect-channel`.
`mount_fixtures` returns the style's fixtures: four short cutters, four
seats and four on-ramps for `points`.

### Contract generalization

`verify_multiconnect_channel` matched seats to cutters by X centre and swept
one path from each X's lowest on-ramp to its highest seat. It now matches
each (seat, on-ramp) pair to the one cutter whose X centre matches and whose
Z extent holds both poses. Travel is swept per cutter, from its own lowest
on-ramp to its own highest seat. On a full-height spine this is the same
matching and the same sweep. A test checks the demo plate's pairs against
the old rule. The four defect-detection cases still fail the contract. Two
discrete pockets in one column are not joined by a sweep: the plate between
them is meant to be solid.

### Load path

The truss webs and rails meet the plate at |x| = root_inner…root_inner+2.4
(30.6–33.0 mm at 66 mm spool width, 22.6–25.0 mm at 50 mm). Their roots start
at y = plate thickness − 2.4, behind the 4.15 mm pockets, so every web
lands on the pocket backing, not on a void. The truss-section test runs on
both points presets. It checks that no web section meets a pocket.

### Volumes

| Preset | mount_style | Volume (mm³) |
| --- | --- | ---: |
| `bambu_reusable_200` | channel | 104,215.208 |
| `ams_generic_200` | channel | 105,882.620 |
| `bambu_reusable_200_points` | points | 108,936.692 |
| `ams_generic_200_points` | points | 110,604.104 |

The points presets are 4,721.484 mm³ (+4.5%) heavier than the matching
channel presets. That is the plate left solid between and around the
pockets, which is the purpose of the style.

### Print audit

Both points presets and all 12 corners spool_width 50/66/70 × saddle
clearance 0.25/1.5 × cradle angle 25/45 pass the print audit and the
finished-edge classes. The only accepted exception is the mount pockets
(the four cutters). When this style landed, the corner 66 / 0.25 / 25
failed the wall check (0.70 mm < 0.9 mm) in **both** styles. The cause was
the saddle's rear end, well away from any pocket, so a strict `xfail`
pinned it until pst-dkqef fixed the body (see "Outboard rear land" below).
The pocket ceilings are the same library slot ends as the channel top, so
the standing print needs support only inside the pockets.


## openConnect slots: `mount_style='openconnect'` (pst-pwtnq)

`mount_style` gains a third value, `openconnect`, for an openGrid wall.
The body (saddle, rail caps, guides, truss webs, front panel) is the same
v2.1 body. Only the grid and the mount pockets change. `channel` stays the
default, and the four Multiboard presets are byte-identical (volumes below).

### Grid follows the style

The module no longer has a fixed `CADENCE`. `dimensions()` resolves the
grid from `mount_style` (`GRIDS`):

| Style | Pitch | Holder cadence | Pocket depth | Max plate width | Min plate thickness |
| --- | ---: | ---: | ---: | ---: | ---: |
| `channel`, `points` | 25 | 75 | 4.15 | 70 (75 − 5 gap) | 6.55 (4.15 + 2.4) |
| `openconnect` | 28 | 84 | 2.7 | 82 (84 − 2 gap) | 5.1 (2.7 + 2.4) |

The shared ranges widen to `plate_width` 68–82 and `plate_thickness`
5.1–9 (defaults unchanged, 70 and 7). `check_plate()` raises a
`ValueError` that names the violated floor, for example
`mount_style='channel' needs plate_width <= 70 mm (cadence 75 - 5 mm gap)`.
The Multiboard thickness check uses the physical floor, 6.55 mm (≥2.4 mm
backing). The old range minimum was that floor rounded up to the 0.1 step,
6.6. The openConnect floors equal the range bounds, so for them
`resolve_values` rejects a violation first.

`guide_outer` / `guide_reach` and the guide-omission threshold keep their
form and read the resolved cadence. At 84 mm, `guide_outer` = 42 − guide_gap,
so the guides reach 4.5 mm further out per side than at 75. At
`guide_gap` 0.5 the holder is 83 mm wide, leaving a 1 mm gap at 84 mm
cadence. Channel length (the plate's grid length) is the root height rounded
up to a 28 mm multiple.

**Param sweep.** `test_endpoints` sweeps every numeric range end at the
default style. Two cells are below the channel floors: `plate_width=82` and
`plate_thickness=5.1`. They are declared **expected-invalid**: a test
requires each to raise. Both are also swept as valid cells under
`openconnect`, together with the other plate range ends (68 and 9).

### Slots and rows

There are four `openconnect.slot_cutter()` slots (pst-qnekl port, snap
nub on, 0.1/0.1 clearance). Columns are at x = ±14, adjacent tile centres.
The upper slot roof (`OC_SLOT_TOP` = 9.0 mm above the seat) is exactly
WEB = 2.4 mm below the plate top, which keeps the upper heads as high as the
plate allows. Since pst-fmvzb the lower row is the lowest whole tile below
it whose on-ramp floor (`OC_SLOT_BOTTOM` = 13.2 mm below the seat) stays
WEB + 0.5 = 2.9 mm above the bed relief (`oc_seats()`), so two slots sit
near the top and two near the bottom. Before pst-fmvzb the rows were one
tile apart (seats 75.4/103.4 and 47.4/75.4 below).

| Grid length | Plate height (t = 5.5) | Seats Z | On-ramps Z | Slot Z extents | Row spacing | Cases |
| ---: | ---: | --- | --- | --- | ---: | --- |
| 112 | 114.8 | 19.4, 103.4 | 8.8, 92.8 | 6.2–28.4, 90.2–112.4 | 84 (3 tiles) | both presets, every 25° corner |
| 84 | 86.8 | 19.4, 75.4 | 8.8, 64.8 | 6.2–28.4, 62.2–84.4 | 56 (2 tiles) | every 45° corner |

Each slot spans x −13.0…+8.6 about its axis, because the on-ramp leans to
−X. The solid plate between rows is 61.8 mm (112 grid) or 33.8 mm (84
grid) tall, and 6.4 mm between columns. The plate margin at the 82 mm
presets is 14.0 mm (left) and 18.4 mm (right). The lowest slot floor is
6.2 mm above the bed (t = 5.5; 5.8 mm at t = 5.1), above the 2.9 mm floor
rule, so the bed edge is solid everywhere. Grid lengths 84 and 112 are the
only ones the parameter ranges reach; a 28 mm grid would leave no tile for
the lower row and `oc_seats()` raises with the minimum root_height. Backing is plate thickness − 2.7: 2.8 mm at the presets and
2.4 mm at the 5.1 mm minimum.

Installation: each head pushes in along +Y at its on-ramp, the holder
shifts 2.2 mm along X, then drops 10.6 mm. All four slots have the same
on-ramp offset (2.2, 0, 10.6), so one motion seats all four heads. A test
pins this. The registered `openconnect-slot` contract (pst-qnekl) runs on
both presets and on the 82 × 5.1 minimum-backing corner. It checks seat
clearance, pull-off retention, the end stop past the seat, the
push/shift/slide path, the dovetail, and 2.4 mm backing behind every pocket
floor.

### One model, two mount types

`mounts = ('multibuild-multiconnect-channel', 'openconnect-slot')`. This is
the first model with two mount types, and `mount_style` selects exactly one.
`ModelSpec.mount_for_values(values)` names the mount present. The module's
`mount_fixtures` hook returns **None** for the other mount.
`registry.resolve_mount_fixtures` returns None for an absent mount, and
raises if the hook and `mount_for_values` disagree. Every consumer skips an
absent (mount, values) pair:

- `mount_contracts.verify` returns False. `test_model_mount_contract`
  requires at least one verified pair per mount.
- `test_print_audit._audit_model` excludes only the present mount's cutters.
- `scripts/export.py::review_context` uses the first mount present under
  the values, not `mounts[0]`. For this model it is not reached, because the
  model declares a static review section. `test_review_sheet` follows the
  same rule.

Coverage is a data-only check in `registry._validate_spec`. When a model
sets `mount_for_values`, the mounts its presets select must equal the
declared mounts. A declared mount that no preset selects fails
registration, and so does a selection that is not declared. Single-mount
models leave it None and are unaffected.

### Load path

The truss webs meet the plate at |x| = root_inner…root_inner + 2.4, with
root_inner = min(spool_width, plate_width − 4)/2 − 2.4. That is 30.6–33.0 mm
at a 66 mm spool and 31.1–33.5 mm at 67 mm, clear of every slot (|x| ≤ 27).
Their roots start at y = t − 2.4 = 3.1, behind the 2.7 mm pockets. The
truss-section test runs on both openConnect presets and checks that no web
section meets a pocket. The upper heads sit 103.4 mm above the bed edge (the
wall pivot), against 75 mm for the channel's top seat row. Since pst-fmvzb
the lower heads sit 19.4 mm above it. The pull-off lever about the
bed-edge pivot is set by the upper row, so it is unchanged; the lower row
now locates the plate near its bottom edge as well as its top. No pull-out
rating is claimed for openConnect heads. The physical validation bead
**pst-m9xt** still applies.

### Corner sweep at 84 mm cadence

The print audit and the edge-class gate run on both presets and on the
v2.1 corners (spool_width 50/66/70 × saddle_clearance 0.25/1.5 ×
cradle_angle 25/45) with an 82 × 5.5 plate. The wider cadence opens two
guide regimes that 75 mm never builds. Each fix below is gated on its own
regime, so the Multiboard presets and the openConnect presets are
unchanged by it.

- **Root to the bed (w50, reach 16.5).** The guide root's 45° underside
  is reach + WEB = 18.9 mm deep at the rail's inner face, more than the
  18 mm saddle apex. `root_to_bed` (reach + WEB > APEX_HEIGHT) clips the
  root at Z = 0; the clipped tail lies inside the rail. The deep truss
  reliefs then cut the root down to the bed chord, so their 45° flanks
  meet the web's outer face. Under `root_to_bed` the deep cutter widens
  outboard (offset 0.4 → 0.6 mm across the root), which keeps that
  concave corner at about 89.4° instead of 91.3°.
- **OCCT rear-corner chamfer (w50).** The rear bevel of the concave
  rail-outer-face / guide-root-rear-face corner fails in OCCT for some
  root depths. The failure does not depend monotonically on cadence, and
  any chamfer length fails once it does. This change shipped a fallback
  wedge for the raising case only. pst-dkqef, merged after it, already
  builds that corner as an explicit `rear_corner_wedge` in every style and
  at every cadence, trimmed by the outboard land cutter. OCCT therefore no
  longer chamfers that corner, and the merge keeps pst-dkqef's
  unconditional wedge in place of the fallback.
- **Rear knife (w70 / c1.5 / a25, 0.71 mm).** This was pst-dkqef's
  unbacked knife: the saddle tangent met the vertical rear face on the
  outboard strip, at x = ±36.96 just outboard of the guide foot. This
  change shipped it as a pinned wall failure. pst-dkqef's outboard rear
  land, merged after it, removes the knife at the 84 mm cadence as well
  (min wall 0.983 mm). The pin is gone, so all 14 openConnect cases must
  now audit `ok`.

### Volumes

| Preset | mount_style | Volume (mm³) |
| --- | --- | ---: |
| `bambu_reusable_200` | channel | 104,215.208 |
| `ams_generic_200` | channel | 105,882.620 |
| `bambu_reusable_200_points` | points | 108,936.692 |
| `ams_generic_200_points` | points | 110,604.104 |
| `bambu_reusable_200_openconnect` | openconnect | 136,367.214 |
| `ams_generic_200_openconnect` | openconnect | 138,726.436 |

The openConnect presets are 32,152 mm³ (+31%) heavier than the matching
channel presets. Measured on the Bambu preset:

- **+19,012 mm³ from the wider guides.** This is the same preset rebuilt
  with the guide cadence held at 75. The guides fill to the resolved 84 mm
  cadence, as INVARIANT 2 requires. Their reach grows from 3.5 to 8.0 mm
  per side at a 67 mm spool.
- **The remaining ~13.1k mm³ is the taller, wider plate and its pockets.**
  The plate is 82 × 5.5 × 114.8 mm, against 70 × 7 × 102.85. It keeps solid
  material where the channel style cuts two full-height channels. The four
  pockets remove 4,043 mm³.

## Outboard rear land (pst-dkqef)

### Defect

The saddle's rear end was a knife wherever nothing backed it. The saddle
tangent (cradle_angle from vertical) met the vertical rear face at
y = rear_y in a 25–45° edge. The rail is backed: behind its rear contact
it continues the tangent plane down to the plate. The outboard strip
between the rail and the guide foot, and the guide root under the guide's
low rear land, were not backed.

The print audit marches walls from UV 0.3/0.5/0.7 on each face only, so it
saw the knife only when a short face put a sample near the edge. That
happened at 66 / 0.25 / 25 (0.705 mm) and, unswept, at 66 / 0.5 / 25
(0.656 mm) and 67 / 0.25 / 25 (0.603 mm). A dense probe (19 × 19 UV,
outboard rear corner only) measures **0.020–0.034 mm** on main at all
three, and at both shipped presets. The inboard cap's rear end has the same
unbacked knife; that is a separate follow-up.

### Fix

`rear_land_cutter()` cuts the guide root before the guide fuses, so the
guide refills wherever it stands above the cut:

1. A flat land at the saddle height WEB/2 behind rear_y, with a 0.4 × 45°
   rear chamfer.
2. Mirrored 30° ramps rise 0.4 mm to the rail's outer face and to the
   guide's lead-in. A flat land meets either wall at ≥ 90°, which the
   finished-edge gate rejects. Where the gap is narrow the two ramps form
   a 60° V.
3. A 45° stage keeps the floor 0.1 mm above the guide's 45° underside, so
   no notch opens below the guide.

Two OCCT chamfer failures moved with the new geometry:

- The guide's rear-end chamfer now runs on the guide blank before its
  underside is cut. After the fuse, the lead-in's rear edge ends on the
  land and the chamfer failed non-monotonically across inset and slope.
  On the cut blank, the guide foot is 0.24 mm thick at the Bambu preset.
  The root buries the chamfer's lower end below the land.
- The concave rail/guide-root rear corner is now an explicit 45° wedge
  (`rear_corner_wedge()`), trimmed by the same land cutter. It replaces the
  vertical chamfer there, which failed for some root depths.

### Validation

Each of these cases builds as one valid solid and passes the finished-edge
classes and contacts, and every one passes the print audit:

- Both presets of each style.
- The 12-corner grid above in channel style.
- The production audit corners.
- 66 / 0.5 / 25, 67 / 0.25 / 25, and 64, 65 and 68 × 0.25/0.5 × 25.

Minimum walls are 0.98–1.39 mm. The target corner reads 1.019 mm in both
styles. The dense probe reads ≥ 1.3 mm on the outboard rear corner in
all seven probed cases (both presets, the three knife corners, 50 / 0.25 /
25 and 66 / 1.5 / 45).

A 240-case build-plus-edges grid matches main exactly. It covers widths
50–70 (15 values), clearances 0.25/0.5/1/1.5 and angles 25/33/40/45. The
only failures, 68 and 68.5 / 0.25 / 40, fail identically on main, in the
inboard cap's rear chamfer. They go to the cap follow-up.

New tests:

- 66 / 0.25 / 25 as `rear-land-corner` in `test_production_print_audit`.
  It replaces the channel `xfail` twin, and the points grid drops its
  `xfail`.
- Four land-junction edge cases.
- `test_outboard_rear_end_has_no_knife`, a dense probe that fails on main
  at both cases (~16 s each).

A 12-case channel print-audit grid was considered and left out. It would
add about 8–9 min of CI (~42 s per case). The points grid already audits
the same 12 body corners, and the knife probe covers what UV sampling
misses.

### Volumes

| Preset | Before (mm³) | After (mm³) | Change |
| --- | ---: | ---: | ---: |
| `bambu_reusable_200` | 104,215.208 | 104,214.349 | −0.859 (−0.00%) |
| `ams_generic_200` | 105,882.620 | 105,881.681 | −0.939 (−0.00%) |
| `bambu_reusable_200_points` | 108,936.692 | 108,935.833 | −0.859 (−0.00%) |
| `ams_generic_200_points` | 110,604.104 | 110,603.165 | −0.939 (−0.00%) |
| `bambu_reusable_200_openconnect` | 136,367.214 | 136,365.583 | −1.631 (−0.00%) |
| `ams_generic_200_openconnect` | 138,726.436 | 138,724.716 | −1.720 (−0.00%) |

The land removes the unbacked knife; the net change is under 1 mm³ per
preset at the 75 mm cadence and under 2 mm³ at the 84 mm openConnect
cadence, where the wider guide root carries a longer land. The openConnect
"before" values come from main after pst-pwtnq (#132), measured
when this branch merged it. The exports, the four-view render and the
openConnect review sheet are regenerated.


## points → Fix-Point slots: what changed and why (pst-7shtl)

**Why.** pst-93yd5 cut `points` as 35.15 mm Multiconnect channel segments
(`point_cutter`). A `points` holder hangs on MultiBuild **Fix Points**
installed in the board, so that was the aliasing
[multibuild-research.md](multibuild-research.md) forbids (Sean 2026-10-01:
"use the cutouts in this zip"). The pockets are now the official **Fix
Point Slot** negative, re-derived from the measured remixing file
(`multibuild/fixpoint.py`, [provenance](provenance.md)). `point_cutter`,
`point_length` and `POINT_ONRAMP` are deleted (no other consumer).

**Slot.** 17 × 23.4 × 3.2 mm. The head enters a well (octagon, inradius
8.5) 6 mm below its seat, then slides up 6 mm. At the seat, an octagon lip
(inradius 6.0 at the face, 0.4 mm land, then 45° out to 8.5 at 2.9 mm deep)
closes over the head's 45° flare (r 5.87 → 8.0). The radial clearance on
the flare is 0.18 mm. The rebuilt slot and head equal the official files
to 0.003 % volume (`tests/test_fixpoint.py -m upstream`).

**Orientation.** Lip end **up** (+Z). Lowering the holder onto the board
carries each head from its well up under its lip, so gravity seats it. The
back view, with the pockets in orange,
[`renders/holder_spool_cradle_points_back.png`](renders/holder_spool_cradle_points_back.png),
shows each opening as the wide well below and the 12 mm lip mouth above.

**Layout.** Columns at x = ±12.5 (one board pitch apart). Rows are kept
**50 mm** apart (`POINT_ROW_SPACING`). Rows 25 apart would fit, but they
would leave only a 1.6 mm web between a lower slot's lip and the next
well, so 50 stays. The upper slot's lip end stops where the channel spine
would, under the closed cap (`point_seats`). The lower well keeps the
2.9 mm floor above the bed relief. The plate floor for `points` drops from
6.55 to **5.6 mm** (3.2 pocket + 2.4 backing). The cap grows by 0.95 mm, so
the plate is 103.8 mm tall at a 100 mm channel length.

| Channel length | Lower slot Z | Upper slot Z | Seats Z | Wells Z | Solid between |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 (both presets) | 26.6–50.0 | 76.6–100.0 | 41.5, 91.5 | 35.5, 85.5 | 26.6 mm |
| 125 (e.g. 25° cradle) | 51.6–75.0 | 101.6–125.0 | 66.5, 116.5 | 60.5, 110.5 | 26.6 mm |

**Mount type.** `points` now declares its own `multibuild-fixpoint-slot`
(`mount_for_values`). Its contract (`tests/mount_contracts.py`) uses the
measured head as the fixture. It checks, per slot:

- the seated head is clear
- the head is held when pulled 0.5, 1 and 2 mm off the wall
- the slot is closed 1 mm past the seat (≈20 mm³ foul)
- the path from wholly outside the back face, into the well and up to the
  seat, is clear
- the lip is narrower than the head at the face and wider behind it
- the backing is at least 2.4 mm
- no two pockets fuse (≥ 0.9 mm apart)

The `channel` and `openconnect` styles are unchanged. Their preset STLs
regenerate byte-identical.

**Load path.** The worst case is the same 30 N down at the front rim. The
moment pulls the upper heads straight off the wall and the lower ones into
it. The upper lips take the pull-off on their 45° faces: the root is 2.5 mm
of PETG/PCTG behind a 0.4 mm land (the official profile), backed by ≥ 3.8 mm
of plate at default thickness. Gravity bears on the lip's top end. Release
force is [U] (research §3). Fix Points have no detent, so a hard upward bump
can lift the holder 6 mm and off, as with any Fix Point accessory.

**Printability.** The print audit excludes the slot cutters as library
geometry, as for the other styles. Run without that exclusion, the audit
reports a 90° downward face inside the pockets. Located on
`bambu_reusable_200_points`, each pocket has exactly two such faces, both
narrower than one 0.42 mm extrusion line:

- the lip's face land, 4.97 × 0.40 mm, at the top of the face opening
- the step at the top of the well, 7.04 × 0.30 mm, at full depth

Every other downward face in the pockets is the profile's 45° chamfer. So
the standing print needs no support in the pockets. The model header's
pocket allowance is kept, but these slots do not use it.

### Volumes

| Preset | mount_style | Volume (mm³) |
| --- | --- | ---: |
| `bambu_reusable_200` | channel | 104,214.349 |
| `ams_generic_200` | channel | 105,881.681 |
| `bambu_reusable_200_points` | points (Fix Point) | 116,558.054 |
| `ams_generic_200_points` | points (Fix Point) | 118,225.386 |
| `bambu_reusable_200_openconnect` | openconnect | 136,365.583 |
| `ams_generic_200_openconnect` | openconnect | 138,724.716 |

Both points presets are **+7,622.221 mm³ (+7.0 %)** heavier than before
(108,935.833 / 110,603.165 after pst-dkqef). That is all pocket size:

- each Fix Point slot removes 979.568 mm³, against 2,768.824 mm³ for the
  Multiconnect segment (4 × 1,789.256 = 7,157.0 mm³)
- the closed cap is 0.95 mm taller (≈465 mm³)

The plate outline and body are unchanged. The slot is the official
envelope, so nothing is oversized.


## Inboard cap rear land (pst-2q3ej)

### Defect

The inboard rail cap had the same unbacked rear knife that pst-dkqef fixed
outboard. Between cap_inner and the rail's inner face nothing stands
behind rear_y, so the saddle tangent met the cap's vertical rear face in a
25–45° edge. The dense probe (19 × 19 UV, inboard cap rear end only) read
0.02–0.03 mm at both presets and at 66 / 0.25 / 25. The print audit passed
it by sampling luck.

Separately, 68 and 68.5 / 0.25 / 40 failed to build on main. OCCT could not
chamfer the cap's rear vertical edges in the narrow-guide branch.

### Fix

`cap_land_cutter()` carries the outboard land across the cap:

1. The same WEB/2 land and 0.4 × 45° rear chamfer as `rear_land_cutter()`
   (shared `land_stage()` helper).
2. A 30° ramp rises 0.4 mm to the rail's inner face, so the land does not
   meet the rail at 90°. The cutter stops at that face; the rail backs the
   cap outboard of it.
3. 45° 0.4 mm bevels finish the land's edge at cap_inner and the cap's
   vertical rear corner there.

`cap_corner_wedge()` is the explicit 45° fill for the concave cap/rail rear
corner. It mirrors `rear_corner_wedge()`.

The cap's rear corners are built, not chamfered, so `holder()` drops them
from the vertical and rear chamfer sets. That removes the chamfer that
failed at 68 / 68.5 / 0.25 / 40.

`holder()` cuts the land, and fuses the wedge, after the top clip. Cutting
the cap in `placement_aids()` left a sliver on the rear knife line, between
the cap curtain's 0.01 mm lift and the clip. At cradle_angle = 45 the clip
fused that sliver into an unorientable saddle face, and every 45° case
failed the R1 joint fillet. The wedge's top stops just above the land's ramp
at the rail face, so its 0.1 mm overlap into the rail stays under the
saddle.

### Validation

A 64-case gate builds every case as one valid solid. Every case passes the
print audit, the finished-edge classes, and the inboard and outboard dense
rear probes (no wall under 0.9 mm). The cases are:

- all six presets
- the seven production corners
- the points grid
- every endpoint
- the bead's corners: 66 / 67 / 50 × 0.25 × 25, 66 / 0.5 / 25,
  66 / 1.5 / 45 and 68 / 68.5 × 0.25 × 40

Minimum walls are 1.08–2.40 mm, the worst overhang is 45.0°, and the worst
exposed edge is 90.0°. The inboard dense probe reads 0.9 mm (its march
cap) at both presets, at 66 / 0.25 / 25, at 68 / 0.25 / 40 and at the
default with cradle_angle = 45. On main it reads 0.02–0.03 mm.

New tests: `test_inboard_cap_rear_end_has_no_knife` (both presets and
66 / 0.25 / 25), plus `cap-land-narrow-40` and `cap-land-narrow-40-half`
edge cases (68 and 68.5 / 0.25 / 40, which do not build on main).

### Volumes

| Preset | Before (mm³) | After (mm³) | Change |
| --- | ---: | ---: | ---: |
| `bambu_reusable_200` | 104,214.349 | 104,201.224 | −13.125 (−0.01%) |
| `ams_generic_200` | 105,881.681 | 105,868.556 | −13.125 (−0.01%) |
| `bambu_reusable_200_points` | 116,558.054 | 116,544.929 | −13.125 (−0.01%) |
| `ams_generic_200_points` | 118,225.386 | 118,212.261 | −13.125 (−0.01%) |
| `bambu_reusable_200_openconnect` | 136,365.583 | 136,352.463 | −13.120 (−0.01%) |
| `ams_generic_200_openconnect` | 138,724.716 | 138,711.600 | −13.116 (−0.01%) |

The land removes the knife from both caps, about 6.6 mm³ per side.

## openConnect rows spread top and bottom (pst-fmvzb)

Operator request (2026-10-01): the four openConnect slots sit two at the top
and two at the bottom of the plate. The upper row is unchanged. The lower
row drops from one tile below it to the lowest 28 mm grid row whose on-ramp
floor stays WEB + 0.5 = 2.9 mm above the bed relief (`oc_seats()`, the
cutter-bbox rule the openConnect layout test already asserted). Columns
(±14), on-ramp offsets and the install motion are unchanged.

| Grid length | Old lower seat | New lower seat | Row spacing | Lower slot floor |
| ---: | ---: | ---: | ---: | ---: |
| 112 (both presets, 25° corners) | 75.4 | 19.4 | 84 (3 tiles) | 6.2 |
| 84 (45° corners) | 47.4 | 19.4 | 56 (2 tiles) | 6.2 |

`OC_SLOT_BOTTOM` (13.2 mm, the on-ramp's clearance floor below the seat)
is derived from the openConnect constants and pinned to the cutter bbox by
a test, as `OC_SLOT_TOP` is. A grid with no room for a second tile raises a
ValueError naming the minimum root_height (> 28 mm); the parameter ranges
only reach 84 and 112. A new test checks solid plate between the rows over
the full pocket footprint, the points-style twin.

The `channel` and `points` styles are unchanged; their preset STLs
regenerate byte-identical.

### Volumes

| Preset | mount_style | Volume (mm³) |
| --- | --- | ---: |
| `bambu_reusable_200` | channel | 104,201.224 |
| `ams_generic_200` | channel | 105,868.556 |
| `bambu_reusable_200_points` | points (Fix Point) | 116,544.929 |
| `ams_generic_200_points` | points (Fix Point) | 118,212.261 |
| `bambu_reusable_200_openconnect` | openconnect | 136,352.459 |
| `ams_generic_200_openconnect` | openconnect | 138,711.596 |

The openConnect presets change by −0.004 mm³ (136,352.463 → 136,352.459 and
138,711.600 → 138,711.596, against main after pst-2q3ej): moving a pocket removes the same slot volume,
and the difference is OCCT volume-integration noise at the new
position. The plate outline and body are unchanged.
