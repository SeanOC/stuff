// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Captive bench-top mount for a Blu Technology digital water flow
// meter (st-jtn). Free-standing — sits on a bench with a wide flat
// base, no fasteners into a surface. The meter is held by two split-
// saddle pairs that clamp the 18 mm bare-pipe bands at each end of
// its 80 mm body; the middle ~44 mm of the pipe (where the off-
// center LCD display saddle lives) hangs in a clear gap between the
// two saddles, so the operator can lift the translucent lens cover
// off without unmounting the meter.
//
// === Meter being mounted (Blu Technology flow meter) ===
//
//   - Pipe section diameter:     27 mm
//   - Pipe section length (end-to-end between QD fittings):  80 mm
//   - Bare pipe before the display-saddle shoulder begins:   18 mm
//     from each end — middle ~44 mm carries the display saddle
//   - Quick-disconnect fittings (one female socket, one male plug)
//     extend past each end of the 80 mm pipe section; this mount
//     stops at the pipe-section ends and leaves the fittings free
//     so hoses can dangle off the bench.
//
// === Hardware (v2 — inverted from v1, bottom-entry bolts) ===
//
//   4× M3×30 mm SHCS (socket-head cap screws) — clearance through the
//        BASE (head countersunk into the base bottom), threaded UP into
//        a heat-set insert pressed into each CAP.
//   4× M3 brass heat-set inserts (5 mm OD × 5 mm depth) — installed
//        into the CAPS from the cap's mating (bottom) face before
//        assembly. Use a soldering iron from the cap's mating side
//        while the cap sits inverted on the bench (its outer top face
//        down, mating face up — the same orientation as printing).
//
//   Per cap: 2 bolts straddling the pipe channel in Y (one at
//   +bolt_y_offset, one at -bolt_y_offset) at the saddle's X centre.
//   Total 4 bolts = 2 caps × 2 bolts.
//
//   Bolt centerlines sit `bolt_y_offset` (default 20 mm) outboard of
//   the pipe-channel axis — that's pipe_radius + wall_t + a small
//   margin so the bolt thread doesn't graze the pipe channel.
//
//   ### Bolt length budget (M3×30)
//
//   The bolt has to bridge the full plastic stack from the base-bottom
//   counterbore up to the insert in the cap:
//     3.2 mm  head countersunk into base bottom (m3_head_depth)
//     4.8 mm  base material above the head (base_t − m3_head_depth)
//    16.7 mm  saddle_bottom (wall_t + pipe_channel_r at defaults)
//     5.0 mm  insert depth in cap (m3_insert_h)
//    ──────
//    29.7 mm  total path; M3×30 gives ~0.3 mm under the insert floor
//             and full thread engagement in the brass insert.
//
//   Why this differs from v1's docstring: the v1 (and original st-jtn
//   bead) spec named M3×10, but the bolt path crossed 16.7 mm of cap
//   material before reaching the insert at the saddle_bottom top —
//   M3×10 fell ~3 mm short of even touching the insert. v2 corrects
//   the recommendation; operators who installed v1 with longer bolts
//   already have the right hardware.
//
// === Install orientation ===
//
//   install +X = along the pipe axis (flow direction; pick the end
//                the meter prefers — symmetric mount, either way)
//   install +Y = lateral (across the bench, perpendicular to flow)
//   install +Z = up (away from the bench top); bench surface at z=0
//
//   The flat 80×60 base bottom (z=0) sits on the bench. The pipe
//   sits captured in the saddles at pipe_center_z; the LCD display
//   faces +Z (up) when the operator aligns the meter so the display-
//   saddle's tall side is in +Z. The bare pipe is rotationally
//   symmetric, so the operator picks the LCD-up orientation at
//   install time — the mount doesn't constrain it.
//
//   The operator can also rotate the meter around the pipe axis (X)
//   to tilt the LCD forward toward the viewer; see "Display tilt
//   relief" below. The chamfered cap tops give clearance for tilts up
//   to ±`display_relief_angle` from vertical (default 35°).
//
//   ### Bolt entry (v2 — inverted vs v1)
//
//   M3 SHCS enter from BELOW the base. The 4 bolt heads sit recessed
//   into counterbores on the base BOTTOM (5.8 × 3.2 mm) so they don't
//   project past the bench-contact face and rock the part. Bolts
//   pass UP through the base, through the saddle_bottom material, and
//   thread into the heat-set inserts pressed into the caps. To remove
//   a cap, the operator flips the mount on its side and backs the
//   bolts out from below — the LCD bezel never blocks the driver.
//
// === Print orientation ===
//
//   Default `part = "assembly"` renders both pieces in their installed
//   positions, for the live preview / catalog thumbnail. For STL
//   export the operator passes `-D 'part="base"'` (one print) or
//   `-D 'part="cap"'` (one print run twice — the two caps are
//   identical):
//
//     - Base: flat-bottom-down on the build plate (z=0 face on the
//       bed). The saddle bottoms' inner curves overhang into the pipe
//       channel; below the equator of a 27 mm pipe, every layer's
//       perimeter is steeper than 45° from horizontal so no supports
//       are needed. The base bottom now also carries the 4× SHCS
//       counterbores (5.8 mm Ø × 3.2 mm deep) — they print as short
//       bridges on the very first 3.2 mm of layers, fine without
//       supports (bridge span = m3_head_d = 5.8 mm).
//
//     - Cap: flat-top-down. The cap's outer top face becomes the bed
//       face, and the inner cylindrical roof (the saddle's upper half)
//       prints as concentric perimeters with no overhang because every
//       layer is again ≤45° steep when measured from the build plate.
//       The cap's inboard-face chamfer (display tilt relief) is at the
//       bottom of the printed orientation — it shows up as a 35°-from-
//       vertical inset on the inboard edge that grows inward as layers
//       progress (a mild overhang well within PETG/ASA tolerance).
//       The heat-set insert pockets open from the cap's mating face,
//       which is the +Z face in the printed orientation — clean blind
//       holes, no bridging.
//
//   Material: PETG (default — water-adjacent, UV-tolerant, easy to
//   print). ASA also fine. PLA acceptable for a dry indoor bench but
//   note the meter sees splash.
//
// === Slop (slip-fit) ===
//
//   `slop` is a per-radius pad on the pipe channel diameter:
//   pipe_channel_d = pipe_dia + 2·slop. Default 0.2 mm gives a 27.4 mm
//   bore on the 27 mm pipe. First-print feedback will tell whether to
//   loosen (rocks side-to-side: increase slop) or tighten (cap won't
//   close, threads strip: decrease slop). Per the bead: don't tune
//   until first print.
//
// === Geometry ===
//
//   - Base: 80 × 60 × 8 mm; corners rounded for finger safety. Four
//     M3 bolt through-holes at the saddle X-centres (clearance
//     m3_clearance_d through the full base + saddle_bottom stack),
//     each with a 5.8 × 3.2 mm counterbore opening on the base BOTTOM
//     face for the SHCS head.
//
//   - Saddle bottom (×2, integral to base): a 15 mm-wide block sitting
//     on the base top at the two bare-pipe X positions. Each block
//     has a half-cylinder cutout for the pipe; the saddle wall
//     thickness below the pipe is `wall_t`. Block X-centres at
//     ±saddle_center_x (≈ ±30 mm) so the two 18 mm bare bands of the
//     meter pipe seat in the saddles. The bolt clearance shafts pass
//     vertically through this block at ±bolt_y_offset.
//
//   - Cap (×2, separate STL): the upper half of each saddle plus a
//     `wall_t` ceiling. Mates flat against the base's saddle top at
//     z = pipe_center_z. Each cap carries 2 heat-set insert pockets
//     (5 mm Ø × 5 mm deep) opening from the cap's mating (bottom)
//     face, aligned with the bolt clearance holes coming up through
//     the base. The cap's inboard top edge is chamfered (see Display
//     tilt relief).
//
//   - Display tilt relief: each cap's inboard top edge (the edge
//     facing the display gap) is chamfered at `display_relief_angle`
//     from vertical (default 35°). The chamfer depth on the inboard
//     face is capped at `cap_h − m3_insert_h − 1 mm` (≈10.7 mm at
//     defaults) so the cut never reaches the insert pocket below.
//     This lets the operator rotate the meter around the pipe axis at
//     install — tilting the LCD forward toward the viewer by up to
//     ±display_relief_angle without the display body striking the cap.
//
//   - Display gap: 80 mm pipe − 2·(saddle X-centre ± half saddle width)
//     ≈ 45 mm clear span between the inner faces of the two saddles.
//     (The bead's ≈44 mm spec — same idea, rounded to ±1 mm.)
//
// === Outputs ===
//
//   Default `part = "assembly"` is the catalog / thumbnail view: base
//   plus both caps in place on the pipe. PRINT_ANCHOR_BBOX matches
//   this view. Per-part STL export uses the `part` enum:
//     openscad -D 'part="base"' -o base.stl …
//     openscad -D 'part="cap"'  -o cap.stl  …

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Which piece(s) to render -----
part = "assembly";  // @param enum choices=assembly|base|cap group=part label="Which piece to render"

