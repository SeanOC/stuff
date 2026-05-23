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
//     Clearance < 0.25 mm risks binding on thermal expansion or surface
//     scratches; > 1.5 mm gets sloppy and rattly. Default 0.3 mm =
//     pocket ID 90.6 mm at 90 mm housing — st-e6q tightened from 0.5 mm
//     (pocket ID 91 mm) for a noticeably snugger seat; bench-tested 0.3
//     and the housing still slips in clean with no binding.
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
//     interface, which approximates the bead's 30 mm gap between
//     housings at side_wall_t=15 (default). Changing side_wall_t
//     reshapes the array footprint and also the dovetail mating
//     depth → keep dovetail_depth ≤ side_wall_t/2 so neither tongue
//     nor slot punches through the wall.
//   - **Outer-edge rounding stays clear of mating + VHB surfaces
//     (st-e6q).** `edge_round_r` rounds only edges of the +Y front
//     face plus the bounding edges of any ±X side face that is
//     *outer* (no neighboring pod). Edges that touch the -Y/VHB face
//     are never rounded (VHB needs a flat back), and edges shared
//     with a mating ±X face are never rounded (so neighboring pods
//     stay flush along the entire interface, with no chamfer-gap at
//     the dovetail edges). End pods get one outer side rounded;
//     inner pods only have their +Y front face's two horizontal
//     edges rounded.
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
// and a female slot on its -X face; both run from the pod's bottom
// (z=0 for the tongue, z=-0.1 for the slot — slightly below the base
// for a clean cut, st-6xj) up to `dovetail_top_z`, with the top
// `dovetail_top_taper_h` of each tapering to a point so the print is
// support-free (st-nn5). Tongue cross-section is a trapezoid wider at
// the +X tip than at the wall face, so once two pods are stacked the
// slot mechanically locks the tongue against -Y pull (the direction
// VHB peels worst).
//
// Assembly workflow: VHB pod A to the wall first; hold pod B above and
// to the side; lower pod B straight down so A's tongue enters B's
// bottom-open slot and rides up as B descends. When B's bottom aligns
// with A's, the closed top of B's slot meets the top of A's tongue
// and arrests further descent — the joint is self-aligning ("drop and
// stop"). VHB pod B once aligned.
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
//
// === Version history ===
//
// v1 (st-r3t)  : initial 3-up bracket, top-rim chamfer, drain hole.
// v1.1 (st-hxk): pod_gap param for slicer separation.
// v1.2 (st-toz): re-enable dovetails at pod_gap > 0; end-cap suppression.
// v1.3 (st-yuu): connected-component invariant tightening.
// v1.4 (st-6xj): open the slot through the pod base — flush mode is now
//                a single connected component (no sealed cavities).
// v1.5 (st-nn5): tapered slot/tongue tops for support-free print.
// v2   (st-e6q): snug pocket (clearance 0.5 → 0.3 mm); outer-edge
//                rounding scope tightened so it never bleeds onto the
//                -Y/VHB face or the dovetail mating geometry; +Y front
//                face's top + bottom horizontal edges added to the
//                rounding set; new invariant pins -Y face flatness.

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>

$fn = 64;

// === User-tunable parameters ===

// ----- Housing fit -----
housing_diameter      = 90;    // @param number min=40 max=160 step=0.5 unit=mm group=housing label="Filter housing OD"
clearance             = 0.3;   // @param number min=0.1 max=2 step=0.05 unit=mm group=housing label="Pocket slip clearance (radial)"
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
dovetail_top_taper_h  = 9;     // @param number min=0 max=30 step=0.5 unit=mm group=array label="Dovetail top taper (0 = flat top, needs support; ≥w_tip/2 prints support-free)"
pod_gap               = 0;     // @param number min=0 max=50 step=1 unit=mm group=array label="Gap between adjacent pods (for slicer export)"

// ----- Edge treatment -----
edge_round_r          = 1.5;   // @param number min=0 max=5 step=0.25 unit=mm group=edges label="Outer edge rounding"

// @preset id="stock_3up"   label="Stock goBlu 3-up (3×90mm, 30mm gap)"      housing_diameter=90 clearance=0.3 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=3 dovetail_enabled=true  dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 dovetail_top_taper_h=9 pod_gap=0  edge_round_r=1.5
// @preset id="single_pod"  label="Single pod (print one at a time)"        housing_diameter=90 clearance=0.3 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=1 dovetail_enabled=true  dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 dovetail_top_taper_h=9 pod_gap=0  edge_round_r=1.5
// @preset id="flush_3up"   label="3-up, no dovetails (VHB only)"           housing_diameter=90 clearance=0.3 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=3 dovetail_enabled=false dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 dovetail_top_taper_h=9 pod_gap=0  edge_round_r=1.5
// @preset id="slicer_3up"  label="3-up for slicer (10mm gap, dovetails on inner faces)" housing_diameter=90 clearance=0.3 pocket_depth=115 collar_headroom=3 top_lead_in_r=5 bottom_ring_thickness=5 bottom_lip_w=5 back_wall_t=7 front_wall_t=5 side_wall_t=15 pod_count=3 dovetail_enabled=true  dovetail_w_base=14 dovetail_w_tip=18 dovetail_depth=6 dovetail_height=80 dovetail_clearance=0.2 dovetail_top_taper_h=9 pod_gap=10 edge_round_r=1.5

