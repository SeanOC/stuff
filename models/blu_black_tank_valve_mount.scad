// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Captive bench-top mount for a Blu Technology 3-way black-tank flush
// valve (st-i32). Companion part to the Blu flow meter mount v2
// (st-246, blu_flow_meter_mount_80mm.scad) — same hardware pattern
// (bottom-entry M3 SHCS, heat-set inserts in caps), but ASYMMETRIC
// saddles (the valve's two inner fittings have different OD) and an
// extra handle-clearance cut so the T-handle's swept volume stays
// free.
//
// === Part being mounted (Blu Technology flush valve) ===
//
//   - Inline pair: female QD socket on one end, male QD plug on the
//     other; both project past the saddles into open air. The portion
//     the saddle grips is the HEX wrench-nut at each inner end of the
//     inline pair — flats, not a round body.
//   - Side outlet (3rd fitting): perpendicular to the inline axis,
//     exits laterally past one Y edge of the base.
//   - T-handle: vertical (+Z), rotates ~90° around its own axis to
//     switch flow paths. This is the ONLY element above the bench
//     surface — everything else lies in the bench plane.
//
//   Operator-confirmed dimensions (2026-05-15) — both measurements are
//   FLAT-TO-FLAT across the hex nut (NOT circular diameters):
//     Inner-face gap between the two inner fittings:  37 mm
//     Left  inner fitting hex flat-to-flat:           31.5 mm
//     Right inner fitting hex flat-to-flat:           29.25 mm
//
//   The saddles grip the inner hex nuts themselves (no bare-pipe band
//   between them, unlike the flow meter). Each saddle's bore is a
//   hexagonal prism sized to its specific fitting — don't average the
//   ftf values and don't use a circular bore (which would grip only
//   the hex's six vertices and let the fitting rotate under load).
//
// === Hardware (same pattern as flow meter v2) ===
//
//   4× M3×30 mm SHCS — clearance through the BASE (head countersunk
//        into the base bottom), threaded UP into a heat-set insert
//        pressed into each CAP.
//   4× M3 brass heat-set inserts (5 mm OD × 5 mm depth) — installed
//        into the CAPS from each cap's mating (bottom) face before
//        assembly, with a soldering iron, while the cap sits inverted
//        on the bench (its outer top face down — same orientation as
//        printing).
//
//   Per cap: 2 bolts straddling the pipe channel in Y, at the saddle's
//   X centre. Total 4 bolts = 2 caps × 2 bolts.
//
//   ### Bolt length budget (M3×30, recomputed for this part)
//
//   Per-saddle saddle_bottom_h is `wall_t + max(hex_apothem_left,
//   hex_apothem_right)` — both saddles share `pipe_center_z`, so the
//   smaller-bore saddle just has more wall under its bore. The apothem
//   (centre-to-flat) is half the flat-to-flat measurement plus slop,
//   so numerically it matches what the v1 circular bore used. At
//   defaults (slop=0.2, wall_t=3, hex_ftf_left=31.5):
//
//     3.2 mm  head countersunk into base bottom (m3_head_depth)
//     4.8 mm  base material above the head (base_t − m3_head_depth)
//    18.95 mm saddle_bottom (wall_t + max_apothem)
//     5.0 mm  insert depth in cap (m3_insert_h)
//    ─────
//    31.95 mm total path; under-head bolt length = 28.75 mm, so an
//             M3×30 SHCS gives ~1.25 mm slack under the insert floor
//             and full thread engagement in the brass insert.
//             (Same path length as v1's circular bore — apothem and
//             old radius coincide numerically; only the bore profile
//             changed.)
//
// === Install orientation ===
//
//   install +X = along the valve's inline axis (the QD pair); pick the
//                end the plumbing prefers — the saddles are sized
//                asymmetrically so the part is NOT mirror-symmetric.
//   install +Y = across the bench, perpendicular to inline; the side
//                outlet exits along ±Y past the base edge.
//   install +Z = up (away from the bench top); bench surface at z=0.
//                The T-handle is the ONLY +Z element above the part.
//
//   The flat base bottom (z=0) sits on the bench. The valve fittings
//   sit captured in the two saddles at pipe_center_z; the T-handle
//   rises above the valve body in the middle gap between saddles. The
//   side outlet exits laterally in ±Y at pipe_center_z; it stays well
//   above the base top (base_t = 8 mm vs pipe_center_z ≈ 27 mm) so it
//   hangs free past whichever Y edge it points at.
//
//   The asymmetric saddles fix the valve's inline orientation: the
//   31.5 mm-ftf hex goes in the -X saddle (left), the 29.25 mm-ftf hex
//   goes in the +X saddle (right). Cap-left and cap-right STLs are
//   distinct (different bore ftf).
//
// === Print orientation ===
//
//   Default `part = "assembly"` renders all three pieces in their
//   installed positions for the live preview / catalog thumbnail. For
//   STL export the operator passes `-D 'part="base"'` (one print),
//   `-D 'part="cap_left"'` (one print), or `-D 'part="cap_right"'`
//   (one print). The two caps are NOT interchangeable.
//
//     - Base: flat-bottom-down on the build plate (z=0 face on the
//       bed). The two saddles' inner curves overhang into their pipe
//       channels; below each bore equator every perimeter layer is
//       steeper than 45° from horizontal, so no supports are needed.
//       The base bottom carries the 4× SHCS counterbores (5.8 mm Ø ×
//       3.2 mm deep) — short bridges over the first 3.2 mm of layers,
//       fine without supports.
//
//     - Cap (left or right): flat-top-down. The cap's outer top face
//       becomes the bed face; the inner hex roof (the saddle's upper
//       half: top horizontal flat + two slanted flats) prints as
//       three planar surfaces, with the slanted flats at 30° from
//       horizontal — well below the 45° overhang threshold, no
//       supports needed. The handle-clearance cut on the inboard face
//       is a shallow cylindrical scoop (≤1.5 mm deep at the
//       centerline at defaults) and prints as a mild concave
//       perimeter — no overhang issues. The heat-set insert pockets
//       open from the cap's mating face, which is the +Z face in the
//       printed orientation — clean blind holes, no bridging.
//
//   Material: PETG (default — water-adjacent like the flow meter) or
//   ASA. PLA acceptable for a dry indoor bench but note the valve
//   sees splash from black-tank flushing.
//
// === Hex bore orientation ===
//
//   Each saddle's bore is a hexagonal prism with axis along the
//   inline (X) direction. The two saddles are oriented DIFFERENTLY
//   so that — viewed end-on along the pipe axis — the right saddle's
//   hex POINTS land where the left saddle's hex FLATS are (a 30°
//   per-saddle clocking offset).
//
//   - LEFT saddle (sx < 0): FLATS-HORIZONTAL. One flat at the top
//     (+Z extreme), one flat at the bottom (−Z extreme), the two
//     equator vertices at ±Y on the saddle/cap parting plane
//     (z = pipe_center_z).
//   - RIGHT saddle (sx > 0): POINTS-VERTICAL. One vertex at the top
//     (+Z extreme), one vertex at the bottom (−Z extreme), the two
//     equator vertices (and the four slanted flats) sit closer to
//     ±Y but offset 30° from the left saddle's equator vertices.
//
//   This asymmetry matches the physical valve, which presents its
//   two fittings with their hex flats clocked 30° apart. Caps share
//   the bore module (`_pipe_channel_cut`), so cap-left and cap-right
//   inherit the matching orientation automatically.
//
//   OpenSCAD's `cylinder($fn=6)` puts a vertex at local +X by default,
//   which (after `rotate([0, 90, 0])` to put the hex axis on global X)
//   lands a vertex at global −Z. We pre-rotate the hex by 30° around
//   its own axis (a local `rotate([0, 0, hex_rot_for(sx)])` before
//   the cylinder) to spin the vertices onto the equator — that's the
//   left saddle's flats-top-and-bottom orientation. For the right
//   saddle we use 60° (= 30° + 30°), which lands the vertices top
//   and bottom. The render harness shows this visually — if the
//   left flats ever go vertical, or the two saddles ever match, the
//   per-saddle rotation has been broken.
//
// === Slop (slip-fit) ===
//
//   `slop` is a per-flat radial pad on the hex apothem (centre-to-
//   flat distance). Effective ftf = hex_ftf + 2·slop. Default 0.2 mm
//   gives a 31.9 mm effective ftf for the 31.5 mm hex and a 29.65 mm
//   effective ftf for the 29.25 mm hex. First-print feedback will
//   tune from here.
//
// === Handle clearance ===
//
//   The T-handle sits above the valve body in the middle 37 mm gap
//   between saddles. Its swept volume (~40 mm tall × ~20 mm radial
//   from the handle pivot) must NOT intersect either cap.
//
//   The mount carves a vertical exclusion cylinder centered on the
//   valve's vertical axis (origin in XY) at z ∈ [pipe_center_z +
//   handle_pivot_above_pipe, pipe_center_z + handle_pivot_above_pipe
//   + handle_excl_h] with radius handle_excl_r. At defaults this
//   removes a thin lens-shaped scoop (~1.5 mm deep at y=0, fading to
//   zero at y ≈ ±7.6 mm) from the inboard top of each cap. The cut
//   leaves cap material on every side of the bolt locations, so cap
//   strength near the inserts is unaffected.
//
//   If the operator's actual handle is wider, raise `handle_excl_r` —
//   the cut deepens but stays well clear of the bolt insert pockets
//   (which sit at x=±saddle_center_x, y=±bolt_y_offset, well outside
//   the exclusion radius at defaults). The invariants harness flags
//   any combination that would sever the cap.
//
// === Side-outlet clearance ===
//
//   The 3rd valve fitting exits in ±Y at z = pipe_center_z ≈ 27 mm,
//   well above the base top (z = base_t = 8 mm). With base_d = 60 mm
//   the +Y / −Y edges of the base sit at y = ±30 mm — 5.5 mm past
//   saddle_y_half (24.5 mm). The outlet (which extends radially out
//   from y=0 well past ±30 mm) hangs cleanly into open air past the
//   base edge. No notch needed — the outlet axis runs above the base
//   top, never through it.
//
// === Base footprint (v2) ===
//
//   v1 shipped with base_w=70, base_d=50 — only ~1.5 mm and ~0.5 mm
//   past the saddle outer faces, so the base was visually "missing"
//   in the assembly view. v2 grows to base_w=90, base_d=60 to match
//   the sibling flow meter mount's footprint, giving ~11 mm overhang
//   in X past each saddle outer face and ~5.5 mm overhang in Y past
//   each saddle/cap side. Enough for desk stability without wasting
//   filament.
//
// === Hex-vertex / insert-pocket clearance ===
//
//   The hex bore's equator vertices extend further from the pipe
//   axis than the old circular bore's wall did: for ftf=31.5 mm and
//   slop=0.2 mm, the apothem stays at 15.95 mm (same as v1's radius)
//   but the vertex sits at apothem / cos(30°) ≈ 18.42 mm. The
//   insert pocket's inboard edge is at y = bolt_y_offset − m3_insert_d
//   /2 = 17.5 mm. The vertex therefore reaches 0.92 mm past the
//   insert-pocket inboard edge, in a thin triangular wedge confined to
//   the bottom ~1.6 mm of the 5 mm-deep insert pocket (the bore
//   slanted flat returns inboard of the pocket above z ≈ equator + 1.6
//   mm). The upper ~3.4 mm of each insert is fully enclosed by plastic;
//   first-print review will determine whether the lower wedge is
//   acceptable or whether bolt_y_offset needs to bump out for v3. The
//   invariants harness flags this overlap with a soft tolerance — see
//   `blu_black_tank_valve_mount.invariants.py`.

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Which piece to render -----
part = "assembly";  // @param enum choices=assembly|base|cap_left|cap_right group=part label="Which piece to render"