// ----- Meter dimensions -----
pipe_dia       = 27;   // @param number min=15 max=60  step=0.5 unit=mm group=meter label="Meter pipe diameter"
pipe_len       = 80;   // @param number min=40 max=200 step=0.5 unit=mm group=meter label="Meter pipe length (between QD fittings)"
bare_band_w    = 18;   // @param number min=10 max=40  step=0.5 unit=mm group=meter label="Bare-pipe length at each end (before display saddle starts)"

// ----- Fit -----
slop           = 0.2;  // @param number min=0 max=1   step=0.05 unit=mm group=fit label="Pipe channel slip clearance (radial pad on diameter)"
saddle_w       = 15;   // @param number min=5 max=30  step=0.5 unit=mm group=fit label="Saddle width along pipe (X)"
wall_t         = 3;    // @param number min=2 max=8   step=0.5 unit=mm group=fit label="Saddle wall thickness around pipe"

// ----- Base -----
base_w         = 80;   // @param number min=40 max=160 step=0.5 unit=mm group=base label="Base width along pipe (X)"
base_d         = 60;   // @param number min=30 max=120 step=0.5 unit=mm group=base label="Base depth across pipe (Y)"
base_t         = 8;    // @param number min=3 max=15  step=0.5 unit=mm group=base label="Base plate thickness (Z)"
edge_round_r   = 1.5;  // @param number min=0 max=5   step=0.25 unit=mm group=base label="Outer edge rounding"

