include <BOSL2/std.scad>
include <BOSL2/threading.scad>

/*
Licensed Creative Commons Attribution-ShareAlike 4.0 International

Created by mitufy. https://github.com/mitufy

openConnect is a connector system designed for openGrid. https://www.printables.com/model/1559478-openconnect-opengrids-own-connector-system
openGrid is created by David D: https://www.printables.com/model/1214361-opengrid-walldesk-mounting-framework-and-ecosystem.
Gridfinity is created by Zack Freedman. https://gridfinity.xyz/
Part of code based on Gridfinity Rebuilt: https://github.com/kennetek/gridfinity-rebuilt-openscad
*/

/* [Main Settings] */
baseplate_style = "Default"; //["Default", "Magnet - All", "Magnet - Corners Only"]
//An even number of width grids is recommended, as 2 Gridfinity cells (42mm x 2) line up with 3 openGrid cells (28mm x 3).
gridfinity_width_grids = 2;
gridfinity_depth_grids = 2;

/* [Shelf Body] */
// Front-most screwholes are omitted when they would have too little space below them.
enable_screw_connections = false;
// Defaults work for M3 and 4-40 screws.
connection_screw_diameter = 3.3; //0.1
magnet_diameter = 6.4; //0.1
magnet_thickness = 2.4; //0.1

/* [Shelf Rim] */
// Adds space between the back wall and the Gridfinity bin area.
shelf_back_offset = 0; //0.1
// Adds extra material to the left and right edges. The shelf width will no longer be an exact 42mm multiple.
shelf_side_rim = 0; //0.1
// Adds extra material to the front edge.
shelf_front_rim = 0; //0.1
// Adds a raised lip to help keep bins on the shelf. Only applies where a rim is enabled.
shelf_rim_lip_height = 0; //0.1

/* [openConnect Settings] */
//Adding locking mechanism to more slots makes the fit tighter, but also more difficult to install.
slot_lock_distribution = "Top Corners"; //["All", "Staggered", "Corners", "Top Corners", "None"]
//Entry ramp direction can matter in tight spaces.
slot_entryramp_flip = false;
//Slot alignment applies when the shelf width is not an exact multiple of 28 mm.
slot_horizontal_alignment = "Center"; //["Center", "Left", "Right"]

/* [Advanced Settings] */
// Increase this if Gridfinity bins fit too tightly.
gridfinity_socket_clearance = 0; //0.01
//Manually offset the horizontal position of the slots.
slot_horizontal_offset = 0; //0.1
//Manually offset the vertical position of the slots.
slot_vertical_offset = 0; //0.1
//Increase clearances if the slots feel too tight.
slot_side_clearance = 0.1; //0.01
slot_depth_clearance = 0.1; //0.01
//Minimum width for bridges. Default is suitable for 0.4mm nozzles, consider increasing when using a larger nozzle.
slot_edge_bridge_min_width = 0.8; //0.01
//Minimum width for walls. Default is suitable for 0.4mm nozzles, consider increasing when using a larger nozzle.
slot_edge_wall_min_width = 0.6; //0.01

/* [Hidden] */
$fa = 1;
$fs = 0.4;
// --- Begin Content of opengrid_base.scad ---

EPS = 0.005;
OG_TILE_SIZE = 28;
OG_STANDARD_THICKNESS = 6.8;
OG_LITE_THICKNESS = 4;
OG_LITE_BASIC_THICKNESS = 3.4;

OG_SNAP_WIDTH = 24.8;
OG_SNAP_CORNER_OUTER_DIAGONAL = 2.7 + 1 / sqrt(2);
OG_SNAP_CORNER_CHAMFER = OG_SNAP_CORNER_OUTER_DIAGONAL * sqrt(2);
OG_SNAP_CORNER_INNER_DIAGONAL = OG_SNAP_WIDTH * sqrt(2) / 2 - OG_SNAP_CORNER_OUTER_DIAGONAL;
OG_SNAP_TEXT_FONT = "Merriweather Sans:style=Bold";
OG_SNAP_EMOJI_FONT = "Noto Emoji";
OG_SNAP_BLUNT_TEXT = "🔓";
OG_SNAP_DIRECTIONAL_ARROW_TEXT = "🔺";

OG_SNAP_THREADS_PROFILE = [
  [-1.25 / 3, -1 / 3],
  [-0.25 / 3, 0],
  [0.25 / 3, 0],
  [1.25 / 3, -1 / 3],
];
OG_SNAP_THREADS_DIAMETER = 16;
OG_SNAP_THREADS_CLEARANCE = 0.5;
OG_SNAP_THREADS_COMPATIBILITY_ANGLE = 53.5;

OG_SNAP_THREADS_PITCH = 3;
OG_SNAP_THREADS_SIDE_OFFSET = 1.2;
OG_THREADS_CONNECT_OFFSET = 1.5;
OG_MIN_WALL_WIDTH = 0.8;

OG_SNAP_TEXT_SIZE = 4;
OG_GADGET_TEXT_SIZES = [OG_SNAP_TEXT_SIZE, OG_SNAP_TEXT_SIZE];
OG_GADGET_TEXT_FONTS = [OG_SNAP_EMOJI_FONT, OG_SNAP_TEXT_FONT];
OG_GADGET_TEXT_FILLS = [true, false];
OG_GADGET_TEXT_POSITIONS = [[2.4, 0], [-2.4, 0]];

OG_SNAP_TEXT_SIZES = [OG_SNAP_TEXT_SIZE, OG_SNAP_TEXT_SIZE, 3.6];
OG_SNAP_TEXT_FONTS = [OG_SNAP_EMOJI_FONT, OG_SNAP_TEXT_FONT, OG_SNAP_EMOJI_FONT];
OG_SNAP_TEXT_FILLS = [true, false, true];

OCHEAD_BOTTOM_HEIGHT = 0.6;
OCHEAD_TOP_HEIGHT = 0.6;
OCHEAD_MIDDLE_HEIGHT = 1.4;
OCHEAD_LARGE_RECT_WIDTH = 17;
OCHEAD_LARGE_RECT_HEIGHT = 10.6;
OCHEAD_LARGE_RECT_CHAMFER = 4;

OCHEAD_NUB_TO_TOP_DISTANCE = 7.2;
OCHEAD_NUB_DEPTH = 0.6;
OCHEAD_NUB_TIP_HEIGHT = 1.2;
OCHEAD_NUB_FILLET = 0.8;

OCHEAD_BACK_POS_OFFSET = 0.4;
OCHEAD_TOTAL_HEIGHT = OCHEAD_TOP_HEIGHT + OCHEAD_MIDDLE_HEIGHT + OCHEAD_BOTTOM_HEIGHT;
OCHEAD_MIDDLE_TO_BOTTOM = OCHEAD_LARGE_RECT_HEIGHT - OCHEAD_LARGE_RECT_WIDTH / 2 - OCHEAD_BACK_POS_OFFSET;

OCSLOT_MOVE_DISTANCE = 10.6;
OCSLOT_ONRAMP_CLEARANCE = 0.8;

FOLD_GAP_WIDTH = 0.4;
FOLD_GAP_HEIGHT = 0.2;
// ── Configuration Structs ────────────────────────────────────────────────────

// Helper function to safely merge two structs or a struct and a flat override list
function _flatten_struct(s) = [for (i = [0:len(s) - 1], j = [0:1]) s[i][j]];
function struct_merge(struct_a, struct_b) =
  len(struct_b) == 0 ? struct_a
  : is_string(struct_b[0]) ? struct_set(struct_a, struct_b)
  : struct_set(struct_a, _flatten_struct(struct_b));

function text_cfg(
  texts = [],
  sizes = OG_GADGET_TEXT_SIZES,
  fonts = OG_GADGET_TEXT_FONTS,
  fills = OG_GADGET_TEXT_FILLS,
  pos_offsets = [[0, 0]],
  text_depth = 0.4
) =
  struct_set(
    [], [
      "texts",
      texts,
      "sizes",
      sizes,
      "fonts",
      fonts,
      "fills",
      fills,
      "pos_offsets",
      pos_offsets,
      "text_depth",
      text_depth,
    ]
  );

module snap_text(
  text_cfg = [],
  snapbody_cfg = [],
  anchor = BOTTOM,
  spin = 0,
  orient = UP
) {
  _cfg = struct_merge(text_cfg(), text_cfg);
  _texts = struct_val(_cfg, "texts");
  _sizes = struct_val(_cfg, "sizes");
  _fonts = struct_val(_cfg, "fonts");
  _fills = struct_val(_cfg, "fills");
  _offsets = struct_val(_cfg, "pos_offsets");
  _depth = struct_val(_cfg, "text_depth");

  _text_count = len(_texts);
  attachable(anchor, spin, orient, size=[1, 1, max(_depth, EPS)]) {
    tag_scope() {
      if (_text_count > 0 && _depth > 0)
        down(_depth / 2)for (i = [0:_text_count - 1]) {
          if (_texts[i] != "") {
            _size = len(_sizes) > i ? _sizes[i] : _sizes[0];
            _font = len(_fonts) > i ? _fonts[i] : _fonts[0];
            _fill = len(_fills) > i ? _fills[i] : _fills[0];

            _offset = len(_offsets) > i ? _offsets[i] : _offsets[0];
            right(_offset[0]) back(_offset[1])
                linear_extrude(height=_depth + EPS) if (_fill)
                  fill() text(_texts[i], size=_size, anchor=str("center", CENTER), font=_font);
                else
                  text(_texts[i], size=_size, anchor=str("center", CENTER), font=_font);
          }
        }
    }
    children();
  }
}

