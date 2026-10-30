# Bench projector mount

`holder_bench_projector_mount` (`holders/bench_projector_mount.py`, slug
`holder-bench-projector-mount`) is step 2 of the projector bench clamp (epic
pst-czxuk, bead pst-czxuk.4). It is a saddle over the cast faux-wood Halloween
bench top that carries the projector on a 1/4"-20 heat-set insert. Its front
cheek is the [lip clip](bench-lip-clip.md)'s C, its rear cheek is the
[width saddle](bench-width-saddle.md)'s plain cheek, and a ribbed plate between
them carries the insert boss. A second top, `top` = `flat` (bead pst-czxuk.5,
preset `flat-250`; solid since pst-czxuk.6), replaces the ribs and boss with
one solid slab the projector stands on; see
[Flat top](#flat-top-pst-czxuk5-solid-pst-czxuk6).

## Provenance

Fit results (step 1, reported by Sean on 2026-10-29):

- **Slab thickness 38 mm, `height_clearance` +0.2 seats** (inner height
  38.2 mm) → `slab_thickness` 38, `height_clearance` default 0.2. This is not a
  kit preset (the lip kit starts at +0.3). Sean printed a +0.2 lip coupon by
  setting the value on the lip clip's model page and confirmed it seats
  (2026-10-29 20:27Z, recorded on pst-czxuk.4). The castings vary by ±0.5 mm,
  so the clearance stays a parameter and can move in 0.1 mm steps.
- **Width 310 mm nominal.** The +3 saddle coupon (313 mm inner) seated but was
  snug in spots, and the width is uneven. So the mount does **not** register on
  width: `width_clearance` defaults to 4.0 (314 mm inner), and the rear cheek is
  a stop against rotation, not a locator. Only the front hook registers.
- **Lip overhang ≈ 12.7 mm beyond the pumpkin end blocks**, so the hook and the
  rear cheek are both 11.5 mm deep (12.7 − 1.2 margin, as on the coupons).

Projector: XGIMI Elfin Flip 4K, 1.55 kg, footprint 245 × 78 mm, 254 mm tall. It
sits centred front-to-back on the bench, tilts on its own stand, and mounts
through its 1/4"-20 socket with a male-to-male adapter.

Insert: 1/4"-20 heat-set, 1/2 in (12.7 mm) long, 8.0 mm nominal hole (Sean
confirmed). The modelled hole is 8.0 + `hole_compensation` 0.2 = 8.2 mm across,
13.7 mm deep (insert length + 1), with a 0.8 mm mouth chamfer.

## Geometry

The model frame is the print frame. The profile lies in XY (`mount_profile`)
and is extruded +Z by `length` (120 mm, range 80–300). The part prints on its
side as a prism, with the insert boss standing on the plate. In use +Y is up,
X runs front-to-back across the bench, and Z runs along it.

- **Front cheek:** `lip_clip_profile` at the same parameters (wall 5,
  hook_depth 11.5, edge_gap 0.5, lead_in 1.5). Below the slab top it is the lip
  coupon's C exactly; the test `assert_lip_c_identical` checks the area
  difference is zero at every endpoint and corner. The C's top jaw sits under
  the plate, so `plate` must be ≥ `wall`.
- **Plate:** `plate` 6 mm, resting on the slab top across the full width.
  Ribbed top only; for the flat top the slab height is derived (`deck_top`).
- **Rear cheek:** `cheek_wall` 4, `cheek_depth` 11.5, 1.5 mm lead-in. Its inner
  face is at `wall + bench_width + width_clearance`, leaving 3.5 mm of rear play
  at the defaults (4.0 less the 0.5 edge gap at the hook).
- **Ribs:** two full-length ribs (`rib_wall` 4, `rib_height` 15), centred
  `rib_spacing` 60 apart about the boss, with R 1 root fillets and R 1 tops.
- **Boss:** Ø `boss_od` 14, with its top flush with the rib tops. It sits on the
  slab centre line by default (`boss_x_offset` 0, + toward the rear) and at
  mid-length (`boss_z_offset` 0). The wall around the 8.2 mm hole is 2.9 mm, so
  `boss_od` must be ≥ hole + 2 × 2.5. The hole floor sits 1.3 mm above the plate
  top, or 7.3 mm above the slab. That stays ≥ 2 mm (`HOLE_FLOOR`) at every
  endpoint.

`width_clearance` runs 1.0–6.0. The default (4.0) sits below the ceiling, so
the endpoint table probes past it. At 6.0 the part is exactly 325 mm long
(BED_X). Anything wider raises the named bed refusal: for example
`bench_width` 315, or `width_clearance` 6 with `cheek_wall` 6.

### Printing: the boss and the hole

