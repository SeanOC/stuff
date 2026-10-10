# Capture bins: CB1 evidence and browser contract

Measured against `origin/main c332021e23316252ade3453be8eb46fb2b16abf6`
(canonical spec rev 4, `pst-r02mp.1`). **Use a bare, neutral baseplate and
colour/luminance thresholding as the next prototype baseline. This experiment
DOES NOT establish accuracy safely below a 1 mm clearance.** The best method
has 0.790 mm mean / 1.612 mm maximum Hausdorff error, despite perfect grid recall
on the bare-plate set. Human contour review and real-photo validation are needed
before CB3 treats these contours as dimensions suitable for manufacturing.

## Experiment

The generator builds an actual 4×4, 42 mm-pitch baseplate from
`gridfinity.baseplate.socket_cutout()` (4 mm top corner radius, 4.65 mm profile,
1 mm solid floor). Six CAD objects use existing registered builders without
changing their definitions: blank label card, cup-lid holders of diameter
84 and 100 mm, and cylindrical holders of diameter 30, 40 and 50 mm (height
30 mm, one slot). Each uses the remaining registry defaults. These are six
object instances across three model families, not six unrelated silhouettes.
Full resolved geometry comes from the pinned source revision; overrides are in
the JSON. Ground truth is the Shapely union of tessellated XY triangles, retaining
the exterior ring and simplifying at 0.01 mm. Internal holes are deliberately
ignored, as required for an outer pocket footprint.

For every object we use poses `(0°, 0, 0)`, `(27°, +3, -2)` and
`(-38°, -2, +3)` mm. Every pose has 0° and 15° planar-camera tilts and all four
backgrounds: **144 measurements**. Source rendering is 0.25 mm/pixel, metric
rectification 0.20 mm/pixel. The renderer uses a z-buffer and per-vertex Lambert
shading (`0.6 + 0.9 * Lambert`, clipped), reusing only the camera-basis helper
from `scripts/thumbnail.py`. Fixed bounds determine extent, never auto-fit.
Perspective uses a known 500 mm camera distance, followed by Gaussian blur
(sigma 0.45 source pixels) and seeded sparse ±1 intensity noise.

The camera warp acts on the already rendered image: **height parallax is absent**.
There is no lens distortion, rolling shutter, automatic exposure, surface texture,
or natural shadow simulation in the main matrix. Object colour is blue; bare/paper plates are
neutral grey on dark surrounds, and skeleton plates are dark on light surrounds. The three additional adverse cases below
probe colour ambiguity, a deliberately strong synthetic cast shadow, and overhang.
These are controlled falsification examples, not a measured phone-photo distribution.

Backgrounds:

- Skeleton: dark 168×168 mm frame with cross-shaped openings and corner pads,
  on a light surround. These 36 rows have no committed PNGs.

- Bare: the entire 168×168 mm plate; its outer rectangle and perimeter sockets
  must remain visible against a surround that contrasts with the plate.
- Paper: a 105×105 mm white square centred on that plate, leaving a 31.5 mm
  border. White-pixel bounds locate the segmentation region; sockets on the
  exposed border still calibrate scale. Objects extending beyond the paper are
  clipped by this baseline and counted as errors, not removed from the table.
- Capture plate: a synthetic smooth 84×84 mm (2×2 cells) square, with four
  10 mm `DICT_4X4_50` ArUco markers (IDs 0,1,2,3 clockwise from upper left).
  Marker bounds are `[3,13]` or `[71,81]` mm on each axis, with a white surround.
  All four markers are required. Marker/quiet-zone corners are excluded from
  segmentation. This is an image experiment, not a newly registered CAD model.
  The main `opencv-python-headless` wheel supplies ArUco here; CB3 must explicitly
  verify that its OpenCV.js build exposes the matching dictionary/detector.

## Measurements

