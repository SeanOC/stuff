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
// === Mount options (mount_type, pst-3tum / pst-j3ej) ===
//
// The saddle geometry is IDENTICAL across the mounts — only the wall
// attachment at the wall end changes, and it is the export-grid filename
// axis. The Multiconnect mount is a TWO-PIECE, dovetail-jointed pair
// (pst-j3ej), so the enum carries four fanned STLs:
//   tab (default)      — the original rounded-square adhesive fin.
//                        Geometry is BYTE-IDENTICAL to the pre-mount model;
//                        tape / 3M Command strip to a smooth wall.
//   opengrid           — an openGrid snap plate that REPLACES the tab, so
//                        the hanger clicks onto a 28mm openGrid panel.
//   multiconnect_plate — PART A of the Multiconnect mount: a slim (~6mm)
//                        Multiconnect slot plate with a dovetail RAIL on its
//                        accessory face. Prints standing, on its own.
//   multiconnect_saddle— PART B: the ear-hanger saddle with a dovetail
//                        SOCKET cut into its wall end (no backer welded on).
//                        Prints in the original supportless orientation.
// The two Multiconnect parts print SEPARATELY (each its own zero-support
// flat print) and slide together at the dovetail — see the assembly note
// below. This replaces the old one-piece Multiconnect variant, which welded
// the plate perpendicular to the saddle and so could not print without
// heavy supports in any orientation (operator, pst-j3ej).
//
// The plate is a whole-tile Multiconnect back behind the saddle's wall
// end. There is NO saddle-spanning floor: the hung headband is trivially
// light, so a MINIMAL plate is by design — in the spirit of the original
// small adhesive tab (operator correction, pst-gmg0). It defaults to a
// single tile and widens 1:1 with width_units for anyone who wants a
// broader couple; height_units floats up from 1 like the sibling mounts.
//
// === Two-piece dovetail joint (pst-j3ej) ===
//
// The plate carries a male dovetail RAIL; the saddle a female SOCKET. The
// rail runs ACROSS the wall (body Y) — the slide axis is horizontal — so
// BOTH the saddle's cantilever lever-out (body +X, pull off the wall) AND
// gravity (body -Z) bear on the dovetail's flared shoulders, not along the
// slide (operator's load rule). You mount the plate on the board, then
// slide the saddle sideways onto the rail; a snug fit
// (dovetail_clearance ~0.25mm, @param) plus an optional glue dot at the
// joint holds it against sliding back out. The joint dims are fixed
// (independent of plate size) so a future tab/opengrid back could grow the
// same rail and become interchangeable (pst-j3ej "don't preclude it").
//
// === Print: the Multiconnect plate prints STANDING, slots horizontal ===
//
// The plate prints in multiconnectBack's NATIVE frame: the slab is a wall
// in the X-Z plane, thin in Y, standing on its z=0 bottom edge. The slot
// openings face horizontal (-Y) and print as vertical walls with their
// undercuts and retention domes self-supporting and the on-ramp bridging —
// the standard Multiconnect ZERO-SUPPORT orientation the sibling backers
// (apple_tv_4th_gen_holder etc.) already print in. The dovetail rail
// protrudes horizontally (+Y) off the SOLID back face, opposite the slot
// openings, and adds no overhang of its own. (pst-j3ej: the operator chose
// the standing print. It is taller than the saddle — brim it if tippy —
// but it is the only orientation that is both support-free AND presents the
// slot openings to the board. An earlier flat print had the slots inverted
// so the plate met the board with a solid face — see the invariant probe.)
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
// The saddle-bearing variants (tab, opengrid, multiconnect_saddle) print
// with the flat mounting side on the bed and the arch rising straight up
// (rotate([0,-90,0]); the upstream orientation, supportless — the saddle
// is a constant vertical cross-section). tab reproduces the upstream
// transform byte-for-byte. multiconnect_saddle is that same saddle with a
// dovetail socket relieved into its wall end (a small ~12mm bridge on the
// bed-facing wall block). The opengrid backer prints snaps-DOWN on the bed
// (first layers are the panel-mating face) with the saddle rising off the
// plate front. The multiconnect_plate prints on its OWN — STANDING, slots
// facing horizontal / rail out (see the two-piece print note above). Every
// part's min-Z bed seat is parameter-derived per variant (pst-t9ri rule —
// no default-only seating). Print the panel-mating face against a smooth
// plate.

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
// Interchangeable back mounts, exported as one STL each (the 'filename'
// flag fans the export grid over the enum). Default is the original
// adhesive tab so the shipped hanger is unchanged. 'opengrid' is a snap
// panel mount. The Multiconnect mount is TWO fanned parts that print
// separately and slide together at a dovetail (pst-j3ej):
// 'multiconnect_plate' (the slot plate + rail) and 'multiconnect_saddle'
// (the saddle + socket). Print ONE of each and join them.
mount_type = "tab"; // @param enum choices=tab|opengrid|multiconnect_plate|multiconnect_saddle group=mount label="Wall mount type" filename

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