// === Derived ===

pocket_id = housing_diameter + 2 * clearance;          // 90.6 at defaults (st-e6q)
pod_w     = pocket_id + 2 * side_wall_t;               // 90.6 + 30 = 120.6
pod_d     = back_wall_t + pocket_id + front_wall_t;    // 7 + 90.6 + 5 = 102.6
pod_h     = bottom_ring_thickness + pocket_depth + collar_headroom; // 123

// Pocket centred in Y such that the -Y back wall is back_wall_t thick.
pocket_cy = -pod_d / 2 + back_wall_t + pocket_id / 2;

// Dovetail Z geometry. `dovetail_cz` is the legacy z-centre value that
// `dovetail_height` was symmetric around; the tongue / slot top sits at
// that value plus half the dovetail_height — both features now anchor
// at the pod base and rise up to `dovetail_top_z` (st-nn5).
dovetail_cz    = pod_h / 2;
dovetail_top_z = dovetail_cz + dovetail_height / 2;

// Dovetails are the post-print assembly mechanism — they stay enabled
// regardless of pod_gap (st-toz, correcting st-hxk's over-suppression).
// End-cap suppression in `array()` is what keeps outer faces flat on
// end pods; this flag just gates the per-pod feature on/off globally
// via the `dovetail_enabled` @param.
dovetails_active = dovetail_enabled;

// Each dovetail slot is open at the pod's bottom face (st-6xj) so an
// adjacent pod's tongue has a path to slide in during VHB install,
// and its top is a tapered point rather than a flat roof (st-nn5)
// so the slot's close prints support-free. The tongue mirrors the
// taper at its top, prints from z=0 with no bottom overhang, and
// mates against the slot in both the straight and tapered regions.
// At pod_gap == 0 the slot's clearance-air ring around the mated
// tongue vents to outside through that bottom opening — no sealed
// inner void, so CGAL outputs the 3-pod assembly as a single
// connected surface.

// Array X-offset for pod index i in [0, pod_count). Centre-to-centre
// spacing is pod_w + pod_gap; at pod_gap = 0 this collapses to pods
// touching flush along their side walls (stock_3up).
function pod_x(i) = (i - (pod_count - 1) / 2) * (pod_w + pod_gap);

// PRINT_ANCHOR_BBOX at defaults (stock_3up, pod_gap = 0, clearance = 0.3):
//   X = pod_count * pod_w + (pod_count - 1) * pod_gap = 3 * 120.6 + 0 = 361.8
//   Y = pod_d = 102.6
//   Z = pod_h = 123
PRINT_ANCHOR_BBOX = [361.8, 102.6, 123];

// Each dovetail slot is open at the pod's bottom face (st-6xj) so
// the cavity is no longer a sealed inner void at pod_gap == 0 — the
// air ring around the mated tongue drains out through the bottom
// opening, and CGAL outputs the assembly as a single connected
// surface. No INVARIANTS_EXPECTED_ORPHANS directive is needed.

// === Dovetail primitive ===
//
// A vertical-slide dovetail extrusion: trapezoid in the XY plane,
// wider at +X tip than at the wall face. Anchored so the mating face
// is at x=0 and the tip extends in +X. Bottom of the extrusion sits
// at z=0; the bottom (height − taper_h) is constant cross-section,
// and the top taper_h linearly scales to a point at z=height
// (`linear_extrude(scale=0)`), producing a self-supporting roof when
// used as a slot subtraction and a self-supporting tip when used as
// a tongue. Pass `taper_h = 0` for the legacy flat-top shape.

module dovetail_polygon(w_base, w_tip, depth) {
    polygon([
        [0,     -w_base / 2],
        [depth, -w_tip  / 2],
        [depth,  w_tip  / 2],
        [0,      w_base / 2],
    ]);
}

module dovetail_extrude(w_base, w_tip, depth, height, taper_h = 0) {
    straight_h = max(height - taper_h, 0.01);
    linear_extrude(height = straight_h)
        dovetail_polygon(w_base, w_tip, depth);
    if (taper_h > 0)
        translate([0, 0, straight_h])
            linear_extrude(height = taper_h, scale = 0)
                dovetail_polygon(w_base, w_tip, depth);
}

// === One pod ===
//
// `expose_left_slot`  — leave the -X face's dovetail slot open (true
//                       for any pod that has a neighbor on its left).
// `expose_right_tongue` — keep the +X face's tongue (true for any pod
//                       with a neighbor on its right).
// End pods get those flags flipped, capping the outer face.