The table includes all 144 runs, including the 126 whose PNGs are not committed.
Each cell contains 18 object/pose cases. Error aggregates use successfully
recovered contours only; grid recall and contour counts expose the denominator.
Time includes image-only detection, rectification, one segmentation/contour
method and offline polygon validation/error calculation; failed detections retain
their time. This is a conservative wall-time bound for the image pipeline. It excludes disk I/O, imports, CAD
construction and fixture rendering. Detection is shared when benchmarking all
four methods but charged to each reported pipeline time. All methods stayed
below 2 seconds here; this is not a browser performance guarantee.

Hardware: AMD Ryzen 7 8745H laptop-class CPU, 16 logical CPUs, Linux x86_64;
OpenCV 5.0.0, Python 3.14.4; OpenCV restricted to one thread. Exact versions and
unrounded per-image values are in `tests/fixtures/capture/measurements.json`.

| Background | Tilt | Method | Grid recall | Contours | Hausdorff mean / max (mm) | Area error mean / max (%) | Time mean / max (s) | >2 s |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| bare | 0° | threshold | 18/18 | 18/18 | 0.780 / 1.611 | 0.802 / 2.578 | 0.049 / 0.053 | 0 |
| bare | 0° | periodic | 18/18 | 18/18 | 0.779 / 1.611 | 0.707 / 2.751 | 0.079 / 0.086 | 0 |
| bare | 0° | grabcut | 18/18 | 18/18 | 1.826 / 4.588 | 1.825 / 5.154 | 0.478 / 0.528 | 0 |
| bare | 0° | structural | 18/18 | 15/18 | 23.455 / 39.843 | 125.924 / 361.897 | 0.763 / 0.842 | 0 |
| bare | 15° | threshold | 18/18 | 18/18 | 0.801 / 1.612 | 0.608 / 1.711 | 0.049 / 0.052 | 0 |
| bare | 15° | periodic | 18/18 | 18/18 | 0.800 / 1.612 | 0.498 / 1.876 | 0.080 / 0.089 | 0 |
| bare | 15° | grabcut | 18/18 | 18/18 | 2.275 / 5.826 | 3.163 / 11.359 | 0.480 / 0.562 | 0 |
| bare | 15° | structural | 18/18 | 5/18 | 33.545 / 35.583 | 194.933 / 361.723 | 0.744 / 0.956 | 0 |
| paper | 0° | threshold | 18/18 | 18/18 | 0.980 / 2.727 | 1.304 / 9.598 | 0.050 / 0.054 | 0 |
| paper | 0° | periodic | 18/18 | 18/18 | 1.162 / 2.727 | 0.766 / 7.791 | 0.072 / 0.081 | 0 |
| paper | 0° | grabcut | 18/18 | 18/18 | 1.994 / 3.905 | 3.290 / 9.620 | 0.465 / 0.510 | 0 |
| paper | 0° | structural | 18/18 | 7/18 | 28.905 / 44.474 | 81.938 / 99.229 | 0.714 / 0.937 | 0 |
| paper | 15° | threshold | 18/18 | 18/18 | 1.016 / 2.872 | 1.079 / 8.394 | 0.049 / 0.053 | 0 |
| paper | 15° | periodic | 18/18 | 18/18 | 1.200 / 2.727 | 1.259 / 5.551 | 0.072 / 0.081 | 0 |
| paper | 15° | grabcut | 18/18 | 18/18 | 2.418 / 4.960 | 4.695 / 9.393 | 0.456 / 0.517 | 0 |
| paper | 15° | structural | 18/18 | 8/18 | 28.084 / 44.474 | 83.332 / 99.291 | 0.704 / 0.870 | 0 |
| aruco | 0° | threshold | 14/18 | 14/18 | 2.981 / 21.980 | 6.549 / 59.699 | 0.013 / 0.014 | 0 |
| aruco | 0° | periodic | 14/18 | 14/18 | 3.077 / 21.980 | 6.630 / 59.445 | 0.019 / 0.021 | 0 |
| aruco | 0° | grabcut | 14/18 | 14/18 | 2.975 / 21.980 | 6.552 / 59.699 | 0.126 / 0.146 | 0 |
| aruco | 0° | structural | 14/18 | 7/18 | 10.095 / 46.176 | 11.817 / 64.819 | 0.187 / 0.256 | 0 |
| aruco | 15° | threshold | 14/18 | 14/18 | 3.020 / 21.980 | 6.583 / 59.629 | 0.013 / 0.014 | 0 |
| aruco | 15° | periodic | 14/18 | 14/18 | 3.140 / 21.980 | 6.949 / 58.273 | 0.019 / 0.020 | 0 |
| aruco | 15° | grabcut | 14/18 | 14/18 | 3.017 / 21.980 | 6.549 / 59.699 | 0.116 / 0.132 | 0 |
| aruco | 15° | structural | 14/18 | 6/18 | 16.192 / 74.596 | 16.770 / 82.708 | 0.185 / 0.253 | 0 |
| skeleton | 0° | threshold | 18/18 | 0/18 | — | — | 0.064 / 0.072 | 0 |
| skeleton | 0° | periodic | 18/18 | 14/18 | 1.522 / 6.044 | 0.443 / 1.067 | 0.095 / 0.104 | 0 |
| skeleton | 0° | grabcut | 18/18 | 0/18 | — | — | 0.582 / 0.693 | 0 |
| skeleton | 0° | structural | 18/18 | 15/18 | 16.564 / 64.529 | 15.009 / 58.463 | 0.744 / 0.992 | 0 |
| skeleton | 15° | threshold | 18/18 | 0/18 | — | — | 0.065 / 0.072 | 0 |
| skeleton | 15° | periodic | 18/18 | 4/18 | 5.116 / 10.337 | 0.990 / 1.155 | 0.096 / 0.107 | 0 |
| skeleton | 15° | grabcut | 18/18 | 0/18 | — | — | 0.610 / 0.669 | 0 |
| skeleton | 15° | structural | 18/18 | 16/18 | 3.791 / 16.955 | 6.061 / 21.037 | 0.737 / 0.835 | 0 |