// ----- Valve dimensions -----
hex_ftf_left  = 31.5;   // @param number min=15 max=60 step=0.25 unit=mm group=valve label="Left inner fitting hex flat-to-flat"
hex_ftf_right = 29.25;  // @param number min=15 max=60 step=0.25 unit=mm group=valve label="Right inner fitting hex flat-to-flat"
fitting_gap   = 37;     // @param number min=20 max=120 step=0.5 unit=mm group=valve label="Inner-face gap between fittings"

// ----- Fit -----
slop     = 0.2;  // @param number min=0 max=1   step=0.05 unit=mm group=fit label="Hex slip clearance (per-flat radial pad on apothem)"
saddle_w = 15;   // @param number min=5 max=30  step=0.5  unit=mm group=fit label="Saddle width along inline axis (X)"
wall_t   = 3;    // @param number min=2 max=8   step=0.5  unit=mm group=fit label="Saddle wall thickness around pipe"

// ----- Base -----
base_w       = 90;   // @param number min=40 max=160 step=0.5 unit=mm group=base label="Base width along inline axis (X)"
base_d       = 60;   // @param number min=30 max=120 step=0.5 unit=mm group=base label="Base depth across inline (Y)"
base_t       = 8;    // @param number min=3 max=15  step=0.5 unit=mm group=base label="Base plate thickness (Z)"
edge_round_r = 1.5;  // @param number min=0 max=5   step=0.25 unit=mm group=base label="Outer edge rounding"

