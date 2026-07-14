// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Ryobi P2860 backpack-sprayer strap saddle — openGrid shoulder, mirrored pair
//
// Hangs the Ryobi ONE+ 18V 4-gal backpack chemical sprayer (P2860) by
// draping its padded shoulder straps over two shoulder-like saddles,
// exactly as it hangs on a person (pst-ege). Print ONE OF EACH side
// (side=right + side=left) and snap them to the grid shoulder-width
// apart — saddle spacing is set by grid placement, not by the model.
//
// Load case (operator-confirmed): EMPTY sprayer only, ~6.8kg total →
// ~3.4kg nominal per saddle, designed with >=3x margin (~10kg). A full
// tank (~22kg) is explicitly OUT OF SCOPE.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived model is for personal use only; do not
// sell prints or files.
//
// === Form (recorded design assumptions, pst-ege) ===
//
// The saddle is a crowned prong projecting straight out from the wall
// (+Z): the strap loop encircles it the way it wraps a shoulder — the
// strap's ~70mm padded width lies ALONG the prong (the 80mm
// strap_channel), the two strands hang down either side of it, and the
// pad bears on the crowned top. Three curves do the work:
//   - Crown ACROSS the prong (R42 dome over the 42mm width): the pad
//     bends over a shoulder-like radius, no edge bearing.
//   - Saddle dip ALONG the channel (saddle_radius, default R55): a
//     circular trough sunk lip_height below the crest so the pad
//     settles centered instead of walking along the prong.
//   - Retention lip: the prong returns to full crest height for the
//     last 12mm before the tip; the dip's tip-side rise IS the lip's
//     smooth inner face. The plate blocks wallward escape.
// The dip's rise stays within 45 deg of vertical at defaults
// (asin(hc/R) ~ 39 deg), so the lip's inner face prints clean; at the
// extreme small-radius/tall-lip corner it locally exceeds 45 deg for a
// few mm near the crest — cosmetic droop zone, still support-free.
// When lip_height and strap_channel demand a chord wider than the
// channel, the dip is clamped to fit and the effective retention rise
// shrinks (documented, not an error).
//
// WHY MIRRORED (side @param): the crown apex is offset 6mm OUTBOARD,
// tilting the bearing surface down toward the sprayer hanging between
// the two saddles, so the leaning strap contacts flat instead of on an
// edge — same reason shoulders aren't cylinders. side=right is the
// right-hand saddle AS YOU FACE THE WALL (apex toward +X); side=left
// mirrors the body about X. THE SNAPS ARE NEVER MIRRORED — they are
// added outside the mirror so snap orientation is identical for both
// pieces (see pst-ozs for what happens when snap orientation is left
// to inference).
//
// === Print orientation: ZERO supports ===
//
// Prints snaps-down: snap faces are the first layers, then the plate,
// then the prong rising as a vertical column ~105mm. Every prong wall
// is vertical or leans inward going up; the dip trough and lip inner
// face stay within the 45 deg rule at defaults (above); the root flare
// fillet widens DOWNWARD onto the plate (never an overhang); the 3.2mm
// channels between snaps stay clear. Layer-line note: hanging load
// bends the prong so layers near the root see tension ACROSS the
// z-stack — at the 10kg design load the root section (42x30 solid,
// Z ~ 6300mm^3, M ~ 5.5N.m) sees ~0.9 MPa vs >=8 MPa typical layer
// adhesion, >8x margin on top of the 3x design margin.
//
// === Wall-hang orientation / load direction (operator-stated) ===
//
// USAGE-UP IS THIS MODEL'S +Y AXIS — stated for this design, not
// inferred from geometry (pst-ege; see pst-ozs). The saddle dip opens
// upward (+Y) and the strap drapes over the prong top. Directional
// snaps hang zrot(90): the strong non-flexing front nub (0.8mm deep vs
// 0.4, indicator-marked) points +Y — up the wall — so the lever-out
// moment the cantilevered prong puts on the top snap row bears on the
// rigid hook, and the flexy click-in side faces down where the moment
// presses the plate into the wall.
//
// === Snap grid: 2 x 3, justified ===
//
// 10kg design load at ~53mm effective cantilever puts ~5.5N.m of
// lever-out on the plate. On a 2x3 grid the top/bottom row couple arm
// is 56mm → ~100N pull spread over the two top-row snaps (~5kg each);
// a 2x2 grid's 28mm arm would double that. Six snaps also carry the
// ~100N shear at ~17N each. Plate is 2x3 tiles = 56 x 84mm.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

