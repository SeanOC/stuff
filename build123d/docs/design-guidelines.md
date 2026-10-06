# build123d model design guidelines

Operator guidance (Sean, 2026-09-02) for every parametric model in `build123d/`
— what the **worker** must design to and what the **reviewer** must check.
Born from test-printing the C-ring holder (v1–v4): the geometry was correct
but the plate was oversized, edges were hard, the cup-to-plate joint was an
obvious stress point, and the mount had no tunables. These rules are the
default; deviate only with a stated functional reason in the PR.

Target printer and materials: **Bambu Lab H2S** (0.4 mm nozzle, 0.2 mm
layers by default, 340×320×340 mm, 65 °C chamber) printing **PLA** or
**PCTG**. Models must print on that machine **without supports** in the
declared orientation, in either material.

---

## 1. Printability (design for FDM)

Design the part around its print orientation; state that orientation in the
model header and assert it in tests (the mount contracts already do this for
the slot aperture).

**Overhangs and bridges**
- Any downward-facing surface steeper than **45° from vertical** needs a
  reason. 45° is the safe limit for both PLA and PCTG; PLA tolerates a little
  more, PCTG less (it sags and strings when pushed).
- Unsupported bridges: keep under **10 mm**. Longer spans get a 45° chamfered
  ceiling or a split into shorter spans.
- Horizontal holes and slots print as sagging ovals: use a teardrop / 45°
  peak, or the offset-layer trick, when the fit matters. Vertical (Z-axis)
  holes are the default choice.
- **No downward-facing fillets.** A fillet on a bottom edge is a shallow
  overhang that prints as a rough curl. Use a **45° chamfer** on any edge
  that faces the build plate or the ceiling of a pocket; fillets go on top
  and vertical edges only. (Library mount cutters are excluded: their profile
  is the spec.)

Multibuild exception (Sean, 2026-09-28): Multiconnect slot pockets may require
supports when printed standing; this does not waive bed-edge chamfers.

**Walls, features, holes**
- Minimum wall: **0.9 mm** (two extrusion widths); use **≥ 1.6 mm** for
  anything load-bearing and **≥ 2.4 mm** for a mount plate backing.
- Minimum standalone feature / pin: **1.8 mm** (four extrusion widths).
- Minimum modelled hole: **Ø2 mm**. Clearance for a mating printed part:
  **0.2 mm loose / 0.1 mm tight** per side. Model exact spec dimensions for
  standards (openGrid / Multiconnect) and let the library clearances stand.

**First layer and the plate-contact face**
- Every edge that touches the build plate gets a **0.3–0.5 mm 45° chamfer**
  (elephant-foot relief) so the part sits flat and mates cleanly.
- Broad flat contact faces warp less with rounded corners (**R ≥ 4 mm**) than
  with sharp ones.

**Strength and orientation**
- Layer adhesion is the weakest direction: a load that pulls layers apart
  (tension along Z, or bending across layer lines) is the failure mode. Route
  loads **along** layers: a hook, lip, or mount plate should be printed so the
  load runs parallel to the plate face, not through the layer stack.
- PLA is stiff and brittle and creeps under sustained load or heat (a sunny
  window, a car): avoid thin snap features that flex repeatedly. PCTG is
  tougher and slightly flexible with excellent layer adhesion, but overhangs,
  bridges and small details are worse than PLA and it strings — design so the
  PCTG print is the one you check overhangs against.
- Print the part in the orientation the load wants, then design the
  overhangs away; do not accept supports to rescue a bad orientation.

**Print time and reliability**
- Fewer perimeters of solid slab beat thick walls; ribs and gussets beat
  bulk. Avoid tiny islands on the first layer and long thin spikes.

## 2. Edge treatment

Every edge a user can see or touch that has **no functional reason to be
sharp** gets a fillet or chamfer. Functional edges stay sharp: mount-face
datums, slot walls, snap notches, mating surfaces, anything a spec defines.

- Vertical outer edges: fillet **R 1–2 mm** (or ≥ half the wall for thin
  walls).
- Top edges and rims (upward-facing): fillet **R ≥ 1 mm**; a cup lip that a
  hand meets gets a full round (R = wall/2).
- Bottom / plate-contact edges and pocket ceilings: **45° chamfer**, never a
  fillet (see §1).
- Inside corners where two bodies meet: fillet **R ≥ 1 mm** — this is a
  stress relief, not cosmetics (see §4).
- Apply edge treatment as the **last** step on the fused part, selected by
  geometry (face normals / positions), never on library cutters. If a fillet
  fails in OCP, fall back to a chamfer and say so in the PR rather than
  shipping a hard edge.

## 3. Material efficiency

Size each feature to **its own** requirement plus margin, not to its
neighbour's size.

