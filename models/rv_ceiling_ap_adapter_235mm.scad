// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// RV ceiling speaker-hole -> WiFi AP adapter/cover plate (st-nhd).
// Covers a 235 mm (9.25 in) ceiling speaker cutout, screws to the
// ceiling through a flange ring, self-centers via a recessed cup that
// nests up into the hole, and presents a 100 mm mating platform with
// 4x M3 heat-set inserts on an 82.55 mm (3.25 in) bolt circle for the
// AP's mounting bracket. Installs overhead: recess goes UP into the
// ceiling, AP hangs DOWN into the room.
//
// === Recorded interpretations / decisions (st-nhd) ===
//
//  - 3.25 in is read as the bolt-circle DIAMETER (distance across
//    opposite holes). The adjacent-spacing reading would put opposite
//    holes at 4.6 in — outside the 100 mm mount — so it's wrong.
//  - ONE-PIECE print at flange_outer_dia = 252 on a 256 mm bed
//    (~1 mm margin, ~8.75 mm flange overlap past the hole edge). No
//    split-segment variant is built; add one only if a wider flange
//    is ever requested.
//  - Ceiling screws default to 6x #6 (3.5 mm) with flush countersunk
//    heads on the room face. The bolt circle defaults to 243 mm
//    (bead said "~244"): 243 keeps the 7 mm countersink rim >= 1 mm
//    inside the plate edge and >= 0.5 mm clear of the perimeter lip.
//  - The AP mating face is FLUSH with the flange's room face and is
//    defined by a relief groove ring (see print orientation below).
//  - REVISED (st-so4): the AP bracket has a RAISED SOLID CENTER HUB
//    with only a pinhole — no cable pass-through at the exact center.
//    Its wiring openings are large cutouts OFFSET from center, inside
//    the bolt circle. So the cable pass-through is now a parametric
//    ring of ARC (kidney) SLOTS offset from center (count, radius,
//    arc length, width, rotation all tunable) — the arc shape gives a
//    wide angular pass zone so the cable finds a path without exact
//    rotational alignment with the bracket. The slot radius is
//    clamped clear of the insert holes and the rib roots. The old
//    dead-center hole (cable_hole_dia) is kept as a parameter but
//    defaults to 0 (off) since it lines up with the bracket's solid
//    hub.
//  - Heat-set inserts default to M3 (4.0 mm hole x 5.5 mm deep) per
//    the bead; operator to confirm the AP bracket's actual screws.
//
// === Print orientation (native): ZERO supports ===
//
// Prints room-face-down. The whole room face — flange ring, pocket
// floor, AP boss mating face — is ONE coplanar plane on the bed
// (maximum adhesion area for a 252 mm disk, the best warp insurance
// there is). This is why the boss face is flush rather than proud: a
// boss protruding past the flange plane would float the entire flange
// on supports in every orientation (both faces of this plate have
// opposite-direction features; coplanarity is the only support-free
// arrangement). The boss is still a defined platform — a relief
// groove ring (4 x 2.5 mm) just outside ap_mount_dia gives the
// bracket a crisp seating edge and burr/lip relief.
//
// Everything above the bed is vertical walls and up-facing surfaces:
//  - recess cup wall, AP boss wall, stiffening ribs: vertical;
//  - the recess pocket OPENS TOWARD THE CEILING (no ceiling panel
//    over the cavity — a closed top would be a ~60 mm annular bridge
//    over the pocket, the exact overhang this layout exists to avoid);
//  - groove ceiling: 4 mm bridge; insert hole tops: 4 mm circle
//    bridges; both trivially self-bridging;
//  - countersinks + insert entry chamfers: 45 deg cones opening at
//    the bed — standard self-supporting countersink-down practice;
//  - cable slots: full-height vertical-walled cuts through the boss
//    column (open at both faces — no new bridges, no support impact);
//  - wall lead-in chamfer + lip: up-facing.
//
// === Structure / warp mitigation ===
//
// One rotate_extrude of a single closed 2D profile forms the entire
// axisymmetric body (base disk, recess wall, AP boss, relief groove,
// perimeter lip, edge chamfers) — one revolved solid, no internal
// unions to leak (st-v7k class). Radial ribs and the discrete holes
// are volumetric unions/cuts into that solid (never face-kissing;
// everything overlaps by >= 0.6 mm, st-v7k).
//
// Stiffness against warp/flex on a thin 252 mm disk comes from the
// recess cup wall (a 13 mm-tall ring at r~114), rib_count radial ribs
// tying the AP boss to that wall, and the perimeter lip. The lip
// rises lip_h above the flange's ceiling face at the outer rim, so
// the EDGE contacts the ceiling first and the screws preload it tight
// against an imperfect surface — a clean shadow-gap-free border, like
// a trim ring. Set lip_h = 0 for a fully flat ceiling face.