side = "right"; // @param enum choices=right|left filename group=saddle label="Which shoulder (as you face the wall)"
strap_channel = 80; // @param number min=56 max=110 step=1 unit=mm group=saddle label="Strap channel length (pad width + margin)"
saddle_radius = 55; // @param number min=40 max=80 step=1 unit=mm group=saddle label="Saddle dip radius (shoulder curve)"
lip_height = 12; // @param number min=6 max=20 step=0.5 unit=mm group=saddle label="Retention lip rise"
snap_lite = false; // @param boolean group=mount label="Lite openGrid snaps (3.4mm instead of 6.8mm)"

// @preset id="default" label="Right saddle (default)" side=right strap_channel=80 saddle_radius=55 lip_height=12 snap_lite=false
// @preset id="left" label="Left saddle" side=left strap_channel=80 saddle_radius=55 lip_height=12 snap_lite=false

// === Fixed geometry ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed of snap tops into the plate (st-vmn)
// Parts sink this far into the solid below them. Zero-overlap
// (face-kissing) unions leave detached shells / non-manifold tangent
// edges (st-v7k class).
bury = 0.6;

cols = 2;           // snap grid (justification in header)
rows = 3;

plate_w  = cols * snap_pitch;   // 56
plate_d  = rows * snap_pitch;   // 84
plate_t  = 6;
plate_z0 = snap_h - weld;
plate_zf = plate_z0 + plate_t;  // wall-plate front face

// Prong cross-section (fixed: strength-sized for the 10kg design load,
// not worth param-sweeping): 42 wide x 30 deep, crowned top.
prong_w   = 42;
prong_d   = 30;
prong_top = prong_d / 2;        // +15 (profile centered on plate center)
crown_r   = 42;                 // shoulder dome across the width
apex_off  = 6;                  // crown apex offset, OUTBOARD (+X on right)
edge_r    = 5;                  // convex profile rounding
flare_r   = 6;                  // root fillet flare onto the plate

lip_t     = 12;                 // full-height lip zone at the tip
prong_len = strap_channel + lip_t;
z_lip     = plate_zf + strap_channel;  // dip ends / lip starts here

// Saddle dip: circular trough of radius saddle_radius whose tip-side
// rise ends exactly at z_lip. Half-chord for a lip_height-deep dip,
// clamped so the trough never reaches closer than 1.5mm to the plate
// (at the clamp the effective rise is shallower than lip_height —
// documented in the header).
dip_hc_raw = sqrt(max(0, 2 * saddle_radius * lip_height - lip_height * lip_height));
dip_hc     = min(dip_hc_raw, (strap_channel - 1.5) / 2);
dip_cz     = z_lip - dip_hc;
dip_cy     = prong_top - lip_height + saddle_radius;

// PRINT_ANCHOR_BBOX at defaults (side=right, snap_lite=false):
//   X = plate_w = 2 * 28                       = 56
//   Y = plate_d = 3 * 28                       = 84
//   Z = 6.8 - 0.02 + 6 + (80 + 12)             = 104.78
PRINT_ANCHOR_BBOX = [56, 84, 104.78];

// === Snaps ===

