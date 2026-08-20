// SPDX-License-Identifier: CC-BY-NC-SA-4.0
//
// Disney ear hanger — saddle hanger for Disney-style ear headbands
// (Mickey/Minnie ears). The saddle arch projects out from the wall and
// the headbands drape over it. Three interchangeable wall mounts
// (mount_type): the original adhesive TAB, an openGrid snap backer, or a
// Multiconnect slot backer.
//
// REMIX / ATTRIBUTION (this is a derivative work, not original):
//   Original: "Disney Ear Hanger" by SpruceWayne
//     Creator: https://makerworld.com/en/@user_2791005939
//     Model:   https://makerworld.com/en/models/551375-disney-ear-hanger
//   (The MakerWorld id 469918 is the default print-profile/instance,
//    not an author profile.)
//   License: CC BY-NC-SA 4.0 (operator-verified — pst-15du). This is a
//     NON-COMMERCIAL license: do not sell prints or files, and share
//     any derivatives alike. Credit SpruceWayne on reshare.
//
// The openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic) and the Multiconnect slot from
// QuackWorks/Modules/multiconnectSlotDesign.scad — both CC BY-NC-SA 4.0,
// NON-COMMERCIAL. Same mount hardware the sibling models
// (apple_tv_4th_gen_holder, ryobi_p2860_strap_saddle) carry.
//
// === Mount options (mount_type, pst-3tum) ===
//
// The saddle geometry is IDENTICAL across all three mounts — only the
// wall attachment at the wall end changes, and it is the export-grid
// filename axis:
//   tab (default)  — the original rounded-square adhesive fin. Geometry
//                    is BYTE-IDENTICAL to the pre-mount model; tape / 3M
//                    Command strip to a smooth wall (pst-15du/pst-wjte).
//   opengrid       — an openGrid snap plate that REPLACES the tab, so the
//                    hanger clicks onto a 28mm openGrid panel.
//   multiconnect   — a Multiconnect slot backer (Multiboard / openGrid MC
//                    studs) that replaces the tab.
// The backer is a whole-tile plate behind the saddle's wall end. There is
// NO saddle-spanning floor: the hung headband is trivially light, so a
// MINIMAL plate is by design — in the spirit of the original small
// adhesive tab (operator correction, pst-gmg0). It defaults to a single
// tile (one openGridSnap / one Multiconnect slot behind the saddle) and
// widens 1:1 with width_units for anyone who wants a broader couple;
// height_units floats up from 1 like the sibling mounts. width_units maps
// 1:1 to a distinct plate width across its whole 1..6 range.
//
// === Up-the-wall axis / load (pst-3tum, JUDGMENT CALL) ===
//
// Mounted, the wall-end face is against the wall (the bed in print), the
// saddle projects horizontally out (+X body), and the headbands drape
// over the crown and hang DOWN. "Up the wall" is the saddle body's +Z
// (the crown side). The saddle cantilevers off the wall, so its weight
// levers the TOP of the backer away from the panel: the directional snaps
// point their strong 0.8mm front nub UP the wall so that pull-out bears on
// the rigid hook, and the Multiconnect retention domes point up too — the
// same rule the sibling mounts use.
//
// === Print orientation: wall face on the bed, arch up ===
//
// Every variant prints with the flat mounting side on the bed and the
// arch rising straight up (rotate([0,-90,0]); the upstream orientation,
// supportless — the saddle is a constant vertical cross-section). tab
// reproduces the upstream transform byte-for-byte. For the backer
// variants the plate + snaps/slots print snaps-DOWN on the bed (first
// layers are the panel-mating face) with the saddle rising off the plate
// front; the min-Z bed seat is parameter-derived per variant (pst-t9ri
// rule — no default-only seating). Print the panel-mating face against a
// smooth plate.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>
// Multiconnect backer (BOSL2-free master copy — a plain difference(),
// no diff() tags, so it is safe as a root-level sibling; same slot back
// apple_tv_4th_gen_holder / ryobi_p2860_strap_saddle / opengrid_bin use).
use <QuackWorks/Modules/multiconnectSlotDesign.scad>

$fn = 50;   // saddle resolution — held at the upstream value so the tab
            // variant stays byte-identical. The snap/slot backer is
            // rendered at $fn = 64 in its own module scope (below), the
            // resolution the sibling mounts use.

