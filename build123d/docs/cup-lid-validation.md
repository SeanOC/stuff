# Cup-lid holder v2.3 — pst-rlnc

Revises v2.2 (main `1a70f46`, PR #115) after Sean's print feedback:
the pins need more engagement and the seat must match his measured bolt
head. Pin fit now defaults to 0.1 mm interference per side (derived base
Ø7.7 mm). The tapered seat ends at a flat shoulder, 2.3 mm below the front.
The plate returns to 5 mm with 2.7 mm backing. Physical PLA/PCTG printing
and bolt/lid fit with the new STL remain tracked in **pst-mvno**.

## Geometry, orientation and material

The plate is a circular segment entirely below the circle center, with an
exactly planar front at Y=5 mm. At defaults, the circle center is Z=16.5 mm;
the top and bottom chords are at Z=15 and Z=-15 mm (circle-relative heights
-1.5 and -31.5 mm). The mirrored channels widen upward and converge toward
the bed, matching reference photo 03. The pins and bolt use the plate's
center between the chords, not the circle center.

Defaults: circle diameter 92.5 mm, chord spacing 30 mm, plate 5 mm,
walls/lips 3 mm, shoulder gap 13.6 mm, radial lip reach 3.9 mm. The measured
finished envelope, including rear cones and edge relief, is
**92.413 × 25.45 × 30 mm** (XYZ).

| Shape parameter | Default | Range | Step |
| --- | --- | --- | --- |
| `lid_diameter` | 85.3 mm | 84–130 mm | 0.1 mm |
| `mount_height` | 30 mm | 20–30 mm | 0.5 mm |
| `top_chord_offset` | 1.5 mm | 0.5–2 mm | 0.5 mm |
| `lip_end_margin` | 2 mm | 1–5 mm | 0.5 mm |
| `lid_clearance` | 0.6 mm | 0.1–0.8 mm | 0.05 mm |
| `shoulder_depth` | 4.5 mm | 2.2–10 mm | 0.1 mm |
| `plate_thickness` | 5 mm | 5–9 mm | 0.5 mm |

The lid-diameter and mount-height ranges supersede v2's 60–130 and 20–45 mm
ranges. With outer radius `R` and bottom depth
`b = top_chord_offset + mount_height`, dimensions require both
`b <= R/sqrt(2)` and `b <= R - 2*tab_thickness - 1`; violations raise
`ValueError`. The default outer-wall tangent leans **42.928°** from vertical.
Every individual parameter endpoint builds with the other defaults; some
combined endpoints are deliberately rejected. For example, lid diameter 84,
tab thickness 2, offset 2 and mount height 30 mm violate the lean guard;
the same combination with default 3 mm tabs is accepted.

The walls remain full height. Each lip ends above the bed, using inner lip
radius `R_lip = R - tab_thickness - (shoulder_depth - lid_clearance)` and
circle-relative stop height `-min(b, R_lip/sqrt(2)) + lip_end_margin`.
At defaults, `R_lip=39.35 mm` and the stop is **Z=-9.325 mm** in the plate
frame, 5.675 mm above the bed. A 45° end ramp rises inward from that stop;
its R1 junction blends into the wall. The inner lip arc ends above the stop,
whose conservative tangent bound is **41.017°**. Only plate and walls touch
the bed; the lips capture the upper arc while the walls support the lid below.

Print standing on the lower chord, **Z=-15 mm with +Z up**. No orientation
rotation is necessary; translate the STL upward 15 mm to the slicer bed.
The layer planes contain the forward-pull (+Y) load at the tabs/lips;
ordinary downward lid weight (-Z) compresses the plate. Continuous R1 webs
spread bending loads at both plate/wall and wall/lip junctions. This is a
geometric load-path argument, not FEA or a physical strength certification.
PLA's brittleness/creep and PCTG's sag/stringing still require the downstream
print test; the digital check uses the 45° limit for both materials.

The revolved profile incorporates full wall-thickness overlap into the plate
and full lip-thickness overlap into the wall along Y, rather than joining
bodies only at tangent faces. R1 internal blends follow the near-vertical
end arcs. All edges bounding the lower chord have 0.4 mm 45° bed relief
(range 0.3–0.5). The upper chord perimeter and exposed rear/front arcs have
0.5 mm chamfers. Functional shoulder-contact and seating edges stay sharp;
cone pin surfaces and the countersink remain functional geometry.

The bed chamfers use OCP's distance/angle construction: equal setbacks on
an oblique arc/chord intersection do not make a 45° chamfer. The curved
chamfer's spline approximation can deviate by under 0.001°; the audit uses
that numeric allowance and proves a 45.01° curved overhang still fails.
Upper chord edges use equal-distance chamfers. Junction fillets are applied
after the chord and exposed-arc relief to avoid an invalid OCP face at the
0.5 mm top-offset endpoint.
One finished half is mirrored to avoid independent spline-fit asymmetry.

Default `sippy_cup_85mm` volume, actual main `1a70f46` v2.2 → v2.3:
**19,781.621 → 16,085.415 mm³ (−18.69%)**.
The shallower seat permits a 1.5 mm thinner plate while retaining 2.7 mm
backing. Walls/lips remain 3 mm with R1 junctions.
There are no other cup-lid presets.

## Pins and board engagement

Pins are true cones at exactly X=±25 mm, Y=Z=0; 25 mm is a fixed Multibuild
pitch. Defaults: base Ø7.7, tip Ø0, half-angle 45°, derived length 3.85 mm.
The sole base control is `pin_fit`: −0.2…0.3 mm per side, step 0.05,
positive for interference. Base diameter is derived as `7.5 + 2*pin_fit`,
giving Ø7.1…8.1 mm. Tip diameter remains 0–0.8 mm and half-angle 45–49°.
The pure `pin_length_mm` helper enforces 2.4–6 mm projection; the actual
endpoint combinations span 2.738…4.05 mm.

The cones engage the board mouth at positive fit. Their bases remain at the
plate back, Y=0; the center bolt clamps. The cavity is 7.5−z mm in diameter
for depth 0–1.5 mm, then 6 mm through 6.4 mm depth. Tests sweep the full pin
length at 0.05 mm intervals for fit {−0.2, 0.1, 0.3} × tip {0, 0.8} ×
half-angle {45, 49}, requiring `pin_d(z) <= cavity_d(z) + 2*pin_fit`.
The −0.2 fit reproduces the old default Ø7.1 pin; −0.1 reproduces the old
maximum Ø7.3 pin. These are pin-only regression fixtures.
Passing the removed `pin_base_diameter` parameter raises an unknown-parameter error.

Dimension evidence: [Multibuild core-part documentation](https://docs.multibuild.io/beginner-section/core-parts-documentation)
for the 25 mm Multi Unit and small-thread holes; the
[tile generator author's measurements of the official remix STEP](https://github.com/asciipip/multiboard-parametric-stacked/blob/master/multiboard_base.scad)
(lines 51–56, 87–95) for 6 mm throat, 7.5 mm mouth and 6.4 mm board depth.
These are cited measurements, not independently measured official files.

A true zero-diameter cone tip exposes an OCP STL-export artifact: one
collapsed triangle with repeated vertices per pin. The shared STL exporter
removes only those triangles, leaving every real triangle and the envelope
unchanged. Both the preset bake and live download use this path. Tests check
watertightness and exact equality of all retained triangles; no hole filling
or tip blunting is performed.

## Bolt seat — measured head with a flat shoulder

| Parameter | Default | Range |
| --- | --- | --- |
| `bolt_clearance_diameter` | 8 mm | 7.8–8.5 mm |
| `head_top_diameter` | 16 mm | 15–18 mm |
| `head_bottom_diameter` | 12 mm | 10–14 mm |
| `head_thickness` | 2.1 mm | 1.8–2.4 mm |
| `head_clearance` | 0.2 mm per side | 0–0.4 mm |
| `head_recess` | 0.2 mm | 0–0.5 mm |

Sean measured a head tapering from Ø16 to Ø12 over 2.1 mm. One conical
cutter follows that slope, `(16−12)/(2*2.1)`, from a Ø16.781 front opening
to Ø12.4 at depth 2.3 mm. At that depth a flat annular shoulder steps down
to the Ø8 through-hole. There is no straight head bore. The head's top rim
sits 0.2 mm below the front with 0.2 mm radial clearance (about 0.19 mm
normal to the tapered surface).

Guards require head top > bottom, at least 1 mm shoulder per side, and at
least 2.4 mm backing. Defaults leave 2.7 mm backing and a 2.2 mm shoulder.
Every individual public endpoint builds; incompatible combinations raise.
Tests accept exactly 2.4 mm backing and 1 mm shoulder. The removed
`countersink_diameter` and `countersink_angle` controls raise as unknown.

The cone half-angle is 43.60°; its upper roof is 46.40° from vertical over
only 2.3 mm. This functional slope matches the measured bolt and is retained.
The sampled audit adds no seat finding, so the round horizontal shank is
still the sole accepted finding.

## Digital print audit

Unexcluded default: overhang **72°**, one downward curved face (the shank
cylinder); bridge **0 mm**, sampled minimum wall **1.60 mm**, bed chamfer
present. The reported 72° is the sampled maximum, not an assertion that a
round hole's analytic ceiling is under 90°.

The production gate remains enabled. Its sole exception is the exact
shank cylinder, Ø8 mm from Y=0 to Y=5 mm, with **no bounding-box margin**.
The countersink, pins and all edge treatments remain audited. A dedicated
test proves every unexcluded failing face lies in that cylinder, the
excluded report passes, and a synthetic downward fillet outside it fails.

```text
print audit: holder_cup_lid  (up = (0.00, 0.00, 1.00))
  overhang   :  45.0°   (≤ 45°) OK
  bridge     :   0.0 mm (≤ 10 mm) OK
  min wall   :  1.60 mm (≥ 0.9 mm) OK
  dn fillets :     0     (= 0)    OK
  bed chamfer: present   (warn)
  => PASS
```

Reproduce from `build123d/`:

```bash
uv run pytest tests/test_cup_lid.py tests/test_toolchain.py
uv run pytest tests/test_print_audit.py -k cup_lid -s
uv run python scripts/manifest.py
uv run python scripts/export.py
uv run python scripts/export.py --presets-only out/presets
```

The committed review render faces the lips. In the exported GLB frame, its
isometric/front view directions are `(1, 1, -1)` and `(0, 0, -1)`, with
the renderer's usual Y-up vector; the top view is unchanged. These camera
directions replace the default rear-facing views for this review image.
The STL keeps the assembly/print coordinate frame above.

Validation for pst-rlnc:

- Cup-lid geometry and print-audit suites: **136 passed**, including all
  **40 individual parameter endpoints**, Ø16.781 front opening, the
  Ø12.4-to-Ø8 flat shoulder, 2.4 mm backing and 1 mm shoulder boundaries,
  pin interference sweeps, lip ramps, bed relief, edge classification and symmetry.
- Raw head slope, backing and shoulder failures are tested with test-only
  widened parameter domains. Public range rejection is tested separately.
- Toolchain and manifest suites: **30 passed**.
- `npm test`: **291 passed**. Regenerated STL is watertight and consistently
  wound. Manifest regenerated from the updated defaults and ranges.
- Compared the render against all four reference photos: the paired channels,
  central bolt, two rear pins and standing profile remain represented.

These are digital checks. Physical PLA/PCTG printability and lid/bolt fit
still require the downstream **pst-mvno** validation.
