# Tombstone sign

`holder-tombstone-sign` (epic pst-tl4ac; S1 pst-tl4ac.1, S3 pst-tl4ac.3) is a
3D-printable version of the Poppy Street Spooks song-request poster. It is
a flat tombstone-shaped plate. The poster's text, the ghost-with-poppy and a
QR code stand 0.6 mm proud of its face in up to eight colours. Two pockets
in its bottom edge take a separately printed stake (S2,
`holder-tombstone-stake`). It lives in the `household` catalog category.

Presets:
- **default**: 240 × 300 × 6, eight colours.
- **one-ams**: four colours (base, bone, pumpkin, poppy), one AMS.
- **two-colour**: bone on ground; the QR dark modules are holes.
- **pinned**: 8 mm plate with a pin cross-hole.
- **small**: 160 × 200 with a 74 mm QR. Reduced content: the two detail
  lines are blank, because the 68-character detail_1 needs 192.55 mm of
  width on two lines against a 144 mm box. Shorter copy can fill them later.

| Controls | Domain / behaviour |
| --- | --- |
| Width / height | 100–325 / 150–320 mm (the H2S single-nozzle bed, printed flat); height must also be ≥ the arch radius + 6 mm |
| Thickness | 5–12 mm; `retention = pin` needs ≥ 7.8 mm |
| Arch | `round` (radius = width / 2) or `shoulder` (radius = width / 3, flat shoulders) |
| Margin | 3–20 mm (default 8) inset from the outline; the gap between bands is half of it |
| Eyebrow, title, scan line, host, footer | Printable ASCII, ≤ 24 characters each; a blank line is left out |
| Detail 1, detail 2 | Printable ASCII, ≤ 72 characters each |
| QR size | 50–300 mm square, including the 4-module quiet zone; the module pitch must be ≥ 2.0 mm |
| Colours | 2–8 filaments, including the plate (see below) |
| Stake retention | `friction` or `pin` |

The QR encodes `https://{host}`, as the poster encodes its site URL. There
is no separate link field.

Values that cannot be laid out raise a `ValueError` that names the limit
and the minimum value that would work. This covers the width needed for the
pockets, a height below the arch radius, the art row against the inset
width, the QR pitch, the pin thickness, and the height needed for the text
and art. A line whose stroke would fall below the 0.9 mm raised stroke floor
raises the label card's error, prefixed with the line's name. This is the
one text gate: no line is ever dropped silently.

## Layout

From top to bottom, inside a `margin` inset of the outline:

| Band | Face | Role | Wrap | Weight |
| --- | --- | --- | --- | --- |
| eyebrow | Lexend Medium, capitals | dim | 1 line | 6 |
| title | Creepster | pumpkin | 1 line, else 2 | 22 |
| art row | ghost (left) + QR panel (right) | — | — | fixed `qr_size` |
| scan line | Lexend Bold | bone | 1 line | 8 |
| detail 1 | Lexend Medium | dim | 1 line, else 2 | 10 |
| detail 2 | Lexend Medium | dim | 1 line, else 2 | 6 |
| host | Lexend Bold | pumpkin | 1 line | 6 |
| footer | Lexend Medium, under a 0.91 mm rule | dim | 1 line | 8 |

The content starts where the arch is half the inset width and ends
`margin` above the bottom edge. Raised content adds material, so unlike
the old inlays it may run over the pockets. Bands are `margin / 2` apart.
The art row takes `qr_size`. The text budget B is what is left, and must be
at least 40 mm.

Each present line first gets its **need**: the height at which its stroke
on its own face clears 0.91 mm (the 0.9 floor plus margin), at the fewest
lines whose width fits the chord. The rest of B is shared out by the
weights. If the needs exceed B, the hungriest line raises the stroke-floor
error. A line that is too wide for the chord at its band's top moves down
until it fits. That is how the capitals eyebrow leaves the arch on
**small**. The band tops come from one pass at the weights alone, then one
re-pass with the needs measured at those tops.

At the defaults, B = 140.99 mm, the needs total 76.21 mm and the bands are
11.9 / 29.0 / 17.6 / 32.9 / 16.7 / 15.9 / 17.0 mm (eyebrow … footer).

