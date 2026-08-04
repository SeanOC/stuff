// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Standalone Multiconnect (Multiboard) connectors — ready-to-print
// pieces that lock an accessory backer into a Multiboard tile (25mm
// grid, 6.25mm standoff) (pst-ks2). One connector per part; the
// connector_type enum fans the export grid into one STL per variant so
// the buildable kinds stay ready-to-print in the repo instead of being
// regenerated from the library each time. Print one, press it in.
//
// === SCOPE: only two connectors exist in the vendored library ===
//
// pst-ks2 originally named four variants — snap-regular, snap-moderate-wb,
// snap-heavy-wb, pushfit. Only TWO are buildable. The vendored QuackWorks
// connector library exposes exactly one snap module (snapConnectBacker
// in Modules/snapConnector.scad — a single BIDIRECTIONAL click snap,
// i.e. Multiboard's "Regular" type; params offset + holdingTolerance
// only) plus one push-fit module (multiboard_push_fit in
// Modules/pushFitConnector.scad). The "Moderate WB" and "Heavy WB" tiers
// are Multiboard PRODUCT taxonomy (libs/README.md, "Multiboard
// constants") describing unidirectional wing-back snaps — there is NO
// .scad module or parameter for them in the vendored generators, so
// nobody can produce them from this library. The enum therefore ships
// the two connectors that exist: snap-regular | pushfit. (Recorded
// assumption — operator option A; see the bead. If the WB tiers are
// wanted they must first be authored/vendored as real geometry.)
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
// and rejects a vector (libs/README.md, "BOSL2 pin note"). Shipping
// snap-regular therefore re-couples a part to that pin: it must stay at
// 456fcd8 while this snap ships. pushfit is pure OpenSCAD and is
// independent of the pin.
//
// === Print orientation (native): ZERO supports ===
//
// snap-regular prints slots-down: the four L-slots that let the snap
// nubs flex are cut through to the bed (z=0), so a solid base pad would
// foul them — the same rule the merged opengrid_snaps sibling follows.
// The upward octagonal bevel is a gentle wall and the four side bumpouts
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

// The two buildable Multiconnect connectors, one exported STL each (the
// 'filename' flag fans the export grid over the enum). snap-regular =
// snapConnectBacker (bidirectional click snap); pushfit =
// multiboard_push_fit (press-in peg). See the SCOPE note above for why
// the moderate-wb / heavy-wb tiers are absent.
connector_type = "snap-regular"; // @param enum choices=snap-regular|pushfit group=connector label="Connector type" filename

// Grip strength of the snap's holding bumpouts (snapConnectBacker's
// holdingTolerance): scales the click nubs that lock into the slot.
// Higher = tighter hold / harder to pull out. Inert for pushfit.
holding_tolerance = 1.0; // @param number min=0.5 max=1.5 step=0.05 group=connector label="Snap grip"

// @preset id="default" label="Regular snap" connector_type=snap-regular
// @preset id="pushfit" label="Push-fit peg" connector_type=pushfit

// === Derived ===

is_snap = (connector_type == "snap-regular");

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

// snap-regular: snapConnectBacker's native z-extent is [-3.485, 3.09];
// lift its slot base to the bed (z=0), slots-down.
if (is_snap)
    translate([0, 0, 3.485])
        snapConnectBacker(offset = 0, holdingTolerance = holding_tolerance);

// pushfit: multiboard_push_fit's native z-extent is [-0.5, 6.0], narrow
// tip down / wide collar up. Mirror it collar-down (zero overhang) and
// drop min-Z to the bed.
if (!is_snap)
    translate([0, 0, 6.0])
        mirror([0, 0, 1])
            multiboard_push_fit();
