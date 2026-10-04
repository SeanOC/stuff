# openConnect compatibility library

`openconnect/` is a port of the openConnect slot from the author's own
OpenSCAD source: mitufy's
[opengrid-projects](https://github.com/mitufy/opengrid-projects) at commit
`04e2277a71c5`, licensed CC BY 4.0. openConnect is openGrid's connector
system ([Printables 1559478](https://www.printables.com/model/1559478),
[MakerWorld 2257440](https://makerworld.com/en/models/2257440), both by
mitufy; openGrid is by David D).

**Why a port.** The `pyproject.toml` HARD RULE allows mount geometry only
from the pinned `opengrid` library or other build123d ecosystem libraries.
Neither ships openConnect. Sean approved this carve-out on 2026-10-01:
"porting from official upstream openscad is definitely better than
homegrown geometry". The port is pinned to that commit and checked against
renders of the author's own modules (see Verification).

## API and mounting datum

```python
from openconnect import slot_cutter, head, seat_location, onramp_location, POCKET_DEPTH

negative = slot_cutter(nubs='left', clearance=(0.10, 0.10))
plate -= Pos(x, 0, z) * negative            # (x, z) = an openGrid tile centre
seated = seat_location(x, z) * head()       # contract fixture only
entry = onramp_location(x, z) * head()
```

`slot_cutter(*, nubs=None, snap=None, clearance=(0.10, 0.10),
entryramp_flip=False, edge_feature='both', slide='up',
excess_thickness=EPS, excess_length=0.0)` returns one slot negative.

- `nubs`: `left` (default), `right`, `both`, or `none`, naming the author's
  lock sides before ramp flip and slide. The deprecated `snap=True/False`
  alias maps to `left/none`, warns, and rejects conflicting `nubs` values.
- `entryramp_flip`: mirrors the slot across its X axis, including the locks.
- `edge_feature`: `both` (default), `top`, `side`, or `none` controls the
  author's bridge/cliff widening; the 0.8 mm bridge and 0.6 mm wall minima
  remain fixed, cited constants.
- `slide`: `up/down/left/right` rotates the slot and head frames by
  **0/180/+90/−90°** about the consumer face normal `(0,−1,0)`.
  `lib/openconnect_lib.scad:467` supplies the grid spin, but the `BOTTOM`
  attachment at `:484` reverses the left/right sense in world coordinates.
  Committed author grid meshes verify these signs. The effective ramp flip
  is `(slide in ('right', 'down')) xor entryramp_flip` (`:468`).
  Rotation happens **once, on the cutter**; grid consumers pass `slide`
  through and use `seat_location(x, z, slide=...)` and
  `onramp_location(x, z, slide=..., entryramp_flip=...)` without rotating again.
- `excess_thickness`: finite, nonnegative extension outside the face, default
  `EPS` (0.005 mm), so the cutter starts at Y=−EPS. `excess_length` extends
  the on-ramp end, default zero. Both follow the upstream through-cut CSG.
- `clearance`: the author's side/depth clearances, default 0.10/0.10 mm,
  each limited to 0–0.5 mm. Head profile and travel remain fixed.

Vase mode is not part of this port; the supported outputs are slots and negative slot grids.

**Datum.** This is the multibuild consumer frame: the back (wall-facing) face is
Y=0, material is at +Y, and the pocket runs Y=0..2.7 (`POCKET_DEPTH`, the 2.6
head plus 0.1 depth clearance). The origin is the seated connector axis,
which must sit on an openGrid **tile centre**. Pitch is 28 mm, and nothing
assumes 25. With default options the negative stays inside the 28 × 28 tile around the origin:
X −13.0..+8.6, Z −13.2..+9.0.

- **Seat:** the head at the origin. The pocket end above it (+Z) is
  closed, with 45° roof chamfers.
- **Entry:** the on-ramp opens on the back face 10.6 mm below the seat
  (`MOVE_DISTANCE`), offset 2.2 mm to −X (`ONRAMP_SHIFT`). The head is pushed
  in along +Y there, moves +2.2 X onto the slot axis, then rides +Z 10.6 mm to
  the seat. The on-ramp leans to −X so the head hooks under the +X lip. A
  head pushed in on the slot axis fouls the lip (up to 6.2 mm³).
- **Retention:** the 14.4 mm neck (mouth 14.2 + 2 × 0.1, widened to
  14.68 mm by the author's bridge rule) holds the 17 mm flange. The lock nub
  (left wall, 0.6 deep) snaps into the head's notch at the seat.

`seat_location(x, z) = Pos(x, 2.6, z) * Rot(90, 0, 0)`. The head's top is
flush with Y=0, and its flange is 0.1 mm off the pocket floor.

Mounts declare `openconnect-slot` and provide
`mount_fixtures(mount_type, values) -> MountFixtures` with `cutters`,
`seat_locs`, `onramp_locs`, entry axis `(0,0,1)` for up, `(0,0,-1)` for down, `(-1,0,0)` for left,
`(1,0,0)` for right, and face normal `(0,-1,0)`.
`holders/openconnect_plate.py` is the registered grid/plate consumer.

**Plate thickness rule.** Backing must be at least 2.4 mm behind the 2.7 mm
pocket, so an openConnect plate is **at least 5.1 mm** thick. The contract
checks this locally behind every pocket floor face.

## Mount contract (`openconnect-slot`)

`tests/mount_contracts.py::verify_openconnect_slot` uses the openConnect
`head()`, not the Multiconnect `RoundHead` that the other contracts build
internally. For every slot it checks:

1. **Seat clearance:** the seated head does not foul the model (< 1 mm³).
2. **Retention:** the seated head, pulled 0.5 / 1 / 2 mm off the wall,
   fouls the plate (> 1 mm³).
3. **End stop:** pushed 1 mm past the seat, the head fouls by > 5 mm³, more
   than the whole lock nub (1.42 mm³) could account for.
4. **Entry path:** from completely outside the face, push in at the on-ramp
   (0.25 mm steps), shift across onto the axis, and slide up to the seat
   (0.5 mm steps). Every pose fouls less than 2 mm³. The nub snap-over peaks
   near 0.8 mm³.
5. **Dovetail:** at the seat height, the pocket is narrower than the
   17 mm flange just inside the face and at least as wide near the floor.
6. **Backing:** every pocket-floor face, extruded 2.4 mm into +Y, is solid.

`tests/test_openconnect.py` also proves that each failure is caught: a sealed
on-ramp, a blocked channel, an open seat end, 1.3 mm backing, and an entry
on the slot axis instead of the on-ramp each raise.

## Grid helper and registered plate

`openconnect.grid.layout(h, v, *, position, lock, slide, entryramp_flip,
except_positions)` is pure placement data, on the author's 28 mm pitch.
Indices run left to right and **top to bottom**: `x = -(h-2*i-1)*14`,
`z = +(v-2*j-1)*14`. `top-corners` means the first row; staggered parity
is `i % 2 == j % 2`. Positions are all/staggered/edge-rows/edge-columns/corners;
locks are corners/all/staggered/top-corners/none. Selected locks use left nubs.
`except_positions` contains `(i,j)` pairs; footprint `limit_region` is not
ported. `fixtures(placements, clearance=(0.1,0.1))` passes slide and flip raw
to the slot and head helpers, without a second rotation or flip. A 2×2
corner-lock layout has four slots at X/Z = ±14; OC3 maps them to cradle seats.

`holders/openconnect_plate.py` replaces the unregistered demo. The app slug
is `openconnect-plate`, in the existing **multiboard** category. Presets:

- `default`: 84 × 56 × 5.1 mm, six slots, corner locks.
- `one-tile`: 28 × 28 × 5.1 mm, one locking slot.
- `negslot`: six disconnected watertight slot solids, exported together as
  one STL/GLB. The author hides the base in negative mode; this is a CAD
  subtraction tool, exempt from print audits and mount contracts.

Size is in whole grids or millimetres; physical width/height are 28–280 mm.
Millimetre dimensions floor to whole grid counts, then center/edge alignment
and offsets position the grid. Offsets must keep complete tiles in the plate.
A standalone plate also rejects a moved on-ramp border below 1.3 mm
(0.9 mm wall plus 0.4 mm edge relief): the approved thin-strip exception
applies only at the exact author grid edge.
Backing defaults to 2.4 mm; **0.5–2.3 mm requires another model's wall and is
not standalone-printable**. Thickness follows the actual clearance-adjusted
pocket depth plus backing (5.1 mm at defaults). Profiles, pitch and travel
remain library constants. At maximum 0.5/0.5 mm clearances the connector has
initial free play: the default mount contract's 0.5 mm pull probe is clear,
but the 1 and 2 mm probes still engage the lip (5.45 and 10.98 mm³ overlap
on the one-tile rounded case). Shipped presets use 0.1/0.1 mm and pass the
full mount contract, including its 0.5 mm pull threshold. There is no fused joint or asserted load rating;
an attached accessory's off-wall pull is the worst-case load, in PLA/PCTG.

Print standing, +Z up. Exposed slab edges have a 0.4 mm chamfer, including the
bed edges; cutters and their mating edges remain untouched. Corner rounding
is none by default. Chamfer/fillet applies to the **two upper footprint
corners**; the two lower corners always get a same-size 45° chamfer, never a
downward fillet (approved pst-zn36d rev 5). Corner sizes are 0, 1 or 2 mm:
smaller radii conflict with the 0.4 mm edge relief, and larger radii remove
required backing beneath edge-row pockets. `build(values, reference=True)`
omits edge relief and preserves all four of the author's rounded corners,
for reference equality at the author's 0.5 mm backing.

**Narrow border audit exception (pst-zn36d rev 4).** With library cutters
supplied to the production audit, the only additional exclusions are exact
solid bands between edge-facing on-ramps and the plate edge. They are
extruded from the actual ramp-end faces in the same placements as the
cutters and clipped to the pocket depth; there is no bounding-box padding.
At default clearances these bands are 0.8 mm high, with the ramp/channel's
slanted cross-section, volume 43.763195959493 mm³ per slot (three in default,
one in one-tile). Slots off the border produce no strip. Tests pin the count,
volume, depth and border bounds for every slide/flip; no other exclusion is
allowed. The author's 0.8/0.6 mm mating features remain under the existing
library-cutter envelopes. No plate margin or global cutter margin changed.

## Verification against the author's renders

openConnect needs BOSL2 structs, which the repo's pinned BOSL2 (456fcd8)
cannot provide, and the build123d CI job has no OpenSCAD engine. The
author's modules were therefore rendered **once**, with openscad
2025.06.12.ai25773 and BOSL2 HEAD b86a758. The renders are committed under
`assets/openConnect/mesh/`, and
[`assets/openConnect/NOTICE`](../../assets/openConnect/NOTICE) records the
exact commands, `-D` overrides, versions and sha256 values:

- `openconnect_plate_one_slot.stl`: the author's `openconnect_plate.scad`
  for one 28 × 28 tile (shipped defaults otherwise).
- `openconnect_plate_{default,asymmetric,negative}.stl`: six-slot default,
  top-corner locks on edge rows (catches reversed Z), and base-free negative.
- `openconnect_head.stl`: the author's `openconnect_head()`.
- `openconnect_nubs_{right,both,none}.stl`, `openconnect_flip.stl`, and
  `openconnect_edge_{top,side,none}.stl`: one-tile plate option renders.
- `openconnect_slide_{down,left,right}.stl` and
  `openconnect_excess_{thickness,length}.stl`: upstream grid negatives
  rendered by the committed wrappers (1.0 mm thickness / 5.0 mm length).

The slot taper uses explicit planar hull faces. A ruled loft can give the
same analytic volume but leave inconsistent STL trim edges when one cutter
is reused at several locations; the demo's watertight-export test covers this.
The head fixture retains its original construction.

All twelve option cases use the same bidirectional 0.01 mm surface bound
and volume comparison. Defaults retain the existing plate geometry and
recorded spool-cradle preset volumes; STL byte order is not an invariant.

`tests/test_openconnect.py` rebuilds the same plate from `slot_body()` and
compares surfaces in both directions. The bound is 0.01 mm, ten times tighter
than the 0.10 + EPS that the spec allows. Measured: volume Δ 0.0005 mm³ and
surface distance ≤ 0.0035 mm, which is float32 STL noise. The head matches
its render to 0.001 mm. Its bounding box is 17 × 10.6 × 2.6, and its
narrowest cross-section is the 14.2 mm mouth. Seated in the rendered slot, it
stays at least 0.07 mm from the plate (0.1/√2 at the nub).

## Provenance

Every constant in `openconnect/constants.py` is **[C]**, cited from another
project's source ([design-guidelines §7](design-guidelines.md#7-provenance)).
Its `locator` is the GitHub URL of the defining line at the pinned commit.
`tests/test_openconnect.py` enforces this. It requires status `C`, the
`.../blob/04e2277a71c5/<file>#L<n>` form, and module-value equality. It also
reads the cited line from the vendored copy and requires the literal there.
These constants are deliberately kept out of `test_reference_provenance.py`'s
`_all_tags()` and `test_multibuild.py`'s `_check_tag`, which require [V].

| Constant | Value (mm) | Locator (file:line @ 04e2277a71c5) |
| --- | --- | --- |
| `TILE_SIZE` (openGrid pitch) | 28 | `lib/opengrid_base.scad:4` |
| `HEAD_BOTTOM/MIDDLE/TOP_HEIGHT` | 0.6 / 1.4 / 0.6 | `opengrid_base.scad:43–45` |
| `HEAD_DEPTH` (derived) | 2.6 | `opengrid_base.scad:56` |
| `HEAD_WIDTH × HEAD_HEIGHT`, `HEAD_CHAMFER` | 17 × 10.6, 4 | `opengrid_base.scad:46–48` |
| `MOUTH_WIDTH` (derived: 17 − 2 × 1.4) | 14.2 | `lib/openconnect_lib.scad:27` |
| `NUB_TO_TOP_DISTANCE`, `NUB_DEPTH`, `NUB_TIP_HEIGHT`, `NUB_FILLET` | 7.2, 0.6, 1.2, 0.8 | `opengrid_base.scad:50–53` |
| `NUB_FLANK_ANGLE`, `NUB_TAPER_SHIFT` (derived 1.4 − 0.6) | 45°, 0.8 | `openconnect_lib.scad:307`, `:274` |
| `BACK_POS_OFFSET` | 0.4 | `opengrid_base.scad:55` |
| `MOVE_DISTANCE`, `ONRAMP_CLEARANCE` | 10.6, 0.8 | `opengrid_base.scad:59–60` |
| `ONRAMP_SHIFT` (derived 0.8 + 1.4), `ONRAMP_ROOF_HEIGHT` | 2.2, 4 | `openconnect_lib.scad:415`, `:417` |
| `SIDE_CLEARANCE`, `DEPTH_CLEARANCE` | 0.10, 0.10 | `openconnect_lib.scad:79–80` |
| `POCKET_DEPTH` (derived 2.6 + 0.1) | 2.7 | `openconnect_lib.scad:99` |
| `EDGE_BRIDGE_MIN_W`, `EDGE_WALL_MIN_W` | 0.8, 0.6 | `openconnect_lib.scad:77–78` |
| `EPS` | 0.005 | `opengrid_base.scad:3` |

Only the numbers that shape the slot and head are recorded. The connector
printing constants (tile thicknesses, thread profile, fold gaps) are not
used here.

**[V] upgrade path (not required).** If the MakerWorld STEP set is uploaded
to the reference bucket, measuring it with `tools/measure_step.py` into
`reference/measured/oc-*.json` would earn [V] for these values.

**Second definition in the repo.**
`models/littletikes_dream_machine_cartridge_holder.scad:292-340` carries a
hand-typed OpenSCAD openConnect receiver (`oc_*` constants at :309-322,
probed by its `invariants.py:91`). The numbers it shares with this table
agree today: 17 / 14.2 / 10.6, the 0.6 + 1.4 + 0.6 stack, 0.1 / 0.1
clearances, 10.6 travel, 2.7 depth. Its geometry is simplified, though: a
straight dovetail with a full-depth on-ramp on the slot axis, and no seat
chamfers, lock nub, offset on-ramp or lip widening.
`build123d/openconnect/constants.py` is the **citation of record**, pinned
to the upstream commit. The SCAD model keeps its literals until someone
migrates it, and any future disagreement is resolved toward the pinned
upstream.

## Licence

The vendored SCAD (`assets/openConnect/`) is CC BY 4.0, unmodified, with
attribution in its `NOTICE`. `openconnect/` adapts the author's slot and head
modules. CC BY 4.0 permits adaptation with attribution: "openConnect by
mitufy, licensed CC BY 4.0." The licence text is
[CC-BY-4.0.txt](../reference/LICENSES/CC-BY-4.0.txt).