// ----- Hardware (M3 SHCS + heat-set insert) -----
m3_clearance_d = 3.5;  // @param number min=3.0 max=5   step=0.1 unit=mm group=hardware label="M3 clearance hole (base pass-through)"
m3_head_d      = 5.8;  // @param number min=4.5 max=8   step=0.1 unit=mm group=hardware label="M3 SHCS head diameter (counterbore)"
m3_head_depth  = 3.2;  // @param number min=2.5 max=6   step=0.1 unit=mm group=hardware label="M3 SHCS head depth (counterbore)"
m3_insert_d    = 5;    // @param number min=4   max=7   step=0.1 unit=mm group=hardware label="M3 heat-set insert OD (cap pocket)"
m3_insert_h    = 5;    // @param number min=3   max=10  step=0.5 unit=mm group=hardware label="M3 heat-set insert depth"
bolt_y_offset  = 20;   // @param number min=15  max=30  step=0.5 unit=mm group=hardware label="Bolt centerline distance from pipe axis (Y)"

// ----- Handle clearance -----
handle_excl_r            = 20;  // @param number min=0  max=40 step=0.5 unit=mm group=handle label="Handle swept-volume radius (from valve vertical axis)"
handle_excl_h            = 40;  // @param number min=10 max=80 step=1   unit=mm group=handle label="Handle swept-volume height (above pivot)"
handle_pivot_above_pipe  = 5;   // @param number min=0  max=30 step=0.5 unit=mm group=handle label="Handle pivot height above pipe centerline"