// ----- Hardware (M3 SHCS + heat-set insert) -----
m3_clearance_d = 3.5;  // @param number min=3.0 max=5   step=0.1 unit=mm group=hardware label="M3 clearance hole (cap pass-through)"
m3_head_d      = 5.8;  // @param number min=4.5 max=8   step=0.1 unit=mm group=hardware label="M3 SHCS head diameter (countersink)"
m3_head_depth  = 3.2;  // @param number min=2.5 max=6   step=0.1 unit=mm group=hardware label="M3 SHCS head depth (countersink)"
m3_insert_d    = 5;    // @param number min=4   max=7   step=0.1 unit=mm group=hardware label="M3 heat-set insert OD (cap pocket)"
m3_insert_h    = 5;    // @param number min=3   max=10  step=0.5 unit=mm group=hardware label="M3 heat-set insert depth"
bolt_y_offset  = 20;   // @param number min=15  max=30  step=0.5 unit=mm group=hardware label="Bolt centerline distance from pipe axis (Y)"

// ----- Display tilt relief -----
display_relief_angle = 35; // @param number min=0 max=50 step=5 unit=deg group=fit label="Cap inboard-edge chamfer angle from vertical (allows meter tilt around pipe axis)"

// @preset id="default" label="Blu flow meter 80mm × 27mm dia (default)" part="assembly" pipe_dia=27 pipe_len=80 bare_band_w=18 slop=0.2 saddle_w=15 wall_t=3 base_w=80 base_d=60 base_t=8 edge_round_r=1.5 m3_clearance_d=3.5 m3_head_d=5.8 m3_head_depth=3.2 m3_insert_d=5 m3_insert_h=5 bolt_y_offset=20 display_relief_angle=35

// === Derived ===

pipe_channel_r = pipe_dia / 2 + slop;     // 13.7 at defaults
pipe_center_z  = base_t + wall_t + pipe_channel_r; // 8 + 3 + 13.7 = 24.7

