# Bench projector mount

`holder_bench_projector_mount` (`holders/bench_projector_mount.py`, slug
`holder-bench-projector-mount`) is step 2 of the projector bench clamp (epic
pst-czxuk, bead pst-czxuk.4). It is a saddle over the cast faux-wood Halloween
bench top that carries the projector on a 1/4"-20 heat-set insert. Its front
cheek is the [lip clip](bench-lip-clip.md)'s C, its rear cheek is the
[width saddle](bench-width-saddle.md)'s plain cheek, and a ribbed plate between
them carries the insert boss.

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
and is extruded +Z by `length` (120 mm, range 80–200). The part prints on its
side as a prism, with the insert boss standing on the plate. In use +Y is up,
X runs front-to-back across the bench, and Z runs along it.

- **Front cheek:** `lip_clip_profile` at the same parameters (wall 5,
  hook_depth 11.5, edge_gap 0.5, lead_in 1.5). Below the slab top it is the lip
  coupon's C exactly; the test `assert_lip_c_identical` checks the area
  difference is zero at every endpoint and corner. The C's top jaw sits under
  the plate, so `plate` must be ≥ `wall`.
- **Plate:** `plate` 6 mm, resting on the slab top across the full width.
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