// ── Utility Functions & Modules ──────────────────────────────────────────────

// Returns true if the position [hgrid, vgrid] fits the description.
function is_grid_pos_described(hgrid, vgrid, max_hgrid, max_vgrid, description, except_pos = []) =
  let (
    is_exception = in_list([hgrid, vgrid], except_pos),
    is_stagger = hgrid % 2 == vgrid % 2,
    is_top_row = vgrid == 0,
    is_bottom_row = vgrid == max_vgrid - 1,
    is_left_column = hgrid == 0,
    is_right_column = hgrid == max_hgrid - 1,
    is_edge_row = is_top_row || is_bottom_row,
    is_edge_column = is_left_column || is_right_column,
    is_corner = is_edge_row && is_edge_column,
    is_top_corner = is_corner && is_top_row,
    is_bottom_corner = is_corner && is_bottom_row,
    matches_pattern = description == "All" || (description == "Staggered" && is_stagger) || (description == "Corners" && is_corner) || (description == "Top Corners" && is_top_corner) || (description == "Bottom Corners" && is_bottom_corner) || (description == "Edge Rows" && is_edge_row) || (description == "Edge Columns" && is_edge_column)
  ) !is_exception && matches_pattern;

// Returns true if the footprint at cp lies fully within limit_region.
function is_pos_shape_in_region(cp, footprint, limit_region) =
  let (
    result = [for (i = footprint) point_in_region(cp + i, limit_region) >= 0]
  ) !in_list(list=result, val=false);

// Conditionally flips children along the given axis. If copy=true, keep the original.
module conditional_flip(axis = "X", coordinate = 0, copy = false, condition) {
  if (condition) {
    if (axis == "X")
      xflip(x=coordinate) children();
    else if (axis == "Y")
      yflip(y=coordinate) children();
    else if (axis == "Z")
      zflip(z=coordinate) children();
    if (copy)
      children();
  }
  else
    children();
}

// Conditionally cuts children to the given half-space along v.
module conditional_half(v = LEFT, pos_offset = 0, mask_size = 100, condition) {
  if (condition) {
    if (v == LEFT || v == RIGHT)
      half_of(v=v, cp=[pos_offset, 0, 0], s=mask_size) tag_scope() children();
    else if (v == FRONT || v == BACK)
      half_of(v=v, cp=[0, pos_offset, 0], s=mask_size) tag_scope() children();
    else if (v == TOP || v == BOTTOM)
      half_of(v=v, cp=[0, 0, pos_offset], s=mask_size) tag_scope() children();
    else
      half_of(v, cp=pos_offset == 0 ? [0, 0, 0] : pos_offset, s=mask_size) tag_scope() children();
  }
  else
    children();
}

module conditional_fold(body_thickness, fold_position = 0, fold_gap_width = 0.4, fold_gap_height = 0.2, fold_sliceoff = 0, mask_size = 100, condition = true) {
  if (condition) {
    back(fold_position) yrot(180) {
        xrot(-90, cp=[0, -fold_position, 0])
          difference() {
            children();
            fwd(fold_position) cuboid([mask_size, mask_size, mask_size], anchor=BACK);
          }
        fwd(fold_gap_width - EPS) up(fold_sliceoff)
            xrot(90, cp=[0, -fold_position, 0])
              difference() {
                children();
                fwd(fold_position + fold_sliceoff)
                  cuboid([mask_size, mask_size, mask_size], anchor=FRONT);
              }
        fwd(fold_gap_width) xrot(-90, cp=[0, -fold_position, 0])
            linear_extrude(fold_gap_width + EPS * 2) difference() {
                projection(cut=true)
                  down(0.01)
                    children();
                fwd(fold_position - fold_gap_height) rect([mask_size, mask_size], anchor=FRONT);
                fwd(fold_position) rect([mask_size, mask_size], anchor=BACK);
              }
      }
  }
  else
    children();
}
// --- End Content of opengrid_base.scad ---


//A slot is generated for every tile by default.
slot_position = "All"; //["All", "Staggered", "Edge Rows", "Edge Columns", "Corners"]
//BEGIN gridfinity constants
GF_PITCH = 42;
GF_BASEPLATE_LOWER_TAPER_HEIGHT = 0.7;
GF_BASEPLATE_RISER_HEIGHT = 1.8;
GF_BASEPLATE_UPPER_TAPER_HEIGHT = 2.15;
GF_BASEPLATE_PROFILE_HEIGHT = GF_BASEPLATE_LOWER_TAPER_HEIGHT + GF_BASEPLATE_RISER_HEIGHT + GF_BASEPLATE_UPPER_TAPER_HEIGHT;
GF_BASEPLATE_CLEARANCE_HEIGHT = 0.35;
GF_TOP_CORNER_RADIUS = 4;
GF_MID_INSET = GF_BASEPLATE_UPPER_TAPER_HEIGHT;
GF_BOTTOM_INSET = GF_BASEPLATE_LOWER_TAPER_HEIGHT + GF_BASEPLATE_UPPER_TAPER_HEIGHT;
GF_MID_CORNER_RADIUS = GF_TOP_CORNER_RADIUS - GF_MID_INSET;
GF_BOTTOM_CORNER_RADIUS = GF_TOP_CORNER_RADIUS - GF_BOTTOM_INSET;
GF_ATTACHMENT_BORDER = 8;
GF_ATTACHMENT_EDGE_CLEARANCE = 4;
GF_ATTACHMENT_DIAMETER = max(0, magnet_diameter);
GF_ATTACHMENT_BOSS_DIAMETER = GF_ATTACHMENT_DIAMETER + 4;
GF_MAGNET_POSITION = min(GF_PITCH / 2 - GF_ATTACHMENT_BORDER, GF_PITCH / 2 - GF_ATTACHMENT_EDGE_CLEARANCE - GF_ATTACHMENT_DIAMETER / 2);
GF_SKELETON_RAIL_WIDTH = GF_BOTTOM_INSET;
GF_SKELETON_WINDOW_SIZE = GF_PITCH - GF_SKELETON_RAIL_WIDTH * 2;
GF_ATTACHMENT_BOSS_RAIL_OVERLAP = 2.4;
GF_ATTACHMENT_WINDOW_SIZE = max(1, min(GF_SKELETON_WINDOW_SIZE, (GF_MAGNET_POSITION + GF_ATTACHMENT_BOSS_DIAMETER / 2 - GF_ATTACHMENT_BOSS_RAIL_OVERLAP) * 2));
SCREW_CONNECTION_MIN_WALL = 0.8;
//END gridfinity constants

//BEGIN openConnect parameters
slot_edge_feature_widen = "Top"; //[Both, Top, Side, None]
slot_slide_direction = "Up"; //[Left,Right,Up,Down]
slot_lock_side = "Left"; //[Left:Standard, Both:Double]

_slot_cfg = ocslot_cfg(
  edge_feature=slot_edge_feature_widen,
  edge_bridge_min_w=slot_edge_bridge_min_width,
  edge_wall_min_w=slot_edge_wall_min_width,
  side_clearance=slot_side_clearance,
  depth_clearance=slot_depth_clearance
);
//END openConnect parameters

//BEGIN shelf parameters
final_gridfinity_width_grids = max(1, floor(gridfinity_width_grids));
final_gridfinity_depth_grids = max(1, floor(gridfinity_depth_grids));
final_magnet_position =
  baseplate_style == "Magnet - All" ? "All"
  : baseplate_style == "Magnet - Corners Only" ? "Corners Only"
  : "None";
final_magnet_diameter = max(0, magnet_diameter);
final_magnet_thickness = max(0, magnet_thickness);
magnet_holes_enabled = final_magnet_position != "None" && final_magnet_diameter > 0 && final_magnet_thickness > 0;
final_baseplate_clearance_height = magnet_holes_enabled ? GF_BASEPLATE_CLEARANCE_HEIGHT : 0;
final_baseplate_height = final_baseplate_clearance_height + GF_BASEPLATE_PROFILE_HEIGHT;
final_connection_screw_diameter = max(0, connection_screw_diameter);
screw_connections_enabled = enable_screw_connections && final_connection_screw_diameter > 0;
final_shelf_base_extra_thickness =
  magnet_holes_enabled ? max(2.4, final_magnet_thickness)
  : 2.4;
final_socket_clearance = max(0, gridfinity_socket_clearance);
//Ensure the slot wall is at least 0.85 thick.
slot_backwall_filler = 0.7;
final_shelf_back_offset = max(0, shelf_back_offset) + slot_backwall_filler;
final_shelf_side_rim = max(0, shelf_side_rim);
final_shelf_front_rim = max(0, shelf_front_rim);

shelf_width = final_gridfinity_width_grids * GF_PITCH + final_shelf_side_rim * 2;
shelf_depth = final_shelf_back_offset + final_gridfinity_depth_grids * GF_PITCH + final_shelf_front_rim;
shelf_deck_height = final_shelf_base_extra_thickness + final_baseplate_height;
final_shelf_bottom_tilt_height = max(0, OG_TILE_SIZE - shelf_deck_height);

