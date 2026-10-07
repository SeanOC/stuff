# Gridfinity capture bin

`gridfinity-capture-bin` is a storage model with a single pocket fitted to an
item footprint. It prints feet-down in PLA or PCTG without supports. There
is no stacking lip, finger notch, label, or mount contract. CB2
(`pst-r02mp.4`, canonical spec rev 4) was built against main
`9297b329dc81b4209f671bfa93f77325817f47cf`.

## Footprint and dimensions

The capture panel (CB3) supplies **Item footprint (from the capture panel)**.
The model imports `capture/encoding.py` rather than defining another wire
format: `v1;x,y;…;x,y`, explicit closure, 0.01 mm quantization, at most 256
vertices and 16 KB, simple geometry with a bounding box at most 252 mm.
Malformed input preserves the encoder's error message. The canned default
is a 140×18 mm marker-pen rounded rectangle.

| Parameter | Default | Domain / meaning |
|---|---|---|
| pocket_depth | 20 mm | 3–90 mm below the top |
| clearance | 1.6 mm | 1–3 mm; round offset of the item outline |
| floor_thickness | 2 mm | 1.2–4 mm above the 7 mm base |
| wall_min | 1.6 mm | 1.2–3 mm between the offset pocket and outer boundary |
| size_mode | auto | `auto` or `manual` |
| width_units / depth_units | 4 / 1 | 1–6 cells each; used in manual mode |

Auto sizing chooses the smallest cell area that contains the complete
clearance outline with the required wall; ties use perimeter then width.
It accounts for the R3.75 outer corners. Offset outlines above 256 vertices
are simplified and expanded to preserve containment. Height is
`ceil((pocket_depth + floor_thickness + 7) / 7)` units; the floor absorbs the
remainder. An outline that cannot fit raises
`footprint + wall exceeds 6×6 cells` (also for an undersized manual choice).
The height calculation prevents `pocket deeper than the bin` for valid
parameter values.

The 1.6 mm clearance default exceeds CB1's measured 0.790 mm mean error,
but not its 1.612 mm worst case. Accuracy below 1 mm clearance is not
established; see [the spike](capture-bins-spike.md).
Presets are marker/default (auto 4×1), deep (45 mm pocket, auto 4×1), and
wide (manual 4×2). Width/depth filename flags use the existing download
name convention. Solid filler around the pocket is intentional stock;
choose slicer infill for the desired weight and print time.

## Library and provenance

The MIT library `build123d/gridfinity/bin.py` provides `base(w, d)` and
`body(w, d, height_units, wall)` with a flat interior floor.
[C] Gridfinity Rebuilt `src/core/standard.scad:175–229` at pin
`910e22d8607fd7f5f51ad5e5cbc5287a76810bfd` supplies 42 mm pitch, 41.5 mm foot
tops, 0.8/1.8/2.15 mm profile stages (4.75 mm total), R3.75 corners and
7 mm height units. The reference wall is 1.24 mm: `d_wall=.95` plus half
of the `.6` divider deduction in `cgs()`, minus `.01` infill inset
(`standard.scad:4,7,10,20`, `bin.scad:bin_get_infill_size_mm`,
`cutouts.scad:cgs`). Its floor transition is R2.8.
See [NOTICE](../assets/gridfinity-rebuilt/NOTICE) for the unmodified reference
render command, pinned engine, mesh hash, and MIT licences.

The mating socket independently uses a 0.7/1.8/2.15 mm profile, total
4.65 mm. The bin's last 0.1 mm stands above the plate. The socket-fit test
clips the bin below that plate top, checks no interfering volume, and pins
per-side gaps at Z=.05 / 1.5 / 4.6 mm to .35 / .25 / .35 mm (±.05).

## Edge treatment and parity

The GR 0.8 mm bottom step is a 45° chamfer, not a thin wall; it already
provides the mating bed relief. No second bed chamfer is added. Foot
profiles and base underside edges are functional mating geometry. The
upward outer rim receives R1; the pocket mouth receives a .15 mm chamfer.
The edge inventory assigns every edge `functional-mating`, `treated-rim`,
or `pocket`, recording its centre, length and angle at every endpoint.
The classifier requires tangent exterior/rim seams, limits the pocket
mouth and vertical seams to 45°, and identifies concave floor boundaries.

`test_pre_treatment_reference_parity` compares the library's 2×2×3 body
at the reference 1.24 mm wall, before rim/pocket treatment, with the pinned
STL. No surface exclusions: ordered bbox ≤.05 mm, volume ≤1%, and both
surface directions ≤.15 mm. Checkpoint measurements were 49418.328114 mm³
reference vs 49417.382438 mm³ port, with maximum distances .019375/.016721 mm.
`test_finished_rim_preserves_bbox_and_reduces_top_extent` separately pins
the finished default bbox to .005 mm and top-face contraction to exactly
R1 per side.