// Standard Multiconnect slot tuning (only affects the multiconnect_plate
// part; ignored otherwise). Defaults reproduce the shipped sibling backer
// slot exactly, threaded through the multiconnectBack() call.
slot_tolerance = 1.0;  // @param number min=0.925 max=1.075 step=0.005 group=mount label="Slot fit tolerance"
slot_retention = true; // @param boolean group=mount label="Slot retention (v2 snap)"
dimple_scale   = 1.0;  // @param number min=0.5 max=1.5 step=0.05 group=mount label="Dimple scale (v1 only)"
on_ramp        = true; // @param boolean group=mount label="Slot on-ramp lead-in"

// Dovetail joint fit (multiconnect_plate rail <-> multiconnect_saddle
// socket). The socket is cut this much wider than the rail (total across
// both flanks) for a friction slide fit; bump it if the parts bind, drop
// it for a tighter hold. A glue dot at the joint is the belt-and-braces.
dovetail_clearance = 0.25; // @param number min=0.0 max=0.6 step=0.05 unit=mm group=mount label="Dovetail slide clearance"

// @preset id="standard"     label="Standard tab (28mm projection)"  mount_type=tab hangerLength=28
// @preset id="deep"         label="Deep tab (45mm projection)"      mount_type=tab hangerLength=45
// @preset id="chunky-tab"   label="Chunky mounting tab"             mount_type=tab tabSize=22 tabThickness=4 tabRounding=3
// @preset id="opengrid"     label="openGrid snap backer"            mount_type=opengrid width_units=1 height_units=2
// @preset id="mc-plate"     label="Multiconnect slot plate (part A)" mount_type=multiconnect_plate width_units=1 height_units=2
// @preset id="mc-saddle"    label="Multiconnect saddle (part B)"     mount_type=multiconnect_saddle

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

// Multiconnect slot plate (multiconnect_plate part). 25mm pitch is fixed
// by choice (exposing it invites board-incompatible prints). The slab is
// SLIM at 6.0mm (pst-j3ej A1): the multiconnect slot needs only ~4.15mm of
// engaging recess to its blind face, plus a ~1.85mm back wall — the old
// 6.5mm slab + 4mm plate cap (~10mm) was far thicker than a light headband
// hook warrants. 6.0 is threaded through as backThickness via patch 0002,
// which keeps the 4.15mm engaging profile identical and adds/removes the
// extra meat behind it.
slot_spacing = 25;   // Multiconnect standard pitch
mc_thickness = 6.0;  // slim slot-plate slab depth (patched backThickness)

// Parts sink this far into the solid below them; cut tools overshoot this
// far past every face they pass through (st-n4v / st-v7k).
bury = 0.6;
ov   = 2;

plate_t = 4;   // openGrid backer plate thickness (fixed — sturdy enough
               // for a light headband hook; not worth a sweep axis).

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

// openGrid plate bottom = snap height minus its 0.02 weld into the plate.
// (Used only by the opengrid backer; the multiconnect_plate part builds its
// own slab in mc_plate_part() below.)
plate_z0  = snap_h - weld;
plate_top = plate_z0 + plate_t;     // plate front face (mount-frame z)
// Uniform backer corner rounding = the tab's upstream offset(2) (pst-4g1u).
// The openGrid plate and the multiconnect slab are each clipped to this
// rounded outline so no square slab corner pokes past as a stray post. The
// snap grid is inboard of this radius, so it is untouched.
plate_corner_r = 2;