- A mount plate is the **mount envelope + margin**, not the width or height
  of the thing it carries. For a Multiconnect slot plate: slot envelope
  (`_min_plate_width(n)` × `MIN_PLATE_HEIGHT`) + 3 mm margins, centred; the
  cup does not stretch the plate.
- Prefer ribs, webs and gussets over thick slabs; prefer a shell with a
  floor over a solid.
- Every PR that touches geometry reports **`part.volume` before/after** for
  each preset (the toolchain already computes it — see the manifest bake) and
  a one-line justification for any increase.
- Keep print-time proxies honest: fewer, larger features print faster than
  many small ones; avoid geometry that forces a raft or brim.

## 4. Structural integration

Two bodies fused at a plane make a stress concentrator and look bolted on.

- Blend bodies with a **fillet at the junction (R ≥ 1 mm, ideally ≥ wall)**
  and, where a load bends across the joint, **gussets or a tangent web** so
  the section grows toward the joint. Overlap ≥ one wall thickness — never a
  tangent contact.
- Put the joint's load path **along layers** (§1). For a wall-hung holder,
  the cup's weight pulls the plate away from the cup: the web between them
  should run vertically and be continuous with both.
- State the worst-case load direction in the model header and check the
  joint against it in the PR text (a sentence, not FEA).

## 5. Parametrics for mounts

Expose what changes the **robustness** of a mount; never expose what the
spec fixes.

- Multiconnect / openGrid: slot **count**, slot **travel/length** (entry
  travel before the seat), optional **snap notches**, plate **margin** are
  tunables. The **28 mm pitch, head/slot profile, and clearances are spec**
  and stay constants from the library.
- Derive the plate from the mount params, validate ranges (a plate must
  always host the full slot envelope + margin), and ship presets covering
  "light" (one slot, short travel) to "robust" (two/three slots, full travel).
- New params mirror the existing `Param` contract (`holders/registry.py`)
  so the web UI and `/api/bd-render` pick them up unchanged.

For Multibuild mounts, use the [multibuild library](multibuild-library.md):
board pitch is fixed at 25 mm, with the pinned Multiconnect head/profile and
clearances unchanged and a flush back-face datum.

## 6. Reviewer checklist (stuff-codex-reviewer)

For any PR touching `build123d/holders/**`, check and cite the file/line:

1. Declared print orientation present; no downward face steeper than 45°
   without a stated reason; no bridge > 10 mm. Cite the UNDERSIDE review tile.
2. No downward-facing fillets; plate-contact edges chamfered.
3. Walls ≥ 0.9 mm (≥ 1.6 mm load-bearing); features ≥ 1.8 mm; holes ≥ Ø2
   — verified by the production print audit AND the exposed-edge classifier
   at EVERY numeric Param endpoint and every documented corner (max
   clearance, min/max width, both angle limits); the worker pastes that
   table into the PR body before opening the PR, and the reviewer re-runs
   any cell it doubts. The audit machine-checks only the 0.9 mm whole-part
   wall floor (`tests/print_audit.py` `MIN_WALL_MM`; the 1.6 mm load-bearing
   floor is deferred there), and the edge classifier is per-model (e.g.
   `assert_finished_edges` in `tests/test_spool_cradle.py`) — name the seam
   used in the table; feature ≥ 1.8 mm and hole ≥ Ø2 stay manual checks
   evidenced by the table.
4. User-exposed non-functional edges treated (fillet/chamfer); functional
   edges untouched; library cutters untouched.
5. Features sized to their own envelope; `part.volume` before/after reported
   per preset; increases justified.
6. Body joints blended (fillet/gusset/web, overlap ≥ wall); load path along
   layers stated.
7. Mount tunables exposed per §5; spec constants unchanged; presets cover
   light→robust; mount contracts (`tests/mount_contracts.py`) still pass.
8. Load direction + material (PLA and PCTG) sanity sentence in the PR.
9. For a port: every exception row cites the reference measurement (file,
   ray/point, value) and names its face family; an exception without a
   reference measurement is blocking. Apply §8 to published geometry.

A miss on 1–3, 7 or 9 is blocking; 4–6 and 8 are blocking when the PR claims
to address them and otherwise a required follow-up bead.
A PR without the endpoint/corner audit table is a blocking omission like a
missing `part.volume`.

## 7. Provenance

Provenance is tracked for every dimension and every committed external
geometry. Tag each interface dimension (in code *and* docs) with one of:

- **[V] — measured.** Measured from an official file (with the measurement
  artefact cited) or from a physical print. For a file, `source` is its
  `source_file_id` in `reference/source-manifest.json`. `locator` is the
  committed measurement under `reference/measured/`. That artefact's
  manifest entry pins the exact file version, `(source_file_id,
  source_sha256)`. Arithmetic on cited numbers is **not** [V]; it inherits
  the tag of its inputs.
