// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// OpenGrid wall cradle for a 4th-generation Apple TV (98 x 98 x 35 mm)
// (pst-hn2). The device lies FLAT in an open tray cantilevered off a
// vertically-mounted openGrid panel: tray floor, partial-height side
// walls, a 45deg front lip that stops it sliding out, a rear plenum
// with a port-cluster opening so the wall-facing HDMI/power/Ethernet
// plugs clear the back plate, and floor slots that vent the (warm)
// device and drop the cables down behind the tray.
//
// DEVICE (Apple TV HD / 4th gen, 2015, model A1625): 98 mm square,
// 35 mm tall, 425 g, rounded corners, ports on the rear edge.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived holder is for personal use only; do
// not sell prints or files.
//
// === Print orientation (native): ZERO supports ===
//
// Prints snaps-down — the snap faces are the first layers, the
// orientation the snap geometry was designed to print in. Mounted,
// +Y is UP the wall and +Z points OUT from the panel, so +Z is also
// the build direction: every face that gains material as the print
// rises is a 45deg plane, never a flat span. Equivalently, anything at
// constant Y (wall tops, the lead-in chamfer) is a vertical face in
// print and costs nothing.
//
//  - plate underside between snaps: 3.2 mm bridges on the 28 mm pitch
//    (proven at these exact spans by opengrid_bin / the
//    led_remote_holder twins); plate rim: 45deg chamfer clamped so it
//    never crosses a snap footprint (st-ocs);
//  - tray floor and side walls: they run continuously in +Z off the
//    plate, so every layer sits on the one below;
//  - front lip: there is deliberately NO vertical front wall — its
//    inner face would be material appearing over the whole open pocket
//    (a ~100 mm bridge). Instead the floor ramps up at 45deg to the lip
//    crest with a matching outer chamfer, so both lip faces are
//    self-supporting, exactly as opengrid_bin does it;
//  - rear retaining rib: a right triangle with the vertical (retaining)
//    face toward the device and the 45deg hypotenuse falling back
//    toward the plate, so the rib grows out of the floor a layer at a
//    time instead of appearing all at once;
//  - floor slots: each closes at its far end with a 45deg point, so the
//    floor never has to bridge back across an open slot.
//
// === Wall-hang orientation / load direction ===
//
// The tray cantilevers a 425 g device ~75 mm off the panel, so the
// lever-out moment lands on the TOP snap row. Directional snaps with
// the strong front nub (non-flexing, 0.8 mm deep vs 0.4) turned +Y —
// up the wall — put that pull-out load on the rigid hook, while the
// flexy click-in side faces down where the moment presses the plate
// into the panel. Same rationale as opengrid_bin / ego_lb6500 (st-0of).
//
// The plate is deliberately taller than the tray: it runs a full
// height_units tiles so a SECOND snap row sits above the tray, giving
// the couple that resists lever-out a real lever arm, and it doubles as
// a backboard behind the 35 mm device.
//
// Sizing the mount, at defaults: ~0.5 kg (device + tray) with its
// centre of mass ~75 mm off the panel is ~0.37 N.m. The plate pivots
// about its bottom edge, so the top snap row at y = 42 mm carries
// 0.37 / 0.042 ~= 8.8 N total, ~4.4 N per top snap across the two —
// far inside what an openGrid snap's hook holds. Dropping to a single
// snap row would shorten that arm to 14 mm and quadruple the per-snap
// pull, which is why the second row is not negotiable here even though
// it costs a tile of plate.
//
// === Rear plenum: why the pocket is not against the plate ===
//
// The Apple TV's ports face the wall. An HDMI plug body plus a mains
// plug need real clearance behind the device, and there is nowhere for
// them to go behind the plate (6.8 mm of snap standoff, then the panel
// and the wall itself). So the pocket is held `port_gap` off the plate,
// leaving an open plenum; the rear rib carries a central opening
// (`port_cutout_w`, offset by `port_cutout_x`) for the plug cluster,
// and the plenum floor slots drop the cables down the wall.
//
// ASSUMPTION (pst-hn2, worked unattended): the 20 mm default is sized
// from typical HDMI/mains plug bodies, NOT from a measured device —
// dial `port_gap` on preview. The `shallow_ports` preset is the
// right-angle-adapter case.
//
// === Fit / corners ===
//
// The pocket is device + `fit_clearance` per side, with SQUARE plan
// corners: the Apple TV's own corners are rounded, so square pocket
// corners can only ever give clearance, never bind. The visible OUTER
// front corners are rounded (`corner_r`) to echo the device's radius,
// clamped to leave >= 1 mm of side wall surviving at the corner.
//
// === Structure / mesh-robustness notes ===
//
// Snaps weld 0.02 mm into the plate and carry the sibling models'
// root-fillet shims (st-v7k: openGridSnap's click nubs are
// face-touching solids; the shims fuse them into one clean solid on
// both CGAL and Manifold). The tray buries 0.6 mm into the plate and
// the rear rib buries 0.6 mm into the floor and side walls — no
// face-kissing unions anywhere (st-v7k). Cut tools overshoot every face
// they pass through (st-n4v: coplanar cut faces are degenerate
// booleans), and the interior cut is differenced from the TRAY only —
// the plate is a sibling union — so it can never gouge the plate or
// clip a snap. Nothing uses hull-backed rounding (BOSL2 cuboid edges=):
// the wasm engine's CGAL applyHull() asserts on some swept dimensions
// (st-7x7/st-560 class), so rounding is done as 2D rect(rounding=)
// footprints and explicit 45deg prisms.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Device -----
device_w      = 98;  // @param number min=60 max=140 step=0.5 unit=mm group=device label="Device width"
device_d      = 98;  // @param number min=60 max=140 step=0.5 unit=mm group=device label="Device depth"
fit_clearance = 1;   // @param number min=0.3 max=3 step=0.1 unit=mm group=device label="Pocket clearance per side"

