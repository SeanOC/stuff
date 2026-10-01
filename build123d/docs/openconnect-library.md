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

negative = slot_cutter(snap=True, clearance=(0.10, 0.10))
plate -= Pos(x, 0, z) * negative            # (x, z) = an openGrid tile centre
seated = seat_location(x, z) * head()       # contract fixture only
entry = onramp_location(x, z) * head()
```

`slot_cutter(*, snap=True, clearance=(side, depth))` returns the negative for
one slot. `snap` keeps the author's left-hand lock nub; `snap=False` drops it
(the slot then has no detent). The clearances are the author's
`slot_side_clearance` / `slot_depth_clearance`, default 0.10 / 0.10, each
limited to 0–0.5 mm. The rest of the slot (head profile, travel, on-ramp,
lip widening) is fixed by the cited constants and is not a parameter.

**Datum.** This is the multibuild consumer frame: the back (wall-facing) face is
Y=0, material is at +Y, and the pocket runs Y=0..2.7 (`POCKET_DEPTH`, the 2.6
head plus 0.1 depth clearance). The origin is the seated connector axis,
which must sit on an openGrid **tile centre**. Pitch is 28 mm, and nothing
assumes 25. The negative stays inside the 28 × 28 tile around the origin:
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
`seat_locs`, `onramp_locs`, entry axis `(0,0,1)` and face normal `(0,-1,0)`.
`openconnect/demo_plate.py` is a minimal example.

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

## Demo plate

`openconnect/demo_plate.py` is not registered. It is 84 × 84 × 5.5 mm
(3 × 3 tiles), printed standing (+Z up), with a 0.4 mm 45° chamfer on the bed
edges. It has four snap slots at the tile centres of the central 2 × 2 block:
X = ±14, Z = 28 and 56.

- Backing: 5.5 − 2.7 = **2.8 mm** (minimum 2.4).
- Slot packing: each slot spans 22.2 mm along Z (−13.2..+9.0) and 21.6 mm
  across X. That leaves a **5.8 mm** web between the rows, a **6.4 mm** web
  between the columns, and at least 14.8 mm to the plate edges.
- Volume before: **N/A (new artifact)**. Final: **34,750.930 mm³**.
- Print audit with the pocket exception: max overhang 45.0°, bridge 0 mm,
  min wall 2.80 mm, PASS. Without it, the pocket's own downward faces fail
  (90°, bridges up to 1.0 mm), as the Multiconnect pockets do. The author
  designs the slot to print standing with the slide axis vertical: the
  seat roof and the on-ramp roof are 45° chamfers.
- It carries no service-load rating and has no fused load-bearing joint.

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
- `openconnect_head.stl`: the author's `openconnect_head()`.

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