On its side the boss is a horizontal column. Its section is a teardrop with
45° flanks and a 2 mm flat tip facing the bed. The insert hole is a teardrop
whose flat roof faces up. The roof is cut at the circle's top, as in
`signs.pin_profile`, so the bore stays 8.2 mm across and 8.2 mm tall for the
insert, and the roof is a 3.4 mm bridge. The boss's root blend, top edge and
hole mouth are all 45° chamfers, because a fillet there would face down in
print.

The two flats are the only flat ceilings on the part (boss tip 2 mm, hole roof
3.4 mm). Both are far under the 10 mm bridge limit. `audit_exclusions` boxes
exactly those two faces (`bridges()`), because the overhang rule reads a flat
ceiling as 90°. The tests measure both spans and check each box holds exactly
its one face.

### Printer: H2S only

At the defaults the profile is **323 × 64.2 mm**, with `length` along Z. The
plan's "≈ 322 × 49" left out the rib and boss stack and the 5 mm lip wall. The
part needs the last 20 mm of X, so it prints on the **H2S**, or on the H2C's
**left nozzle only**. It does not fit the H2C's right nozzle (305 mm) or
dual-nozzle printing (300 mm). Print in **PCTG** for outdoors. It is a long,
flat-ish part on the bed, so expect to want a brim if the corners lift.

Volume: 286.7 cm³ at the defaults (about 364 g of PCTG), 191.6 cm³ for the
`short-80` preset and 476.9 cm³ for `long-200`. The 323 × 120 × 6 mm plate
alone is 233 cm³; the spec fixes it at 6 mm.

## Flat top (pst-czxuk.5, solid pst-czxuk.6)

Sean printed the ribbed first article and asked for a flat top instead
(2026-10-29 23:35Z): make the mount thick enough that its top is flush with
the insert, with a recess round the hole for the male-to-male adapter, so the
projector's feet rest on the mount. `top` = `flat` does that; `ribbed` (the
default) is unchanged, and the `short-80` and `long-200` presets keep main's
volume and bounding box exactly (`test_ribbed_presets_unchanged`).

The adapter, measured 00:30Z: a knurled disc Ø16 × 4 mm with an 8 mm thread
each side. The projector's 245 mm side runs along the bench with its feet
more or less at its ends, so the preset is **`flat-250`** (`top` flat,
`length` 250; `length` runs to 300, inside the 325 mm build height).

