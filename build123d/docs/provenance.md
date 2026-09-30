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
| openGrid | CC BY 4.0 | via the MIT `opengrid` Python library; no openGrid files are mirrored yet | — |
| Gridfinity | MIT | not used by build123d yet | — |

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
is world X and `v` is world Z. For XY, they are world X and Y.

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

`tests/test_reference_provenance.py` checks the committed evidence on every
PR:

- manifest coverage, sha256, FK resolution and entry completeness
- that no upstream original is committed
- that every [V] value re-derives from these JSON files
- that every contradicted [C] value keeps its cited number and follow-up bead

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
| Tile thickness | 6.4 | 6.2 | −0.2 | changed → pst-rs70f |
| Large octagon mouth / central across flats | 23.4 / 21.4 | 23.4 / 21.4 | 0 | **confirmed** [V] |
| Large octagon band height | 2.4 | 2.2 | −0.2 | changed → pst-kooqt (taper 2.0 per face confirmed) |
| Large helix outer / inner Ø | 22.6 / 21.4 | 22.5 / 21.4 | −0.1 / 0 | outer changed → pst-23uzq; inner **confirmed** |
| Large helix outer width / pitch | 0.5 / 2.5 | 0.5 / 2.5 | 0 | **confirmed** [V] (single start, right hand, 45° flanks) |
| Large helix inner (base) width | 1.583 | 1.6 | +0.017 | changed → pst-x5vo8 |
| Small-hole mouth Ø | 7.5 | 8.0 | +0.5 | changed → pst-az4hh (consumer: `SmallHoleConePin`) |
| Small-hole throat Ø | 6 | 6.0 | 0 | **confirmed** → `SMALL_HOLE_THROAT_D` [V] |
| Small-hole throat band | 2.9 | 4.2 | +1.3 | changed → pst-hav1h (official = 45° chamfer, then thread) |
| Small-hole taper depth per face | 1.75 | 1.0 | −0.75 | changed → pst-3spc5 |
| Small thread pitch | 3 | 3.125 | +0.125 | changed (docs only) → pst-gvdrx |
| Small thread outer Ø / inner Ø | 7 / 6 | 7.0 / 6.0 | 0 | **confirmed** |
| Small thread axial widths outer / inner | 0.77 / 2.5 | 0.625 / 2.5 | −0.145 / 0 | outer changed (docs only) → pst-5lum5 |

"Changed" means the official file contradicts the cited value. The constant
is **not** changed in the measuring PR. Each follow-up bead decides whether
to adopt the measured value or justify keeping the cited one. The
regenerated tile (`multibuild/tile.py`, `TILE_PROFILE`) already uses the
measured values.

**Multiconnect.** The official v2 head and negative equal the pinned
`opengrid` library profile exactly:

- head radii 10 / 7.5, heights 1 + 2.5 + 0.5
- negative +0.15 radial, depth 4.15 = `multiconnect.POCKET_DEPTH`
- the dimension-drawing PDFs agree ([C]: 20.3 / 4.15 / 0.15 / 2.5, 1.2121,
  0.4379)

One official slot segment is 25 mm long, one board pitch. The library's
28 mm default is the openGrid unit, and this repo's `slot_cutter` already
sets the travel explicitly.

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
