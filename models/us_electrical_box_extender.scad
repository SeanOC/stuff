// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// US electrical box extender — 1-4 gang extension ring that builds a
// recessed box out flush with a thick (tile/panel/shiplap) wall, with
// per-gang screw posts on the standard US device-box hole pattern.
//
// PORTED from BlackjackDuck (Andy)'s "Customizable US Electrical Box
// Extension" on MakerWorld:
//   https://makerworld.com/en/models/1252965-customizable-us-electrical-box-extension
// This is an INTEGRATION + PARAM-WIRING port, not a redesign: the
// source geometry (rect_tube shell + BOSL2 diff/tag screw posts laid
// out with xcopies/ycopies) is reproduced faithfully; only the
// Customizer-comment parameters were converted to this repo's @param
// annotation format.
//
// LICENSING: the original is licensed Creative Commons Attribution-
// NonCommercial-ShareAlike 4.0 (CC-BY-NC-SA 4.0). This derived work
// carries the same terms — NON-COMMERCIAL: personal use only, do not
// sell prints or files, and attribution to BlackjackDuck (Andy) must
// be retained. Same discipline as the QuackWorks-derived models in
// this repo (cf. ego_lb6500_blower_mount.scad).
//
// === Print orientation (native): open-face down, extrudes up ===
//
// z=0 is the flat back face — the ring rim, the screw-post bottoms and
// their wall bridges all sit ON the bed as the first layer. The whole
// part then extrudes straight up `box_depth`: the rounded rectangular
// shell walls, the round screw posts, and the vertical through-holes
// are all prisms with no overhanging faces, so it prints support-free
// in any orientation that puts a flat z-face on the bed. There is no
// bridging span anywhere — the frame is open front-to-back (it is a
// spacer ring, not a closed box), so nothing needs to bridge across
// the opening.
//
// === Standard US device-box conformance (pst-c6l) ===
//
// The defaults ARE the NEMA/industry device-box spec — this is a
// dimensionally faithful extender, not an approximation:
//   - single-gang face:   2.25 x 3.75 in
//   - width by gang:      2.25 / 3.75 / 5.75 / 7.6 in for 1..4 gang
//   - yoke lateral pitch (per gang):  1.8125 in (1-13/16)  -> screw_col_spacing_in
//   - device-screw vertical spacing:  3.28125 in (3-9/32)  -> screw_row_spacing_in
//   - device mounting screws:         6-32 UNC (3.505 mm major dia)
// (The sidecar pins these defaults so a silent drift fails CI.)
//
// Screw-hole sizing (screw_hole_size, default 3.25 mm): the posts take
// the device's own 6-32 mounting screws. 3.25 mm is BELOW the 3.505 mm
// major diameter on purpose, so the screw thread-forms (self-taps) into
// the plastic post — the extender itself becomes the new mount point.
// This is the proven default from the source design and a deliberate
// middle ground; pick per your assembly method (both ends are inside
// the param's 2-5 mm range):
//   - screws thread INTO the posts (default): 3.25 mm, or 2.85-3.0 mm
//     for a firmer self-tap bite in softer plastic.
//   - screws PASS THROUGH to the box ears behind: open to ~3.6 mm for
//     a 6-32 clearance hole.
// Kept at the source's 3.25 mm here (faithful port).

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>

$fn = 64;

// === User-tunable parameters ===

gang_count       = 2;    // @param integer min=1 max=4 step=1 group=box label="Gang count"
box_depth        = 25;   // @param number min=10 max=60 step=1 unit=mm group=box label="Box depth"
wall_thickness   = 3;    // @param number min=1.5 max=6 step=0.5 unit=mm group=box label="Wall thickness"
mount_post_width = 12;   // @param number min=8 max=14 step=1 unit=mm group=screws label="Screw post width"
screw_hole_size  = 3.25; // @param number min=2 max=5 step=0.05 unit=mm group=screws label="Screw hole diameter (6-32 self-tap; see header)"

// Advanced overrides — match these to your specific box's dimensions.
// Left without min/max on purpose: they are a matched spec for a given
// US box standard, not free exploration axes, so the param sweep does
// not push them to non-physical extremes (an oversized screw pattern
// on an undersized box would float the posts off the walls).
box_width_override_in = 0;       // @param number min=0 max=8 step=0.25 unit=in group=overrides label="Box width override (in; 0 = auto by gang)"
box_height_in         = 3.75;    // @param number unit=in group=overrides label="Box height (in)"
screw_row_spacing_in  = 3.28125; // @param number unit=in group=overrides label="Screw vertical spacing (in) = 3 + 9/32"
screw_col_spacing_in  = 1.8125;  // @param number unit=in group=overrides label="Screw lateral spacing (in) = 1 + 13/16"
screw_lateral_offset  = 0;       // @param number unit=mm group=overrides label="Screw mount lateral shift (mm; -left / +right)"

// @preset id="1-gang" label="1-gang" gang_count=1
// @preset id="2-gang" label="2-gang (default)" gang_count=2
// @preset id="4-gang" label="4-gang" gang_count=4

// === Derived ===

function inches_to_mm(inches) = inches * 25.4;

// Outer box width follows the gang count via the standard US box width
// lookup, unless overridden. (2.25 / 3.75 / 5.75 / 7.6 inches.)
box_width_in =
    box_width_override_in != 0 ? box_width_override_in
    : gang_count == 1 ? 2.25
    : gang_count == 2 ? 3.75
    : gang_count == 3 ? 5.75
    : gang_count == 4 ? 7.6
    : 0;

// Half the vertical gap between the screw hole pattern and the box
// edge — the length of the bridge that ties each post row to its
// nearer wall. Derived (not a @param), so it always tracks the box
// height / screw spacing above.
screw_mount_inset = inches_to_mm(box_height_in - screw_row_spacing_in) / 2;

// PRINT_ANCHOR_BBOX — outermost printed bbox in mm (X, Y, Z) at
// defaults (gang_count = 2, override off). Keep the arithmetic below
// current; the invariants gate fails on >1mm drift from the exported
// STL.
//   X = box width  = 3.75 in x 25.4 = 95.25
//   Y = box height = 3.75 in x 25.4 = 95.25, but the round screw-post
//       tops sit flush with the box edge and their radius reaches
//       ~47.67 each side -> 95.34 governs
//   Z = box depth  = 25
PRINT_ANCHOR_BBOX = [95.25, 95.34, 25];

// === Body (faithful port of the source union) ===

union() {
    // Outer box: rounded rectangular tube, open front and back.
    rect_tube(size = [inches_to_mm(box_width_in), inches_to_mm(box_height_in)],
              wall = wall_thickness, h = box_depth,
              rounding = wall_thickness, irounding = wall_thickness / 2);

    // Screw mounts: `gang_count` columns x 2 rows. Each post is a
    // cylinder unioned with a rectangular bridge to its nearer wall
    // (BACK for the bottom row, FRONT for the top — chosen by $idx),
    // then drilled through with the screw clearance hole.
    right(screw_lateral_offset)
    xcopies(spacing = inches_to_mm(screw_col_spacing_in), n = gang_count)
        ycopies(spacing = inches_to_mm(screw_row_spacing_in) + 0.02)
            union() {
                diff() {
                    cyl(d = mount_post_width, h = box_depth, anchor = BOT);
                    cuboid([mount_post_width, screw_mount_inset - 1, box_depth],
                           anchor = $idx == 0 ? BOT + BACK : BOT + FRONT);
                    tag("remove") down(0.01)
                        cyl(d = screw_hole_size, h = box_depth + 0.02, anchor = BOT);
                }
            }
}
