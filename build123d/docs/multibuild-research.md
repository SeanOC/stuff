# Multibuild mounting research — pst-frt6

Research date: 2026-09-28. Scope: library groundwork for the wall spool cradle;
no geometry implemented. **Recommend a thin `multibuild` adapter around the
pinned Multiconnect cutters, plus separately validated board primitives.**

**Evidence:** [V] independently checked source arithmetic/implementation;
[C] cited author/specification claim, not independently measured hardware;
[U] unresolved, including where the inspected source does not establish a fact.
A [V] code value does **not** certify official-part or printed compatibility.
Dimensions below are mm. Source keys link to URLs; locators identify exact
sections or source lines. No official STEP was measured in this research.

## 1. System, names, catalogue and publication

[C] MultiBuild is the umbrella; MultiBoard is its board subsystem, with
MultiBin alongside it ([Core], headings). Jonathan/Keep Making is credited
as Multiboard's designer ([SCAD README], “Credits”). Current names are
**Fix-Points** (formerly Multipoints) and **Rails** (formerly Multipoint Rails)
([Core], “Multipoint”, lines 231–245). Keep legacy names in search metadata.

[C] Relevant core catalogue: tiles, snaps, bolt-locked/friction inserts,
Peg Click, small/mid/large threads, Fix-Points and Rails ([Core], §§1–5,11–12).
“Multibolt”/“T-thread” is not a sufficient thread identifier: the older
[Knowledge Hub](https://www.multiboard.io/knowledge-hub/) “Bolts” section
calls them Bolts/T-Bolts; the current catalogue separates thread sizes.
[U] No universal T-thread specification was established. Select an exact part.
Multiconnect is David D's separate connector family, also used by openGrid
([openGrid], description/model origin); it is not another name for Fix-Point.
Catalogue dimensions established here are in §§2–3; missing profiles remain
explicitly unresolved rather than being filled from similarly named parts.

[C] Publication on stuff.seanoc.com: the [full licence], dated
2025-12-19, §3.3 permits substantially changed remixes; original files may
not be redistributed. Incorporated MultiBuild material retains its terms;
the text encourages applying them to the whole remix. §4 requires preserving
notices, avoiding implied endorsement and attributing underlying designs
where practicable. Publish the holder's contribution with source credit and
licence link; do not bundle original tiles/remix assets or assume the repo's
software licence covers them. Commercial printed sales require the applicable
subscription (§3.2); distributing design files is a separate permission.
The [licence page] says the [Community Promise] prevails on conflicts; the
promise does not mean the designs are presently CC0. [U] Whether a new
independent compatibility primitive is a derivative needs resolution for the
actual implementation. Multiconnect assets require their own per-file licence
check; the MIT Python library does not establish rights in every referenced CAD asset.

## 2. Board dimensions and seam rules

| Fact and status | Value / limit | Exact evidence |
| --- | --- | --- |
| [C] Grid pitch | 25 | [Core], “Measurement System” and §1, lines 29,42 |
| [C] Board thickness | 6.4, from an author's official-remix measurements | [SCAD], `multiboard_base.scad` L56–61; cited original [tile remix](https://than.gs/m/994681) uploaded 2024-01-19 |
| [C] Large-hole envelope | Octagon: across flats 23.4 at mouths, 21.4 centrally; central band height 2.4 | [SCAD] L68–83,218–224,270–280; these are not circular thread diameters |
| [C] Large-hole thread | Trapezoidal helix: outer Ø22.6, inner Ø21.4; axial widths 0.5 outer / 1.583 inner; pitch 2.5 | [SCAD] L85–94; `multihole_threads` L228–233 extends helix past the 6.4 board before boolean operations |
| [U] Production thread fit | Above is a reconstructed **female hole**, not a qualified male Multibolt/T-bolt spec. Starts, flank rounding, lead-in, male fit allowance and current official tolerances remain unverified | [SCAD] L85–94,285 onward; [Core] §5 gives compatibility, not a thread drawing |
| [C] Small-hole envelope | Mouth Ø7.5, throat Ø6, central band 2.9; threaded rather than a plain conical bore | [SCAD] L96–104,237–265 |
| [V] Small-hole taper depth | (6.4−2.9)/2 = **1.75** at each face; throat from depth 1.75 to 4.65 | Arithmetic from [SCAD] L270–280; [U] physical agreement pending STEP/print check |
| [C] Small-hole thread | Pitch 3, outer Ø7, inner Ø6; axial widths 0.77 / 2.5 | [SCAD] L100–104,257–265 |
| [V] Grid phase / edges | Large centers `(25i+12.5,25j+12.5)`; small centers `(25i+25,25j+25)` where present. First large center is 12.5 from the nominal cell boundary, not every scalloped outer edge | [SCAD] L135–162,167–193; arithmetic on source coordinates |
| [C] Tile edge variants | Core has projecting peg-hole teeth on two sides; side on one; corner on neither. Tooth-side bounding size is cell count ×25 +8 | [SCAD README] “Usage” / “Tile Stack Sizing”; not an 8 mm gap between tiles |
| [C] Joining | Official installation uses Dual Snaps; offset snap mounts give 6.25 wall offset | [Mounting], “Installation Steps”, L46–50; [Core] §2.2 L88 |
| [U] Seam collision / clearances | Nominal lattice continuity does not prove clearance past snap heads, pillars, teeth or a misaligned installed seam. No official global fit allowance found | [Mounting] steps/images and [Core] connection descriptions; need installed hardware envelope and chosen tile variant |

The existing [cup-lid validation](cup-lid-validation.md#pins-and-board-engagement)
uses a simplified 1.5 mm taper and cylindrical remainder. That disagrees with
its cited source above; follow-up **pst-akdj** owns reconciliation. Do not
promote that fixture into the new library or silently revise the cup-lid here.

## 3. Fixed-point mounts and retention

| Fact and status | Finding and exact evidence |
| --- | --- |
| [U] Threaded Multiconnect on MultiBoard | Candidate is David D's raised connector [model 1074671](https://www.printables.com/model/1074671-multiconnect-generic-connector-for-multiboard-v2), with the board-threaded base and round accessory head. Direct page fetch failed; exact large-thread variant, stand-off and revisions need confirmation from its files. [openGrid] “Highlighted models” identifies raised/flush variants, not their dimensions. |
| [V] Pinned library head | [Python] `constants.py` L11–15: radii 10 / 7.5; axial heights 1 + 2.5 taper + 0.5 = 4. `multiconnect.py` L62–108 builds that round profile. |
| [V] Cutter profile / clearance | [Python] `multiconnect.py` L188–219,225–254: radial allowance 0.15; slot full-width allowance 0.3; bottom-height +0.212132034, top-height −0.062132034; derived depth 4.15. These are library allowances, not verified official MultiBuild tolerances. |
| [U] Official profile equality | [openGrid organization](https://github.com/openGrid-3D/) recommends changing generator grid size for Multiconnect compatibility; that supports reuse in principle, not dimensional equality of every revision. Compare the selected head/negative in David D's [v2 modelling files](https://www.printables.com/model/1008622-multiconnect-for-multiboard-v2-modeling-files) with the above. Fetch failed; no STEP equality claimed. |
| [V] Slot travel vs spacing | [Python] `constants.py` L4,17 defaults length to 28; `Slot` accepts length (`multiconnect.py` L17–24). Board head-center locations instead use integer multiples of 25 ([Core] §1); that placement is independent of entry travel. A same-row centered array is `x=(i−(count−1)/2)*25`. |
| [V] Snap-in variant | [Python] `SnapInSlotCutter` L260–332 combines slot, triangular exclusions and paired head cutters: local `head_spacing=0.795`, triangle base 8, inset 0.6. This spacing is a seat detail, **not board pitch**. `SnapInSlot` L119–160 also scales asymmetric notch positions by length / length-reference (default reference 28). |
| [C] Fix-Point alternative | Regular mates with a hole; Lite with a Rail and is 1 mm thinner. Installation/removal is sliding; tile anchoring can use threads or bolt-locking ([Core] §11, L238–251). Do not treat all Multipoints as push-in snap pegs. |
| [U] Fix-Point geometry / bump retention | Head cross-section, neck, negative, detent and release force were not established by [Core] §11. Need selected official remix files. The description of slide removal does not prove upward-bump resistance. |
| [V]/[U] Existing holders / likely intent | Repo `holders/cylindrical.py` imports Multiconnect cutters and uses openGrid spacing ([local source](../holders/cylindrical.py), L91–95,135–175). Multiconnect is therefore the leading hypothesis for those holders. Sean's physical mounts remain [U]: “slide on to fixed points” also describes Fix-Points per [Core] §11. |

**Design recommendation:** prioritize a positive anti-lift feature or validated
snap retention for the spool cradle. [V] The current [mount contract](../tests/mount_contracts.py)
L230–289 checks normal pull-off capture and dovetail direction; [U] it does not
measure upward release force, creep or impact. Neither system is proven
bump-proof by this research. Multiconnect needs pitch-aware placement and
profile validation; Fix-Point needs a distinct head/negative/retention implementation.

## 4. Library survey and reuse decision

Searches on the research date: PyPI JSON endpoints for `multiboard`,
`multibuild`, `multiconnect` returned 404; [`opengrid`](https://pypi.org/project/opengrid/)
is unrelated building-analysis software. GitHub repository queries
`multiboard language:Python`, `multibuild language:Python`, `multiboard cadquery`,
`multiboard build123d`, plus web searches of those CAD names found:

| Candidate | Licence, maintenance snapshot, suitability |
| --- | --- |
| [fangpenlin/opengrid][Python] | MIT (`LICENSE`); pinned commit dated 2026-07-18. Existing build123d cutters are the reusable implementation. |
| [cad123d/multiboard__hook](https://github.com/cad123d/multiboard__hook/tree/0b71becbc7d59c00628f1b91c99637492bdcbcd3) | Last push 2025-01-05. `LICENSE`: MIT scripts with explicit reservation of Multiboard product rights. README/files implement a push-fit hook/import examples, not a board/thread/connector library. |
| [chryms0n/multibuild-designs](https://github.com/chryms0n/multibuild-designs/tree/af825469d21fcaa337ad3565e04649261a3dcad9) | Last push 2026-09-28; no licence found. `lib/multiboard.py` has constants and a clearance helper; its thickness/hole values are user measurements. No thread or Multiconnect builder; do not copy without permission. |
| [asciipip/multiboard-parametric-stacked][SCAD] | Last commit 2025-01-09; Multiboard licence (`LICENSE.md`). OpenSCAD reconstruction, useful dimensional evidence; not a Python CAD library. README credits `shaggyone/multiboard-parametric`. The bead's “asciipip/multiboard-parametric-scad” name resolves here through the existing cup-lid citation. |
| [madfam-org/yantra4d](https://github.com/madfam-org/yantra4d) | Active 2026-09-28, platform AGPL-3.0; README advertises a Multiboard cartridge under CC-BY-NC-SA-4.0. Inspected repository tree exposed only Multiboard preview assets, so reusable cartridge geometry/licence provenance remains [U]. |

No suitable complete Python/CadQuery package was established; this is a
bounded search result, not proof of absence.

**Reuse through parameters, not a global constant patch.** [V] Python default
arguments capture constants at definition time; changing `OPEN_GRID_UNIT_SIZE`
after import misses them. `SlotCutter` also explicitly supplies the constant
length. Use the injected `slot` factory to override length (existing
`cylindrical._slot_cutter`, L299 onward), then inject that cutter into
`SnapInSlotCutter`. Preserve head/profile allowances. Audit notch-reference
scaling separately. Board thickness and openGrid base/snap geometry are
system-specific; do not port `base.py` by changing pitch.

## 5. Proposed module API (follow-on only)

| Surface | Contract / acceptance |
| --- | --- |
| `multibuild.constants` | `PITCH=25`; provisional `TILE_THICKNESS=6.4`, `SMALL_HOLE_MOUTH_D=7.5`, `SMALL_HOLE_THROAT_D=6`, `SMALL_HOLE_THROAT_HEIGHT=2.9`, `LARGE_HOLE_PROFILE` carrying the §2 fields **and provenance**. Resolve [U] fields before claiming official compatibility. No user pitch/profile controls. |
| `SmallHoleConePin(fit_per_side, tip_diameter, half_angle)` | Separate alignment pin from the threaded-hole cutter. Derive length and base from mouth plus fit; intersect/sweep against the sourced full cavity. Do not inherit cup-lid fit defaults without validation. |
| `LargeHoleThreadCutter(depth, profile)` | Female negative combining octagon, mouth relief and trapezoidal helix. Explicit right/left hand, starts, phase and runout in a validated profile record; no assumed ISO metric thread. Gate production on official STEP comparison. A male connector builder needs separate male fit data. |
| `MulticonnectSlotCutter(travel, snap_notches)` | Compose pinned head/slot cutters, explicit travel injection, unchanged profile/clearances. Board-facing datum and insertion axis documented; pocket wide internally. A separate `mount_locations(count, grid_step=1)` uses integer pitch multiples. |
| `FixPointCutter(variant)` | Deferred until Regular/Lite negatives and retention geometry are sourced; do not alias to Multiconnect. |
| Registry and fixture hook | Add `multibuild-multiconnect-slot` to `KNOWN_MOUNTS` and `CONTRACTS` together. Model supplies `mount_fixtures(mount_type, values) -> MountFixtures`: cutters, seat locations, face normal and entry axis. Reuse six existing checks only after confirmed head equality; add lattice-spacing, seam-obstacle and neighboring-pocket/backing checks. Separate Fix-Point contract when implemented. |

Apply [design-guidelines §5](design-guidelines.md#5-parametrics-for-mounts):
expose count, travel, snap notches and plate margin via registry `Param`;
derive the plate from the actual cutter envelope. Use the selected system's
fixed pitch. Validate assembly insertion, seating and normal retention on
all presets; add an anti-lift test appropriate to the chosen latch and require
physical PETG/PCTG bump/creep trials before claiming retention performance.

## 6. Questions for Sean / evidence needed next

- Which exact connector/negative files and revision are on the wall: raised
  or flush Multiconnect, or Regular/Lite Fix-Point? Confirm before library selection.
- Which tile variant, wall offset and seam hardware must the holder clear?
- What loaded spool mass, bump direction and acceptable removal action define
  retention? Is a release tab or locking bolt acceptable?
- Obtain the selected official remix STEP files for thread, head and Fix-Point
  measurements; resolve the small-hole discrepancy in pst-akdj.
- Is the site serving free remix downloads only, or commercial/paid content?
  Confirm licence treatment for the actual derived assets before publication.

[Core]: https://docs.multibuild.io/beginner-section/core-parts-documentation
[Mounting]: https://docs.multibuild.io/beginner-section/tile-mounting-guide
[SCAD]: https://github.com/asciipip/multiboard-parametric-stacked/blob/4db5f07abb4653193014eb1bba761011bc29eb87/multiboard_base.scad
[SCAD README]: https://github.com/asciipip/multiboard-parametric-stacked/blob/4db5f07abb4653193014eb1bba761011bc29eb87/README.md
[Python]: https://makerrepo.com/r/fangpenlin/opengrid
[openGrid]: https://www.printables.com/model/1214361-opengrid-walldesk-mounting-framework-and-ecosystem
[licence page]: https://multibuild.io/license
[full licence]: https://docs.google.com/document/d/1C0-Iyxydqk_d2I3o_5ualJ9Ywt9gwVdl9eukvC8JeKA/export?format=txt
[Community Promise]: https://multibuild.io/community-promise

Source pin for all [Python] line references:
`eea2b4154a10d2909e5edece567cbe0563aaf955`, files `opengrid/constants.py`
and `opengrid/multiconnect.py`, as pinned in this repo's `build123d/pyproject.toml`.
Local source references use main `b589d2d5`; web line references identify the
text extraction on the research date and are supplemented by section names.
