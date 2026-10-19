# build123d 0.13.0 upgrade spike

Bead `pst-oy53e`, measured 2026-10-19 against
`origin/main@15d441e439ad834b4dc347fed35ad933bc2ad4ab`.
Report only: the committed dependency lock, models, tests, hash pins and
workflows are unchanged.

**Recommendation: no-go for an unmodified dependency upgrade.** OCP API
removals stop test collection and tombstone construction; class-signature
introspection also breaks the Multibuild slot cutter. The label-card
exports also require deliberate hash review. This is a recommendation for
the mayor/operator; it does not authorize an upgrade or automatic re-pinning.

## Method and provenance

The baseline is the committed 0.11.1 lock. The candidate is a separate copy
of the same tracked repository with its own virtual environment, resolved
using `uv sync --upgrade-package build123d==0.13.0`. No compatibility patches
were applied to either source tree. The initial scratch copy contained only
`build123d/`; its service-file failures were discarded, and the diagnostic
suite was restarted after copying the rest of the tracked repo.

The long candidate diagnostic run was subsequently split to rebalance the
tail: 2,282 regular cases finished in its first stage, and the remaining 178
were scheduled with `--maxschedchunk=1`. The case sets are disjoint and their
union is checked against all 2,460 collectable regular candidate cases.
The 73 tests in `test_tombstone_sign.py` cannot collect; 39 of them are audits.
These staged diagnostics do not provide a comparable passing-suite benchmark.

Three Git-inventory assertions failed because `git ls-files` saw the archived
scratch tree as untracked. All three passed in a targeted rerun with the
original index and the scratch tree supplied through scoped `GIT_DIR` and
`GIT_WORK_TREE` environment variables. They are harness failures, not upgrade
regressions. The reproduction recipe uses a real scratch Git checkout to
avoid them. No Git settings or source files were changed for that verification.

