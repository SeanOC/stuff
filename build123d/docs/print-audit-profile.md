# Print-audit profile (pst-bzahj, CI P8 spike)

Where `tests/print_audit.audit()` spends its time, and the one speed-up taken.

**Result.** 75–85 % of a cradle audit was build123d rebuilding OCCT's solid
classifier on every `part.is_inside(point)` call. The audit now loads that
classifier once and reuses it (`_ClassifiedPart`). It makes the same calls at
the same points with the same tolerance, so every report is unchanged. The
equality proof covers every audit call site. The cradle default audit dropped
from 77.1 s to 11.3 s of CPU (−85 %).

## Method

- `scripts/profile_print_audit.py` builds each case the same way as
  `test_print_audit._build_and_audit`: registry values, mount-fixture cutters
  and the cup-lid shank exclusion. It then times each audit phase on its own
  (`time.process_time`, CPU seconds) and the end-to-end `audit()`.
- A second pass with counting wrappers on `Solid.is_inside`, `Face.is_inside`,
  `Face.position_at` and `Face.normal_at` records the call counts per phase.
  It runs separately so the wrappers do not distort the times.
- `--cprofile <case>` prints a cProfile of `audit()`, sorted by tottime.
  pyinstrument was not needed: cProfile pinned the hotspot to one frame.
- Cases: `holder_spool_cradle` at defaults; the cradle at `PRINT_CORNER`
  (test_spool_cradle `diagonal-root-corner`: spool Ø205, width 70,
  cradle_angle 25, clearance .25, plate 68 × 6.6); `holder_cup_lid` at
  defaults with its shank exclusion.
- Hardware: AMD Ryzen 7 8745H (8 cores / 16 threads), Linux 6.17, Python
  3.14.4, build123d 0.11.1, OCP 7.9.3.1. The host is shared with other
  workers (load average ~6 during the runs). CPU time still inflates under
  hyperthread contention (pst-mxfqk), so read single numbers as ±10 %.
- "Sum of phases" exceeds `audit()` end-to-end on the cradle. Each phase was
  timed in a fresh call, so OCCT's lazily built face caches warm up once per
  phase rather than once per audit.

## Before: origin/main (cadb72a)

cProfile, cradle default: 4,907 `Solid.is_inside` calls took 77.4 s
cumulative out of 86.9 s. Of that, **65.4 s was `is_inside` tottime**, which
is the `BRepClass3d_SolidClassifier(self.wrapped)` constructor. All 16,833
`Perform` calls (solid + face) took only 12.9 s. `Face.is_inside` took 2.1 s
over 11,926 calls. Everything else was under 4 s.

### cradle default (337 faces, 2 cutter regions)

| phase | CPU s | % | Solid.is_inside | Face.is_inside | position_at | normal_at |
|---|---:|---:|---:|---:|---:|---:|
| overhang | 6.85 | 8 | 337 | 5775 | 5438 | 9691 |
| bridge raster | 4.62 | 5 | 222 | 310 | 88 | 222 |
| wall march | 66.97 | 79 | 4011 | 3541 | 3197 | 4883 |
| curved faces | 3.00 | 4 | 115 | 1990 | 1875 | 3557 |
| bed chamfer | 3.39 | 4 | 222 | 310 | 88 | 222 |
| sum of phases | 84.83 | | | | | |
| **audit() end-to-end** | **77.13** | | | | | |

### cradle diagonal-root corner (307 faces, 2 cutter regions)

| phase | CPU s | % | Solid.is_inside | Face.is_inside | position_at | normal_at |
|---|---:|---:|---:|---:|---:|---:|
| overhang | 5.92 | 10 | 307 | 4943 | 4636 | 7767 |
| bridge raster | 2.94 | 5 | 198 | 634 | 436 | 198 |
| wall march | 42.16 | 74 | 3295 | 3949 | 3635 | 4213 |
| curved faces | 2.80 | 5 | 109 | 1734 | 1625 | 3051 |
| bed chamfer | 3.10 | 5 | 198 | 634 | 436 | 198 |
| sum of phases | 56.92 | | | | | |
| **audit() end-to-end** | **50.52** | | | | | |

### cup lid (53 faces, 1 exclusion region)

| phase | CPU s | % | Solid.is_inside | Face.is_inside | position_at | normal_at |
|---|---:|---:|---:|---:|---:|---:|
| overhang | 0.31 | 17 | 53 | 1334 | 1281 | 2189 |
| bridge raster | 0.04 | 3 | 31 | 37 | 6 | 31 |
| wall march | 1.22 | 70 | 945 | 544 | 487 | 864 |
| curved faces | 0.14 | 8 | 22 | 547 | 525 | 1056 |
| bed chamfer | 0.05 | 3 | 31 | 37 | 6 | 31 |
| sum of phases | 1.76 | | | | | |
| **audit() end-to-end** | **1.78** | | | | | |