Periodic subtraction estimates a per-pixel-phase median over 42 mm cells, then
thresholds its RGB residual; on the flat paper/marker backgrounds it uses a
constant robust median instead. GrabCut uses the same colour/luminance candidate
mask, eroded foreground seeds, hard background from calibrated 42 mm cells with no
item candidates, and probable background around items in occupied cells;
it runs two iterations. This is a comparison of four concrete methods, not an
exhaustive search for the best segmentation model.

The bare threshold baseline wins on accuracy, recall and complexity. Its periodic
variant gives essentially the same Hausdorff error for about twice the time.
GrabCut expands into the background on several objects and is both slower and
less accurate. The paper's bounded working area clips larger silhouettes. The
84 mm marker plate is too small for this object set: 8/36 missing calibrations,
and up to 21.980 mm contour error even among detected cases. Its small-object
speed advantage does not justify requiring a new capture-plate model from CB2.

A separate calibration check on the committed successful images samples a 3×3
metric grid through the known generating camera transform and the recovered H.
Maximum displacement is 0.095 mm on both bare/paper (54 sample points each),
and 0.245 mm on ArUco (36 points). This subset suggests the measured contour
errors are dominated by segmentation/raster processing rather than scale recovery;
it is not a claim about real-camera calibration.

At the worst bare-plate case (`cylinder50-p2-bare-t15`), the largest discrepancies
are the narrow concave junctions between the round holder and its back plate.
The 0.20 mm raster and 3×3 closing remove thin gaps; a small area error therefore
coexists with a 1.612 mm boundary error. RDP uses 0.3 mm tolerance but is **not**
an end-to-end accuracy guarantee. Shapes exceeding 256 simplified vertices are
rejected rather than silently increasing that tolerance.

## Failure modes seen

These probes use the 30 mm cylindrical holder on the bare plate at 15°.
They are committed separately from the balanced matrix; their errors are not
mixed into its aggregates.