// @preset id="default" label="Blu black-tank flush valve (default)" part="assembly" hex_ftf_left=31.5 hex_ftf_right=29.25 fitting_gap=37 slop=0.2 saddle_w=15 wall_t=3 base_w=90 base_d=60 base_t=8 edge_round_r=1.5 m3_clearance_d=3.5 m3_head_d=5.8 m3_head_depth=3.2 m3_insert_d=5 m3_insert_h=5 bolt_y_offset=20 handle_excl_r=20 handle_excl_h=40 handle_pivot_above_pipe=5

// === Derived ===

// Hex apothem = half flat-to-flat (centre-to-flat distance) + slop.
// Numerically the apothem coincides with v1's circular radius, so all
// downstream stack math (pipe_center_z, saddle_bottom_h, bolt path)
// is unchanged from v1.
hex_apothem_left  = hex_ftf_left  / 2 + slop;  // 15.95 at defaults
hex_apothem_right = hex_ftf_right / 2 + slop;  // 14.825 at defaults
max_apothem       = max(hex_apothem_left, hex_apothem_right);

// Circumradius (centre-to-vertex) = apothem / cos(30°). The equator
// vertices sit at y = ±circumradius on the saddle/cap parting plane.
hex_circumradius_left  = hex_apothem_left  / cos(30);  // 18.42 at defaults
hex_circumradius_right = hex_apothem_right / cos(30);  // 17.12 at defaults

// Both saddles share the same pipe-axis Z so the valve fittings line
// up coaxially. Use the larger apothem to set the height — the
// smaller-bore saddle ends up with a little extra wall below its
// channel.
pipe_center_z = base_t + wall_t + max_apothem;  // 26.95 at defaults

// Saddle X centres land at half the fitting gap + half a saddle width
// outboard of origin: the saddle inboard faces are then exactly
// fitting_gap apart, which is what seats the two valve fittings.
saddle_center_x = fitting_gap / 2 + saddle_w / 2;  // 26 at defaults

