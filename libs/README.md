# Vendored OpenSCAD Libraries

These are exposed to OpenSCAD via `OPENSCADPATH=libs/` (set by the skill
helpers). When authoring a model, prefer a library primitive over hand-rolling
geometry.

| Library                     | Purpose                                          | Pinned SHA | Vendored? |
|-----------------------------|--------------------------------------------------|------------|-----------|
| NopSCADlib                  | Mechanical + project utilities, vitamins         | `c9baa0e`  | menu only |
| threads-scad                | ISO metric threads, bolts, nuts, washers         | `4ae9aeb`  | menu only |
| MCAD                        | General-purpose shape / fastener helpers         | `bd0a7ba`  | menu only |
| BOSL2                       | Attachment / transform system; broad toolkit     | `456fcd8`  | ✅        |
| gridfinity-rebuilt-openscad | Gridfinity bins, baseplates, lite variants (MIT) | `910e22d`  | ✅        |
| QuackWorks                  | Multiboard / Multiconnect accessory generators   | `6123129`  | ✅        |

**Vendored** means `scripts/vendor-libs.sh` clones it at the pinned SHA
(it runs as the npm `prebuild` hook and in CI) — only those three are
present in a fresh clone, and they are the only ones shipped models use.
The **menu only** rows are an available-libraries menu for `/scad-new`:
documented pins, not cloned by the script. To actually use one in a
model, add it to `scripts/vendor-libs.sh` (or vendor via the `scad-lib`
skill) first. See `docs/deps-review-2026-07.md` for the July 2026
upstream review of every row.

BOSL2 is opt-in (R6 permits); added as a dependency for Multiboard work.
QuackWorks is **CC BY-NC-SA 4.0** — fine for personal use, derived parts
cannot be sold.

**BOSL2 pin note (pst-9sw, 2026-07-21):** pin **stays** at `456fcd8`
(2024-09-22). QuackWorks stays at `6123129` (still upstream HEAD). The
*original* reason for the hold is gone, but a new one replaced it — see the
end of this note.

History: st-kls pinned BOSL2 *back* to `456fcd8` because PR #1475 (`ae73c6d`)
tightened `attachable()` to assert `is_finite(spin)`, and two QuackWorks
backers — `snapConnector.scad:59` and `multiconnectSlotDesignBOSL.scad:211` —
pass `spin=[x,y,z]` vectors. That pin was the newest BOSL2 those two files
accept. A compat patch for the drift was tried and rejected: on the wasm
engine the BOSL2 slot backer aborts or hangs in *every* configuration under
v2.0.747 (pst-d7d, pst-q0l, pst-7bs).

That vector-spin blocker is now dissolved — by dropping both files instead of
patching them. `snapConnector.scad` was already unused by every model; the two
models that used `multiconnectSlotDesignBOSL.scad` moved to QuackWorks'
BOSL2-free master copy of the same backer,
`Modules/multiconnectSlotDesign.scad` (patch 0002 below). Nothing in the
catalog references either vector-spin call site now, so `is_finite(spin)` is
moot. That migration is what this change lands, and it is green on the current
pin: full sweep 720 passed / 20 skipped / 0 failed.

**The bump itself is still blocked, for a new and different reason.** Moving to
`fbcdfdd5` (v2.0.747) *with* the migration in place regresses 6 wasm sweep
cases that pass on `456fcd8` — `blu_black_tank_valve_mount` (`hex_ftf_left`/
`hex_ftf_right=37.5`, `slop=0`, `saddle_w=30`, `wall_t=5`) and
`blu_flow_meter_mount_80mm` (`base_w=100`), all `CGAL error in applyHull():
assertion violation`. Both are BOSL2 hull consumers, neither is touched by the
migration, and desktop CGAL export stays clean — the failure is wasm-only at
param extremes. A default-params-only check (pst-7bs) called this bump clean
and was wrong: **gate BOSL2 bumps with `npm run test:sweep`.** Until those 2
models' hull usage is fixed, the pin holds — which also means mitufy's
openConnect receivers (st-kls, pst-yr1) are still waiting on it.

