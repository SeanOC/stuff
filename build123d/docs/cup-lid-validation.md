# Cup-lid holder v2.1 — pst-5slt

Revises v2 under the same `holder_cup_lid` registry name so a lid can slide
into the cradle from above. Implements the reviewed lower-segment domain
and the mayor's shortened-lip decision in pst-5slt. The inherited pin cavity
clearance still accepts equality at the 7.3 mm base endpoint.
Physical PLA/PCTG printing and bolt/lid fit remain tracked in **pst-mvno**.

## Geometry, orientation and material

The plate is a circular segment entirely below the circle center, with an
exactly planar front at Y=5 mm. At defaults, the circle center is Z=16.5 mm;
the top and bottom chords are at Z=15 and Z=-15 mm (circle-relative heights
-1.5 and -31.5 mm). The mirrored channels widen upward and converge toward
the bed, matching reference photo 03. The pins and bolt use the plate's
center between the chords, not the circle center.

Defaults: circle diameter 91.9 mm, chord spacing 30 mm, plate 5 mm,
walls/lips 3 mm, shoulder gap 13.3 mm, radial lip reach 4.2 mm. The measured
finished envelope, including rear cones and edge relief, is
**91.813 × 24.85 × 30 mm** (XYZ).

| Shape parameter | Default | Range | Step |
| --- | --- | --- | --- |
| `lid_diameter` | 85.3 mm | 84–130 mm | 0.1 mm |
| `mount_height` | 30 mm | 20–30 mm | 0.5 mm |
| `top_chord_offset` | 1.5 mm | 0.5–2 mm | 0.5 mm |
| `lip_end_margin` | 2 mm | 1–5 mm | 0.5 mm |

The lid-diameter and mount-height ranges supersede v2's 60–130 and 20–45 mm
ranges. With outer radius `R` and bottom depth
`b = top_chord_offset + mount_height`, dimensions require both
`b <= R/sqrt(2)` and `b <= R - 2*tab_thickness - 1`; violations raise
`ValueError`. The default outer-wall tangent leans **43.277°** from vertical.
Every individual parameter endpoint builds with the other defaults; some
combined endpoints are deliberately rejected. For example, lid diameter 84,
tab thickness 2, offset 2 and mount height 30 mm violate the lean guard;
the same combination with default 3 mm tabs is accepted.

The walls remain full height. Each lip ends above the bed, using inner lip
radius `R_lip = R - tab_thickness - (shoulder_depth - lid_clearance)` and
circle-relative stop height `-min(b, R_lip/sqrt(2)) + lip_end_margin`.
At defaults, `R_lip=38.75 mm` and the stop is **Z=-8.900 mm** in the plate
frame, 6.100 mm above the bed. A 45° end ramp rises inward from that stop;
its R1 junction blends into the wall. The inner lip arc ends above the stop,
whose conservative tangent bound is **40.957°**. Only plate and walls touch
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

Default `sippy_cup_85mm` volume, v2 → v2.1:
**17,016.661 → 16,130.034 mm³ (-5.21%)**.
The lower segment and shortened lips reduce material while maintaining
3 mm walls/lips and R1 junctions.
There are no other cup-lid presets.

## Pins and board clearance

Pins are true cones at exactly X=±25 mm, Y=Z=0; 25 mm is a fixed Multibuild
pitch, not a configurable parameter. Defaults: base Ø7.1, tip Ø0, half-angle
45°, derived length 3.55 mm. Ranges: base 6.9–7.3 mm, tip 0–0.8 mm, half-angle
45–49°. The pure `pin_length_mm` helper enforces 2.4–6 mm projection.

These are **loose anti-rotation cones**, not chamfer seats. Their bases are
coplanar with the plate back at Y=0, allowing the plate to sit flush. The
mouth rim limits lateral motion (default ±0.2 mm); the center bolt clamps.
The cavity is 7.5−z mm in diameter for depth 0–1.5 mm, then 6 mm through
6.4 mm depth. Tests sweep the full pin length at 0.05 mm intervals for all
pin parameter corners and require at least 0.1 mm radial clearance.

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

## Bolt seat — operator-approved best guess

| Parameter | Default | Range |
| --- | --- | --- |
| `bolt_clearance_diameter` | 8 mm | 7.5–8.5 mm |
| `countersink_diameter` | 12.5 mm | 10.5–13 mm |
| `countersink_angle` | 90° included | 90–100° |

These are **BEST GUESS** fit dimensions, not published Multibuild bolt specs.
The front countersink has depth 2.25 mm, leaving 2.75 mm plate backing.
Combinations leaving less than 2.4 mm backing or no more than 2 mm diametral
head/shank difference raise `ValueError`. The hole is round and horizontal;
its upper curved shank surface is the only accepted print-audit finding.

## Digital print audit

Unexcluded default: overhang **72°**, one downward curved face (the shank
cylinder); bridge **0 mm**, sampled minimum wall **1.58 mm**, bed chamfer
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
  min wall   :  1.58 mm (≥ 0.9 mm) OK
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

Validation of geometry commit `dd3d1b4` in [PR #114](https://github.com/SeanOC/stuff/pull/114):

- Cup-lid geometry suite: **110 passed**, including all **34 individual
  parameter endpoints**, lower-segment outline, inner/outer lean, accepted
  and rejected combinations, lip ramps, bed relief, pins, bolt, and symmetry.
- Cup-lid print-audit suite: **3 passed**, with the standing orientation and
  exact shank-only exclusion above. Audit thresholds and exclusions are unchanged.
- Full CAD coverage: **319 passing tests** across the full run and final
  cup-lid rerun, with **1 expected xfail** for the existing openGrid smoke
  model. The first full run found an overly strict new ramp-bound assertion
  at the R1 blend; the corrected test checks the actual ramp plane and bed
  clearance, and the subsequent 110-test cup-lid run passed.
- `npm test`: **291 passed**. The manifest freshness check passed; the
  regenerated STL is watertight and consistently wound.
- GitHub checks for build123d models, unit tests, and Playwright passed on
  that commit. Independent review also reported all 34 endpoints passing
  the production audit and 141 valid pairwise endpoint combinations building
  as single valid solids; its fresh STL export matched the committed file.

These are digital checks. Physical PLA/PCTG printability and lid/bolt fit
still require the downstream **pst-mvno** validation.
