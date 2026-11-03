# Outside-corner r2: crown clearance decision

Checkpoint for pst-1h4z6, 2026-11-03, before changing production geometry.

The full arc and a separate cradle are implementable, but the specified
crown height needs clarification before designing the teeth. Invariant 1
places the lowest tangent line `support_gap_mm` above the pad. Invariant 2
requires fin-top contact lands at most 1 mm long and a dot-only witness.
With a uniform pad top below the crown, its entire width is at the normal
gap at the lowest tangent line. Cutting teeth into the fins cannot remove
that continuous pad-backed line. This is a clearance issue, not a claim
that separated CAD solids touch or that a particular slicer will fuse them.

In print coordinates, with the crown at Z=0, the underside is
`z(y) = R - sqrt(R*R - y*y)`. At Y=0 its downward normal is vertical,
independently of X. A pad top at Z=-gap therefore backs the entire crown
at exactly the requested normal gap. There is zero space above that pad
for a fin at the crown. The existing 4 mm floor bevel at either side
reduces the crown width to `channel_width - 8 mm`; it does not break up
the remaining line.

Verified against the unflattened production BREP at three X positions
(centre and +/-5 mm), using points 0.01 mm above/below the tangent line:

| Case | Floor radius (mm) | Crown width (mm) | Crown Z (mm) | Pad top Z at gap 0.2 (mm) |
| --- | ---: | ---: | ---: | ---: |
| w1 / h22 / r0 | 18.600 | 18.400 | 3.885996 | 3.685996 |
| w1 / h22 / r1 | 46.600 | 18.400 | -4.315014 | -4.515014 |
| w2 / h28 / r1 | 52.600 | 46.400 | 3.827121 | 3.627121 |

All nine probes had material just above and no material just below the
analytic underside. Geometry sources: `outside_floor_radius` and
`outside_axis` in `underware/path.py`, and `unflattened_outside_corner`
and `outside_print_frame` in `holders/underware_path_channels.py`.

Requested decision: may invariant 1 instead put the crown one support gap
above the **central tooth tops**, with those tops raised above the pad?
A proposed starting height is 1 mm above the unchanged 0.6 mm pad. That
would preserve the full arc, normal gap, separate solids, solid pad and
tooth-only backing, while changing the specified crown-to-pad distance
and resulting print height. Alternatively, authorize a recessed or
perforated pad beneath the crown and specify its permitted remaining
thickness. Neither interpretation has been silently selected.

After a spec revision, implement the geometry and audit together, then
regenerate presets, manifest, endpoint/edge evidence and review renders.
Production code and baseline records are unchanged in this checkpoint;
the full test suite and print acceptance have not been run.
