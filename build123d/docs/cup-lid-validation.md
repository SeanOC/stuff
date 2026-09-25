# Cup-lid holder — pst-tti3

The end-standing digital print audit passes with the front countersink.
Bolt dimensions are **BEST GUESS**, explicitly approved by Sean at 18:43Z
on pst-tti3. Physical fit remains to be tested in pst-mvno.

## Geometry and material

Default `sippy_cup_85mm`: lid 85.3 mm, shoulder height 13 mm and radial
shoulder depth 4.5 mm. Opening radius 42.95 mm includes 0.3 mm clearance;
maximum lip engagement is 4.2 mm, contact band 6 mm, axial gap 13.3 mm.
Pins lie at X = ±25 mm relative to the center opening; pair spacing permits
50/100 mm only, with envelope checks. Each pin has a rounded top, inscribed
45° lower V and 0.5 mm tip chamfer.

The lower channel has a flat bed face. The upper channel's ceiling slopes
at 45° across its axial gap, with a retaining lip roofed across its width. This preserves
shoulder clearance. No audit exclusions or threshold changes were used.

Volume, `sippy_cup_85mm`: **19,834.554 → 19,668.273 mm³ (-0.84%)**
for the bolt-seat revision (original prototype: 17,807.799 mm³).
The countersink and larger clearance hole remove material; the strengthened
lip and junction blends are unchanged. Envelope: **98.5229 × 31.5458 × 28 mm**
(XYZ).
The plate spans the capture locations; lips use only their contact band.
Worst load is a forward pull (+Y); ordinary lid weight (-Z) lies along
layers when standing on the -X end. Bed perimeter chamfer is 0.4 mm.
The upper lip now has a full 4 mm section along the forward-pull direction.
Its underside slopes at 45° across Z, ending in a 4 mm axial land rather
than thinning to zero along Y. Maximum engagement remains 4.2 mm; this is
not increased into the 4.5 mm shoulder. A regression test probes near the
engagement tip through 3.2 mm of material and enforces ≥1.6 mm audit wall.
The revised whole-part minimum is 2.4 mm.

R1 side-junction fillets blend both end channels into the plate, running
parallel to print-up so no downward curved surface is added. The upper
channel roof provides a continuous sloped web into its outer wall; wall/
plate overlap is the plate thickness (at least 4 mm), exceeding the 2.4 mm
wall. Exposed plate rails, upper end perimeter and front lip rims have
0.3–0.4 mm chamfers. Lid-contact faces, pin-fit geometry and engagement
ridges remain functional datums. The bed perimeter retains 0.3–0.5 mm
relief. Physical validation is tracked separately in **pst-mvno**.

## Passing digital print audit

```text
print audit: holder_cup_lid  (up = (1.00, 0.00, 0.00))
  overhang   :  45.0°   (≤ 45°) OK
  bridge     :   0.0 mm (≤ 10 mm) OK
  min wall   :  2.40 mm (≥ 0.9 mm) OK
  dn fillets :     0     (= 0)    OK
  bed chamfer: present   (warn)
  => PASS
```

Reproduce from `build123d/`:

```bash
uv run pytest 'tests/test_print_audit.py::test_model_print_audit[holder_cup_lid]' -s
```

The STL uses assembly coordinates; rotate +X upward to print standing on
its -X end. Passing the geometric audit is not a physical print test.

## Bolt seat — BEST GUESS, operator approved

Sean authorized these estimates on pst-tti3 at 18:43Z; they are **not
published Multibuild spec dimensions**:

| Parameter | Default | Range |
| --- | --- | --- |
| `bolt_clearance_diameter` | 8.0 mm (~7.6 mm major + 0.4 mm clearance) | 7.6–9 mm |
| `countersink_diameter` | 13.0 mm | 11–15 mm |
| `countersink_angle` | 90° included | 90–120° |

The default head depth is 2.5 mm. The cone opens on the concave front (+Y);
its 13 mm diameter is measured at the center tangent plane Y=6 mm. The
cone continues through the curved front so it has no cylindrical pocket
ceiling. A head at that tangent plane is flush at the center and slightly
recessed at its sides. The shank exits the flat back with a 45° teardrop
roof toward +X. Angles below 90° are excluded for support-free printing.

Combinations leaving less than 2.4 mm backing behind the cone are rejected:
the default leaves 3.5 mm; a 4 mm plate needs a smaller/shallower seat.
Geometry tests probe mouth diameter, seat depth, back exit and roof,
in addition to the parameter boundaries and full print audit.

The pin dimensions use the [tile generator author's measurements of the
official remix STEP](https://github.com/asciipip/multiboard-parametric-stacked/blob/master/multiboard_base.scad)
(lines 51–56, 87–95): throat 6.0 mm, board depth 6.4 mm. Diameter 5.6 mm
leaves 0.2 mm per side; projection 5.9 mm leaves 0.5 mm axial clearance.
These are cited measurements, not independently measured official files.

## Validation

- Full `uv run pytest`: **289 passed, 1 xfailed** in 296 s.
- Targeted model tests plus registered print audit: **85 passed**.
- `npm test`: **291 passed** on this revision.
- All registered models exported successfully after channel changes.
- Manifest regenerated; review render and STL regenerated from revised model.
- Root `python3 scripts/render-all.py`: **28/28 passed** earlier in this PR;
  unrelated SCAD thumbnail differences discarded.

The review render uses the exported mesh rotated to show its front channels.