// Saddle bottom (integral to base) and cap heights. Cap is uniform
// across left/right — the bore difference shows up only as different
// material above the smaller bore's channel.
saddle_bottom_h = pipe_center_z - base_t;  // 18.95 at defaults
cap_h           = wall_t + max_apothem;    // 18.95 at defaults

// Y extent: cover the pipe plus an insert-radius+margin around each
// bolt. Same formula as v2.
saddle_y_half = bolt_y_offset + m3_insert_d / 2 + 2;  // 24.5 at defaults
saddle_y      = 2 * saddle_y_half;                    // 49 at defaults

// Handle swept-volume cylinder, centered on the valve vertical axis.
handle_excl_z_start = pipe_center_z + handle_pivot_above_pipe;       // 31.95
handle_excl_z_end   = handle_excl_z_start + handle_excl_h;           // 71.95

arch_top_z = base_t + saddle_bottom_h + cap_h;  // 45.9 at defaults

// PRINT_ANCHOR_BBOX (assembly view).
PRINT_ANCHOR_BBOX = [base_w, base_d, arch_top_z];

// sx = +1 → right saddle (29.25 mm ftf hex); sx = −1 → left (31.5 mm
// ftf hex). Returns the hex apothem; the cylinder($fn=6) call uses
// apothem / cos(30°) as its circumradius parameter.
function hex_apothem_for(sx) = (sx > 0) ? hex_apothem_right
                                        : hex_apothem_left;

// Per-saddle local-Z pre-rotation (degrees). Left saddle uses 30°
// (flats top/bottom); right saddle uses 60° (= 30° + 30°), which
// clocks its hex by an extra 30° so its POINTS land top/bottom,
// 30° offset from the left's flats.
function hex_rot_for(sx) = (sx > 0) ? 60 : 30;

// === Geometry — base + integral saddle bottoms ===

module _base_plate() {
    translate([0, 0, base_t / 2])
        cuboid([base_w, base_d, base_t],
               rounding = edge_round_r,
               edges    = "ALL",
               except   = BOTTOM);
}

module _saddle_bottom(sx) {
    cx = sx * saddle_center_x;
    translate([cx, 0, base_t + saddle_bottom_h / 2])
        cuboid([saddle_w, saddle_y, saddle_bottom_h],
               rounding = edge_round_r,
               edges    = "Z");
}

// Pipe-channel cut for ONE saddle. Each saddle has its own hex bore
// apothem AND its own clocking, so cuts are separate hex prisms
// confined to each saddle's X window. The per-saddle pre-rotation
// (30° left, 60° right — see hex_rot_for) around the hex's own
// (local Z) axis spins the default vertex-at-+X into the desired
// orientation, which (after the outer rotate([0, 90, 0]) puts the
// hex axis on global X) lands flats top/bottom for the left saddle
// and POINTS top/bottom for the right saddle. cos(30°) maps apothem
// to the cylinder()-style circumradius.
module _pipe_channel_cut(sx) {
    apothem      = hex_apothem_for(sx);
    circumradius = apothem / cos(30);
    hex_rot      = hex_rot_for(sx);
    cx           = sx * saddle_center_x;
    eps          = 0.5;
    length       = saddle_w + 2 * eps;
    translate([cx - length / 2, 0, pipe_center_z])
        rotate([0, 90, 0])
            rotate([0, 0, hex_rot])
                cylinder(h = length, r = circumradius, $fn = 6);
}

// Debossed "L" / "R" letter on each ±Y face of a saddle or cap,
// centered horizontally on the saddle's X centre and vertically on
// `z_center`. Subtracted from the host solid (base or cap) so the
// printed pair is visually self-labelling no matter which side faces
// the operator: the left half of the base + cap_left both show "L";
// the right half + cap_right both show "R". The font is left unset
// so openscad picks the host's default; 0.5 mm deboss into a 19 mm-
// thick wall is cosmetic only — no impact on the bolt anchorage or
// bore geometry.
//
// rotate([90, 0, 0]) stands the 2D text up in the XZ plane and
// extrudes it in −Y; mirror([0, 1, 0]) flips that copy to the -Y face
// while keeping the letter forward-reading from each viewing side.
module _lr_marker(sx, z_center) {
    letter  = (sx > 0) ? "R" : "L";
    cx      = sx * saddle_center_x;
    deboss  = 0.5;
    char_h  = 6;
    eps     = 0.01;
    for (sy = [-1, +1]) {
        mirror([0, (sy < 0) ? 1 : 0, 0])
            translate([cx, saddle_y_half + eps, z_center])
                rotate([90, 0, 0])
                    linear_extrude(height = deboss + eps)
                        text(letter, size = char_h,
                             halign = "center", valign = "center");
    }
}

