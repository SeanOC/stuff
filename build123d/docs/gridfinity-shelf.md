# openConnect Gridfinity shelf

`openconnect-gridfinity-shelf` adapts mitufy's shelf generator. It combines
42 mm Gridfinity sockets with one 28 mm-tall row of openConnect slots.
It lives in the `multiboard` catalog category alongside the other wall-mount
models. It uses the existing openConnect library, including the author's
4 mm entry extension and separate row strip.

Presets: **default** (2×2), **magnets** (2×2, magnets in every cell), **wide**
(4×2), and **sturdy-back** (2×2, 1.55 mm extra back offset). The published
backing is 0.85 mm; sturdy-back increases it to 2.4 mm. Width and depth cell
counts and the baseplate style appear in download filenames.

| Controls | Domain / behavior |
| --- | --- |
| Grid width / depth | 1–6 / 1–4 cells; even widths align 84 mm with three openGrid tiles |
| Baseplate style | Default, Magnet – All, Magnet – Corners Only |
| Magnets | Diameter 0–8 mm, thickness 0–3 mm; zero disables magnets |
| Side screw connections | Optional; diameter 2–5 mm; holes omitted if the author's 0.8 mm bottom wall cannot be retained |
| Back offset | 0–20 mm, in addition to the fixed 0.7 mm filler |
| Side / front rim | 0–10 mm; matching lips appear only when that rim is nonzero |
| Lip height | 0–5 mm |
| Socket clearance | 0–0.2 mm, saturating at +0.2 mm |
| Slot locks | All, Staggered, Corners, Top Corners, None |
| Slot placement | Center/Left/Right alignment, entry-ramp flip, horizontal ±14 mm and vertical ±10 mm offsets; impossible offsets raise a named validation error |

The model is built with the back in the XZ plane and the deck horizontal.
The parameter-dependent `print_frame` rotates the wedge underside onto the
bed. Audit, review, baked export and live export use this frame; mount
contracts use the original model coordinates. Print wedge-down in PLA or
PCTG. The continuous wedge supports loads from bins pulling away from the
wall. This is a geometric printability assessment, not a load rating.

Every underside loop receives 0.3 mm bed relief after the final cut. The
nominal 45° bevel uses OCCT's angle operation with an accepted 0.01° inward
slope margin for fitted curved faces. Other published edges are retained
under the bead's explicit Gridfinity-profile, mount-face and author-exterior
exceptions. Backing probes exclude only the below-wedge region and the exact
volume removed by this bed bevel, including pocket/window loops.

Source and port: **CC BY-SA 4.0**, attribution **mitufy**; credits **David D**
(openGrid), **Zack Freedman** (Gridfinity), and **Gridfinity Rebuilt**
(MIT-derived profile constants). See the source, hashes, rendering commands
and BOSL2 pin in [NOTICE](../../assets/openConnect-gridfinity-shelf/NOTICE),
and the [licence text](../reference/LICENSES/CC-BY-SA-4.0.txt).