Reading the tables:

- **Face sampling** (`position_at` + `Face.is_inside` + `normal_at`) is cheap.
  On the cradle it is about 2–3 s in total across all phases.
- **Cutter/exclusion subtraction** (`_in_any_box`) does not show up. The
  cradle's two regions are bboxes. The cup lid's exact cylinder costs an
  `is_inside` per sample, but that lid audit is 1.8 s in total.
- Every phase is dominated by its `Solid.is_inside` calls at about 13–17 ms
  each, and nearly all of that is classifier construction. The wall march is
  79 % of the audit because it makes 82 % of those calls (up to 18 bisections
  per sample).

## The speed-up: reuse one classifier per audit

`audit()` wraps the part in `_ClassifiedPart`. That proxy builds one
`BRepClass3d_SolidClassifier` and answers `is_inside` with
`Perform(point, tol)` followed by build123d's own rule:
`State() == IN or IsOnAFace()`. Every other attribute, such as `faces()` and
`vertices()`, goes to the real part.

No phase logic, grid, constant or threshold changed. The call counts after
the change match the counts before it to the call, so the audit probes the
same points.

### After (this branch)

| case | phase CPU s: overhang / bridge / wall / curved / chamfer | audit() before → after | change |
|---|---|---:|---:|
| cradle default | 2.05 / 0.43 / 7.13 / 1.81 / 0.50 | 77.13 → **11.30** | −85 % |
| cradle diagonal-root corner | 1.99 / 0.66 / 5.89 / 1.28 / 0.60 | 50.52 → **11.74** | −77 % |
| cup lid | 0.28 / 0.01 / 0.23 / 0.15 / 0.01 | 1.78 → **0.70** | −61 % |

The wall march is still the largest phase at about 60 %. What remains is
mostly the 4,011 `Perform` calls themselves plus face sampling. The next lever
would be listed option (c), a wall-march pre-test. With the classifier
reused, it can only save part of about 7 s per cradle audit, so it is not
worth its proof burden now.

### Why not the listed options (a)–(d)

Each of these targets a cost that is small once the profile is read:

- **(a) cache face samples across passes.** It would save about 2/3 of the
  per-pass `_outward_normal` calls, which are about 14 s of 77 s (18 %)
  because each makes one `Solid.is_inside` call. Below the 25 % bar on its
  own, and the classifier reuse removes most of that cost anyway.
- **(b) planar faces sampled once.** This touches only the overhang and
  curved passes, about 10 s together, and their cost is `_outward_normal`
  rather than the 25 samples.
- **(c) wall-march pre-test or vectorised bisection.** It reduces call count
  but leaves the 13 ms per call. A pre-test that skips faces also needs its
  own proof that it never skips a thin wall.
- **(d) drop faces inside a cutter before sampling.** The cradle has only 2
  cutter regions, so there is little to drop.

Classifier reuse is not on the bead's list; it is option (e). It was chosen
because the profile shows it removes the dominant cost in every phase without
touching any decision logic. The bead's invariants still hold: no verdict
change (proof below), no constants changed, and no new runtime dependency.
OCP is what build123d itself calls.

## Equality proof

`scripts/audit_equality_proof.py` is a one-off pytest plugin, not a permanent
test. It wraps `tests.print_audit.audit` so that every call any test makes
also runs the origin/main `print_audit.py`, loaded from git, on the same
arguments. It then compares every `PrintAuditReport` field: floats to 1e-6,
everything else exact. Downward fillets compare by type, location and angle,
which identifies the offending faces. It covers every audit call site:
test_print_audit (all registered models, the budget test and the cup-lid
exclusion test), test_spool_cradle, test_multibuild, test_openconnect,
test_cylindrical_junction and test_cup_lid.

Run (-n 4, 2026-10-02, against origin/main cadb72a): 429 passed, 6 skipped,
1 xfailed (the standing smoke-tile wall miss). Per-call rows are in the PR body.

| test file | audit calls | reference CPU s | new CPU s | differing |
|---|---:|---:|---:|---:|
| test_cylindrical_junction.py | 14 | 50.8 | 12.2 | 0 |
| test_multibuild.py | 4 | 16.6 | 3.3 | 0 |
| test_openconnect.py | 2 | 34.0 | 5.8 | 0 |
| test_print_audit.py | 27 | 129.0 | 29.4 | 0 |
| test_spool_cradle.py | 41 | 3842.0 | 560.6 | 0 |
| **total** | **88** | **4072.4** | **611.3** | **0** |

