# Tombstone sign

`holder-tombstone-sign` (epic pst-tl4ac, S1 pst-tl4ac.1) is a 3D-printable
alternative to the Poppy Street Spooks song-request poster. It is a flat
tombstone-shaped plate with four lines of text and a QR code. Two pockets
in its bottom edge take a separately printed stake (S2,
`holder-tombstone-stake`). It lives in the `household` catalog category.

Presets:
- **default**: 240 × 300 × 6, four colours, inlaid, viewer opens on the face.
- **three-colour**: the same sign, with the title printed in bone.
- **raised**: one colour, printed face up, with the text and QR raised.
- **pinned**: 8 mm plate with a pin cross-hole.
- **small**: 160 × 200 with a 74 mm QR.

| Controls | Domain / behaviour |
| --- | --- |
| Width / height | 100–325 / 150–320 mm (the H2S single-nozzle bed, printed flat); height must also be ≥ the arch radius + 6 mm |
| Thickness | 5–12 mm; `retention = pin` needs ≥ 7.8 mm |
| Arch | `round` (radius = width / 2) or `shoulder` (radius = width / 3, flat shoulders) |
| Margin | 3–20 mm inset from the outline, and the gap between layout blocks |
| Title, headline, scan line, host | Printable ASCII, ≤ 24 characters each; a blank line is left out |
| QR link | Printable ASCII, ≤ 64 characters |
| QR size | 50–300 mm square, including the 4-module quiet zone; the module pitch must be ≥ 2.0 mm |
| Colours | `four` / `three` / `two` (see below) |
| Text style | `inlaid` (face down, flush) or `raised` (face up, one colour) |
| Stake retention | `friction` or `pin` |

Values that cannot be laid out raise a `ValueError` that names the limit
and the minimum value that would work. This covers the width needed for the
pockets, a height below the arch radius, the QR against the inset width, the QR pitch, the pin thickness,
and the height needed for the text and QR. A line whose stroke would fall
below the stroke floor (0.7 mm inlaid, 0.9 mm raised) raises the label
card's error, prefixed with the line's name.

## Layout

From top to bottom, inside a `margin` inset of the outline: title,
headline, QR, scan line, host. The content stops where the arch narrows to
half the inset width. Below that, the QR takes `qr_size` and each gap takes
`margin`. The four text bands share the rest 30 / 25 / 25 / 20 %. Each line is
autoscaled and centred in its band by `labels.label_text.layout_text`. Under
the arch, a width-bound line is shorter than its band. The text box is
therefore widened, by bisection, to the arch chord at the ink's top.

No inlay sits below **35 mm** from the bottom edge (`signs.INLAY_FLOOR`,
the pocket depth). A 0.6 mm inlay over a pocket would leave 1.2 − 0.6 =
0.6 mm of skin, below the 0.9 mm wall floor.

The default title, "Poppy Street Spooks", is width-bound under the round
arch: it fits on one line about 14 mm tall, smaller than the headline.
For a bigger title, use a shorter one or a shoulder arch.

## Colours (inlaid, printed face down)

Every colour is a flush 0.6 mm inlay in the bed face (`INLAY_DEPTH`). It is
modelled in the print frame and mirrored about YZ, as on the label card.

| colours | filament 1 | 2 | 3 | 4 |
| --- | --- | --- | --- | --- |
| four | base (stone) | bone: headline, scan line, host, QR light field | ink: QR dark modules | accent: title |
| three | base | bone: all text + QR light field | ink | — |
| two | base (also the QR light field: use a light filament) | ink: all text + QR dark modules | — | — |

Parts are named after their filament. The bake writes
`<preset>-<part>.stl` for each part, plus one 3MF object with one part per
filament. With `raised`, the plate is filament 1 and the raised text plus
QR dark modules are `bone`. The viewer GLB keeps a single material for
raised.

## QR

The QR is encoded by segno 1.6.6 (`pyproject.toml`, pinned) at error level
**M** with no boost, and the version comes from the data. The default URL
(29 characters) is version 3: 29 modules plus 2 × 4 quiet, 37 in all. That
gives a 100 / 37 = 2.70 mm pitch at the default size and 74 / 37 = 2.00 mm
on **small**. Dark modules are merged and shrunk by 0.01 mm, so that
diagonal neighbours never share an edge (a shared edge would make the ink
body non-manifold).

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

The sign prints flat, face down (inlaid) or face up (raised). The rims of
both faces carry a 0.4 mm chamfer (on the bed side, this relieves
elephant's foot). In plan, the outline corners are rounded 3 mm.

A pocket's roof is a flat 8 mm bridge, below `MAX_BRIDGE_MM` (10). The
audit's overhang check reads a flat ceiling as 90°. The tests therefore
first measure the unexcluded bridge (8.0 mm), then assert that every
downward face steeper than 45° lies in one of the planes listed by
`audit_exclusions`, and only then audit with those planes excluded (the
cartridge holder's precedent). The pin hole's 1.33 mm flat roof is listed
the same way.

The raised preset excludes its raised text and QR modules, as the label
card does: tapered glyph terminals read thin by the wall march.
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
