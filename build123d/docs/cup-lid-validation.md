# Cup-lid holder v2 — pst-vks5

Replaces the rejected v1 shape under the same `holder_cup_lid` registry name.
Implements canonical v5 plus Mayor Revision 7 and its plan-review clarification:
pin cavity clearance accepts equality at the 7.3 mm base endpoint.
Physical PLA/PCTG printing and bolt/lid fit remain tracked in **pst-mvno**.

## Geometry, orientation and material

The plate is the central circular segment between two parallel chords, with
an exactly planar front at Y=5 mm. The two end walls and inward lips are
mirror images across X=0. Defaults: circle diameter 91.9 mm, chord spacing
30 mm, plate 5 mm, walls/lips 3 mm, shoulder gap 13.3 mm, radial lip reach
4.2 mm. Envelope: **91.9 × 24.85 × 30 mm** (XYZ, including rear cones).

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

The chord chamfers use OCP's distance/angle construction: equal setbacks on
an oblique arc/chord intersection do not make a 45° chamfer. The curved
chamfer's spline approximation can deviate by under 0.001°; the audit uses
that numeric allowance and proves a 45.01° curved overhang still fails.
One finished half is mirrored to avoid independent spline-fit asymmetry.

Default `sippy_cup_85mm` volume: **19,668.273 → 17,016.661 mm³ (-13.48%)**.
The flat plate and symmetric full-height end channels remove the v1 concave
slab/asymmetric roof while maintaining 3 mm walls/lips and R1 junctions.
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
cylinder); bridge **0 mm**, sampled minimum wall **2.67 mm**, bed chamfer
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
  min wall   :  2.67 mm (≥ 0.9 mm) OK
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

The committed review render is the exported GLB viewed from the front:
rotate its scene 180° about the viewer's Y axis before `render_review`.
The STL keeps the assembly/print coordinate frame above.

Validation on this revision: full `uv run pytest tests/` **306 passed,
1 expected xfail** (existing openGrid smoke-model spec exemption); `npm test`
**291 passed**. The Python suite includes the 30-endpoint cup-lid parameter
sweep, all preset bakes, registered audits and live STL download regression.
