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
// === Hardware ===
//
//   4× M3×10 mm SHCS (socket-head cap screws) — clearance through
//        each cap, threaded into a heat-set insert in the base.
//   4× M3 brass heat-set inserts (5 mm OD × 5 mm depth) — installed
//        into the base from the top before assembly.
//
//   Per cap: 2 bolts straddling the pipe channel in Y (one at
//   +bolt_y_offset, one at -bolt_y_offset) at the saddle's X centre.
//   Total 4 bolts = 2 caps × 2 bolts.
//
//   Bolt centerlines sit `bolt_y_offset` (default 20 mm) outboard of
//   the pipe-channel axis — that's pipe_radius + wall_t + a small
//   margin so the bolt thread doesn't graze the pipe channel.
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
//       are needed.
//
//     - Cap: flat-top-down. The cap's outer top face becomes the bed
//       face, and the inner cylindrical roof (the saddle's upper half)
//       prints as concentric perimeters with no overhang because every
//       layer is again ≤45° steep when measured from the build plate.
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
//   - Base: 80 × 60 × 8 mm; corners rounded for finger safety. Two
//     heat-set insert pockets at each saddle X-centre (4 pockets
//     total) sized for the 5×5 mm brass inserts.
//
//   - Saddle bottom (×2, integral to base): a 15 mm-wide block sitting
//     on the base top at the two bare-pipe X positions. Each block
//     has a half-cylinder cutout for the pipe; the saddle wall
//     thickness below the pipe is `wall_t`. Block X-centres at
//     ±saddle_center_x (≈ ±30 mm) so the two 18 mm bare bands of the
//     meter pipe seat in the saddles.
//
//   - Cap (×2, separate STL): the upper half of each saddle plus a
//     `wall_t` ceiling. Mates flat against the base's saddle top at
//     z = pipe_center_z. M3 bolt clearance holes + countersink for
//     the SHCS heads, aligned with the inserts in the base.
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
m3_insert_d    = 5;    // @param number min=4   max=7   step=0.1 unit=mm group=hardware label="M3 heat-set insert OD (base pocket)"
m3_insert_h    = 5;    // @param number min=3   max=10  step=0.5 unit=mm group=hardware label="M3 heat-set insert depth"
bolt_y_offset  = 20;   // @param number min=15  max=30  step=0.5 unit=mm group=hardware label="Bolt centerline distance from pipe axis (Y)"

// @preset id="default" label="Blu flow meter 80mm × 27mm dia (default)" part="assembly" pipe_dia=27 pipe_len=80 bare_band_w=18 slop=0.2 saddle_w=15 wall_t=3 base_w=80 base_d=60 base_t=8 edge_round_r=1.5 m3_clearance_d=3.5 m3_head_d=5.8 m3_head_depth=3.2 m3_insert_d=5 m3_insert_h=5 bolt_y_offset=20

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

// Heat-set insert pocket: a cylinder open at the BASE TOP face going
// downward into the base by m3_insert_h. Pocket sits inside the
// saddle's footprint (X within saddle, Y at ±bolt_y_offset).
module _insert_pocket(sx, sy) {
    // The pocket reaches `m3_insert_h` deep below the saddle's TOP
    // face (= base_top + saddle_bottom_h), so the insert sits with
    // its top flush with the saddle's top face — that's the surface
    // the cap clamps against. A small 0.2 mm overshoot below the
    // pocket bottom kills coplanar-face jitter.
    pocket_top_z = base_t + saddle_bottom_h;
    eps = 0.2;
    pocket_h = m3_insert_h + eps;
    translate([sx * saddle_center_x,
               sy * bolt_y_offset,
               pocket_top_z - m3_insert_h])
        translate([0, 0, -eps])
            cylinder(h = pocket_h, d = m3_insert_d);
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
                _insert_pocket(sx, sy);
    }
}

// === Geometry — cap (×2, identical STL) ===

// One cap module, positioned at its saddle's X centre. The cap sits
// flat on the saddle's top face (z = base_t + saddle_bottom_h) and
// has the half-cylinder pipe cutout opening DOWNWARD (mirror of the
// saddle bottom's upward cut). Plus two M3 clearance + countersink
// holes for the bolts.
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
        // Bolt holes through the cap into the base inserts.
        for (sy = [-1, +1])
            _cap_bolt_cut(sx, sy, cap_bottom_z, cap_top_z);
    }
}

// Cap bolt cut: a clearance shaft running the full cap height,
// with a countersink for the M3 SHCS head opening at the cap top.
module _cap_bolt_cut(sx, sy, cap_bottom_z, cap_top_z) {
    eps_top    = 0.1;
    eps_bot    = 0.1;
    shaft_h    = (cap_top_z - cap_bottom_z) + eps_top + eps_bot;
    head_h     = m3_head_depth + eps_top;
    cx = sx * saddle_center_x;
    cy = sy * bolt_y_offset;
    // Full-height clearance shaft.
    translate([cx, cy, cap_bottom_z - eps_bot])
        cylinder(h = shaft_h, d = m3_clearance_d);
    // Countersink at the cap's top face for the SHCS head.
    translate([cx, cy, cap_top_z - m3_head_depth])
        cylinder(h = head_h, d = m3_head_d);
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