// Two saddles each clamp one bare-pipe band. Their X centres land in
// the middle of the bare band at each end of the pipe:
//   from a pipe end: bare_band starts at 0 and runs `bare_band_w`;
//   saddle centre = bare_band_w / 2 ≈ 9 mm from the end (default).
// Pipe centred on the base (base_w == pipe_len at defaults) → saddle
// centres at ±(pipe_len/2 − bare_band_w/2) ≈ ±31 mm.
saddle_center_x = pipe_len / 2 - bare_band_w / 2;

// Display gap = clear span between the two saddles' inner faces.
display_gap = 2 * saddle_center_x - saddle_w; // ≈ 47 mm at defaults

// Saddle / cap Y extent. Needs to cover the pipe + bolt anchorages on
// either side. Bolt at ±bolt_y_offset; allow insert-radius + 2 mm of
// margin around the insert (so the cap face stays solid past the bolt
// head).
saddle_y_half = bolt_y_offset + m3_insert_d / 2 + 2;  // 20 + 2.5 + 2 = 24.5
saddle_y      = 2 * saddle_y_half;                    // 49 at defaults

// Heights of the saddle bottom (integral to base, fills up to pipe
// equator) and the cap (mirror — pipe equator up to cap top).
saddle_bottom_h = wall_t + pipe_channel_r;  // 16.7 at defaults
cap_h           = wall_t + pipe_channel_r;  // 16.7 at defaults

// Cap top z = base top + saddle_bottom_h + cap_h = base_t + 2·(wall_t
// + pipe_channel_r) — the "≈33 mm arch above base top" from the bead.
arch_top_z = base_t + saddle_bottom_h + cap_h;  // 41.4 at defaults

// Display tilt relief chamfer. dz on the inboard face is clamped to
// leave `chamfer_clearance_t` of wall between the chamfer floor and
// the insert pocket top above it; dx along the cap top is dz·tan(θ).
// At defaults (cap_h=16.7, m3_insert_h=5, angle=35°): dz=10.7, dx=7.5.
chamfer_clearance_t = 1;  // mm wall left between chamfer and insert pocket
chamfer_dz          = max(0, cap_h - m3_insert_h - chamfer_clearance_t);
chamfer_dx          = chamfer_dz * tan(display_relief_angle);

// PRINT_ANCHOR_BBOX (assembly view): base footprint × arch_top_z.
PRINT_ANCHOR_BBOX = [base_w, base_d, arch_top_z];

// === Geometry — base + integral saddle bottoms ===

module _base_plate() {
    // Base block, top rim + vertical corners rounded for finger
    // safety; bottom rim left sharp so the plate sits flush against
    // the bench (any roundover there would rock the part).
    translate([0, 0, base_t / 2])
        cuboid([base_w, base_d, base_t],
               rounding = edge_round_r,
               edges    = "ALL",
               except   = BOTTOM);
}

// One saddle bottom block (integral to base, half-cylinder pipe cutout
// in the top half). sx = ±1 selects which end of the pipe.
module _saddle_bottom(sx) {
    cx = sx * saddle_center_x;
    translate([cx, 0, base_t + saddle_bottom_h / 2])
        cuboid([saddle_w, saddle_y, saddle_bottom_h],
               rounding = edge_round_r,
               edges    = "Z");
}

// Pipe-channel cut: a single cylinder along +X, axis at z =
// pipe_center_z, length = pipe_len + slack to overshoot the saddles
// at both ends so the cut doesn't leave a thin coplanar wall.
module _pipe_channel_cut() {
    eps = 0.5;  // overshoot past saddle outer faces
    translate([-pipe_len / 2 - eps, 0, pipe_center_z])
        rotate([0, 90, 0])
            cylinder(h = pipe_len + 2 * eps, r = pipe_channel_r);
}

// Bolt clearance through the base + saddle_bottom: a counterbore for
// the SHCS head opens on the base BOTTOM face (z=0) and a clearance
// shaft runs from above the counterbore up to the cap mating face
// (top of saddle_bottom). The bolt enters from below and threads into
// the insert in the cap above. A small overshoot at both ends kills
// coplanar-face jitter at the base-bottom and cap-mating planes.
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
    difference() {
        union() {
            _base_plate();
            _saddle_bottom(+1);
            _saddle_bottom(-1);
        }
        _pipe_channel_cut();
        for (sx = [-1, +1])
            for (sy = [-1, +1])
                _base_bolt_clearance(sx, sy);
    }
}

