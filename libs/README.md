# Vendored OpenSCAD Libraries

These are exposed to OpenSCAD via `OPENSCADPATH=libs/` (set by the skill
helpers). When authoring a model, prefer a library primitive over hand-rolling
geometry.

| Library      | Purpose                                       | Pinned SHA  |
|--------------|-----------------------------------------------|-------------|
| NopSCADlib   | Mechanical + project utilities, vitamins      | `c9baa0e`   |
| threads-scad | ISO metric threads, bolts, nuts, washers      | `4ae9aeb`   |
| MCAD         | General-purpose shape / fastener helpers      | `bd0a7ba`   |
| BOSL2        | Attachment / transform system; broad toolkit  | `456fcd8`   |
| QuackWorks   | Multiboard / Multiconnect accessory generators | `6123129`   |

BOSL2 is opt-in (R6 permits); added as a dependency for Multiboard work.
QuackWorks is **CC BY-NC-SA 4.0** — fine for personal use, derived parts
cannot be sold.

**BOSL2 pin note (st-kls, 2026-04-17):** pinned back from `663cd7c` (2026-04-16)
to `456fcd8` (2024-09-22, last commit before PR #1475). BOSL2 PR #1475
(`ae73c6d`, 2024-09-27) tightened `attachable()` to assert `is_finite(spin)`,
which breaks QuackWorks `snapConnector.scad:59` and
`multiconnectSlotDesignBOSL.scad:211` — both pass `spin=[x,y,z]` vectors.
QuackWorks upstream HEAD (`6123129`) still uses the vector-spin syntax, so a
forward bump on QuackWorks is not available. The `456fcd8` pin is the newest
BOSL2 that accepts the syntax every pinned QuackWorks backer (snap + slot)
depends on. Verified renders without local patches: snap backer, slot backer.

## NopSCADlib — `use <NopSCADlib/...>`

Large mechanical library with "vitamins" (off-the-shelf hardware models) plus
utilities. Start by `use <NopSCADlib/core.scad>;` to get the shared helpers.

- `use <NopSCADlib/core.scad>;` — the shared core (math, common modules).
  Required by most other NopSCADlib headers.
- `use <NopSCADlib/vitamins/screw.scad>;` — parameterized screw models
  (`screw(M3_cap_screw, length)`, etc.). Pairs with `nut.scad`,
  `washer.scad`.
- `use <NopSCADlib/vitamins/ball_bearing.scad>;` — standard ball bearings
  (e.g. `ball_bearing(BB608)`).
- `use <NopSCADlib/utils/core/rounded_rectangle.scad>;` — 2D rounded rects
  (extrude for fillets / plate shapes).
- `use <NopSCADlib/printed/box.scad>;` — parameterized printable enclosures.

## threads-scad — `use <threads-scad/threads.scad>`

Efficient list-comprehension threading. Prefer this over hand-rolled helices
for any threaded feature.

- `ScrewThread(outer_diam, height, pitch=0)` — external thread rod.
- `ScrewHole(outer_diam, height)` — threaded hole (subtract from a solid).
- `MetricBolt(diameter, length)` — hex-head metric bolt.
- `MetricNut(diameter)` — hex nut sized to a metric thread.
- `AugerThread(...)` — self-tapping auger-style.

## MCAD — `use <MCAD/...>`

Grab bag of smaller utilities; lighter than NopSCADlib but covers basic
shapes and fasteners.

- `use <MCAD/nuts_and_bolts.scad>;` — `boltHole(...)`, `nutHole(...)`.
- `use <MCAD/regular_shapes.scad>;` — regular polygons, pipes, ellipses.
- `use <MCAD/teardrop.scad>;` — teardrop holes (3D-print-friendly horizontal
  holes).
- `use <MCAD/motors.scad>;` — stepper motor (NEMA) outline models.
- `use <MCAD/bearing.scad>;` — basic rolling bearings.

## BOSL2 — `include <BOSL2/std.scad>`

Belfry OpenSCAD Library v2. Large, well-documented toolkit used by many
community generators (including the Multiboard snap-backer). Unlike the other
libraries, BOSL2 expects `include <>` (not `use <>`) for `std.scad` because
it relies on global constants and operators.

- `include <BOSL2/std.scad>;` — imports the standard set (shapes, transforms,
  attachments, thread primitives).
- `use <BOSL2/threading.scad>;` — parametric threads (alternative to
  threads-scad; BOSL2 version has more profile options).
- `use <BOSL2/screws.scad>;` — ISO/UTS screw + nut generators.
- `use <BOSL2/rounding.scad>;` — fillet / chamfer 2D+3D utilities.
- `use <BOSL2/gears.scad>;` — involute gears, racks, worm gears.

## QuackWorks — Multiboard / Multiconnect accessories

Active community repo providing connector-back generators and accessory
shells that snap into Multiboard / Multipoint tiles (25mm grid, 6.25mm
standoff). Depends on BOSL2. **License: CC BY-NC-SA 4.0.**

- `use <QuackWorks/Modules/multiconnectGenerator.scad>;` — parametric
  accessory-back generator; pick this first for any Multiboard mount.
- `use <QuackWorks/Modules/snapConnector.scad>;` — standalone snap
  connector primitive.
- `use <QuackWorks/Modules/pushFitConnector.scad>;` — push-fit variant.
- `use <QuackWorks/Modules/multiconnectSlotDesignBOSL.scad>;` — the
  BOSL2-based slot geometry generator.
- Browse `QuackWorks/Deskware/`, `QuackWorks/Underware/`, `QuackWorks/Misc/`
  for full accessory examples to crib from.

**Multiboard constants (no library needed for these):**
- Grid pitch: 25mm (1 MU)
- Offset snap (DS Part A) standoff: 6.25mm
- Snap types: Regular (bidirectional), Moderate WB (unidirectional), Heavy WB
