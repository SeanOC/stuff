# Gridfinity capture bin — blocked checkpoint

Work for `pst-r02mp.4`, canonical spec rev 3, started from main
`9297b329dc81b4209f671bfa93f77325817f47cf`. This branch is incomplete and is
not ready for a PR. No published-geometry exception has been invented.

The MIT library prototype preserves the Gridfinity Rebuilt foot profile
[C] `src/core/standard.scad:175-229` at pin
`910e22d8607fd7f5f51ad5e5cbc5287a76810bfd`: 42 mm pitch, 41.5 mm foot top,
0.8/1.8/2.15 mm profile stages (4.75 mm total), R3.75 corners and 7 mm
height units. See [NOTICE](../assets/gridfinity-rebuilt/NOTICE) for the
reference command, engine, hash and licence. The reference outer wall is
1.24 mm: `d_wall=.95` + half of the `.6` divider deduction in `cgs()`
− `.01` infill inset. Its floor transition is R2.8.

## Spec conflict requiring a mayor revision

Invariant (e) requires overhang ≤45° and no pre-declared exceptions.
The pinned, unmodified 2×2×3 reference has a horizontal downward-facing
bridge surface at Z=4.75 mm between feet. There are 374 mesh triangles in
this plane, total area 119.575428 mm², normal (0,0,-1). An upward ray from
(0,10,0) first meets that surface at (0,10,4.75).
Source: `src/core/base.scad:164-180`, `_base_bridge_solid`, which joins the
individual feet with a flat-bottomed extrusion.

The library parity prototype passes ordered bbox within .05 mm, volume
within 1%, and both-direction surface caps .15 mm without exclusions:

| Measurement | Result |
|---|---:|
| Reference volume | 49418.328114 mm³ |
| Port volume | 49417.382438 mm³ |
| Port → reference max distance | .019375 mm |
| Reference → port max distance | .016721 mm |
| Raw production overhang, 2×2×3 port | **90° — FAIL** |
| Raw production local bridge, 2×2×3 port | 3.0 mm |
| Raw production minimum wall | 1.24 mm |
| Downward fillets | 0 |
| Bed chamfer | present |

The initial default capture bin also reports 90°, bridge 2.6 mm, minimum
wall capped at 3 mm, no downward fillets and a present bed chamfer.
These are diagnostic runs, not a completed endpoint acceptance table.

Decision requested: revise invariant (e) to allow a narrowly inventoried,
reference-measured short horizontal bridge under §8 (retaining the raw
bridge measurement and checking all other faces), or specify a different
geometry/parity contract. Changing the published underside silently would
contradict parity; suppressing its audit result silently would contradict
invariant (e).

Reproduce the evidence from `build123d/`:

```sh
uv run pytest tests/test_gridfinity_capture_bin.py -q
```

## Prototype and remaining work

The capture model imports the CB1 encoder and parser. The panel will supply
its footprint string; this branch supplies a canned 140×18 mm rounded
rectangle. Shapely clearance drives automatic cell sizing. `base_height`
in the height formula means the 7 mm base, and the floor absorbs the
height-unit remainder. That solid filler is deliberate pocket stock;
large/deep bins should use fewer perimeters with suitable slicer infill.
The model has no mount contract. Feet-down is the intended PLA/PCTG pose.

After the spec decision: finish footprint simplification/containment and
error tests, socket-fit tests, all endpoint/preset audits and the exterior
edge inventory. Finish dimension-aware download names, bake all presets,
report before/after preset volumes, run the full Python suite and web tests,
and run ruff. The checkpoint's generated manifest and catalog registration
are present; the feature is not claimed complete.
