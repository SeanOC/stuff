# Underware outside-corner cable channel (openGrid)

`underware_outside_corner` (`holders/underware_path_channels.py`, geometry
`underware/path.py:build_outside_corner`, slug `underware-outside-corner`,
bead pst-38hu7) is the convex twin of [`underware_mitre`](../holders/underware_path_channels.py):
the same two Underware "monokini" arms, but the 90° bend turns the other way —
floor **outside**, open grip side **inside** — so it wraps the outside edge
where two openGrid panels meet and each arm snaps to the panel on its side.

It is an original design derived from the ported mitre (no author source, no
parity mesh), under the family's CC BY-NC-SA 4.0 (non-commercial,
share-alike); see the row in `assets/underware-opengrid/NOTICE`. Section
golden: [`renders/sections/underware-outside-corner.svg`](renders/sections/underware-outside-corner.svg).

## Geometry

Model frame as the mitre's (`underware.channel`): X across the channel, Z = 0
the first arm's closed face, grips up.

- **First arm**: the mitre's, unchanged (`mitre_first`, the 0.8 mm lead-out
  `STUB`, cord cutouts on this arm only). It runs along −Y and ends at
  y = −cw/2; the bend starts at its tangent plane y = −w/2.
- **Bend** (`outside_bend`): the channel section revolved 90° about the
  X-parallel axis `outside_axis` = (y = −w/2, z = (h − 3.4) + added_radius·28).
  The open faces (wall tops, where the openGrid tiles sit) are at radius
  `added_radius·28` from the axis, the closed floor at
  `outside_floor_radius` = added_radius·28 + h − 3.4.
- **Second arm**: rises +Z from the axis height, grips toward −Y, its open
  face on the plane y = −w/2 + added_radius·28 (`outside_second_location`:
  the mitre's second-arm frame turned 180° about X, so cell index 0 is the
  free tip and the suppress codes keep their sides).
- **Edge line** (`outside_edge`): where the two open faces meet — the panels'
  convex edge. At added_radius 0 it is the bend axis and the open faces meet
  at a right angle there, around a square edge. **added_radius > 0 needs an
  edge rounded (or clear) to at least added_radius·28 mm about the bend
  axis**; a square edge would cut into the bend.
- `mirror_channel` x-flips the whole part.

Spec deviation (recorded): the bead's "floor radius = inner radius +
channel_total_height" measures from the grip tops; the bend has no grips, and
with the open faces (wall tops) at the stated inner radius the floor sits at
inner + h − 3.4 mm. Taking the grip tops as the inner radius instead would put
the open faces 3.4 mm off the axis at added_radius 0, and a square panel edge
would then cut 1.4 mm into the bend's walls.

### Grip cells

Both arms keep the mitre's cell arithmetic: first-arm cells sit exactly where
the mitre's do; second-arm cells sit the mitre's distance from the bend's
tangent plane (14 mm + 28 k), mirrored to the other side of the bend. Measured
from the edge line along each panel that is

