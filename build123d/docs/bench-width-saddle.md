# Bench width saddle (fit coupon)

`holder_bench_width_saddle` (`holders/bench_width_saddle.py`, slug
`holder-bench-width-saddle`) is step 1b of the projector bench clamp (epic
pst-czxuk, bead pst-czxuk.3): a short inverted-U saddle that spans the cast
faux-wood Halloween bench top across its width, printed as a five-coupon kit to
pin down that width the way the [lip coupon](bench-lip-clip.md) pins down the
slab thickness.

## Measurement provenance

Sean's tape reading (2026-10-29), which the coupon exists to refine:

- Bench top width ≈ **310 mm**, measured between the slab's two long edge
  faces → `bench_width` default. The plan review checked `photo-3.jpg` and
  confirmed 310 mm is the cross-width (the axis on which the two end blocks
  sit side by side), not the slab's length.
- The slab overhangs the end blocks by ≈ 1/2 in = 12.7 mm (the lip coupon's
  reading), so `cheek_depth` defaults to 11.5 = 12.7 − 1.2 mm, mirroring the lip
  coupon's `hook_depth`.
- The surfaces are textured castings (expect ±0.5 mm per face) and the top
  edges may be rounded. So both cheek tips carry a 45° `lead_in`, and both
  cheek roots carry a `jaw_root_radius` fillet that clears a rounded edge.

Reference photos are in the city repo, not this one:
`assets/incoming/bench-projector-clamp-2026-10-28/` (see the lip coupon's page
for what each photo shows).

## Geometry

The model frame is the print frame. The inverted-U profile lies in XY
(`saddle_profile`) and is extruded +Z by `coupon_length`, so the coupon prints
on its side as a prism with no supports.

In use, +Y is up:

- The bar (y `cheek_depth`..`cheek_depth + wall`) rests on the slab top.
- A cheek (x 0..`wall` and its mirror) hangs `cheek_depth` down each long edge
  face.
- The inner width between the cheek faces is `bench_width + width_clearance`.

The label is debossed 0.6 mm (`INLAY_DEPTH`) into the bar's outer face. Its
baseline runs along X, the bench width, so it reads across the bench when the
coupon sits on top. That convention is chosen so `coupon_length` only has to
hold the glyph **height** (`+3.0` is 6.7 mm tall at `text_size` 9 against
11 mm of room at the default 15 mm length); a baseline along the coupon length
would need about 20 mm of room. Step 2 should keep it. By default the label
shows the signed `width_clearance`, for example `+1.0`.

## Printer: H2S only

The widest preset is 310 + 3 + 2 × 4 = **321 mm** long, against `BED_X` 325 mm
(`holders/printer.py`). That is why `wall` defaults to 4, and why any
over-wide combination raises a ValueError naming `bench_width` as the thing to
reduce. The part needs the last 20 mm of X, so it prints on the **H2S**, or on
the H2C **left nozzle only**. It does not fit the H2C right nozzle (305 mm) or
dual-nozzle printing (300 mm). Print it in PLA or PCTG, and expect a long, thin
part to want a clean bed and a brim if the corners lift.

## Fit-kit procedure

1. Bake or download the five presets from the catalog:
   `fit-minus-1-0`, `fit-plus-0-0`, `fit-plus-1-0` (the default),
   `fit-plus-2-0` and `fit-plus-3-0`. They bracket the tape reading in 1 mm
   steps, from 309 mm to 313 mm inner width. Locally, run
   `uv run python scripts/export.py --presets-only <dir>`.
2. Print the kit, or just the coupons you want. Use the declared pose: on its
   side, label face vertical.
3. Drop each coupon over the bench top where the clamp will sit. For each one,
   report:
   - whether it seats fully (bar flat on the top, both cheeks down the edges);
   - whether it rocks or slides across the width;
   - which coupon is the snuggest one that still seats.
   If none fits, measure the width again at that spot.
4. The mayor appends the report to pst-czxuk.3. It seeds the step-2 bead.

Out of scope here: the real clamp (step 2), the 1/4"-20 insert boss, and any use
of the slab thickness.