The [0.12 release notes](https://github.com/gumyr/build123d/releases/tag/v0.12.0)
describe the removed APIs, builder placement/selection changes and exporter
changes. [0.13](https://github.com/gumyr/build123d/releases/tag/v0.13.0)
adds the OCP 8 transition. Installed versions, rather than the shorthand
kernel names in those notes, are recorded below.

| Dependency | Baseline | Candidate |
| --- | --- | --- |
| build123d | 0.11.1 | 0.13.0 |
| cadquery-ocp-novtk / cadquery-ocp-proxy | 7.9.3.1.1 | 8.0.1.1.0 |
| ocp-gordon | 0.2.2 | 0.3.1 |
| ocpsvg | 0.6.0 | 0.7.0 |
| bd-materials | absent | 0.2.4 |
| threejs-materials | absent | 1.2.5 |
| fonttools | 4.63.0 | 4.63.0 |
| lib3mf | 2.5.0 | 2.5.0 |
| Python | 3.14.4 | 3.14.4 |

The resolver also adds dataclasses-json 0.6.7, deprecated 3.0.0,
marshmallow 3.26.2, mypy-extensions 1.1.0, platformdirs 4.13.5,
pygltflib 1.16.5, typing-inspect 0.9.0 and wrapt 2.5.1.
All other existing package versions remain unchanged; opengrid stays at
`eea2b4154a10d2909e5edece567cbe0563aaf955`.

Lock-file SHA-256: baseline
`d5aedd1449bc99c8bb74c42301ae9d3a850d6f0817e28832ca6b74551689a404`;
scratch candidate
`fc7cb653206641314140f2f51509a6b31dcaddd12fbe20a56694330b0390f47d`.

Local runs use Ubuntu 24.04.4 x86_64, AMD Ryzen 7 8745H (8 cores / 16 threads),
and uv 0.13.1. They are **not** measurements on a GitHub runner or a CI
container. The current workflow uses `ubuntu-latest`, not a pinned container.
Concurrent local suites/probes and existing baseline audit cache entries
make local elapsed times unsuitable for an upgrade speedup claim.

Audit baselines come from the successful
[main run 39231607959](https://github.com/SeanOC/stuff/actions/runs/39231607959),
at the same source SHA: `bd123-audit-rows` and all six
`bd123-audit-rows-<group>` artifacts. All `rows*.jsonl` files, including worker
files, are included: 725 outcome rows and 477 measurement rows. No local
baseline audit is substituted for those published rows.

## (a) Removed APIs and import/attribute errors

The first-party scan covers 149 Python files. An AST-based import probe
resolves all 653 `from build123d...` / `from OCP...` imported names in the
candidate environment; only the tombstone test import fails. Runtime
attributes require the execution checks as well as this import scan.

| API/change | First-party sites | Finding |
| --- | --- | --- |
| Tangent arc/line classes; `Face.make_plane`; `is_planar_face`; `split_by_perimeter` | None | No direct migration |
| `to_axis`, `to_plane`, `to_wire`, `to_arcs`, `relocate`, `LocationEncoder` | None | No direct migration |
| `to_tuple` | `tests/test_underware_text_label.py:81`, twice on one line | Removed `Vector` method; use `tuple(vector)` |
| Arc `end_angle` / `angular_direction`; SVG `is_inkscape_label` | None | No direct migration |
| Builder `add` / `new_edges` | None | All 19 `.add()` calls are Python sets |
| `BoundBox.is_inside` / `find_outside_box_2d` | None | Shape/face containment calls are a different API |
| `Select.LAST` / `Select.NEW` / `selectors=` | None | No direct selection sites to compare |
| `Unit.MM`, ExportSVG colours | `tools/measure_step.py:173,177` | Section exporters use default colours; `test_measure_step.py::test_section_dxf_svg_written` passes in the candidate |
| `TopTools_ListOfShape` | `tests/test_tombstone_sign.py:20,580` | OCP 8 import error prevents collection of this entire module |
| `TopoDS.Vertex_s` | `holders/tombstone_sign.py:430` | OCP 8 attribute error prevents plate construction |
| Class `inspect.signature` | `multibuild/multiconnect.py:37`; `tests/test_multibuild.py:115` | Class signatures become `(*args, **kwargs)`; default lookups raise `KeyError` for `head_spacing` / `bottom_radius_clearance` |

For `SnapInSlotCutter`, `RoundHeadCutter` and `SlotCutter`, introspecting
`cls.__init__` instead retains the pinned defaults in both environments:
`head_spacing=0.795`, `bottom_radius_clearance=0.15` and
`bottom_width_clearance=0.3`. The opengrid source pin did not change. This
breaks a production Multibuild helper outside the app-preset registry;
successful registered presets therefore do not cover it. Seven Multibuild
tests expose this regression. The other first-party signature inspection,
`tests/test_print_audit.py:648`, examines a function hook rather than these
classes.

The first unmodified full-suite invocation stops at collection in 8.90 s
with one error. To obtain results for the rest of the corpus, the diagnostic
run uses `--continue-on-collection-errors`; it is not a passing full suite.
The tombstone-dependent audit-cache test fails while building geometry,
before it can compare cache keys. That failure is not evidence of unstable
cache hashes.

## (b) Geometry, placement and selection

There are no direct `Select.LAST/NEW` call sites. Nevertheless the probe
builds every registered preset, including smoke registrations, because the
builder placement refactor can affect models without explicit selections.
It records BREP volume, face/solid count, raw and print-frame bounds,
print-frame centre, and containment at 125 normalized interior sample points
(each axis at 0.1, 0.3, 0.5, 0.7, 0.9 of its bounding-box extent). Production
STL volume and triangle counts are recorded after baking each app preset.
These checks detect placement/geometry changes at the measured points;
they are not a proof of identical surfaces or every parameter setting.

The bake probe calls the unchanged `export_presets_only` once per preset
with a one-preset registry view, so a failure cannot hide subsequent models.
The normal all-presets bake is also exercised by the suite's production
subprocess test. Failed builds have no candidate geometry or hashes; their
cells must not be interpreted as zero drift.

The probe completed 68 baseline and 68 candidate registrations/presets. 63 have paired BREP measurements. Candidate build/bake errors: 5.

<details>
<summary>All 68 preset and smoke comparisons</summary>

| Model / preset | Baseline BREP mm³ | Δ BREP mm³ | Faces 0.11 → 0.13 | STL mm³ 0.11 → 0.13 | Triangles 0.11 → 0.13 | Max bounds Δ mm / containment differences |
| --- | ---: | ---: | --- | --- | --- | --- |
| `holder-cup-lid/sippy_cup_85mm` | 16085.41480 | +1.81899e-12 | 53 → 53 | 16082.19064 → 16082.19064 | 10380 → 10380 | 0 / 0 |
| `smoke-opengrid-tile-1x1/defaults` | 983.29200 | -3.18323e-12 | 50 → 50 | smoke / unavailable | — | 1.55e-15 / 0 |
| `smoke-multiconnect-roundhead/defaults` | 1007.92764 | +0 | 5 → 5 | smoke / unavailable | — | 0 / 0 |
| `label-demo/defaults` | 1317.77581 | +5.15451e-06 | 26 → 26 | smoke / unavailable | — | 4.26e-14 / 0 |
| `holder-spray-can/spray_can` | 46093.51443 | +2.18279e-11 | 68 → 68 | 46091.95594 → 46091.95594 | 4078 → 4078 | 0 / 0 |
| `holder-spray-can/spray_can_light` | 43166.83317 | +1.45519e-11 | 60 → 60 | 43162.75757 → 43162.75757 | 3962 → 3962 | 0 / 0 |
| `holder-spray-can/spray_can_robust` | 55600.90849 | +2.91038e-11 | 79 → 79 | 55588.41326 → 55588.41326 | 3282 → 3282 | 0 / 0 |
| `holder-bottle-500ml/bottle_500ml` | 47929.49019 | -1.45519e-11 | 68 → 68 | 47921.75867 → 47921.75867 | 4086 → 4086 | 0 / 0 |
| `holder-bottle-500ml/bottle_500ml_light` | 45039.40963 | +0 | 60 → 60 | 45028.70362 → 45028.70362 | 3970 → 3970 | 0 / 0 |
| `holder-bottle-500ml/bottle_500ml_robust` | 57835.44305 | -2.18279e-11 | 79 → 79 | 57821.48259 → 57821.48259 | 3282 → 3282 | 0 / 0 |
| `holder-spool-cradle/channel` | 105052.23309 | +9.5721e-07 | 412 → 412 | 105071.02200 → 105071.02200 | 17562 → 17562 | 5.68e-14 / 0 |
| `holder-spool-cradle/points` | 117395.93810 | +9.63133e-07 | 380 → 380 | 117412.72431 → 117412.72431 | 13994 → 13994 | 5.68e-14 / 0 |
| `holder-spool-cradle/openconnect` | 137203.46831 | +9.73669e-07 | 440 → 440 | 137222.19932 → 137222.19932 | 18240 → 18240 | 0 / 0 |
| `holder-label-card/inlaid` | 1891.85581 | +1.08726e-07 | 26 → 26 | 1891.84929 → 1891.84929 | 1564 → 1564 | 1.44e-13 / 0 |
| `holder-label-card/raised` | 2038.90647 | +1.08725e-07 | 181 → 181 | 2038.88251 → 2038.88251 | 19696 → 19696 | 1.44e-13 / 0 |
| `openconnect-plate/default` | 17877.22303 | +0 | 228 → 228 | 17877.22024 → 17877.22024 | 7096 → 7096 | 0 / 0 |
| `openconnect-plate/one-tile` | 2968.48052 | +0 | 65 → 65 | 2968.47991 → 2968.47991 | 1770 → 1770 | 0 / 0 |
| `openconnect-plate/negslot` | 6067.08630 | +0 | 208 → 208 | 6067.08851 → 6067.08851 | 7028 → 7028 | 0 / 0 |
| `openconnect-gridfinity-shelf/default` | 26504.38326 | -0.000141293 | 294 → 294 | 26504.60360 → 26504.74963 | 25896 → 16868 | 1e-07 / 0 |
| `openconnect-gridfinity-shelf/magnets` | 53079.29271 | +7.63058e-05 | 362 → 362 | 53077.66218 → 53077.80886 | 36880 → 27634 | 1e-07 / 0 |
| `openconnect-gridfinity-shelf/wide` | 53063.49292 | -0.000286333 | 544 → 544 | 53063.99254 → 53064.28174 | 48266 → 30044 | 1e-07 / 0 |
| `openconnect-gridfinity-shelf/sturdy-back` | 29768.25995 | +2.33096e-05 | 294 → 294 | 29768.49050 → 29768.63475 | 26014 → 16936 | 1e-07 / 0 |
| `openconnect-drawer/default` | 120780.16184 | +0 | 883 → 883 | 120780.28080 → 120780.28080 | 10248 → 10248 | 0 / 0 |
| `openconnect-drawer/small` | 20663.44312 | +0 | 204 → 204 | 20663.49460 → 20663.49460 | 5982 → 5982 | 0 / 0 |
| `openconnect-drawer/top-slot` | 131680.19787 | +0 | 1074 → 1074 | 131680.32870 → 131680.32870 | 7818 → 7818 | 0 / 0 |
| `openconnect-drawer/container` | 65648.48393 | +0.0154107 | 642 → 642 | 65650.50624 → 65650.50624 | 12928 → 12928 | 0 / 0 |
| `openconnect-drawer/two-compartments` | 139453.62455 | +0 | 1171 → 1171 | 139453.81886 → 139453.81886 | 14458 → 14458 | 0 / 0 |
| `openconnect-drawer/organiser` | 83758.72769 | +0.167516 | 710 → 710 | 83761.04113 → 83761.04113 | 14780 → 14780 | 0 / 0 |
| `openconnect-drawer/stopper-clips` | 130.08000 | +0 | 56 → 56 | 130.08001 → 130.08001 | 2184 → 2184 | 0 / 0 |
| `openconnect-drawer/container-solid` | 71985.27992 | +0.250241 | 175 → 175 | 71987.37971 → 71987.37971 | 10728 → 10728 | 0 / 0 |
| `gridfinity-capture-bin/default` | 176978.03787 | +1.3891e-05 | 229 → 229 | 176870.88764 → 176870.71881 | 26864 → 16616 | 1.92e-13 / 0 |
| `gridfinity-capture-bin/deep` | 247272.96555 | +2.1728e-05 | 229 → 229 | 247086.82613 → 247086.65731 | 26864 → 16616 | 1.92e-13 / 0 |
| `gridfinity-capture-bin/wide` | 417254.75472 | +3.77715e-05 | 327 → 327 | 417119.74201 → 417119.40468 | 44696 → 24200 | 1.8e-12 / 0 |
| `littletikes-dream-machine-cartridge-holder/default` | 155023.64226 | +1.07154e-05 | 1139 → 1139 | 155025.83092 → 155025.83092 | 32528 → 32528 | 8.28e-13 / 0 |
| `littletikes-dream-machine-cartridge-holder/full_holder` | 1338807.88924 | +0.000446305 | 10015 → 10015 | 1338819.71909 → 1338819.71909 | 215648 → 215648 | 1.16e-10 / 0 |
| `littletikes-dream-machine-cartridge-holder/blank_back` | 140072.44606 | +1.07148e-05 | 75 → 75 | 140074.69124 → 140074.69124 | 11152 → 11152 | 8.28e-13 / 0 |
| `littletikes-dream-machine-cartridge-holder/openconnect` | 132563.52680 | +1.07143e-05 | 323 → 323 | 132565.77003 → 132565.77003 | 18374 → 18374 | 8.28e-13 / 0 |
| `holder-tombstone-sign/default` | 535359.69818 | AttributeError: module 'OCP.OCP.TopoDS.TopoDS' has no attribute 'Vertex_s' | 2911 → unavailable | 535283.08928 → unavailable | 391066 → unavailable | unavailable |
| `holder-tombstone-sign/one-ams` | 532751.16306 | AttributeError: module 'OCP.OCP.TopoDS.TopoDS' has no attribute 'Vertex_s' | 3534 → unavailable | 532674.55527 → unavailable | 393306 → unavailable | unavailable |
| `holder-tombstone-sign/two-colour` | 532751.16306 | AttributeError: module 'OCP.OCP.TopoDS.TopoDS' has no attribute 'Vertex_s' | 3534 → unavailable | 532674.55527 → unavailable | 393306 → unavailable | unavailable |
| `holder-tombstone-sign/pinned` | 533533.50837 | AttributeError: module 'OCP.OCP.TopoDS.TopoDS' has no attribute 'Vertex_s' | 2923 → unavailable | 533457.45674 → unavailable | 392278 → unavailable | unavailable |
| `holder-tombstone-sign/small` | 287067.89916 | AttributeError: module 'OCP.OCP.TopoDS.TopoDS' has no attribute 'Vertex_s' | 2911 → unavailable | 287033.34784 → unavailable | 424948 → unavailable | unavailable |
| `holder-tombstone-stake/default` | 96822.97478 | -2.3179e-05 | 69 → 69 | 96822.99258 → 96822.99262 | 1968 → 1968 | 5.33e-15 / 0 |
| `holder-tombstone-stake/long` | 103216.57478 | -2.56373e-05 | 69 → 69 | 103216.59258 → 103216.59258 | 1968 → 1968 | 8.88e-15 / 0 |
| `holder-tombstone-stake/cross-bar` | 147770.25556 | -1.93162e-05 | 107 → 107 | 147770.17301 → 147770.17305 | 3612 → 3612 | 5.54e-13 / 0 |
| `holder-tombstone-stake/pinned` | 96699.05479 | -2.48793e-05 | 77 → 77 | 96699.11014 → 96699.11018 | 2760 → 2760 | 5.33e-15 / 0 |
| `underware-i-channel/default` | 16295.06000 | +0 | 104 → 104 | 16295.06026 → 16295.06026 | 364 → 364 | 0 / 0 |
| `underware-i-channel/wide-tall` | 18513.03600 | +0 | 68 → 68 | 18513.03648 → 18513.03648 | 236 → 236 | 0 / 0 |
| `underware-i-channel/cutouts` | 15012.52341 | +0 | 128 → 128 | 15012.68418 → 15012.68418 | 1516 → 1516 | 0 / 0 |
| `underware-i-channel/label` | 16242.40953 | +0 | 227 → 227 | 16242.41697 → 16242.41697 | 4994 → 4994 | 0 / 0 |
| `underware-transition/widen-1-to-2` | 11983.62400 | +0 | 58 → 58 | 11983.62442 → 11983.62442 | 196 → 196 | 0 / 0 |
| `underware-transition/raise-22-to-34` | 11793.03600 | +0 | 80 → 80 | 11793.03601 → 11793.03601 | 268 → 268 | 0 / 0 |
| `underware-transition/bridge` | 13884.42400 | +0 | 74 → 74 | 13884.42375 → 13884.42375 | 252 → 252 | 0 / 0 |
| `underware-l/L` | 9001.62168 | +0 | 65 → 65 | 9000.51973 → 9000.51973 | 1304 → 1304 | 0 / 0 |
| `underware-l/L-mirrored` | 9001.62168 | +0 | 65 → 65 | 9000.51973 → 9000.51973 | 1304 → 1304 | 0 / 0 |
| `underware-l/L-tall` | 34222.93005 | +0 | 101 → 101 | 34218.93453 → 34218.93453 | 1352 → 1352 | 0 / 0 |
| `underware-t/T` | 12389.19298 | +0 | 97 → 97 | 12389.13200 → 12389.13200 | 1428 → 1428 | 0 / 0 |
| `underware-t/T-tall` | 31054.42721 | +0 | 151 → 151 | 31054.33600 → 31054.33600 | 1620 → 1620 | 0 / 0 |
| `underware-x/X` | 15001.34997 | +0 | 126 → 126 | 15001.22784 → 15001.22784 | 2620 → 2620 | 0 / 0 |
| `underware-x/X-tall` | 39093.79441 | +0 | 198 → 198 | 39093.61182 → 39093.61182 | 2876 → 2876 | 0 / 0 |
| `underware-text-label/label-1x5` | 8092.52133 | +0 | 110 → 110 | 8092.52131 → 8092.52131 | 340 → 340 | 0 / 0 |
| `underware-text-label/label-2x3` | 9553.37733 | +0 | 70 → 70 | 9553.37738 → 9553.37738 | 212 → 212 | 0 / 0 |
| `underware-path-channel/S` | 15829.44387 | +0 | 66 → 66 | 15831.40522 → 15831.40522 | 3778 → 3778 | 0 / 0 |
| `underware-path-channel/S-wide` | 20473.33488 | +0 | 66 → 66 | 20472.53129 → 20472.53129 | 3486 → 3486 | 0 / 0 |
| `underware-path-channel/diagonal` | 15279.40198 | +0 | 74 → 74 | 15279.15775 → 15279.15775 | 1212 → 1212 | 0 / 0 |
| `underware-path-channel/diagonal-wide-tall` | 31384.70396 | +0 | 74 → 74 | 31384.24670 → 31384.24670 | 636 → 636 | 0 / 0 |
| `underware-mitre/mitre` | 9655.76589 | +0 | 68 → 68 | 9654.62648 → 9654.62648 | 1212 → 1212 | 0 / 0 |
| `underware-mitre/mitre-r1` | 14546.59733 | +0 | 68 → 68 | 14544.29227 → 14544.29227 | 1128 → 1128 | 0 / 0 |

</details>

Maximum paired centre-coordinate delta: 0.000197450286 mm. Solid counts changed in 0 paired cases. Bounds include both raw model coordinates and the declared print frame. Smoke registrations have no app bake.

All 63 paired configurations retain face and solid counts; all 125 containment
samples match in each. Maximum raw/print bounds drift is `1e-7` mm. Seven
app presets have different STL triangle counts: all four gridfinity-shelf
presets and all three capture-bin presets. Their maximum absolute STL-volume
delta is 0.337339 mm³ (wide capture bin); maximum relative delta is
0.000551% (default shelf). These are measured export differences despite
stable BREP topology, not a claim of byte-identical geometry.

All 60 paired app GLBs retain identical materials, scenes and node
names/transforms/child structure, including the exporter root rotation.

The stored face-centre queries provide another placement diagnostic: the
maximum bidirectional nearest-centre distance is 0.025206 mm for the drawer
`organiser`, and 0.002176 mm for `container` and `container-solid`; every
other paired case is below 0.000023 mm. `Face.center()` uses surface mass
properties for planar faces and UV midpoints for curved faces in both
installed versions, so these query results are not fixed physical landmarks.
They require investigation alongside the drawer BREP-volume drift before
claiming exact surface equivalence, even though the drawer STL volumes and
sampled containment match.

## (c) Bake hashes and generic 3MF

The normal all-presets bake aborts at the first tombstone-sign preset. The
60 successful candidate app bakes in this report are independent per-preset
probes, not a successful complete production bake. All five sign generic
3MFs are unavailable in the candidate; the four generic files that can be
compared are tabulated below. An independent check of the 68 candidate STL
files (including per-colour files) confirms that every file is watertight
and has positive volume, reproducing those production-bake assertions
despite the early abort of the normal all-presets command.

Every paired GLB also changes its `asset.generator` from Open CASCADE Technology 7.9 to 8.0. Label-card GLB accessor/buffer/mesh encoding changes as well; stable materials and transforms alone do not imply identical binary mesh layout.

All eight baseline label-card hashes reproduce the committed pins. Six candidate hashes change; the inlay/text STLs remain byte-identical. Old hashes below are abbreviated; the full originals remain in `tests/test_presets_bake.py::LABEL_CARD_BAKE_SHA256`.

| File | Old SHA-256 prefix | Candidate SHA-256 | Classification |
| --- | --- | --- | --- |
| `inlaid-base.stl` | `b7b7a2b6de63` | `652bfe7302ea46d5f1f27799b87fa0bc3b938c3545725bb39e878bb14ba559f9` | export byte drift; review before re-pin |
| `inlaid-inlay.stl` | `4b93c5af55cb` | `4b93c5af55cb64c06988f0d92ff410bc900b8ab25ce6f4d65ebe49ada54703b8` | unchanged |
| `inlaid.3mf` | `cbd8d53e918c` | `31285f50ca71ee756992ed1244ba8072bea19ae9c2ddc4b1b8b2066cb9fc65a2` | export byte drift; review before re-pin |
| `inlaid.glb` | `f41f6ed78d27` | `0025d4ef06338150637d21390651837d7ab74fedb54589eae77b6c5db69f7fcb` | export byte drift; review before re-pin |
| `raised-base.stl` | `b1d00fc5feb7` | `0ec892480b7db346ab2d66b96e604d5e80c8b46afbd71b86815d8e22faf8fe25` | export byte drift; review before re-pin |
| `raised-text.stl` | `5b59e46e2dc8` | `5b59e46e2dc89e552bc24141432efec9330975e99e08ce45bf24e342bb722517` | unchanged |
| `raised.3mf` | `c4f858b69b89` | `e376c6666dc37902e9b91d0f618ae3c939b463d89ee73e322982c5bc997c9d3c` | export byte drift; review before re-pin |
| `raised.glb` | `803ddae6a192` | `1e01b6e0719db5417d69fb03a2a40a7a510768d826c1e7541fc4ca8635ce143b` | export byte drift; review before re-pin |

Both available generic label-card 3MFs differ. Only `3D/3dmodel.model` changes; its XML is identical after removing the mesh elements. Thus materials, names, UUIDs, component/build structure and all other ZIP entries match. Base meshes have identical vertex counts and vertex sets rounded to 0.001 mm, but different triangle-coordinate sets. The inlay/text triangle-coordinate sets match. Together with the geometry table, this supports tessellation drift rather than a changed label-card design; it does not authorize blindly re-pinning every model.

| Generic 3MF | Mesh vertices / triangles, baseline → candidate | Bytes identical? |
| --- | --- | --- |
| `holder-label-card/inlaid.3mf` | object 3: 4399/8794 → 4399/8794; object 4: 3631/7234 → 3631/7234 | No |
| `holder-label-card/raised.3mf` | object 3: 768/1532 → 768/1532; object 4: 3632/7236 → 3632/7236 | No |
| `underware-text-label/label-2x3.3mf` | object 3: 2547/5090 → 2547/5090; object 4: 2439/4866 → 2439/4866 | Yes |
| `underware-text-label/label-1x5.3mf` | object 3: 2611/5218 → 2611/5218; object 4: 2439/4866 → 2439/4866 | Yes |

A second independent candidate bake of all four buildable multi-colour presets reproduced all 28 file hashes exactly. This checks repeatability within the measured environment, not portability across architectures or future dependency versions.

The following counts cover production files from the per-preset bake; absent candidate files are failures, not unchanged files.

| Format | Baseline files | Candidate files | Paired identical | Paired changed | Missing candidate |
| --- | ---: | ---: | ---: | ---: | ---: |
| .stl | 103 | 68 | 34 | 34 | 35 |
| .glb | 65 | 60 | 0 | 60 | 5 |
| .png | 65 | 60 | 42 | 18 | 5 |
| .3mf | 18 | 8 | 4 | 4 | 10 |

## (d) Audit baseline drift

Compared with the published main artifacts: 686 candidate audit outcomes versus 725 baseline outcomes, and 468 paired measurements out of 477 baseline measurements. Comparisons use `(nodeid, name)` and absolute numeric tolerance `1e-6` in each field’s native units; strings, booleans and inventories must match. Missing measurements are reported separately and never treated as a pass.

| Test module | Paired / baseline measurements | Rows differing above tolerance | Candidate failed audit outcomes |
| --- | ---: | ---: | ---: |
| `tests/test_cartridge_holder.py` | 36 / 36 | 0 | 0 |
| `tests/test_gridfinity_capture_bin.py` | 19 / 19 | 18 | 0 |
| `tests/test_gridfinity_shelf.py` | 28 / 28 | 24 | 0 |
| `tests/test_openconnect_drawer.py` | 64 / 64 | 0 | 0 |
| `tests/test_openconnect_drawer_container.py` | 77 / 77 | 63 | 0 |
| `tests/test_openconnect_plate.py` | 24 / 24 | 0 | 0 |
| `tests/test_print_audit.py` | 3 / 7 | 0 | 5 |
| `tests/test_tombstone_sign.py` | 0 / 5 | 0 | 0 |
| `tests/test_underware.py` | 38 / 38 | 0 | 0 |
| `tests/test_underware_junctions.py` | 52 / 52 | 0 | 0 |
| `tests/test_underware_path_channels.py` | 62 / 62 | 0 | 0 |
| `tests/test_underware_text_label.py` | 17 / 17 | 0 | 0 |
| `tests/test_underware_transition.py` | 48 / 48 | 0 | 0 |

Changed numeric fields across paired measurements:

| Field | Changed rows | Maximum absolute delta | Case at maximum |
| --- | ---: | ---: | --- |
| `.vol_cm3` | 63 | 0.00186703731 | `tests/test_openconnect_drawer_container.py::test_endpoint_audit_and_edges[vertical_grids=8]` |
| `.volume` | 42 | 0.000411166809 | `tests/test_gridfinity_capture_bin.py::test_endpoint_audit_edges_and_containment[6x6]` |

Nonnumeric field changes: 0.

All differing paired measurements are volume fields (`volume` in mm³; `vol_cm3` in cm³). Recorded wall, overhang, bridge, edge, mount and inventory fields match within the stated tolerance. This applies to available rows only; failed or uncollected tombstone cases have no corresponding measurement.

The largest container volume delta is 1.867037 mm³ (0.001084%) at `tests/test_openconnect_drawer_container.py::test_endpoint_audit_and_edges[vertical_grids=8]`. A numerical-query change is plausible, but this report does not establish exact surface equivalence.

Missing baseline measurements, grouped by module and candidate outcome:

| Module | Candidate outcome | Missing measurement rows |
| --- | --- | ---: |
| `tests/test_print_audit.py` | failed | 4 |
| `tests/test_tombstone_sign.py` | not collected/completed | 5 |

10 collected audit outcomes change from pass to fail; all fail during tombstone construction with `TopoDS.Vertex_s`. The other 39 baseline audit cases are in the uncollectable tombstone-sign module. The existing smoke-tile wall expected failure is unchanged.

Changed audit outcomes:

| Test | Baseline | Candidate |
| --- | --- | --- |
| `tests/test_audit_cache.py::test_every_manifest_preset_keys_identically_across_processes` | passed | failed |
| `tests/test_presets_bake.py::test_presets_only_bakes_every_app_listed_preset` | passed | failed |
| `tests/test_print_audit.py::test_audit_full_only_presets_fit_the_bed[holder_tombstone_sign-one-ams]` | passed | failed |
| `tests/test_print_audit.py::test_audit_full_only_presets_fit_the_bed[holder_tombstone_sign-pinned]` | passed | failed |
| `tests/test_print_audit.py::test_audit_full_only_presets_fit_the_bed[holder_tombstone_sign-small]` | passed | failed |
| `tests/test_print_audit.py::test_audit_full_only_presets_fit_the_bed[holder_tombstone_sign-two-colour]` | passed | failed |
| `tests/test_print_audit.py::test_model_print_audit[holder_tombstone_sign]` | passed | failed |
| `tests/test_tombstone_stake.py::test_tenons_fill_the_real_pockets_with_the_contract_clearance[6.0-False]` | passed | failed |
| `tests/test_tombstone_stake.py::test_tenons_fill_the_real_pockets_with_the_contract_clearance[8.0-False]` | passed | failed |
| `tests/test_tombstone_stake.py::test_tenons_fill_the_real_pockets_with_the_contract_clearance[8.0-True]` | passed | failed |

## (e) Suite results and runtime

The unchanged baseline completes with **2,507 passed, 29 skipped and one expected failure**. The optional capture group and serial budgets are measured separately below. The candidate cannot complete an ordinary full-suite invocation: collection fails after 8.90 s. Continuing past that error and finishing every collectable regular case gives the diagnostic results below.

| Run | Result | Elapsed seconds (JUnit) |
| --- | --- | ---: |
| Baseline full suite, four workers | 2,507 passed; 29 skipped; 1 xfailed | 4142.77 |
| Candidate diagnostic, both disjoint stages | 2,386 passed; 25 failed; 24 errors; 29 skipped; 1 xfailed | 7408.02 total |
| Candidate Git-inventory verification | All three scratch-context failures pass with the correct index | 2.47 |
| Baseline budget supplement | 23 passed; 0 failed; 0 errors; 0 skipped | 116.87 |
| Baseline capture supplement | 89 passed; 0 failed; 0 errors; 1 skipped | 82.21 |
| Candidate budget supplement | 22 passed; 1 failed; 0 errors; 0 skipped | 137.48 |
| Candidate capture supplement | 88 passed; 0 failed; 0 errors; 2 skipped | 119.27 |
| Candidate local-fixture rerun | 1 passed | 1.37 |

Excluding the three verified Git-context failures, the candidate has **22 genuine failed tests and 24 errors**. The errors include one collection failure and 23 fixture-setup failures. The latter all fail while constructing the same tombstone plate. The missing 73 tombstone-sign tests are not counted as passes or independent assertion failures.

| Test module | Failures | Errors | Cause |
| --- | ---: | ---: | --- |
| `tests.test_tombstone_sign (collection)` | 0 | 1 | `TopTools_ListOfShape` |
| `tests.test_audit_cache` | 1 | 0 | `TopoDS.Vertex_s` |
| `tests.test_bd_render_service` | 1 | 0 | `TopoDS.Vertex_s` |
| `tests.test_multibuild` | 7 | 0 | `class signature defaults` |
| `tests.test_presets_bake` | 1 | 0 | `TopoDS.Vertex_s` |
| `tests.test_presets_bake` | 1 | 0 | `label-card byte pins` |
| `tests.test_print_audit` | 5 | 0 | `TopoDS.Vertex_s` |
| `tests.test_review_sheet` | 0 | 23 | `TopoDS.Vertex_s` |
| `tests.test_tombstone_stake` | 3 | 0 | `TopoDS.Vertex_s` |
| `tests.test_toolchain` | 1 | 0 | `TopoDS.Vertex_s` |
| `tests.test_underware_text_label` | 2 | 0 | `Vector.to_tuple` |

The serial candidate budget supplement exercises the same known tombstone construction failure; it is not an additional root cause. Capture tests use the frozen optional group (`opencv-python-headless==5.0.0.93`) in both environments, installed only after the full diagnostics and budgets. No lock was regenerated for those supplements. Both capture runs skip one case awaiting a real photo. The archived candidate additionally skips `test_capture_sheet.py::test_real_sheet_flat_item` because `tests/fixtures/capture/real/sheet/card.png` is local-only. Copying the existing baseline fixture into the scratch tree and rerunning only that test passes; effective capture coverage is 89 passes and the same one unavailable-photo skip on each version. The fixture is not published by this report.

**A passing full-suite runtime delta is not available.** The candidate has missing collection coverage, early failures and a two-stage scheduler; the baseline has pre-existing audit-cache entries (906 hits, 10 misses, 10 cache-disabled calls). The local full suites also overlapped with each other/probes on a shared host. Their observed elapsed times must not be converted into an upgrade regression or speedup percentage. The first candidate stage takes 5,440.57 s; its unfinished-case stage takes 1967.45 s. The serial budget comparison is narrower: each case disables the audit cache and measures `time.process_time()` for the model build plus audit. It is not a full-suite benchmark.

For the 22 paired cold audit measurements, total CPU time is 127.896 → 143.270 s (+12.02%). This is one sample per model, in baseline-then-candidate order; no repeated-run uncertainty estimate is available.

<details>
<summary>Paired serial audit CPU timings</summary>

| Model | Baseline CPU s | Candidate CPU s | Delta |
| --- | ---: | ---: | ---: |
| `gridfinity_capture_bin` | 5.216 | 3.602 | -30.94% |
| `holder_bottle_500ml` | 1.806 | 1.192 | -34.00% |
| `holder_cup_lid` | 0.79 | 0.66 | -16.46% |
| `holder_label_card` | 4.327 | 2.779 | -35.78% |
| `holder_spool_cradle` | 23.398 | 18.044 | -22.88% |
| `holder_spray_can` | 1.797 | 1.19 | -33.78% |
| `holder_tombstone_sign` | 44.634 | construction failed | unavailable |
| `holder_tombstone_stake` | 0.533 | 0.479 | -10.13% |
| `label_demo` | 2.152 | 1.001 | -53.49% |
| `littletikes_dream_machine_cartridge_holder` | 9.036 | 8.088 | -10.49% |
| `openconnect_drawer` | 37.112 | 60.071 | +61.86% |
| `openconnect_gridfinity_shelf` | 17.691 | 27.134 | +53.38% |
| `openconnect_plate` | 6.37 | 5.276 | -17.17% |
| `smoke_multiconnect_roundhead` | 0.041 | 0.032 | -21.95% |
| `smoke_opengrid_tile_1x1` | 0.71 | 0.557 | -21.55% |
| `underware_i_channel` | 1.273 | 1.078 | -15.32% |
| `underware_l` | 1.413 | 1.201 | -15.00% |
| `underware_mitre` | 1.162 | 0.907 | -21.94% |
| `underware_path_channel` | 2.983 | 2.622 | -12.10% |
| `underware_t` | 1.798 | 1.406 | -21.80% |
| `underware_text_label` | 5.249 | 3.544 | -32.48% |
| `underware_transition` | 0.573 | 0.512 | -10.65% |
| `underware_x` | 2.466 | 1.895 | -23.15% |

</details>

For context only, the published baseline CI run uses Ubuntu runner image `20261012.334.1`. Pytest elapsed times are: fast 923.91 s (1,871 passed, 4 skipped); serial budget 109.09 s (23 passed); audit 1,563.36 s (488 passed, 5 skipped, 1 xfailed); full shards 1–6: 616.02, 419.51, 614.94, 460.27, 635.47 and 231.32 s (69, 19, 18, 57, 56 and 16 passed respectively). These are separate parallel CI jobs, not a local elapsed-time baseline.

Three alternating fresh-process import probes give median cumulative Python `-X importtime` values of 3.815989 s → 2.980107 s. Whole-process wall samples are baseline 9.333724/5.470223/4.556222 s and candidate 5.380761/4.112381/4.007074 s. They are illustrative shared-host samples, not evidence of a reliable import speedup.

## Ordered migration work

1. Migrate the OCP collection import in the tombstone test to
   `OCP.collections.List_TopoDS_Shape`, and the model's `TopoDS.Vertex_s`
   call to `TopoDS.Vertex`. A candidate-environment smoke check confirms
   that the cast works and a `BRepAlgoAPI_Common` accepts the new list with
   `Append`, `SetArguments` and `SetTools`. This does not replace rerunning
   tombstone geometry, overlap, edge and print-audit contracts.
2. Replace both `Vector.to_tuple()` calls in the text-label test with
   `tuple(vector)`. Read pinned Multibuild defaults from the actual constructor
   signatures (`cls.__init__`), then rerun the slot/channel profile and
   clearance contracts; do not replace library-derived values with copied
   constants. Run the full suite without collection-error continuation.
   Resolve any additional semantic failures listed in the measured results;
   do not relax geometry/printability assertions to accommodate the upgrade.
3. Rebuild the failed presets and obtain every currently missing audit row.
   Compare their placement, topology, production print audit and exposed-edge
   results at endpoints/corners against this same main baseline. Cache-key
   stability must be tested after geometry construction works. Investigate
   the drawer volume/face-centre query drift rather than assuming that
   unchanged face counts prove surface equivalence.
4. Review the label-card triangulation changes, repeat the bake to establish
   deterministic bytes, then deliberately re-pin changed hashes in a future
   upgrade PR. The existing test explicitly permits deliberate OCCT/lib3mf
   re-pins. Unchanged text/inlay hashes need no re-pin. Generic 3MF export
   must retain its one-object structure and part/filament assignments.
5. Rerun matched cold-cache CI jobs on the same runner configuration, including
   the serial budget tests and all six audit-full shards. Only comparable,
   passing suites can support a runtime regression/speedup claim. Obtain
   operator approval for the dependency upgrade after those gates pass.

## Reproduction

Run from the repository root. The scratch checkout must contain the whole
tracked repo and its Git index: service tests read `services/bd-render/`
outside `build123d/`, and provenance tests query tracked files.
Do not upgrade the working tree's lock. The commands below use the measured
commit explicitly; later main revisions change the test/preset population.

```sh
mkdir -p .tmp-upgrade-spike
git clone --shared . .tmp-upgrade-spike/candidate
git -C .tmp-upgrade-spike/candidate checkout --detach \
  15d441e439ad834b4dc347fed35ad933bc2ad4ab
uv sync --project .tmp-upgrade-spike/candidate/build123d \
  --upgrade-package build123d==0.13.0
uv pip list --python .tmp-upgrade-spike/candidate/build123d/.venv/bin/python
gh run download 39231607959 -p 'bd123-audit-rows*' \
  -D .tmp-upgrade-spike/baseline-rows

cd .tmp-upgrade-spike/candidate/build123d
.venv/bin/python -m pytest tests/ -q --tb=short
# The preceding command stops during collection. Diagnostic coverage:
BD_AUDIT_OUT="$PWD/../../candidate-rows/rows.jsonl" \
  .venv/bin/python -m pytest tests/ -q -n 4 --dist load \
  --maxschedchunk=1 --continue-on-collection-errors --tb=short \
  --junitxml=../../candidate.xml
# Run budgets serially, after other local CAD processes finish.
.venv/bin/python -m pytest tests/test_print_audit.py -q -s -n 0 \
  -m 'budget and not upstream' --tb=short
# The default group skips these optional capture modules.
uv sync --frozen --group capture
.venv/bin/python -m pytest tests/test_capture_baseline.py \
  tests/test_capture_dark.py tests/test_capture_sheet.py \
  tests/test_capture_spike.py -q --tb=short
.venv/bin/python scripts/export.py --presets-only ../../candidate-bake
.venv/bin/python -X importtime -c 'import build123d'
```

The diagnostic full selection already includes `audit` and `audit_full`;
it does not need a duplicate sweep. To run only those tiers, use
`-m 'audit and not upstream'`. Every explicit marker expression must retain
`not upstream`; private-reference parity tests are outside this offline
comparison. The normal `--run-slow` opt-in remains off, matching the default
suite and CI. Per-preset and import probes are reproduced below.

For a baseline rerun, check out the same SHA in a second scratch directory,
run `uv sync --frozen` there, and use the same probe and Python commands.
The local baseline gate for this report was
`uv run pytest tests/ -q -n 4 --dist load --tb=short --junitxml=...`,
from the unchanged working-tree `build123d/` directory. The published CI
audit comparison remains the authority for audit drift.

<details>
<summary>Per-preset geometry and production-bake probe</summary>

Save this as `probe.py` outside the source tree, then invoke it with each
virtual environment's Python: `python probe.py PATH_TO_BUILD123D OUTPUT_DIR`.
The registry override affects only this process and only the export list;
each model's build and production exporter run unchanged. The final JSONL
row is written even when construction or export raises.

```python
import sys, json, time, traceback, hashlib
from pathlib import Path
root, out = map(lambda s: Path(s).resolve(), sys.argv[1:3])
sys.path.insert(0, str(root))
from dataclasses import replace
from holders.registry import all_models, in_print_frame
import scripts.export as export
import trimesh
out.mkdir(parents=True, exist_ok=True)
rows = out/'metrics.jsonl'
for spec in all_models():
    presets = spec.presets or [None]
    for preset in presets:
        key = preset.id if preset else 'defaults'
        row = dict(model=spec.slug, preset=key, smoke=spec.is_smoke)
        start=time.perf_counter()
        try:
            values=spec.resolve_values(preset.values if preset else {})
            raw=spec.build(values)
            part=in_print_frame(spec, values, raw)
            box=part.bounding_box()
            row.update(volume=part.volume, faces=len(part.faces()), solids=len(part.solids()),
                       bbox=[list(box.min),list(box.max)], center=list(part.center()),
                       raw_bbox=[list(raw.bounding_box().min),list(raw.bounding_box().max)],
                       face_centers=sorted([list(f.center()) for f in part.faces()]))
            points=[tuple(list(box.min)[i]+(list(box.max)[i]-list(box.min)[i])*t[i] for i in range(3))
                    for t in __import__('itertools').product([.1,.3,.5,.7,.9], repeat=3)]
            row['occupancy']=[part.is_inside(p) for p in points]
            if not spec.is_smoke:
                # Run the production bake independently per preset so one error
                # cannot hide all later presets. No model/source modifications.
                export.all_models=lambda: [replace(spec, presets=(preset,))]
                row['bake_returncode']=export.export_presets_only(out/'bake')
                mesh=trimesh.load_mesh(out/'bake'/spec.slug/f'{key}.stl')
                row.update(stl_volume=float(mesh.volume), triangles=len(mesh.faces), stl_bounds=mesh.bounds.tolist())
        except Exception as error:
            row.update(error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
        row['duration_s']=time.perf_counter()-start
        with rows.open('a') as f: f.write(json.dumps(row)+'\n')
        print(row['model'],row['preset'],row.get('error','ok'),flush=True)
files={str(p.relative_to(out/'bake')):hashlib.sha256(p.read_bytes()).hexdigest()
       for p in (out/'bake').rglob('*') if p.is_file()}
(out/'hashes.json').write_text(json.dumps(files,indent=2)+'\n')
```

Compare `metrics.jsonl` by `(model, preset)` and `hashes.json` by relative
filename. The placement table uses the maximum absolute difference across
all six raw and print-frame bounds coordinates. Audit rows are joined by
`(nodeid, name)`; compare numeric fields with absolute tolerance `1e-6` and
all booleans/strings/inventory counts exactly. Missing rows stay missing.
For 3MF payload analysis, compare ZIP members, then compare each XML mesh's
vertices and triangle coordinates independently of index ordering.

</details>

<details>
<summary>Candidate uv pip list before the optional capture supplement</summary>

```text
Package                 Version
----------------------- ---------
annotated-types         0.8.0
anytree                 2.13.0
asttokens               3.0.2
bd-materials            0.2.4
build123d               0.13.0
cadquery-ocp-novtk      8.0.1.1.0
cadquery-ocp-proxy      8.0.1.1.0
certifi                 2026.7.22
charset-normalizer      3.5.1
dataclasses-json        0.6.7
deprecated              3.0.0
execnet                 2.1.2
executing               2.2.1
ezdxf                   1.4.4
fonttools               4.63.0
idna                    3.19
iniconfig               2.3.0
ipython                 9.17.0
ipython-pygments-lexers 1.1.1
jedi                    0.20.0
joblib                  1.5.3
lib3mf                  2.5.0
makerrepo               0.5.6
mapbox-earcut           2.1.0
marshmallow             3.26.2
matplotlib-inline       0.2.2
mpmath                  1.3.0
mypy-extensions         1.1.0
narwhals                2.25.0
networkx                3.7
numpy                   2.5.2
ocp-gordon              0.3.1
ocpsvg                  0.7.0
opengrid                0.1.0
packaging               26.3
parso                   0.8.7
pexpect                 4.9.0
pillow                  12.3.0
platformdirs            4.13.5
pluggy                  1.6.0
prompt-toolkit          3.0.53
psutil                  7.2.2
ptyprocess              0.7.0
pure-eval               0.2.3
pydantic                2.13.5
pydantic-core           2.46.5
pygltflib               1.16.5
pygments                2.21.0
pyparsing               3.3.2
pytest                  9.1.1
pytest-datadir          1.8.0
pytest-regressions      2.11.0
pytest-split            0.11.0
pytest-xdist            3.8.0
pyyaml                  6.0.3
requests                2.34.2
rtree                   1.4.1
scikit-learn            1.9.0
scipy                   1.18.1
segno                   1.6.6
shapely                 2.1.2
stack-data              0.6.3
svgelements             1.9.6
svgpathtools            1.7.4
svgwrite                1.4.3
sympy                   1.14.0
threadpoolctl           3.6.0
threejs-materials       1.2.5
traitlets               5.16.1
trianglesolver          1.2
trimesh                 5.0.0
typing-extensions       4.16.0
typing-inspect          0.9.0
typing-inspection       0.4.4
urllib3                 2.7.0
venusian                3.1.1
wcwidth                 0.8.3
webcolors               24.8.0
wrapt                   2.5.1
```

</details>