| arm | distance of cell k from the edge line |
| --- | --- |
| first  | 14.8 + 28·(added_radius + k) mm (the mitre's 0.8 mm lead-out) |
| second | 14 + 28·(added_radius + k) mm |

i.e. the 14 + 28 k hole lattice of a tile that ends at the edge line (first
arm +0.8 mm). Accepted for v1 (mayor, 2026-10-31): both tiles cut to meet at
the edge.

**Edge offset (pst-ufdvc).** Where the two tiles overlap at a convex edge
instead (the usual box or cabinet corner), the covered tile's holes sit one
tile thickness further from the edge: 6.8 mm for openGrid full, 4 mm for
openGrid lite. `edge_offset_mm` (0–8 mm, default 0) adds that distance to the
formula above on the arm `offset_arm` names (`first` | `second`, default
`second`): its cells move toward its free tip by exactly the offset, while
the other arm, the bend and both arm lengths stay as they are. A shifted
grip can extend beyond the wall envelope in the print frame: the extents
include the surviving grip profiles and their end ramps.
The arm is still length_units × 28 mm long and its outermost (tip-side) grip
has only 28/2 − 15/2 = 6.5 mm of slack to the tip, so a cell whose 15 mm grip
would cross the tip face is dropped: past 6.5 mm the shifted arm loses its
tip-side cell (a 2-unit arm at 6.8 mm keeps its inner grip), and a 1-unit arm
would lose its only cell, which is a named error. Per-cell suppress codes
keep their lattice index, so a dropped cell's code is ignored.

## Print orientation

A 90° bend has no support-free orientation. The candidates:

| orientation | what overhangs |
| --- | --- |
| **bend down, −45° about X (chosen)** | each arm in the mitre's print attitude (grips up and inward at 45°, so the mitre's grip-end-wedge / flare-slit-fin / cutout-sill exceptions apply unchanged); only the bend's convex floor underside overhangs, rising off a bed flat |
| bend up, +45° (the mitre's Λ) | open side faces down: grips point down 45°, and the channel ceiling at the crown is a 90° bridge 22.4–106.4 mm wide |
| upright (first arm flat) | half the bend's floor underside, plus 90° ledges at every second-arm grip end |

`outside_print_frame` is −45° about X (y' = (y + z)/√2, z' = (z − y)/√2): the
bend points down and both arms rise at 45°. The default cradle holds the
complete arc above the bed. With `supports=none`, `bend_flat` cuts
`BEND_FLAT_MM` = 0.6 mm into the 2 mm floor at the floor cylinder's lowest
line (`outside_bed_plane`), leaving 1.4 mm of floor and one bed strip
(≥ 100 mm² at width 1; 0.4–1.5 % of the volume). Every preset and every
combination the bed check allows fits the H2S's 325 × 320 × 325 mm
(`outside_extent`, equal to the print-frame bounding box); 8-cell arms overrun
the bed even at width 1, height 10, so `length_units` ≤ 7
(`MAX_ARM_OUTSIDE`), and longer/wider/taller combinations are named errors.

The analytic bed check includes `grip_flare` and `edge_offset_mm`, including
one-sided/suppressed grips and dropped cells. Previously it used only the
unflared wall envelope. For example, at otherwise default values, flare
9.9° increases the width from 26.400 to 33.940 mm, and offset 6.5 mm increases
the height from 38.365 to 38.789 mm. Mirroring preserves these sizes. These
examples fit the H2S; the corrected check rejects any combination whose
full grip envelope exceeds the bed limits, and its error names flare and
offset among the settings to reduce. This correction changes size validation,
with no change to the built geometry, parameters or presets.

### Built-in supports

**Release change (r2):** `supports=built_in` is now the default for all three
base presets. The former `outside-corner-r1-supported` preset is folded into
`outside-corner-r1`. Download names and preset order otherwise stay the same;
`supports` is still not a filename token. A returning downloader now gets a
full smooth arc with a detached cradle. Set `supports=none` for the previous
byte-identical bed-flat channel and its scoped `BendUnderside` exception.

The retained channel is one solid and the complete pad/cradle is a second
solid. There is no bonded bed strip, tear-off skin or groove outline. A
0.95 mm crown rail runs across the lowest tangent line; its tooth tops stand
1 mm above the pad and one `support_gap_mm` below the arc (mayor rev 2).
Curved flank fins use the same gap, measured along the cylinder normal.
The part's floor remains a continuous cylinder tangent to both arms.

Tooth lands are 0.95 mm long on 0.95 mm fins. Their pitch is at most 6 mm
in either direction, so even a contact-cell diagonal stays below the
10 mm bridge limit. Recessed webs connect the teeth to the pad. The short
fin continuations under the 45° arms remain for sound roots; their tops
are recessed from the contact gap. The intended witness is a grid of dots.

The pad is 0.6 mm thick, with R4 corners, a 0.3 mm bed chamfer and a 5 mm
margin around the fin footprint. One rounded, chamfered 10 × 10 mm pull
ear extends beyond that margin to start peeling. Remove the pad and all
fins together after cooling. Default gap is 0.2 mm (range 0.1–0.3 mm);
use 0.25–0.3 mm for PCTG and inspect the sliced contact layers. The curved
lands preserve the exact normal gap, rather than snapping to layer heights.
Sean's second print remains the acceptance for hand removal and finish.

Material and contact counts at the default 0.2 mm gap (mm³):

| Case | Retained full-arc channel | Pad + fins | Total | Tooth lands |
| --- | ---: | ---: | ---: | ---: |
| w1 / h22 / r0 | 8695.186 | 1157.161 | 9852.347 | 28 |
| w1 / h22 / r1 | 13586.018 | 2981.948 | 16567.966 | 60 |
| w2 / h28 / r1 | 24885.699 | 7351.802 | 32237.500 | 135 |

The added material is 13.3%, 21.9% and 29.5% of the retained part,
respectively. The crown rail, greater clearance below the full arc and
closer fin spacing buy isolated tooth contacts with bounded spans. These
remain thin fins on a three-layer pad, without a solid supporting block.

The production audit verifies a connected disposable cradle, no contact
with the retained channel, actual tooth probes at the normal gap, and
bracketed contact cells on the same retained surface with spans ≤10 mm.
Only the declared pad material can be below the normal 0.9 mm wall floor;
fins and the retained channel are checked separately from that exception.
Fin and pad surfaces cannot waive their own overhangs. The bend has no
`BendUnderside` exception in this mode. Bed validation includes the pad,
pull ear and the 1 mm crown rail.

The [default review sheet](renders/review/underware-outside-corner.png) and
[radius-1 sheet](renders/review/underware-outside-corner-outside-corner-r1.png)
show the fins in ISO/FRONT and the pad in UNDERSIDE. Regenerate them with
`uv run python scripts/export.py --commit-review --model underware-outside-corner`.
`tests/test_underware_outside_support.py` checks the contacts, tooth relief,
pad/ear, unsupported compatibility and supported endpoint audit.

### The one published exception: `BendUnderside` (signed by the mayor on pst-38hu7, 2026-10-31)

In `supports=none` only, the bend's floor underside — the cylinder of `outside_floor_radius` over the
bend's quadrant and the channel width — prints unsupported by design. In the
print frame it is a convex downward face rising off the bed flat with
overhang from 63–80° (at the flat) down to 45°. It exempts no chamfer, wall,
grip or arm face (`test_bend_exception_is_narrow_and_exact`: without it the
audit fails on exactly its two cylinder faces; a new overhang beside it is not
waived). Size, chord = floor radius × √2, wall span (floor width) = channel
width 26.4 + 28·(units − 1) mm:

| height | added_radius 0 | 1 | 2 |
| --- | --- | --- | --- |
| 10 mm | r 6.6, chord 9.3 mm | r 34.6, chord 48.9 | r 62.6, chord 88.5 |
| 22 mm | r 18.6, chord 26.3 | r 46.6, chord 65.9 | r 74.6, chord 105.5 |
| 72 mm | r 68.6, chord 97.0 | r 96.6, chord 136.6 | r 124.6, chord 176.2 |

across width 1–4 (wall span 26.4–110.4 mm; the cylinder itself is the
floor's flat width between the 4 mm chamfers, 18.4–102.4 mm). Unlike the mitre's arch (a concave ceiling,
90° at its crown) this is a convex underside that starts on the bed, the
easier case; test-print the largest radius first, supports stay optional.

## Audit rows

`tests/test_underware_outside_corner.py::test_endpoint_audit_and_edges` runs
the production print audit and the exposed-edge inventory at every numeric
Param endpoint, each preset and the documented corners (raw = no
exceptions; filtered = the family exceptions + BendUnderside):

| case | vol mm³ | raw ovh ° | min wall mm | worst overhang ° | exposed-edge ° | exceptions | ok |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| outside-corner | 8624 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| outside-corner-r1 | 13473 | 77.2 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| outside-corner-w2-h28-y2 | 27271 | 74.1 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| width-4 | 22495 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| height-10 | 4283 | 63.3 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| height-72 | 36506 | 78.7 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| length-7 | 47732 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| radius-2 | 18334 | 79.0 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| mirror | 8624 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| max-corner | 159423 | 80.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| min-corner | 4283 | 63.3 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| length-7-w4-h10 | 94545 | 63.3 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| separators-w4 | 38725 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| separators-w3-r1 | 31302 | 77.2 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |
| flare-9.9 | 9378 | 72.4 | 1.281 | 45.0 | 45.0 | grip-end-wedge, flare-slit-fin, bend-underside | PASS |
| flare-9.9-h72-r2 | 68167 | 80.4 | 1.281 | 45.0 | 45.0 | grip-end-wedge, flare-slit-fin, bend-underside | PASS |
| flare-5-suppress | 8602 | 72.4 | 1.295 | 45.0 | 45.0 | grip-end-wedge, flare-slit-fin, bend-underside | PASS |
| suppress-all | 8333 | 72.4 | 1.400 | 45.0 | 45.0 | bend-underside | PASS |
| cut-both | 20378 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, cutout-sill, bend-underside | PASS |
| cut-n4-w6 | 33350 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, cutout-sill, bend-underside | PASS |
| cut-w20 | 20516 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, cutout-sill, bend-underside | PASS |
| cut-d56 | 26896 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, cutout-sill, bend-underside | PASS |
| cut-d14 | 20232 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, cutout-sill, bend-underside | PASS |
| cut-shift-14 | 20874 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, cutout-sill, bend-underside | PASS |
| cut-left-mirror | 21019 | 72.4 | 1.300 | 45.0 | 45.0 | grip-end-wedge, cutout-sill, bend-underside | PASS |
| cut-right-top-h10 | 11862 | 63.3 | 1.300 | 45.0 | 45.0 | grip-end-wedge, bend-underside | PASS |

Min wall 1.300 mm is the grip nubs (1.400 with every grip suppressed; the
bed-flat floor keeps 1.4 mm), 1.281 with a 9.9° flare. Raw (no exceptions)
the only failures are the bend underside's two cylinder faces and the
family's published grip-end wedge / flare-slit fin / cutout sill regions. A
separate sweep of all 54 width {1, 2, 4} × height {10, 22, 72} ×
added_radius {0, 1, 2} × mirror corners gave one valid solid each, the
analytic extent equal to the print-frame bbox, and the same verdict (raw
bend overhang 63.3–80.4°, filtered 45.0°, no bridge).

Preset volumes (finished, mm³): outside-corner 8624, outside-corner-r1
13473, outside-corner-w2-h28-y2 27271. Nothing is added beyond the mitre's
arms and section: the bend is the section revolved, the bed flat removes
0.4–1.5 %.