slot_h_grids = max(1, floor(shelf_width / OG_TILE_SIZE));
slot_grid_width = slot_h_grids * OG_TILE_SIZE;
slot_horizontal_alignment_offset =
  slot_horizontal_alignment == "Left" ? shelf_width - slot_grid_width
  : slot_horizontal_alignment == "Right" ? 0
  : (shelf_width - slot_grid_width) / 2;

final_shelf_rim_lip_height = max(0, shelf_rim_lip_height);
has_side_lips = final_shelf_rim_lip_height > 0 && final_shelf_side_rim > 0;
has_front_lip = final_shelf_rim_lip_height > 0 && final_shelf_front_rim > 0;
side_wall = has_side_lips ? final_shelf_side_rim : 0;
front_wall = has_front_lip ? final_shelf_front_rim : 0;
inner_width = shelf_width - side_wall * 2;
inner_depth = shelf_depth - front_wall - final_shelf_back_offset;
print_bottom_angle = final_shelf_bottom_tilt_height <= 0 ? 0 : atan(final_shelf_bottom_tilt_height / shelf_depth);

//END shelf parameters

//BEGIN generation

//END generation







  // Keeps a printable wall above the hole while the shelf wedge supplies material below.




{
// --- Begin Content of openconnect_lib.scad ---
/*
Licensed Creative Commons Attribution 4.0 International

Created by mitufy. https://github.com/mitufy

openConnect is a connector system designed for openGrid. https://www.printables.com/model/1559478-openconnect-opengrids-own-connector-system
openGrid is created by David D: https://www.printables.com/model/1214361-opengrid-walldesk-mounting-framework-and-ecosystem.
Inspired by David's multiConnect: https://www.printables.com/model/1008622-multiconnect-for-multiboard-v2-modeling-files.
*/








  // Slot heads may inset the right nub when the top bridge widens. ochead_cfg does not have this parameter.

  // bridging doesn't work well with tapered nub
  // nub_angle_right =
  //   nub_taperin && _middle_height - _nub_depth - nub_inset_right > 0 ? adj_opp_to_ang(_middle_height - nub_inset_right, _middle_height - _nub_depth - nub_inset_right)
  //   : 0;









  // Slot dimensions needed for grid sizing/placement
//END openConnect slot modules

//BEGIN openConnect connectors





{
// --- Begin Content of opengrid_threads_lib.scad ---
/*
Licensed Creative Commons Attribution 4.0 International

Created by mitufy. https://github.com/mitufy

openGrid is created by David D: https://www.printables.com/model/1214361-opengrid-walldesk-mounting-framework-and-ecosystem.
*/



// Positive threads are printed protrusions; negative threads are snap cut tools.
// Clearance belongs to negative snap threads only.

















function threads_cfg(
  threads_type = "Blunt",
  threads_diameter = OG_SNAP_THREADS_DIAMETER,
  threads_clearance = OG_SNAP_THREADS_CLEARANCE,
  threads_pitch = OG_SNAP_THREADS_PITCH,
  threads_top_bevel = 0.5,
  threads_bottom_bevel_standard = 2,
  threads_bottom_bevel_lite = 1.2,
  threads_offset_angle = 0,
  threads_blunt_cutoff = true
) =
  struct_set(
    [], [
      "threads_type",
      threads_type,
      "threads_diameter",
      threads_diameter,
      "threads_clearance",
      threads_clearance,
      "threads_pitch",
      threads_pitch,
      "threads_top_bevel",
      threads_top_bevel,
      "threads_bottom_bevel_standard",
      threads_bottom_bevel_standard,
      "threads_bottom_bevel_lite",
      threads_bottom_bevel_lite,
      "threads_offset_angle",
      threads_offset_angle,
      "threads_blunt_cutoff",
      threads_blunt_cutoff,
    ]
  );
function negative_threads_cfg(threads_cfg = []) = struct_merge(threads_cfg(), threads_cfg);
function positive_threads_cfg(threads_cfg = []) =
  struct_set(negative_threads_cfg(threads_cfg), ["threads_clearance", 0]);
function snap_expand_cfg(
  expand_distance_standard = 0.6,
  expand_distance_lite = 0.4,
  expand_entry_height_standard = 0.4,
  expand_entry_height_lite = 0.4,
  expand_entry_height_blunt = 1,
  expand_end_height_standard = 2,
  expand_end_height_lite = 1.2,
  expand_split_angle = 45
) =
  struct_set(
    [], [
      "expand_distance_standard",
      expand_distance_standard,
      "expand_distance_lite",
      expand_distance_lite,
      "expand_entry_height_standard",
      expand_entry_height_standard,
      "expand_entry_height_lite",
      expand_entry_height_lite,
      "expand_entry_height_blunt",
      expand_entry_height_blunt,
      "expand_end_height_standard",
      expand_end_height_standard,
      "expand_end_height_lite",
      expand_end_height_lite,
      "expand_split_angle",
      expand_split_angle,
    ]
  );
module blunt_threads(threads_height = OG_STANDARD_THICKNESS, top_bevel = 0, bottom_bevel = 0, blunt_ang = 10, threads_cfg = [], anchor = BOTTOM, spin = 0, orient = UP) {
  _threads_cfg = struct_merge(threads_cfg(), threads_cfg);
  _diameter = struct_val(_threads_cfg, "threads_diameter") + struct_val(_threads_cfg, "threads_clearance");
  _pitch = struct_val(_threads_cfg, "threads_pitch");
  _top_cutoff = struct_val(_threads_cfg, "threads_blunt_cutoff");

  thread_lead_in_offset = 1.5;
  min_turns = 0.5;
  thread_degrees_per_mm = 360 / _pitch;
  offset_height = min(threads_height - thread_lead_in_offset - bottom_bevel, 0);
  turns = max(0, (threads_height - thread_lead_in_offset - bottom_bevel) / _pitch) + min_turns;

  attachable(anchor, spin, orient, d=_diameter, h=threads_height) {
    tag_scope() down(threads_height / 2) diff() {
          cyl(d=_diameter - 2 + EPS, h=threads_height, anchor=BOTTOM, $fn=256);
          diff("helix_cutoff") {
            zrot(0.25 * thread_degrees_per_mm) up(0.25)
                zrot(-(min_turns * _pitch) * thread_degrees_per_mm) up(-(min_turns * _pitch))
                    zrot(offset_height * thread_degrees_per_mm) up(offset_height)
                        thread_helix(
                          d=_diameter, turns=turns, pitch=_pitch, profile=OG_SNAP_THREADS_PROFILE,
                          anchor=BOTTOM, internal=false, lead_in_ang2=blunt_ang, $fn=256
                        );
            tag("helix_cutoff") up(threads_height + (_diameter + 2) / 2) cube(_diameter + 2, center=true);
          }
          if (_top_cutoff || top_bevel > 0)
            tag("remove") down((_diameter + 2) / 2) cube(_diameter + 2, center=true);
          if (top_bevel > 0)
            force_tag("remove") rotate_extrude() left(_diameter / 2 - top_bevel / 2 + EPS) right_triangle([top_bevel + EPS, top_bevel + EPS], anchor=BOTTOM);
          if (bottom_bevel > 0)
            force_tag("remove") up(threads_height) rotate_extrude() right(_diameter / 2 - bottom_bevel + EPS) right_triangle([bottom_bevel + EPS, bottom_bevel + EPS], anchor=BOTTOM, spin=180);
        }
    children();
  }
}
module snap_threads(threads_height = OG_STANDARD_THICKNESS, threads_cfg = [], text_cfg = [], anchor = BOTTOM, spin = 0, orient = UP) {
  _threads_cfg = struct_merge(threads_cfg(), threads_cfg);
  _text_cfg = struct_merge(text_cfg(), text_cfg);
  _threads_type = struct_val(_threads_cfg, "threads_type");
  _threads_offset_angle = struct_val(_threads_cfg, "threads_offset_angle");
  _threads_blunt_cutoff = struct_val(_threads_cfg, "threads_blunt_cutoff");
  _snap_threads_top_bevel = struct_val(_threads_cfg, "threads_top_bevel");
  _snap_threads_bottom_bevel_standard = struct_val(_threads_cfg, "threads_bottom_bevel_standard");
  _snap_threads_bottom_bevel_lite = struct_val(_threads_cfg, "threads_bottom_bevel_lite");
  _threads_diameter = struct_val(_threads_cfg, "threads_diameter");
  _threads_clearance = struct_val(_threads_cfg, "threads_clearance");
  _threads_pitch = struct_val(_threads_cfg, "threads_pitch");
  _snap_threads_bottom_bevel =
    threads_height >= OG_STANDARD_THICKNESS ? _snap_threads_bottom_bevel_standard
    : threads_height >= OG_LITE_BASIC_THICKNESS ? _snap_threads_bottom_bevel_lite
    : 0;

  attachable(anchor, spin, orient, d=_threads_diameter + _threads_clearance, h=threads_height) {
    tag_scope() diff() {
        down(threads_height / 2) zrot(_threads_offset_angle + OG_SNAP_THREADS_COMPATIBILITY_ANGLE) {
            if (_threads_type == "Blunt")
              blunt_threads(threads_height=threads_height, threads_cfg=_threads_cfg);
            else
              generic_threaded_rod(d=_threads_diameter + _threads_clearance, l=threads_height, pitch=_threads_pitch, profile=OG_SNAP_THREADS_PROFILE, bevel1=_snap_threads_top_bevel, bevel2=_snap_threads_bottom_bevel, blunt_start=false, anchor=BOTTOM, internal=false);
          }
        if (struct_val(_text_cfg, "text_depth") > 0)
          up(threads_height / 2 - EPS)
            tag("remove") zrot(_threads_offset_angle)
              snap_text(text_cfg=_text_cfg, anchor=TOP);
      }

    children();
  }
}
module positive_snap_threads(threads_height = OG_STANDARD_THICKNESS, threads_cfg = [], text_cfg = [], anchor = BOTTOM, spin = 0, orient = UP) {
  snap_threads(
    threads_height=threads_height,
    threads_cfg=positive_threads_cfg(threads_cfg),
    text_cfg=text_cfg,
    anchor=anchor,
    spin=spin,
    orient=orient
  ) children();
}
module negative_snap_threads(threads_height = OG_STANDARD_THICKNESS, threads_cfg = [], text_cfg = [], anchor = BOTTOM, spin = 0, orient = UP) {
  snap_threads(
    threads_height=threads_height,
    threads_cfg=negative_threads_cfg(threads_cfg),
    text_cfg=text_cfg,
    anchor=anchor,
    spin=spin,
    orient=orient
  ) children();
}
module expanding_threads(threads_height = OG_STANDARD_THICKNESS, threads_cfg = [], text_cfg = [], expand_cfg = [], anchor = BOTTOM, spin = 0, orient = UP) {
  _expand_cfg = struct_merge(snap_expand_cfg(), expand_cfg);
  _is_standard = threads_height >= OG_STANDARD_THICKNESS;

  _threads_cfg = negative_threads_cfg(threads_cfg);
  _threads_type = struct_val(_threads_cfg, "threads_type");
  _threads_pitch = struct_val(_threads_cfg, "threads_pitch");

  _expand_distance_raw = _is_standard ? struct_val(_expand_cfg, "expand_distance_standard") : struct_val(_expand_cfg, "expand_distance_lite");
  _expand_distance = max(0, _expand_distance_raw);
  _entry_height = _threads_type == "Blunt" ? struct_val(_expand_cfg, "expand_entry_height_blunt") : (_is_standard ? struct_val(_expand_cfg, "expand_entry_height_standard") : struct_val(_expand_cfg, "expand_entry_height_lite"));
  _end_height = _is_standard ? struct_val(_expand_cfg, "expand_end_height_standard") : struct_val(_expand_cfg, "expand_end_height_lite");
  _expand_split_angle = struct_val(_expand_cfg, "expand_split_angle");

  expand_distance_step = 0.05;
  transition_height = threads_height - _entry_height - _end_height;
  expand_segment_count = _expand_distance > 0 ? ceil(_expand_distance / expand_distance_step) : 0;
  expand_height_step = expand_segment_count > 0 ? transition_height / expand_segment_count : transition_height;
  thread_degrees_per_mm = 360 / _threads_pitch;

  _no_text_cfg = ["text_depth", 0];
  _no_cutoff_cfg = ["threads_blunt_cutoff", false];
  _no_top_bevel_cfg = ["threads_top_bevel", 0];
  _no_bottom_bevel_cfg = ["threads_bottom_bevel_standard", 0, "threads_bottom_bevel_lite", 0];

  _diameter = struct_val(_threads_cfg, "threads_diameter") + struct_val(_threads_cfg, "threads_clearance");

  render() {
    attachable(anchor, spin, orient, d=_diameter, h=threads_height) {
      tag_scope() down(threads_height / 2) {
          if (_entry_height > 0)
            negative_snap_threads(threads_height=_entry_height + EPS, text_cfg=_no_text_cfg, threads_cfg=struct_merge(_threads_cfg, concat(_no_cutoff_cfg, _no_top_bevel_cfg, _no_bottom_bevel_cfg)));
          if (expand_segment_count > 0) {
            for (a = [0:expand_segment_count - 1]) {
              aseg_position = _entry_height + expand_height_step * a;
              aseg_expansion_distance = min(_expand_distance, expand_distance_step * (a + 1));
              zrot(-_expand_split_angle)
                partition(spread=-aseg_expansion_distance - EPS, cutpath="flat", $slop=aseg_expansion_distance / 2)
                  zrot(_expand_split_angle) up(aseg_position) zrot(aseg_position * thread_degrees_per_mm)
                        negative_snap_threads(threads_height=expand_height_step + EPS, text_cfg=_no_text_cfg, threads_cfg=struct_merge(_threads_cfg, concat(_no_cutoff_cfg, _no_top_bevel_cfg, _no_bottom_bevel_cfg)));
            }
          }
          else if (transition_height > 0)
            up(_entry_height) zrot(_entry_height * thread_degrees_per_mm)
              negative_snap_threads(threads_height=transition_height + EPS, text_cfg=_no_text_cfg, threads_cfg=struct_merge(_threads_cfg, concat(_no_cutoff_cfg, _no_top_bevel_cfg, _no_bottom_bevel_cfg)));
          if (_end_height > 0) {
            if (_expand_distance > 0)
              zrot(-_expand_split_angle)
                partition(spread=-_expand_distance - EPS, cutpath="flat", $slop=_expand_distance / 2)
                  zrot(_expand_split_angle) up(_entry_height + transition_height) zrot((_entry_height + transition_height) * thread_degrees_per_mm)
                        negative_snap_threads(threads_height=max(_end_height, 0) + EPS, text_cfg=_no_text_cfg, threads_cfg=struct_merge(_threads_cfg, concat(_no_cutoff_cfg, _no_top_bevel_cfg)));
            else
              up(_entry_height + transition_height) zrot((_entry_height + transition_height) * thread_degrees_per_mm)
                    negative_snap_threads(threads_height=max(_end_height, 0) + EPS, text_cfg=_no_text_cfg, threads_cfg=struct_merge(_threads_cfg, concat(_no_cutoff_cfg, _no_top_bevel_cfg)));
          }
        }
      children();
    }
  }
}
// --- End Content of opengrid_threads_lib.scad ---

}
function ochead_cfg(
  bottom_height = OCHEAD_BOTTOM_HEIGHT,
  top_height = OCHEAD_TOP_HEIGHT,
  middle_height = OCHEAD_MIDDLE_HEIGHT,
  large_rect_width = OCHEAD_LARGE_RECT_WIDTH,
  large_rect_height = OCHEAD_LARGE_RECT_HEIGHT,
  large_rect_chamfer = OCHEAD_LARGE_RECT_CHAMFER,
  nub_to_top_distance = OCHEAD_NUB_TO_TOP_DISTANCE,
  nub_depth = OCHEAD_NUB_DEPTH,
  nub_tip_height = OCHEAD_NUB_TIP_HEIGHT,
  nub_fillet = OCHEAD_NUB_FILLET,
  back_pos_offset = OCHEAD_BACK_POS_OFFSET
) =
  let (
    small_rect_width = large_rect_width - middle_height * 2,
    small_rect_height = large_rect_height - middle_height,
    small_rect_chamfer = large_rect_chamfer - middle_height + ang_adj_to_opp(45 / 2, middle_height),
    total_height = top_height + middle_height + bottom_height,
    middle_to_bottom = large_rect_height - large_rect_width / 2 - back_pos_offset,
    bottom_profile = back(large_rect_width / 2 + back_pos_offset, rect([large_rect_width, large_rect_height], chamfer=[large_rect_chamfer, large_rect_chamfer, 0, 0], anchor=BACK)),
    top_profile = back(small_rect_width / 2 + back_pos_offset, rect([small_rect_width, small_rect_height], chamfer=[small_rect_chamfer, small_rect_chamfer, 0, 0], anchor=BACK))
  ) struct_set(
    [], [
      "bottom_height",
      bottom_height,
      "top_height",
      top_height,
      "middle_height",
      middle_height,
      "large_rect_width",
      large_rect_width,
      "large_rect_height",
      large_rect_height,
      "large_rect_chamfer",
      large_rect_chamfer,
      "nub_to_top_distance",
      nub_to_top_distance,
      "nub_depth",
      nub_depth,
      "nub_tip_height",
      nub_tip_height,
      "nub_fillet",
      nub_fillet,
      "back_pos_offset",
      back_pos_offset,
      "small_rect_width",
      small_rect_width,
      "small_rect_height",
      small_rect_height,
      "small_rect_chamfer",
      small_rect_chamfer,
      "total_height",
      total_height,
      "middle_to_bottom",
      middle_to_bottom,
      "bottom_profile",
      bottom_profile,
      "top_profile",
      top_profile,
    ]
  );
function ocslot_cfg(
  edge_feature = "Both",
  edge_bridge_min_w = 0.8,
  edge_wall_min_w = 0.6,
  side_clearance = 0.10,
  depth_clearance = 0.10,
  footprint_wall = 2,
  vase_linewidth = 0.6,
  vase_overhang_angle = 45,
  head_cfg = ochead_cfg()
) =
  let (
    _head_cfg = struct_merge(ochead_cfg(), head_cfg),
    head_middle_height = struct_val(_head_cfg, "middle_height"),
    head_nub_to_top = struct_val(_head_cfg, "nub_to_top_distance"),
    head_large_rect_width = struct_val(_head_cfg, "large_rect_width"),
    head_large_rect_height = struct_val(_head_cfg, "large_rect_height"),
    head_large_rect_chamfer = struct_val(_head_cfg, "large_rect_chamfer"),
    head_small_rect_width = struct_val(_head_cfg, "small_rect_width"),
    head_small_rect_height = struct_val(_head_cfg, "small_rect_height"),
    head_small_rect_chamfer = struct_val(_head_cfg, "small_rect_chamfer"),
    head_back_pos_offset = struct_val(_head_cfg, "back_pos_offset"),
    bottom_height = struct_val(_head_cfg, "bottom_height") + ang_adj_to_opp(45 / 2, side_clearance) + depth_clearance,
    top_height = struct_val(_head_cfg, "top_height") - ang_adj_to_opp(45 / 2, side_clearance),
    total_height = top_height + head_middle_height + bottom_height,
    nub_to_top_distance = head_nub_to_top + side_clearance,
    small_rect_width = head_small_rect_width + side_clearance * 2,
    small_rect_height = head_small_rect_height + side_clearance * 2,
    small_rect_chamfer = head_small_rect_chamfer + side_clearance - ang_adj_to_opp(45 / 2, side_clearance),
    large_rect_width = head_large_rect_width + side_clearance * 2,
    large_rect_height = head_large_rect_height + side_clearance * 2,
    large_rect_chamfer = head_large_rect_chamfer + side_clearance - ang_adj_to_opp(45 / 2, side_clearance),
    middle_to_bottom = large_rect_height - large_rect_width / 2 - head_back_pos_offset,
    top_profile = back(
      small_rect_width / 2 + head_back_pos_offset,
      rect([small_rect_width, small_rect_height], chamfer=[small_rect_chamfer, small_rect_chamfer, 0, 0], anchor=BACK)
    ),
    bottom_profile = back(
      large_rect_width / 2 + head_back_pos_offset,
      rect([large_rect_width, large_rect_height], chamfer=[large_rect_chamfer, large_rect_chamfer, 0, 0], anchor=BACK)
    ),
    footprint = back(
      large_rect_width / 2 + head_back_pos_offset + footprint_wall,
      rect(
        [
          large_rect_width + footprint_wall * 2,
          large_rect_height + footprint_wall * 2,
        ],
        chamfer=[
          large_rect_chamfer + footprint_wall - ang_adj_to_opp(45 / 2, footprint_wall),
          large_rect_chamfer + footprint_wall - ang_adj_to_opp(45 / 2, footprint_wall),
          0,
          0,
        ],
        anchor=BACK
      )
    ),
    top_bridge_offset = (edge_feature == "Both" || edge_feature == "Top") ? max(0, edge_bridge_min_w - top_height) : 0,
    side_bridge_offset = (edge_feature == "Both" || edge_feature == "Side") ? max(0, edge_bridge_min_w - top_height) : 0,
    side_cliff_offset = (edge_feature == "Both" || edge_feature == "Side") ? max(0, edge_wall_min_w - top_height) : 0,
    bridge_offset_profile = right(side_bridge_offset / 2 - side_cliff_offset / 2, back(small_rect_width / 2 + head_back_pos_offset + top_bridge_offset, rect([small_rect_width + side_bridge_offset + side_cliff_offset, small_rect_height + OCSLOT_MOVE_DISTANCE + OCSLOT_ONRAMP_CLEARANCE + top_bridge_offset], chamfer=[small_rect_chamfer + top_bridge_offset + side_bridge_offset, small_rect_chamfer + top_bridge_offset + side_cliff_offset, 0, 0], anchor=BACK))),
    vase_wall_thickness = vase_linewidth * 2,
    vase_bottom_height = bottom_height + ang_adj_to_opp(45 / 2, vase_wall_thickness),
    vase_top_height = top_height - ang_adj_to_opp(45 / 2, vase_wall_thickness),
    vase_sweep_profile_base = [
      [0, 0],
      [0, vase_bottom_height],
      [min(head_middle_height, total_height - vase_bottom_height), total_height],
      [head_middle_height + vase_wall_thickness, total_height],
      [head_middle_height + vase_wall_thickness, bottom_height + head_middle_height],
      [vase_wall_thickness, bottom_height],
      [vase_wall_thickness, 0],
    ],
    vase_sweep_profile = total_height - vase_bottom_height > head_middle_height ? list_insert(vase_sweep_profile_base, 2, [head_middle_height, vase_bottom_height + head_middle_height]) : vase_sweep_profile_base
  ) struct_set(
    [], [
      "edge_feature",
      edge_feature,
      "edge_bridge_min_w",
      edge_bridge_min_w,
      "edge_wall_min_w",
      edge_wall_min_w,
      "side_clearance",
      side_clearance,
      "depth_clearance",
      depth_clearance,
      "footprint_wall",
      footprint_wall,
      "bottom_height",
      bottom_height,
      "top_height",
      top_height,
      "total_height",
      total_height,
      "nub_to_top_distance",
      nub_to_top_distance,
      "small_rect_width",
      small_rect_width,
      "small_rect_height",
      small_rect_height,
      "small_rect_chamfer",
      small_rect_chamfer,
      "large_rect_width",
      large_rect_width,
      "large_rect_height",
      large_rect_height,
      "large_rect_chamfer",
      large_rect_chamfer,
      "middle_to_bottom",
      middle_to_bottom,
      "top_profile",
      top_profile,
      "bottom_profile",
      bottom_profile,
      "footprint",
      footprint,
      "top_bridge_offset",
      top_bridge_offset,
      "side_bridge_offset",
      side_bridge_offset,
      "side_cliff_offset",
      side_cliff_offset,
      "bridge_offset_profile",
      bridge_offset_profile,
      "vase_linewidth",
      vase_linewidth,
      "vase_wall_thickness",
      vase_wall_thickness,
      "vase_bottom_height",
      vase_bottom_height,
      "vase_top_height",
      vase_top_height,
      "vase_sweep_profile",
      vase_sweep_profile,
      "vase_overhang_angle",
      vase_overhang_angle,
      "head_cfg",
      _head_cfg,
    ]
  );
function connector_slot_cfg(
  coin_slot_height = 2.6,
  coin_slot_width = 13,
  coin_slot_thickness = 2.4,
  flat_slot_height = 5,
  flat_slot_width = 6.5,
  flat_slot_height_offset = 0.7,
  flat_slot_start_thickness = 1.8,
  flat_slot_end_thickness = 1.2
) =
  let (
    coin_slot_radius = coin_slot_height / 2 + coin_slot_width ^ 2 / (8 * coin_slot_height)
  ) struct_set(
    [], [
      "coin_slot_height",
      coin_slot_height,
      "coin_slot_width",
      coin_slot_width,
      "coin_slot_thickness",
      coin_slot_thickness,
      "coin_slot_radius",
      coin_slot_radius,
      "flat_slot_height",
      flat_slot_height,
      "flat_slot_width",
      flat_slot_width,
      "flat_slot_height_offset",
      flat_slot_height_offset,
      "flat_slot_start_thickness",
      flat_slot_start_thickness,
      "flat_slot_end_thickness",
      flat_slot_end_thickness,
    ]
  );
module openconnect_head(head_type = "head", head_cfg = [], slot_cfg = [], add_nubs = "Both", nub_flattop = false, nub_taperin = true, excess_thickness = 0, size_offset = 0, anchor = BOTTOM, spin = 0, orient = UP) {
  _head_cfg = struct_merge(ochead_cfg(), head_cfg);
  cfg = head_type == "head" ? _head_cfg : struct_merge(ocslot_cfg(head_cfg=_head_cfg), slot_cfg);

  _nub_depth = struct_val(_head_cfg, "nub_depth");
  _nub_tip_height = struct_val(_head_cfg, "nub_tip_height");
  _nub_fillet = struct_val(_head_cfg, "nub_fillet");
  _middle_height = struct_val(_head_cfg, "middle_height");
  _back_pos_offset = struct_val(_head_cfg, "back_pos_offset");

  bottom_profile = struct_val(cfg, "bottom_profile");
  top_profile = struct_val(cfg, "top_profile");
  bottom_height = struct_val(cfg, "bottom_height");
  top_height = struct_val(cfg, "top_height");
  large_rect_width = struct_val(cfg, "large_rect_width");
  large_rect_height = struct_val(cfg, "large_rect_height");
  nub_to_top_distance = struct_val(cfg, "nub_to_top_distance");

  total_height = bottom_height + top_height + _middle_height;

  // Slot heads may inset the right nub when the top bridge widens. ochead_cfg does not have this parameter.
  nub_inset_right = struct_val(cfg, "side_bridge_offset", 0);

  nub_angle_left = nub_taperin ? adj_opp_to_ang(_middle_height, _middle_height - _nub_depth) : 0;
  // bridging doesn't work well with tapered nub
  // nub_angle_right =
  //   nub_taperin && _middle_height - _nub_depth - nub_inset_right > 0 ? adj_opp_to_ang(_middle_height - nub_inset_right, _middle_height - _nub_depth - nub_inset_right)
  //   : 0;

  attachable(anchor, spin, orient, size=[large_rect_width, large_rect_width, total_height]) {
    tag_scope() down(total_height / 2) difference() {
          union() {
            linear_extrude(h=bottom_height) polygon(offset(bottom_profile, delta=size_offset));
            up(bottom_height - EPS) hull() {
                up(_middle_height) linear_extrude(h=EPS) polygon(offset(top_profile, delta=size_offset));
                linear_extrude(h=EPS) polygon(offset(bottom_profile, delta=size_offset));
              }
            if (top_height + excess_thickness > 0)
              up(bottom_height + _middle_height - EPS)
                linear_extrude(h=top_height + excess_thickness + EPS) polygon(offset(top_profile, delta=size_offset));
          }
          back(large_rect_width / 2 - nub_to_top_distance + _back_pos_offset) {
            if (add_nubs == "Left" || add_nubs == "Both")
              left(large_rect_width / 2 + size_offset + EPS)
                openconnect_lock(bottom_height=bottom_height, middle_height=_middle_height, nub_depth=_nub_depth, nub_tip_height=_nub_tip_height, nub_fillet=_nub_fillet, nub_angle=nub_angle_left, nub_flattop=nub_flattop);
            if (add_nubs == "Right" || add_nubs == "Both")
              right(large_rect_width / 2 + size_offset + EPS)
                xflip() openconnect_lock(bottom_height=bottom_height, middle_height=_middle_height, nub_depth=_nub_depth, nub_tip_height=_nub_tip_height, nub_fillet=_nub_fillet, nub_angle=0, nub_flattop=nub_flattop);
          }
        }
    children();
  }
}
module openconnect_lock(bottom_height, middle_height, nub_depth = OCHEAD_NUB_DEPTH, nub_tip_height = OCHEAD_NUB_TIP_HEIGHT, nub_fillet = OCHEAD_NUB_FILLET, nub_angle = 0, nub_flattop = false) {
  right(nub_depth) zrot(-90) {
      linear_extrude(bottom_height)
        trapezoid(h=nub_depth, w2=nub_tip_height, ang=[nub_flattop ? 90 : 45, 45], rounding=[nub_fillet, nub_flattop ? 0 : nub_fillet, nub_flattop ? 0 : -nub_fillet, -nub_fillet], anchor=BACK, $fn=64);
      up(bottom_height)
        linear_extrude(v=[0, tan(nub_angle) * middle_height, middle_height])
          trapezoid(h=nub_depth, w2=nub_tip_height, ang=[nub_flattop ? 90 : 45, 45], rounding=[nub_fillet, nub_flattop ? 0 : nub_fillet, nub_flattop ? 0 : -nub_fillet, -nub_fillet], anchor=BACK, $fn=64);
    }
}
module openconnect_slot(slot_type = "slot", slot_cfg = [], add_nubs = "Left", slot_entryramp_flip = false, excess_thickness = EPS, excess_length = 0, anchor = BOTTOM, spin = 0, orient = UP) {
  cfg = struct_merge(ocslot_cfg(), slot_cfg);

  ocslot_edge_wall_min_width = struct_val(cfg, "edge_wall_min_w");

  ocslot_bottom_height = struct_val(cfg, "bottom_height");
  ocslot_top_height = struct_val(cfg, "top_height");
  ocslot_total_height = struct_val(cfg, "total_height");
  ocslot_nub_to_top_distance = struct_val(cfg, "nub_to_top_distance");
  ocslot_small_rect_width = struct_val(cfg, "small_rect_width");
  ocslot_small_rect_height = struct_val(cfg, "small_rect_height");
  ocslot_small_rect_chamfer = struct_val(cfg, "small_rect_chamfer");
  ocslot_large_rect_width = struct_val(cfg, "large_rect_width");
  ocslot_large_rect_height = struct_val(cfg, "large_rect_height");
  ocslot_large_rect_chamfer = struct_val(cfg, "large_rect_chamfer");
  ocslot_middle_to_bottom = struct_val(cfg, "middle_to_bottom");

  ocslot_top_profile = struct_val(cfg, "top_profile");
  ocslot_bottom_profile = struct_val(cfg, "bottom_profile");
  ocslot_footprint_wall = struct_val(cfg, "footprint_wall");
  ocslot_footprint = struct_val(cfg, "footprint");

  attachable(anchor, spin, orient, size=[OG_TILE_SIZE, OG_TILE_SIZE, ocslot_total_height]) {
    tag_scope() down(ocslot_total_height / 2) if (slot_type == "slot")
        conditional_flip(axis="X", condition=slot_entryramp_flip) ocslot_body(excess_thickness=excess_thickness, excess_length=excess_length);
      else if (slot_type == "vase")
        ocvase_body();
    children();
  }
  module ocvase_body(cfg = cfg) {
    ocvase_wall_thickness = struct_val(cfg, "vase_wall_thickness");
    ocvase_bottom_height = struct_val(cfg, "vase_bottom_height");
    ocvase_top_height = struct_val(cfg, "vase_top_height");
    ocvase_sweep_profile = struct_val(cfg, "vase_sweep_profile");
    ocvase_overhang_angle = struct_val(cfg, "vase_overhang_angle");
    straight_base_length = ocslot_large_rect_height - ocslot_large_rect_chamfer;
    straight_extra_length = tan(ocvase_overhang_angle) * ocslot_total_height;
    _slot_head_cfg = struct_val(cfg, "head_cfg", ochead_cfg());
    _middle_height = struct_val(_slot_head_cfg, "middle_height");
    nub_angle = adj_opp_to_ang(_middle_height, _middle_height - struct_val(_slot_head_cfg, "nub_depth"));
    sweep_corner_radius = ocvase_wall_thickness * sqrt(2);
    sweep_corner_offset = ang_adj_to_opp(45 / 2, sweep_corner_radius - ocvase_wall_thickness);
    vase_sweep_path = ["setdir", 90, "move", straight_extra_length + straight_base_length - sweep_corner_offset, "arcleft", sweep_corner_radius, 45, "move", ocslot_large_rect_chamfer * sqrt(2)];
    fwd(ocslot_middle_to_bottom + straight_extra_length)
      diff() {
        xflip_copy() right(ocvase_wall_thickness + ocslot_large_rect_width / 2) path_sweep(ocvase_sweep_profile, path=turtle(vase_sweep_path));
        if (add_nubs == "Left" || add_nubs == "Right" || add_nubs == "Both")
          conditional_flip(axis="X", copy=add_nubs == "Both", condition=add_nubs == "Right" || add_nubs == "Both")
            left(ocvase_wall_thickness + ocslot_large_rect_width / 2) back(ocslot_large_rect_height + straight_extra_length - ocslot_nub_to_top_distance) {
                _nub_depth = struct_val(_slot_head_cfg, "nub_depth");
                _nub_tip_h = struct_val(_slot_head_cfg, "nub_tip_height");
                _nub_fillet = struct_val(_slot_head_cfg, "nub_fillet");
                right(ocvase_wall_thickness)
                  openconnect_lock(bottom_height=ocslot_bottom_height, middle_height=_middle_height, nub_depth=_nub_depth, nub_tip_height=_nub_tip_h, nub_fillet=_nub_fillet, nub_angle=nub_angle);
                left(EPS)
                  tag("remove") openconnect_lock(bottom_height=ocvase_bottom_height, middle_height=_middle_height, nub_depth=_nub_depth, nub_tip_height=_nub_tip_h, nub_fillet=_nub_fillet, nub_angle=nub_angle);
              }
        xrot(90 - ocvase_overhang_angle) tag("remove") cuboid([OG_TILE_SIZE, 60, ocslot_total_height * 2], anchor=BOTTOM + FRONT);
      }
  }
  module ocslot_body(excess_thickness = 0, excess_length = 0) {
    _slot_head_cfg = struct_val(cfg, "head_cfg", ochead_cfg());
    _middle_height = struct_val(_slot_head_cfg, "middle_height");
    _back_pos_offset = struct_val(_slot_head_cfg, "back_pos_offset");
    _slot_move_distance = struct_val(_slot_head_cfg, "slot_move_distance", OCSLOT_MOVE_DISTANCE);
    _slot_onramp_clearance = struct_val(_slot_head_cfg, "slot_onramp_clearance", OCSLOT_ONRAMP_CLEARANCE);

    ocslot_bridge_offset_profile = struct_val(cfg, "bridge_offset_profile");
    ocslot_side_excess_profile = [
      [0, 0],
      [ocslot_large_rect_width / 2, 0],
      [ocslot_large_rect_width / 2, ocslot_bottom_height],
      [ocslot_small_rect_width / 2, ocslot_bottom_height + _middle_height],
      [ocslot_small_rect_width / 2, ocslot_bottom_height + _middle_height + ocslot_top_height + excess_thickness],
      [0, ocslot_bottom_height + _middle_height + ocslot_top_height + excess_thickness],
    ];
    difference() {
      union() {
        openconnect_head(head_type="slot", slot_cfg=cfg, add_nubs=add_nubs, excess_thickness=excess_thickness);
        back(_back_pos_offset) xrot(90) up(ocslot_middle_to_bottom) linear_extrude(_slot_move_distance + _slot_onramp_clearance + _back_pos_offset + excess_length) xflip_copy() polygon(ocslot_side_excess_profile);
        up(ocslot_bottom_height) linear_extrude(ocslot_top_height + _middle_height + EPS) polygon(ocslot_bridge_offset_profile);
        fwd(_slot_move_distance) {
          linear_extrude(ocslot_bottom_height + EPS) onramp_2d(excess_length=excess_length);
          up(ocslot_bottom_height)
            linear_extrude(_middle_height * sqrt(2) + EPS, v=[-1, 0, 1]) onramp_2d(excess_length=excess_length);
          left(_middle_height) up(ocslot_bottom_height + _middle_height)
              linear_extrude(ocslot_top_height + excess_thickness) onramp_2d(excess_length=excess_length);
        }
        if (excess_thickness > 0)
          fwd(ocslot_small_rect_chamfer) cuboid([ocslot_small_rect_width, ocslot_small_rect_height, ocslot_total_height + excess_thickness], anchor=BOTTOM);
      }
      if (ocslot_edge_wall_min_width - excess_length > 0)
        fwd(OG_TILE_SIZE / 2)
          cuboid([OG_TILE_SIZE, ocslot_edge_wall_min_width, ocslot_bottom_height + _middle_height + ocslot_top_height + excess_thickness + EPS], anchor=FRONT + BOTTOM);
    }
  }
  module onramp_2d(excess_length = 0) {
    _slot_head_cfg = struct_val(cfg, "head_cfg", ochead_cfg());
    _middle_height = struct_val(_slot_head_cfg, "middle_height");
    _back_pos_offset = struct_val(_slot_head_cfg, "back_pos_offset");
    _slot_onramp_clearance = struct_val(_slot_head_cfg, "slot_onramp_clearance", OCSLOT_ONRAMP_CLEARANCE);
    offset(delta=_slot_onramp_clearance)
      left(_slot_onramp_clearance + _middle_height) back(ocslot_large_rect_width / 2 + _back_pos_offset) {
          rect([ocslot_large_rect_width, ocslot_large_rect_height + excess_length], chamfer=[ocslot_large_rect_chamfer, ocslot_large_rect_chamfer, 0, 0], anchor=TOP);
          trapezoid(h=4, w1=ocslot_large_rect_width - ocslot_large_rect_chamfer * 2, ang=[45, 45], anchor=BOTTOM);
        }
  }
}
function _openconnect_slot_footprint_rotate(slot_slide_direction) =
  slot_slide_direction == "Left" ? 90
  : slot_slide_direction == "Right" ? -90
  : slot_slide_direction == "Down" ? 180
  : 0;
module openconnect_slot_grid_limit_debug(slot_cfg = [], horizontal_grids = 1, vertical_grids = 1, slot_slide_direction = "Up", excess_thickness = EPS, excess_length = 0, limit_region = [], anchor = BOTTOM, spin = 0, orient = UP) {
  cfg = struct_merge(ocslot_cfg(), slot_cfg);
  ocslot_total_height = struct_val(cfg, "total_height");
  ocslot_footprint = struct_val(cfg, "footprint");
  has_limit_region = is_region(limit_region);
  footprint_rotate = _openconnect_slot_footprint_rotate(slot_slide_direction);
  debug_z = ocslot_total_height / 2 + excess_thickness + EPS;
  debug_h = 0.04;
  attachable(anchor, spin, orient, size=[horizontal_grids * OG_TILE_SIZE, vertical_grids * OG_TILE_SIZE, ocslot_total_height]) {
    tag_scope() {
      if (has_limit_region)
        %color("blue", 0.18)
          up(debug_z)
            linear_extrude(height=debug_h)
              region(limit_region);
      for (i = [0:horizontal_grids - 1])
        for (j = [0:vertical_grids - 1]) {
          x_offset = -(horizontal_grids - i * 2 - 1) * OG_TILE_SIZE / 2;
          y_offset = (vertical_grids - j * 2 - 1) * OG_TILE_SIZE / 2;
          checked_footprint = zrot(footprint_rotate, ocslot_footprint);
          footprint_in_region = !has_limit_region || is_pos_shape_in_region(cp=[x_offset, y_offset], footprint=checked_footprint, limit_region=limit_region);
          footprint_path = [for (pt = checked_footprint) [x_offset, y_offset] + pt];
          %color(has_limit_region ? (footprint_in_region ? "green" : "red") : "orange", 0.28)
            up(debug_z + debug_h)
              linear_extrude(height=debug_h)
                polygon(footprint_path);
        }
    }
    children();
  }
}
module openconnect_slot_grid(slot_cfg = [], slot_type = "slot", horizontal_grids = 1, vertical_grids = 1, slot_slide_direction = "Up", slot_position = "All", slot_lock_distribution = "None", slot_lock_side = "Left", slot_entryramp_flip = false, excess_thickness = EPS, excess_length = 0, except_slot_pos = [], chamfer = 0, rounding = 0, limit_region = [], anchor = BOTTOM, spin = 0, orient = UP) {
  cfg = struct_merge(ocslot_cfg(), slot_cfg);
  // Slot dimensions needed for grid sizing/placement
  ocslot_total_height = struct_val(cfg, "total_height");
  ocslot_footprint = struct_val(cfg, "footprint");
  has_limit_region = is_region(limit_region);
  attachable(anchor, spin, orient, size=[horizontal_grids * OG_TILE_SIZE, vertical_grids * OG_TILE_SIZE, ocslot_total_height]) {
    grid_slot_spin = slot_slide_direction == "Left" ? -90 : slot_slide_direction == "Right" ? 90 : slot_slide_direction == "Down" ? 180 : 0;
    grid_slot_flip = slot_slide_direction == "Right" || slot_slide_direction == "Down" ? !slot_entryramp_flip : slot_entryramp_flip;
    footprint_rotate = _openconnect_slot_footprint_rotate(slot_slide_direction);
    down(ocslot_total_height / 2) tag_scope()
        intersect() {
          cuboid([horizontal_grids * OG_TILE_SIZE, vertical_grids * OG_TILE_SIZE, ocslot_total_height + excess_thickness], edges="Z", chamfer=chamfer, rounding=rounding, anchor=BOTTOM) {
            if (excess_length > 0)
              attach(FRONT, BACK)
                cuboid([horizontal_grids * OG_TILE_SIZE, excess_length, ocslot_total_height + excess_thickness], anchor=BOTTOM);
            for (i = [0:horizontal_grids - 1])
              for (j = [0:vertical_grids - 1]) {
                x_offset = -(horizontal_grids - i * 2 - 1) * OG_TILE_SIZE / 2;
                y_offset = (vertical_grids - j * 2 - 1) * OG_TILE_SIZE / 2;
                checked_footprint = zrot(footprint_rotate, ocslot_footprint);
                if (!has_limit_region || is_pos_shape_in_region(cp=[x_offset, y_offset], footprint=checked_footprint, limit_region=limit_region))
                  if (is_grid_pos_described(i, j, horizontal_grids, vertical_grids, slot_position, except_slot_pos))
                    right(x_offset) back(y_offset)
                        attach(BOTTOM, BOTTOM, inside=true, spin=grid_slot_spin)
                          tag("intersect") openconnect_slot(slot_type=slot_type, slot_cfg=slot_cfg, add_nubs=is_grid_pos_described(i, j, horizontal_grids, vertical_grids, slot_lock_distribution) ? slot_lock_side : "", slot_entryramp_flip=grid_slot_flip, excess_thickness=excess_thickness, excess_length=excess_length);
              }
          }
        }
    children();
  }
}
module openconnect_screw(threads_height = OG_STANDARD_THICKNESS, text_cfg = [], head_cfg = [], connectorslot_cfg = [], threads_cfg = [], folded = false) {
  _head_cfg = struct_merge(ochead_cfg(), head_cfg);
  _total_height = struct_val(_head_cfg, "total_height");
  _middle_to_bot = struct_val(_head_cfg, "middle_to_bottom");
  _slot_cfg = struct_merge(connector_slot_cfg(), connectorslot_cfg);

  ocfold_gap_width = FOLD_GAP_WIDTH;
  ocfold_gap_height = FOLD_GAP_HEIGHT;
  ocscrew_overhang_cyl_diameter = 15.6;

  ocscrew_coin_slot_height = struct_val(_slot_cfg, "coin_slot_height");
  ocscrew_coin_slot_width = struct_val(_slot_cfg, "coin_slot_width");
  ocscrew_coin_slot_thickness = struct_val(_slot_cfg, "coin_slot_thickness");
  ocscrew_coin_slot_radius = struct_val(_slot_cfg, "coin_slot_radius");
  ocscrew_flat_slot_height = struct_val(_slot_cfg, "flat_slot_height");
  ocscrew_flat_slot_width = struct_val(_slot_cfg, "flat_slot_width");
  ocscrew_flat_slot_height_offset = struct_val(_slot_cfg, "flat_slot_height_offset");
  ocscrew_flat_slot_start_thickness = struct_val(_slot_cfg, "flat_slot_start_thickness");
  ocscrew_flat_slot_end_thickness = struct_val(_slot_cfg, "flat_slot_end_thickness");

  _shifted_offsets = [for (p = struct_val(text_cfg, "pos_offsets", [])) [p[0], p[1] + (folded ? 2 : 0)]];
  _text_cfg_shifted = struct_set(text_cfg, ["pos_offsets", _shifted_offsets]);

  tag_scope() conditional_fold(
      body_thickness=threads_height + _total_height,
      fold_position=_middle_to_bot + EPS,
      fold_gap_width=ocfold_gap_width, fold_gap_height=ocfold_gap_height,
      fold_sliceoff=ocfold_gap_width / 2, condition=folded
    )
      up(threads_height + _total_height) xrot(180) zrot(180)
            diff() {
              up(_total_height - EPS)
                positive_snap_threads(threads_height=threads_height, threads_cfg=threads_cfg, text_cfg=_text_cfg_shifted);
              tag_intersect("") {
                tag(folded ? "keep" : "") openconnect_head(head_type="head", add_nubs="Both", head_cfg=_head_cfg);
                if (!folded)
                  tag("intersect") up(_total_height - EPS) right(0.32) back(0.45)
                          cyl(d2=ocscrew_overhang_cyl_diameter, d1=ocscrew_overhang_cyl_diameter + _total_height * 2, h=_total_height, anchor=TOP);
              }
              tag("remove") up(ocscrew_coin_slot_height) zrot(90) xrot(90)
                      cyl(r=ocscrew_coin_slot_radius, h=ocscrew_coin_slot_thickness, $fn=128, anchor=BACK) {
                        fwd(ocscrew_flat_slot_height_offset)
                          attach(BACK, BOTTOM)
                            prismoid(
                              size1=[ocscrew_flat_slot_width, ocscrew_flat_slot_start_thickness],
                              size2=[undef, ocscrew_flat_slot_end_thickness],
                              h=ocscrew_flat_slot_height - ocscrew_coin_slot_height + ocscrew_flat_slot_height_offset,
                              xang=[90, 90]
                            );
                        left(ocscrew_coin_slot_width / 2)
                          attach(BACK, BACK, inside=true)
                            cuboid([ocscrew_coin_slot_width, ocscrew_coin_slot_radius, ocscrew_coin_slot_thickness]);
                      }
            }
}
// --- End Content of openconnect_lib.scad ---

}
right(shelf_width) zrot(180)
    difference() {
      xrot(-print_bottom_angle) up(final_shelf_bottom_tilt_height)
          tag_diff(tag="", remove="rm1")
            cuboid([shelf_width, shelf_depth, shelf_deck_height], rounding=GF_TOP_CORNER_RADIUS, edges=[BACK + LEFT, BACK + RIGHT], anchor=FRONT + LEFT + BOTTOM) {
              back((final_shelf_back_offset - final_shelf_front_rim) / 2) down(shelf_deck_height / 2 - final_shelf_base_extra_thickness)
                  force_tag("rm1") gridfinity_baseplate_cutouts();
              if (has_side_lips || has_front_lip)
                tag_diff(tag="", remove="rm0") {
                  attach(TOP, BOTTOM)
                    cuboid([shelf_width, shelf_depth, final_shelf_rim_lip_height], rounding=GF_TOP_CORNER_RADIUS, edges=[BACK + LEFT, BACK + RIGHT])
                      back(final_shelf_back_offset) attach(TOP, TOP, align=FRONT, inside=true)
                          tag("rm0") cuboid([inner_width, inner_depth, final_shelf_rim_lip_height + EPS], rounding=GF_TOP_CORNER_RADIUS, edges=has_side_lips && has_front_lip ? "Z" : has_front_lip ? [BACK + LEFT, BACK + RIGHT] : []);
                }
              if (final_shelf_bottom_tilt_height > 0)
                shelf_tilted_bottom();
            }
      xrot(90 - print_bottom_angle) right(slot_horizontal_alignment_offset + slot_horizontal_offset) back(slot_vertical_offset)
            openconnect_slot_grid(slot_cfg=_slot_cfg, slot_type="slot", horizontal_grids=slot_h_grids, vertical_grids=1, slot_position=slot_position, slot_lock_distribution=slot_lock_distribution, slot_lock_side=slot_lock_side, slot_entryramp_flip=slot_entryramp_flip, slot_slide_direction=slot_slide_direction, excess_thickness=EPS, excess_length=4, anchor=TOP + FRONT + LEFT);
    }

