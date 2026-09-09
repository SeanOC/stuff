# Multiconnect slab corner audit — pst-kapi

Baseline: `a2060f8` (main). Native engine: OpenSCAD 2025.06.12.ai25773,
`--backend=CGAL`; BOSL2 `456fcd8`, QuackWorks `6123129` plus the repository
patches. This audit uses STL exports and point containment, not thumbnail
appearance. Dimensions and mesh volumes are in mm and mm³.

## Ten-model audit

The table describes the baseline. No baseline slab was clipped. Protrusion
is the greatest distance from a square slab corner to the ideal plate arc,
`r * (sqrt(2) - 1)`, after confirming solid occupancy outside that arc.
The EGO imported plates have fixed r2 corners at low Y; their extensions
have tunable r1–3 corners at high Y. The maximum includes both kinds.

| Model | Plate/backer rounding | Slab clipped? | Pokes? | Maximum protrusion (mm) | Disposition |
| --- | --- | --- | --- | ---: | --- |
| led_remote_holder_51x84mm | r1 | No | Y | 0.414214 | Follow-up pst-5fq5 |
| led_remote_holder_55x124mm | r1 | No | Y | 0.414214 | Follow-up pst-jvui |
| apple_tv_4th_gen_holder | r1 plate; front rail radius is separate | No | Y | 0.414214 | Follow-up pst-ai7k |
| ryobi_p2860_strap_saddle | r8 | No | Y | 3.313708 | Slot conflict; follow-up pst-iabc |
| ego_powerhead_mount | r2 source, r1–3 extension | No | Y | 1.242641 | Fixed |
| ego_ea0820_edger_mount | r2 source, r1–3 extension | No | Y | 1.242641 | Fixed |
| ego_lb6500_blower_mount | Square plate | No | N | 0 | Byte-identical |
| littletikes_dream_machine_cartridge_holder | No Multiconnect variant | N/A | N/A | — | Byte-identical |
| opengrid_bin | r1 | No | Y | 0.414214 | Follow-up pst-4fy0 |
| opengrid_multiconnect_adapter | r1 | No | Y | 0.414214 | Fixed |

Little Tikes currently declares `opengrid|blank|openconnect`; passing an
unsupported `mount_type="multiconnect"` would not audit a Multiconnect slab.
The Disney reference has since moved to a separate slot-plate/dovetail
assembly. It is left byte-identical; the fix retains the original reference's
principle of intersecting the slab with the plate outline.

All 77 baseline exports were watertight single solids. [audit.csv](audit.csv)
records every case, parameter override, corner radius, volume and bounding box.
Each case varies the named parameter from defaults with Multiconnect selected
(the adapter is intrinsically a Multiconnect receiver):

- Both remotes: min/max remote width, remote height, side clearance, wall,
  plate length cap and plate thickness; combined narrow/tall and wide/short.