// ----- Dovetail joint (multiconnect_plate rail <-> multiconnect_saddle
// socket), pst-j3ej. Fixed dims (independent of plate size) so the joint is
// a stable interface a future tab/opengrid back could reuse. The rail runs
// along body Y (across the wall = the horizontal slide axis); its
// cross-section flares in body Z from a dt_neck neck at the plate face to a
// wider dt_tip tip at depth dt_depth, so it captures body +X pull-out (the
// cantilever lever-out) and body Z (gravity) on the flared shoulders.
// Flank angle atan((dt_tip-dt_neck)/2 / dt_depth) ~= 26.6deg — a short
// self-supporting ridge on the standing plate (rail out, +Y) and a
// ~dt_tip-wide bridge on
// the saddle wall block (socket relieved into the bed-facing face).
dt_depth = 4;    // rail height / socket depth (body X)
dt_neck  = 8;    // rail width at the plate face (body Z)
dt_tip   = 12;   // rail width at the tip (body Z), > dt_neck -> undercut
dt_len   = 24;   // rail length along the slide axis (body Y)
// Socket centre up-the-wall (body Z). The saddle's solid wall-end block
// spans body z ~ [3, 20]; 11 centres the socket in it with margin, and the
// tip half-width (dt_tip/2 + clearance) stays clear of the block top.
dovetail_z = 11;

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
// build Z). tab / multiconnect_saddle: min body X is the wall cap at
// -(hangerLength/2+5.05) (the socket only relieves material, so it does not
// move the seat). opengrid: min body X is the snap panel face at mount_tx.
// Derived per variant so every mount_type + hangerLength seats (pst-t9ri).
// (multiconnect_plate seats itself in mc_plate_part(), below.)
seat_z = mount_type == "opengrid" ? -mount_tx : hangerLength / 2 + 5.05;
// Centre the saddle variants in build-X (cosmetic; the anchor check only
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
// The other variants have their own bbox — measured on their own STLs, not
// pinned here. opengrid/multiconnect_saddle keep the 65mm saddle width;
// multiconnect_plate is a standalone W x H tile slab (28 x 56 at defaults).
PRINT_ANCHOR_BBOX = [31.1, 65, 38.1];