module shelf_tilted_bottom() {
  ztop = -shelf_deck_height / 2 + EPS;
  zback = ztop - final_shelf_bottom_tilt_height;
  bottom_mask_height = final_shelf_bottom_tilt_height + EPS * 4;

  intersection() {
    hull() {
      up(ztop)
        cuboid([shelf_width, shelf_depth, EPS], anchor=TOP);
      fwd(shelf_depth / 2) up(zback)
          cuboid([shelf_width, EPS, EPS], anchor=BOTTOM);
      back(shelf_depth / 2) up(ztop)
          cuboid([shelf_width, EPS, EPS], anchor=BOTTOM);
    }
    up(ztop - final_shelf_bottom_tilt_height / 2)
      cuboid([shelf_width, shelf_depth, bottom_mask_height], rounding=GF_TOP_CORNER_RADIUS, edges=[BACK + LEFT, BACK + RIGHT]);
  }
}
module gridfinity_baseplate_cutouts() {
  grid_copies(spacing=[GF_PITCH, GF_PITCH], n=[final_gridfinity_width_grids, final_gridfinity_depth_grids])
    gridfinity_socket_cutout();
  if (final_shelf_base_extra_thickness + final_shelf_bottom_tilt_height > 0)
    baseplate_window_cutouts();
  if (magnet_holes_enabled)
    magnet_position_copies()
      cyl(d=final_magnet_diameter, h=final_magnet_thickness, $fn=128, anchor=TOP);
  if (screw_connections_enabled)
    screw_connection_cutouts();
}
module baseplate_window_cutouts() {
  window_size = magnet_holes_enabled ? GF_ATTACHMENT_WINDOW_SIZE : GF_SKELETON_WINDOW_SIZE;
  down(final_shelf_base_extra_thickness + final_shelf_bottom_tilt_height + EPS)
    linear_extrude(height=final_shelf_base_extra_thickness + final_shelf_bottom_tilt_height + EPS * 2)
      difference() {
        grid_copies(spacing=[GF_PITCH, GF_PITCH], n=[final_gridfinity_width_grids, final_gridfinity_depth_grids])
          rect([window_size, window_size], rounding=GF_BOTTOM_CORNER_RADIUS, $fn=64);
        if (magnet_holes_enabled)
          magnet_position_copies()
            circle(d=GF_ATTACHMENT_BOSS_DIAMETER, $fn=128);
      }
}
module magnet_position_copies() {
  corner_spacing = [
    (final_gridfinity_width_grids - 1) * GF_PITCH + GF_MAGNET_POSITION * 2,
    (final_gridfinity_depth_grids - 1) * GF_PITCH + GF_MAGNET_POSITION * 2,
  ];