// === Geometry — cap (×2, identical STL) ===

// One cap module, positioned at its saddle's X centre. The cap sits
// flat on the saddle's top face (z = base_t + saddle_bottom_h) and
// has the half-cylinder pipe cutout opening DOWNWARD (mirror of the
// saddle bottom's upward cut). Two heat-set insert pockets open from
// the cap's mating face; the inboard top edge is chamfered for
// display-tilt clearance.
module _cap_geom(sx) {
    cx = sx * saddle_center_x;
    cap_bottom_z = base_t + saddle_bottom_h;
    cap_top_z    = cap_bottom_z + cap_h;
    difference() {
        translate([cx, 0, cap_bottom_z + cap_h / 2])
            cuboid([saddle_w, saddle_y, cap_h],
                   rounding = edge_round_r,
                   edges    = "Z");
        // Pipe channel (same as base's, but only the upper half cuts
        // the cap since the cap material lives above pipe_center_z).
        _pipe_channel_cut();
        // Heat-set insert pockets (×2), opening from the cap mating face.
        for (sy = [-1, +1])
            _cap_insert_pocket(sx, sy);
        // Inboard top edge chamfer for meter tilt clearance.
        _cap_chamfer_cut(sx);
    }
}

// Heat-set insert pocket inside the cap. Opens from the cap's mating
// (bottom) face at z = base_t + saddle_bottom_h and goes UP into the
// cap body by m3_insert_h. After printing flat-top-down, this pocket
// is at the top of the printed cap, oriented as a clean blind hole
// for insertion of the brass insert with a soldering iron.
module _cap_insert_pocket(sx, sy) {
    cx  = sx * saddle_center_x;
    cy  = sy * bolt_y_offset;
    eps = 0.2;
    cap_bottom_z = base_t + saddle_bottom_h;
    translate([cx, cy, cap_bottom_z - eps])
        cylinder(h = m3_insert_h + eps, d = m3_insert_d);
}

// Inboard top edge chamfer: removes a triangular prism from the cap's
// top-inboard wedge so the meter can be rotated forward around the
// pipe axis at install time. dz is clamped so the chamfer never
// approaches the heat-set insert pocket below (keeps ≥1 mm of cap
// wall between the chamfer floor and the insert top).
module _cap_chamfer_cut(sx) {
    inboard_x = sx * (saddle_center_x - saddle_w / 2);
    cap_top_z = base_t + saddle_bottom_h + cap_h;
    eps       = 0.1;
    y_min     = -saddle_y / 2 - eps;
    y_max     =  saddle_y / 2 + eps;
    // Three points in the XZ cross-section of the wedge. Mirrored
    // along Y as 6 tiny spheres, hulled into a triangular prism.
    pts_xz = [
        [inboard_x - sx * eps,                       cap_top_z + eps],
        [inboard_x + sx * (chamfer_dx + eps),        cap_top_z + eps],
        [inboard_x - sx * eps,                       cap_top_z - chamfer_dz],
    ];
    hull() {
        for (y = [y_min, y_max])
            for (p = pts_xz)
                translate([p[0], y, p[1]])
                    sphere(r = 0.01, $fn = 4);
    }
}

module cap_part_in_place(sx) {
    _cap_geom(sx);
}

// Standalone cap (for STL export). Translated to z=0 with cap top
// down so it prints with the smooth outer face on the build plate —
// matches the bead's flat-top-down print orientation. Picks +X
// saddle as the canonical orientation; the -X cap is identical
// (mirror-symmetric in Y about its own centre).
module cap_for_print() {
    cap_bottom_z = base_t + saddle_bottom_h;
    cap_top_z    = cap_bottom_z + cap_h;
    // Move the +X cap to the origin, then flip top→bottom so the
    // outer top face sits on z=0.
    translate([0, 0, cap_top_z])
        rotate([180, 0, 0])
            translate([-saddle_center_x, 0, 0])
                _cap_geom(+1);
}

// === Assembly + part selection ===

module assembly() {
    base_part();
    cap_part_in_place(+1);
    cap_part_in_place(-1);
}

if (part == "base") {
    base_part();
} else if (part == "cap") {
    cap_for_print();
} else {
    assembly();
}