The ghost is 0.47 × the panel height (the poster's ratio). Ghost and panel
are centred as a pair with a `margin` gap between them. The panel is a bone
square with 8 mm corners; its padding is the QR's quiet zone.

Differences from the paper poster:
- The host is its own band, not set inline after detail 2.
- The eyebrow has no letter-spacing: the poster's tracking pushed its width
  to 110.40 mm against a 112.00 mm box.
- The sidewalk line ("Please keep the sidewalk clear for neighbors") is
  dropped for now. It needs 238 mm on one line against a 224 mm box.
- The ember highlights on the petals print solid (the poster draws them at
  0.55 opacity, which has no 3D analogue).

## Colours (raised, printed face up)

Every colour is a raised body exactly 0.6 mm (`INLAY_DEPTH`, three layers)
on the top face. All of them lie in one slab and never overlap; where two
roles meet they share an edge. Where the art overlaps, the later SVG
element wins: the flower trims the ghost body and the highlights trim the
petals. Eyes, mouth and poppy centre are holes, so the plate shows through.

Roles, in order (filament N is role N):

| # | Role | Preview | Used for |
| --- | --- | --- | --- |
| 1 | base | #120a1e | the plate |
| 2 | bone | #f4ecdc | ghost body, QR panel, scan line |
| 3 | pumpkin | #ff7a1a | title, host |
| 4 | poppy | #e5322d | petals |
| 5 | leaf | #5b8f3a | leaf |
| 6 | dim | #b7a9c9 | eyebrow, detail lines, footer and its rule |
| 7 | ink | #0a0a0a | QR dark modules |
| 8 | ember | #ff5a4e | petal highlights |

`colours` = N keeps the first N roles. Each inactive role folds until it
lands on an active one: ember → poppy, ink → hole, dim → bone,
leaf → pumpkin, poppy → pumpkin, pumpkin → bone. So **one-ams** (4) prints
base, bone, pumpkin and poppy, and its QR dark modules are holes in the
bone panel. **two-colour** prints everything raised in bone.

Parts are named after their filament. The bake writes `<preset>-<part>.stl`
for each part, plus one 3MF object with one part per active filament (8 at
the default). The viewer GLB has one material per part. Same-filament
bodies are unioned, and QR dark modules are shrunk 0.01 mm, so no two
bodies of one filament meet only at an edge.

## Fonts and art

| Asset | Source | Licence |
| --- | --- | --- |
| `assets/fonts/creepster/Creepster-Regular.ttf` | Google Fonts | OFL 1.1 (`OFL.txt`) |
| `assets/fonts/lexend/Lexend-{Medium,Bold}.ttf` | googlefonts/lexend `fonts/lexend/ttf/` (fontmake statics) | OFL 1.1 (`OFL.txt`) |
| `assets/art/ghost-with-poppy.svg` | Sean's design from the show site | see `assets/art/NOTICE` |

`labels.label_text` takes a font path and style, and refuses a substituted
font. The variable-font instances extrude invalid solids, so only the
upstream statics are used. Creepster kerns some pairs into each other
("x" into "t"), so overlapping glyph solids are fused before the plate fuse.

`holders/sign_ghost.py` rebuilds the SVG's twelve primitives under their
full transform chain. `import_svg` composes a group's translate with an
element's rotate in the wrong order. Every region clears the 0.9 mm floor at
every preset (narrowest 1.86 mm on **small**). The only details dropped are
the two the SVG's own comment lists: the leaf vein and the seed dots.

## QR

The QR is encoded by segno 1.6.6 (`pyproject.toml`, pinned) at error level
**M** with no boost, and the version comes from the data. The default
`https://poppystreetspooks.com` (29 characters) is version 3: 29 modules plus
2 × 4 quiet, 37 in all. That gives a 100 / 37 = 2.70 mm pitch at the
default size and 74 / 37 = 2.00 mm on **small**. When `ink` is folded
away, the dark modules are holes in the bone panel. The decode test then
reads them as the base colour.

## Stake joint (`holders/signs.py`)

| Constant | Value |
| --- | --- |
| Pockets | 2, centred X = ±40 |
| Pocket | 8.0 wide × 35 deep × (thickness − 2 × 1.2 skin) |
| Clearance | 0.2 per side, every axis |
| Tenon | 7.6 × 34.6 × (thickness − 2.8); the stake's shoulder bears on the bottom edge |
| Pin | Ø3.2 on X at Y = 20, Z = thickness / 2; flat-topped teardrop section (1.33 mm flat roof) |

The stake (S2) imports only this module, so the pocket and the tenon
cannot drift apart.

## Printability

The sign prints flat, face up. The rims of both faces carry a 0.4 mm
chamfer (on the bed side, this relieves elephant's foot). In plan, the
outline corners are rounded 3 mm. Every raised feature has walls ≥ 0.9 mm
(the stroke floor), so the thin-wall check passes without an exclusion.

A pocket's roof is a flat 8 mm bridge, below `MAX_BRIDGE_MM` (10). The
audit's overhang check reads a flat ceiling as 90°. The tests therefore
first measure the unexcluded bridge (8.0 mm), then assert that every
downward face steeper than 45° lies in one of the planes listed by
`audit_exclusions`, and only then audit with those planes excluded (the
cartridge holder's precedent). The pin hole's 1.33 mm flat roof is listed
the same way.

The raised slab (Z thickness … thickness + 0.6, from `margin` up) is
excluded too, as on the label card: tapered glyph terminals read thin by
the wall march. The tests check that the box holds every raised part.
`tests/test_tombstone_sign.py` prints the per-preset numbers.

Worst-case load is wind on the face, which bends the plate about X at the
pockets. The plate prints flat, so the bending stress runs in-plane, along
the layers. Use PLA or PCTG; choose PCTG for a sign left outdoors.

## Stake

`holder-tombstone-stake` (S2 pst-tl4ac.2, `holders/tombstone_stake.py`) is
the ground stake. It is one flat blade, printed flat with the tenon face on
the bed. In plan, from the bottom up:

- a **shaft** `width` wide (25–60, default 40) ending in a 45° point. The
  45° is the included angle, so each flank is 22.5° and the point is
  width / (2 tan 22.5°) long (48.3 mm at 40). The tip stays sharp to enter
  the ground.
- 45° **shoulders** flaring the shaft out to the head, filleted 5 mm at the
  concave corner where they meet the shaft.
- a **head** `head_width` × `head_height` (87.6–140 × 20–60, default
  90 × 30). Its top edge bears on the sign's bottom edge.
- two **tenons** rising from the head's top edge at X = ±40
  (`signs.POCKET_XS`), each 7.6 × 34.6 × (thickness − 2.8).

`length` (150–320, default 300) is the whole printed length, tip to tenon
ends, so ≤ 320 is the bed bound. A length too short for the point, 8 mm of
straight shaft, the shoulders and the head is a named `ValueError` that
gives the minimum. So is a head narrower than 2 × (40 + 7.6 / 2) = 87.6 mm,
where the tenons would overhang the head.

Presets:
- **default**: 40 × 300 × 6, head 90 × 30.
- **long**: 320 mm.
- **cross-bar**: adds the cross-bar.
- **pinned**: 8 mm blade with the pin cross-hole, for the 8 mm pinned sign.

| Joint | Value |
| --- | --- |
| Thickness | The stake's `thickness` must equal the sign's: the tenon height is the contract's formula of it |
| Tenon Z | Flush with the bed face: stake Z 0 … tenon_t, never centred in the blade (a centred tenon printed flat is a 7.6 × 34.6 mm flat ceiling) |
| Assembly offset | sign Z = stake Z + 1.4 (`SKIN + JOINT_CLEARANCE`): the tenon sits centred in its pocket, 0.2 clear of every wall and 0.4 at the pocket end |
| Consequence | The sign rides 1.4 mm off the stake's mid-plane, a 1.4 mm step at each face of the joint |
| Pin (`retention = pin`) | `signs.pin_profile` on the sign's own axis (Y = 20 above the head top, the tenon's mid-height), so the plate hole and the tenon hole are one hole; needs thickness ≥ 7.8, so pair the **pinned** stake with the **pinned** sign |

`tests/test_tombstone_stake.py` builds the real sign and the real stake,
places the stake at the 1.4 mm offset, and checks that each tenon lies
wholly inside its pocket. It moves each tenon toward every pocket wall to
confirm the exact gap, at thickness 6 and 8, with and without the pin.

The **cross-bar** (`cross_bar`, length `cross_length` 100–320, default 200)
is a second blade, as wide and thick as the shaft. It is half-lapped across
the shaft 50 mm below the shoulders: each blade loses half its thickness
over the lap, and the pair interlock flush on both faces. It adds buried
face area against wind. Both blades print flat side by side, as one
two-solid part, each with its lap notch facing up so neither notch is a
ceiling. Turn the bar over to assemble.

Printability: every preset audits with no exclusion (worst overhang 45°,
the rim chamfers; no bridge), except the pinned preset. There, each
tenon's pin hole has the teardrop's 1.33 mm flat roof, listed in
`audit_exclusions` as the sign lists its own. Both rims carry the 0.4 mm
chamfer. So do the tenons' bed rims, so elephant's foot cannot eat the
0.2 mm joint clearance. Plan corners are rounded: 3 mm, and min(3,
head_width / 2 − 43.8) at the head top, so the rounding never reaches a
tenon root. At head_width 87.6 that corner is square, because the tenon's
outer face continues the head's side. Tenon, pin and lap faces are mating
faces and stay sharp. The viewer opens on the top face, which shows the step
down to the tenons; the bed face is one plane.

Worst-case load is wind on the face of the default 240 × 300 sign, pushing
through the blade's thickness. The sign's moment about X crosses the joint
in the two tenons. It spreads through the head and the 45° shoulders into
the shaft, and the soil resists it along the buried shaft. The blade prints
flat, so the bending stress runs along the layers. The tenons are the
weakest section. As an estimate (drag coefficient 1.2, centre of pressure
138 mm above the bottom edge), a 15 m/s gust puts about 1.5 N·m on the
joint. That is about 58 MPa in the two 7.6 × 3.2 tenons at thickness 6,
near PLA's strength, against about 22 MPa in 7.6 × 5.2 tenons at thickness
8. Use the 8 mm pinned pair where the sign faces wind. PLA or PCTG; choose
PCTG for a stake left outdoors.
