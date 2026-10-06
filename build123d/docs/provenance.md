# Provenance and licences for external geometry

Rule: [design-guidelines §7](design-guidelines.md#7-provenance). **[V]** means
measured from an official file (artefact cited) or a physical print. **[C]**
means cited, and **[U]** means unresolved. Upstream originals are **never
committed**. They live in the private mirror (see
[`reference/FETCH.md`](../reference/FETCH.md)).

## Licences

| System / files | Licence | Use here | Text |
| --- | --- | --- | --- |
| MultiBuild / Multiboard remixing files (tiles, threads, snaps, Fix-Points) | Multiboard Licence, 2025-12-19. Revocable and non-commercial; remixes carry the same terms; attribution; **no redistribution of originals** | Sean 2026-09-29: may be used directly for non-commercial purposes. We commit measurements and a regenerated tile, never the files | [Multiboard-Licence-2025-12-19.txt](../reference/LICENSES/Multiboard-Licence-2025-12-19.txt) (retrieved 2026-09-29 from the [full licence](https://docs.google.com/document/d/1C0-Iyxydqk_d2I3o_5ualJ9Ywt9gwVdl9eukvC8JeKA/export?format=txt); [licence page](https://multibuild.io/license)) |
| Multiconnect v2 modelling files ([Printables 1008622](https://www.printables.com/model/1008622)) | CC BY 4.0 | measured; attribution: David D | [CC-BY-4.0.txt](../reference/LICENSES/CC-BY-4.0.txt) |
| Multiconnect connector STEPs ([716558](https://www.printables.com/model/716558), [1160115](https://www.printables.com/model/1160115), [1024741](https://www.printables.com/model/1024741)) | CC BY-NC-SA 4.0 | mirrored, not measured yet | [CC-BY-NC-SA-4.0.txt](../reference/LICENSES/CC-BY-NC-SA-4.0.txt) |
| openGrid | CC BY 4.0 | via the MIT `opengrid` Python library; David D's Multiconnect snap files are vendored verbatim in `assets/openGrid-multiconnect/` | [CC-BY-4.0.txt](../reference/LICENSES/CC-BY-4.0.txt) |
| openConnect ([mitufy/opengrid-projects](https://github.com/mitufy/opengrid-projects) @ `04e2277a71c5`) | CC BY 4.0 | four author `.scad` files vendored verbatim plus two renders in `assets/openConnect/` (attribution: mitufy). **HARD-RULE exception (Sean 2026-10-01):** `openconnect/` is ported from the author's own OpenSCAD because no build123d library ships it; the port is pinned by commit and mesh-verified against the author's rendered plate (`tests/test_openconnect.py`). Constants are [C] with line locators; see [openconnect-library.md](openconnect-library.md) | [CC-BY-4.0.txt](../reference/LICENSES/CC-BY-4.0.txt) |
| openGrid positive snap / `opengrid_snap/` ([QuackWorks](https://github.com/AndyLevesque/QuackWorks/blob/6123129/openGrid/opengrid-snap.scad) `6123129`, `openGrid/opengrid-snap.scad` + local patch `0001-opengrid-snap-linear-extrude-click-holes.patch`) | CC BY-NC-SA 4.0; design David D, OpenSCAD metasyntactic | **HARD-RULE exception (Sean 2026-10-05):** ported because no build123d library ships the positive snap; pinned by commit; verified against committed reference meshes (`assets/opengrid-snap/`, no QuackWorks source committed) | [CC-BY-NC-SA-4.0.txt](../reference/LICENSES/CC-BY-NC-SA-4.0.txt) |
| Gridfinity profile | MIT-derived constants | `gridfinity/baseplate.py`, cited from the shelf source :291–311, :1263–1340 | see shelf NOTICE |
| openConnect Gridfinity shelf (mitufy, MakerWorld 3055852, profile 3438217) | CC BY-SA 4.0 | Original SCAD and reference meshes in root `assets/openConnect-gridfinity-shelf/`; Python adaptation in `holders/gridfinity_shelf.py` and `gridfinity/baseplate.py`. Explicit redistribution exception, pst-5k38j; source hash and BOSL2 pin in [NOTICE](../../assets/openConnect-gridfinity-shelf/NOTICE) | [CC-BY-SA-4.0.txt](../reference/LICENSES/CC-BY-SA-4.0.txt) |
| Inter 4.1 ([rsms/inter v4.1 release](https://github.com/rsms/inter/releases/tag/v4.1), `extras/ttf/Inter-Bold.ttf`, sha256 `28831609…947f`) | SIL OFL 1.1 | **NOTICE:** the static Inter Bold TTF is vendored verbatim with its licence in `assets/fonts/inter/` for label text (pst-0zfra, [labels-spike.md](labels-spike.md)). OFL allows bundling and embedding; the font is not sold on its own and keeps its name and licence | [OFL.txt](../assets/fonts/inter/OFL.txt) |

`tools/measure_step.py` maps each source-manifest licence string to its
committed text (`LICENCE_TEXTS`). `--record` refuses to record a source whose
licence has no committed text.

**MIT carve-out.** [`multibuild/tile.py`](../multibuild/tile.py) is a remix
under the Multiboard Licence and is not MIT. It has a per-file header, the
adjacent [`LICENSE-MULTIBOARD.md`](../multibuild/LICENSE-MULTIBOARD.md), and
an exclusion in the root `README.md`. Every MultiBuild-derived file in
`reference/measured/` (`mb-*`) records `licence: Multiboard Licence` in its
manifest entry.

## Committed reference artefacts

All live in `reference/measured/`. Each has one entry in
[`reference/artifact-manifest.json`](../reference/artifact-manifest.json)
with these fields:

- `file`, `sha256`
- the foreign key `(source_file_id, source_sha256)`, which pins the exact
  mirrored version in `source-manifest.json`
- `source_group_id`, `licence`, `licence_text`
- `measured_on`, `tool_version`, and the reproducing `command`
- `plane`

Section files are in plane-local `(u, v)` coordinates. For an XZ section, `u`
is world X and `v` is world Z. For XY, they are world X and Y; for YZ, world Y and Z.

| Stem (`.json` `.dxf` `.svg`) | Source file | Section | Shows |
| --- | --- | --- | --- |
| `mc-v2-round` | Multiconnect v2_Round.step | XZ @ 0 | head: r 10 band 1.0, 45° taper 2.5, r 7.5 top 0.5 |
| `mc-v2-round-negative` | Multiconnect v2_Round Negative.step | XZ @ 0 | negative: r 10.15 / 7.65, bands 1.2121 / 0.4379, depth 4.15 |
| `mc-v2-slot-negative` | Multiconnect v2_Slot Negative.step | XZ @ Y=50 | slot: 20.3 wide, 4.15 deep, 25 long segment |
| `mb-large-octagon-hole-positive` | Large Octagon Hole (Positive).step | XY @ 3.1 | tile cell 25 × 25, planar levels 0 / 6.2 |
| `mb-multihole-negative` | Multihole (Negative).step | XZ @ 0 | octagon 23.4 → 21.4 over 2.0 per face; female helix r 10.7 / 11.25, pitch 2.5 |
| `mb-small-thread-negative` | Small Thread (Negative).step | XZ @ 0 | Ø8 mouth, 45° to Ø6 at 1.0; thread Ø6 / Ø7, pitch 3.125 |
| `mb-small-thread-hole-positive` | Small Thread Hole (Positive).step | XY @ 3.1 | small-hole cell centred on (12.5, 12.5): grid phase |
| `mb-small-vertical-12-5mm-positive` | 12.5mm - Small Vertical (Positive).step | XZ @ 0 | male small thread Ø5.75 / Ø6.75, pitch 3.125 |
| `mb-fix-point-slot-negative` | Fix Point Slot - Negative.step (group `multibuild-fix-point-slots`) | YZ @ X=0 | slot 17 × 23.4 × 3.2: lip mouth 6.0, land 0.4, 45° to 8.5 at 2.9; well end −14.5, undercut to −14.9 from 1.8 |
| `mb-fix-point-positive` | Fix Point - Positive.step (group `multibuild-fix-points`) | XZ @ Y=0 | head: neck r 5.87 × 0.454, 45° flare, flats ±7.2, r 8.0, top 3.0 |

`tests/test_reference_provenance.py` checks the committed evidence on every
PR:

- manifest coverage, sha256, FK resolution and entry completeness
- that no upstream original is committed
- that every [V] value re-derives from these JSON files
- that every MultiBuild constant is [V] and equals its measured value

The trusted workflow's `upstream` run regenerates each JSON and SVG
byte-for-byte from the mirror. DXF bytes embed save timestamps, so only
their content is compared.

The JSON `bbox` is OpenCascade's optimal box. For B-spline faces, such as
threads, it can overshoot the trimmed face: `mb-small-thread-hole-positive`
reports Z 6.6375, but its true top is 6.2. Derived values therefore use
the exact `levels` (planar faces normal to the axis) and the section edges.

## Measured vs cited values (MultiBuild)

| Value | Cited [C] | Measured [V] | Δ | Status |
| --- | --- | --- | --- | --- |
| Grid pitch | 25 | 25 | 0 | **confirmed** → `PITCH` [V] |
| Grid phase (small = large + 12.5, 12.5) | SCAD arithmetic | same | 0 | **confirmed** → `GRID_PHASE_PROVENANCE` [V] |
| Tile thickness | 6.4 | 6.2 | −0.2 | **adopted** → `TILE_THICKNESS` [V] (pst-ozpae) |
| Large octagon mouth / central across flats | 23.4 / 21.4 | 23.4 / 21.4 | 0 | **confirmed** [V] |
| Large octagon taper depth per face | 2.0 | 2.0 | 0 | **confirmed** → `LARGE_HOLE_TAPER_DEPTH` [V] |
| Large octagon band height | 2.4 | 2.2 | −0.2 | **adopted**, derived: `TILE_THICKNESS − 2·LARGE_HOLE_TAPER_DEPTH` (pst-ozpae) |
| Large helix outer / inner Ø | 22.6 / 21.4 | 22.5 / 21.4 | −0.1 / 0 | outer **adopted** (pst-ozpae); inner **confirmed** [V] |
| Large helix outer width / pitch | 0.5 / 2.5 | 0.5 / 2.5 | 0 | **confirmed** [V] (single start, right hand, 45° flanks) |
| Large helix inner (base) width | 1.583 | 1.6 | +0.017 | **adopted** (pst-ozpae; 45° flanks: pitch 2.5 − inner vertical extent 0.9) |
| Small-hole mouth Ø | 7.5 | 8.0 | +0.5 | **adopted** → `SMALL_HOLE_MOUTH_D` [V] (pst-ozpae; consumers `SmallHoleConePin`, `holder_cup_lid`) |
| Small-hole throat Ø | 6 | 6.0 | 0 | **confirmed** → `SMALL_HOLE_THROAT_D` [V] |
| Small-hole throat band | 2.9 | — | — | **removed** (pst-ozpae): the official hole is a 45° chamfer, then the thread; no plain band exists (6.2 − 2·1.0 = 4.2 is thread length) |
| Small-hole taper depth per face | 1.75 | 1.0 | −0.75 | **adopted**, derived: `(SMALL_HOLE_MOUTH_D − SMALL_HOLE_THROAT_D) / 2` at 45° (pst-ozpae) |
| Small thread pitch | 3 | 3.125 | +0.125 | **adopted** (docs only; pst-ozpae) |
| Small thread outer Ø / inner Ø | 7 / 6 | 7.0 / 6.0 | 0 | **confirmed** |
| Small thread axial widths outer / inner | 0.77 / 2.5 | 0.625 / 2.5 | −0.145 / 0 | outer **adopted** (docs only; pst-ozpae) |

pst-ff71 measured these without changing any constant; pst-ozpae adopted
every contradicted value in one PR (it consolidates the per-value beads
pst-rs70f, pst-kooqt, pst-23uzq, pst-x5vo8, pst-az4hh, pst-hav1h, pst-3spc5,
pst-gvdrx, pst-5lum5 and pst-oogqr). `multibuild/constants.py` now holds no
[C] value, and the regenerated tile (`multibuild/tile.py`, `TILE_PROFILE`)
references those constants instead of copying them. Shipped-holder fit
consequences: [cup-lid-validation.md](cup-lid-validation.md#pins-and-board-engagement) and
[spool-cradle-validation.md](spool-cradle-validation.md).

**Multiconnect.** The official v2 head and negative equal the pinned
`opengrid` library profile exactly:

- head radii 10 / 7.5, heights 1 + 2.5 + 0.5
- negative +0.15 radial, depth 4.15 = `multiconnect.POCKET_DEPTH`
- the dimension-drawing PDFs agree ([C]: 20.3 / 4.15 / 0.15 / 2.5, 1.2121,
  0.4379)

One official slot segment is 25 mm long, one board pitch. The library's
28 mm default is the openGrid unit, and this repo's `slot_cutter` already
sets the travel explicitly.

**Fix Point (pst-7shtl).** No cited Fix-Point dimension existed, so every
`multibuild/fixpoint.py` constant is [V] from the two `mb-fix-point-*`
artefacts (`fixpoint.PROVENANCE`). The rebuilt slot negative and head equal
the originals: volume within 0.003 %, bounding box exact, symmetric
difference ≤ 0.024 mm³ (`tests/test_fixpoint.py -m upstream`). The slot file
also carries a 0.5 mm locator tip at the origin below Z=0 (0.02 mm³, outside
any consumer); it is not rebuilt. The magnet-hole slot variants (the same slot
plus a magnet pocket from Z 3.2 to 5.2: Horizontal 10.6 × 10.6 bbox,
≈179 mm³, i.e. round, not square; Vertical 17 × 10.2 bbox) and the Lite,
Turn Slot and Twist Hole parts are mirrored but not measured or built.

## Measuring and recording

From `build123d/`, with the mirror pulled (`reference/FETCH.md`):

```bash
uv run tools/measure_step.py "reference/upstream/<group>/<sha12>/<file>.step" \
    --plane XZ --z 0 --json reference/measured/<stem>.json \
    --dxf reference/measured/<stem>.dxf --svg reference/measured/<stem>.svg --record
```

The media type follows the suffix:

- `.step`, `.stp` and `.brep` load as analytic B-rep, reporting cylinders,
  planes, `coaxial_radii` and `levels`.
- `.3mf` and `.stl` load as meshes, reporting bbox, volume and solids. Their
  analytic fields are `null` with `"analytic": "unsupported for mesh
  input"`, and multi-object files become one Compound.
- `.pdf` files are citation-only ([C] drawings) and are never loaded.
- `.zip` archives are never loaded.

`--record` finds the source by its sha256 and upserts one entry per output.
Commit the outputs and the manifest in the same PR.
