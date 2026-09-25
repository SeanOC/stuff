# Cup-lid prototype — pst-tti3

**Draft; do not merge or treat the STL as a validated support-free print.**
The prototype makes the geometry and remaining failures reviewable. It does
not complete the bead's acceptance criteria.

Sean's measured default is `sippy_cup_85mm`: lid diameter 85.3 mm, shoulder
height 13 mm, radial shoulder depth 4.5 mm. The opening radius is 42.95 mm
(0.3 mm radial clearance); lip engagement is 4.2 mm and the contact band is
6 mm high, within the 13 mm shoulder. The channel has 13.3 mm axial clearance.
The model interprets shoulder height as axial depth and shoulder depth as
radial engagement. The short-axis front concavity has the same 42.95 mm
radius; the channel walls follow the lid circle in the wall plane.

The two pin axes sit at X = -25/+25 mm, Y = Z = 0, relative to the center
hole, in one row of small holes. Allowed pin spacings are 50 and 100 mm:
25 or 75 mm would put the individual pins halfway between the small holes
relative to the central fastener. A 100 mm pair is rejected for a lid too
small to leave the required mounting margin.

## Geometry and material

Before: no previous build123d model, so volume comparison is **N/A**.
After, `sippy_cup_85mm`: **17,807.799 mm³**, one watertight solid.
Envelope in the assembly frame: **90.7 × 29.9458 × 28 mm** (X × Y × Z).
Depth includes the rear pins, plate concavity, shoulder gap and retaining
lips. The originally requested `thickness + pin_length` would omit the
front channels and is not the whole-part bounding box.

The plate spans the two lid capture locations. Each lip has its own small
contact band rather than extending the full plate height. Worst-case load
is a forward pull (+Y) bending the lips/plate; normal lid weight (-Z) lies
along layers in the requested +X print orientation. Junction blending and
complete exposed-edge treatment remain unfinished pending channel redesign.

## Measured print audit

The mayor's revised orientation is modeled: **-X end on bed, +X up**,
plate vertical and pins horizontal. The pins have an upper semicircle and
inscribed 45° lower flats, with a 0.5 mm tip lead-in. A flat-topped D pin was
experimentally rejected: it still has a circular underside and scored 90°
overhang plus one downward curved face in an isolated plate/pin audit.
The revised pins are not among the full-model audit's flagged faces, but
their initial short cantilever ridge still needs slicer/physical validation.
The center through-hole has a 45° roof toward +X. The plate's bed-contact
end edges have a 0.4 mm chamfer.

```text
print audit: holder_cup_lid  (up = (1.00, 0.00, 0.00))
  overhang   :  90.0°   (≤ 45°) FAIL
  bridge     :   0.0 mm (≤ 10 mm) OK
  min wall   :  2.40 mm (≥ 0.9 mm) OK
  dn fillets :     4     (= 0)    FAIL
  bed chamfer: present   (warn)
  => FAIL: overhang 90.0° > 45° (steeper than 45° from vertical); 4 downward-facing curved face(s) [CYLINDER@(-45,0,0), CYLINDER@(-45,15,0), CYLINDER@(43,14,-0), CYLINDER@(39,23,-0)] — use a 45° chamfer, not a bottom fillet

```

The remaining flagged faces are the **end-channel surfaces**, including
the upper channel's concave underside and lip underside. Standing on an end
does not make these faces vertical. They must be redesigned while preserving
lid clearance, or the print arrangement must change; this prototype does
not assert that either PLA or PCTG can print them without support. No cutter
exclusions or modified audit thresholds were used.

Reproduce from `build123d/`:

```bash
uv run python - <<'PYCODE'
from holders.cup_lid import SPEC
from tests.print_audit import audit
part = SPEC.build(SPEC.resolve_values())
print(audit(part, orientation=SPEC.print_orientation, model=SPEC.name).format())
PYCODE
```

## Center mount evidence still missing

The official [Small Thread Fix Point](https://thangs.com/m/1123334) and
[core-parts documentation](https://docs.multibuild.io/beginner-section/core-parts-documentation)
describe a **slide-on** receiver, not a plain clearance-hole attachment.
The required Fix Point head/shank measurements were not found in QuackWorks
or the accessible official documentation. The official STEP download page
was inaccessible in this environment. No dimensions were inferred from its
photo or invented as spec constants.

The current **7.2 mm opening is provisional small-thread bolt clearance**:
7 mm published thread-major dimension plus 0.2 mm diametral clearance. It
is not verified as a Fix Point receiver. Need confirmation of a through-bolt
mount versus the official receiver and, for the latter, accessible official
geometry/dimensions. Until then, this remains a draft with the bead open.

The pin dimensions are based on the [tile generator author's measurements
of the official remix STEP](https://github.com/asciipip/multiboard-parametric-stacked/blob/master/multiboard_base.scad)
(lines 51–56, 87–95): 6.0 mm minimum hole, 6.4 mm board depth. The 5.6 mm
pin diameter leaves 0.2 mm clearance per side; 5.9 mm projection leaves
0.5 mm axial clearance. These are cited secondary measurements of the
official STEP, not independently measured official files; direct source
verification remains part of the uncompleted dimension acceptance criterion.

## Validation

- Targeted tests: **69 passed**, including each individual numeric parameter
  minimum/maximum, watertightness, single body, positive volume, actual pin
  probes, lattice alignment, through-hole probes and shoulder engagement.
- `npm test`: **291 passed**.
- Manifest regenerated; all registered models exported successfully.
- Full `uv run pytest`: **253 passed, 1 xfailed, 1 failed** in 190 s.
  The failure is `test_model_print_audit[holder_cup_lid]`, reproduced above.
  The later 20 added individual-boundary cases passed in the targeted sweep.
- Root render-all is running; its unrelated regenerated thumbnails will not
  be included in this model's change.

The review render uses the same exported mesh, rotated to show the channel
face. The STL remains in the assembly coordinate frame; the requested print
orientation would require rotating +X upward. It is intentionally labeled a
prototype rather than supplied as a print-ready artifact.
