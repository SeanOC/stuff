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

- **CC BY 4.0.** Operator-verified: Sean read the MakerWorld model pages
  directly on 2026-08-17 (models **1307474** and **1179191**). Republishing
  the STEP/3MF/STL in this public repo is permitted **with attribution** —
  this resolves the earlier vendoring/republish question.
- **Attribution (required):** the **openGrid project** / **David D
  (`ddanier`)**. Preserve it in this repo and in any derived work.
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
| openGrid Multiconnect        | ✅   | .3mf   | 20.0 × 20.0 (round-tapered) | 10.8 | Screw-in **head/plug** — internal M16 shank + presents the Multiconnect **male stud** |
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

Once the head is screwed into the snap, the part it presents to an
accessory is **not** the thread — it is a **rotationally-symmetric male
stud**: a Ø ~20 mm cap ~1.2 mm thick sitting on a Ø ~7.5 mm neck. Measured
from the head mesh (`openGrid Multiconnect.3mf`, radial envelope by Z):

| Z from cap face | outer Ø | feature                                            |
|-----------------|---------|----------------------------------------------------|
| 0.0 – 1.2 mm    | ~20.0   | cap disc (the retained head)                       |
| 1.2 – 3.0 mm    | ~11 → 7.5 | neck taper down to the stem                       |
| 3.0 – 9.0 mm    | ~16 / 15 | M16 thread shank — screws **into the snap**, hidden |

The exposed cap-on-neck is the Multiconnect **male** profile; the thread
below it is internal (see above).

## Fit verification vs. our `mount_type=multiconnect` channel — they mate

Bead `pst-c73m` asked to confirm the "shared-standard compatibility" claim
with real numbers. **The numbers confirm it.** Our `mount_type=multiconnect`
builds the **female** Multiconnect slot; these openGrid snaps present the
matching **male** stud. They are two halves of the *same* Multiconnect
interface.

Our slot is `rotate_extrude`d from the profile
`[[0,0],[10.15,0],[10.15,1.2121],[7.65,3.712],[7.65,5],[0,5]]` in
`multiconnectSlotDesign.scad` — i.e. a rotationally-symmetric cavity, **not**
a linear dovetail. Direct clearance comparison (male head vs female slot):

| Feature                | openGrid male stud | our female slot | clearance / note                     |
|------------------------|--------------------|-----------------|--------------------------------------|
| Cap / mouth Ø          | ~20.0 mm           | 20.3 mm (r 10.15) | 0.3 mm — cap seats in the mouth pocket |
| Cap / mouth seat depth | ~1.2 mm            | 1.2121 mm       | ≈ exact — near-identical seat height |
| Neck Ø vs throat Ø     | ~7.5 mm neck       | 15.3 mm waist (r 7.65) | neck clears the throat freely  |
| Retention             | Ø20 cap > Ø15.3 throat | v2 snap + on-ramp | cap is captured behind the throat |

The cap Ø and its 1.2 mm seat depth match the slot mouth (20.3 mm, 1.2121 mm)
almost exactly; the Ø7.5 neck passes through the Ø15.3 throat while the Ø20
cap is retained behind it. This is a textbook Multiconnect male/female
engagement, and it corrects the earlier read that these were "different
systems" — the earlier conclusion mistook the internal assembly thread for
the accessory interface, and assumed a rotationally-symmetric stud could not
be Multiconnect (our own slot is itself rotationally symmetric).

**The real, documented limitation is pitch, not profile:**

- One openGrid cell = **28 mm**; the Multiboard slot default
  (`distanceBetweenSlots`) = **25 mm**. A **single** stud mates with a single
  slot regardless.
- To engage **multiple** openGrid studs at once (snaps in adjacent cells,
  28 mm apart), build the accessory back at `distanceBetweenSlots = 28`
  instead of the 25 mm default, so slot spacing matches the openGrid lattice.
- Tolerance: cap Ø20.0 vs mouth Ø20.3 gives ~0.3 mm nominal clearance;
  measurements are ±0.15 mm — **verify fit on a test print** before relying
  on them, and note the v2 retention snap engages the neck.

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
- Stud / thread cross-sections: `trimesh.section()` sweeps along each
  axis; thread pitch by autocorrelating bore radius vs. Z.