| Probe | Grid | Threshold Hausdorff / area error | Periodic | GrabCut |
|---|---|---|---|---|
| Same neutral colour as plate | detected | no contour | 20.011 mm / 83.681% | no foreground seeds |
| Strong offset shadow | detected | 10.058 mm / 26.141% | 10.339 mm / 28.630% | 10.258 mm / 28.592% |
| Item overhanging right edge | rejected | no contour | no contour | no contour |

The shadow is an outer-silhouette mask shifted 6 mm right / 4 mm down and
multiplied into the background at 28% brightness before drawing the object.
The same-colour probe paints the visible object pixels grey 180. The overhang
probe translates the actual object +75 mm. These deliberately expose how fragile
thresholding is outside its capture protocol; grid confidence alone does not
measure contour quality. Missing markers, cropped board boundaries, featureless
borders and nonrectangular board outlines must trigger recapture. A confidence
value is a correlation/reprojection score, not a calibrated probability.

## Coordinates and encoding for CB2

`detect_grid(rgb)` returns `Grid(H, confidence, size_mm, kind)`. For an unmarked
plate it identifies the visible outer rectangle and counts the repeated sockets
along both perimeter axes (2–6 cells), using their known 42 mm pitch. Its origin
is the visible upper-left lattice corner, +X right and +Y down. Lattice symmetry
means this is a local image-oriented frame, not persistent board identity.
ArUco uses the fixed ID layout to remove that ambiguity.

`rectify(rgb, grid.H, size_mm=grid.size_mm, kind=grid.kind)` returns RGB pixels,
`mm_per_px` and `origin_mm`. Without an extent it covers the transformed source
image and may return a negative origin. `segment(rectified, method)` returns a
binary mask. `footprint(mask, mm_per_px=..., origin_mm=...)` returns an explicitly
closed exterior ring in that same metric frame. Input is RGB uint8, never BGR.
Production callers must validate and inspect the contour before accepting it.

The proposed wire format is `v1;x,y;x,y;…;x,y`, with **explicit repeated first
vertex**, decimal millimetres at 0.01 mm resolution, at most 256 distinct vertices
(the closing copy is extra), and at most 16 KiB UTF-8. Example:
`v1;0.00,0.00;10.00,0.00;10.00,10.00;0.00,10.00;0.00,0.00`.
`capture.encoding.parse()` and `encode()` are stdlib-only and can be imported
without loading OpenCV. `encode()` validates after rounding, so quantization
cannot silently create a duplicate vertex or invalid ring.

The validator rejects unknown versions, non-finite values, exponent notation,
excess decimal precision, unclosed/degenerate rings, repeated vertices,
self-crossings/touches, overlapping adjacent edges, area below 25 mm², and bounds
wider or taller than 252 mm (6×6 cells). Translation and either winding are allowed;
CB2 can translate the bounding box into its bin. Coordinates are additionally
bounded to ±1,000,000 mm to keep numeric operations finite. The bounding-box limit
is a footprint limit **before** wall/clearance allowances; CB2 must account for
those when sizing a bin and may need to reject a footprint at this upper bound.
Holes and multiple objects are outside this contract. Encoding size remains well
below the render service's 64 KiB total-body cap, leaving room for other params.

## CB3 algorithm summary (nine steps)

1. Read an RGB image; require the whole board and contrasting surround.
2. Detect four known ArUco IDs, or fit rectangular board candidates from both pale and dark polarities.
3. For an unmarked board, correlate perimeter profiles, falling back to interior profiles, to count 42 mm cells.
4. Solve image-pixel-to-mm homography; reject absent or inconsistent calibration.
5. Warp at 0.20 mm/pixel and keep the metric origin and board extent.
6. Exclude the outer rim, marker corners, or pixels outside detected paper bounds.
7. On pale plates threshold chroma >35 or luminance <65; on dark plates use
   the robust structural background residual. Close gaps with a 3×3 kernel.
8. Take the largest outer contour; for dark plates reject contact with the ROI
   boundary before simplifying at 0.3 mm and rejecting >256 vertices.
9. Map to millimetres, show for human review, quantize/validate and encode `v1`.

## Printed reference sheet v1 (Python reference)