  if (final_magnet_position == "All")
    grid_copies(spacing=[GF_PITCH, GF_PITCH], n=[final_gridfinity_width_grids, final_gridfinity_depth_grids])
      grid_copies(spacing=[GF_MAGNET_POSITION * 2, GF_MAGNET_POSITION * 2], n=[2, 2])
        children();
  else if (final_magnet_position == "Corners Only")
    grid_copies(spacing=corner_spacing, n=[2, 2])
      children();
}
module screw_connection_cutouts() {
  hole_radius = final_connection_screw_diameter / 2;
  // Keeps a printable wall above the hole while the shelf wedge supplies material below.
  hole_z = -(hole_radius + SCREW_CONNECTION_MIN_WALL);
  hole_depth = GF_PITCH / 2;
  grid_front_y = final_gridfinity_depth_grids * GF_PITCH / 2 + final_shelf_front_rim;

  for (x = [-shelf_width / 2, shelf_width / 2])
    for (grid_y = [0:final_gridfinity_depth_grids - 1])
      let(
        hole_y = (grid_y - (final_gridfinity_depth_grids - 1) / 2) * GF_PITCH,
        hole_tilt_height = final_shelf_bottom_tilt_height * (grid_front_y - hole_y) / shelf_depth,
        hole_center_to_bottom = (final_shelf_base_extra_thickness + hole_tilt_height + hole_z) * cos(print_bottom_angle),
        hole_bottom_wall = hole_center_to_bottom - hole_radius
      )
      if (hole_bottom_wall >= SCREW_CONNECTION_MIN_WALL)
        translate([
          x,
          hole_y,
          hole_z,
        ])
          rotate([0, 90, 0])
            cylinder(h=hole_depth, d=final_connection_screw_diameter, center=true, $fn=64);
}
module gridfinity_socket_cutout() {
  top_size = min(GF_PITCH + 0.2, GF_PITCH + final_socket_clearance);
  mid_size = max(1, top_size - GF_MID_INSET * 2);
  bottom_size = max(1, top_size - GF_BOTTOM_INSET * 2);
  top_radius = max(0.1, GF_TOP_CORNER_RADIUS);
  mid_radius = max(0.1, GF_MID_CORNER_RADIUS);
  bottom_radius = max(0.1, GF_BOTTOM_CORNER_RADIUS);