module _base_bolt_clearance(sx, sy) {
    cx  = sx * saddle_center_x;
    cy  = sy * bolt_y_offset;
    eps = 0.1;
    // Counterbore at base bottom for the M3 SHCS head.
    translate([cx, cy, -eps])
        cylinder(h = m3_head_depth + eps, d = m3_head_d);
    // Clearance shaft from just above the counterbore up through the
    // saddle_bottom to its top face (= cap mating plane).
    shaft_bot_z = m3_head_depth - eps;
    shaft_top_z = base_t + saddle_bottom_h + eps;
    translate([cx, cy, shaft_bot_z])
        cylinder(h = shaft_top_z - shaft_bot_z, d = m3_clearance_d);
}

module base_part() {
    base_marker_z = base_t + saddle_bottom_h / 2;  // mid saddle-bottom
    difference() {
        union() {
            _base_plate();
            _saddle_bottom(-1);
            _saddle_bottom(+1);
        }
        _pipe_channel_cut(-1);
        _pipe_channel_cut(+1);
        for (sx = [-1, +1])
            for (sy = [-1, +1])
                _base_bolt_clearance(sx, sy);
        for (sx = [-1, +1])
            _lr_marker(sx, base_marker_z);
    }
}

// === Geometry — cap (×2, asymmetric STLs) ===

module _cap_geom(sx) {
    cx             = sx * saddle_center_x;
    cap_bottom_z   = base_t + saddle_bottom_h;
    cap_marker_z   = cap_bottom_z + cap_h / 2;
    difference() {
        translate([cx, 0, cap_bottom_z + cap_h / 2])
            cuboid([saddle_w, saddle_y, cap_h],
                   rounding = edge_round_r,
                   edges    = "Z");
        _pipe_channel_cut(sx);
        for (sy = [-1, +1])
            _cap_insert_pocket(sx, sy);
        _handle_exclusion_cut();
        _lr_marker(sx, cap_marker_z);
    }
}

module _cap_insert_pocket(sx, sy) {
    cx           = sx * saddle_center_x;
    cy           = sy * bolt_y_offset;
    eps          = 0.2;
    cap_bottom_z = base_t + saddle_bottom_h;
    translate([cx, cy, cap_bottom_z - eps])
        cylinder(h = m3_insert_h + eps, d = m3_insert_d);
}

// Vertical exclusion cylinder centered on the valve vertical axis at
// (0,0). Carves any cap material the T-handle's swept volume passes
// through. The exclusion z-range starts at handle_excl_z_start (above
// the valve body) and extends handle_excl_h upward. At defaults the
// cylinder reaches r=20 mm; the cap inboard faces sit at x=±18.5 mm so
// a thin lens of material is removed from each cap inboard top — the
// outboard ends (where the insert pockets live) are untouched.
module _handle_exclusion_cut() {
    if (handle_excl_r > 0 && handle_excl_h > 0)
        translate([0, 0, handle_excl_z_start])
            cylinder(h = handle_excl_h, r = handle_excl_r);
}

module cap_part_in_place(sx) {
    _cap_geom(sx);
}

// Standalone cap for STL export. Translated to the origin and flipped
// flat-top-down so the smooth outer face sits on the build plate.
module cap_for_print(sx) {
    cap_bottom_z = base_t + saddle_bottom_h;
    cap_top_z    = cap_bottom_z + cap_h;
    translate([0, 0, cap_top_z])
        rotate([180, 0, 0])
            translate([-sx * saddle_center_x, 0, 0])
                _cap_geom(sx);
}

// === Assembly + part selection ===

module assembly() {
    base_part();
    cap_part_in_place(-1);
    cap_part_in_place(+1);
}

if (part == "base") {
    base_part();
} else if (part == "cap_left") {
    cap_for_print(-1);
} else if (part == "cap_right") {
    cap_for_print(+1);
} else {
    assembly();
}