// One openGrid snap in its own frame (front/strong nub toward +X),
// welded into a single solid — verbatim from ego_lb6500_blower_mount
// (st-0of), where it's verified watertight + single-component for both
// snap depths. openGridSnap models its click nubs as face-touching
// solids whose root tangent line survives as a non-2-manifold edge;
// each 0.3mm shim straddles a nub/core contact plane (local x=12.4)
// and volumetrically fuses nub to core on both CGAL and Manifold. The
// 14mm-wide front nub's shim widens to 14.6; the rear nub's sits 0.65
// higher (its root rides above the base band in the directional
// variant). NEVER re-derive snap geometry — the browser pipeline can
// only resolve vendored libs/, so this wrapper is kept textually
// identical across models: fix a bug here, apply it to the siblings.
module welded_directional_snap() {
    base   = snap_lite ? 0 : 3.4;
    root_z = max(0, base - 0.01);
    root_h = snap_lite ? 0.61 : 0.62;
    openGridSnap(lite = snap_lite, directional = true,
                 anchor = BOT, orient = UP, spin = 0);
    for (a = [90, 270])                       // side nubs
        zrot(a) translate([12.4, 0, root_z])
            cuboid([0.3, 11.6, root_h], anchor = BOT);
    translate([12.4, 0, root_z])              // front (strong) nub
        cuboid([0.3, 14.6, root_h], anchor = BOT);
    zrot(180) translate([12.4, 0, base + 0.64])  // rear (click) nub
        cuboid([0.3, 11.6, 0.62], anchor = BOT);
}

// One snap per tile on the 28mm pitch, XY centered. zrot(90) turns
// each snap's strong front nub toward +Y — up the wall in usage
// (operator-stated orientation, header). Called OUTSIDE the side
// mirror on purpose: both mirror variants get identical snaps.
module grid_snaps() {
    for (cx = [0 : cols - 1], ry = [0 : rows - 1])
        translate([(cx - (cols - 1) / 2) * snap_pitch,
                   (ry - (rows - 1) / 2) * snap_pitch,
                   0])
            zrot(90) welded_directional_snap();
}

// === Body ===

// Prong cross-section (right-hand chirality, apex toward +X): a
// rounded-bottom rect capped by the crown circle, convex corners
// rounded via 2D shrink-then-grow offsets (2D only — no hull-backed
// 3D rounding, st-7x7/st-560). Built as a BOSL2 region so the same
// shape feeds both linear_extrude (via the region() module) and
// offset_sweep (which needs the path data, not module geometry).
function prong_profile() =
    let (
        base = intersection([
            rect([prong_w, prong_d],
                 rounding = [0, 0, edge_r + 3, edge_r + 3]),
            move([apex_off, prong_top - crown_r], circle(r = crown_r))
        ])
    )
    offset(offset(base, r = -edge_r, closed = true),
           r = edge_r, closed = true);

// Saddle dip cutter: cylinder lying along X, guarded by a box so
// extreme params can never gouge the plate. Both pieces overshoot the
// prong in X (st-n4v: no coplanar cut faces).
module dip_cutter() {
    intersection() {
        translate([0, dip_cy, dip_cz])
            xcyl(r = saddle_radius, h = prong_w + 24);
        translate([0, dip_cy, (plate_zf + 1.5 + z_lip + 8) / 2])
            cuboid([prong_w + 30, 2 * saddle_radius + 10,
                    z_lip + 8 - (plate_zf + 1.5)], anchor = CENTER);
    }
}

// Prong: root flare fillet onto the plate (offset_sweep bottom flare —
// stacked-offset VNF, not hull-backed), then the plain extruded shaft,
// minus the dip. The flare segment and shaft overlap by bury.
module prong() {
    difference() {
        union() {
            translate([0, 0, plate_zf - bury])
                offset_sweep(prong_profile(),
                             height = flare_r + bury + 2,
                             bottom = os_circle(r = -flare_r));
            translate([0, 0, plate_zf + flare_r])
                linear_extrude(height = prong_len - flare_r)
                    region(prong_profile());
        }
        dip_cutter();
    }
}

module body() {
    translate([0, 0, plate_z0])
        linear_extrude(height = plate_t)
            rect([plate_w, plate_d], rounding = 8);
    prong();
}

union() {
    grid_snaps();  // never mirrored — see header
    if (side == "left") mirror([1, 0, 0]) body();
    else body();
}