$fn = 96;

// === User-tunable parameters ===

// ----- Ceiling hole + flange -----
ceiling_hole_dia = 235;  // @param number min=200 max=245 step=0.5 unit=mm group=ceiling label="Ceiling cutout diameter"
hole_clearance   = 1.25; // @param number min=0.5 max=3 step=0.25 unit=mm group=ceiling label="Recess clearance per side"
flange_outer_dia = 252;  // @param number min=240 max=254 step=1 unit=mm group=ceiling label="Flange outer diameter (max 254 = X1C bed)"
flange_t         = 4;    // @param number min=3 max=6 step=0.5 unit=mm group=ceiling label="Flange / floor thickness"
lip_h            = 1.0;  // @param number min=0 max=2 step=0.25 unit=mm group=ceiling label="Perimeter seating-lip height (0 = flat)"

// ----- Ceiling screws -----
screw_count    = 6;    // @param number min=4 max=10 step=1 group=screws label="Ceiling screw count"
screw_hole_dia = 4.0;  // @param number min=3 max=5.5 step=0.1 unit=mm group=screws label="Screw clearance hole (#6 = 4.0)"
screw_head_dia = 7.0;  // @param number min=6 max=10 step=0.5 unit=mm group=screws label="Countersink head diameter"
screw_bc_dia   = 243;  // @param number min=238 max=248 step=0.5 unit=mm group=screws label="Screw bolt-circle diameter"

// ----- Recess (nests into the hole) -----
recess_depth  = 9;  // @param number min=5 max=15 step=0.5 unit=mm group=recess label="Recess projection into the ceiling"
recess_wall_t = 4;  // @param number min=2.4 max=6 step=0.4 unit=mm group=recess label="Recess cup wall thickness"
rib_count     = 6;  // @param number min=0 max=12 step=1 group=recess label="Stiffening rib count"

// ----- AP mount -----
ap_mount_dia       = 100;   // @param number min=60 max=140 step=1 unit=mm group=ap label="AP mating boss diameter"
ap_bolt_circle_dia = 82.55; // @param number min=40 max=120 step=0.05 unit=mm group=ap label="Insert bolt-circle diameter (3.25in = 82.55)"
insert_hole_dia    = 4.0;   // @param number min=3 max=6.5 step=0.1 unit=mm group=ap label="Heat-set insert hole (M3 = 4.0)"
insert_depth       = 5.5;   // @param number min=4 max=10 step=0.5 unit=mm group=ap label="Heat-set insert depth"
cable_hole_dia     = 0;     // @param number min=0 max=60 step=1 unit=mm group=ap label="Dead-center cable hole (0 = off; AP bracket hub is solid)"

// ----- Offset cable pass-through (st-so4) -----
// Arc (kidney) slots on a circle between the center and the insert
// bolt circle, matching the AP bracket's off-center wiring openings.
cable_slot_count   = 2;   // @param number min=0 max=6 step=1 group=cable label="Cable slot count (0 = none)"
cable_slot_bc_dia  = 54;  // @param number min=20 max=80 step=1 unit=mm group=cable label="Slot centerline circle diameter"
cable_slot_arc_deg = 60;  // @param number min=10 max=120 step=5 unit=deg group=cable label="Slot arc length (between end-cap centers)"
cable_slot_w       = 14;  // @param number min=6 max=24 step=0.5 unit=mm group=cable label="Slot radial width"
cable_slot_rot_deg = 45;  // @param number min=0 max=180 step=5 unit=deg group=cable label="Slot pattern rotation"

// @preset id="default" label="Default (235mm hole, one-piece, M3 inserts)" ceiling_hole_dia=235 hole_clearance=1.25 flange_outer_dia=252 flange_t=4 lip_h=1 screw_count=6 screw_hole_dia=4 screw_head_dia=7 screw_bc_dia=243 recess_depth=9 recess_wall_t=4 rib_count=6 ap_mount_dia=100 ap_bolt_circle_dia=82.55 insert_hole_dia=4 insert_depth=5.5 cable_hole_dia=0 cable_slot_count=2 cable_slot_bc_dia=54 cable_slot_arc_deg=60 cable_slot_w=14 cable_slot_rot_deg=45

// Debug: cut the +Y half away to expose the cross-section (used by
// the committed section render; never on for printing/export).
section_view = false;

