# Cup-lid holder — pst-tti3

The end-standing digital print audit now passes. The front bolt seat is
unfinished; the STL is for geometry review until that interface is verified.
The model is registered as a smoke/scaffold model and excluded from the
production manifest and app catalog. Restore production registration only
after implementing and testing the verified bolt seat. Geometry, tests,
and review exports remain available; this registration change leaves the
default preset volume unchanged at 19,834.554 mm³.

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

Volume, `sippy_cup_85mm`: **19,859.697 → 19,834.554 mm³ (-0.13%)** for this review revision
(original prototype: 17,807.799 mm³).
The thicker lip adds only 12 mm³ before edge treatment; the chamfers
remove slightly more material than the junction blends add. Envelope: **98.5229 × 31.5458 × 28 mm** (XYZ).
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

## Bolt seat: source conflict to resolve

Sean confirmed a **small-thread flat-head through-bolt**, superseding the
Fix Point receiver interpretation. A front recess must seat its head flush
with the concave face; the clearance hole must exit the flat back with a
45° roof toward +X.

The official [9 mm Small Thread, Flat Head, Bolt](https://thangs.com/m/974190)
listing describes a low-clearance head, but publishes neither head diameter
nor countersink angle. Its illustration appears to show an octagonal flat
head with a flat underside, rather than a countersunk cone. Need the actual
bolt geometry or confirmation of the intended seating shape; do not invent
spec dimensions or claim that a generic 90° cone fits this part. The front
seat and requested countersink parameters are **not implemented yet**.

The pin dimensions use the [tile generator author's measurements of the
official remix STEP](https://github.com/asciipip/multiboard-parametric-stacked/blob/master/multiboard_base.scad)
(lines 51–56, 87–95): throat 6.0 mm, board depth 6.4 mm. Diameter 5.6 mm
leaves 0.2 mm per side; projection 5.9 mm leaves 0.5 mm axial clearance.
These are cited measurements, not independently measured official files.

## Validation

- Full `uv run pytest`: **275 passed, 1 xfailed** in 230 s.
- Targeted model tests plus registered print audit: **71 passed**.
- `npm test`: **291 passed** on this revision.
- All registered models exported successfully after channel changes.
- Manifest regenerated; review render and STL regenerated from revised model.
- Root `python3 scripts/render-all.py`: **28/28 passed** earlier in this PR;
  unrelated SCAD thumbnail differences discarded.

The review render uses the exported mesh rotated to show its front channels.
