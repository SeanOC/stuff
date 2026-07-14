# Imported STL → openGrid conversion playbook

How to take an externally-authored STL (a vendor bracket, a scanned
part, an operator upload) and turn it into a parametric model in this
repo that mounts to an [openGrid](https://www.printables.com/model/1214361)
wall panel and prints supportless.

Distilled from the `ego_powerhead_mount` series, which is the worked
example for every step:

| Step | Bead | PR |
| --- | --- | --- |
| Import + plugs + first snap grid | pst-3m2 | [#13](https://github.com/SeanOC/stuff/pull/13) |
| Snap orientation correction | pst-ozs | [#15](https://github.com/SeanOC/stuff/pull/15) |
| Supportless printability | pst-efb | [#21](https://github.com/SeanOC/stuff/pull/21) |
| Blending / edge finish | pst-5kz | [#27](https://github.com/SeanOC/stuff/pull/27) |

Follow the steps in order — each one exists because skipping it cost a
correction cycle the first time through.

## 1. Source STL: commit it, import() it

- Commit the reference mesh next to the model:
  `models/<name>_source.stl` (see `models/ego_powerhead_mount_source.stl`).
  It is both the geometry source and the fidelity baseline the
  invariants sidecar compares against forever after.
- **`import()`-based modeling is the default**, not a native remodel.
  The wasm render-path performance problem that once forced a native
  reconstruction (`ego_lb6500_blower_mount`) is fixed; imports render
  fine through the real pipeline now (expect ~30–40 s per wasm render
  for a ~8k-triangle mesh — slow, not fatal). See
  [docs/ci.md](ci.md) for the render pipeline.
- A silently-dropped import is a fatal pipeline error
  (`lib/wasm/closure.ts` missingAssets), but keep the sidecar's
  raycast comparison anyway — it's what proves the *right* mesh
  shipped, not just *a* mesh.
- Start the `.scad` by writing a measured **source-mesh anatomy**
  section in the header (frame conventions, key features, dimensions
  sliced off the mesh with trimesh). Everything downstream — plugs,
  snap placement, probes — hangs off those numbers.

## 2. Geometry prep: retire the old mounting features

The part used to mount some other way; those features are now dead
weight or print liabilities.

- **Fill screw holes with flush plugs** (PR #13 pattern): cylinders
  spanning the full plate thickness, flush at both faces, oversized so
  there is real weld overlap (≥3 mm of material past the hole
  envelope — *measure the envelope by slicing the mesh*, including
  countersink flare and any shaft tilt; the powerhead's Ø5.1 shafts
  were tilted ~8° and flared to Ø9.5, so Ø16 plugs).
- Flush plugs keep the wall face a single flat plane — that matters in
  step 6, because the wall face is also the build-plate face.
- Don't touch functional geometry (bearing surfaces, clearance slots).
  If a feature might be functional, it is — ask the operator.

## 3. Snap attachment

- Use the vendored QuackWorks directional snap:
  `libs/QuackWorks/openGrid/opengrid-snap.scad`. `libs/` is
  gitignored — run `bash scripts/vendor-libs.sh` first. Use
  `use <...>`, not `include <...>`: the file ends with a top-level
  demo call that would inject a stray snap into every render.
- **Licensing note is mandatory**: the snap library is
  **CC BY-NC-SA 4.0 (non-commercial)**. Carry the licensing block in
  the model header the way `ego_powerhead_mount.scad` and
  `ego_lb6500_blower_mount.scad` do.
- **Grid pitch is 28 mm.** Size the snap grid by load: a cantilevered
  tool holder started at 2×3 (six snaps) and grew to 2×4 when the
  plate expanded. Justify the count in the header.
- **Convention: the build-plate face is the snap face.** The flat
  face the part sits on when printed is the wall-facing face that
  carries the snaps. Snap tops are the first layers on the bed.

## 4. Orientation is operator input, not inference

The pst-ozs lesson, and the one correction cycle that was pure rework:
PR #13 *inferred* usage-up from the bearing faces (+Y, carefully
reasoned, documented) — and it was inverted. The operator's real-world
mounting orientation was −Y up. PR #15 rotated every snap 180°.

- **Ask which way is up in usage. Do not infer it from geometry.**
  If the bead doesn't state it, mail the operator before placing
  directional snaps.
- Record it as a model-frame axis ("usage-up is −Y"), in both the
  bead and the file header, with the provenance ("operator-stated",
  not "inferred").
- The **strong non-flexing nub points usage-up** (on the QuackWorks
  snap it's the 0.8 mm-deep, indicator-marked one; the flexy click-in
  side is 0.4 mm). The lever-out moment from a cantilevered load must
  bear on the rigid hook; the flexy side faces down, where the moment
  presses the plate into the wall.

## 5. Invariants sidecar

Every model ships `models/<stem>.invariants.py` (see
[AGENTS.md](../AGENTS.md)). For imported-STL conversions:

- **Orientation probes must be vertex-extent-based, never
  `mesh.contains()`.** Raycast point-containment 0.2 mm inside the
  nub tips is parity-flaky across environments: the welded snap shims
  leave tangent faces that double-count ray crossings, so CI read
  probe points as void while the identical points passed locally
  (pst-ozs). Instead, pin vertex extents in the snap-only z band —
  e.g. "the −Y edge of the bottom snap row reaches 13.2 mm (strong
  nub), the +Y edge of the top row stops at 12.8 mm (click nub)". See
  `_check_snap_orientation` in `ego_powerhead_mount.invariants.py`.
- **Fidelity via raycast comparison against the source mesh**: ray
  the export and the committed source STL on a jittered grid (jitter
  off round coordinates — trimesh's ray engine drops hits landing
  exactly on triangle edges) and assert the preserved bearing
  surfaces match within tolerance (≤0.5 mm on smooth points) and that
  no new material appears where the source has none. This is what
  makes a broken or wrong import unshippable.
- **Validate the probes by making them fail**: run the sidecar
  against a deliberately wrong artifact — the pre-fix STL, or a
  mirrored copy — and confirm it fails. PR #15's orientation probe
  was accepted only after it failed against the pre-rotation export.
  A probe that has never failed proves nothing.

## 6. Printability: supportless in the print orientation

Target: **zero slicer supports** with the snap face on the build
plate. Method from PR #21:

1. **Find the real overhangs with a slicer-style face scan** of the
   export: for every downward-facing triangle, measure its angle from
   vertical and its height above the bed. Threshold **~50° from
   vertical** for common FDM. Ignore faces on the bed, short bridges
   (a few mm), and the vendored snap's own sub-mm click-nub reliefs —
   openGrid prints in exactly this orientation by design.
2. **First tool: expand the back plate to whole 28 mm grid cells** so
   overhanging regions of the imported body start from plate material
   instead of mid-air. Align to whole cells only (the powerhead plate
   went 110 → 112 mm = exactly 4 cells, upgrading the snap grid to
   2×4 as a side benefit). Don't blindly cover everything — keep the
   plate sensible.
3. **Residual mid-air starts get breakaway ribs**: thin ribs welded
   at the bottom through a ~0.5 mm snap-off neck, stopping ~0.2 mm
   short of the ceiling they support so the first layer above bridges
   onto the rib tops. The body stays a single 2-manifold solid. Note
   "snap the ribs out before first use" in the catalog blurb.
4. Where an overhang is not functional surface, reshaping with 45°
   chamfers/gussets beats supporting it.
5. **Verify by re-running the face scan** and quantifying the worst
   remaining unsupported region (PR #21/#27 compared total >50°
   off-bed face area against a baseline). Add invariants probes for
   the printability guarantees: rib presence, open breakaway gaps (a
   fused rib can't be snapped out), maximum floating-rim reach.

## 7. Blending and edge finish

Extensions bolted onto a molded part *look* bolted on (pst-5kz). To
make new geometry read as part of the original:

- **Measure the roundover radius off the source edges** (the
  powerhead bracket carried r=2.0 on every convex edge) and expose it
  as a `@param` defaulting to the measured value.
- **Tangent-join new slabs**: start the new surface exactly where the
  source's own roundover ends so old and new rounding continue
  tangentially with no crease.
- **Struts/braces landing on new edges**: cut the new edge back to
  the strut's own face plane (45° on the powerhead) and flow through
  a tangent arc, so the brace lands over the new edge the way it
  landed over the old one.
- **Do not fillet breakaway features** — ribs snap out before first
  use; blending them in defeats witness-mark-free removal.
- Fillets must not regress step 6: keep every blend face ≤45° or
  upward-facing in print orientation, and re-run the face scan.
- **wasm CGAL trap** (PR #27): BOSL2 `cuboid(rounding=, edges=)`
  hulls eight corner shapes; degenerate corner pieces (e.g. rounding
  equal to half the slab depth) deterministically trip the wasm CGAL
  `convex_hull_3` assertion — caught only by the param sweep, and
  retries don't help. Build rounded slabs as an intersection of
  rounded-`rect()` extrusions instead: plain polygons, no hull.

## 8. Verification battery

Run all of these before opening the PR (CI runs them too, selectively —
see [docs/ci.md](ci.md)):

```bash
bash scripts/vendor-libs.sh                                # once per worktree
npm test                                                   # unit + catalog gates
npm run test:sweep -- tests/sweep/<stem>.test.ts           # wasm param sweep
python3 scripts/check-invariants.py <stem>                 # sidecar + built-ins
npx playwright test tests/e2e/stl-download.spec.ts         # download route
```

- The **download-route check** (from PR #13) exercises the real
  `POST /api/export` path: the artifact must be manifold, a single
  body, with the imported geometry present — an import()-asset e2e
  fixture pins the pipeline itself, and a model-specific bbox tell
  (e.g. full Z extent) catches a silently-dropped mesh.
- trimesh gotcha: `is_watertight` can read false on a
  Manifold-produced export because trimesh's load-time vertex merging
  drops zero-area zipper triangles. Check raw edge topology (every
  edge used by exactly 2 triangles) before believing it.
- **Regenerate renders for operator review** — but let CI's pinned
  engine commit the thumbnails (a local engine churns every model's
  PNGs byte-wise). Operator eyeballing of renders is what caught both
  the bolted-on look (pst-5kz) and drives sign-off.

## 9. Lifecycle

- Branch `gc-pilot/<bead-id>` from latest `origin/main`.
- PR to `main`; never push `main` directly.
- Auto-merge lands the PR on green with no human merge step, and
  open PR branches are auto-updated when `main` moves — see
  [docs/ci.md](ci.md) for the full PR lifecycle.
- Record the PR URL on the bead; expect operator corrections as
  follow-up beads rather than review comments (that's how this whole
  series ran).
