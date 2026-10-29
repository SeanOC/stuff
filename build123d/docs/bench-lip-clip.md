# Bench lip clip (fit coupon)

`holder_bench_lip_clip` (`holders/bench_lip_clip.py`, slug `holder-bench-lip-clip`)
is step 1 of the projector bench clamp (epic pst-czxuk, bead pst-czxuk.1): a
short C-clip that hooks the lip of the cast faux-wood Halloween bench, printed
as a five-coupon kit to dial in the grip before the full clamp is drawn.

## Measurement provenance

Sean's rough tape measurements (2026-10-28), which the coupon exists to refine:

- Slab (bench top) thickness ≈ 2 in = **50.8 mm** → `slab_thickness` default.
- Lip depth (overhang beyond the pumpkin end block) ≈ 1/2 in = **12.7 mm** →
  `hook_depth` default 11.5 = 12.7 − 1.2 mm margin, so the hook clears the end
  block even near the ends.
- The surfaces are textured castings (expect ±0.5 mm), and the slab's top edge
  may be slightly rounded. So the spine stands `edge_gap` 0.5 mm off the edge
  face, and both jaw tips carry a 45° `lead_in`.

Reference photos are in the city repo, not this one:
`assets/incoming/bench-projector-clamp-2026-10-28/`

- `photo-1.jpg`: vertical tape on the slab end, showing the thickness and the
  overhang above the end block.
- `photo-2.jpg`: horizontal tape along the slab top near the end, showing the
  stepped end profile.
- `photo-3.jpg`: the whole setup. The slab overhangs the end block on every
  side, and the underside is open mid-span.
- `photo-4.jpg`: the projector on its loop stand, with HDMI and power on the
  side.

## Geometry

The model frame is the print frame. The C profile lies in XY (`lip_clip_profile`)
and is extruded +Z by `coupon_length`, so the coupon prints on its side as a
prism with no supports.

In use, +Y is up:

- The bottom hook (y 0..wall) reaches `hook_depth` under the overhang.
- The spine climbs the edge face.
- The top jaw rests `top_reach` onto the slab top.

The inner height is `slab_thickness + height_clearance`. The label is debossed
0.6 mm (`INLAY_DEPTH`) into the spine's outer face. Its baseline runs along the
lip, so it reads horizontally when the coupon sits on the bench. By default it
shows the signed `height_clearance`, for example `+0.8`.

## Fit-kit procedure

1. Bake or download the five presets from the catalog:
   `fit-plus-0-3`, `fit-plus-0-8` (the default), `fit-plus-1-3`, `fit-plus-1-8`
   and `fit-plus-2-3`. The repo's URL-safe preset ids replace the dot with a
   dash. Locally, run `uv run python scripts/export.py --presets-only <dir>`.
2. Print the kit, or just the coupons you want, in PLA or PCTG. Use the
   declared pose: on its side, label face vertical.
3. Slide each coupon onto the lip, top jaw first. For each one, report:
   - whether it seats fully (spine against the edge face, hook under the lip);
   - whether it rocks;
   - which coupon is the snuggest one that still seats.
   If none fits, measure the slab again where the clamp will sit.
4. The mayor appends the report to pst-czxuk.1. It seeds the step-2 bead.

## Step 2: the clamp

Step 2 extrudes the same `lip_clip_profile` longer and adds:

- a **1/4"-20 heat-set insert boss** on the top jaw. The hole diameter and
  depth come from Sean's insert datasheet and are **TBD**, never guessed;
- a **clamping screw** through the bottom hook or the spine, so the grip does
  not rely on the fit alone;
- **reach and length** sized to the projector's loop-stand footprint, for the
  male-to-male 1/4"-20 adapter;
- the winning `height_clearance` from the fit report as the new default.

Out of scope here: the boss, the screw and the projector-base geometry.
Wrapping the whole bench top is also out, because Sean chose the lip.