// === Derived ===

recess_dia = ceiling_hole_dia - 2 * hole_clearance;  // 232.5 @ defaults
recess_r   = recess_dia / 2;                         // 116.25
wall_in_r  = recess_r - recess_wall_t;               // 112.25
flange_r   = flange_outer_dia / 2;                   // 126
boss_r     = ap_mount_dia / 2;                       // 50
total_h    = flange_t + recess_depth;                // 13: room face -> wall top

lip_w         = 2.0;   // perimeter lip radial width
edge_chamfer  = 0.6;   // 45deg bed-edge chamfer on the outer rim
lead_in       = 1.5;   // 45deg entry chamfer on the recess wall top
groove_w      = 4.0;   // relief groove ring width outside the boss
// Relief groove depth, clamped so its bridged ceiling never thins
// below 1 mm even at the minimum flange_t.
groove_d      = min(2.5, flange_t - 1);
bury          = 0.6;   // volumetric overlap for welded unions (st-v7k)

// Ribs tie the boss to the cup wall, buried radially into both and
// vertically into the floor. Clamped so a small ap_mount_dia can
// never push the rib root past the insert bolt circle's meat.
rib_w    = 2.4;
rib_in_r = boss_r - 5;
rib_out_r = wall_in_r + 0.75;

// Cable slot centerline radius, clamped so the slot's outer edge
// always stays >= 2 mm clear of the insert holes and >= 1 mm clear of
// the rib roots (never cut a rib or an insert boss), and its inner
// edge stays >= 0.5 mm off the axis (valid annulus even at extreme
// slider combos — the inner-edge clamp wins if they conflict). At the
// defaults every clamp is inactive: slot_r = 54/2 = 27, max 30.275.
slot_out_max_r = min(ap_bolt_circle_dia / 2 - insert_hole_dia / 2 - 2,
                     rib_count > 0 ? rib_in_r - 1 : boss_r - 1.5);
slot_r = max(cable_slot_w / 2 + 0.5,
             min(cable_slot_bc_dia / 2, slot_out_max_r - cable_slot_w / 2));

// Countersink cone: 45deg from screw_head_dia down to the hole.
cs_h = (screw_head_dia - screw_hole_dia) / 2;
// Screw bolt circle clamped so the countersink rim always stays
// >= 1 mm inside the plate edge (a slider combo like a small flange
// with a big head must never break through the outer wall). At the
// defaults the clamp is exactly inactive: min(121.5, 126-3.5-1) = 121.5.
screw_bc_r = min(screw_bc_dia / 2, flange_r - screw_head_dia / 2 - 1);

// PRINT_ANCHOR_BBOX at defaults:
//   X = Y = flange_outer_dia          = 252
//   Z = flange_t + recess_depth = 4+9 = 13
PRINT_ANCHOR_BBOX = [252, 252, 13];

// === Axisymmetric body ===
// One closed profile in the (r, z) half-plane, room face at z = 0
// (the bed), ceiling side up. Revolved solid includes: base disk with
// bed-edge chamfer, relief groove, perimeter lip, recess cup wall
// with lead-in chamfer, AP boss column. The cable hole is drilled
// afterward so cable_hole_dia = 0 degenerates cleanly.
module body_revolve() {
    // lip_h = 0 must not leave duplicate consecutive vertices (a
    // degenerate polygon edge), so the lip step only enters the
    // profile when it has height.
    lip_pts = lip_h > 0
        ? [[flange_r, flange_t + lip_h],               // outer wall
           [flange_r - lip_w, flange_t + lip_h],       // lip top
           [flange_r - lip_w, flange_t]]               // lip inner wall
        : [[flange_r, flange_t]];                      // flat rim
    rotate_extrude(convexity = 6)
        polygon(concat(
            [[0, 0],                                   // axis, room face
             [boss_r, 0],                              // boss mating face
             [boss_r, groove_d],                       // groove inner wall
             [boss_r + groove_w, groove_d],            // groove ceiling
             [boss_r + groove_w, 0],                   // groove outer wall
             [flange_r - edge_chamfer, 0],             // bed face
             [flange_r, edge_chamfer]],                // bed-edge chamfer
            lip_pts,
            [[recess_r, flange_t],                     // flange ceiling face
             [recess_r, total_h - lead_in],            // cup wall outer
             [recess_r - lead_in, total_h],            // lead-in chamfer
             [wall_in_r, total_h],                     // cup wall top
             [wall_in_r, flange_t],                    // cup wall inner
             [boss_r, flange_t],                       // pocket floor top
             [boss_r, total_h],                        // boss outer wall
             [0, total_h]]));                          // boss top -> axis
}

