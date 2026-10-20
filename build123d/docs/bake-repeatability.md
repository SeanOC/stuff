# Bake repeatability and geometry comparisons

The OCCT 8 production bake has deterministic **paths**, but not guaranteed
byte-identical contents across fresh processes. This investigation
(pst-cdd2c) takes the bead's explicit comparison-contract option. It changes
no model, meshing setting, production writer, or output pin. Normalizing
triangle order alone would hide one symptom without fixing the changed
triangulations.

## Comparison contract

1. Keep the existing production bake gates: every app-listed preset and
   expected artifact must exist; STLs must be watertight with positive
   volume; GLB material counts must match the preview parts. These checks
   remain in `tests/test_presets_bake.py`. Keep existing model-specific byte
   pins, including `LABEL_CARD_BAKE_SHA256`; this finding is not permission
   to remove or regenerate them.
2. Compare bytes first, under the same lockfile, platform and inputs.
   A byte difference needs classification, not an automatic re-pin.
3. For STL **ordering equivalence**, require an identical multiset of
   oriented triangle coordinates. Ignore triangle order and cyclic choice
   of first vertex, and equate signed zero. Retain duplicate triangles and
   winding. Use raw stored coordinates, with no rounding or vertex welding.
   This proves equality of the represented oriented triangle surfaces; it
   does not establish GLB materials, normals, transforms, 3MF components or
   printer-profile equivalence.
4. If connectivity, winding or coordinates differ, equal counts, vertex
   sets, bounds and volume are **insufficient** to declare equal geometry.
   Review the changed surfaces and the BREP/audit evidence. A planar
   re-triangulation may be harmless, but must be demonstrated rather than
   inferred from scalar metrics. Do not automatically accept a changed
   diagonal, reversed winding, duplicate triangles or a small coordinate
   perturbation.
5. Compare GLB scene/material/transform structure and 3MF build-item,
   component, filament and printer-profile semantics separately. PNGs are
   rendered outputs: compare the source GLB and pixel differences. Neither
   an unchanged STL nor unchanged GLB bytes waive a changed PNG.
6. The numerical BREP/audit baseline, tolerance table, bake-structure
   comparator and deliberate re-baseline/waiver policy belong to
   **pst-6dhmb** (`geometry_baseline.py`, `compare_audit_rows.py`,
   `compare_bake.py`, as specified there). This investigation does not
   introduce a competing tolerance table or silently approve those pending
   comparisons. Until that work lands, connectivity/coordinate changes
   require explicit evidence and review. Output re-pins must document
   counts, volumes and the reason; a volume change is a geometry change,
   not an ordering exception.

`scripts/bake_repeatability.py` is a diagnostic for points 2–4. It reports
every changed file and classifies changed STLs. Its metrics use a welded
copy, matching the production watertightness check; its exact triangle
comparison uses the unprocessed mesh. It exits **1 for any byte or file-set
difference**, including harmless triangle reordering, and **0 only for byte
identity**. It is not the geometry-acceptance gate, and does not check that
two nonempty input directories contain the complete registry.

## Reproduce with fresh processes

From `build123d/`, use the production exporter, as the existing subprocess
bake test does. Each command starts a fresh Python/OCCT process. Use new
output directories; the exporter does not delete stale files.

```sh
uv sync --frozen
mkdir -p ../.tmp-bake-repeatability
uv run --frozen python scripts/export.py --presets-only ../.tmp-bake-repeatability/a \
  > ../.tmp-bake-repeatability/a.log 2>&1
uv run --frozen python scripts/export.py --presets-only ../.tmp-bake-repeatability/b \
  > ../.tmp-bake-repeatability/b.log 2>&1
uv run --frozen python scripts/bake_repeatability.py \
  ../.tmp-bake-repeatability/a ../.tmp-bake-repeatability/b \
  > ../.tmp-bake-repeatability/comparison.json
# Exit 1 is expected when the diagnostic finds byte differences.
```

Check both export exit codes before comparing. Keep their logs and
artifacts, the JSON, the commit SHA, `uv.lock`, platform and package
versions. Run more than two bakes when narrowing an intermittent finding.
Full repeats are an explicit investigation command, not extra work in the
default pytest/fast job. The existing full-bake coverage test remains the
production gate; the new diagnostic's small regression tests exercise
ordering, winding, connectivity, duplicates and coordinate changes.

To repeat the meshing-concurrency control, run this snippet in **two
separate processes**, each with a new target directory. These monkeypatches
are investigation-only; they are not installed in production.

