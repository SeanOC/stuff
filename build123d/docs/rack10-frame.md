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
