# openConnect drawer

The shell adapts mitufy's drawer under CC BY-SA 4.0. Source files, library
pins and reference meshes are documented in
[the reference NOTICE](../assets/openConnect-drawer/NOTICE).
Print every mount-face choice back-wall-down in PLA or PCTG.

## Honeycomb ceilings

`honeycomb_ceiling=roofed` is the shipping default. Each top, bottom or side
Honeycomb wall keeps the source lattice, frame and fitting reinforcements.
After clipping each opening to those boundaries, a horizontal ceiling chord
longer than 10 mm receives an inward 45° roof. Two slopes descend from the
chord ends to a midpoint at depth chord/2. The added triangle is intersected
with the opening; a shallow opening can therefore split into two triangular
openings. Chords at most 10 mm remain allowed flat bridges. The slot-bearing
wall remains solid.

This redesign follows the unsupported-bridge rule in the
[design guidelines](../build123d/docs/design-guidelines.md). Outward peaks
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