// === User-tunable parameters ===

hangerLength = 28;  // @param number min=15 max=60 step=1 unit=mm group=hanger label="Projection (saddle depth off wall)"

// Hanging tab (mount_type = "tab") — the rounded-square fin on the flat
// mounting face at the wall end that the whole hanger hooks / mounts by.
// It is square by nature (the upstream source is `square(15)`), so a
// single size drives both width and height. `tabRounding` is the corner
// radius, which also grows the plate outward by that radius (offset
// semantics); `tabThickness` is how far the fin stands off the wall face.
// Defaults reproduce the upstream geometry byte-for-byte. Ignored by the
// openGrid / Multiconnect mounts.
tabSize      = 15;  // @param number min=8 max=30 step=1   unit=mm group=tab label="Tab size (square side)"
tabThickness = 3;   // @param number min=2 max=6  step=0.5 unit=mm group=tab label="Tab thickness (stand-off)"
tabRounding  = 2;   // @param number min=0 max=5  step=0.5 unit=mm group=tab label="Tab corner rounding"

// ----- Wall mount -----
// Three interchangeable back mounts, exported as one STL each (the
// 'filename' flag fans the export grid over the enum). Default is the
// original adhesive tab so the shipped hanger is unchanged; 'opengrid'
// and 'multiconnect' are the panel-mount alternatives. Same @param set
// the sibling mounts (apple_tv, ryobi, opengrid_bin) copy.
mount_type = "tab"; // @param enum choices=tab|opengrid|multiconnect group=mount label="Wall mount type" filename

// Backer plate size in whole openGrid tiles. NO saddle-spanning floor: the
// hung headband is trivially light, so a minimal plate behind the saddle is
// by design (pst-gmg0, reversing the pst-51es 3-tile floor). width_units
// maps 1:1 to a distinct plate width across 1..6 — width=1 is a single
// openGridSnap / Multiconnect slot directly behind the saddle, in the
// spirit of the original small tab. height_units keeps its own >=1 tile
// floor (units_h below) that equals its min, so it maps 1:1 too. Only
// affect the opengrid / multiconnect mounts.
width_units  = 1;     // @param integer min=1 max=6 group=mount label="Backer width (openGrid units)"
height_units = 2;     // @param integer min=1 max=6 group=mount label="Backer height (openGrid units, min)"
snap_lite    = false; // @param boolean group=mount label="Lite openGrid snaps (3.4mm instead of 6.8mm)"

// Standard Multiconnect slot tuning (only affects mount_type =
// "multiconnect"; ignored otherwise). Defaults reproduce the shipped
// sibling backer exactly, threaded through the multiconnectBack() call.
slot_tolerance = 1.0;  // @param number min=0.925 max=1.075 step=0.005 group=mount label="Slot fit tolerance"
slot_retention = true; // @param boolean group=mount label="Slot retention (v2 snap)"
dimple_scale   = 1.0;  // @param number min=0.5 max=1.5 step=0.05 group=mount label="Dimple scale (v1 only)"
on_ramp        = true; // @param boolean group=mount label="Slot on-ramp lead-in"

// @preset id="standard"     label="Standard tab (28mm projection)"  mount_type=tab hangerLength=28
// @preset id="deep"         label="Deep tab (45mm projection)"      mount_type=tab hangerLength=45
// @preset id="chunky-tab"   label="Chunky mounting tab"             mount_type=tab tabSize=22 tabThickness=4 tabRounding=3
// @preset id="opengrid"     label="openGrid snap backer"            mount_type=opengrid width_units=1 height_units=2
// @preset id="multiconnect" label="Multiconnect slot backer"        mount_type=multiconnect width_units=1 height_units=2

// === Derived ===

padding = 0.1;  // internal epsilon for clean CSG cuts; not user-tunable

