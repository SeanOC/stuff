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
