// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// OpenGrid wall cradle that holds a 4th-generation Apple TV
// (98 x 98 x 35 mm) VERTICALLY — standing on edge with one 98 x 98
// face flat against the mount plate, parallel to the panel (pst-e1v).
//
// This replaces the original horizontal open-tray form (pst-hn2). A
// tray cantilevered the device ~75 mm off the panel; standing it up
// drops the protrusion to the device's 35 mm thickness plus the plate
// and snaps (~46 mm off the panel face at defaults, vs ~140 mm), which
// is what makes it tuckable behind a wall-mounted TV. The load path
// improves with it: the overturning moment falls by ~3.5x because the
// centre of mass moves from ~75 mm off the panel to ~25 mm.
//
// DEVICE (Apple TV HD / 4th gen, 2015, model A1625): 98 mm square,
// 35 mm thick, 425 g, rounded corners, ports along ONE edge — mounted
// here as the BOTTOM edge, so plugs and cables hang straight down out
// of the cable cutout instead of being trapped behind the device.
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived holder is for personal use only; do
// not sell prints or files.
//
// === Form: slide-in cradle, and how you actually load it ===
//
// A bottom shelf carries the device's weight; two full-height side
// rails stop it sliding sideways; each rail carries a small front lip
// (`lip_reach`) that overlaps the device's front face so it cannot tip
// or fall out. The top is open.
//
// Honest note on "drop it in from the top": with front lips on both
// rails, straight-down insertion is geometrically impossible — the gap
// between the lips (pocket_w - 2 * lip_reach) is by construction
// NARROWER than the device, which is exactly what makes the lips
// retain. So loading is tilt-and-rock: stand the device's bottom edge
// on the shelf tilted forward, then rock the top back against the
// plate until it is behind both lips. The lips' 45deg undersides are
// the lead-in for that rock. Do it at the bench, then snap the loaded
// cradle onto the panel — behind a TV you do not want to be fiddling
// with retention by feel.
//
// The alternative (front lip on the shelf only, nothing on the rails)
// IS a true drop-in, but leaves the device free to rotate forward out
// of the cradle about its bottom-front corner. Behind a TV that is a
// one-way trip to the floor, so captive won.
//
// === Print orientation (native): ZERO supports ===
//
// Prints snaps-down, the orientation the snap geometry was designed
// for. Mounted, +Y is UP the wall and +Z points OUT from the panel, so
// +Z is also the build direction. Everything that gains material as
// the print rises is either a 45deg plane or a face at constant Y (a
// vertical wall in print, free):
//
//  - plate underside between snaps: 3.2 mm bridges on the 28 mm pitch
//    (proven at these exact spans by opengrid_bin / the
//    led_remote_holder twins); plate rim: 45deg chamfer clamped so it
//    never crosses a snap footprint (st-ocs);
//  - plate vent slots run straight along the build axis, so they have
//    no ceiling to bridge at all;
//  - bottom shelf and side rails: solid columns growing in +Z off the
//    plate, every layer landing on the one below;
//  - the back-relief step (where the rails' inner faces jump OUTBOARD
//    from the device-back lands to the pocket sides at `z_back`) opens
//    up as Z rises — material is being removed, never added;
//  - retaining lips: their undersides are 45deg ramps from the pocket
//    wall to the lip crest, the same self-supporting idiom
//    opengrid_bin uses for its front lip. A square lip underside would
//    be a flat overhang the full length of both rails;
//  - the shelf's bottom-front and the rails' top-front edges carry
//    45deg end chamfers whose faces point upward in print.
//
// === Wall-hang orientation / load direction ===
//
// Directional snaps with the strong front nub (non-flexing, 0.8 mm
// deep vs 0.4) turned +Y — up the wall — put pull-out load on the
// rigid hook, while the flexy click-in side faces down where the
// moment presses the plate into the panel. Same rationale as
// opengrid_bin / ego_lb6500 (st-0of), and unchanged from pst-hn2.
//
// Sizing, at defaults: ~0.5 kg with its centre of mass ~25 mm off the
// panel is ~0.12 N.m. The plate pivots about its bottom edge and the
// top snap row sits at y = 98 mm, so that row carries ~1.3 N total,
// ~0.6 N per snap — an order of magnitude inside an openGrid hook, and
// a third of what the old tray asked for. The four snaps are one per
// CORNER tile: widest stance under the load, full plate height as the
// lever arm for the couple, and — because render cost here is ~95%
// snap geometry — a snap count that stays flat over the whole
// parameter range instead of growing as units_w x units_h.
//
// === Ventilation ===
//
// The Apple TV runs warm and is passively cooled through its case, so
// pressing 98 x 98 mm of it flat against a PLA plate would be the one
// real regression of standing it up. Two vertical `land_w` strips hold
// the device `back_relief` off the plate, leaving a full-height air
// channel behind it that is open at the top and vents out of the cable
// cutout at the bottom — a chimney. `vent_count` slots through the
// plate open that channel to the panel lattice; they are placed in the
// band the corner snap footprints leave clear, so they can never
// collide with a snap.
//
// === Cables ===
//
// The port edge faces down. The shelf is two corner ears with a
// `cable_w` gap between them, so plug bodies project down through the
// gap into free air and the cables run down the wall in front of the
// plate — nothing is trapped between the device and the panel.
//
// === Why no mount_orientation param ===
//
// The bead offered keeping the old horizontal tray selectable. It does
// not fall out cleanly: the two forms share only the plate and the
// snap grid, so a switch would mean carrying both geometries, both
// derived blocks, and both sets of invariants probes behind an `if`,
// for a form the operator has replaced. Vertical only; the tray is in
// git history at pst-hn2 if it is ever wanted back.
//
// === Fit / corners ===
//
// The pocket is device + `fit_clearance` per side, with SQUARE plan
// corners: the Apple TV's own corners are rounded, so square pocket
// corners can only ever give clearance, never bind. The visible OUTER
// front corners of the rails are rounded (`corner_r`) to echo the
// device's radius, clamped to leave >= 1 mm of rail surviving.
//
// === Structure / mesh-robustness notes ===
//
// Snaps weld 0.02 mm into the plate and carry the sibling models'
// root-fillet shims (st-v7k: openGridSnap's click nubs are
// face-touching solids; the shims fuse them into one clean solid on
// both CGAL and Manifold). The cradle body buries 0.6 mm into the
// plate. Cut tools overshoot every face they pass through (st-n4v:
// coplanar cut faces are degenerate booleans), and the pocket cut is
// differenced from the CRADLE BODY only — the plate is a sibling union
// — so it can never gouge the plate or clip a snap. Nothing uses
// hull-backed rounding (BOSL2 cuboid edges=): the wasm engine's CGAL
// applyHull() asserts on some swept dimensions (st-7x7/st-560 class),
// so rounding is done as 2D rect(rounding=) footprints and explicit
// 45deg prisms.

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Device -----
device_w      = 98;  // @param number min=60 max=140 step=0.5 unit=mm group=device label="Device width (across the wall)"
device_h      = 98;  // @param number min=60 max=140 step=0.5 unit=mm group=device label="Device height (up the wall)"
device_t      = 35;  // @param number min=10 max=60 step=0.5 unit=mm group=device label="Device thickness (off the wall)"
fit_clearance = 1;   // @param number min=0.3 max=3 step=0.1 unit=mm group=device label="Pocket clearance per side"