// Tab seat: the fin is anchored by its BOTTOM edge at tabSeatZ and grows
// UPWARD as tabSize/tabRounding increase, rather than being centred on a
// fixed z. tabSeatZ (15.5) sits ~2-6mm inside the arch's wall-end
// shoulder, whose cross-section here is independent of every @param — so
// a fixed seat keeps the fin fused to the body across the whole size
// range: a smaller tab can't lift off the arch, a larger one just stands
// taller. Deriving the centre from the seat (not hardcoding z=25) is
// PR #65 round-2's no-default-only-seating rule applied to the tab
// (pst-wjte). tabCenterZ evaluates to 25 at defaults, so default geometry
// is unchanged.
tabSeatZ   = 15.5;
tabCenterZ = tabSeatZ + tabSize / 2 + tabRounding;

// ----- Mount hardware constants (verbatim from the sibling mounts) -----
snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed of snap tops into the plate (st-v7k)

// Multiconnect backer. The 6.5mm slab depth and 25mm pitch are held fixed
// by choice (exposing them invites board-incompatible prints), same
// reasoning as the sibling mounts.
slot_spacing = 25;   // Multiconnect standard pitch
mc_thickness = 6.5;  // backer slab depth (= the module's fixed backThickness)
mc_weld      = 0.4;  // backer top sink into the plate (real overlap)

// Parts sink this far into the solid below them; cut tools overshoot this
// far past every face they pass through (st-n4v / st-v7k).
bury = 0.6;
ov   = 2;

plate_t = 4;   // backer plate thickness (fixed — sturdy enough for a
               // light headband hook; not worth a sweep axis).

// Plate is a whole number of openGrid tiles on each axis. width: NO
// saddle-spanning floor (pst-gmg0, reversing pst-51es) — just a >=1
// whole-tile guard, so units_w == width_units across the range and a
// 1-tile plate backs the saddle minimally (the plate may be narrower than
// the 65mm saddle by design). height: a >=1 tile floor from the saddle's
// up-wall span (~19mm + min_wall pad -> ceil = 1 tile), which equals
// height_units's @param min, so units_h == height_units too (no dead
// zone). max() on each axis is a no-op guard at the declared mins.
min_wall = 2.4;
saddle_up     = 19;                 // saddle wall-end height (body Z, dome)
units_w  = max(width_units,  1);
units_h  = max(height_units, ceil((saddle_up + 2 * min_wall) / snap_pitch));
W = units_w * snap_pitch;
H = units_h * snap_pitch;

// Plate bottom = thickness of whichever back mount is selected, minus its
// weld into the plate. openGrid: snap tops weld 0.02 up. Multiconnect: the
// 6.5mm slab welds mc_weld up. (Used only by the backer variants.)
plate_z0  = mount_type == "multiconnect" ? mc_thickness - mc_weld
                                         : snap_h - weld;
plate_top = plate_z0 + plate_t;     // plate front face (mount-frame z)
// Uniform backer corner rounding = the tab's upstream offset(2) (pst-4g1u).
// The plate AND the Multiconnect slab under it are clipped to ONE rounded
// outline (backer_outline below), so their corners round together and no
// square slab corner pokes past the rounded plate as a stray post. The
// snap grid is inboard of this radius, so it is untouched.
plate_corner_r = 2;

// ----- Backer placement in the saddle body frame (pst-3tum) -----
// The mount is authored in a local MOUNT frame (Xm across the wall, +Ym up
// the wall, +Zm out of the wall / toward the saddle, panel face at Zm=0),
// exactly like the sibling mounts, so the snap/slot/plate code is reused
// unchanged. rotate([90,0,90]) maps (Xm,Ym,Zm) -> (Zm,Xm,Ym) = body
// (X out, Y across, Z up) — VERIFIED by render, not just arithmetic.
// Then translate lands it at the wall end:
//   body_x = Zm + mount_tx : plate front (Zm=plate_top) welds weld_embed
//            into the saddle wall face at x = -(hangerLength/2+5); snaps
//            (Zm=0) sit furthest -X (the bed after the print rotate).
//   body_y = Xm            : plate X-centred on the saddle (Ty=0).
//   body_z = Ym + mount_tz : plate (Ym in [0,H]) centred up-the-wall on
//            the saddle dome centre.
weld_embed    = 2;    // plate front buried this deep into the saddle wall
wall_face_x   = -(hangerLength / 2 + 5);       // saddle wall face, body X
plate_front_x = wall_face_x + weld_embed;      // plate front face, body X
mount_tx      = plate_front_x - plate_top;     // so Zm=plate_top -> plate_front_x
saddle_up_center = 12.6;                        // dome up-wall centre (measured), body Z
mount_tz      = saddle_up_center - H / 2;       // centre the plate on it