```sh
uv run --frozen python - ../.tmp-bake-repeatability/serial-a <<'PY'
import sys
from pathlib import Path
import build123d.exporters3d as exporters
import build123d.topology.shape_core as core
from OCP.BRepMesh import BRepMesh_IncrementalMesh
def serial(shape, tolerance, relative, angular, parallel):
    return BRepMesh_IncrementalMesh(shape, tolerance, relative, angular, False)
exporters.BRepMesh_IncrementalMesh = serial
core.BRepMesh_IncrementalMesh = serial
from scripts.export import export_presets_only
raise SystemExit(export_presets_only(Path(sys.argv[1])))
PY
```

For the broader one-thread control, replace both meshing monkeypatches with:

```python
from OCP.OSD import OSD_Parallel, OSD_ThreadPool
assert OSD_Parallel.ToUseOcctThreads_s()
OSD_ThreadPool.DefaultPool_s().Init(1)
```

This controls OCCT's default worker pool, not every possible external
thread pool or source of nondeterminism.

## Evidence

The original discovery on unmodified `8d17fbe5` compared two complete
65-preset / 251-file bakes. Stopper STL/GLB ordering, pinned-stake STL/GLB
connectivity and the default sign PNG varied **without changing the
exporter**. That control predates the private-Mesher refactor in PR #237.
All 18 3MFs matched in those two runs; that was an observation, not a
format-wide stability guarantee.

The committed `bake-repeatability-evidence.json` records this investigation
on `b38d60c5` (PR #237 merged), with build123d 0.13.0,
cadquery-ocp-novtk 8.0.1.1.0 and trimesh 5.0.0. Every full bake used all
65 app presets and produced 251 files.

The fresh unmodified baseline pair changed these STLs (both runs remain
watertight with consistent winding):

| Preset | Vertices | Triangles | Volume mm³, before → after | Classification |
| --- | ---: | ---: | --- | --- |
| drawer / stopper-clips | 1,096 | 2,184 | 130.080008337617 → 130.080008337617 | Same oriented triangles |
| cartridge / default | 16,202 | 32,528 | 155025.83091547695 → 155025.83091547692 | Same oriented triangles |
| cartridge / full_holder | 107,250 | 215,648 | 1338819.7190942452 → 1338819.7190942452 | Same oriented triangles |
| tombstone sign / pinned | 196,135 | 392,278 | 533457.456753663 → 533457.456753663 | Changed connectivity |
| tombstone stake / pinned | 1,378 | 2,760 | 96699.11018038432 → 96699.11018038432 | Changed connectivity |

Counts, exact vertex sets and bounds matched in each pair. The tiny
cartridge volume-sum difference accompanies **exactly identical oriented
triangle multisets**, so it is accumulation order, not a moved surface.
The other scalar agreements do not prove the changed connectivity harmless.

Two full bakes with serial meshing still differed in stopper/cartridge
ordering, pinned sign/stake connectivity, pinned-sign 3MFs and PNGs. In
particular, the earlier observation that all 3MFs matched did not generalize.
Serial meshing is therefore insufficient to restore full-bake byte identity.
Two full bakes with the default OCCT pool limited to one thread still
changed stopper ordering, pinned sign/stake connectivity and a sign PNG.
Restricting that pool is also insufficient; the experiment does not
identify pointer hashing as the remaining cause.

Additional isolation:

- Four fresh targeted builds of stopper clips produced four BREP hashes
  **before meshing**. One visible BREP difference was an edge coordinate
  changing from `-0.70000000000000007` to `-0.69999999999999996`.
  Thus STL byte variation cannot be attributed solely to the writer.
- Four fresh targeted builds of the pinned stake produced two pre-mesh
  BREP hashes, with changed curve/wire representations. Exporting one
  fixed, saved BREP in four fresh processes produced identical STL bytes
  (`eda0f02a466f08942cbb3ed81a73753da9d365c7ae2ab78628e2cd1ef6cc5cf1`).
  This points to build/topology history as a contributor; it does not
  prove every meshing path deterministic.
- The default sign PNG in the discovery/current comparison changed one of
  160,000 pixels (maximum channel delta 13), while its GLB bytes matched.
  The two fresh current baseline bakes changed one pixel in the two-colour
  sign PNG (maximum channel delta 18), again with identical GLB bytes.
  Two isolated renders of the same default-sign GLB matched, including
  loaded vertex, face and normal arrays. The render symptom is therefore
  not explained by GLB ordering alone; its precise numerical cause remains
  unresolved. No PNG tolerance or automatic waiver is introduced.

No outputs are re-pinned. Production geometry and watertightness are
preserved by leaving the production execution paths unchanged.