## Published exception #1: inter-foot underside

This is the only print exception authorized in canonical rev 4. Raw
measurements remain in the audit table; they are not replaced by the
filtered result.

| Inventory field | Pin / enforcing contract |
|---|---|
| Source | GR `src/core/base.scad:164–180`, `_base_bridge_solid`, at the NOTICE pin |
| Reference mesh | `assets/gridfinity-rebuilt/mesh/gr-bin-2x2x3-nolip.stl` |
| Face family | Downward planar underside at Z=4.75: body footprint minus all foot-top footprints, R3.75 corners |
| Reference measurement | 374 triangles; 119.575428 mm² ±.001; ray (0,10,0) along +Z first hits Z=4.75 ±1e-6 |
| Raw angle / local bridge | 90° / 3.0 mm on the 2×2×3 reference port; 90° / 2.59 mm (2.6 rounded) on default capture bin |
| Envelope | Exact analytic footprint difference, extruded only over 4.75 ±.0001 mm; no enlarged bbox; empty for 1×1 |
| Area endpoints | 1×1, 2×2, 6×6; both actual downward area and envelope area match analytic body area minus cell-count × foot area within .5% |
| Reference pins | `test_reference_has_horizontal_underside_between_feet`, `test_published_exception_1_is_the_only_raw_miss` |
| Narrowness pins | `test_published_underside_family_area`, `test_exception_rejects_new_ledge` (2 mm ledge under wall at Z=8 still fails) |
| Domain gate | `test_endpoint_audit_edges_and_containment`: every numeric endpoint, each preset, 1×1, 6×6, tight wall and combined limits |

The raw reference port must have exactly the 90° overhang failure. The
filtered audit must meet 45° / 10 mm / .9 mm at all buildable endpoints.
Raw local bridge remains ≤10 mm. No downward fillets are permitted and
bed chamfer presence is asserted. This exception cannot cover pocket,
floor or rim defects.

For the large grids, the endpoint harness first rejects points outside the
exclusion solid's bounds, then asks the unchanged native BRep classifier
about every remaining point. The box never grants an exemption.
`test_exact_exclusion_prefilter_preserves_native_membership` compares both
paths at slab boundaries, foot holes, the inter-foot gap and exterior points.
This avoids expensive solid queries for unrelated wall and fillet samples.

Worst-case lateral item forces run along XY layers; item weight compresses
the floor. There is no cantilevered mount joint. Minimum requested wall is
1.2 mm; use the 1.6 mm default or higher for lateral load-bearing use.

## Reproduction

From `build123d/`:

```sh
uv run pytest tests/test_gridfinity_capture_bin.py -q -s
uv run pytest tests/ -q
uv run python scripts/manifest.py
```

The endpoint test prints `AUDIT_ROW` records with raw/filtered overhang and
bridge, minimum wall, exposed seam angle (rim and pocket mouth/vertical seams),
volume and outcome. The
committed edge inventory is `tests/gridfinity_capture_bin_edges.json`.
Preset STL/GLB/PNG baking uses `scripts/export.py`; the tracked review
includes the underside and centre section at
[review](../build123d/docs/renders/review/gridfinity-capture-bin.png).

## Capture panel

On the Gridfinity capture bin page, choose **Take or choose a photo** to
use a photo or the phone's rear camera. Place one contrasting item on a
Gridfinity baseplate, with the whole baseplate inside the frame and a dark,
plain surround. Photograph straight down in daylight or under a lamp.

**Photos never leave your browser.** The detector loads only when you
select a file. The blue overlay shows the recovered 42 mm lattice; amber
shows the item outline. Inspect both before selecting **Apply footprint**.
This fills the existing footprint parameter and requests one live preview;
only the encoded outline and model parameters go to the render service.
The existing STL download uses the current parameter values.

The panel's clearance slider edits the same value as the Parameters control.
**Type pocket depth yourself:** the photo gives the outline only, not depth.
Accuracy measured on synthetic renders: **0.79 mm mean / 1.61 mm max**.
Real-photo measurements are pending; check the overlay and allow clearance.

Errors keep the detector's exact message and add the following advice:

| Message | Advice |
|---|---|
| `no perimeter lattice contrast` | Show the whole baseplate on a dark, plain surface. |
| `no board boundary` | Show the whole baseplate on a dark, plain surface. |
| `board boundary is not a visible rectangle` | Show the whole baseplate on a dark, plain surface. |
| `perimeter does not support a 42 mm lattice` | Use a Gridfinity baseplate 2–6 cells per side. |
| `board touches image edge` | Step back so the whole baseplate is inside the frame. |
| `no item contour` | The item must contrast with the plate (colour or darker). |
| `contour cannot meet the 0.3 mm / 256 vertex contract` | Simplify the item's outline or move the camera closer. |
| `footprint must fit 6x6 cells (252x252 mm)` | The item is too large for a 6×6 bin. |
| Server: `footprint + wall exceeds 6x6 cells` | Reduce clearance or wall_min, or pick a manual size. |

The server's size error appears under the footprint parameter after Apply.

## Capture pipeline (TypeScript)

CB3a (`pst-r02mp.5`, canonical spec rev 3) ports the bare/paper threshold
path from main `a6d6a6590d9388b6e8e3121eb9d05639abeb874f` into `lib/capture/`.
`capture(File | Blob | ArrayBuffer)` returns the encoded footprint, metric
ring, grid homography/confidence/extent, and rectified RGB image/origin.
The nine steps follow [CB1's summary](../build123d/docs/capture-bins-spike.md#cb3-algorithm-summary-nine-steps),
with two branches trimmed:

1. Decode RGB uint8. Browser `createImageBitmap` honours EXIF orientation;
   node tests decode PNG using the single added dev dependency, `pngjs`.
2. Fit the largest pale rectangular board outline. The ArUco branch is omitted.
3. Correlate perimeter strips to infer the number of 42 mm cells.
4. Solve the image-pixel-to-millimetre homography.
5. Warp at 0.20 mm/pixel, retaining metric origin and board extent.
6. Exclude the 3 mm outer rim or pixels outside detected paper bounds. The
   ArUco marker-corner branch is omitted.
7. Threshold chroma >35 or gray <65, then close gaps with a 3×3 kernel.
8. Keep the largest external contour, simplify at 0.3 mm, reject outside
   3–256 distinct vertices, and ignore holes.
9. Map to millimetres, quantize to 0.01 mm, validate, and encode `v1`.

The panel, human review overlay, registry flag, and render request are supplied by
CB3b. ArUco was dropped for its poorer accuracy, missed calibrations and lack
of a capture-plate model ([CB1 decision](../build123d/docs/capture-bins-spike.md#measurements)).
Constants and validation messages cite the Python source lines in each module.
The pre-wall limit is `footprint must fit 6x6 cells (252x252 mm)`;
the later server model's `footprint + wall exceeds 6×6 cells` remains a
separate constraint. No real-photo accuracy claim is made.

### Python oracle and reproduction

From `build123d/`, run:

```sh
uv run --group capture python -m capture.baseline
uv run --group capture pytest tests/test_capture_baseline.py -q
```

The committed `build123d/tests/fixtures/capture/python-footprints.json` has
`source_main`, `opencv`, `python`, `machine`, `cpu`, `threads: 1`,
`mm_per_px: 0.2`, and `records` sorted by PNG name. `mm_per_px` is the
rectified resolution; it is distinct from `measurements.json`'s
`mm_per_source_pixel` source-image resolution. Each record contains `png`,
`sha256`, `kind`, `result`, `footprint`, `error`, `vertices`, `area_mm2`, and
`truth_mm` copied from the measurement record or stress case. Area is measured
from the encoded ring. A failed contour retains `kind: "lattice"`; a failed
calibration has `kind: null`. Error rows have null footprint/area and zero
vertices. Truth is advisory and is never used by the fitting pipeline.

The denominator is fixed at 15: twelve bare/paper fixtures plus same-colour,
shadow, and edge-overhang stress cases; no ArUco or renderer-golden images.
Generation sets `cv2.setNumThreads(1)` before processing. Freshness compares
names, hashes, results, kind, errors, vertex counts and truth exactly; parsed
ring coordinates tolerate 0.05 mm and area tolerates 0.1 mm² across platforms.
Only the parsed ring is compared, so raster-derived wire strings need not
be byte-identical after regeneration. Pure-string `encode(parse(s))` is
separately required to preserve every committed footprint byte-for-byte.

### Detection errors

`DetectionError` preserves the reachable Python strings verbatim:

- `no perimeter lattice contrast`
- `perimeter does not support a 42 mm lattice`
- `no board boundary`
- `board boundary is not a visible rectangle`
- `board touches image edge`
- `no item contour`
- `contour cannot meet the 0.3 mm / 256 vertex contract`

Encoding errors also retain Python's messages, including explicit closure,
repeated vertices, adjacent overlap, crossings/touches, finite pairs,
coordinate magnitude, 25 mm² minimum area, vertex count, byte limit, and
6×6 span. They remain distinct from detection failures.

### Vendored runtime

OpenCV.js **5.0.0** is the official prebuilt file from the
[5.0.0 release docs archive](https://github.com/opencv/opencv/releases/tag/5.0.0),
member `js/bin/opencv.js` (identical to `doc/doxygen/html/opencv.js`).
The tagged online `opencv.js` URL returned 404; the release archive supplied
it. This matches the Python baseline's OpenCV 5.0.0, wheel 5.0.0.93: **no
major-version skew**. The unmodified file contains WASM, needs no separate
asset or runtime CDN, and is committed without Git LFS.

**Size flag:** 16,211,109 bytes (16.21 MB / 15.46 MiB), increasing the largest
tracked blob from about 2.03 MB. This exceeds the spec's 12 MB flagging
threshold; proceeding is explicitly permitted. SHA-256:
`bf6130c3d755915e5d005b69e574225817f98dc5556fe640628f8f18c1eb568f`.
See [NOTICE](../public/vendor/opencv/NOTICE) and the accompanying Apache-2.0
license. `scripts/vendor-libs.sh` manages only SCAD libraries.

`loadOpenCV()` caches one promise. In browsers it inserts one local script
on first use and awaits runtime initialization; node tests load that same
file. The pipeline imports OpenCV only through this loader. Mat/contour
handles are deleted after use, including detection failures; returned pixel
buffers and homographies own their data.

The capability test enumerates every runtime call: `Mat`, `Mat.ones`,
`MatVector`, `Size`, `matFromArray`, `cvtColor`, `threshold`, `findContours`,
`contourArea`, `arcLength`, `approxPolyDP`, `getPerspectiveTransform`,
`warpPerspective`, `boundingRect`, `morphologyEx`, and `getBuildInformation`.
All are available; no missing-function fallback is needed. Typed-array loops
implement NumPy's reductions/masks, and an explicit 3×3 matrix calculation
implements the optional full-image rectification transform.

### Cross-implementation parity

From the repo root:

```sh
CAPTURE_PARITY_TABLE=/tmp/capture-parity.md npx vitest run lib/capture
```

The gate compares TypeScript against the committed Python result on each
identical PNG: symmetric boundary Hausdorff ≤0.6 mm, area delta ≤1%, and
mean Hausdorff over all 13 footprints ≤0.3 mm. Boundary sampling at ≤0.02 mm
plus a 0.01 mm allowance gives a conservative Hausdorff upper bound; identical
rings are exactly zero. Errors must match in class and exact message. The
truth column is advisory, including the deliberately poor shadow case.
All 13 rings match exactly here (mean 0 mm, every area delta 0%).

| PNG | Python vertices | TS vertices | Hausdorff mm (upper bound) | Area delta % | TS vs truth mm (advisory) |
|---|---:|---:|---:|---:|---:|
| cup100-p2-bare-t0.png | 27 | 27 | 0.0000 | 0.0000 | 0.5220 |
| cup100-p2-paper-t0.png | 27 | 27 | 0.0000 | 0.0000 | 0.5220 |
| cup84-p1-bare-t15.png | 24 | 24 | 0.0000 | 0.0000 | 0.3725 |
| cup84-p1-paper-t15.png | 24 | 24 | 0.0000 | 0.0000 | 0.3533 |
| cylinder30-p0-bare-t15.png | 31 | 31 | 0.0000 | 0.0000 | 1.0028 |
| cylinder30-p0-paper-t15.png | 31 | 31 | 0.0000 | 0.0000 | 1.0028 |
| cylinder40-p1-bare-t0.png | 34 | 34 | 0.0000 | 0.0000 | 1.3400 |
| cylinder40-p1-paper-t0.png | 34 | 34 | 0.0000 | 0.0000 | 1.3400 |
| cylinder50-p2-bare-t15.png | 35 | 35 | 0.0000 | 0.0000 | 1.6216 |
| cylinder50-p2-paper-t15.png | 35 | 35 | 0.0000 | 0.0000 | 1.6216 |
| label-p0-bare-t0.png | 8 | 8 | 0.0000 | 0.0000 | 0.2107 |
| label-p0-paper-t0.png | 8 | 8 | 0.0000 | 0.0000 | 0.2107 |
| stress-edge-overhang.png | — | — | board boundary is not a visible rectangle | — | — |
| stress-same-colour.png | — | — | no item contour | — | — |
| stress-shadow.png | 31 | 31 | 0.0000 | 0.0000 | 10.3374 |