Source main: `f6010d52f91257f2171b72a7f65de787784733a5`. The separate sheet
matrix reuses all six CAD objects and three poses (18 silhouettes), at 0°/15°
and neutral/warm illuminants. Its 72 PNGs live in `fixtures/capture/sheet/`,
each below 200 KB; `sheet-measurements.json` includes image homographies,
ground-truth outlines, detected marker corners, and error measurements.
`sheet-footprints.json` is a separate Python-only baseline for the future TS
port. The original 144-row measurements and three shared footprint baselines
are unchanged.

The detector chooses Letter/A4 from all 16 marker corners, requires mean
reprojection below 0.8 mm, re-bases the origin to the field, and applies
`bar_mm / 100` once. The sheet-only segmenter white-balances a copy, identifies
chromatic pixels at chroma >20, and accepts neutral pixels only below 0.55 or
above 1.30 times field lightness. It opens and closes with 1 mm elliptical
kernels (5×5 samples at 0.2 mm/pixel). The plate paths retain their existing
residual >48 threshold; the sheet rule independently accepts chromatic pixels
so a tinted card near field lightness is retained. The empty sheet has zero
mask pixels after opening. The field region has a 3 mm inset and no marker
corner exclusion because the markers lie outside the field.

All four lighting/tilt groups detect and recover 18/18 silhouettes and meet
the mean Hausdorff limit of 1.5 mm. The maximum error is reported separately;
the mean gate does not imply every individual contour is within 1.5 mm.

| Lighting | Tilt | Detection / footprint | Mean / max Hausdorff (mm) | Gate |
|---|---|---|---|---|
| neutral | 0° | 18/18 | 1.067 / 2.109 | PASS |
| neutral | 15° | 18/18 | 1.156 / 2.475 | PASS |
| warm | 0° | 18/18 | 1.063 / 2.109 | PASS |
| warm | 15° | 18/18 | 1.133 / 2.475 | PASS |

Regenerate only sheet artifacts from `build123d/`:

```sh
uv run --group capture python -m capture.synth --sheet
uv run --group capture python -m capture.real_sheet_oracle
uv run --group capture pytest tests/test_capture_sheet.py -q
```

## Real photos

**No real-plate accuracy claim yet.** The original two photographs exercise
named errors. The separate sheet records below include one locally measured
flat-card success; its personal photo is not published.
The inside-plate success test is skipped with the explicit reason
“awaiting a real photo with the item fully inside the plate” until both a photo
and caliper truth are supplied in `real/real-footprints.json`.

Sean's protocol:

1. Use a matte 4×4 Gridfinity baseplate on a plain surface that contrasts with the plate.
   Measure the outer span and at least three consecutive pitches with calipers
   or a steel ruler; record deviations from 168 mm / 42 mm, material and colour.
2. Photograph one marker pen, one hex key, and one small box separately. Lay each
   flat, entirely inside the board with a visible perimeter row. Record maximum
   length/width and height with calipers, and supply a dimensioned tracing or
   ruler-calibrated flatbed scan of each outline as independent ground truth.
3. Use the iPhone's main 1× camera, straight down at 40–60 cm. Keep the phone
   parallel to the board, all corners visible and the baseplate filling most
   of the frame with a narrow surround. Avoid digital zoom and portrait mode.
4. Take a daylight version and a lamp version of each item without moving it:
   six originals minimum. Keep the lamp direction/shadows visible; record phone
   model, distance, lighting, and which image matches each ground-truth outline.
5. Repeat with a white sheet trimmed so grid cells remain visible around it.
   Keep the entire item on the paper. If an actual 84 mm four-marker plate is
   available, photograph items that fit with all markers unobscured; do not
   fabricate validation images for this missing physical background.
6. Supply original HEIC/JPEG files, not resized screenshots or messaging-app
   previews. The mayor can convert to RGB PNG without rescaling, run the same
   methods and add per-image recall, Hausdorff, area and wall-time rows below.