// ----- Shell -----
plate_t     = 4;  // @param number min=3 max=6 step=0.5 unit=mm group=shell label="Back plate thickness"
shelf_rise  = 10; // @param number min=4 max=30 step=0.5 unit=mm group=shell label="Shelf height above plate bottom"
shelf_t     = 4;  // @param number min=2.5 max=8 step=0.5 unit=mm group=shell label="Shelf thickness"
back_relief = 2;  // @param number min=0 max=6 step=0.5 unit=mm group=shell label="Air gap behind the device"
corner_r    = 5;  // @param number min=0 max=10 step=0.5 unit=mm group=shell label="Outer front corner radius"

// ----- Retention -----
lip_reach = 3;  // @param number min=1 max=8 step=0.5 unit=mm group=retention label="Rail lip overlap onto the device"
land_w    = 12; // @param number min=1 max=30 step=0.5 unit=mm group=retention label="Back land width (per side)"

// ----- Cables -----
cable_w = 78; // @param number min=20 max=120 step=1 unit=mm group=cables label="Bottom cable cutout width"
cable_x = 0;  // @param number min=-25 max=25 step=1 unit=mm group=cables label="Cable cutout offset (+ = right)"

// ----- Ventilation -----
vent_count = 3;  // @param integer min=0 max=6 group=vent label="Plate vent slots"
vent_w     = 10; // @param number min=4 max=20 step=0.5 unit=mm group=vent label="Plate vent slot width"

