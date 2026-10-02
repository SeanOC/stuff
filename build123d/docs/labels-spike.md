# Labels spike (pst-0zfra, L1 of epic pst-mbh56)

**DRAFT — in progress.** Q1, Q2 and the Q6 measurements are done. Q3 (3MF), Q4
(web), Q5 (service), the `label_demo` model, the exports, the provenance row
and the DECISIONS table are still to do. See the bead's RESUME note.

Run from `build123d/`. All measurements are at origin/main 38af4ad + this branch.

## Q1 Font rendering

**Font: Inter Bold 4.001, static TTF** ([rsms/inter v4.1 release](https://github.com/rsms/inter/releases/tag/v4.1),
`extras/ttf/Inter-Bold.ttf`, sha256 `28831609…947f`), OFL 1.1, vendored with
its licence at `assets/fonts/inter/`.

Candidates were measured with `Text(s, font_size=10, font_path=…)`, then
`extrude(…, 0.8)`:

| font file | string | bbox X × Y (mm) | glyph faces | holes | solids | valid | Text + extrude (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Atkinson Hyperlegible Bold (static) | Filament | 40.61 × 7.70 | 9 | 2 | 9 | yes | 12 + 19 |
| | PLA Black | 47.18 × 6.80 | 8 | 5 | 8 | yes | 7 + 13 |
| | PETG-CF | 40.67 × 6.92 | 7 | 1 | 7 | yes | 6 + 14 |
| | aeo | 16.44 × 5.22 | 3 | 3 | 3 | yes | 6 + 10 |
| Inter Bold (static) | Filament | 41.23 × 7.78 | 9 | 2 | 9 | yes | 7 + 13 |
| | PLA Black | 48.08 × 7.38 | 8 | 5 | 8 | yes | 6 + 14 |
| | PETG-CF | 43.59 × 7.47 | 7 | 1 | 7 | yes | 5 + 11 |
| | aeo | 17.17 × 5.63 | 3 | 3 | 3 | yes | 6 + 8 |
| Inter[opsz,wght] (variable, google/fonts) | Filament | 43.09 × 7.91 | 10 | 1 | 10 | **NO** | 12 + 21 |
| Roboto[wdth,wght] (variable, google/fonts) | PLA Black | 37.83 × 7.60 | 15 | 0 | 15 | **NO** | 10 + 19 |

- Static fonts build valid solids. The counters are correct: "aeo" gives 3
  holes, one each; "PLA Black" gives 5 (P, A, B×2, a).
- **Variable fonts build invalid solids** with wrong holes, because OCCT does
  not union the overlapping contours. Only static TTFs are allowed.
- Roboto in google/fonts is now OFL (`ofl/roboto/OFL.txt`), not Apache. That
  answers plan-review A2.

**Silent substitution (the fallback test).** `Text('PLA', 10, font_path='/nonexistent/Nope.ttf')`
and `font_path=<a .txt file>` both return 3 faces, 17.68 mm wide, **with no
error and no warning**. A bad `font=` name only logs a FreeSans substitution
warning. Cause: build123d `Text` checks `check_font(path)` and then silently
falls back to `find_font(name)`. It also renders by font NAME, so an
installed system font of the same family could win.
`holders/label_text.load_font()` closes this:

- it raises `FileNotFoundError` for a missing file;
- fontTools raises for a non-font file;
- it raises `RuntimeError` unless OCCT's BOLD aspect resolves to exactly the
  vendored path.

**Mirror.** `print_orientation` is metadata only (plan-review A1): export.py
writes the part unrotated. So the card is modelled in the print frame and the
text is mirrored explicitly about the YZ plane. The face-down visible face
then reads correctly from below. *(The label_demo proof — glyph order and an
asymmetric 'F' — is still to be written.)*

## Q2 fit_text — autoscale + centre

`holders/label_text.fit_text(text, box_w, box_h, margin, depth=0.6)`
returns `FittedText(part, scale, min_stroke, min_gap)`. That is a NamedTuple
whose first two fields are the specified `(Part, scale)`; the extra fields
are the "report" that Q2 asks for.

For each string it builds at 10 pt, scales uniformly by
`min((W−2m)/w, (H−2m)/h)` and centres the ink bbox on the origin.

Card box 60 × 14, margin 1.5 (the Atkinson run, before the switch to Inter):

| string | scale | ink bbox | centre | min stroke | min gap | time |
| --- | --- | --- | --- | --- | --- | --- |
| Filament | 1.404 | 57.00 × 10.81 | (0,0) | 1.24 | 0.51 | 1.1 s |
| PLA Black | 1.208 | 57.00 × 8.22 | (0,0) | 1.14 | 0.43 | 1.0 s |
| PETG-CF | 1.402 | 57.00 × 9.70 | (0,0) | 1.79 | 0.50 | 1.0 s |
| W | 1.647 | 14.21 × 11.00 | (0,0) | 1.98 | 3.85 | 0.2 s |
| Bambu PLA Matte Charcoal (24 ch) | 0.443 | 57.00 × 3.07 | (0,0) | **0.39** | **0.16** | 3.9 s |

**Stroke and gap metric.** The stroke is the narrowest disc diameter whose
morphological opening (shapely `buffer(-r).buffer(r)`) removes a piece at
least 0.75 r thick. Corner slivers stay below that unless the corner is
sharper than about 16°. The scan runs upward, because bisection is not
monotonic here. The gap is the same metric on the complement inside the
padded bbox. A known artefact: Inter's 'M' crotch reads as a 0.18 gap (the
scan floor), which is an acute notch, not a real gap.

**Why Inter, not Atkinson.** At 10 pt the strokes are similar, but the gaps
are not:

| font | Filament | PLA Black | PETG-CF |
| --- | --- | --- | --- |
| Atkinson Bold | stroke 0.88, gap 0.36 | stroke 0.94, gap 0.36 | stroke 1.28, gap 0.36 |
| Inter Bold | stroke 0.90, gap 0.92 | stroke 0.96, gap 1.12 | stroke 1.12, gap 1.10 |

The Atkinson gaps are the tailed 'l' beside 'a' and the E→T bars. With text
flush on the bed, a gap is a base-colour first-layer feature, so 0.36 × 1.4
= 0.5 mm is one marginal line. Inter keeps more than 1.2 mm at label scale.

**Inter Bold over all printable ASCII at 10 pt (cap height 7.275)**, from
`.tmp` sweep:

- thinnest strokes: `$` 0.58, `%` 0.82, `*` 0.86, `e` 0.90, `a` 0.96;
- narrowest gaps: `"` 0.82, `$` 0.88, `e` 0.92, `f` 0.96;
- alphanumerics: minimum stroke 0.90 (`e`), minimum real gap 0.92 (`e`).

**Printability bound.** With a stroke of at least 0.9 mm (≈ 2 lines), the
scale must be at least 1.0, i.e. the ink is no wider than the 10 pt width
≈ the box width. On a 57 mm line that is about 10–11 characters. A
24-character string goes to 0.39 mm. So L2 must clamp: reject, wrap to two
lines, or accept a single-line inlay threshold. *(Decision still to be
written.)*

## Q6 Card envelope — measurements so far

The front panel is `Box(spool_width, WEB=2.4, panel_height)` at
y = `end_y` (spool_cradle.py:541). Its outer face is at `end_y + 2.4`, facing
+Y toward the user.

| case | panel W × H (mm) | contact_z |
| --- | --- | --- |
| default (66) / ams 66 / bambu 67 | 66 (67) × 58.90 | 53.90 |
| spool_width = 50 / 70 | 50 / 70 × 58.90 | |
| lip 0 / lip 15 | 66 × 53.90 / 68.90 | |
| d190 a25 / d205 a45 | 66 × 78.14 / 53.17 | |

The loaded spool's outer surface sits relative to the panel face at heights
above the panel top (+ is proud of the face):

| case | +0 mm | +5 mm | +10 mm | +20 mm |
| --- | --- | --- | --- | --- |
| default | −3.3 | +0.2 | +3.2 | +8.2 |
| lip 15 | −5.1 | −2.5 | −0.1 | +3.5 |
| d190 a25 | −3.1 | −1.3 | +0.3 | +2.5 |

So a top-slide card can only be inserted with the spool out. That is fine,
because the label changes when the spool changes. Side-slide is blocked by
the neighbour: cadence 75 minus spool 66 leaves a 9 mm gap. The usable card
width at the 50 mm endpoint is about 44 mm.