| Real item | Daylight | Lamp | Ground truth / result |
|---|---|---|---|
| Marker pen (sharpie-daylight.png) | dark lattice, 168×168 mm, confidence 0.808449 | — | structural → `item crosses the plate edge`; barrel truth 12.75 mm, length unknown |
| Marker + calipers (sharpie-calipers.png) | boundary obstructed | — | `board obstructed by an object crossing its edge` |
| Hex key | pending | pending | pending |
| Small box | pending | pending | pending |

### 2026-10-09 printed sheet and plate negatives

Original JPEGs were converted to RGB PNG without rescaling; original JPEG and
PNG SHA-256 provenance lives in `real/sheet/sheet-footprints.json`. Sean
confirmed the printed check bar measures 100 mm. These new records and PNGs
are isolated under `real/sheet/`, including six additional plate negatives;
the two existing plate records stay in `real/real-footprints.json`.

The flat card fixture is held locally at
`rig-stuff/scratch/capture-photos/sheet-letter-2026-10-09/card.jpg` until a
non-personal flat item replaces it. The converted `real/sheet/card.png` is
local-only and ignored by git, pending Sean's explicit publication sign-off.
Its original JPEG hash, truth and measured ring remain in
`real/sheet/sheet-footprints.json`. Without the PNG, the flat-item test skips
with `local-only fixture: card.png not published`; the oracle warns and
preserves that record without claiming to replay it. Public-photo tests still
run, and the recorded flat result is historical evidence, not a fresh CI
measurement. Any later approval to publish the photo will be a follow-up.

| Photo | Result | Interpretation |
|---|---|---|
| Sheet bare | `no item contour` | 0 mask pixels after the 1 mm opening |
| Sheet cleaner | approximately 102.5 × 38 mm vs 95 × 28 mm truth | tall item, visible side wall; outside flat-item accuracy claim |
| Sheet Sharpie | `item crosses the sheet field` | cap crosses the field's top boundary; gray barrel also segments partially |
| Sheet card (~0.8 mm thick; local-only photo) | recorded 84.8 × 54.2 mm vs 85.60 × 53.98 mm truth | `inside-sheet`; both minAreaRect sides within 1.5 mm locally; CI replay skips without PNG |
| 4×4 plate bare | `board obstructed by an object crossing its edge` | unchanged detector error, no markers |
| 4×4 cleaner, Sharpie crossing, Sharpie off plate | `board boundary is not a visible rectangle` | unchanged detector errors, no markers |
| 2×2 bare, cleaner | `board obstructed by an object crossing its edge` | unchanged detector errors, no markers |

All eight real plate photos detect zero ArUco markers, and retain their
original errors. A neutral item near field lightness with chroma at most 20 remains a v1
limitation; a colored field is a future option, outside this version.

## Reproduction and CI

From `build123d/`:

```sh
uv sync --frozen --group capture
uv run --group capture python -m capture.synth --output tests/fixtures/capture
uv run --group capture pytest tests/test_capture_spike.py -q
uv run --group capture pytest tests/ -q
```

Generation is offline and separate from pytest. Eighteen representative PNGs
cover every object/background pair from the original three backgrounds, with poses/tilts distributed deterministically
(object index modulo three / two). Three stress PNGs and one 24×24 renderer golden
bring the committed total to **22 PNGs**, each below 200 KB. All 144 main rows
retain ground-truth rings, known camera transforms, source identity, pose, measured
errors, timings and failure reasons in JSON; committed images also have SHA-256s.
The generator preserves mesh tessellation provenance; its metric ground truth is
never passed to the detector, rectifier or segmenter. Only evaluation sees it.

Tests replay the 18 representative images plus stress cases, check fixture budgets
and full matrix coverage, validate the encoding (including rounding failures), and
compare the fixed-scale renderer with its small golden. A separate 2 mm upper
bound pins the observed bare baseline; it is a regression bound, **not** a claim
that the product's 1 mm-clearance goal passed.

