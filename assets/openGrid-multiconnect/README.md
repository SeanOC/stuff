# openGrid Multiconnect — vendored reference geometry

Official source CAD for the **openGrid Multiconnect** two-part mounting
system, delivered by the operator on 2026-08-17 (bead `pst-c73m`) and
vendored here so the geometry lives in-repo and nobody has to shuttle
files around again.

**These are reference assets, not OpenSCAD libraries.** They are not on
`OPENSCADPATH` and no model `include`s them. They exist to (a) preserve
provenance and (b) serve as the measured source for a possible future
native SCAD rebuild of the snap bodies. Do **not** treat them as a
build dependency.

## Provenance

- **Project:** openGrid (opengrid.world) Multiconnect.
- **Author:** `ddanier` — David D., the credited Multiconnect co-author —
  exported from **Shapr3D** (STEP via HOOPS Exchange 2024.8). The STEP
  `FILE_NAME` path (`/Users/ddanier/…`) and author field confirm first-party
  origin, not a third-party remix.
- **Export dates:** base `openGrid Multiconnect` + `Foldable` on
  2025-03-21 (Shapr3D 5.821); `Snap`, `Directional Snap`, `Directional
  Snap v2`, `BETA Lock Snap` on 2025-08-01 (Shapr3D 5.911).
- **Delivered by:** operator (Sean), 2026-08-17, into
  `city/incoming/mc-opengrid/`.
- Upstream publishes **no SCAD** for these parts; STEP/mesh is the only
  machine-readable source available.

## License — **CC BY 4.0** (operator-verified)

Redistribution notice for the vendored files (CC BY 4.0 §3(a)(1)). A copy of
this notice also lives beside the files as
[`NOTICE`](./NOTICE).

- **License:** Creative Commons Attribution 4.0 International (**CC BY 4.0**) —
  <https://creativecommons.org/licenses/by/4.0/>. Operator-verified: Sean read
  the source model pages directly on 2026-08-17 (openGrid Multiconnect on
  MakerWorld, models **1307474** and **1179191**). Republishing the STEP/3MF/STL
  in this public repo is permitted **with attribution**.
- **Author / project:** **David D (`ddanier`)** for the **openGrid project**.
- **Canonical source:** openGrid Multiconnect — <https://www.opengrid.world/projects/multiconnect/>
  (files published on MakerWorld models 1307474 / 1179191).
- **Attribution (required):** "openGrid Multiconnect by David D (ddanier),
  CC BY 4.0" — preserve it in this repo and in any derived work.
- **Modification status:** the committed `.step` and `.3mf`/`.stl` files are
  vendored **verbatim (unmodified)**, keeping their original filenames; only
  the `.shapr` editables and the bundle `.zip` were omitted (see below).
  Nothing in these files was altered.
- The `models/*.scad` in this repo are **CC BY-NC-SA 4.0**; a SCAD part
  *derived* from these CC-BY sources can ship under the repo's own terms so
  long as openGrid / `ddanier` attribution is carried through.

## What was vendored (and what was not)

Delivered set = 17 files + a bundle zip, in four formats per part
(`.step`, `.3mf`, `.stl`, `.shapr`). Vendored here:

- **`step/`** — ISO-10303-21 STEP (AP242), one per part (6 files). Open,
  measurable interchange format; the archival source of record.
- **`mesh/`** — print-ready meshes: `.3mf` where delivered (5 files) plus
  the Lock Snap `.stl` (it ships no `.3mf`). One mesh per part.

**Intentionally not committed** (kept in the operator's
`city/incoming/mc-opengrid/` stash; ask if you need them):

- **`.shapr`** — Shapr3D's proprietary editable source (~7 MB). Not
  usable in this repo's OpenSCAD/mesh toolchain; the STEP is the open
  equivalent for measurement and reference. Omitted for repo hygiene.
- **`MulticonnectforopenGrid.zip`** — redundant container of the same
  17 delivered files.

This trims the footprint from ~20 MB to ~3 MB while keeping a measurable
STEP and a printable mesh for every part. If the operator wants the
editable `.shapr` originals archived in-repo too, they can be added.

## Family matrix

| Part                         | step | mesh   | Footprint (mm)      | Height (mm) | Role                                                            |
|------------------------------|------|--------|---------------------|-------------|----------------------------------------------------------------|
| openGrid Multiconnect        | ✅   | .3mf   | 20.0 × 20.0 (round-tapered) | 10.8 | Screw-in **head/plug** — **external** M16 shank (screws into the snap bore) + presents the Multiconnect **male stud** |
| openGrid Multiconnect Snap   | ✅   | .3mf   | 25.6 × 25.6 (square) | 6.8        | Base **snap body** — clicks into openGrid lattice, threaded bore |
| … Directional Snap           | ✅   | .3mf   | 25.6 × 26.0 (square + key) | 6.8   | Snap body with a directional/anti-rotation key (+0.4 in Y)     |
| … Directional Snap v2        | ✅   | .3mf   | 25.6 × 26.0 (square + key) | 6.8   | Revised directional snap                                       |
| … Foldable Multiconnect      | ✅   | .3mf   | 22.0 × 20.0          | 10.0       | Foldable/hinged variant                                        |
| BETA … Lock Snap             | ✅   | .stl   | 25.8 × 25.8 (square) | 6.8        | BETA locking snap body (two-body: 25.8 frame + 22.8 inner)     |

