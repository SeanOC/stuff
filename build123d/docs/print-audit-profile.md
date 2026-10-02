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