// ----- OpenGrid mount -----
// Tile counts are MINIMUMS: the plate always grows to whole tiles big
// enough for the device, so the mount stays grid-aligned whatever the
// device dimensions are set to.
width_units  = 4;     // @param integer min=1 max=6 group=mount label="Width (openGrid units, min)"
height_units = 4;     // @param integer min=1 max=6 group=mount label="Height (openGrid units, min)"
snap_lite    = false; // @param boolean group=mount label="Lite snaps (3.4mm instead of 6.8mm)"

// @preset id="default" label="Apple TV HD, vertical" device_w=98 device_h=98 device_t=35 fit_clearance=1 plate_t=4 shelf_rise=10 shelf_t=4 back_relief=2 corner_r=5 lip_reach=3 land_w=12 cable_w=78 cable_x=0 vent_count=3 vent_w=10 width_units=4 height_units=4 snap_lite=false
// @preset id="snug" label="Tight captive fit" device_w=98 device_h=98 device_t=35 fit_clearance=0.5 plate_t=4 shelf_rise=10 shelf_t=4 back_relief=2 corner_r=5 lip_reach=5 land_w=12 cable_w=78 cable_x=0 vent_count=3 vent_w=10 width_units=4 height_units=4 snap_lite=false

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed depth of snap tops into the plate (st-v7k)

// Parts sink this far into the solid below them; cut tools overshoot
// this far past every face they pass through.
bury = 0.6;
ov   = 2;

pocket_w = device_w + 2 * fit_clearance;   // across the wall
pocket_h = device_h + fit_clearance;       // up the wall (open at top)
pocket_t = device_t + fit_clearance;       // off the wall

// Plate is whole openGrid tiles, grown past the unit minimums whenever
// the device needs it, so the snap grid always covers the cradle.
min_wall = 2.4;
units_w  = max(width_units,  ceil((pocket_w + 2 * min_wall) / snap_pitch));
units_h  = max(height_units, ceil((shelf_rise + pocket_h) / snap_pitch));
W = units_w * snap_pitch;
H = units_h * snap_pitch;

// Side rails take up whatever the whole-tile plate leaves around the
// pocket, so their thickness is derived rather than dialled.
side_wall_t = (W - pocket_w) / 2;

plate_z0  = snap_h - weld;      // plate bottom (welds into snap tops)
plate_top = plate_z0 + plate_t; // plate front face

// Both clamps floor at 0.5 rather than 0: a zero-width land or lip
// would collapse two vertices of the pocket profile onto each other
// and hand polygon() a degenerate path.
land_e = max(0.5, min(land_w,    pocket_w / 2 - 5));
lip_e  = max(0.5, min(lip_reach, min(side_wall_t - 1, pocket_w / 2 - 5)));

z_back  = plate_top + back_relief;  // device's back face rests here
z_face  = z_back + pocket_t;        // device's front face / lip ramp start
z_front = z_face + lip_e;           // rail crest, and the model's top in print

// Shelf cannot start below the plate's bottom edge.
shelf_t_e = min(shelf_t, shelf_rise);
y_shelf0  = shelf_rise - shelf_t_e;

// Leave >= 1mm of rail surviving at the rounded outer corner.
corner_r_e = max(0, min(corner_r, side_wall_t - 1));

// 45deg break on the shelf's bottom-front and the rails' top-front
// edges. Not a @param: it is finish, and every extra slider costs the
// wasm sweep a pair of full renders.
end_chamfer = min(1.5, shelf_t_e - 0.5);