- **[C] — cited.** A claim from documentation, a drawing, or another
  project's source. It is cited with a source key and line/section locator
  (`docs/multibuild-research.md`).
- **[U] — unresolved.** Nobody has established it yet. Say what evidence would
  resolve it.

When a measurement disagrees with a cited value that a model depends on, do
not change the value silently. It stays [C], and the code carries a
`# measured <value>` comment and a follow-up bead. The delta is recorded in
the research tables.

**Licences.** Multiboard/MultiBuild-licensed files may be used directly for
non-commercial purposes (Sean 2026-09-29). Their licence (revocable,
non-commercial, remixes under the same terms, attribution) is copied next to
the artefact. Multiconnect connector STEPs are CC BY-NC-SA and modelling files
are CC BY 4.0. openGrid is CC BY 4.0 and Gridfinity is MIT.

**Upstream originals are never committed.** They live in the private mirror
(`reference/FETCH.md`). What is committed is our measured output (JSON plus
DXF/SVG sections, made with `tools/measure_step.py --record`) and geometry
regenerated from measured values (`multibuild/tile.py`, carved out of the
repository's MIT licence). See [provenance.md](provenance.md) for the licence
table, the committed artefacts and the measure/record workflow.

## 8. Published-geometry ports

The rules above remain the default. A port may preserve published geometry
only through a pre-declared, reference-verified exception inventory. A
licence or a passing parity test alone grants no geometric exception. See
the [porting recipe](porting.md) and the separate
[vendoring grant check](provenance.md#vendored-source-grant-check).
The precedents below were checked against main `a5bdcb1`.

### What may yield, and its required pin

| Rule | Scoped published exception | Pin required |
| --- | --- | --- |
| Wall floor | An inventoried mating face family may retain the author's thinner wall. | Exact face membership and reference wall measurements; e.g. the directional snap's **23 lite / 26 full faces** in [DIRECTIONAL_FACES](../tests/opengrid_snap_inventory.py), checked by `test_published_print_inventory` and `test_directional_reference_features` in [test_opengrid_snap.py](../tests/test_opengrid_snap.py). |
| Mount backing depth | A named shallow contract may retain published backing. | `openconnect-slot-shallow` in [mount_contracts.py](../tests/mount_contracts.py) pins **0.8 mm**; the shelf's published **0.85 mm** and sturdy-back **2.4 mm** are checked by `test_published_backing_is_point_85_and_sturdy_is_2_point_4` and `test_endpoint_audit_mount_and_edges` in [test_gridfinity_shelf.py](../tests/test_gridfinity_shelf.py). Keep the full-depth proof on that preset. |
| Edge treatment | Functional/mating edges (Gridfinity profile boundaries, mount faces) and explicitly inventoried author exterior edges may stay sharp. | A geometric edge inventory such as [gridfinity_shelf_edges.json](../tests/gridfinity_shelf_edges.json), checked by `edge_inventory` and `test_endpoint_audit_mount_and_edges`; no blanket waiver of all edges on a port. |
| Parameter-driven thin walls | A published family may thin across its declared domain. | Pins at **both endpoints and the midpoint**, plus rejection of misses outside the inventory. The shelf's ten-face socket-wall family (two back lower tapers, six straight and two corner upper tapers) is selected by socket/exterior adjacency; `test_rev14_published_socket_wall_thickness` pins clearance **0 / 0.1 / 0.2 mm**, and `test_rev14_no_other_thin_faces_at_max_clearance` checks the remainder. Counts describe the tested default grid, not every grid size. |

Published mating overhangs retain their measured angle and local bridge
span, as in the snap's [directional inventory](opengrid-snap-library.md#directional-mating-exceptions)
and `test_published_print_inventory`. This is a scoped reason under §1,
not a global relaxation of the holder angle limit.
The cartridge holder's source figure-pocket domes likewise retain only
their approved cylindrical-surface inventory (`audit_exclusions` in
[cartridge_holder.py](../holders/cartridge_holder.py), checked by
`test_exceptions_are_narrow_and_dense_bridge_is_short` and
`test_source_pocket_fit` in [test_cartridge_holder.py](../tests/test_cartridge_holder.py)).
A published functional dome is not permission to add downward edge fillets:
the raw audit reports that curved face, and the exact source-surface
exclusion must still reject a new overhang outside it.

### How exceptions are pinned

Measure the **unmodified author source at the NOTICE pin**, rendered with
the recorded engine, library pins and parameters. Record any existing
compatibility patch separately (the snap NOTICE records its line-neutral
patch); never modify reference geometry to make the port pass. Each row
names the source file/lines, reference mesh, ray or sample point and
direction, measured value, face family, parameter cases and enforcing test.

Select faces by **adjacency and their geometric family**, never by thickness
or by collecting only the faces where the audit happened to fail. Geometric
locators must identify the whole family independently of the measured miss.
Pins are self-policing: an extra miss outside the inventory fails; a missing
inventoried face or a drifted value fails. The openConnect plate's exact
ramp-end strips follow the same rule: `test_only_exact_edge_ramp_strips_are_excluded`
in [test_openconnect_plate.py](../tests/test_openconnect_plate.py) pins their
count, volume and bounds without an enlarged exclusion box.

### What never yields

- **Bed-contact chamfers, no downward fillets, and manifold port output**
  remain required under §§1–2 (including the existing library-cutter
  distinction). A non-manifold author mesh is reference evidence, not an
  excuse for a non-manifold port: see `test_single_watertight_solid` and
  `test_published_print_inventory` in [test_opengrid_snap.py](../tests/test_opengrid_snap.py),
  and `test_endpoint_audit_mount_and_edges` in [test_gridfinity_shelf.py](../tests/test_gridfinity_shelf.py).
- **No bridge above 10 mm without a measured span.** A published ceiling's
  face width or angle is not a span measurement or a waiver. Keep the
  production local-bridge measurement in the inventory; the snap's pinned
  ceilings remain below `MAX_BRIDGE_MM` in [print_audit.py](../tests/print_audit.py).
  A measured span above that limit still needs the §1 redesign.
- **Parity caps stay 0.05 mm bbox / 1% volume / 0.15 mm surface**, pinned in
  `test_mesh_parity` above and the shelf's `test_reference_parity`. For
  mandatory bed treatment, compare bbox on the pre-treatment solid and
  separately assert the finished solid's analytic reduction. For the shelf,
  the depth reduction is `0.3*t/(1+t)`, where
  `t = tan(print_bottom_angle) * tan(45.01°)`; width and height stay fixed.
  Surface-band exclusions remove only **over-cap samples** inside a band
  computed on the **reference**. Report and cap both total band coverage and
  excluded fraction: the shelf pins a **0.5 mm** band, **6%** coverage and
  **2%** excluded samples in `reference_bed_band`,
  `test_rev10_reference_bed_band_coverage` and `test_reference_parity`.
  The snap's separate internal-contact-surface exclusion is pinned in
  `test_mesh_parity`; it does not exclude exterior surface errors.
- **Backing must test material that ought to exist.** The probe is
  **unbounded by default** (`verify_openconnect_slot` in
  [mount_contracts.py](../tests/mount_contracts.py)). An explicit
  `backing_envelope` clips it to the model's **uncut body**, before mount or
  clearance cuts, minus mandatory edge-treatment volume. Any narrower
  envelope must be declared and recorded in the exception inventory. The
  worked precedent is `backing_envelope` in
  [gridfinity_shelf.py](../holders/gridfinity_shelf.py): uncut wedge minus
  the actual bed bevel. `test_rev11_backing_envelope` proves that the only
  removed probe volume is below the wedge or in the bevel, keeping sockets,
  windows, magnets and screws inside the checked region. **Never derive the
  envelope from the finished part**: then the missing-volume test becomes
  identically zero and cannot detect missing backing.

### Parameter domains

Every numeric endpoint and documented corner has one of three outcomes:
passes the ordinary contracts; raises a **named `ValueError` for unbuildable
geometry**; or passes a **pre-declared published exception**. An audit miss
on buildable published geometry must never become a `ValueError`. The
author's saturation value is the endpoint, not an invented cutoff before a
thin wall appears. The shelf pins **0.2 mm** socket-clearance saturation in
`test_socket_stack_and_clearance_saturation`; its endpoint audit accepts
only the named horizontal/vertical slot-offset errors for impossible
placements. These are the test seams in [test_gridfinity_shelf.py](../tests/test_gridfinity_shelf.py).

---

Sources for the numbers: [Hydra Research design rules](https://www.hydraresearch3d.com/design-rules),
[UltiMaker design for FFF](https://ultimaker.com/learn/design-for-fff-3d-printing-maximize-your-success/),
[Layer X FDM design rules](https://layerx3d.in/blog/fdm-design-rules-wall-thickness-overhangs-bridging-tolerances),
[Bambu Lab wiki: warping](https://wiki.bambulab.com/en/knowledge-sharing/printed-model-warping),
[Bambu Lab wiki: PETG guide](https://wiki.bambulab.com/en/filament/petg) (PCTG is a PETG-family copolyester),
[Bambu Lab H2S specs](https://us.store.bambulab.com/products/h2s).