The CPU times here are under `-n 4` contention, so they run higher than the
serial profile above. The ratio still holds: 85 % less across all 88 calls.

Reproduce:

```bash
cd build123d
AUDIT_PROOF_DIR=/tmp/proof PYTHONPATH=. uv run pytest -p scripts.audit_equality_proof \
  tests/test_print_audit.py tests/test_spool_cradle.py tests/test_multibuild.py \
  tests/test_openconnect.py tests/test_cylindrical_junction.py tests/test_cup_lid.py -q -n 4
uv run python scripts/audit_equality_proof.py /tmp/proof   # table; exit 1 on any diff
```

## Budgets

The cradle's own 120 s entry in `test_print_audit._MODEL_BUDGET_S` is
removed. The cradle now falls under the 60 s default: 11–12 s of audit plus
about 3 s of build, measured serially. That leaves about 4× headroom for
CI's slower cores. The default stays at 60 s and nothing was loosened.

## Cache

`audit()` answers from `tests/audit_cache.py` (pst-sx1g3) when the same
geometry, arguments and audit code were audited before. One JSON file per key
holds the stored `PrintAuditReport`. A hit returns a report equal to the stored
one, field by field. It costs the key build (under 1.2 s on the largest part)
instead of the 10–80 s audit, and that key time is not counted in `audit_s`. A
report is stored only after an audit returns; an audit that raises stores
nothing.

**Key.** The key is a sha256 over four parts, in this order:

1. **The part's shape signature** (`audit_cache.shape_sig`). A geometry copy
   is meshed at tolerance 0.01. Each face contributes its sorted mesh
   vertices and its area, both rounded to 1e-6, and the face list is sorted
   and hashed. The audited part itself is never meshed. The I2 determinism
   gate rejected two simpler forms:
   - **BREP bytes.** OCCT orders topology records by TShape address, so
     `holder-tombstone-sign/pinned`, `holder-tombstone-stake/pinned` and
     `littletikes-dream-machine-cartridge-holder/default` write different
     BREPs across processes, or within one process depending on what was
     built first. The geometry is the same each time.
   - **Sorted triangle centroids.** The tombstone presets mesh to the same
     vertices (within 3e-14), but the mesher picks different diagonals on
     planar faces. Per-face vertex sets do not depend on the diagonals, and
     the area separates two faces that share a vertex set.

   A signature costs under 1.2 s on the largest part.
2. **The audit code.** This is the text of `tests/print_audit.py` and
   `tests/audit_cache.py`, plus every UPPER_CASE module constant of
   `print_audit` read at call time. It also takes `holders.printer`'s
   `BED_X/BED_Y/BED_Z` read at call time, and the frozen bed defaults of
   `bed_failure` and `PrintAuditReport`. A threshold change in any file
   changes the key.
3. **The installed versions** of build123d, OCP and Python.
4. **Canonical JSON of the other arguments:**
   - **Orientation:** rounded to 1e-6.
   - **`print_frame`:** position plus Euler orientation, rounded to 1e-6.
     Euler degeneracy can only cause a spurious miss, never a false hit.
   - **Model label:** used as is.
   - **Cutters:** each one keys as the bbox of the cutter as `_cutter_boxes`
     receives it, after `print_frame` moves it. The list is sorted.
   - **Exclusions:** sorted. The form depends on the element:
     - A Shape keys as its shape signature. A bbox key would make a hexagonal
       ceiling facet and a rectangle with the same bbox collide.
     - A 6-tuple keys as its rounded numbers.
     - An analytic predicate (`is_inside`, no `.wrapped`) keys as its
       qualified class name, the sha256 of `inspect.getsource` of its class,
       and the total canonical JSON of `vars()`. In that JSON, numbers are
       rounded, a Shape becomes its shape signature, a BoundBox becomes its corners,
       and containers are walked recursively.

If any argument has no faithful form, the call is **uncacheable**: it runs,
nothing is stored, and it counts as `off`. This covers any other type, a
predicate whose source cannot be read, and a `vars()` entry of an unknown
type. **An exclusion predicate must be self-contained.** If its `is_inside`
delegates to a module-level helper or constant, editing that helper changes
the behaviour but not the key.
**A test that monkeypatches an audit helper must turn the cache off.** The
key covers the source bytes of `print_audit.py` and `audit_cache.py` and the
UPPER_CASE constants, so a patched constant changes the key but a patched
lowercase helper (for example `_face_in_box`) does not. Without the switch
the patched call is a hit and never runs. Wrap that call in
`audit_cache.disabled()`, as
`test_cartridge_holder.py::test_rectangular_exclusion_fast_path_is_equivalent`
does.

