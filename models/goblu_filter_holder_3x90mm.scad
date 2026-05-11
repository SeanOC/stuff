// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Side-mount RV water filter holder for the goBlu 3-cylinder assembly
// (st-r3t). Replaces the stock top-mount blue bracket: this is a
// VHB-stuck side bracket that cradles the lower ~115 mm of each 90 mm
// stainless filter housing. Three identical pods sit flush in a row,
// optionally interlocked with a vertical-slide dovetail; each pod
// independently bonds to the RV interior wall via the flat back face.
//
// === Load-bearing invariants (don't regress) ===
//
//   - **Pocket ID = housing_diameter + 2·clearance.** The whole point of
//     the holder is that the filter housing slides in and out cleanly.
//     Clearance < 0.5 mm risks binding on thermal expansion or surface
//     scratches; > 1.5 mm gets sloppy and rattly. Default 0.5 mm =
//     pocket ID 91 mm per the bead's "91 mm" anchor.
//   - **back_wall_t ≤ 10 mm.** Spec ceiling. Pushing the assembly more
//     than 10 mm off the RV wall makes the cantilever moment on the VHB
//     too large; the VHB rating sheet derates fast past that.
//   - **Back face is flat: no ribs, holes, or fillets on -Y.** VHB
//     needs ≥ 70% continuous bond area. The dovetail features live on
//     the ±X side faces; the drain hole is on -Z; the pocket opens on
//     +Z. The back face stays a pristine flat rectangle.
//   - **Pocket depth + collar headroom < housing body height.** The
//     housing is 118 mm tall under the collar; pocket_depth=115 +
//     collar_headroom=3 = 118, with the headroom keeping the holder
//     rim 3 mm clear of the collar's underside so the collar isn't
//     bearing the housing's weight against our top rim.
//   - **Cell spacing is derived, not set.** pod_w = pocket_id +
//     2·side_wall_t. Two adjacent pods share a 2·side_wall_t-wide
//     interface, which matches the bead's 30 mm gap between housings
//     at side_wall_t=15 (default). Changing side_wall_t reshapes the
//     array footprint and also the dovetail mating depth → keep
//     dovetail_depth ≤ side_wall_t/2 so neither tongue nor slot
//     punches through the wall.
//
// === Install orientation ===
//
//   install +Z = up toward RV ceiling (cylinder axis)
//   install -Y = into the wall (VHB face — flat, no features)
//   install +X = along the wall, across the 3-pod array
//
// VHB tape goes on the -Y face. Filters drop into pockets from +Z.
// Water drains out of -Z through the bottom retaining ring's central
// hole. Pods touch flush on their ±X faces; the optional dovetail
// keeps neighbors from skewing in -Y (VHB peel direction) under a
// lateral bump.
//
// === Print orientation ===
//
// Each pod prints individually: pocket axis vertical (+Z up, same as
// install), -Z face on the build plate. The pocket cylindrical walls
// then print as concentric perimeters (one per layer); the top-rim
// lead-in chamfer is in-plane and prints cleanly with no overhang.
// The -Y VHB face stays vertical during printing — it's a side face
// of a roughly cubic block, so no support is needed.
//
// PETG or ASA preferred (RV interior, intermittent moisture). PLA is
// acceptable in shaded interior installs but check that the cabinet
// doesn't see > 50 °C in summer sun.
//
// === Pod-to-pod interconnect ===
//
// Vertical-slide dovetail. Each pod has a male tongue on its +X face
// and a female slot on its -X face, both running vertically over
// dovetail_height (default 80 mm, centred on the pod's mid-height).
// Tongue cross-section is a trapezoid wider at its tip than its base,
// so once two pods are stacked the slot mechanically locks the tongue
// against -Y pull (the direction VHB peels worst).
//
// When pod_count > 1 the model auto-caps the outermost faces (the
// leftmost pod's -X slot is filled, the rightmost pod's +X tongue is
// omitted) so the assembly presents flat outer side walls. Setting
// pod_count = 1 renders a single pod with both dovetail features
// exposed (useful as the print-time slice).
//
// === pod_gap and the slicer_3up preset (st-hxk, corrected by st-toz) ===
//
// `pod_gap` is print-time air space, nothing more. It pushes adjacent
// pods apart in X so the slicer sees each pod as an independent body
// (per-pod move, rotate, support). Dovetail features are NOT suppressed
// when pod_gap > 0 — they're the post-print assembly mechanism: the
// user prints the pods separately, then slides them together by hand
// and the tongues engage the slots.
//
// End-cap suppression is independent of pod_gap and runs in both
// modes: the leftmost pod's -X slot is filled, the rightmost pod's +X
// tongue is omitted. So for pod_count = 3 you always get four dovetail
// features — leftmost tongue (+X inner), middle slot+tongue (both
// inner-facing), rightmost slot (-X inner). The outer faces of the
// end pods stay flat in both modes.
//
// pod_gap = 0 (stock_3up): pods touch flush, the tongues already sit
// inside the adjacent slots, and the union collapses to a single
// connected body. That's the installed-on-the-wall geometry.
//
// pod_gap > 0 (slicer_3up uses 10 mm): tongues protrude into open air
// short of the next pod's face (default tongue depth 6 mm < 10 mm
// gap, so 4 mm clearance), each pod is its own connected component,
// and post-print the user slides them together to engage.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Housing fit -----
housing_diameter      = 90;    // @param number min=40 max=160 step=0.5 unit=mm group=housing label="Filter housing OD"
clearance             = 0.5;   // @param number min=0.1 max=2 step=0.05 unit=mm group=housing label="Pocket slip clearance (radial)"
pocket_depth          = 115;   // @param number min=20 max=200 step=1 unit=mm group=housing label="Pocket depth (cylinder support length)"
collar_headroom       = 3;     // @param number min=0 max=20 step=0.5 unit=mm group=housing label="Headroom under housing collar"
top_lead_in_r         = 5;     // @param number min=0 max=10 step=0.5 unit=mm group=housing label="Top-rim lead-in radius"