## Measured constants

All figures **measured from the delivered STEP/mesh** (units = mm), not
quoted from a published spec. Cross-checked STEP `CYLINDRICAL_SURFACE`
radii against mesh cross-sections; treat as ±0.15 mm and verify against a
test print before committing SCAD to them.

### Center thread (snap bore ↔ head screw) — *internal joint only*

This thread is the **internal** joint that assembles the two-part snap: it
attaches the head/plug to the snap body, nothing else. It is **not** the
accessory-facing interface (that is the male stud measured below). The snap
body carries the internal thread; the head/plug carries the mating external
thread.

| Feature                    | Ø major | Ø minor | pitch    | notes                              |
|----------------------------|---------|---------|----------|------------------------------------|
| Snap internal (female)     | ~16.5   | ~14.5   | ~3.0     | root Ø ≈ 16.5, crest Ø ≈ 14.5      |
| Head external (male)       | ~16.0   | ~14.0   | ~3.0     | crest Ø ≈ 16.0, root Ø ≈ 14.0      |

- **Nominal:** an ~**M16 × 3.0** class thread (coarse, FDM-friendly),
  single-start, assumed right-hand. ~0.5 mm diametral clearance between
  male crest and female root gives the screw-fit.
- **Pitch** was recovered by autocorrelating bore radius vs. Z on the Snap
  mesh (median ≈ 3.0 mm, spread 2.5–3.3); it is **not** cleanly present in
  the STEP text (Shapr3D models the flanks as B-spline-swept surfaces, so
  there are no stacked circle entities to read a pitch from directly, and
  no OCC/CAD kernel is available in this environment). Confirm the 3.0 mm
  pitch on a print before relying on it.

### Snap body footprint

- Square snap body: **25.6 × 25.6 mm**, **6.8 mm** thick; base plate
  ~24.8 mm with a ~25.6 mm retention flange at z ≈ 4.2–4.8 (the ears that
  grab the openGrid lattice). Sized to one openGrid cell (28 mm lattice
  pitch) with clearance.
- Directional snap adds a **+0.4 mm** key in one axis (25.6 × 26.0).
- Lock Snap (BETA) is **25.8 × 25.8 × 6.8**, two-body.

### Accessory-facing male stud (the Multiconnect interface)

Once the head is screwed home, the shape it presents to an accessory is a
**tapered male stud** — a smooth Ø20 → Ø15 frustum, **not** a cap-on-neck.
Measured from the head mesh (`openGrid Multiconnect.3mf`) by **watertight
cross-section** — the outer Ø of the closed section outline at each depth Z
below the cap face (`trimesh.section`, so it reads the true cone surface, not
just mesh vertices):

| Z below cap face | outer Ø | feature                                                        |
|------------------|---------|----------------------------------------------------------------|
| 0.0 – 1.0 mm     | ~20.0   | flat cap face (with a central screwdriver-drive recess)        |
| 1.2 mm           | ~19.6   | cap edge starts to taper                                       |
| 1.5 mm           | ~19.0   | taper                                                          |
| 2.0 mm           | ~18.0   | taper                                                          |
| 2.5 mm           | ~17.0   | taper                                                          |
| 3.0 mm           | ~16.0   | taper                                                          |
| 3.5 mm           | ~15.0   | end of frustum → start of thread shank                        |
| 3.5 – ~9.6 mm    | Ø14–16  | **external** M16-class thread — screws INTO the snap bore, hidden after assembly |

There is **no narrow Ø7.5 neck** — an earlier reading took the Ø~7.5 *inner*
loop of the cap's drive recess (7.5 mm is its *radius*, ~Ø15) for an outer
neck. The exposed male profile is the Ø20→Ø15 frustum; below it the head
carries its **external** thread, which is swallowed by the snap body's
internal bore once assembled.

## Fit verification vs. our `mount_type=multiconnect` channel — they mate

Bead `pst-c73m` asked to confirm the "shared-standard compatibility" claim
with real numbers. **The numbers confirm it.** Our `mount_type=multiconnect`
builds the **female** Multiconnect slot; these openGrid snaps present the
matching **male** stud. They are two halves of the *same* Multiconnect
interface.

**The female slot is a throat-first undercut, not a countersink.** In pinned
`QuackWorks/Modules/multiconnectSlotDesign.scad` the profile
`[[0,0],[10.15,0],[10.15,1.2121],[7.65,3.712],[7.65,5],[0,5]]` is used two
ways: a `rotate_extrude` builds the **round loading pocket** (entered via the
on-ramp cone) and two mirrored `linear_extrude` calls sweep the same profile
into the **longitudinal channel** you slide along. What matters is how that
profile lands in the slab once `multiconnectBack()` places it: the slab
occupies `y ∈ [−6.5, 0]` (board face at `y = −6.5`), the slot tool is
translated `y = −2.35`, and the revolve axis ends up along `y`, so profile
depth `q` maps to `y = −2.35 − q`. **Measured directly** — a single-slot
`multiconnectBack(25, 40, 25)` exported (Manifold + CGAL) and cross-sectioned
through the pocket centre with `trimesh.section` — the cavity is:

| Depth from board face (`y = −6.5`) | cavity Ø | feature                          |
|------------------------------------|----------|----------------------------------|
| 0.00 mm (board face)               | **15.3** | **throat** — the narrow opening  |
| 0.00 – ~0.44 mm                    | 15.3     | throat land                      |
| ~0.44 → ~2.9 mm                    | 15.3 → 20.3 | flares open to the undercut   |
| ~2.9 – ~4.15 mm                    | **20.3** | **undercut pocket** (widest)     |
| ~4.15 mm                           | —        | blind end (2.35 mm of solid backing to the front face) |

So the board-facing opening is **Ø15.3**, widening to a **Ø20.3 undercut**
behind it and blind-ending at **~4.15 mm** — **not** a Ø20.3 mouth tapering to
Ø15.3 over 5 mm. (An earlier revision had this axis reversed.)

**How the stud engages.** It is **not** pushed straight through the throat —
the Ø20 cap will not pass a Ø15.3 hole. The stud enters where the **on-ramp**
cone (`r1 = 12 → r2 = 10.15`) locally opens the throat, then **slides along
the channel**; the **Ø20 cap is captured in the Ø20.3 undercut behind the
Ø15.3 throat**, and the v2 snap detent seats it. This is a keyhole/undercut
slide-fit — the same family as our own slot, and the mechanism that makes the
two systems interoperate.

**Co-located clearances** (male feature vs the female feature it actually
rides in, once seated):

| Female feature        | female Ø | mating male feature      | male Ø | diametral clearance |
|-----------------------|----------|--------------------------|--------|---------------------|
| throat                | 15.3     | Ø15 stem (frustum small end / behind cap) | ~15.0 | ~0.3 mm |
| undercut pocket       | 20.3     | Ø20 cap                  | ~20.0  | ~0.3 mm             |
| flare (throat→pocket) | 15.3→20.3 over ~2.5 mm | Ø20→Ø15 frustum (complementary sense) | ~2.5 mm band | slip |

The Ø15 stem clears the Ø15.3 throat (~0.3 mm) and the Ø20 cap is retained in
the Ø20.3 pocket (~0.3 mm), with the male Ø20→Ø15 frustum and the female
Ø15.3→Ø20.3 flare complementary across the ~2.5 mm taper. **Assembled axial
seating** (how deep the cap sits, exactly where the detent bites — the pocket
is only ~4.15 mm deep) is **not** proven on paper: measurements are ±0.15 mm,
so **verify fit on a test print** before relying on the joint.

This still corrects the original "different systems" read (it mistook the
head's internal assembly thread for the accessory interface); the systems do
share the Multiconnect male/female interface.

**The real, documented limitation is pitch, not profile:**

- One openGrid cell = **28 mm**; the Multiboard slot default
  (`distanceBetweenSlots`) = **25 mm**. A **single** stud mates with a single
  slot regardless.
- To engage **multiple** openGrid studs at once (snaps in adjacent cells,
  28 mm apart), build the accessory back at `distanceBetweenSlots = 28`
  instead of the 25 mm default, so slot spacing matches the openGrid lattice.

Directional and Lock Snap variants add anti-rotation keys but present the
same male stud, so the fit conclusion is unchanged.

**This is documentation only** — per the bead, existing Multiboard
connectors are not relabeled and nothing is rebuilt in SCAD here. It bears
on `pst-d3c3` (the apple_tv MC backer): the two systems **do** interoperate
on a single stud, which supports keeping the `mount_type=multiconnect`
target as-is. Re the mayor's source-ambiguity note (`ci-wisp-u8lc7o3`):
openGrid Multiconnect and Multiboard Multiconnect share the male/female
**stud profile**; they differ in **native board pitch** (28 mm vs 25 mm) and
in how the snap attaches to its board (openGrid lattice clip + screw vs
Multiboard slot). Naming a single "correct" system is still an operator call,
but on geometry they are cross-compatible per connector.

## Measurement method (reproducible)

Scripts used (trimesh + stdlib only; no CAD kernel required) are described
inline in the PR for `pst-c73m`. Summary:

- STEP bounding boxes + thread radii: regex over `CARTESIAN_POINT`,
  `CIRCLE`, `CYLINDRICAL_SURFACE` entities.
- Print-body footprints: parse `.3mf` (zip + `3dmodel.model` XML) → trimesh
  → `split()` connected components → per-body bbox.
- Stud / thread cross-sections: parse `.3mf` (zip + `3dmodel.model` XML) for
  vertices **and** triangles → build a `trimesh.Trimesh` → `mesh.section()` at
  each depth Z, and take the outer Ø from the closed section outline (not
  per-vertex radii — a vertex sweep under-samples a smooth cone between mesh
  rows and can misread an inner recess as an outer neck). Thread pitch by
  autocorrelating bore radius vs. Z.