// Bed seat (min build-Z = 0) after rotate([0,-90,0]) (which maps body X ->
// build Z). tab: min body X is the wall cap at -(hangerLength/2+5.05).
// backer: min body X is the snap/slot panel face at mount_tx. Derived per
// variant so every mount_type + hangerLength seats on the bed (pst-t9ri).
seat_z = mount_type == "tab" ? hangerLength / 2 + 5.05 : -mount_tx;
// Centre the backer variants in build-X (cosmetic; the anchor check only
// covers the tab default). tab keeps its shipped 18.95 (pst-t9ri).
seat_x = mount_type == "tab" ? 18.95 : saddle_up_center;

// PRINT_ANCHOR_BBOX — measured at the DEFAULT variant (mount_type = tab);
// this is the STL the drift check and the invariants sidecar load.
// X (31.1): tab-dependent. rotate maps body-Z to build-X, spanning the
//    arch's lowest interior point (body z ~= 3.4) up to the tab top (body
//    z = tabCenterZ + tabSize/2 + tabRounding = 34.5 at defaults).
// Y (65.0): saddle width across the two ±32.5 side clips — arch-only.
// Z (38.1): vertical print height = hangerLength(28) + the two end flares
//    (each +5); hangerLength-dependent.
// The opengrid / multiconnect variants have their own bbox — the backer
// plate is W x H tiles (28 x 56 at defaults, one tile wide) and is
// narrower than the 65mm saddle, so their across-wall extent is still the
// saddle's 65mm — measured on their own STLs, not pinned here.
PRINT_ANCHOR_BBOX = [31.1, 65, 38.1];

// === Assembly ===
translate([ seat_x, 0, seat_z ]) rotate([ 0, -90, 0 ]) {
    earHanger();
    if (mount_type != "tab") wall_mount_placed();
}

module earHanger()
{

    difference()
    {

        union()
        {

            // main shape
            translate([ 0, 0, 0 ]) baseShape(hangerLength);

            // hanging tab (mount_type = "tab" only; the openGrid /
            // Multiconnect backers replace it — pst-3tum)
            if (mount_type == "tab")
                translate([ -hangerLength / 2 - 5, 0, tabCenterZ ]) rotate([ 0, 90, 0 ]) linear_extrude(height = tabThickness)
                {
                    offset(tabRounding) square(tabSize, center = true);
                }

            // front end
            hull()
            {
                translate([ hangerLength / 2, 0, 0 ]) scale([ 1, 1, 1 ]) baseShape(0.1);

                translate([ hangerLength / 2 + 5, 0, 1 ]) scale([ 1, 1, 1.2 ]) baseShape(0.1);
            }

            // wall end
            hull()
            {
                translate([ -hangerLength / 2, 0, 0 ]) scale([ 1, 1, 1 ]) baseShape(0.1);

                translate([ -hangerLength / 2 - 5, 0, 1 ]) scale([ 1, 1, 1.2 ]) baseShape(0.1);
            }
        }

        translate([ 0, 0, -3 ]) rotate([ 0, 90, 0 ]) scale([ 1, 2, 2 ])
            cylinder(d = 35, h = hangerLength - 2, center = true);
    }
}

// this creates the main shape
module baseShape(height)
{

    difference()
    {

        translate([ 0, 0, 0 ]) rotate([ 0, 90, 0 ]) scale([ 1, 2, 1 ]) cylinder(d = 35, h = height, center = true);

        translate([ 0, 0, -20 ]) cube([ height + padding, 60, 30 ], center = true);

        translate([ 0, 55, 0 ]) cube([ height + padding, 45, 60 ], center = true);

        translate([ 0, -55, 0 ]) cube([ height + padding, 45, 60 ], center = true);
    }
}

// ===================================================================
// Wall mount (openGrid / Multiconnect) — pst-3tum
// ===================================================================
// Authored in the MOUNT frame (Xm across, +Ym up-wall, +Zm out-of-wall),
// then rotate([90,0,90]) + translate carry it to the saddle wall end. The
// snap wrapper, grid layout and Multiconnect transform are verbatim from
// apple_tv_4th_gen_holder (st-0of / pst-qdje) — do not re-derive them.