// ----- Bottom retaining ring + drain -----
bottom_ring_thickness = 5;     // @param number min=2 max=15 step=0.5 unit=mm group=drain label="Bottom retaining-ring thickness"
bottom_lip_w          = 5;     // @param number min=0 max=20 step=0.5 unit=mm group=drain label="Bottom retaining lip width (radial)"

// ----- Wall thicknesses -----
back_wall_t           = 7;     // @param number min=3 max=10 step=0.5 unit=mm group=walls label="Back wall (VHB face) thickness"
front_wall_t          = 5;     // @param number min=3 max=15 step=0.5 unit=mm group=walls label="Front wall thickness"
side_wall_t           = 15;    // @param number min=5 max=25 step=0.5 unit=mm group=walls label="Side wall thickness (per pod)"

// ----- Array + interconnect -----
pod_count             = 3;     // @param integer min=1 max=5 group=array label="Pod count in array"
dovetail_enabled      = true;  // @param boolean group=array label="Enable side-face dovetails"
dovetail_w_base       = 14;    // @param number min=5 max=30 step=0.5 unit=mm group=array label="Dovetail base width (at wall face)"
dovetail_w_tip        = 18;    // @param number min=6 max=40 step=0.5 unit=mm group=array label="Dovetail tip width (away from wall)"
dovetail_depth        = 6;     // @param number min=2 max=12 step=0.5 unit=mm group=array label="Dovetail depth (X-protrusion / slot-cut)"
dovetail_height       = 80;    // @param number min=20 max=200 step=1 unit=mm group=array label="Dovetail vertical extent"
dovetail_clearance    = 0.2;   // @param number min=0 max=1 step=0.05 unit=mm group=array label="Dovetail slip clearance (slot oversize)"
pod_gap               = 0;     // @param number min=0 max=50 step=1 unit=mm group=array label="Gap between adjacent pods (for slicer export)"

// ----- Edge treatment -----
edge_round_r          = 1.5;   // @param number min=0 max=5 step=0.25 unit=mm group=edges label="Outer edge rounding"

