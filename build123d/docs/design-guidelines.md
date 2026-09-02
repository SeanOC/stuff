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

## 6. Reviewer checklist (stuff-codex-reviewer)

For any PR touching `build123d/holders/**`, check and cite the file/line:

1. Declared print orientation present; no downward face steeper than 45°
   without a stated reason; no bridge > 10 mm.
2. No downward-facing fillets; plate-contact edges chamfered.
3. Walls ≥ 0.9 mm (≥ 1.6 mm load-bearing); features ≥ 1.8 mm; holes ≥ Ø2.
4. User-exposed non-functional edges treated (fillet/chamfer); functional
   edges untouched; library cutters untouched.
5. Features sized to their own envelope; `part.volume` before/after reported
   per preset; increases justified.
6. Body joints blended (fillet/gusset/web, overlap ≥ wall); load path along
   layers stated.
7. Mount tunables exposed per §5; spec constants unchanged; presets cover
   light→robust; mount contracts (`tests/mount_contracts.py`) still pass.
8. Load direction + material (PLA and PCTG) sanity sentence in the PR.

A miss on 1–3 or 7 is blocking; 4–6 and 8 are blocking when the PR claims
to address them and otherwise a required follow-up bead.

---

Sources for the numbers: [Hydra Research design rules](https://www.hydraresearch3d.com/design-rules),
[UltiMaker design for FFF](https://ultimaker.com/learn/design-for-fff-3d-printing-maximize-your-success/),
[Layer X FDM design rules](https://layerx3d.in/blog/fdm-design-rules-wall-thickness-overhangs-bridging-tolerances),
[Bambu Lab wiki: warping](https://wiki.bambulab.com/en/knowledge-sharing/printed-model-warping),
[Bambu Lab wiki: PETG guide](https://wiki.bambulab.com/en/filament/petg) (PCTG is a PETG-family copolyester),
[Bambu Lab H2S specs](https://us.store.bambulab.com/products/h2s).