// Cable cutout: keep >= 6mm of shelf ear each side, then clamp the
// offset so both ears survive.
cable_w_e   = max(0, min(cable_w, pocket_w - 12));
cable_x_max = max(0, (pocket_w - cable_w_e) / 2 - 6);
cable_x_e   = max(-cable_x_max, min(cable_x, cable_x_max));

// Plate vent slots live in the rectangle the four corner-tile snap
// footprints leave clear, further clipped to the device's own back so
// they always open into the relief channel rather than into a rail.
vent_x_max  = units_w > 1
    ? min((units_w - 1) / 2 * snap_pitch - snap_w / 2 - 2,
          pocket_w / 2 - land_e - 2)
    : 0;
vent_y0_raw = 0.5 * snap_pitch + snap_w / 2 + 2;
vent_y1_raw = units_h > 1
    ? (units_h - 0.5) * snap_pitch - snap_w / 2 - 2
    : 0;
vent_y0 = max(vent_y0_raw, shelf_rise + 2);
vent_y1 = min(vent_y1_raw, shelf_rise + pocket_h - 2);
vent_pitch = vent_count > 0 ? 2 * vent_x_max / vent_count : 0;
vent_w_e   = vent_count > 0 ? min(vent_w, vent_pitch - 3) : 0;
vent_ok    = vent_count > 0 && vent_x_max > 6 && vent_w_e > 2
             && (vent_y1 - vent_y0) > 10;

plate_corner_r = 1;   // plate outline rounding, matches the siblings
// 45deg plate bottom-rim chamfer. The snap grid leaves a 1.6mm rim
// ((28 - 24.8)/2) per side; the clamp keeps the cut off the snap
// footprints (st-ocs) and below the cradle's base.
snap_margin   = (snap_pitch - snap_w) / 2;
plate_chamfer = min(plate_t - bury - 0.2, snap_margin - 0.2);

assert(side_wall_t >= min_wall - 0.001,
       "pocket is wider than the whole-tile plate — should be impossible");
assert(pocket_h >= 20, "pocket height collapsed");
assert(H >= shelf_rise + 1, "plate is shorter than the shelf");

// PRINT_ANCHOR_BBOX at defaults:
//   X = W = 4 * 28                                  = 112
//   Y = H = 4 * 28                                  = 112
//   Z = z_front = (6.8 - 0.02) + 4 + 2 + 36 + 3     = 51.78
PRINT_ANCHOR_BBOX = [112, 112, 51.78];

// === Snaps ===
// Frame: X centered, Y = 0 at the plate's bottom edge (bottom on the
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

// Stadium slots straight through the plate along the build axis, so
// they cost nothing in print and open the back-relief channel to the
// panel lattice.
module vent_slots() {
    if (vent_ok)
        for (i = [0 : vent_count - 1])
            translate([(i - (vent_count - 1) / 2) * vent_pitch,
                       (vent_y0 + vent_y1) / 2,
                       plate_z0 - ov])
                linear_extrude(height = plate_t + 2 * ov)
                    rect([vent_w_e, vent_y1 - vent_y0],
                         rounding = vent_w_e * 0.49);
}

module plate() {
    difference() {
        translate([0, 0, plate_z0])
            linear_extrude(height = plate_t)
                rect([W, H], rounding = plate_corner_r, anchor = FRONT);
        plate_rim_chamfers();
        vent_slots();
    }
}

// === Cradle ===

// The cradle is extruded along +Y (up the wall) from a plan profile in
// the XZ plane, which is what lets its outer FRONT corners carry
// rect(rounding=) without any hull, and what makes the pocket — lands,
// rail faces and lips alike — a single constant cross-section cut.
// Helper: a 2D profile whose local (x, y) reads as model (X, Z), swept
// over model Y in [y0, y1].
module plan_extrude(y0, y1) {
    translate([0, y1, 0])
        rotate([90, 0, 0])
            linear_extrude(height = y1 - y0)
                children();
}