// ----- Shell -----
wall_h   = 20; // @param number min=6 max=34 step=1 unit=mm group=shell label="Side wall height"
floor_t  = 3;  // @param number min=2 max=5 step=0.5 unit=mm group=shell label="Floor thickness"
plate_t  = 4;  // @param number min=3 max=6 step=0.5 unit=mm group=shell label="Back plate thickness"
corner_r = 5;  // @param number min=0 max=10 step=0.5 unit=mm group=shell label="Outer front corner radius"

// ----- Retention -----
// Both auto-clamp below the side wall height (see Derived) so no
// slider combination makes a lip or rib taller than the tray.
lip_rise = 8; // @param number min=3 max=20 step=0.5 unit=mm group=retention label="Front lip rise"
rib_h    = 8; // @param number min=3 max=20 step=0.5 unit=mm group=retention label="Rear retaining rib height"

// ----- Ports / cables -----
port_gap      = 20; // @param number min=5 max=40 step=1 unit=mm group=ports label="Rear plenum depth (plug clearance)"
port_cutout_w = 62; // @param number min=20 max=110 step=1 unit=mm group=ports label="Port-cluster opening width"
port_cutout_x = 0;  // @param number min=-25 max=25 step=1 unit=mm group=ports label="Port opening offset (+ = right)"

// ----- Ventilation / cable slots -----
slot_count = 4; // @param integer min=0 max=8 group=vent label="Floor slots per row"
slot_w     = 9; // @param number min=4 max=20 step=0.5 unit=mm group=vent label="Floor slot width"

// ----- OpenGrid mount -----
// Tile counts are MINIMUMS: the plate always grows to whole tiles wide
// enough for the tray (see Derived), so the mount stays grid-aligned
// whatever the device dimensions are set to.
width_units  = 4;     // @param integer min=1 max=6 group=mount label="Width (openGrid units, min)"
height_units = 2;     // @param integer min=1 max=4 group=mount label="Height (openGrid units, min)"
snap_lite    = false; // @param boolean group=mount label="Lite snaps (3.4mm instead of 6.8mm)"

// @preset id="default" label="Apple TV HD, 20mm plug plenum" device_w=98 device_d=98 fit_clearance=1 wall_h=20 floor_t=3 plate_t=4 corner_r=5 lip_rise=8 rib_h=8 port_gap=20 port_cutout_w=62 port_cutout_x=0 slot_count=4 slot_w=9 width_units=4 height_units=2 snap_lite=false
// @preset id="shallow_ports" label="Right-angle adapters (8mm plenum)" device_w=98 device_d=98 fit_clearance=1 wall_h=20 floor_t=3 plate_t=4 corner_r=5 lip_rise=8 rib_h=8 port_gap=8 port_cutout_w=62 port_cutout_x=0 slot_count=4 slot_w=9 width_units=4 height_units=2 snap_lite=false

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed depth of snap tops into the plate (st-v7k)