  linear_extrude(height=final_baseplate_clearance_height + EPS)
    rect([bottom_size, bottom_size], rounding=bottom_radius, $fn=128);
  hull() {
    up(final_baseplate_clearance_height)
      linear_extrude(height=EPS)
        rect([bottom_size, bottom_size], rounding=bottom_radius, $fn=128);
    up(final_baseplate_clearance_height + GF_BASEPLATE_LOWER_TAPER_HEIGHT)
      linear_extrude(height=EPS)
        rect([mid_size, mid_size], rounding=mid_radius, $fn=128);
  }
  up(final_baseplate_clearance_height + GF_BASEPLATE_LOWER_TAPER_HEIGHT - EPS)
    linear_extrude(height=GF_BASEPLATE_RISER_HEIGHT + EPS * 2)
      rect([mid_size, mid_size], rounding=mid_radius, $fn=128);
  hull() {
    up(final_baseplate_clearance_height + GF_BASEPLATE_LOWER_TAPER_HEIGHT + GF_BASEPLATE_RISER_HEIGHT)
      linear_extrude(height=EPS)
        rect([mid_size, mid_size], rounding=mid_radius, $fn=128);
    up(final_baseplate_height + EPS)
      linear_extrude(height=EPS)
        rect([top_size, top_size], rounding=top_radius, $fn=128);
  }
}