module pod(expose_left_slot, expose_right_tongue) {
    // Outer-edge rounding (st-e6q): scope to the four edges of the
    // +Y front face (top, bottom, and the two vertical corners
    // bordering ±X). Everything else stays sharp.
    //
    //   • BACK+TOP, BACK+BOTTOM — the "top/bottom perimeter
    //     horizontal edges" the bead asks for (#3).
    //   • BACK+LEFT, BACK+RIGHT — vertical edges between +Y and
    //     ±X. The rounding sits within `edge_round_r` mm (1.5 mm at
    //     default) of the +Y face and stays > 40 mm clear of the
    //     dovetail base at y = ±dovetail_w_base/2, so it does not
    //     bleed into the dovetail tongue/slot geometry (#2).
    //
    // Never rounded:
    //   • Any edge touching FRONT (= -Y/VHB) — preserves the
    //     flat-bond invariant. Stricter than the pre-st-e6q
    //     `edges="Z"`, which rounded FRONT+LEFT and FRONT+RIGHT
    //     (small bleed onto -Y).
    //   • ±X face top/bottom horizontal edges (TOP/BOTTOM +
    //     LEFT/RIGHT) — these would bleed across the mating
    //     interface onto the neighboring pod at pod_gap = 0, and
    //     a per-pod-position edge spec breaks CGAL by producing
    //     non-manifold slivers at the interface (BOSL2 cuboid's
    //     corner_shape places epsilon-cubes at cnt=0 corners that
    //     don't line up between mismatched-spec neighbors).
    //
    // Numerical precision shim: CGAL union of N pods at
    // pod_gap = 0 can leave 4-shared edges along the pod-pod
    // interface at clearance values that yield non-round pod_w
    // (e.g. clearance = 0.3 → pod_w = 120.6 → CGAL leaves
    // 4-shared edges at x = ±60.3 instead of a clean 2-shared
    // boundary). A 1 µm overlap on each cuboid forces CGAL to see
    // overlap instead of tangent, producing a clean 2-volume Nef
    // polyhedron at every clearance value the @param range allows.
    pod_overlap_eps = 0.001;

    difference() {
        union() {
            // Pod block.
            cuboid([pod_w + pod_overlap_eps, pod_d, pod_h],
                   rounding = edge_round_r,
                   edges    = [BACK],
                   anchor   = BOTTOM);

            // Dovetail tongue on +X face. Anchored at the pod base
            // (z=0) so the tongue prints continuously off the build
            // plate with no bottom overhang (st-nn5). Tongue reaches
            // up to `slot_top_z` — same elevation as the slot's
            // closed top — so the drop-and-stop alignment still
            // engages at full descent. The top `dovetail_top_taper_h`
            // tapers to a point (scale=0 linear_extrude) so the
            // tongue's tip is self-supporting in print and mates
            // with the slot's matching tapered close.
            if (dovetails_active && expose_right_tongue)
                translate([pod_w / 2, 0, 0])
                    dovetail_extrude(dovetail_w_base, dovetail_w_tip,
                                     dovetail_depth, dovetail_top_z,
                                     dovetail_top_taper_h);
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

        // Dovetail slot on -X face. Cut the same dovetail shape into
        // the wall, oversized by `dovetail_clearance` for slip fit.
        // `dovetail_extrude` extends in +X from its anchor at x=-pod_w/2,
        // so the polygon walks inward through the wall — narrow at the
        // face, widening to the dovetail tip. That's the inverse profile
        // of an adjacent pod's +X tongue, so the two mate with slip fit.
        //
        // Slot extends DOWN through the pod's bottom face (st-6xj) so an
        // adjacent pod's tongue has a path in: install pod A on the wall,
        // hold pod B above and to the side, lower pod B straight down,
        // and A's tongue enters B's slot through B's bottom and slides
        // up as B descends. The top stays at `dovetail_top_z` — when B
        // descends far enough that its bottom aligns with A's, the slot
        // top (a tapered point) meets the tongue top (also a tapered
        // point) and arrests further descent ("drop and stop").
        //
        // The top `dovetail_top_taper_h` of the cut scales to a point
        // (st-nn5) so the slot's roof is a self-supporting cone rather
        // than a flat horizontal overhang — prints without supports.
        if (dovetails_active && expose_left_slot) {
            slot_bot_z = -0.1;  // overshoot the pod base for a clean cut
            slot_h     = dovetail_top_z - slot_bot_z;
            translate([-pod_w / 2, 0, slot_bot_z])
                dovetail_extrude(
                    dovetail_w_base + 2 * dovetail_clearance,
                    dovetail_w_tip  + 2 * dovetail_clearance,
                    dovetail_depth + 0.1,  // slot floor overshoot in X
                    slot_h,
                    dovetail_top_taper_h);
        }
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