**Switch.** The default store is `build123d/.cache/audit/`, which is
gitignored. `BD_AUDIT_CACHE=<dir>` moves it and `BD_AUDIT_CACHE=off` disables
it. A corrupt or unreadable entry is logged and treated as a miss, and the
next store overwrites it. Writes are atomic, so xdist workers can store the
same key at the same time.

**The budget stays cold.** bd123's serial `audit budgets` step sets
`BD_AUDIT_CACHE: off`. Independently, `test_print_audit._timed_audit(cold=True)`
runs the timed audit under `audit_cache.disabled()` and asserts that it was
not a hit. A cached audit would make the 60 s and 90 s budgets trivially
true.

**Observability.** Every pytest session ends with this line:
`AUDIT-CACHE hits=N misses=M off=K audit_s=S`. `audit_s` is the summed CPU
seconds of the cache misses; off/uncacheable audits count under `off` but are
not timed. Under xdist there is one line per worker (`worker=gwN`) and a
`worker=all` total.

**CI.** The `audit` job and each `audit_full` shard restore and save
`build123d/.cache/audit` with `actions/cache@v4`. The key is
`bd-audit-<hash of print_audit.py, audit_cache.py, uv.lock>-<job>-<run id>`
(`<job>` is `audit` or the shard number), and each job restores its own prefix
`bd-audit-<hash>-<job>-`. `actions/cache` restores only the newest single
entry that matches the prefix, not a union of entries. A prefix shared by all
jobs therefore restored whichever job saved last, often a small shard archive,
and on PR #204 that left the `audit` job cold until it hit its timeout. The
fast job does not cache.

**Clear it.** Run `rm -rf build123d/.cache/audit`. In CI, delete the
`bd-audit-*` caches in the repo's Actions → Caches page, or change either
hashed file.

**Equality proofs and timings.** `scripts/audit_equality_proof.py` and
`scripts/profile_print_audit.py` run every `audit()` they time inside
`audit_cache.disabled()` (pst-dyobq), so they never read or store a cached
report. Any other timing work needs the same wrap or `BD_AUDIT_CACHE=off`.
Otherwise the "new CPU s" column times cache hits.

## The slowest audit_full item (pst-vhywk)

`test_openconnect_drawer_container.py::test_endpoint_audit_and_edges[vertical_grids=8]`
had 738 s in `tests/.test_durations` and took 833–855 s on CI cold. As one pytest
item it set the floor on its shard's wall time. The profiler now has it as
`drawer_container_vertical_grids_8`. That case uses the test's own `print_frame`
and exclusions (`m.audit_exclusions + container_wall_regions`, 407 regions).
Both the profiler and the timings below run with the cache off.

The test's own phases were timed in one process with `BD_AUDIT_CACHE=off`
(2,363 faces). The host was shared, with a load average of 20–33 and the
profiler running alongside, so read the absolute seconds as inflated (the
quiet-host figure is 672 s for the whole item). The shares are what V1 decides
on:

| phase | wall s | CPU s | % of wall |
|---|---:|---:|---:|
| build (`m.build`) | 36.8 | 37.5 | 3 |
| ceiling chords | 0.2 | 0.2 | 0 |
| exclusion regions | 1.7 | 1.7 | 0 |
| cache key (`shape_sig` of the part) | 1.3 | 1.6 | 0 |
| **`audit()`** | **1089.1** | **964.4** | **92** |
| bed-bevel sections | 4.1 | 4.0 | 0 |
| edge inventory | 52.7 | 52.0 | 4 |

**Decision (bead V1).** `audit()` takes 92 % of the item's wall time (91 % of
its CPU time), above the bead's 60 % line, so this case does not need to be
split or sampled. A cache hit swaps the audit for a key build of a few seconds.
What remains is the build and the edge inventory, about 95 s on this loaded
host and under 8 % of the item. The exclusions are all Shapes (`Box`, `Solid`), so the
call is cacheable. On main run 38630578619, shard 4 reported `off=0`. A
test-level split (option (c)) could not help on its own, because the audit half
would still hold over 90 % of the item. The cache answers only when the container's geometry,
exclusions and audit code are unchanged since the shard last saved. A PR that
changes any of them runs this item cold again, at the old ~14 min CI wall.