// === Ribs ===
// Radial stiffeners across the open pocket: buried 5 mm into the boss,
// 0.75 mm into the cup wall, and `bury` into the floor. Tops are flush
// with the cup wall / boss tops. The 15 deg offset keeps every rib
// off the 0/90/180/270 insert axes for any rib_count up to 12
// (cosmetic only — inserts end at r = 43.3, ribs start at r = 45, so
// they can't collide radially at defaults anyway).
module ribs() {
    if (rib_count > 0)
        for (i = [0 : rib_count - 1])
            rotate([0, 0, i * 360 / rib_count + 15])
                translate([rib_in_r, -rib_w / 2, flange_t - bury])
                    cube([rib_out_r - rib_in_r, rib_w,
                          total_h - flange_t + bury]);
}

// === Cuts ===

// Countersunk ceiling-screw holes: clearance shaft through the
// flange, 45deg countersink opening at the bed so the head sits
// flush on the room face.
module screw_holes() {
    for (i = [0 : screw_count - 1])
        rotate([0, 0, i * 360 / screw_count])
            translate([screw_bc_r, 0, 0]) {
                translate([0, 0, -1])
                    cylinder(d = screw_hole_dia, h = flange_t + lip_h + 2);
                translate([0, 0, -0.01])
                    cylinder(d1 = screw_head_dia, d2 = screw_hole_dia,
                             h = cs_h);
            }
}

// Heat-set insert holes: 4x on the bolt circle, 90 deg apart, opening
// on the room face (the accessible face — inserts press in from
// below after printing). 0.5 mm entry chamfer for iron alignment.
module insert_holes() {
    for (i = [0 : 3])
        rotate([0, 0, i * 90])
            translate([ap_bolt_circle_dia / 2, 0, 0]) {
                translate([0, 0, -1])
                    cylinder(d = insert_hole_dia, h = insert_depth + 1);
                translate([0, 0, -0.01])
                    cylinder(d1 = insert_hole_dia + 1, d2 = insert_hole_dia,
                             h = 0.5);
            }
}

// Optional dead-center hole (default off — the AP bracket's center
// hub is solid, so nothing lines up behind it; see st-so4 note).
module cable_hole() {
    if (cable_hole_dia > 0)
        translate([0, 0, -1])
            cylinder(d = cable_hole_dia, h = total_h + 2);
}

// 2D pie wedge spanning [-a/2, +a/2] out to radius r, for masking an
// annulus down to an arc. Fan-triangulated from the origin.
module pie_2d(r, a) {
    n = max(4, ceil($fn * a / 360));
    polygon(concat([[0, 0]],
        [for (i = [0 : n]) let (t = -a / 2 + a * i / n)
            [r * cos(t), r * sin(t)]]));
}

// 2D arc (kidney) slot: an annular band of radial width w on
// centerline radius r, spanning arc_deg between the end-cap centers,
// closed with semicircular ends (so the full angular span is a bit
// more than arc_deg).
module arc_slot_2d(r, w, arc_deg) {
    intersection() {
        difference() {
            circle(r = r + w / 2);
            circle(r = r - w / 2);
        }
        pie_2d(r + w, arc_deg);
    }
    for (a = [-arc_deg / 2, arc_deg / 2])
        rotate([0, 0, a])
            translate([r, 0])
                circle(d = w);
}

// Offset cable pass-through slots (st-so4): full-height vertical cuts
// through the AP boss on the (clamped) slot_r circle, equally spaced,
// rotated as a pattern by cable_slot_rot_deg. Default pair at 45/225
// deg sits between the 0/90/180/270 insert axes.
module cable_slots() {
    if (cable_slot_count > 0)
        for (i = [0 : cable_slot_count - 1])
            rotate([0, 0, cable_slot_rot_deg + i * 360 / cable_slot_count])
                translate([0, 0, -1])
                    linear_extrude(total_h + 2)
                        arc_slot_2d(slot_r, cable_slot_w, cable_slot_arc_deg);
}

// === Assembly ===

module adapter_plate() {
    difference() {
        union() {
            body_revolve();
            ribs();
        }
        screw_holes();
        insert_holes();
        cable_hole();
        cable_slots();
    }
}

if (section_view)
    difference() {
        adapter_plate();
        translate([-flange_r - 5, 0, -5])
            cube([flange_outer_dia + 10, flange_r + 10, total_h + 10]);
    }
else
    adapter_plate();