- Apple TV: min/max device width/height, clearance, shelf thickness,
  width/height units and plate thickness; 1×6, 6×1 and 6×6 requested unit minima
  (the model's device-fit floor still determines the actual plate dimensions).
- Ryobi: defaults; its 56×84 plate is fixed, independent of its saddle params.
- Both EGO extensions: defaults, min/max extension radius and backer thickness;
  plate aspects are fixed at 56×112 and 56×140.
- EGO blower: defaults and min/max backer thickness; plate outline is fixed.
- Bin: min/max width/height units and plate thickness; 1×4, 6×1, 6×4 aspects.
- Adapter: single/double, min/max plate thickness; these are its narrowest and
  widest supported aspects, 28×28 and 56×28.

The initial corner probes sit 0.05mm inside both rectangle edges, midway
through the slab, below the holder body (above the plate for the adapter).
Apple TV probes are transformed from mount coordinates `(x,y,z)` to its
standing print coordinates `(x,-z,y)`. EGO and Ryobi body rounding was checked
against the current SCAD/source meshes, not the original grep hints.

## Choice of fixes and slot preservation

Ryobi is the worst protrusion but fails the mandatory slot-clearance check.
At its entrance, 0.1mm from the edge, the r8 arc starts at an X inset of
`8 - sqrt(8² - 7.9²) = 6.739mm`. The default slot starts at
`15.5 - 10.15 = 5.35mm`. The native baseline confirms slot air at
X inset 5.5mm, entrance inset 0.1mm, slab Z=4mm. Clipping would remove a slot
side wall and change the entrance. It is skipped and the follow-up explicitly
requires resolving this contract before any clip.

The two EGO models are next worst. Their full plate footprints use
`rounding=[ext_fillet, ext_fillet, 2, 2]`; the new intersection spans exactly
`backer_thickness + mc_weld`. The remaining r1 models tie; the adapter is
selected because both supported sizes have a simple fixed slot-clearance
bound. Its clip uses the existing plate rectangle and the original receiver
Z range. No library cutter, transform, thickness, pitch or tunable changes.

Slot channels on both EGO plates are at X=15.5 and 40.5. At the greatest
slot tolerance their half-width is 10.15×1.075, leaving 4.58875mm to the
plate edge, beyond the greatest 3mm corner. On-ramps need a separate check:
for every tolerance step 0.925…1.075, their circle centers are at
`Y=13+25*n*tolerance`, with conservative radius `12*tolerance`. Restricting
these circles to the two corner bands (Y=0…2 and Y=H−3…H) gives minimum
clearance **beyond** the clipped region:

| Model | Minimum additional clearance | Closest tolerance |
| --- | ---: | ---: |
| EGO powerhead | 0.533647mm | 1.005 |
| EGO edger | 0.251556mm | 1.025 |
| Adapter, either size | ≥0.1mm | 1.075 |

For the adapter, even an on-ramp's full radius fits:
`14 - 12*1.075 = 1.1mm > corner_r=1mm` (double has more margin).
Both EGO closest-on-ramp cases are included in the native evidence and WASM
sweep, alongside the extreme radius/thickness/tolerance combinations.

## Geometry evidence

All 29 native before/after cases passed.
[verification.csv](verification.csv) records the before/after mesh volume
(the OpenSCAD/STL equivalent of `part.volume`) at defaults and each tested
extreme. It also records these independent checks:

- Native CGAL export is watertight and contains exactly one connected solid.
- All six bounding-box coordinates agree within 0.001mm.
- Each of four corners is probed at three slab depths: diagonal inset 0.1r
  must be air; inset 0.4r must be solid. Low-Y EGO corners always use r2.
- 500 reproducible samples across the inboard slot band have identical
  before/after occupancy (NumPy RNG seed 123). The analytic clearance above
  additionally protects the slot envelope between samples.

The new sidecar probes fail on the baseline with only corner-rounding
failures (both EGO variants and both adapter sizes). They pass on the edited
exports. All removal is confined to the four corner regions by construction:
an intersection around the original, unmodified slab module. Volume decreases
in every tested case; no material increase needs justification.

To reproduce an individual CSV row, run the baseline and edited source with
its JSON overrides translated into OpenSCAD `-D` arguments, for example:

```sh
bash scripts/vendor-libs.sh
OPENSCADPATH="$PWD/libs" openscad --backend=CGAL -o /tmp/edger.stl \
  -D 'mount_type="multiconnect"' -D 'ext_fillet=3' \
  -D 'slot_tolerance=1.025' models/ego_ea0820_edger_mount.scad
python3 -c 'import trimesh; m=trimesh.load_mesh("/tmp/edger.stl"); print(m.volume, m.bounds, m.is_watertight, len(m.split(only_watertight=False)))'
```

Keep imported EGO source STLs beside their SCAD files when extracting the
baseline. The audit row overrides are relative to that model's defaults.
The adapter has no `mount_type` switch.

## Design-guidelines §6 assessment

This is a corner-only change to existing OpenSCAD models. The checklist was
applied to the changed geometry; the preserved source models are not newly
certified against the later build123d guidelines.

1. Print orientations remain declared in the model headers. The new faces
   are vertical extrusions: they introduce no overhang or bridge.
2. No downward fillet is introduced. Existing bed-contact/mating edges retain
   their prior treatment; adding an all-edge chamfer would exceed this bead's
   explicit outline-only/slot-preservation scope.
3. No isolated feature or hole is introduced. The analytic slot-clearance
   check proves the clipping stays outside the slot profiles; the outer
   corner terminations now follow the existing plate outline.
4. The exposed square corner posts are replaced with the existing plate arcs.
   Functional/library edges are preserved.
5. Each plate keeps its original envelope; measured volume only decreases.
6. Existing bodies, gussets/struts, weld depths and load paths are preserved.
   The native connectivity checks confirm the corner cuts do not split them.
7. All mount tunables and library constants remain byte-for-byte the same;
   both adapter size presets and the EGO min/max mount variants are tested.
8. Gravity loads the EGO domes toward low Y and bends the tool arms away from
   the wall; the adapter's downward dome bears a hanging accessory's weight.
   The corner cuts stay outside these mating/load-bearing regions. This
   removes sharp corners without a new PLA/PCTG support or layer-load demand;
   no physical print/load test is claimed.

## Automated regression commands

```sh
python3 scripts/export-all.py --changed-paths 'models/ego_powerhead_mount.scad models/ego_ea0820_edger_mount.scad models/opengrid_multiconnect_adapter.scad'
python3 scripts/check-invariants.py ego_powerhead_mount
python3 scripts/check-invariants.py ego_ea0820_edger_mount
python3 scripts/check-invariants.py opengrid_multiconnect_adapter
pnpm test
pnpm exec tsc --noEmit
pnpm test:sweep
pnpm test:sweep tests/sweep/ego_powerhead_mount.test.ts tests/sweep/ego_ea0820_edger_mount.test.ts tests/sweep/opengrid_multiconnect_adapter.test.ts
```

The final command includes Multiconnect-specific combination cases that a
one-parameter sweep from the openGrid default cannot exercise. Default exports
passed 6/6, all three sidecars passed, unit tests passed 291/291, and TypeScript
passed. WASM/CI results are recorded in the PR and bead notes.
