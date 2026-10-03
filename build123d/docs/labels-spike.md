# Labels spike (pst-0zfra, L1 of epic pst-mbh56)

This spike answers L1's six questions by running code. The **DECISIONS**
table at the end is what L2 (pst-qznya), L3 and L4 (pst-egc3j) build on.
Rows marked *proposed* need Sean's confirmation.

Run every command from `build123d/`. All measurements are at origin/main
38af4ad plus this branch.

What the spike delivers:

- the vendored font in `assets/fonts/inter/`;
- `holders/label_text.py`, with `load_font` and `fit_text`;
- the demo model `holders/label_demo.py`;
- `tests/test_label_demo.py`, 12 tests;
- the demo exports in `docs/exports/label_demo*`.

The demo model is smoke-tagged, so it is registered for the test harness but
left out of the manifest and the app catalog.

## Q1 Font rendering

**Font: Inter Bold 4.001, static TTF** ([rsms/inter v4.1 release](https://github.com/rsms/inter/releases/tag/v4.1),
`extras/ttf/Inter-Bold.ttf`, sha256 `28831609…947f`), licensed OFL 1.1. It is
vendored with its licence in `assets/fonts/inter/`, and the NOTICE row is in
[provenance.md](provenance.md).

Each candidate was built with `Text(s, font_size=10, font_path=…)` and then
`extrude(…, 0.8)`:

| font file | string | bbox X × Y (mm) | glyph faces | holes | solids | valid | Text + extrude (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Atkinson Hyperlegible Bold (static) | Filament | 40.61 × 7.70 | 9 | 2 | 9 | yes | 12 + 19 |
| | PLA Black | 47.18 × 6.80 | 8 | 5 | 8 | yes | 7 + 13 |
| | PETG-CF | 40.67 × 6.92 | 7 | 1 | 7 | yes | 6 + 14 |
| | aeo | 16.44 × 5.22 | 3 | 3 | 3 | yes | 6 + 10 |
| **Inter Bold (static)** | Filament | 41.23 × 7.78 | 9 | 2 | 9 | yes | 7 + 13 |
| | PLA Black | 48.08 × 7.38 | 8 | 5 | 8 | yes | 6 + 14 |
| | PETG-CF | 43.59 × 7.47 | 7 | 1 | 7 | yes | 5 + 11 |
| | aeo | 17.17 × 5.63 | 3 | 3 | 3 | yes | 6 + 8 |
| Inter[opsz,wght] (variable, google/fonts) | Filament | 43.09 × 7.91 | 10 | 1 | 10 | **NO** | 12 + 21 |
| Roboto[wdth,wght] (variable, google/fonts) | PLA Black | 37.83 × 7.60 | 15 | 0 | 15 | **NO** | 10 + 19 |

- **Static fonts build valid solids with correct counters.** "aeo" gives 3
  holes, one per letter. "PLA Black" gives 5 holes: P, A, two in B, and a.
- **Variable fonts build invalid solids** with the wrong holes. OCCT does not
  union their overlapping contours, so only static TTFs are allowed.
- **Roboto is now OFL, not Apache.** The google/fonts copy ships
  `ofl/roboto/OFL.txt`. This answers plan-review A2.
- **Why Inter over Atkinson:** Atkinson's letter gaps are too narrow. See Q2.

**Missing or bad font (the fallback test).** Two calls fail silently:

- `Text('PLA', 10, font_path='/nonexistent/Nope.ttf')`;
- `Text('PLA', 10, font_path=<a .txt file>)`.

Both return 3 faces, 17.68 mm wide, **with no error and no warning**. A bad
`font=` name only logs a FreeSans substitution warning.

The cause is in build123d's `Text`: it calls `check_font(path)` and then
silently falls back to `find_font(name)`. It also renders by font *name*, so
an installed system font of the same family could win.

`holders/label_text.load_font()` closes these gaps (proved by
`test_missing_or_bogus_font_fails_loudly` and
`test_vendored_font_resolves_to_its_own_file`):

- a missing file raises `FileNotFoundError`;
- a non-font file makes fontTools raise;
- `RuntimeError` is raised unless OCCT's BOLD aspect resolves to exactly the
  vendored path.

**Characters the font lacks are also substituted silently.**
`text_sketch('🙂')` still returns 3 faces, drawn from some fallback font.
Inter covers all printable ASCII, plus é, ü, ° and ✓ (2,852 code points), but
not emoji. Charset validation therefore belongs in the model and the route,
not in `Text`. See DECISIONS.

**Mirroring.** `print_orientation` is metadata only (plan-review A1):
`scripts/export.py` writes the part unrotated. So the card is modelled in the
print frame, with the visible face on the bed at Z = 0. `label_demo.parts()`
mirrors the text about the YZ plane, so the card reads left to right once it
is flipped face up.

`test_text_is_mirrored_for_face_down` proves the mirror on a section of the
"Filament" inlay. In the model frame the rightmost glyph is a cap-height `F`.
The area of its +X half is more than 1.5× that of its −X half: the stem is on
+X.

- mirrored: ratio 2.38, as built;
- unmirrored: ratio 0.87, with the rightmost glyph a `t`, so the test fails.

## Q2 fit_text: autoscale and centre

`holders/label_text.fit_text(text, box_w, box_h, margin, depth=0.6)` returns
`FittedText(part, scale, min_stroke, min_gap)`. That is a NamedTuple whose
first two fields are the specified `(Part, scale)`. The other two fields are
the report Q2 asks for.

The function:

1. builds the text at 10 pt;
2. scales it uniformly by `min((W−2m)/w, (H−2m)/h)`;
3. centres the ink bounding box on the origin.

Centring uses the **ink bbox**, not the baseline. A string with a descender
therefore sits a little higher.

Inter Bold on a 60 × 14 card with a 1.5 mm margin:

| string | scale | ink bbox (mm) | centre | min stroke | min gap | time |
| --- | --- | --- | --- | --- | --- | --- |
| Filament | 1.382 | 57.00 × 10.76 | (0, 0) | 1.24 | 1.27 | 1.8 s |
| PLA Black | 1.185 | 57.00 × 8.75 | (0, 0) | 1.14 | 1.33 | 1.7 s |
| PETG-CF | 1.308 | 57.00 × 9.77 | (0, 0) | 1.46 | 1.44 | 1.2 s |
| W (1 char) | 1.512 | 14.96 × 11.00 | (0, 0) | 1.91 | 3.54 | 0.2 s |
| PETG-CF Black (13 ch) | 0.779 | 57.00 × 5.83 | (0, 0) | **0.75** | **0.86** | 2.5 s |
| Bambu PLA Matte Charcoal (24 ch) | 0.432 | 57.00 × 3.23 | (0, 0) | **0.39** | **0.08** | 2.8 s |

The centre is within 4e-15 mm. Most of the time goes on the stroke/gap scan;
with `measure=False` a fit takes about 0.1 s. `test_fit_text_fills_box_and_centres`
pins the first four rows, and `test_fit_text_reports_unprintable_long_string`
pins the last.

**How stroke and gap are measured.** The stroke is the narrowest disc
diameter whose morphological opening (shapely `buffer(-r).buffer(r)`)
removes a piece at least 0.75 r thick. Corner slivers stay below that unless
the corner is sharper than about 16°. The scan runs upward, because
bisection is not monotonic here. The gap is the same metric applied to the
complement inside the padded bbox.

There is one known artefact: Inter's 'M' crotch reads as a 0.18 mm gap at
10 pt (the 0.08 in the last row), which is an acute notch, not a real gap.

**Why Inter, not Atkinson.** At 10 pt the strokes are similar, but the gaps
are not:

| font | Filament | PLA Black | PETG-CF |
| --- | --- | --- | --- |
| Atkinson Bold | stroke 0.88, gap 0.36 | stroke 0.94, gap 0.36 | stroke 1.28, gap 0.36 |
| Inter Bold | stroke 0.90, gap 0.92 | stroke 0.96, gap 1.12 | stroke 1.12, gap 1.10 |

Atkinson's narrow gaps are the tailed 'l' next to 'a' and the E→T bars.
With the text flush on the bed, a gap is a base-colour first-layer feature,
so Atkinson's gap at label scale (0.36 × 1.4 = 0.5 mm) is one marginal line.

**Inter Bold over all printable ASCII at 10 pt** (cap height 7.275), from
`PYTHONPATH=. uv run python scripts/labels_ascii_sweep.py`:

- thinnest strokes: `$` 0.58, `%` 0.82, `*` 0.86, `e` 0.90, `a` 0.96;
- narrowest gaps: `"` 0.82, `$` 0.88, `e` 0.92, `f` 0.96;
- alphanumerics: minimum stroke 0.90 (`e`), minimum real gap 0.92 (`e`).

**The printability bound is set by the card width.** A stroke of at least
0.9 mm needs a scale of at least 1.0. Inter Bold advances about 5.2 mm per
character at 10 pt, so 57 mm of ink fits about 11 characters per line. A
second line does not help much, because the width still binds.

On a 60 × 24 card, with each line fitted on its own:

| lines | scale | min stroke |
| --- | --- | --- |
| "Bambu PLA" / "Matte Charcoal" | 1.03 / 0.78 | 0.99 / **0.70** |
| "PETG-CF" / "Black" | — | 1.46 / 1.30 |

On a 44 mm card (the spool_width = 50 endpoint), one-line "PLA Black" is
0.82 and "Filament" is 0.89.

The 24-character maximum in L2's spec therefore cannot hold a 0.9 mm stroke
on any card that fits the panel. This is why the stroke floor is a
*proposed* row in DECISIONS.

## Q3 Multi-colour 3MF: face down, text flush

`uv run python -m holders.label_demo` writes these files to `docs/exports/`:

| file | what |
| --- | --- |
| `label_demo.3mf` | one object, two parts: base on filament 1, inlay on filament 2 |
| `label_demo_base.stl`, `label_demo_inlay.stl` | the two parts, for a manual assembly |
| `label_demo_debossed.stl` | single-colour, face down. Identical geometry to the base |
| `label_demo_raised.stl` | single-colour, face up, text raised 0.6 mm and not mirrored |

The card is 60 × 14 × 1.6 mm, with corner radius 1.5 and a 0.4 mm chamfer on
the bed and top edges. The text is "PLA Black". The inlay is the card ∩ the
mirrored text over Z 0–0.6 mm, and the base is the card minus the inlay.

Both parts touch Z = 0, their volumes sum to the card's, and they overlap by
less than 1e-6 mm³ (`test_inlay_is_flush_on_the_bed_and_base_fills_the_rest`).

**build123d's stock export splits the text into one object per glyph.**
`Mesher.add_shape([base, inlay])` gives this structure, read from
`3D/3dmodel.model`:

```
<build> 9 × <item>   ← base + one per glyph solid; the text Compound is flattened
no basematerials     ← .color / .label sit on the Compound, so they are lost
```

A `Compound` and a list of `Part`s produce the same output, because
`add_shape` flattens a Compound into its solids. In Bambu Studio this is
nine separate objects: `Object_1` to `Object_9`, all on filament 1
(`test_stock_mesher_splits_text_into_one_object_per_glyph`).

**`label_demo.export_3mf_one_object` writes the 3MF core-spec assembly.**
It uses lib3mf through `Mesher`'s own wrapper and mesh helpers, so it adds no
new dependency:

```
<basematerials id="1"> base #1A1A1A, inlay #F5F5F5
<object id="3" name="base"  pid="1" pindex="0"> mesh
<object id="4" name="inlay" pid="1" pindex="1"> mesh (8 shells)
<object id="2" name="label_demo"> <components> 3, 4
<build> 1 × <item objectid="2">
+ Metadata/model_settings.config: object 2 → part 3 extruder 1, part 4 extruder 2
```

**Bambu Studio 02.08.02.61** (the Linux AppImage, run headless) reads the
file with
`bambu-studio --export-3mf rt.3mf docs/exports/label_demo.3mf`, and its own
re-exported `Metadata/model_settings.config` shows:

```
<object id="3"> name=label_demo extruder=1
  <part id="1" subtype="normal_part"> name=base  extruder=1  mesh_stat … edges_fixed=0 facets_removed=0 facets_reversed=0
  <part id="2" subtype="normal_part"> name=inlay extruder=2  mesh_stat … edges_fixed=0 facets_removed=0 facets_reversed=0
```

So it is **ONE object with two parts, with the inlay on filament 2 and no mesh
repairs**. Bambu Studio ignores the 3MF mesh names and the basematerial
colours. Without the sidecar, the parts are called `label_demo` and
`label_demo_2` and both go on filament 1. Two more findings:

- **Do not declare `Application=BambuStudio` in the model metadata.** Bambu
  Studio then treats the file as a full project and **segfaults** (rc 139).
  The test asserts that the metadata is absent.
- **Headless two-filament slicing did not work.**
  `--slice 0 --load-filaments "<PLA>;<Generic PLA>"` loads both filaments,
  but logs `no filament colors found in projects` and slices everything with
  filament 1, even when `project_settings.config` carries two colours. That
  is a CLI limitation for non-project 3MFs. The object tree above is the
  evidence; the real two-colour slice is a GUI check for Sean.

**PrusaSlicer has not been checked.** No Linux build is available here:
PrusaSlicer's latest GitHub releases (2.9.6, 3.0.0-alpha12) ship no Linux
assets. Two things are unverified: whether PrusaSlicer loads the
`<components>` object as one multi-part object, and whether it reads any
filament assignment (the sidecar is Bambu's format). **Hand-off to Sean:** open `docs/exports/label_demo.3mf` in
Bambu Studio and PrusaSlicer, and record the object tree and one two-colour
slice here.

**Single-colour fallback, sliced on the H2S** (Bambu Studio CLI, Bambu Lab
H2S 0.4 nozzle, 0.20mm Standard @BBL H2S, Bambu PLA Basic):

| variant | layers | layer-1 features | layer-1 retractions | layer-1 G1 moves | print time |
| --- | --- | --- | --- | --- | --- |
| debossed, face down (`_debossed.stl`) | 8 | 10 outer + 11 inner walls, 4 bottom-surface regions | 47 | 1644 | 255 s |
| raised, face up (`_raised.stl`) | 11 | 1 outer + 1 inner wall, 1 bottom surface | 4 | 349 | 263 s |

The **raised face-up card has the cleaner first layer**: one rectangle.
The debossed card prints its first layer around 8 letter holes, and bridges
the ceiling of the recess at Z = 0.6.

What the H2S profile does to flush text, from `; elefant_foot_compensation`
in the gcode and the `process/` JSON:

- `elefant_foot_compensation = 0`. `fdm_process_single_0.20.json` overrides
  the common 0.15, so glyphs are not shrunk on layer 1.
- `initial_layer_line_width = 0.4`.
- `wall_generator = arachne`, with `min_bead_width = 85%` and
  `min_feature_size = 25%`.

So a 0.9 mm stroke is about two first-layer lines. Arachne keeps strokes
down to about 0.34 mm as single beads instead of dropping them. First-layer
squish widens the inlay into the base by roughly the elephant's foot; on a
two-colour part that only matters where a gap is under about 0.5 mm.

With a 0.6 mm inlay (3 layers at 0.2), each of the first 3 layers prints
both filaments, so expect about 3 filament swaps per plate (AMS purge per
swap).

## Q4 Web: string params

- **Model side: already supported.** `holders/registry.py:66` lists
  `"string"` as a valid kind, and `:108` checks that the value is a `str`.
  `scripts/manifest.py:79` emits `"string": ("kind", "default")`, and
  `:215-216` rejects only unknown kinds. `label_demo` declares
  `Param('text', 'string', 'PLA Black')` and registers cleanly. It is smoke,
  so `test_demo_is_smoke_and_out_of_catalog` checks it never reaches the
  manifest.
- **UI: a text input already exists.** `components/ParamRow.tsx:45-47`
  dispatches `"string"` to `StringRow` (`:196-224`), an
  `<input type="text">`. `components/BdDetailPage.tsx:320` renders the
  shared `ParamRail`, so a build123d model with a string param gets the input
  with no UI change. The input has **no `maxLength`**.
- **Validation: none.** `app/api/bd-render/route.ts:255-256` coerces
  anything with `String(raw)`: no length cap and no charset check. The
  Python service's `resolve_values` checks only the type.
- **Gaps for L4.** Add an optional `maxLength` (and a charset rule) to
  `Param`, the manifest per-kind table (`"string"` row), `lib/models/bd-manifest.ts`,
  `StringRow` (`maxLength`), `route.ts` and the Python validation. Without a
  cap, a long string costs render time, and the font's silent substitution
  (Q1) lets emoji through.
- **Neighbour pst-fcjqj (plan-review A8)** adds a `filename` flag to the same
  `Param` dataclass and manifest table. It also rewires the download naming
  in `BdDetailPage.tsx` and the bd-render `content-disposition` header. L4
  touches the same files and the same pattern (an optional per-kind field),
  so whichever lands second rebases onto the other's field table.

## Q5 Service: bd-render

These changes are all for L4, and this spike changes none of them (plan-review
A7):

1. **Font in the image.** `services/bd-render/Dockerfile` copies only
   `holders`, `multibuild`, `openconnect` and `scripts` (`:38-41`). Add
   `COPY build123d/assets ./assets`. `label_text.FONT_PATH` resolves through
   `holders/../assets/fonts/inter/`, which matches the `/build123d` layout,
   and `load_font` fails loudly if the file is missing. This adds 420 KB to
   the image.
2. **3MF export.** `render_worker.py:12/:54` accepts only `glb|stl`. Add
   `3mf`, calling a shared multi-part writer: L2 should move
   `export_3mf_one_object` to `scripts/export.py`. Add `"3mf"` to
   `BdRenderFormat` (`lib/render-service/bd-client.ts:23`), to the route's
   format check (`route.ts:65-67`), to `CONTENT_TYPE`
   (`model/3mf`), and to the `content-disposition` attachment branch. The
   cache key already includes the format.
3. **lib3mf is already in the image and already imported.** It comes in
   transitively through build123d (`uv.lock:41`; on linux-aarch64, `:45`
   substitutes `py-lib3mf`). The image is x86_64 (`Dockerfile:15`), so the
   1.575 MB `lib3mf-2.5.0-py3-none-manylinux2014_x86_64` wheel installs:
   6.9 MB on disk, 5.3 MB of it `lib3mf.so`. `uv sync --frozen` already
   installs it. `python -X importtime -c "import build123d"` shows
   `lib3mf` taking **5.8 ms of the 1.50 s** build123d import, because
   `build123d.mesher` imports it at module load.
4. **Cold start: no change.** Writing the 3MF for "PLA Black" takes 0.21 s
   after the 0.30 s build, and makes a 184 KB file.

## Q6 Card envelope

The front panel is `Box(spool_width, WEB=2.4, panel_height)` at
y = `end_y` (spool_cradle.py:541). Its outer face is at `end_y + 2.4`, facing
+Y toward the user.

| case | panel W × H (mm) | contact_z |
| --- | --- | --- |
| default (66) / ams 66 / bambu 67 | 66 (67) × 58.90 | 53.90 |
| spool_width = 50 / 70 | 50 / 70 × 58.90 | |
| lip 0 / lip 15 | 66 × 53.90 / 68.90 | |
| d190 a25 / d205 a45 | 66 × 78.14 / 53.17 | |

The table below gives the loaded spool's outer surface relative to the panel
face, at heights above the panel top. Positive values are proud of the face.

| case | +0 mm | +5 mm | +10 mm | +20 mm |
| --- | --- | --- | --- | --- |
| default | −3.3 | +0.2 | +3.2 | +8.2 |
| lip 15 | −5.1 | −2.5 | −0.1 | +3.5 |
| d190 a25 | −3.1 | −1.3 | +0.3 | +2.5 |

What this means for the card:

- The panel is at least 53 mm tall in every case, so card height is not
  constrained. Width binds: the panel width is the spool width, 50–70 mm.
- **A card that slides in from the top can only be inserted with the spool
  out.** Above the panel top the spool is proud of the face within 5–10 mm.
  That is acceptable, because the label changes when the spool changes.
- **Side-slide is blocked by the neighbouring cradle.** At cadence 75 with a
  66 mm spool, the gap is only 9 mm.

**Proposed holder: two side rails, a bottom lip, and a card that slides in
from the top.** This is a front view, looking at the panel face (−Y):

```
        ┌ panel top ───────────────────────────────┐
        │  ║                                    ║  │   ║ = rail, 3.0 wide
        │  ║ ┌────────────────────────────────┐ ║  │   lip overlaps card 1.5
        │  ║ │   PLA Black  (flush inlay)     │ ║  │   card W = panel W − 6
        │  ║ └────────────────────────────────┘ ║  │
        │  ╚════════════════════════════════════╝  │   bottom lip = stop
        │                front panel               │
```

This is a section through one rail (X–Y):

```
   panel face ─┤▓▓▓│
               │   │← slot 2.0 deep (card 1.6 + 0.2 per side)
               │▓▓▓▓▓▓▓▓   ← lip 1.2 thick, overlapping the card edge by 1.5
   rail proud of the face: 2.0 + 1.2 = 3.2 mm
```

The proposed envelope is in DECISIONS. The card's visible face is its
**bed** face, so it is flat and chamfered 0.4 mm, which doubles as the
rail's lead-in.

The text margin at the sides and bottom must cover the lip:
≥ 1.5 + 0.5 = **2.0 mm** (the demo uses 1.5). At the 50 mm endpoint the card
is 44 mm wide, and one line of about 8 characters holds a 0.9 mm stroke.

## DECISIONS

| # | Topic | Decision | Evidence |
| --- | --- | --- | --- |
| D1 | Font | **Inter Bold 4.001, static TTF**, OFL 1.1, vendored in `assets/fonts/inter/`. Only static fonts: variable TTFs build invalid solids | Q1 table; provenance row |
| D2 | Font loading | Load only through `label_text.load_font` / `text_sketch`. A missing file, a non-font or a mismatched OCCT face raises; never call `Text(font_path=…)` directly | Q1 fallback test; 2 tests |
| D3 | Mirroring | Model in the print frame, face down, and **mirror the text about YZ explicitly**. `print_orientation` stays `(0, 0, 1)`; it is metadata only | Q1 mirror test, ratio 2.38 vs 0.87 |
| D4 | Fit rule | `fit_text`: build at 10 pt, uniform scale = min over both axes of (box − 2·margin), centre the ink bbox. It reports `min_stroke` / `min_gap`, and the **model** clamps | Q2 table; 5 tests |
| D5 | Stroke floor | *proposed:* **0.7 mm** for a flush inlay (cosmetic, ≥ 1.75 first-layer lines, kept by Arachne). 0.9 mm for raised text. **Sean to confirm**: a 0.9 floor allows only about 11 characters on a 60 mm card | Q2 bound; Q3 profile |
| D6 | Text length / lines / charset | *proposed:* printable ASCII `0x20–0x7E` only, max 24 characters. One line if `min_stroke` ≥ floor; otherwise two lines split at the space nearest the middle, with a common scale; otherwise reject with the stroke in the message | Q1 substitution; Q2 two-line table |
| D7 | Card envelope | *proposed:* **W = panel width − 6** (60 at the default 66, 44 at 50, 64 at 70) × **20** × **1.6** mm, corner radius 1.5, 0.4 mm chamfer on both faces. Text margin 2.0 at the sides and bottom | Q6 |
| D8 | Holder | *proposed:* two side rails plus a bottom lip, card slides in from the top. Slot 2.0 deep (0.2 mm clearance per side on 1.6); lip 1.2 thick, 1.5 overlap; rails proud of the face 3.2 mm; insert with the spool removed | Q6 clearance table |
| D9 | Inlay depth | **0.6 mm** (3 layers at 0.2). L2 may expose 0.4–0.8 | Q3 |
| D10 | 3MF structure | **One components object** whose parts are `base` (filament 1) and `inlay` (filament 2), plus the Bambu `Metadata/model_settings.config` sidecar. Never `Application=BambuStudio`, and never build123d's stock `Mesher.add_shape` for a multi-part label (it writes one object per glyph). **Revised (L2):** Bambu Studio's "not from Bambu Lab, load geometry data and color data only" notice comes from the absent `project_settings.config` (Plater.cpp `load_files`); it keeps every part's `extruder`, so the inlay stays on filament 2. No `project_settings.config` is written: it would load our print config over the user's presets. The writer lives in `scripts/export.py` | Q3 object trees; 2 tests |
| D11 | Single-colour fallback | **Raised, face up** (cleanest first layer: 4 vs 47 retractions). The debossed face-down STL is the base alone; offer it, but not as the default | Q3 slice table |
| D12 | Web (L4) | `StringRow` exists. Add `maxLength` and the charset rule end to end: `Param` → manifest `"string"` row → `bd-manifest.ts` → `StringRow` → `route.ts:255` → Python. Rebase with pst-fcjqj's `filename` field | Q4 |
| D13 | Service (L4) | `COPY build123d/assets ./assets`; `render_worker` format `3mf` using the shared writer, which L2 moves to `scripts/export.py`; `BdRenderFormat` / route / `CONTENT_TYPE` `model/3mf`. No new dependency, and no change to the image or cold start beyond the 420 KB font | Q5 |
| D14 | Slicer check | Bambu Studio's object tree is verified headless. **Open:** a two-colour GUI slice in Bambu Studio and PrusaSlicer, by Sean, recorded here | Q3 |