// Parts sink this far into the solid below them; cut tools overshoot
// this far past every face they pass through.
bury = 0.6;
ov   = 2;

pocket_w = device_w + 2 * fit_clearance;
pocket_d = device_d + 2 * fit_clearance;
body_h   = floor_t + wall_h;

// Plate is whole openGrid tiles, grown past the unit minimums whenever
// the tray needs it, so the snap grid always covers the tray footprint.
min_wall = 2.4;
units_w  = max(width_units,  ceil((pocket_w + 2 * min_wall) / snap_pitch));
units_h  = max(height_units, ceil((body_h + 2) / snap_pitch));
W = units_w * snap_pitch;
H = units_h * snap_pitch;

// Side walls take up whatever the whole-tile plate leaves around the
// pocket, so their thickness is derived rather than dialled.
side_wall_t = (W - pocket_w) / 2;

plate_z0  = snap_h - weld;      // plate bottom (welds into snap tops)
plate_top = plate_z0 + plate_t;

rib_e   = min(rib_h,    wall_h - 2);   // stay below the wall tops
lip_e   = min(lip_rise, wall_h - 2);
z_rib0  = plate_top + port_gap;        // rib's 45deg back ramp starts
z_rib1  = z_rib0 + rib_e;              // rib's vertical retaining face
z_bend  = z_rib1 + pocket_d;           // pocket ends, front ramp starts
z_front = z_bend + lip_e;              // tray front face / lip crest

// Leave >= 1mm of side wall surviving at the rounded outer corner.
corner_r_e = max(0, min(corner_r, side_wall_t - 1));

// Port opening: keep >= 5mm of rib ear each side, then clamp the offset
// so both ears survive.
port_w_e   = max(0, min(port_cutout_w, pocket_w - 20));
port_x_max = max(0, (pocket_w - port_w_e) / 2 - 5);
port_x_e   = max(-port_x_max, min(port_cutout_x, port_x_max));

// Floor slots: evenly pitched across the pocket, clamped to leave a
// >= 3mm rib between neighbours. A slot needs slot_w_e/2 of run to
// close at 45deg, so the plenum row is skipped outright when port_gap
// leaves less than that.
slot_pitch = slot_count > 0 ? pocket_w / slot_count : 0;
slot_w_e   = slot_count > 0 ? min(slot_w, slot_pitch - 3) : 0;
plenum_z0  = plate_top + 3;
plenum_z1  = z_rib0 - 3;
pocket_ok  = slot_count > 0 && slot_w_e > 0;
plenum_ok  = pocket_ok && (plenum_z1 - plenum_z0) > slot_w_e / 2 + 2;

plate_corner_r = 1;   // plate outline rounding, matches the siblings
lead_in        = 1.2; // 45deg lead-in on the pocket's top inner edges
// 45deg plate bottom-rim chamfer. The snap grid leaves a 1.6mm rim
// ((28 - 24.8)/2) per side; the clamp keeps the cut off the snap
// footprints (st-ocs) and below the tray wall bases.
snap_margin   = (snap_pitch - snap_w) / 2;
plate_chamfer = min(plate_t - bury - 0.2, snap_margin - 0.2);

assert(side_wall_t >= min_wall - 0.001,
       "pocket is wider than the whole-tile plate — should be impossible");
assert(pocket_d >= 20, "pocket depth collapsed");

// PRINT_ANCHOR_BBOX at defaults:
//   X = W = 4 * 28                                     = 112
//   Y = H = 2 * 28                                     = 56
//   Z = z_front = (6.8 - 0.02) + 4 + 20 + 8 + 100 + 8  = 146.78
PRINT_ANCHOR_BBOX = [112, 56, 146.78];

// === Snaps ===
// Frame: X centered, Y = 0 at the tray's bottom edge (bottom on the
// wall as mounted), Z = 0 on the bed at the snap faces.

// One openGrid snap in its own frame (front/strong nub toward +X),
// welded into a single solid — verbatim from opengrid_bin /
// ego_lb6500_blower_mount (st-0of), where it is verified watertight and
// single-component for both snap depths. Each click-nub root gets a
// 0.3mm shim straddling the nub/core contact plane (local x=12.4); the
// 14mm-wide front nub's shim widens to 14.6, and the rear nub's sits
// 0.65 higher (its root rides above the base band in the directional
// variant).
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

