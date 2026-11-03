# rack10 frame: HomeRacker 12U plan F

Sean selected **F: two 6U bays**, 17-unit width, 16-unit depth. The printed
frame is approximately 285 mm wide × 270 mm deep × 600 mm high, with
255 mm inner width and 240 mm inner depth. Each post segment is 18 units
(270 mm), so each bay has 270 mm between joints (6U = 266.7 mm).
This print list builds the frame; equipment rails and device mounts are
separate parts, and the frame has no established load rating.

Sources: [HomeRacker at 90556d1](https://github.com/kellervater/homeracker/tree/90556d1),
by Patrick Pötz; committed subset and license notices in
[`libs/homeracker`](../../libs/homeracker/NOTICE). Wrappers and presets are
[CC BY-SA 4.0](../../models/homeracker-LICENSE.md). Model URLs use dashes;
source filenames use underscores, per stuff's existing slug convention.

## F: full print list

Solid volumes below are measured from the pinned upstream geometries before
infill. **Planning assumption: 30% of solid volume, PLA density 1.24 g/cm³**.
The estimate is `quantity × solid cm³ × 0.30 × 1.24`; it does not model walls,
top/bottom layers, brims or purge. It is a rough budgeting proxy, not a
slicer mass prediction or a prescription for load-bearing infill. Thin
connectors and pins can be close to solid despite a sparse infill setting;
check slicer totals and choose walls/infill for the actual load.

| Part | Model / preset | Quantity | Solid cm³ each | PLA estimate g, batch |
|---|---|---:|---:|---:|
| Support / posts | `homeracker-support` / `18u` | 8 | 54.80 | 163.1 |
| Support / width | `homeracker-support` / `17u` | 6 | 51.76 | 115.5 |
| Support / depth | `homeracker-support` / `16u` | 6 | 48.71 | 108.7 |
| Top corner | `homeracker-connector` / `3d3w` | 4 | 10.24 | 15.2 |
| Bottom + middle corner | `homeracker-connector` / `3d4w` | 8 | 11.31 | 33.7 |
| Lock pin | `homeracker-lockpin` / `standard` | 44 | 0.31 | 5.0 |
| Foot | `homeracker-foot` / `standard` | 4 | 3.54 | 5.3 |
| **Total** | | **80 pieces** | | **446.5** |

For 44 pins, print two `plate-20` batches plus four `standard` pins (or a
third plate for spares). The `quantity` control can produce the remaining
four in one file. The plate has five columns and four rows, spaced 16 ×
36 mm, with twenty separate watertight solids; no connecting sprues.
The four feet each take a pin; 40 pins secure the 20 frame members.
Use `3d4w` for the eight bottom/middle corners. `3d4w-pull-through-z` is an
optional continuous-post connector, **not a substitution in this segmented
F print list**.

## Orientation and fit test

- Supports lie along the bed, 15 mm high. The longest preset is 270 mm;
  every supplied support fits an H2S/H2C bed. Keep their long axis in-plane.
  The full 1–50 unit control intentionally permits future larger-bed
  frames; above 23 units exceeds a 350 mm straight bed span.
- Connectors use upstream's optimal print rotation and chamfered landing
  face. Keep that rotation and auto-drop to the bed in the slicer; do not
  rotate a socket upright. Use a brim if the contact patch needs it.
- Pins lie on their broad side, with the tension slit through Z. Feet stand
  on their broad plate with the insert upward. These core presets need no
  supports. Supports have 4 mm square pin holes and 1 mm chamfers.
- Rack panels lie on their broad face, only 2 mm high. Both supplied
  10-inch presets fit the bed; full 19-inch panels (482.6 mm) and the 8U
  endpoint need a larger bed. Splitting panels is not exposed here.

**Before printing the complete frame**, print one `3d3w` connector, two
short supports (`units=2`), and standard pins. Seat and pin both beams;
check insertion, retention, release and material flow. HomeRacker's own
mating tolerance is **0.2 mm**; the wrappers do not rescale it. Standard
supports have one pin-hole axis (`x_holes=false`); roll each beam about
its long axis to align the holes with the connector's pin port before
insertion. `x_holes=true` exposes upstream's optional second axis.

## Assembly order

1. **Bottom frame:** arrange four `3d4w` joints with two 17u width beams
   and two 16u depth beams. Point the paired Z sockets up/down and the
   horizontal sockets inward. Seat the four foot inserts in the downward
   sockets. Square the rectangle and lock the eight beam ends plus feet.
2. **Lower posts:** insert four 18u supports into the upward sockets.
3. **Middle frame:** make a second width/depth rectangle from four `3d4w`
   joints, two 17u and two 16u supports. Seat it on the lower posts; keep
   the remaining Z sockets upwards. Lock all engaged ends.
4. **Upper posts:** insert four more 18u supports into the middle joints.
5. **Top frame:** assemble the last two 17u and two 16u beams with four
   `3d3w` joints. Face the remaining sockets downward and seat on the posts.
   Lock the final ends and confirm the frame is square and all feet seat.

Push pins from the **inside** of the frame where accessible, leaving the
grips available for removal. Another pin can push out a tight pin from the
opposite side. Verify every member end and all four feet are retained
before adding rails or equipment.

## G: 10U alternative only

| Plan | Supports | Connectors | Pins / feet | Envelope |
|---|---|---|---|---|
| G / two 5U bays | 8 × `15u` (225 mm), 6 × `17u`, 6 × `16u` | 4 × `3d3w`, 8 × `3d4w` | 44 / 4 | ≈285 × 270 × 510 mm |

## Printed EIA rail strips (implementation checkpoint; not released)

`rack10-rail-strip` is a separate 30 mm wide bar: 15 mm covers the post,
15 mm projects into the opening. Use four `18u` strips per bay (front and
rear, left and right), eight for plan F. The `18u` preset is **18 pin units
= 270 mm = 6 rack U**, not 18 rack U. Plan G uses eight `15u` strips
(225 mm, 5 rack U each). Roll **every strip-carrying post** so its single
pin-hole axis runs front-to-back. Mirror the bar across the opening for
the opposite side; do not shift its hole column independently.

The local origin is the post's outer bottom corner. X runs inboard, Y up
the post, Z from the rail's front face toward the post. The post front
face is Z = thickness. Peg centers are X = 7.5, Y = 7.5 + 15k mm for
k = 1 through n−2; the end stations are reserved for connector lock pins.
Peg width is **3.8 mm** (4.0 minus the cited 0.2 mm tolerance), length
14.8 mm. The back relief clears a 2.1 mm deep, 15 mm long and
**17.1 mm wide** sleeve footprint, including its overlap into the flange.
The cutter adds 0.3 mm around that footprint to allow for concave chamfers. The
whole-body sleeve intersection test checks both ends.

The hole column is X = 24.2375 mm, 5.7625 mm from the flange's free edge.
Across the 255 mm post opening the mirrored columns are 236.525 mm apart;
the flanges leave 225 mm clear. Each bar contains complete U groups,
centered along its length: `(length − floor(length / 44.45) × 44.45) / 2`
is the first U boundary above the post's bottom end. The bottom connector's
outer sleeve top face is 15 mm above that end, so the first U boundary is
**13.35 mm below** that face for `18u`, **13.625 mm below** for `15u`.
Hole centers are 6.35, 22.225 and 38.1 mm above each U boundary.

Restart the U grid in each bay; equipment never straddles the 15 mm middle
connector. For F, upper-bay post coordinates start 285 mm above lower-bay
post coordinates. All holes populated means 18 inserts per strip, 144
total: 3 holes × 12 rack U × 4 strip columns (front-left, front-right,
rear-left, rear-right). The 15 mm and 15.875 mm pitches coincide only every
1905 mm; mounting and equipment columns are independent.

The `coupon` is 5 pin units (75 mm), with three interior mounts and both
end reliefs. Sean's PETG fit print must check seating on a sleeved post,
grid alignment, insertion and pull-off before committing to eight rails.
Workers do not print. The baseline geometry uses the requested 8 mm
diameter, 8.5 mm deep blind pockets and at least 3 mm backing; insert mode
below 11.5 mm thickness raises `RailFitError: insert web`. Cage mode uses
a 9.525 mm square window through a 2 mm front web and an open rear channel
at least 8 mm deep. Front face down is the declared print orientation.
The 270 × 30 mm primary preset fits both printers without rotation.

### Checkpoint blockers requiring a specification revision

The ordinary production audit rejects the blind insert ceiling at 90°,
even though its measured bridge span is 7.5 mm (below the 10 mm bridge
limit). Its overhang and bridge gates are independent. Keeping a full
8 mm diameter cylindrical pocket 8.5 mm deep, adding a 45° conical roof,
then retaining 3 mm backing needs **15.5 mm thickness**, beyond the 14 mm
maximum. No audit exception has been added. The scoped endpoint test is
intentionally still red until the hardware/roof contract is revised.

Likewise 30 pin units means a 450 × 30 mm flat bar. Even the best square
bounding box is `(450 + 30) / sqrt(2) = 339.41 mm` on each side, exceeding
325 × 320 mm. A one-piece 30-unit strip cannot meet the specified beds.
The checkpoint preserves the requested range and reports the failed
endpoint; it does not silently shorten or segment the rail.

The requested short M6 × 8 mm insert is not yet tied to a verified vendor
part. [Harrison Silverdale series 20103](https://www.harrisonsilverdale.com/products/details/thermocert-heatstake-insert-for-thermoplastic72.html),
row **TH060H090**, cites an 8.0 mm hole but a **9.0 mm insert length**, an
11 mm hole depth and a 2 mm minimum wall. This supports only the cited hole
diameter, **not** compatibility with the present pocket or its 1.7625 mm
outer ligament. Hardware choice and roof/backing geometry need a consistent
revision together. Pin-hole-mode grip seating and cage-nut hardware fit
also still need verification; this checkpoint is not a production release.

HomeRacker provenance [C]: upstream commit **90556d1**, full paths
`libs/homeracker/models/core/lib/constants.scad` (TOLERANCE, BASE_UNIT,
LOCKPIN_HOLE_SIDE_LENGTH), `libs/homeracker/models/core/lib/support.scad:62–71`
(single-axis stations), `:103–129` (4 mm throat, 5.6 mm flared mouth),
`libs/homeracker/models/core/lib/connector.scad:33` (19.2 mm sleeve),
`:184–185` (orthogonal ports), and
`libs/homeracker/models/core/lib/lockpin.scad:30–40` (pin and grip dimensions).
Bar/interface dimensions [C]: E2b rev 2/3 and round-3 PASS. These rails are
original geometry; they do not copy HomeRacker's pin or support solids.

## Optional panels

Neither F nor G requires blank panels to assemble the frame. For this
HomeRacker family, use `homeracker-rackpanel` / `10in-1u` or `10in-2u` when
a plain cover with upstream rack bores is wanted. The separate build123d
rack10 panel family serves custom device/keystone layouts. Do not add a
panel quantity to the frame list until the device layout calls for one.

## Geometry and dependency verification

`tests/fixtures/homeracker-reference.json` records upstream bboxes and solid
volumes, with full HomeRacker/BOSL2 commits. Per-model wasm sweeps cover
parameter endpoints and every preset; preset geometry must remain within
0.01 mm and 0.1% volume, including twenty separate solids for the plate.
The desktop invariant sidecars pin each default export too.

HomeRacker uses its committed private BOSL2 **v2.0.779**. The global
`456fcd8` pin fails to render upstream rackpanel with a cuboid-length
assertion. An import-prefix patch isolates the newer copy without changing
`OPENSCADPATH` or the BOSL2 seen by existing Multiconnect models.
SCAD models register through the source, catalog, sidecar and sweep entry;
the build123d manifest contains no SCAD records.

Two applied patches are retained alongside the source: isolated import
prefixes, then browser-compatible equivalent primitives. The latter removes
recursive support-hole attachment, flattens foot and unbraced full-panel
placement, replaces rounded 3D hulls with extruded 2D profiles, includes
the panel's split constants, and overlaps the foot spacer into its base by
0.001 mm. Pin necks overlap their body by 0.001 mm and the inner grip-base
end overlaps by 0.002 mm; outer envelopes stay fixed, avoiding detached
necks and zero-volume scraps in twenty-pin desktop exports. Preset geometry remains within the upstream reference tolerances.
