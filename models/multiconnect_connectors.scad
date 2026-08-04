// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Standalone Multiconnect (Multiboard) connectors — ready-to-print
// pieces that lock an accessory backer into a Multiboard tile (25mm
// grid, 6.25mm standoff) (pst-ks2). One connector per part; the
// connector_type enum fans the export grid into one STL per variant so
// every kind stays ready-to-print in the repo instead of being
// regenerated from the library each time. Print one, press it in.
//
// === Four variants: three snap tiers + push-fit ===
//
// Operator decision (2026-08-04, option A): ship all four contracted
// variants — snap-regular, snap-moderate-wb, snap-heavy-wb, pushfit — as
// real geometry. The vendored QuackWorks library exposes ONE snap
// primitive (snapConnectBacker in Modules/snapConnector.scad) and ONE
// push-fit module (multiboard_push_fit in Modules/pushFitConnector.scad);
// there is no separate Wing-Back generator or WB spec upstream. The three
// snap tiers are therefore DERIVED from the single snap primitive along
// its two real physical levers, matching Multiboard's snap taxonomy
// (libs/README.md "Multiboard constants": Regular = bidirectional,
// Moderate WB / Heavy WB = unidirectional):
//
//   * snap-regular     Regular — bidirectional click. Retention bumpouts
//                      on all four sides; presses in and pulls out both
//                      ways. Grip = holding_tolerance (default 1.0).
//   * snap-moderate-wb Moderate WB — unidirectional "wing back". Bumpouts
//                      on ONE opposing pair only (the Y sides), so it
//                      seats along one axis and resists pull-out while the
//                      bumpout-free X sides flex to admit it. Moderate grip.
//   * snap-heavy-wb    Heavy WB — same unidirectional wing-back geometry
//                      with a stronger grip (larger holding bumpouts) for a
//                      firmer, more permanent hold.
//   * pushfit          press-in tapered peg (multiboard_push_fit).
//
// The bumpout-side selection is threaded through snapConnectBacker via
// patch scripts/patches/QuackWorks/0004 (bumpoutSides param, default =
// all four, so snap-regular renders byte-for-byte as before). This is an
// honest realization of the named tiers from the library primitive — the
// retention feature IS the bumpout, and confining it to one axis is what
// makes a snap "wing back" — not a copy of Multiboard's proprietary WB
// tooling.
//
// LICENSING: the connectors are QuackWorks' snapConnectBacker and
// multiboard_push_fit (libs/QuackWorks/Modules/{snapConnector,
// pushFitConnector}.scad; Multiconnect by Andy Levesque, credit David D;
// Multiboard by Keep Making; push-fit by Evil_K9), licensed CC
// BY-NC-SA 4.0 AND the Multiboard License — NON-COMMERCIAL, attribution,
// share-alike. This derived part is for personal use only; do not sell
// prints or files.
//
// === BOSL2 pin coupling (do NOT bump BOSL2) ===
//
// snapConnectBacker passes spin=[x,y,z] VECTORS into BOSL2's
// offset_sweep()/attachable(), which only the pinned BOSL2 456fcd8
// accepts — newer BOSL2 tightened attachable() to assert is_finite(spin)
// and rejects a vector (libs/README.md, "BOSL2 pin note"). All three snap
// tiers therefore re-couple to that pin: it must stay at 456fcd8 while any
// snap ships. pushfit is pure OpenSCAD and is independent of the pin.
//
// === Print orientation (native): ZERO supports ===
//
// The snap tiers print slots-down: the four L-slots that let the snap
// nubs flex are cut through to the bed (z=0), so a solid base pad would
// foul them — the same rule the merged opengrid_snaps sibling follows.
// The upward octagonal bevel is a gentle wall and the retention bumpouts
// are small self-supporting arcs. pushfit prints collar-down (widest
// 14.6mm face on the bed, mirrored) so the peg tapers inward going up —
// no overhang at all. Both sit min-Z on the bed; no supports, no raft.
//
// === BOSL2 diff() tags: root-level siblings only ===
//
// snapConnectBacker builds itself with BOSL2 diff()/tag("remove"), which
// BREAKS if wrapped in an explicit union() alongside a sibling. Each
// connector is emitted as a lone top-level statement (a bare transform
// around one primitive), never union()'d with anything else.