// One openGrid snap in its own frame (front/strong nub toward +X), welded
// into a single solid. Each click-nub root gets a 0.3mm shim straddling
// the nub/core contact plane (local x=12.4); the 14mm-wide front nub's
// shim widens to 14.6, and the rear nub's sits 0.65 higher (its root rides
// above the base band in the directional variant). NEVER re-derive snap
// geometry — kept textually identical across models.
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

// One snap in EVERY tile (ryobi_p2860_strap_saddle precedent, not
// apple_tv's four corners): this backer prints snaps-DOWN, so a full grid
// keeps the plate underside supported — 24.8mm snap pads on the 28mm pitch
// leave only 3.2mm bridges, where corner-only snaps would float the plate
// 6.8mm over the bed across a ~59mm span. zrot(90) turns each snap's strong
// front nub toward +Ym — up the wall (load rationale in the header).
module grid_snaps() {
    for (cx = [0 : units_w - 1], ry = [0 : units_h - 1])
        translate([(cx - (units_w - 1) / 2) * snap_pitch,
                   (ry + 0.5) * snap_pitch,
                   0])
            zrot(90) welded_directional_snap();
}

// QuackWorks' BOSL2-free master slot back — a plain difference() (slab
// minus slot tools). multiconnectBack's local frame L is a cube x[0,W]
// y[-6.5,0] z[0,H] with the slot channels recessed from the y=-6.5 face,
// closed retention domes at high z and entry mouths + on-ramps at low z.
// rotate(180,[0,1,1]) maps (lx,ly,lz) -> (-lx, lz, ly): L.z -> +Ym (domes
// point UP the wall — retention takes the cantilever load), L.y -> +Zm
// (openings face -Zm, the panel/bed face the snaps engage), L.x -> -Xm
// (re-centred on x=0). The outer translate lands the slab at z[0,6.5] with
// the openings at z=0; the plate bottom sits mc_weld lower (plate_z0) so
// the backer top overlaps into the plate as a real weld. Verbatim
// transform from the sibling mounts (front-anchored y[0,H] frame).
module multiconnect_backer() {
    // Clip the vendored slab's square corners to the shared rounded outline
    // so it matches the plate cap welded on top of it — kills the stray
    // square-corner post that poked past the rounded plate (pst-4g1u). The
    // clip prism spans the slab's full depth (z 0..mc_thickness); the slots
    // sit inboard of the corners, so only the 4 corners are trimmed.
    intersection() {
        translate([W / 2, 0, mc_thickness])
            rotate(180, [0, 1, 1])
                multiconnectBack(backWidth = W, backHeight = H,
                                 distanceBetweenSlots = slot_spacing,
                                 quickRelease = !slot_retention,
                                 tolerance = slot_tolerance,
                                 dimple = dimple_scale,
                                 onRamp = on_ramp);
        translate([0, 0, -padding])
            linear_extrude(height = mc_thickness + 2 * padding)
                backer_outline();
    }
}

// The shared backer footprint: a rounded rect, front-anchored y[0,H],
// X-centred. Both the plate cap and the Multiconnect slab are built on this
// one outline so their corners round uniformly (pst-4g1u).
module backer_outline() {
    rect([W, H], rounding = plate_corner_r, anchor = FRONT);
}

// The backer plate: a plain rounded slab, front-anchored y[0,H], X-centred,
// z[plate_z0, plate_top]. Its front face (plate_top) welds into the saddle.
module plate() {
    translate([0, 0, plate_z0])
        linear_extrude(height = plate_t)
            backer_outline();
}

// Whole mount in the MOUNT frame: plate + (snaps or Multiconnect backer),
// at the sibling resolution ($fn = 64).
module wall_mount() {
    $fn = 64;
    plate();
    if (mount_type == "multiconnect") multiconnect_backer();
    else grid_snaps();
}

// Mount placed at the saddle wall end (see the placement derivation above).
module wall_mount_placed() {
    translate([mount_tx, 0, mount_tz])
        rotate([90, 0, 90])
            wall_mount();
}