// Solid slab from the shelf's underside to the plate's top edge, the
// full plate width, standing off the plate face out to the rail crest.
// The pocket is carved out of it above the shelf.
module cradle_block() {
    plan_extrude(y_shelf0, H)
        translate([0, plate_top - bury])
            // rect rounding order: [X+Y+, X-Y+, X-Y-, X+Y-]. Local Y+
            // is the front (away from the panel); the plate end stays
            // square. The scalar 0 fallback is required, not cosmetic:
            // rect() only takes its square() fast path when rounding is
            // scalar-equal to 0, so an all-zero VECTOR falls into the
            // rounded-polygon path and returns a degenerate path (BOSL2
            // shapes2d.scad ~line 155, "Unable to convert points[0] to
            // a vec2").
            rect([W, z_front - (plate_top - bury)],
                 rounding = corner_r_e > 0
                     ? [corner_r_e, corner_r_e, 0, 0] : 0,
                 anchor = FRONT);
}

// The pocket, as one (X, Z) profile swept up the wall from the shelf
// top to past the plate's top edge. Reading it from the plate outward:
// the narrow band at the bottom is the void BETWEEN the two back lands
// the device rests on; at z_back the void steps outboard to the full
// pocket width (rail inner faces); at z_face each side ramps back in at
// 45deg to the lip crest. It punches below the cradle's own bottom
// plane so the pocket's rear face is the plate's own front face —
// stopping exactly at plate_top would instead leave two coplanar
// boundary faces in the union (st-v7k class). Safe because it is
// differenced from the cradle block only; the plate is a sibling.
module pocket_cavity() {
    pw2  = pocket_w / 2;
    li   = pw2 - land_e;   // land inner edge — the relief channel wall
    lipi = pw2 - lip_e;    // lip crest, overlapping the device's face
    zc   = plate_top - bury - ov;
    plan_extrude(shelf_rise, H + ov)
        polygon([[-li,   zc],
                 [ li,   zc],
                 [ li,   z_back],
                 [ pw2,  z_back],
                 [ pw2,  z_face],
                 [ lipi, z_front],
                 [ lipi, z_front + ov],
                 [-lipi, z_front + ov],
                 [-lipi, z_front],
                 [-pw2,  z_face],
                 [-pw2,  z_back],
                 [-li,   z_back]]);
}

// Splits the shelf into two corner ears. Cables and plug bodies drop
// straight down through the gap, and it is also the bottom mouth of the
// back-relief chimney. Overshoots INTO the pocket void above the shelf
// (rather than stopping level with it) so the two cut tools overlap
// instead of meeting face-to-face (st-n4v).
module cable_cut() {
    y0 = y_shelf0 - ov;
    y1 = shelf_rise + ov;
    z0 = plate_top - bury - ov;
    z1 = z_front + ov;
    translate([cable_x_e - cable_w_e / 2, y0, z0])
        cube([cable_w_e, y1 - y0, z1 - z0]);
}

// 45deg breaks on the two exposed front edges that the XZ plan rounding
// cannot reach: the shelf's bottom-front and the rails' top-front. Both
// faces point upward in print, so neither costs support. Profiles in
// (Y, Z), extruded across the full width.
module end_chamfers() {
    c = end_chamfer;
    if (c > 0.2)
        translate([-(W / 2 + ov), 0, 0])
            rotate([90, 0, 90])
                linear_extrude(height = W + 2 * ov) {
                    polygon([[y_shelf0 - ov, z_front - c],
                             [y_shelf0,      z_front - c],
                             [y_shelf0 + c,  z_front],
                             [y_shelf0 + c + ov, z_front],
                             [y_shelf0 + c + ov, z_front + ov],
                             [y_shelf0 - ov, z_front + ov]]);
                    polygon([[H + ov,     z_front - c],
                             [H,          z_front - c],
                             [H - c,      z_front],
                             [H - c - ov, z_front],
                             [H - c - ov, z_front + ov],
                             [H + ov,     z_front + ov]]);
                }
}

module cradle() {
    difference() {
        cradle_block();
        pocket_cavity();
        cable_cut();
        end_chamfers();
    }
}

// === Assembly ===

grid_snaps();
plate();
cradle();