// One snap in each CORNER tile, centered in its tile (1.6mm rim to the
// plate edge on every side). zrot(90) turns each snap's strong front
// nub toward +Y — up the wall (load rationale in the header).
//
// Corner tiles rather than opengrid_bin's one-per-tile: the corners put
// the widest possible stance under the cantilever and give the
// lever-out couple the full plate height as its lever arm, which is
// where the strength actually comes from (see the load figures in the
// header). It also keeps the snap count — and so the render cost, which
// is ~95% snap geometry — flat over the whole parameter range instead
// of growing as units_w x units_h.
module grid_snaps() {
    cols = units_w > 1 ? [0, units_w - 1] : [0];
    rows = units_h > 1 ? [0, units_h - 1] : [0];
    for (cx = cols, ry = rows)
        translate([(cx - (units_w - 1) / 2) * snap_pitch,
                   (ry + 0.5) * snap_pitch,
                   0])
            zrot(90) welded_directional_snap();
}

// === Back plate ===

// 45deg chamfer cuts along all four bottom edges of the plate. Four
// explicit triangular prisms rather than edge_profile(): they overshoot
// the ends and overlap at the corners, so the cuts stay transversal
// through the rounded plate corners, and they overshoot 2mm BELOW the
// plate bottom plane (st-n4v: a coplanar cut bottom is a degenerate
// boolean). Differenced from the plate only — grid_snaps() is a sibling
// union — so the snaps cannot be clipped.
module plate_rim_chamfers() {
    c = plate_chamfer;
    // ±X edges: profile in XZ, extruded along Y.
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, H + ov, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = H + 2 * ov)
                        polygon([[W / 2 - c - ov, plate_z0 - ov],
                                 [W / 2 + ov, plate_z0 - ov],
                                 [W / 2 + ov, plate_z0 + c + ov]]);
    // ±Y ends: profile in YZ, extruded along X; the y=0 prism is built
    // directly and mirrored across y = H/2 for the top end.
    for (sy = [0, 1])
        translate([0, sy * H, 0])
            mirror([0, sy, 0])
                translate([-(W + 2 * ov) / 2, 0, 0])
                    rotate([90, 0, 90])
                        linear_extrude(height = W + 2 * ov)
                            polygon([[c + ov, plate_z0 - ov],
                                     [-ov, plate_z0 - ov],
                                     [-ov, plate_z0 + c + ov]]);
}

module plate() {
    difference() {
        translate([0, 0, plate_z0])
            linear_extrude(height = plate_t)
                rect([W, H], rounding = plate_corner_r, anchor = FRONT);
        plate_rim_chamfers();
    }
}

// === Tray ===

// The tray block is extruded along +Y (up the wall) from a plan profile
// in the XZ plane, which is what lets its outer FRONT corners carry
// rect(rounding=) without any hull. Helper: a 2D profile whose local
// (x, y) reads as model (X, Z), swept over model Y in [y0, y1].
module plan_extrude(y0, y1) {
    translate([0, y1, 0])
        rotate([90, 0, 0])
            linear_extrude(height = y1 - y0)
                children();
}

module tray_block() {
    plan_extrude(0, body_h)
        translate([0, plate_top - bury])
            // rect rounding order: [X+Y+, X-Y+, X-Y-, X+Y-]. Local Y+
            // is the tray front; the plate end stays square. The scalar
            // 0 fallback is required, not cosmetic: rect() only takes
            // its square() fast path when rounding is scalar-equal to
            // 0, so an all-zero VECTOR falls into the rounded-polygon
            // path and returns a degenerate path (BOSL2 shapes2d.scad
            // ~line 155, "Unable to convert points[0] to a vec2").
            rect([W, z_front - (plate_top - bury)],
                 rounding = corner_r_e > 0
                     ? [corner_r_e, corner_r_e, 0, 0] : 0,
                 anchor = FRONT);
}

