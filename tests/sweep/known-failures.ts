// Sweep cases that already failed on main when the param-sweep guard
// first ran (st-7x7 discovery sweep, 2026-07-03). Each is a
// pre-existing model bug at a param extreme — tracked by the referenced
// bead, skipped here so the guard gates NEW regressions without
// blocking on old debt. Remove entries as their beads close; the case
// then re-arms itself.
//
// Shape: stem -> { sweep case label -> "bead-id: one-line reason" }.

export const KNOWN_FAILURES: Record<string, Record<string, string>> = {
  aquor_bib_drip_deflector: {
    "bib_plate_width=90": "st-dlu: renders 3 disjoint components (geometry degenerates)",
    "width=50": "st-dlu: renders 3 disjoint components (geometry degenerates)",
  },
  blu_black_tank_valve_mount: {
    "hex_ftf_left=15": "st-ti3: openscad exit=1 (BOSL2 assertion)",
    "saddle_w=5": "st-ti3: openscad exit=1 (BOSL2 assertion)",
    "wall_t=2": "st-ti3: openscad exit=1 (BOSL2 assertion)",
    "hex_ftf_right=60": "st-ti3: assembly splits to 4 components (expected 3)",
    "fitting_gap=120": "st-ti3: assembly splits to 5 components (expected 3)",
    "handle_excl_r=40": "st-ti3: assembly splits to 5 components (expected 3)",
  },
  blu_flow_meter_mount_80mm: {
    "pipe_dia=60": "st-38y: openscad exit=1 (BOSL2 assertion)",
    "saddle_w=17.5": "st-38y: openscad exit=1 (BOSL2 assertion)",
    "wall_t=5": "st-38y: openscad exit=1 (BOSL2 assertion)",
    "base_d=30": "st-38y: openscad exit=1 (BOSL2 assertion)",
    "edge_round_r=5": "st-38y: openscad exit=1 (BOSL2 assertion)",
    "bolt_y_offset=15": "st-38y: openscad exit=1 (BOSL2 assertion)",
    "base_w=40": "st-38y: assembly splits to 5 components (expected 3)",
    "pipe_len=120": "st-38y: assembly splits to 5 components (expected 3)",
    "pipe_len=200": "st-38y: assembly splits to 5 components (expected 3)",
  },
  cylindrical_holder_slot: {
    "cup_depth=0": "st-1us: BOSL2 assertion (transforms.scad:1440) at zero depth",
  },
  spraycan_carrier_6x50mm: {
    "base_thickness=1.5": "st-9hn: BOSL2 rounding-too-large assertion",
    "fillet_r=5": "st-9hn: BOSL2 rounding-too-large assertion",
    "handle_post_d=30": "st-9hn: rotate_extrude X-coordinate-sign error",
  },
};