Rev 4's WORKFLOW CARVE-OUT changes only `.github/workflows/bd123.yml`'s **fast
sync step** to `uv sync --frozen --group capture`. Capture is a non-default uv
group; the lock is regenerated. Test collection skips before importing capture
when cv2 is absent. The Dockerfile parity test excludes this dev/CI-only package;
no currently shipped model/script imports it. `services/bd-render/Dockerfile`
and `scripts/thumbnail.py` remain unchanged. Future CB2 use of the stdlib encoding
module must explicitly revisit packaging without pulling image analysis into the
render service. Fixture geometry inherits the source models' provenance; the
baseplate source carries CC-BY-SA-4.0 and Gridfinity Rebuilt-derived constants.


## Plate polarity and skeleton plates (Tier 1.1)

This extension was measured against `origin/main` a555403. Board candidates use
`gray > 85` and inverse threshold at 85, retaining the same quadrilateral
approximation and image-edge guard. An interior autocorrelation fallback handles
skeleton rims without socket lips. The strongest acceptable candidate records
`polarity=pale|dark`; confidence defaults to 0.5 (domain 0.3–0.8).

Pale bare/paper captures still default to `threshold`. Their twelve committed
oracle records are unchanged. Dark plates default to `structural`. The fourth
method folds the rectified image into 42 mm lattice cells and takes a median
RGB phase template across cells. Initial residual inliers and six trimmed
least-squares iterations fit each cell's RGB gain and offset using background
pixels; the cutoff is median + 2 MAD within four intensity strata learned from the
template quartiles, with a one-code-value numerical floor. Each brightness
range retains background inliers, so unequal lighting does not discard a whole
background class.
This excludes item/shadow outliers rather than dividing by an occupied tile's
median luminance. A local RGB envelope over ±2 pixels tolerates phase and
fractional-pixel resampling differences. Residuals above median + k MAD (k=5,
domain 3–8; one-code-value floor) become foreground. Shift tolerance is 1–3 px.
After 3×3 closing, coverage above 35% (domain 20–50%) raises
`item too large for the plate or background not modelled`.

On the supplied daylight image the default yields 20.2615% foreground and a
163.339 mm largest-component long axis. Its contour touches the 3 mm inset ROI,
so the capture raises `item crosses the plate edge` before contour encoding.
These numbers describe an invalid, edge-crossing capture and are not accuracy
measurements. The independent manual scale probe measures the whole marker at
168.298 mm; the earlier 134 mm output was fragmented. Reproduce the parameter
sweep with `uv run python scripts/probe_capture_structural.py`; reproduce the
independent annotations with `scripts/probe_capture_photo_scale.py`.

The complete skeleton matrix includes difficult CAD outlines: structural contour
recovery is 15/18 at 0° and 16/18 at 15°, with mean/max Hausdorff errors
16.564/64.529 mm and 3.791/16.955 mm respectively. Fragmentation and background
leakage remain visible in these measurements; the narrow white-rectangle test
and named real-photo errors do not establish general real-item accuracy.

Synthetic skeleton plates have a dark frame and corner pads, cross openings,
and a light surround with minimum channel 220. All 36 additional measurements
use `png=null`, preserving the 18 selected synthetic fixtures and image budget.
A white 30×12 mm rectangle is also tested through image-only detection and
segmentation, requiring each bbox side within 1 mm and coverage below 10%.
The two unscaled, orientation-baked real RGB PNGs have a separate 8 MB limit;
their sibling oracle stores original JPEG hashes, PNG hashes, method, result,
ring, and available caliper truth. The original synthetic baseline generator
remains measurements-driven and unchanged.


The successful synthetic white-item test also varies tile gain from 0.65 to
1.025 and offset from 0 to 9 RGB code values. Its recovered bbox is 30×12 mm;
foreground coverage is 1.404% under uniform light and 4.902% with the gain/offset
variation. The shared JSON contour oracle is regenerated with
`uv run python scripts/probe_capture_structural.py --synthetic-oracle tests/fixtures/capture/structural-footprints.json`.
Both Python and TypeScript compare these successful contours, in addition to
the unchanged pale-photo oracle and the real-photo error parity.