// Interior cut: a (Y, Z) profile extruded across the pocket width. This
// one cut carves the pocket floor, both side-wall inner faces, the open
// top, the open front, the 45deg front lip ramp AND the plenum. It
// punches below the tray's bottom plane at the back so the plenum's
// rear face is the plate's own front face — stopping exactly at
// plate_top would instead leave two coplanar boundary faces in the
// union (st-v7k class). Safe because it is differenced from the tray
// only; the plate is a sibling.
module cavity() {
    zc = plate_top - bury - ov;
    pts = [
        [body_h + ov, zc],                  // up the plate face
        [body_h + ov, z_front + ov],        // over the top, out the front
        [floor_t + lip_e, z_front + ov],    // down the open front...
        [floor_t + lip_e, z_front],         // ...to the lip crest
        [floor_t, z_bend],                  // 45deg inner lip ramp
        [floor_t, zc],                      // pocket floor, back to the plate
    ];
    translate([-pocket_w / 2, 0, 0])
        rotate([90, 0, 90])
            linear_extrude(height = pocket_w)
                polygon(pts);
}

// Rear retaining rib, in two ears either side of the port opening — the
// pocket's back stop, so the device cannot slide into the plenum and
// foul its own plugs. Right triangle in (Y, Z): vertical retaining face
// toward the device at z_rib1, 45deg hypotenuse falling back toward the
// plate. Unioned AFTER the cavity cut (the cavity would otherwise erase
// it), and buried into the floor below and the side wall outboard.
module rib_ear(x0, x1) {
    w = x1 - x0;
    if (w > 0.2)
        translate([x0, 0, 0])
            rotate([90, 0, 90])
                linear_extrude(height = w)
                    polygon([[floor_t - bury, z_rib0 - bury],
                             [floor_t + rib_e, z_rib1],
                             [floor_t - bury, z_rib1]]);
}

module rear_rib() {
    rib_ear(-pocket_w / 2 - bury, port_x_e - port_w_e / 2);
    rib_ear(port_x_e + port_w_e / 2, pocket_w / 2 + bury);
}

// Front-bottom 45deg chamfer across the full width: the outer face of
// the lip ramp, and the matching trim on the side walls' front-bottom
// corners. The hypotenuse passes through (y=0, z=z_bend) and
// (y=lip_e, z=z_front), parallel to the inner ramp — so the lip is a
// constant-thickness ramped wall rather than a solid wedge.
module front_chamfer_cut() {
    translate([-(W / 2 + ov), 0, 0])
        rotate([90, 0, 90])
            linear_extrude(height = W + 2 * ov)
                polygon([[-ov, z_bend - ov],
                         [lip_e + ov, z_front + ov],
                         [-ov, z_front + ov]]);
}

// One floor slot: a plan rectangle that closes at its far (+Z) end in a
// 45deg point, so the floor never bridges back across the slot. Cut
// through the full floor thickness and out both faces.
module floor_slot(xc, z0, z1) {
    w = slot_w_e;
    plan_extrude(-ov, floor_t + ov)
        translate([xc, 0])
            polygon([[-w / 2, z0],
                     [ w / 2, z0],
                     [ w / 2, z1 - w / 2],
                     [ 0,     z1],
                     [-w / 2, z1 - w / 2]]);
}

// Two rows on the same pitch: under the pocket they vent the device,
// in the plenum they drop the cables down the wall.
module floor_slots() {
    if (pocket_ok)
        for (i = [0 : slot_count - 1])
            floor_slot((i - (slot_count - 1) / 2) * slot_pitch,
                       z_rib1 + 5, z_bend - 5);
    if (plenum_ok)
        for (i = [0 : slot_count - 1])
            floor_slot((i - (slot_count - 1) / 2) * slot_pitch,
                       plenum_z0, plenum_z1);
}

// 45deg lead-in along the tray's top inner edges so the device drops
// into the pocket without catching. Extruded along Z, so the chamfer
// face is a vertical wall in print; it starts just clear of the plate
// so it can never notch the plate's front face.
module lead_in_chamfers() {
    for (sx = [-1, 1])
        scale([sx, 1, 1])
            translate([0, 0, plate_top + bury])
                linear_extrude(height = z_front - plate_top + ov)
                    polygon([[pocket_w / 2, body_h - lead_in],
                             [pocket_w / 2 + lead_in + ov, body_h + ov],
                             [pocket_w / 2 - ov, body_h + ov]]);
}

module tray() {
    difference() {
        union() {
            difference() {
                tray_block();
                cavity();
                front_chamfer_cut();
            }
            rear_rib();
        }
        floor_slots();
        lead_in_chamfers();
    }
}

// === Assembly ===

grid_snaps();
plate();
tray();