include <BOSL2/std.scad>
// `use` not `include`: both connector files end with top-level demo
// geometry (snapConnector.scad renders a full backer plate) that would
// otherwise inject stray solids into every render. `use` pulls in the
// module definitions only.
use <QuackWorks/Modules/snapConnector.scad>
use <QuackWorks/Modules/pushFitConnector.scad>

$fn = 64;

// === User-tunable parameters ===

// The four Multiconnect connectors, one exported STL each (the 'filename'
// flag fans the export grid over the enum). snap-regular = bidirectional
// click; snap-moderate-wb / snap-heavy-wb = unidirectional wing-back
// (moderate / firm grip); pushfit = press-in peg. See the header note for
// how the three snap tiers are derived from the one library primitive.
connector_type = "snap-regular"; // @param enum choices=snap-regular|snap-moderate-wb|snap-heavy-wb|pushfit group=connector label="Connector type" filename

// Grip strength of the snap's holding bumpouts (snapConnectBacker's
// holdingTolerance): scales the click nubs that lock into the slot.
// Higher = tighter hold / harder to pull out. Tunes around each snap
// tier's base grip; the heavy tier adds a fixed step on top. Inert for
// pushfit.
holding_tolerance = 1.0; // @param number min=0.5 max=1.5 step=0.05 group=connector label="Snap grip"

// @preset id="default" label="Regular snap" connector_type=snap-regular
// @preset id="moderate-wb" label="Moderate wing-back" connector_type=snap-moderate-wb
// @preset id="heavy-wb" label="Heavy wing-back" connector_type=snap-heavy-wb
// @preset id="pushfit" label="Push-fit peg" connector_type=pushfit

// === Derived ===

is_regular  = (connector_type == "snap-regular");
is_moderate = (connector_type == "snap-moderate-wb");
is_heavy    = (connector_type == "snap-heavy-wb");
is_snap     = is_regular || is_moderate || is_heavy;

// Wing-back tiers are unidirectional: retention bumpouts on one opposing
// pair (the Y sides) only. Regular keeps all four (bidirectional).
bumpout_sides = is_regular ? [RIGHT, LEFT, FWD, BACK] : [FWD, BACK];

// Heavy WB grips harder: step the holding bumpouts up, clamped to the
// library's [0.5, 1.5] holdingTolerance range. The Snap grip slider tunes
// around each tier's base (1.0 for regular/moderate, 1.4 for heavy).
tier_grip = is_heavy ? 1.4 : 1.0;
snap_grip = max(0.5, min(1.5, tier_grip * holding_tolerance));

// Multiboard reference constants (libs/README.md): 25mm grid pitch,
// 6.25mm Part-A standoff. Documentation/sanity anchors only — no
// geometry is derived from them (the connectors carry their own dims).
MB_PITCH    = 25;    // mm, 1 MU
MB_STANDOFF = 6.25;  // mm, offset snap (DS Part A) standoff

// PRINT_ANCHOR_BBOX at defaults (connector_type = "snap-regular"),
// measured from the export. The invariants gate fails on >1mm drift, so
// keep this current. snapConnectBacker is a 23.37mm octagonal snap
// standing 6.58mm once its slot base is dropped to the bed.
PRINT_ANCHOR_BBOX = [23.37, 23.37, 6.58];

// === Connectors (root-level siblings; never union()'d — diff() tags) ===

// snap tiers: snapConnectBacker's native z-extent is [-3.485, 3.09]; lift
// its slot base to the bed (z=0), slots-down. bumpout_sides selects
// bidirectional (all four) vs unidirectional wing-back (one opposing pair).
if (is_snap)
    translate([0, 0, 3.485])
        snapConnectBacker(offset = 0, holdingTolerance = snap_grip, bumpoutSides = bumpout_sides);

// pushfit: multiboard_push_fit's native z-extent is [-0.5, 6.0], narrow
// tip down / wide collar up. Mirror it collar-down (zero overhang) and
// drop min-Z to the bed.
if (connector_type == "pushfit")
    translate([0, 0, 6.0])
        mirror([0, 0, 1])
            multiboard_push_fit();
