# openConnect drawer

`openconnect_drawer` adapts mitufy's **openConnect Drawer Generator**
([Printables 1559284](https://www.printables.com/model/1559284)) under
**CC BY-SA 4.0**. Attribution: "openConnect Drawer Generator" by mitufy,
licensed CC BY-SA 4.0; adapted for this repo in `build123d/drawer/` and
`build123d/holders/openconnect_drawer.py`, which stay CC BY-SA 4.0. Source
file, library pins, render commands and reference hashes are in
[the reference NOTICE](../../assets/openConnect-drawer/NOTICE) and its
`SHA256SUMS`.

A drawer is three printed parts, chosen with `part`:

| `part` | What it is | Print orientation (PLA or PCTG, no supports) |
| --- | --- | --- |
| `shell` | The box that mounts on an openConnect wall: slots on the Back, Top, Bottom, Left or Right face, magnets, stopper holes, optional dividers | Back wall down, open front up, for every mount face |
| `container` | The sliding drawer: handle, label holder, magnet pockets, optional dividers | Bottom down, handle toward −Y (`drawer/container.py` `print_frame`) |
| `stopper_clips` | Two clips that push through the shell's stopper holes and stop the container | Flat on the bed, 2.0 mm tall, as laid out by the author. The Z=0 edge stays sharp by exception (see Deviations from the source); print with the slicer's elephant-foot compensation at 0.1–0.15 mm |

All three are built from the same drawer size (`horizontal_grids`,
`vertical_grids`, `depth_grids` in 28 mm openGrid tiles). The container is
sized from the shell's inner box, so build both with the same size values.

## Parameters

| Group | Parameters | Notes |
| --- | --- | --- |
| Drawer Size | `part`, `horizontal_grids`, `vertical_grids`, `depth_grids` | 1–8 tiles each |
| Shell | slot face, wall types, `shell_thickness` 1.6–4, outer chamfer, slot backing, honeycomb strut | Mount profiles and the 28 mm pitch are library constants |
| Slots / Advanced | lock distribution, positions, entry ramp, clearances | Side clearance capped at 0.3 mm (retention) |
| Magnets, Stoppers | back/side magnet pockets, stopper holes, `stopper_edge_distance`, `stopper_clip_length` 4–12 | Clip length is the leg length below the wall |
| Shell Divider | `add_shell_divider` None/Width/Height/Both, `shell_divider_wall_type`, `shell_width_compartment_list`, `shell_height_compartment_list` | Lists in tiles |
| Container | wall types and thicknesses, fillet, label, handle, container magnets, clearances | |
| Container Divider | `add_container_divider` None/Width/Depth/Both, `container_divider_wall_height_offset`, width/depth `grid_count` + `compartment_list` | Lists in grid units |

## Dividers and compartment lists

A compartment list is comma-separated whole numbers, for example `3,2`.
Running sums below the grid count are divider positions; whatever is left
becomes the last compartment ([C] :399-417). On a 5-tile shell, `3,2` and
`3,3` both give compartments 3 and 2, and `5` gives no divider. Spaces are
ignored. An entry that is not a positive whole number, an empty list or a
grid count below 1 is a named error (`drawer/dividers.py`).

**Shell dividers** are solid or honeycomb walls `2 × shell_thickness`
thick, centred on tile boundaries over the full depth. `Width` lists run
left to right as seen from the front; `Height` lists run top to bottom.
Every compartment gets the author's per-compartment fittings: back magnets
at its own tiles, top-wall stopper holes at its end tiles, a through
stopper hole in each height divider above it, and side-magnet pockets on
both faces of each width divider.

**One container per compartment.** A divided shell holds one container per
compartment, and each container is built separately, exactly as the
author's customizer says (:44-49): set `horizontal_grids` (and
`vertical_grids` for height compartments) to that compartment's size and
keep `depth_grids`. The `two-compartments` preset is the shell only
(`Width`, `3,2`); build its containers with the `container` part at
`horizontal_grids=3` and at `horizontal_grids=2`. A container sized from a
divided compartment fits it, because a compartment's inner span equals a
same-size shell's inner span.

**Container dividers** split one container. Its inner span, less the
1.2 mm divider walls, is divided into `grid_count` units and the list
counts units: `3` with `1,1,1` gives thirds across, `5` with `2,3` gives
2/5 and 3/5 front to back (the `organiser` preset). Divider walls stand
`container_divider_wall_height_offset` (default 10 mm) below the side
walls, with `container_inner_fillet` foot fillets.

**Stopper clips.** `stopper_clips` prints the author's pair; their shaft
matches `shell_thickness`. For the stopper hole in a height divider (a
`2 × shell_thickness` wall), lengthen `stopper_clip_length` by
`shell_thickness`, as the author's customizer note says (:81).

### Picking lists

- Shell lists count 28 mm tiles: the sum should equal `horizontal_grids`
  (Width) or `vertical_grids` (Height). A shorter list leaves the remainder
  as the last compartment; a longer one is cut at the grid.
- Each shell compartment must be at least one tile; for a container's side
  magnets and stoppers to line up, prefer compartments of two or more
  tiles.
- Container lists count units of `grid_count`; pick the grid count so the
  compartments you want are whole numbers of it.

## Parity

Reference meshes are rendered by the NOTICE commands from the pinned author
SCAD; the parity tests compare the library's source-mode build
(`honeycomb_ceiling='source'`) against them.

| Reference | Test | Volume ref → port | Max surface distance (kept) |
| --- | --- | --- | --- |
| shell-divider-width (`Width`, `3,2`) | `test_shell_divider_parity` | 138.830 → 138.776 cm³ (−0.04 %) | ≤ 0.15 mm outside the bed band |
| shell-divider-height (`Height`, `1,1`) | `test_shell_divider_parity` | 164.822 → 164.767 cm³ (−0.03 %) | ≤ 0.15 mm outside the bed band |
| container-divider-both (`Both`) | `test_container_divider_parity` | 82.900 → 82.871 cm³ (−0.03 %) | 0.020 mm (cap 0.05) |
| stoppers | `test_stopper_clip_parity` | 0.13008 → 0.13008 cm³ | ≤ 0.02 mm ($fn=64 arcs) |

Masked skins are zero-material reference faces only: stopper-hole flange
planes (shell, as in D1), the container's coincident wall faces (D3) and
the clip's internal cuboid faces, whose share matches the reference's
surplus area (420.0 vs 295.5 mm²). D1–D3 parity rows are unchanged.

## Honeycomb ceilings

`honeycomb_ceiling=roofed` is the shipping default. Each top, bottom or side
Honeycomb wall keeps the source lattice, frame and fitting reinforcements.
After clipping each opening to those boundaries, a horizontal ceiling chord
longer than 10 mm receives an inward 45° roof, including a flat ceiling that
a reinforcement plate leaves below a short horn (the container's label
plates). Two slopes descend from the
chord ends to a midpoint at depth chord/2. The added triangle is intersected
with the opening; a shallow opening can therefore split into two triangular
openings. Chords at most 10 mm remain allowed flat bridges. The shell's slot-bearing
wall remains solid.

This redesign follows the unsupported-bridge rule in the
[design guidelines](design-guidelines.md). Outward peaks
were rejected because they overflow the frame and merge adjacent openings.
The inward profile adds only the material required for the over-limit roof;
it does not move the lattice or expand the panel outline. Default and
underdesk bottoms retain 97 openings. The small bottom has 19 openings
instead of the source's 17, because two clipped cells split.

The catalog accepts only `honeycomb_ceiling=roofed`. For mesh parity,
library callers can pass `honeycomb_ceiling='source'` directly to
`drawer.shell.build({...})`, or `ceiling='source'` to the panel helper.
The parity tests and `scripts/check-drawer-roof-contract.py` use these
library overrides. Source mode can contain bridges over 10 mm and is not
available through the registry or web app.
The analytic `ceiling_chords(frame_up)` inventory
reports the source chord and whether the selected mode roofs it; endpoint
audits require every unroofed chord to be at most 10 mm, alongside the
production print audit and exposed-edge classifier. The 3D audit's local
width alone cannot measure a through-wall ceiling span.

`honeycomb_strut_hyp` has catalog bounds of 1.1–16.3 mm and a 0.1 mm step.
At the maximum, an unclipped hexagon measures 2.0496 mm flat-to-flat;
frame-clipped openings can be smaller. Under the mayor's `pst-t0ob3.2 REV 7`
exception, Ø2 mm applies to full hexagons only: frame-clipped decorative
closed slots are exempt and become sub-millimetre slots at large struts.
Its named library
`HoneycombStrutOutOfRange` guard rejects values below 1.1 mm (perpendicular
strut below about 0.95 mm), nonfinite values, and values that leave no hex
opening. `HoneycombPanelTooSmall` rejects panels smaller than the source's
frame-and-cell requirement; neither guard silently substitutes a solid wall.

## Deviations from the source

**Left/Right slot orientation (decided by Sean 2026-10-12).** Source :1427
(`slot_slide_direction = Top||Bottom ? "Left" : "Up"`) combined with :1421
`attach(LEFT/RIGHT)` orients the side slots along the drawer depth, so a
Left or Right shell can only hang with its opening facing up. We rotate
those slots 90° about the face normal (`slide='left'` on Left,
`slide='right'` on Right, compensating for their opposite normals). The
shell now hangs opening-forward: as on the Back face, the head travels up
relative to the shell while the shell drops onto the seat. Grid positions,
tile counts and side-magnet exclusions are unchanged; the same cutters
rotate in place. Back, Top and Bottom keep the source orientation.

The author reference set has no Left/Right shell meshes, so mesh parity is
unaffected. Do not add the author's Left/Right meshes as parity targets;
they would pin the source orientation.
`test_mount_entry_axis_in_model_frame` guards the entry axis for every face.

**Shell dividers (pst-t0ob3.4).** Mesh parity is pinned on the Back face;
these differences only show elsewhere.

- Height dividers on a Top or Bottom slot face stay on the tile boundary.
  The author insets them from the top of the slot-thickened box (:1597,
  :1620-1624), which shifts them by the extra slot thickness.
- Back magnets sit at each height compartment's own bottom tile. The author
  offsets rows from the bottom using the top-first divider sums
  (:1454-1455), which misplaces the magnets of an asymmetric list. Symmetric
  lists are unchanged.
- With a Top slot face, the slot under every per-compartment stopper hole
  is dropped. The author frees only the two corner tiles (:1425-1426), so the
  inner holes would cut through slots. The Top frame mirrors source X, so a
  stopper at source tile `c` frees slot column `h-1-c`.
- Default lists are `3,2` (width) and `1,1` (height). The author's `3,3` and
  `2,3` give the same width split, but no height divider on the 2-tile
  default.
- Spaces in a list are removed. The author turns them into empty entries.

**Container dividers (pst-t0ob3.4).**

- Every divider is kept. The author skips one whose inset reaches the
  inner span (:1629), which only drops valid dividers of many small
  compartments.
- A divider's footprint is subtracted from the wall openings it crosses.
  The author's union refills the same area, so the geometry is identical;
  production then closes any resulting piece under Ø2 mm, like every other
  opening.
- Named errors: too many divider walls for the inner span, and divider
  walls that do not rise above the floor fillet
  (`container_divider_wall_height_offset`).

**Container production departures (D3, recorded here for later parity
work).** The container's production build departs from the author mesh in
three deliberate ways. Parity is pinned in SOURCE mode on container-default,
all-solid and 1x1x1 only, so none of these is a bug.

- A window edge can clip a hex row into a strip thinner than 0.1 mm; that
  strip is dropped (`drawer/container.py` `wall_layouts`).
- The production side and front windows stop at the front fillet tangent,
  where the author's window leaves a 0.09 mm feather.
- DECISION C(b) closes every lattice opening whose roofed profile has an
  inscribed circle under `MIN_LATTICE_OPENING_MM` = 2.0 mm.

**Operator decisions (pst-t0ob3.4, mayor 2026-10-14).**

- Q1, a list that sums past the grid. The port follows the author and cuts
  it at the grid, so the remainder becomes the last compartment. This is
  not an error. The named errors are exactly: an entry that is not a
  positive integer, an empty list, and a grid count below 1.
- Q2, the stopper-clip audit waiver: a mayor-approved exception row. The
  clip's 0.7 mm flange (with its flare) and 0.6 mm wedge nubs ([C] :1812)
  mate with the shell's stopper-hole recess, so they are not thickened
  (stoppers.stl parity holds). They are excluded by exact envelopes
  (`drawer/stopper.py` `audit_exclusions`). At stopper_clip_length 4, 6
  and 12, `test_stopper_exclusions_cover_only_the_snap_features` asserts
  that the excluded material is no more than the flange + flare + nub
  volume and that the rest of the clip passes at MIN_WALL 0.9 (it measures
  ≥ 1.5 mm). The hole variant's 0.8 mm flange floor is the shell's
  registered fitting floor (`tests/openconnect_drawer_inventory.py`).
- Stopper-clip bed edge: a mayor-signed §8 exception row (pst-t0ob3.4,
  2026-10-14) for the bed-contact chamfer rule (design-guidelines §1). The
  family is the Z=0 profile boundary of both clips, meaning every edge of
  the extrusion's bottom face. The author ships it sharp (stoppers.stl, bbox
  34.4 × 8.3 × 2.0). A 0.3 mm relief would leave a 0.1 mm land on the
  0.7 mm flange and remove the first layer of the 0.6 mm nubs, so the slicer's
  elephant-foot compensation does that job instead.
  `test_stopper_bed_edge_exception_is_exactly_the_profile_boundary` pins
  the family by adjacency to the bed face at L 4/6/12.
  `test_bed_chamfer_exception_does_not_reach_other_parts` asserts that
  every other preset still reports a bed chamfer.

