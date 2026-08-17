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

## License — **TBV (to be verified)**

- openGrid's documentation repo (`openGrid-docs`) states **CC BY 4.0**,
  but the **per-model MakerWorld license for these specific snap parts is
  UNVERIFIED**. Treat as **TBV** until the operator confirms the exact
  publication terms.
- The `models/*.scad` in this repo are **CC BY-NC-SA 4.0** regardless, so
  any derived SCAD would inherit the non-commercial restriction anyway.
- Attribution to `ddanier` / the openGrid project must be preserved in any
  derived work.

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
| openGrid Multiconnect        | ✅   | .3mf   | 20.0 × 20.0 (round-tapered) | 10.8 | Screw-in **head/plug** — male thread + slotted grip dome       |
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

### Center thread (snap bore ↔ head screw)

The snap body carries an **internal** thread; the head/plug carries the
mating **external** thread.

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

## Fit verification vs. our `mount_type=multiconnect` channel — ⚠️ DIFFERENT INTERFACES

Bead `pst-c73m` asked to confirm the "shared-standard compatibility" claim
with real numbers. **The numbers do not support it.** These openGrid parts
and our Multiboard-derived channel are **mechanically different systems:**

| | openGrid Multiconnect (this pack) | Multiboard Multiconnect (`libs/QuackWorks/Modules/multiconnectSlotDesign.scad`, our `mount_type=multiconnect`) |
|---|---|---|
| Interface     | **Screw thread**, ~M16 × 3.0        | **Dovetail slot**                                    |
| Female profile| Threaded bore Ø ~16.5               | Dovetail: mouth 20.3 mm → waist 15.3 mm, 5 mm deep   |
| Male profile  | Threaded dome/plug Ø ~16.0          | Dovetail stud, 25 mm slot pitch                      |
| Engagement    | Rotate to screw in                  | Slide along the 25 mm slot axis                      |

A part built for one **will not mount** to the other: there is no dovetail
anywhere in these openGrid files (every cross-section of the head is
rotationally symmetric — a threaded knob, not a slide-in stud), and our
`multiconnectSlotDesign` has no thread. The "Multiconnect accessory
channel = shared standard" premise recorded in the bead is **not borne out
by the delivered geometry.**

This matches the mayor's standing source-ambiguity note
(`ci-wisp-u8lc7o3`): openGrid Multiconnect (threaded) is a genuinely
different profile from Multiboard Multiconnect (dovetail). **This finding
is documentation only** — per the bead, existing Multiboard connectors are
not to be relabeled and nothing is rebuilt in SCAD here. It is flagged for
the operator because it bears directly on `pst-d3c3` (the apple_tv MC
backer) and on whether our `mount_type=multiconnect` targets the intended
system.

## Measurement method (reproducible)

Scripts used (trimesh + stdlib only; no CAD kernel required) are described
inline in the PR for `pst-c73m`. Summary:

- STEP bounding boxes + thread radii: regex over `CARTESIAN_POINT`,
  `CIRCLE`, `CYLINDRICAL_SURFACE` entities.
- Print-body footprints: parse `.3mf` (zip + `3dmodel.model` XML) → trimesh
  → `split()` connected components → per-body bbox.
- Dovetail/thread cross-sections: `trimesh.section()` sweeps along each
  axis; thread pitch by autocorrelating bore radius vs. Z.