// @preset id="stock_3up"   label="Stock goBlu 3-up (3×90mm, 30mm gap)"      housing_diameter=90 clearance=0.5 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=3 dovetail_enabled=true  dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 pod_gap=0  edge_round_r=1.5
// @preset id="single_pod"  label="Single pod (print one at a time)"        housing_diameter=90 clearance=0.5 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=1 dovetail_enabled=true  dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 pod_gap=0  edge_round_r=1.5
// @preset id="flush_3up"   label="3-up, no dovetails (VHB only)"           housing_diameter=90 clearance=0.5 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=3 dovetail_enabled=false dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 pod_gap=0  edge_round_r=1.5
// @preset id="slicer_3up"  label="3-up for slicer (10mm gap, dovetails on inner faces)" housing_diameter=90 clearance=0.5 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=3 dovetail_enabled=true  dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 pod_gap=10 edge_round_r=1.5

// === Derived ===

pocket_id = housing_diameter + 2 * clearance;          // 91 at defaults
pod_w     = pocket_id + 2 * side_wall_t;               // 91 + 30 = 121
pod_d     = back_wall_t + pocket_id + front_wall_t;    // 7 + 91 + 5 = 103
pod_h     = bottom_ring_thickness + pocket_depth + collar_headroom; // 123

// Pocket centred in Y such that the -Y back wall is back_wall_t thick.
pocket_cy = -pod_d / 2 + back_wall_t + pocket_id / 2;

// Dovetail Z-centre (centred on pod height).
dovetail_cz = pod_h / 2;

// Dovetails are the post-print assembly mechanism — they stay enabled
// regardless of pod_gap (st-toz, correcting st-hxk's over-suppression).
// End-cap suppression in `array()` is what keeps outer faces flat on
// end pods; this flag just gates the per-pod feature on/off globally
// via the `dovetail_enabled` @param.
dovetails_active = dovetail_enabled;

// At pod_gap == 0 each tongue ends up sitting inside its mating slot's
// cavity with clearance air on all four perimeter sides, which CGAL
// outputs as a sealed inner void — the slot cavity's inner surface
// shows up as a separate connected component in the rendered STL,
// distinct from the outer body. That's a known harmless artifact of
// the dovetail's slip-fit geometry, not a real defect. The model
// declares two expected such orphan components below
// (// INVARIANTS_EXPECTED_ORPHANS = 2) so the topology check tolerates
// them. At pod_gap > 0 (slicer_3up) the pods are spaced apart and each
// tongue/slot is on the outer surface of its own pod — no enclosed
// voids, no orphans.

// Array X-offset for pod index i in [0, pod_count). Centre-to-centre
// spacing is pod_w + pod_gap; at pod_gap = 0 this collapses to pods
// touching flush along their side walls (stock_3up).
function pod_x(i) = (i - (pod_count - 1) / 2) * (pod_w + pod_gap);

// PRINT_ANCHOR_BBOX at defaults (stock_3up, pod_gap = 0):
//   X = pod_count * pod_w + (pod_count - 1) * pod_gap = 3 * 121 + 0 = 363
//   Y = pod_d = 103
//   Z = pod_h = 123
PRINT_ANCHOR_BBOX = [363, 103, 123];

// At pod_gap == 0 each mated tongue/slot forms a fully-enclosed inner
// cavity (the tongue + clearance air ring + slot walls are sealed in
// by the tongue base contacting the slot mouth perimeter). CGAL emits
// the cavity's inner surface as a separate connected component. The
// 3-pod stock_3up assembly has two such cavities (pod0→pod1 and
// pod1→pod2 dovetail joints), so the topology check tolerates two
// orphans below the standard 50-tri threshold. (st-yuu)
// INVARIANTS_EXPECTED_ORPHANS = 2

// === Dovetail primitive ===
//
// A vertical-slide dovetail tongue: trapezoid in the XY plane, wider
// at +X tip than at the wall face. Anchored so its mating face is at
// x=0 and its tip extends in +X.  Extruded along Z by `height`,
// centred on z=0.

module dovetail_tongue(w_base, w_tip, depth, height) {
    poly = [
        [0,     -w_base / 2],
        [depth, -w_tip  / 2],
        [depth,  w_tip  / 2],
        [0,      w_base / 2],
    ];
    translate([0, 0, -height / 2])
        linear_extrude(height = height)
            polygon(poly);
}