// === Assembly ===
// multiconnect_plate is a standalone part in its OWN print frame; every
// other variant is the saddle in the shared wall-face-down print frame.
if (mount_type == "multiconnect_plate") {
    mc_plate_part();
} else {
    translate([ seat_x, 0, seat_z ]) rotate([ 0, -90, 0 ]) {
        if (mount_type == "multiconnect_saddle")
            difference() {
                union() { earHanger(); dovetail_backing(); }
                dovetail_socket();
            }
        else {
            earHanger();
            if (mount_type == "opengrid") wall_mount_placed();
        }
    }
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
// openGrid wall mount — pst-3tum
// ===================================================================
// Authored in the MOUNT frame (Xm across, +Ym up-wall, +Zm out-of-wall),
// then rotate([90,0,90]) + translate carry it to the saddle wall end. The
// snap wrapper and grid layout are verbatim from apple_tv_4th_gen_holder
// (st-0of / pst-qdje) — do not re-derive them. (The Multiconnect mount is
// now the standalone two-piece plate + saddle-socket further below.)

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

// The openGrid backer footprint: a rounded rect, front-anchored y[0,H],
// X-centred — the tab's offset(2) rounding, so no square corner pokes past
// the plate as a stray post (pst-4g1u).
module backer_outline() {
    rect([W, H], rounding = plate_corner_r, anchor = FRONT);
}

// The openGrid backer plate: a plain rounded slab, front-anchored y[0,H],
// X-centred, z[plate_z0, plate_top]. Its front (plate_top) welds into the
// saddle; the snaps hang off its back.
module plate() {
    translate([0, 0, plate_z0])
        linear_extrude(height = plate_t)
            backer_outline();
}

// openGrid mount in the MOUNT frame: plate + snap grid, at the sibling
// resolution ($fn = 64).
module wall_mount() {
    $fn = 64;
    plate();
    grid_snaps();
}

// Mount placed at the saddle wall end (see the placement derivation above).
module wall_mount_placed() {
    translate([mount_tx, 0, mount_tz])
        rotate([90, 0, 90])
            wall_mount();
}

// ===================================================================
// Multiconnect two-piece: slot plate (part A) + saddle socket (part B)
// — pst-j3ej
// ===================================================================

// PART A — the standalone slim Multiconnect slot plate, in its OWN print
// frame: the slab lies flat with the slot/panel face DOWN on the bed
// (build z=0) and the dovetail rail rising UP (+build z). The vendored
// multiconnectBack L-frame is a cube x[0,W] y[-t,0] z[0,H] with the slots
// recessed from the y=0 mating face; rotate([-90,0,0]) maps L(x,y,z) ->
// (x, z, -y), so the slab sits at build x[0,W] y[0,H] z[0,t] with the
// mating face on the bed (L.y=0 -> build z=0). See the print note in the
// header for why slot-DOWN / rail-UP (the rail cannot point below the bed).
// The standalone Multiconnect slot plate, in its own STANDING print frame.
// The slab sits in multiconnectBack's NATIVE frame — a wall in the X-Z
// plane, thin in Y, standing on its z=0 bottom edge — so the slot openings
// face horizontal (-Y) and print as vertical walls with self-supporting
// undercuts and an on-ramp bridge: the native Multiconnect ZERO-SUPPORT
// orientation the sibling backers use once stood up (pst-j3ej, operator-
// picked standing plate). The dovetail rail protrudes horizontally (+Y)
// off the SOLID back face (y=0), opposite the slot openings.
module mc_plate_part() {
    $fn = 64;
    union() {
        mc_slab_standing();
        plate_rail_standing();
    }
}

// The slim slot slab in the native frame, clipped to the rounded outline
// (in the X-Z face plane, through the full Y depth) so its corners match
// the sibling backers (pst-4g1u). multiconnectBack's cube is x[0,W]
// y[-mc_thickness,0] z[0,H] with the slot channels recessed from the
// y=-mc_thickness face (openings face -Y) and the solid back at y=0.
module mc_slab_standing() {
    intersection() {
        multiconnectBack(backWidth = W, backHeight = H,
                         distanceBetweenSlots = slot_spacing,
                         backThickness = mc_thickness,
                         quickRelease = !slot_retention,
                         tolerance = slot_tolerance,
                         dimple = dimple_scale,
                         onRamp = on_ramp);
        translate([0, padding, 0])
            rotate([90, 0, 0])
                linear_extrude(height = mc_thickness + 2 * padding)
                    translate([W / 2, H / 2])
                        rect([W, H], rounding = plate_corner_r);
    }
}

// The dovetail rail: a shallow trapezoidal ridge on the SOLID back face
// (y=0), centred on the plate, protruding +Y (horizontal, toward the
// saddle) and running along build X (= the across-wall slide axis). Hull
// of a narrow neck band (dt_neck, buried bury into the slab) and a wider
// tip band (dt_tip) at depth dt_depth -> an undercut ridge (flanks
// ~26.6deg). Same trapezoidal shape (24 long x 4 deep x 8->12 flare) the
// saddle socket receives — the two parts print separately and slide
// together, so the plate's print frame is independent of the joint.
module plate_rail_standing() {
    translate([W / 2, 0, H / 2])
        hull() {
            translate([0, -bury / 2, 0])
                cube([dt_len, bury, dt_neck], center = true);
            translate([0, dt_depth, 0])
                cube([dt_len, 0.2, dt_tip], center = true);
        }
}

// PART B backing — the saddle's wall end is a hollow arch the whole way
// through (the inner cut's scale([1,2,2]) doubles its length past the wall
// cap), so there is no solid there to host a socket. This refills the arch
// channel over just the wall-cap depth (x in [wall_face_x-ov,
// wall_face_x+dt_depth+2]) with the arch's OWN outer silhouette (baseShape
// + the wall-end hull, un-hollowed), clipped to that slab — a solid
// mounting back flush inside the arch outline (bbox unchanged). Prints flat
// on the bed with the rest of the wall face. The socket is then cut into it.
module dovetail_backing() {
    intersection() {
        translate([wall_face_x - ov, -40, -25])
            cube([ov + dt_depth + 2, 80, 60]);
        union() {
            baseShape(hangerLength);
            hull() {
                translate([-hangerLength / 2, 0, 0]) baseShape(0.1);
                translate([-hangerLength / 2 - 5, 0, 1]) scale([1, 1, 1.2]) baseShape(0.1);
            }
        }
    }
}

// PART B — the dovetail SOCKET tool, in the saddle BODY frame (X out of
// wall, +Y across, +Z up). Cut from earHanger() at the wall end. The socket
// is the rail's trapezoid, dovetail_clearance wider across the flanks,
// running through the saddle along Y (open both ends so the rail slides in
// from either side). Its narrow mouth is at the wall face (body X =
// wall_face_x) and it widens to the tip at +dt_depth, so it grips the rail
// against +X pull-out. Centred body z = dovetail_z, inside the solid wall
// block. A mouth extension past the wall face keeps the entry open.
module dovetail_socket() {
    c = dovetail_clearance;
    through = 80;                       // > 65mm saddle width -> open both ends
    hull() {
        translate([wall_face_x, 0, dovetail_z])
            cube([0.1, through, dt_neck + c], center = true);
        // 0.4mm deeper than the rail so the flanks + the flush plate/wall
        // faces seat, not the rail tip bottoming in the socket.
        translate([wall_face_x + dt_depth + 0.4, 0, dovetail_z])
            cube([0.1, through, dt_tip + c], center = true);
    }
    // open the mouth: extend the neck outward past the wall face
    translate([wall_face_x - ov, 0, dovetail_z])
        cube([2 * ov, through, dt_neck + c], center = true);
}