**Local patches (st-79a, 2026-07-10):** `scripts/vendor-libs.sh` applies
`scripts/patches/<lib>/*.patch` after checkout; the `.vendor-sha` marker
embeds a fingerprint of the patch set so editing a patch re-vendors.
Patches are applied with `git apply -p1` (the CI image has git but not
`patch(1)`, st-1uw), so they must be git-apply-compatible unified diffs.
Current patches:

- `QuackWorks/0001-opengrid-snap-linear-extrude-click-holes.patch` —
  `openGrid/opengrid-snap.scad` cut its click holes with
  `cuboid(rounding=0.3, edges="Z", $fn=100)`. BOSL2 builds partial-edge
  cuboid rounding as `hull()` of 8 corner pieces; in the wasm engine
  `hull()` routes through CGAL and the micro-segmented pieces trip the
  `convex_hull_3.h:684` assert (st-7x7 class), and the same geometry
  exports non-watertight STLs for every openGrid-snap model. The patch
  cuts the identical stadium prism with `linear_extrude` of a rounded
  `rect()` — no hull. Drop the patch if upstream fixes the click holes.

- `QuackWorks/0002-multiconnect-nonbosl-backer-parameters.patch` —
  `Modules/multiconnectSlotDesign.scad` is the BOSL2-free master copy of the
  Multiconnect backer, and it is what `cylindrical_holder_slot` and
  `ego_lb6500_blower_mount` mount on (pst-9sw). Upstream's
  `multiconnectBack()` takes only `(backWidth, backHeight,
  distanceBetweenSlots)`; backer thickness, slot-ladder height and
  v1-dimple-vs-v2-snap retention are file-scope Customizer variables, which
  `use <>` does not import and a model cannot set. The patch promotes the
  three we need to module parameters, all defaulting to upstream's values so
  the geometry is unchanged at default arguments. Unlike the BOSL2-compat
  shim it replaces, it tracks no moving API — the file has zero BOSL2
  references — so it should not rot across BOSL2 bumps. Drop it if upstream
  promotes these itself.

Licensing note: the QuackWorks patch contains modified QuackWorks source
lines, so the patch file itself is a **CC BY-NC-SA 4.0** derivative — it is
not covered by the repo's MIT code license, despite living under
`scripts/`.

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

## gridfinity-rebuilt-openscad — `use <gridfinity-rebuilt-openscad/...>`

Parametric Gridfinity generator (kennetek/gridfinity-rebuilt-openscad,
v2.0.0). Produces bins, baseplates, and "lite" hollow-base bins that
fit the standard 42mm Gridfinity grid. The repo bundles its own copy of
`threads-scad` under `src/external/`, so the upstream `threads-scad/`
library row above is independent of this one.

- `use <gridfinity-rebuilt-openscad/gridfinity-rebuilt-bins.scad>;` —
  top-level customizer-style file. Easier to crib from than to call;
  most of its work is at the top level rather than inside a module.
- `include <gridfinity-rebuilt-openscad/src/core/standard.scad>;` —
  spec constants (`GRID_DIMENSIONS_MM`, `BASE_HEIGHT`, `d_wall`,
  `d_div`, hole radii, stacking-lip geometry). `include` (not `use`)
  because the API depends on the global constants.
- `use <gridfinity-rebuilt-openscad/src/core/gridfinity-rebuilt-utility.scad>;` —
  `height()` / `fromGridfinityUnits()` / `bundle_hole_options()`.
- `use <gridfinity-rebuilt-openscad/src/core/bin.scad>;` —
  `new_bin(...)`, `bin_render(bin) { ... }`, `bin_subdivide(bin, [x, y])`.
- `use <gridfinity-rebuilt-openscad/src/core/cutouts.scad>;` —
  `cut_compartment_auto(size, style_tab, top_left_only, scoop)`.
- `use <gridfinity-rebuilt-openscad/gridfinity-rebuilt-baseplate.scad>;` /
  `gridfinity-rebuilt-lite.scad` — sibling top-level files for plates
  and lite bins (no project model wires them up yet).

To override a stock spec constant (e.g. wall thickness), `include` the
`standard.scad` file and reassign after the include — OpenSCAD's
last-write-wins variable scoping makes this safe.

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