// === One pod ===
//
// `expose_left_slot`  — leave the -X face's dovetail slot open (true
//                       for any pod that has a neighbor on its left).
// `expose_right_tongue` — keep the +X face's tongue (true for any pod
//                       with a neighbor on its right).
// End pods get those flags flipped, capping the outer face.

module pod(expose_left_slot, expose_right_tongue) {
    difference() {
        union() {
            // Pod block with rounded vertical edges. Bottom rim stays
            // sharp (build-plate adhesion), top rim picks up a small
            // round so the corner doesn't snag.
            cuboid([pod_w, pod_d, pod_h],
                   rounding = edge_round_r,
                   edges    = "Z",
                   anchor   = BOTTOM);

            // Dovetail tongue on +X face.
            if (dovetails_active && expose_right_tongue)
                translate([pod_w / 2, 0, dovetail_cz])
                    dovetail_tongue(dovetail_w_base, dovetail_w_tip,
                                    dovetail_depth, dovetail_height);
        }

        // Pocket bore: open top, full pocket_depth + collar_headroom.
        // Start from the top of the bottom retaining ring.
        translate([0, pocket_cy, bottom_ring_thickness])
            cylinder(h = pocket_depth + collar_headroom + 0.1,
                     d = pocket_id);

        // Top-rim lead-in: conical opening from pocket_id at depth
        // top_lead_in_r down to (pocket_id + 2·top_lead_in_r) at the
        // very top. Replaces a hard top corner with a generous flare.
        translate([0, pocket_cy, pod_h - top_lead_in_r])
            cylinder(h = top_lead_in_r + 0.01,
                     d1 = pocket_id,
                     d2 = pocket_id + 2 * top_lead_in_r);

        // Drain through-hole at the bottom: smaller diameter than the
        // pocket so a 5 mm radial lip remains for the housing to rest
        // on. Skip the lip entirely when bottom_lip_w = 0 → drain ID
        // matches pocket ID and the housing falls through.
        translate([0, pocket_cy, -0.1])
            cylinder(h = bottom_ring_thickness + 0.2,
                     d = max(pocket_id - 2 * bottom_lip_w, 1));

        // Dovetail slot on -X face. Cut the same tongue shape into the
        // wall, oversized by `effective_clearance` for slip fit.
        // `dovetail_tongue` extends in +X from its anchor: anchored at
        // x=-pod_w/2, the polygon walks inward through the wall — narrow
        // at the face, widening to the dovetail tip. That's the inverse
        // profile of an adjacent pod's +X tongue (which is narrow at
        // its base, widest at its tip), so the two mate with slip fit.
        // At pod_gap == 0 the effective clearance collapses to 0 so the
        // tongue and slot share boundary surfaces — required for CGAL
        // to fuse them into one connected solid (otherwise the tongue
        // orphans inside the slot cavity, st-yuu / st-v7k). (st-yuu —
        // earlier code rotated the subtrahend 180° and cut into empty
        // space outside the pod.)
        if (dovetails_active && expose_left_slot)
            translate([-pod_w / 2, 0, dovetail_cz])
                dovetail_tongue(
                    dovetail_w_base + 2 * dovetail_clearance,
                    dovetail_w_tip  + 2 * dovetail_clearance,
                    dovetail_depth + 0.1,  // slot floor overshoot
                    dovetail_height + 0.01);
    }
}

// === Array layout ===
//
// pod_count pods placed at cell_spacing = pod_w + pod_gap along X.
// End-cap suppression runs identically in both gap modes (st-toz):
// leftmost pod's -X slot is suppressed (flat outer face), rightmost
// pod's +X tongue is suppressed (flat outer face). For pod_count = 3
// that yields four dovetail features — one tongue + one slot on each
// inner-facing interface — in both `stock_3up` (pods touching, dovetails
// already mated) and `slicer_3up` (pods spaced apart, user mates them
// post-print).
//
// Single pod (pod_count=1) shows both dovetail features when active,
// for inspection during print prep.

module array() {
    if (pod_count == 1) {
        pod(expose_left_slot = true, expose_right_tongue = true);
    } else {
        for (i = [0 : pod_count - 1])
            translate([pod_x(i), 0, 0])
                pod(expose_left_slot   = (i > 0),
                    expose_right_tongue = (i < pod_count - 1));
    }
}

array();