**Shape: one solid slab.** The first flat top (pst-czxuk.5) was a box deck: a
skin on two walls and a column, the hollow open at both ends. Sean sliced
`flat-250` and replaced it (2026-10-30 03:28Z): "get rid of all of that crazy
bridging and just make it solid at that height for the full width of the
bench. Let the sparse infill on the slicer handle material saving for the
interior space." So the plate is thickened into one solid slab over exactly
its own footprint, cheek to cheek across the bench (x = 0 to the rear cheek's
outer face) and the full length, from the slab top up to the deck top. There
is no box, no column, no channel and no skin, and the `deck_width`,
`deck_skin` and `deck_wall` parameters are gone. The slab's two long top edges
are R 1 (the plate's `OUTER_RADIUS`), the bed edges keep the 45° bed chamfer,
and the lip C and rear cheek are unchanged (`assert_lip_c_identical` holds
for both tops).

**Recess and hole.** `boss_x_offset` and `boss_z_offset` place them in the
slab. The recess is round, Ø `recess_d` 18 (the 16 mm disc + 1 mm radial;
12–24, and ≥ hole + 7 = 15.2 so the disc has a floor ring round the insert)
and `recess_depth` 6 deep, with a flat floor. The insert sits flush with that
floor. The hole below it is the same 8.2 mm teardrop bore, `pocket` =
max(`insert_length`, `adapter_thread`) + 1 deep (13.7 at the defaults). The
adapter's lower thread runs on through the insert into the free bore. The hole
floor stays `HOLE_FLOOR` (2 mm) above the slab. The recess floor is sharp by
function, like the hole floor: the disc seats on it. Both mouths are 0.8 mm
45° chamfers. Guards: the recess and its chamfer stay `END_MARGIN` (3 mm)
inside either end, and ≥ 2.5 mm (`INSERT_WALL`) from either side of the slab
(the second cannot bite inside the declared ranges: there is always ≥ 16 mm
of slab beside the recess).

**The deck top is derived, never set:** `deck_top` (above the slab) =
`recess_depth` + `pocket` + `HOLE_FLOOR` = 6 + 13.7 + 2 = 21.7 mm at the
defaults, 15.7 mm above the plate's old top (`deck_height`), and the
footprint is 323 × 64.9 mm. Set `recess_depth` from the adapter:

> `recess_depth` = body height + upper thread − what the projector's socket
> swallows − foot height

The defaults are 4 + 8 − ~6 − 0 = 6. If the socket takes the whole 8 mm
thread, 4.5 works (the formula gives 4; the extra 0.5 is clearance). Set it on
the model page. At the shallowest settings (`recess_depth` 1, `insert_length`
and `adapter_thread` 6) the deck top is 10 mm above the slab, never below the
thickest plate.

**Printing.** The pose is unchanged (the prism on its side). The recess and
the hole are horizontal bores with flat roofs facing up, both cut at the
circle's top. `recess_d` ≤ 24 keeps the recess roof ≤ 9.94 mm (2r(√2 − 1)),
under the 10 mm bridge limit. Nothing else bridges: the flat top has exactly
two flat ceilings, the recess roof (7.5 mm at the defaults) and the hole roof
(3.4 mm), and `bridges()` and `audit_exclusions` box exactly those (the box
deck's column tip went with the column).

**Infill is the material saving.** The model is solid; the printed plastic is
whatever the slicer's walls, top and bottom shells and sparse infill make of
it. The slicer runs perimeters round each bore, so the insert and the disc sit
in solid walls whatever the infill density.

**Load.** The insert now sits in the whole slab (≥ 16 mm of it beside the
recess), not a Ø23 ring, and the feet bear straight down on a solid top
instead of a 4 mm skin spanning 82 mm, so both of the box deck's stress
figures are moot. The bump's 1.1 N·m still enters at the insert; the slab
carries it into the bench as the ribbed plate does.

**Volume** (`part.volume`, the solid envelope, not the printed plastic):

| Case | Volume | vs ribbed@250 |
|---|---|---|
| `short-80` (ribbed) | 191.6 cm³ | unchanged from main |
| `long-200` (ribbed) | 476.9 cm³ | unchanged from main |
| ribbed, `length` 250 (not a preset) | 595.8 cm³ | — |
| `flat-250`, box deck (pst-czxuk.5, main) | 681.0 cm³ | +85.2 cm³ (+14.3 %) |
| `flat-250`, solid (pst-czxuk.6) | 1829.6 cm³ | +1233.8 cm³ (+207 %) |

The solid figure is the ask: the slab is 323 × 21.7 × 250 mm above the bench
top (1752 cm³, less the two bores) plus the cheeks below it. The design
guidelines' §3 shell/volume rule is waived for this top by Sean's choice: the
slicer's sparse infill does the saving.

## Load case

The checking material is PCTG. The load is 1.55 kg (15.2 N) with its centre of
mass ~130 mm above the socket, plus a 0.5 g lateral bump (7.6 N). The boss
section is 15 mm tall:

| Section | Moment | Section modulus (X / Z bump) | Bending stress |
|---|---|---|---|
| Boss root (solid teardrop, 164 mm²) | 1.10 N·m | 274 / 284 mm³ | 4.0 / 3.9 MPa |
| Just above the hole floor (ring, 110 mm²) | 1.09 N·m | 242 / 261 mm³ | 4.5 / 4.2 MPa |

The axial stress from the weight is 0.14 MPa. Bending stress in the boss runs
along Y, which lies in the print layers whichever way the bump comes; only
its shear crosses the layers. These figures are about a tenth of typical FDM
PCTG tensile strength. That strength is not datasheet-checked here, and the
brass insert, which stiffens the ring, is ignored.

The plate rests on the slab, so the weight goes straight into the bench, and
the ribs are not carrying a sag load. The front hook holds the mount down
against uplift.

Along the bench, a 0.5 g bump's tipping moment about the plate's end
(1.15 N·m, at a 151 mm lever) about equals the restoring moment of projector
plus mount over half the length (1.13 N·m). So the full-length hook is what
keeps the mount down in that direction. A longer `length` (the `long-200`
preset) doubles the margin if the first article rocks.

## Fitting

The profile is a constant prism and the slab is a constant prism. So **slide
the mount on from the end of the bench**, hook under the front lip, the way
the lip coupon goes on. The hook and the rear cheek are both 11.5 mm deep,
under the 12.7 mm overhang, so they pass outside the pumpkin end block.

Rocking it on from above does not work. With +0.2 vertical play the hooked C
can tilt only ≈ 1°, which lifts the rear cheek about 5 mm, short of its
11.5 mm depth.

This assumes the bench end is free to slide past. That is an inference from
the plan's "every cheek/hook ≤ 11.5 mm deep", not something measured; check it
on the first article.

## First article

Sean prints one at the defaults and checks:

1. It slides on and seats: plate flat on the top, hook under the lip, no rock.
2. The heat-set insert goes in square and flush in the 8.2 mm hole.
3. The projector, on its adapter, sits stable through a light push along the
   bench.

Out of scope: tilt, cable management, labels, a second projector.
