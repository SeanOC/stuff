include <BOSL2/walls.scad>
include <BOSL2/std.scad>
include <BOSL2/threading.scad>

/*
Licensed Creative Commons Attribution-ShareAlike 4.0 International

Created by mitufy. https://github.com/mitufy

openConnect is a connector system designed for openGrid. https://www.printables.com/model/1559478-openconnect-opengrids-own-connector-system
openGrid is created by David D: https://www.printables.com/model/1214361-opengrid-walldesk-mounting-framework-and-ecosystem.
*/

generate_drawer_shell = true;
generate_drawer_container = true;

/*[Drawer Size]*/
vertical_grids = 2;
horizontal_grids = 5;
depth_grids = 5;

/*[Shell Main Settings]*/
//"Back" for wall-mounted drawers. "Top" for underdesk drawers. Other options are niche and not commonly used.
shell_slot_position = "Back"; //["Back", "Top", "Bottom", "Left", "Right"]
shell_top_wall_type = "Solid"; //["Solid","Honeycomb"]
shell_bottom_wall_type = "Honeycomb"; //["Solid","Honeycomb"]
shell_side_wall_type = "Solid"; //["Solid","Honeycomb"]
//Note that changing shell dimensions would also change container size.
shell_thickness = 2.4; //0.1
shell_outer_chamfer = 2; //0.1

/*[Container Main Settings]*/
container_front_wall_type = "Honeycomb"; //["Solid","Honeycomb"]
container_back_wall_type = "Solid"; //["Solid","Honeycomb"]
//Honeycomb patterns on the side of shell and container do not align. To avoid an inconsistent see-through look, use honeycomb on only one of the two parts.
container_side_wall_type = "Honeycomb"; //["Solid","Honeycomb"]
container_solid_wall_thickness = 1.6;
container_honeycomb_wall_thickness = 2; //0.1
//How much lower the back and side walls are compared to the front. "stopper_clip_length" needs to be larger than this value to work.
container_back_side_height_offset = 3; //0.1
container_inner_fillet = 2; //0.1

/*[Shell Divider]*/
//Divide the drawer shell into several compartments. "Height" stacks drawers vertically. "Width" places them side-by-side.
add_shell_divider = "None"; //["None","Width","Height","Both"]
shell_divider_wall_type = "Honeycomb"; //["Solid","Honeycomb"]
//Compartment sizes by openGrid tiles, separated by commas.
shell_height_compartment_list = "2,3";
//Compartment sizes also correspond to the size of each container, which needs to be generated separately.
shell_width_compartment_list = "3,3";

/*[Container Divider]*/
//Divide the drawer container into several compartments.
add_container_divider = "None"; //["None","Width","Depth","Both"]
container_divider_wall_thickness = 1.2;
//Difference between the height of divider walls and side walls. Increase this value to make the dividers shorter.
container_divider_wall_height_offset = 10;
//Container compartment's unit size is its inner space divided by grid_count.
container_width_grid_count = 3;
//Compartment sizes separated by commas.
container_width_compartment_list = "1,1,1";
//Example 1: width_grid_count="3", width_compartment_list="1,1,1" - container divided into three compartments, each 1\3rd of the total width.
container_depth_grid_count = 5;
//Example 2: depth_grid_count="5", depth_compartment_list="2,3" - container divided into 2 compartments, the first is 2\5ths of the depth, the second 3\5ths.
container_depth_compartment_list = "2,3";

/*[Label and Handle]*/
add_label_holder = true;
//Default label size is recommended for honeycomb front wall. Solid front wall can have larger labels.
label_width = 48;
label_height = 10;
label_thickness = 1; //0.1
handle_thickness = 2.4; //0.1
//How much the handle protrudes from the front of the drawer container.
handle_depth = 12;

/*[Stopper Settings]*/
//Simple drawer stoppers, preventing the container from sliding all the way out.
generate_drawer_stopper_clips = false;
add_stopper_holes = true;
//Increase this value if the clips are meant for walls in a vertically divided drawer shell.
stopper_clip_length = 6;
//Determine how much the container pulls out before the stoppers engage.
stopper_edge_distance = 3; //0.1

/*[Magnet Settings]*/
//Back magnets hold the container securely when it's pushed in.
add_back_magnet_holes = true;
shell_back_magnet_thickness = 2; //0.1
container_back_magnet_thickness = 1; //0.1
back_magnet_diameter = 6; //0.1
//Side magnets act as stoppers by holding the container when it's pulled out.
add_side_magnet_holes = true;
//If wall thickness is not enough for magnets, small "bulges" will be added.
shell_side_magnet_thickness = 1; //0.1
container_side_magnet_thickness = 1; //0.1
side_magnet_diameter = 6; //0.1
//Below values determine how much the container pulls out before the side magnets engage.
shell_side_magnet_edge_distance = 6; //0.1
container_side_magnet_edge_distance = 6; //0.1

/* [openConnect Settings] */
//Adding locking mechanism to more slots makes the fit tighter, but also more difficult to install.
slot_lock_distribution = "Top Corners"; //["All", "Staggered", "Corners", "Top Corners", "None"]
//Entry ramp direction can matter in tight spaces.
slot_entryramp_flip = false;
//A slot is generated for every tile by default. Fewer slots mean more surface area, which improves bed adhesion.
slot_position = "All"; //["All", "Staggered", "Edge Rows", "Edge Columns", "Corners"]

/*[Advanced Drawer Settings]*/
container_height_clearance = 0.4; //0.05
container_width_clearance = 0.3; //0.05
container_depth_clearance = 0.4; //0.05
stopper_width_clearance = 0.2; //0.1
stopper_height_clearance = 0.2; //0.1
shell_to_slot_wall_thickness = 0.9; //0.1
//The thickness of the strut of honeycomb pattern.
honeycomb_strut_hyp = 5; //0.1

/*[Advanced openConnect Settings]*/
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

/*[Hidden]*/
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

$fa = 1;
$fs = 0.4;

shell_inner_chamfer = max(0, calc_inner_chamfer(shell_outer_chamfer, shell_thickness));
container_outer_chamfer = shell_inner_chamfer;
container_divider_wall_fillet = container_inner_fillet;
container_inner_bottom_fillet = container_inner_fillet;
container_inner_side_fillet = container_inner_fillet;
container_bottom_wall_type = "Solid"; //["Solid","Honeycomb"]
container_back_magnet_hole_position = "Bottom Corners"; //["All","Corners","Bottom Corners"]

view_cross_section = "None"; //["None","Right","Back","Diagonal"]
view_drawer_overlapped = false;
//Ensures minimum feature width for printing. "Both" is default for compatibility, though only one (or none) may be needed depending on orientation.
slot_edge_feature_widen = shell_slot_position == "Back" ? "None" : "Side";

_slot_cfg = ocslot_cfg(
  edge_feature=slot_edge_feature_widen,
  edge_bridge_min_w=slot_edge_bridge_min_width,
  edge_wall_min_w=slot_edge_wall_min_width,
  side_clearance=slot_side_clearance,
  depth_clearance=slot_depth_clearance
);

magnet_hole_side_clearance = 0.2;
magnet_hole_depth_clearance = 0.15;

//shell parameters
shell_ocslot_part_thickness = struct_val(_slot_cfg, "total_height") + shell_to_slot_wall_thickness;
shell_width = horizontal_grids * OG_TILE_SIZE + (shell_slot_position == "Left" || shell_slot_position == "Right" ? shell_ocslot_part_thickness - shell_thickness : 0);
shell_height = vertical_grids * OG_TILE_SIZE + (shell_slot_position == "Top" || shell_slot_position == "Bottom" ? shell_ocslot_part_thickness - shell_thickness : 0);
shell_depth = depth_grids * OG_TILE_SIZE;
shell_inner_width = horizontal_grids * OG_TILE_SIZE - shell_thickness * 2;
shell_inner_height = vertical_grids * OG_TILE_SIZE - shell_thickness * 2;
shell_inner_depth = depth_grids * OG_TILE_SIZE - shell_ocslot_part_thickness;
//hexwall size is calculated so outer strut overlap with shell wall
shell_hexwall_width = shell_width - shell_inner_chamfer * 2;
shell_hexwall_height = shell_height - shell_inner_chamfer * 2;
shell_hexwall_depth = shell_depth + shell_thickness - shell_ocslot_part_thickness;

//shell divider parameter
shell_height_divide_strs = str_split(str_strip(str_replace_char(shell_height_compartment_list, " ", ","), ","), ",");
shell_height_divide_nums = [for (i = [0:len(shell_height_divide_strs) - 1]) parse_num(shell_height_divide_strs[i])];
shell_height_divide_cumnums = add_shell_divider == "Height" || add_shell_divider == "Both" ? [for (i = cumsum(shell_height_divide_nums)) if (i < vertical_grids) i] : [vertical_grids];
shell_height_divide_tmp =
  len(shell_height_divide_cumnums) == 0 ? []
  : slice(shell_height_divide_nums, 0, len(shell_height_divide_cumnums) - 1);
shell_height_divide_list =
  len(shell_height_divide_cumnums) == 0 ? [vertical_grids]
  : last(shell_height_divide_cumnums) == vertical_grids ? shell_height_divide_tmp
  : concat(shell_height_divide_tmp, [vertical_grids - last(shell_height_divide_cumnums)]);
shell_vertical_compartments = add_shell_divider == "Height" || add_shell_divider == "Both" ? shell_height_divide_list : [vertical_grids];

shell_width_divide_strs = str_split(str_strip(str_replace_char(shell_width_compartment_list, " ", ","), ","), ",");
shell_width_divide_nums = [for (i = [0:len(shell_width_divide_strs) - 1]) parse_num(shell_width_divide_strs[i])];
shell_width_divide_cumnums = add_shell_divider == "Width" || add_shell_divider == "Both" ? [for (i = cumsum(shell_width_divide_nums)) if (i < horizontal_grids) i] : [horizontal_grids];
shell_width_divide_tmp =
  len(shell_width_divide_cumnums) == 0 ? []
  : slice(shell_width_divide_nums, 0, len(shell_width_divide_cumnums) - 1);
shell_width_divide_list =
  len(shell_width_divide_cumnums) == 0 ? [horizontal_grids]
  : last(shell_width_divide_cumnums) == horizontal_grids ? shell_width_divide_tmp
  : concat(shell_width_divide_tmp, [horizontal_grids - last(shell_width_divide_cumnums)]);
shell_horizontal_compartments = add_shell_divider == "Width" || add_shell_divider == "Both" ? shell_width_divide_list : [horizontal_grids];

//container parameters
container_width = shell_inner_width - container_width_clearance * 2;
container_height = shell_inner_height - container_height_clearance * 2;
container_depth = shell_inner_depth - container_depth_clearance;
container_front_wall_thickness = container_front_wall_type == "Solid" ? container_solid_wall_thickness : container_honeycomb_wall_thickness;
container_bottom_wall_thickness = container_bottom_wall_type == "Solid" ? container_solid_wall_thickness : container_honeycomb_wall_thickness;
container_side_wall_thickness = container_side_wall_type == "Solid" ? container_solid_wall_thickness : container_honeycomb_wall_thickness;
container_back_wall_thickness = container_back_wall_type == "Solid" ? container_solid_wall_thickness : container_honeycomb_wall_thickness;
container_back_wall_height = container_height - container_back_side_height_offset;
container_side_wall_height = container_back_wall_height - container_outer_chamfer;
container_divider_wall_height = container_side_wall_height - container_divider_wall_height_offset;


//hexwall parameters
honeycomb_unit_space_adj = 14;
honeycomb_unit_space_hyp = ang_adj_to_hyp(30, honeycomb_unit_space_adj);
honeycomb_strut_adj = ang_hyp_to_adj(30, honeycomb_strut_hyp);
hex_ir = (honeycomb_unit_space_hyp - honeycomb_strut_adj) / 2;
hex_or = hex_ir * 2 / sqrt(3);
fronthex_width_struts = floor(container_width / honeycomb_unit_space_adj);
fronthex_width = fronthex_width_struts * honeycomb_unit_space_adj;
//height struts is round to nearest 0.5
fronthex_height_struts = floor(container_height / honeycomb_unit_space_hyp * 2) / 2;
fronthex_height = fronthex_height_struts * honeycomb_unit_space_hyp;
fronthex_height_offset = (container_height - fronthex_height) / 2;
fronthex_bottom_strut_height = honeycomb_unit_space_hyp / 2 + honeycomb_strut_adj / 2 + fronthex_height_offset - honeycomb_strut_adj;
height_adj_to_width_opp = ang_adj_to_opp(30, abs(fronthex_height_offset));
//this is a magic number because I don't want to calculate hexagon anymore
hex_hole_fill_edge = 3;
shell_hex_frame_thickness = honeycomb_strut_adj;
container_top_frame_thickness = honeycomb_strut_adj;

stopper_width = 4.8;
stopper_height = 2.4;
stopper_rounding = 0.4;
stopper_flank_width = 2;
stopper_flank_depth = 0.8;
//when set to 0, the center of the stopper is 14mm to the edge of the drawer.
stopper_to_edge_offset = 0;

handle_chamfer = 0.4;

//magnet parameters
shell_back_magnet_hole_thickness = shell_back_magnet_thickness + magnet_hole_depth_clearance;
container_back_magnet_hole_thickness = container_back_magnet_thickness + magnet_hole_depth_clearance;
back_magnet_hole_diameter = back_magnet_diameter + magnet_hole_side_clearance * 2;
back_magnet_ocslot_offset = 4.6;
back_magnet_grid_space =
  container_back_magnet_hole_position == "Corners" ? [OG_TILE_SIZE * (horizontal_grids - 2), OG_TILE_SIZE * (vertical_grids - 1)]
  : container_back_magnet_hole_position == "Bottom Corners" ? [OG_TILE_SIZE * (horizontal_grids - 2), OG_TILE_SIZE * (vertical_grids - 1)]
  : [OG_TILE_SIZE, OG_TILE_SIZE];
back_magnet_grid_count =
  container_back_magnet_hole_position == "Corners" ? [min(horizontal_grids - 1, 2), min(vertical_grids, 2)]
  : container_back_magnet_hole_position == "Bottom Corners" ? [min(horizontal_grids - 1, 2), 1]
  : [horizontal_grids - 1, vertical_grids];

shell_side_magnet_hole_thickness = shell_side_magnet_thickness + magnet_hole_depth_clearance;
container_side_magnet_hole_thickness = container_side_magnet_thickness + magnet_hole_depth_clearance;
side_magnet_hole_diameter = side_magnet_diameter + magnet_hole_side_clearance * 2;

//BEGIN generation
half_of_anchor =
  view_cross_section == "Right" ? RIGHT
  : view_cross_section == "Back" ? BACK
  : view_cross_section == "Diagonal" ? RIGHT + BACK
  : 0;

//END generation

            //left wall
            //right wall
            //top wall
            //bottom wall
            //openconnect slot
          //front wall
          //back wall
          //side walls
          //bottom wall








  //Calculate honeycomb pattern so I can align the stem of the handle in a way that looks natural. I'm pretty sure some of the calculations are redundant, but I cannot improve the code because I forgot how they work an hour after typing them.






  //middle truss




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
assert(vertical_grids > 0 && horizontal_grids > 0 && depth_grids > 0, "drawer grid counts must be greater than 0");
assert(shell_thickness > 0, "shell_thickness must be greater than 0");
assert(shell_inner_width > 0 && shell_inner_height > 0 && shell_inner_depth > 0,
  "shell inner dimensions must be greater than 0; increase grid counts or reduce shell_thickness/shell_to_slot_wall_thickness");
assert(container_width > 0 && container_height > 0 && container_depth > 0,
  "container dimensions must be greater than 0; reduce clearances or increase drawer size");
assert(container_width - container_side_wall_thickness * 2 > 0 &&
    container_height - container_bottom_wall_thickness > 0 &&
    container_depth - container_back_wall_thickness - container_front_wall_thickness > 0,
  "container inner dimensions must be greater than 0; reduce wall thicknesses or increase drawer size");
conditional_half(v=half_of_anchor, condition=half_of_anchor != 0) {
  if (generate_drawer_shell)
    down(view_drawer_overlapped ? shell_ocslot_part_thickness : 0)
      back(shell_slot_position == "Top" ? (shell_ocslot_part_thickness - shell_thickness) / 2 : shell_slot_position == "Bottom" ? -(shell_ocslot_part_thickness - shell_thickness) / 2 : 0)
        left(shell_slot_position == "Left" ? (shell_ocslot_part_thickness - shell_thickness) / 2 : shell_slot_position == "Right" ? -(shell_ocslot_part_thickness - shell_thickness) / 2 : 0)
          drawer_shell();
  if (generate_drawer_container && !(generate_drawer_shell && add_shell_divider != "None"))
    fwd(view_drawer_overlapped || !generate_drawer_shell ? 0 : vertical_grids * OG_TILE_SIZE / 2 + 10)
      up(view_drawer_overlapped ? container_depth_clearance : container_height / 2)
        xrot(view_drawer_overlapped ? 0 : 90)
          drawer_container();
  if (generate_drawer_stopper_clips)
    right(generate_drawer_shell ? horizontal_grids * OG_TILE_SIZE / 2 + 10 : 0) up((stopper_height - stopper_height_clearance * 2) / 2)
        xrot(-90) {
          drawer_stopper(hole_excess=shell_thickness);
          right(OG_TILE_SIZE)
            drawer_stopper();
        }
}

function calc_inner_chamfer(outer_chamfer, wall_thickness) = (outer_chamfer / sqrt(2) + wall_thickness - wall_thickness * sqrt(2)) * sqrt(2);
module drawer_shell() {
  difference() {
    intersection() {
      diff(remove="rm_outer", keep="") diff(keep="keep rm_outer") {
          cuboid([shell_width, shell_height, shell_depth], anchor=BOTTOM) {
            shell_inner_cut_align =
              shell_slot_position == "Bottom" ? BACK
              : shell_slot_position == "Top" ? FRONT
              : shell_slot_position == "Left" ? RIGHT
              : shell_slot_position == "Right" ? LEFT : CENTER;
            left_hc = shell_side_wall_type == "Honeycomb" && shell_slot_position != "Left";
            right_hc = shell_side_wall_type == "Honeycomb" && shell_slot_position != "Right";
            top_hc = shell_top_wall_type == "Honeycomb" && shell_slot_position != "Top";
            bottom_hc = shell_bottom_wall_type == "Honeycomb" && shell_slot_position != "Bottom";
            attach(TOP, TOP, align=shell_inner_cut_align, inset=shell_thickness, inside=true)
              tag("remove") cuboid([shell_inner_width, shell_inner_height, shell_inner_depth], edges="Z", chamfer=shell_inner_chamfer);
            //left wall
            if (left_hc)
              attach(TOP, RIGHT, align=LEFT, inside=true, spin=90)
                tag("keep") hex_panel([shell_hexwall_depth, shell_hexwall_height, shell_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=shell_hex_frame_thickness);
            attach(TOP, TOP, align=LEFT, inside=true)
              tag(left_hc ? "remove" : "keep") cuboid([shell_thickness + (left_hc ? EPS : 0), shell_inner_height - shell_inner_chamfer * 2, shell_inner_depth]);
            //right wall
            if (right_hc)
              attach(TOP, RIGHT, align=RIGHT, inside=true, spin=90)
                tag("keep") hex_panel([shell_hexwall_depth, shell_hexwall_height, shell_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=shell_hex_frame_thickness);
            attach(TOP, TOP, align=RIGHT, inside=true)
              tag(right_hc ? "remove" : "keep") cuboid([shell_thickness + (right_hc ? EPS : 0), shell_inner_height - shell_inner_chamfer * 2, shell_inner_depth]);
            //top wall
            if (top_hc)
              attach(TOP, RIGHT, align=BACK, inside=true)
                tag("keep") hex_panel([shell_hexwall_depth, shell_hexwall_width, shell_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=shell_hex_frame_thickness);
            if (add_stopper_holes)
             attach(BACK, BACK, align=TOP, inside=true)
                tag("keep") cuboid([shell_inner_width, shell_thickness, stopper_edge_distance + stopper_height + hex_hole_fill_edge]);
            attach(TOP, TOP, align=BACK, inside=true)
              tag(top_hc ? "remove" : "keep") cuboid([shell_inner_width - shell_inner_chamfer * 2, shell_thickness + (top_hc ? EPS : 0), shell_inner_depth]);
            //bottom wall
            if (bottom_hc)
              attach(TOP, RIGHT, align=FRONT, inside=true)
                tag("keep") hex_panel([shell_hexwall_depth, shell_hexwall_width, shell_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=shell_hex_frame_thickness);
            attach(TOP, TOP, align=FRONT, inside=true)
              tag(bottom_hc ? "remove" : "keep") cuboid([shell_inner_width - shell_inner_chamfer * 2, shell_thickness + (bottom_hc ? EPS : 0), shell_inner_depth]);
            //openconnect slot
            slot_parent_anchor =
              shell_slot_position == "Back" ? BOTTOM
              : shell_slot_position == "Top" ? BACK
              : shell_slot_position == "Bottom" ? FRONT
              : shell_slot_position == "Left" ? LEFT
              : RIGHT;
            slot_hgrids = shell_slot_position == "Left" || shell_slot_position == "Right" ? vertical_grids : horizontal_grids;
            slot_vgrids = shell_slot_position == "Back" ? vertical_grids : depth_grids;
            except_slot_pos =
              (add_stopper_holes && shell_slot_position == "Top") || (add_side_magnet_holes && shell_slot_position == "Right") || (add_side_magnet_holes && shell_slot_position == "Left") ? [[0, 0], [slot_hgrids - 1, 0]] : [];
            slot_slide_direction = shell_slot_position == "Top" || shell_slot_position == "Bottom" ? "Left" : "Up";
            slot_chamfer = shell_slot_position == "Back" ? min(4, max(0.8, slot_edge_wall_min_width) + OCHEAD_MIDDLE_HEIGHT + 1) : 0;
            attach(slot_parent_anchor, TOP, inside=true)
              right(slot_horizontal_offset) back(slot_vertical_offset)
                tag("rm_outer") openconnect_slot_grid(slot_cfg=_slot_cfg, horizontal_grids=slot_hgrids, vertical_grids=slot_vgrids, slot_position=slot_position, slot_lock_distribution=slot_lock_distribution, slot_entryramp_flip=slot_entryramp_flip, slot_slide_direction=slot_slide_direction, excess_thickness=EPS, except_slot_pos=except_slot_pos, chamfer=slot_chamfer);
            if (add_side_magnet_holes) {
              if (left_hc)
                attach(LEFT + FRONT, LEFT + FRONT, align=TOP, inside=true)
                  tag("keep") cuboid([shell_thickness, shell_height, shell_side_magnet_edge_distance + side_magnet_hole_diameter + hex_hole_fill_edge]);
              ycopies(OG_TILE_SIZE, vertical_grids)
                right(shell_slot_position == "Left" ? shell_ocslot_part_thickness : shell_thickness) left(shell_side_magnet_hole_thickness - EPS * 2) attach(LEFT, FRONT, align=TOP, inset=shell_side_magnet_edge_distance, inside=true)
                      tag("rm_outer") teardrop(h=shell_side_magnet_hole_thickness, d=side_magnet_hole_diameter, cap_h=side_magnet_hole_diameter / 2 + 0.2);
              if (right_hc)
                attach(RIGHT + FRONT, RIGHT + FRONT, align=TOP, inside=true)
                  tag("keep") cuboid([shell_thickness, shell_height, shell_side_magnet_edge_distance + side_magnet_hole_diameter + hex_hole_fill_edge]);
              ycopies(OG_TILE_SIZE, vertical_grids)
                left(shell_slot_position == "Right" ? shell_ocslot_part_thickness : shell_thickness) right(shell_side_magnet_hole_thickness - EPS * 2) attach(RIGHT, FRONT, align=TOP, inset=shell_side_magnet_edge_distance, inside=true)
                      tag("rm_outer") teardrop(h=shell_side_magnet_hole_thickness, d=side_magnet_hole_diameter, cap_h=side_magnet_hole_diameter / 2 + 0.2);
            }
            if (add_shell_divider == "Width" || add_shell_divider == "Both")
              drawer_divider(is_shell=true, by_width=true);
            if (add_shell_divider == "Height" || add_shell_divider == "Both")
              drawer_divider(is_shell=true, by_width=false);
            if (add_back_magnet_holes) {
              for (i = [0:len(shell_vertical_compartments) - 1]) {
                for (j = [0:len(shell_horizontal_compartments) - 1]) {
                  back(i == 0 ? 0 : shell_height_divide_cumnums[i - 1] * OG_TILE_SIZE)
                    right(j == 0 ? 0 : shell_width_divide_cumnums[j - 1] * OG_TILE_SIZE)
                      left((horizontal_grids - 2) / 2 * OG_TILE_SIZE)
                        fwd((vertical_grids - 1) / 2 * OG_TILE_SIZE - back_magnet_ocslot_offset)
                          line_copies(spacing=OG_TILE_SIZE * max(shell_horizontal_compartments[j] - 2, 0), n=min(shell_horizontal_compartments[j] - 1, 2), p1=[0, 0, 0])
                            attach(BOTTOM, BOTTOM, inside=true)
                              tag("rm_outer") cyl(h=shell_back_magnet_hole_thickness, d=back_magnet_hole_diameter, chamfer1=-0.2);
                }
              }
            }
            if (add_stopper_holes)
              for (i = [0:len(shell_horizontal_compartments) - 1])
                left(shell_width / 2 - OG_TILE_SIZE / 2) right(i == 0 ? 0 : shell_width_divide_cumnums[i - 1] * OG_TILE_SIZE) {
                    for (j = [0:shell_horizontal_compartments[i] == 1 ? 0 : 1])
                      left(shell_horizontal_compartments[i] == 1 ? 0 : j == 0 ? stopper_to_edge_offset : -stopper_to_edge_offset) right(j * (shell_horizontal_compartments[i] - 1) * OG_TILE_SIZE) {
                          tag("rm_outer") attach(BACK, TOP, align=TOP, inset=stopper_edge_distance, inside=true)
                              drawer_stopper(hole=true, hole_excess=shell_slot_position == "Top" ? shell_ocslot_part_thickness - shell_thickness : 0);
                        }
                  }
          }
        }
      shell_chamfer_edge_except =
        shell_slot_position == "Bottom" ? [FRONT + LEFT, FRONT + RIGHT]
        : shell_slot_position == "Top" ? [BACK + LEFT, BACK + RIGHT]
        : shell_slot_position == "Left" ? [BACK + LEFT, FRONT + LEFT]
        : shell_slot_position == "Right" ? [BACK + RIGHT, FRONT + RIGHT]
        : [];
      cuboid([shell_width, shell_height, shell_depth], edges="Z", chamfer=shell_outer_chamfer, except=shell_chamfer_edge_except, anchor=BOTTOM);
    }
  }
}
module drawer_container() {
  intersect(intersect="mask", keep="kp_root") {
    diff(remove="rm_outer", keep="mask kp_root") diff(remove="remove", keep="keep mask rm_outer kp_root")
        cuboid([container_width, container_height, container_depth], anchor=BOTTOM) {
          side_hc = container_side_wall_type == "Honeycomb";
          bottom_hc = container_bottom_wall_type == "Honeycomb";
          front_hc = container_front_wall_type == "Honeycomb";
          back_hc = container_back_wall_type == "Honeycomb";
          attach(BACK, BACK, align=BOTTOM, inset=container_back_wall_thickness, inside=true)
            tag("remove") cuboid([container_width - container_side_wall_thickness * 2, container_height - container_bottom_wall_thickness, container_depth - container_back_wall_thickness - container_front_wall_thickness])
                tag("keep") if (container_inner_bottom_fillet > 0) {
                  edge_mask([FRONT])
                    rounding_edge_mask(r=container_inner_bottom_fillet);
                  edge_mask(["Y"])
                    rounding_edge_mask(r=container_inner_side_fillet);
                  corner_mask([FRONT])
                    rounding_corner_mask(r=container_inner_bottom_fillet);
                }
          //front wall
          if (front_hc)
            attach(FRONT, LEFT, align=TOP, inside=true)
              tag("keep") hex_panel([container_height, container_width, container_front_wall_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=min(container_side_wall_thickness, container_bottom_wall_thickness));
          attach(TOP, TOP, align=FRONT, inset=container_bottom_wall_thickness + container_inner_bottom_fillet, inside=true)
            tag(front_hc ? "remove" : "keep") cuboid([container_width - container_side_wall_thickness * 2 - (front_hc ? container_inner_side_fillet * 2 : 0), container_height - container_bottom_wall_thickness - (front_hc ? container_top_frame_thickness + container_inner_bottom_fillet : 0), container_front_wall_thickness + (front_hc ? EPS : 0)]);
          //back wall
          if (back_hc)
            attach(FRONT, LEFT, align=BOTTOM, inside=true)
              tag("keep") hex_panel([container_height, container_width, container_back_wall_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=min(container_side_wall_thickness, container_bottom_wall_thickness));
          attach(BOTTOM, BOTTOM, align=FRONT, inset=container_bottom_wall_thickness + container_inner_bottom_fillet, inside=true)
            tag(back_hc ? "remove" : "keep") cuboid([container_width - container_side_wall_thickness * 2 - (back_hc ? container_inner_side_fillet * 2 : 0), back_hc ? container_back_wall_height - container_bottom_wall_thickness - container_top_frame_thickness - container_inner_bottom_fillet : container_back_wall_height, container_back_wall_thickness + (back_hc ? EPS : 0)]);
          //side walls
          if (side_hc)
            attach(FRONT, LEFT, align=[LEFT, RIGHT], inside=true, spin=90)
              tag("keep") hex_panel([container_height, container_depth, container_side_wall_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=min(container_side_wall_thickness, container_bottom_wall_thickness));
          down(container_front_wall_thickness) back(container_bottom_wall_thickness + container_inner_bottom_fillet)
              attach(FRONT + TOP, FRONT + TOP, align=[LEFT, RIGHT], inside=true)
                tag(side_hc ? "remove" : "keep") cuboid([container_side_wall_thickness + (side_hc ? EPS : 0), container_side_wall_height - container_bottom_wall_thickness - (side_hc ? container_top_frame_thickness + container_inner_bottom_fillet : 0), container_depth - container_front_wall_thickness - container_back_wall_thickness - (side_hc ? container_inner_side_fillet * 2 : 0)]);
          //bottom wall
          if (bottom_hc)
            attach(TOP, LEFT, align=FRONT, inside=true)
              tag("keep") hex_panel([container_depth, container_width, container_bottom_wall_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=min(container_side_wall_thickness, container_back_wall_thickness, container_front_wall_thickness));
          attach(FRONT, FRONT, align=BOTTOM, inset=container_back_wall_thickness, inside=true)
            tag(bottom_hc ? "remove" : "keep") cuboid([container_width - container_side_wall_thickness * 2 - (bottom_hc ? container_inner_side_fillet * 2 : 0), container_bottom_wall_thickness + (bottom_hc ? EPS : 0), container_depth - container_front_wall_thickness - container_back_wall_thickness - (bottom_hc ? container_inner_bottom_fillet * 2 : 0)]);


          tag("mask") {
            attach(FRONT, FRONT, align=TOP, inset=-handle_depth, inside=true)
              cuboid([container_width, container_height, container_front_wall_thickness + handle_depth], edges="Z", chamfer=container_outer_chamfer);
            attach(FRONT, FRONT, align=TOP, inset=container_front_wall_thickness, inside=true)
              cuboid([container_width, container_side_wall_height, container_depth - container_front_wall_thickness - container_back_wall_thickness], edges=[FRONT + LEFT, FRONT + RIGHT], chamfer=container_outer_chamfer);
            attach(BOTTOM, BOTTOM, align=FRONT, inside=true)
              cuboid([container_width, container_back_wall_height, container_back_wall_thickness], edges=["Z"], chamfer=container_outer_chamfer);
          }
          container_handle();
          if (add_label_holder)
            container_label_holder();
          if (add_container_divider == "Width" || add_container_divider == "Both")
            drawer_divider(is_shell=false, by_width=true);
          if (add_container_divider == "Depth" || add_container_divider == "Both")
            drawer_divider(is_shell=false, by_width=false);
          if (add_side_magnet_holes)
            xflip_copy() {
              hole_extrude_thickness = container_side_magnet_hole_thickness - container_side_wall_thickness + 0.45 + EPS;
              if (container_side_wall_type == "Honeycomb")
                attach(LEFT + FRONT, LEFT + FRONT, align=BOTTOM, inside=true)
                  tag("keep") cuboid([container_side_wall_thickness, container_height - container_back_side_height_offset - container_outer_chamfer, container_side_magnet_edge_distance + side_magnet_hole_diameter + hex_hole_fill_edge]);
              ycopies(OG_TILE_SIZE, vertical_grids) {
                attach(LEFT, FRONT, align=BOTTOM, inset=container_side_magnet_edge_distance, inside=true, spin=90)
                  tag("rm_outer") teardrop(h=container_side_magnet_hole_thickness, d=side_magnet_hole_diameter, cap_h=side_magnet_hole_diameter / 2 + 0.2);
                if (hole_extrude_thickness > EPS)
                  right(container_side_wall_thickness) attach(LEFT, FRONT, align=BOTTOM, inset=container_side_magnet_edge_distance, inside=true, spin=90)
                      tag("kp_root") teardrop(h=hole_extrude_thickness, d=side_magnet_hole_diameter + 0.2, cap_h=side_magnet_hole_diameter / 2 + 0.2, chamfer1=-hole_extrude_thickness);
              }
            }
          if (add_back_magnet_holes) {
            hole_extrude_thickness = container_back_magnet_hole_thickness - container_back_wall_thickness + 0.45 + EPS;
            if (back_hc)
              line_copies(back_magnet_grid_space[0], back_magnet_grid_count[0])
                attach(BOTTOM + FRONT, BOTTOM + FRONT, inside=true)
                  tag("keep") cuboid([back_magnet_hole_diameter + 4.2, container_height - container_back_side_height_offset, container_back_wall_thickness]);
            fwd((vertical_grids - 1) / 2 * OG_TILE_SIZE - back_magnet_ocslot_offset)
              line_copies(back_magnet_grid_space[0], back_magnet_grid_count[0]) {
                attach(BOTTOM, FRONT, inside=true)
                  tag("rm_outer") teardrop(h=container_back_magnet_hole_thickness, d=back_magnet_hole_diameter, cap_h=back_magnet_hole_diameter / 2 + 0.2);
                if (hole_extrude_thickness > EPS)
                  up(container_back_wall_thickness) attach(BOTTOM, FRONT, inside=true)
                      tag("kp_root") teardrop(h=hole_extrude_thickness, d=back_magnet_hole_diameter + 0.2, cap_h=back_magnet_hole_diameter / 2 + 0.2, chamfer1=-hole_extrude_thickness);
              }
          }
        }
  }
}
module drawer_divider(is_shell, by_width) {
  divider_wall_thickness = is_shell ? shell_thickness * 2 : container_divider_wall_thickness;
  divider_wall_type = is_shell ? shell_divider_wall_type : "Solid";
  grid_count =
    by_width && !is_shell ? container_width_grid_count
    : !by_width && !is_shell ? container_depth_grid_count
    : by_width && is_shell ? horizontal_grids : vertical_grids;
  compartment_list =
    by_width && !is_shell ? container_width_compartment_list
    : !by_width && !is_shell ? container_depth_compartment_list
    : by_width && is_shell ? shell_width_compartment_list : shell_height_compartment_list;
  divide_strs = str_split(str_strip(str_replace_char(compartment_list, " ", ","), ","), ",");
  divide_nums = [for (i = [0:len(divide_strs) - 1]) parse_num(divide_strs[i])];
  divide_cumnums = [for (i = cumsum(divide_nums)) if (i < grid_count) i];
  inner_size =
    by_width && !is_shell ? container_width - container_side_wall_thickness * 2 - divider_wall_thickness * len(divide_cumnums)
    : !by_width && !is_shell ? container_depth - container_front_wall_thickness - container_back_wall_thickness - divider_wall_thickness * len(divide_cumnums)
    : by_width && is_shell ? shell_inner_width : shell_inner_height;
  wall_alignment =
    by_width && !is_shell ? LEFT
    : !by_width && !is_shell ? TOP
    : by_width && is_shell ? LEFT : BACK;

  solidwall_anchor =
    by_width && !is_shell ? FRONT + TOP
    : !by_width && !is_shell ? FRONT
    : by_width && is_shell ? TOP : LEFT;
  solidwall_x =
    by_width ? divider_wall_thickness
    : is_shell ? shell_width : container_width;
  solidwall_y =
    by_width && is_shell ? shell_height
    : !by_width && is_shell ? divider_wall_thickness
    : min((container_height - container_back_side_height_offset - container_outer_chamfer), container_divider_wall_height + container_bottom_wall_thickness);
  solidwall_z =
    by_width && !is_shell ? container_depth
    : !by_width && !is_shell ? divider_wall_thickness
    : shell_depth;

  hexwall_spin = by_width ? 90 : 0;
  hexwall_length = !by_width ? shell_width : shell_height;
  hexwall_depth = shell_hexwall_depth;

  compartment_size_unit = is_shell ? OG_TILE_SIZE : inner_size / grid_count;
  compartment_first_wall_offset =
    by_width && !is_shell ? container_side_wall_thickness
    : !by_width && !is_shell ? container_front_wall_thickness
    : (shell_slot_position == "Bottom" && !by_width) || (shell_slot_position == "Left" && by_width) ? -(divider_wall_thickness - shell_ocslot_part_thickness)
    : -(divider_wall_thickness - shell_thickness);

  container_divider_fillet_edges = by_width ? [FRONT + LEFT, FRONT + RIGHT] : [FRONT + TOP, FRONT + BOTTOM];
  for (i = [0:len(divide_cumnums) - 1]) {
    compartment_inset = divide_cumnums[i] * compartment_size_unit + compartment_first_wall_offset + (is_shell ? 0 : i * divider_wall_thickness);
    if (divide_cumnums[i] > 0 && compartment_inset < inner_size) {
      tag_intersect(tag="keep", intersect="msk0", keep="kp1") {
        attach(solidwall_anchor, solidwall_anchor, align=wall_alignment, inset=compartment_inset, inside=true)
          tag_diff(tag=divider_wall_type == "Honeycomb" ? "" : "kp1", remove="rm1") cuboid([solidwall_x, solidwall_y, solidwall_z]) {
              if (is_shell) {
                if (!by_width && add_stopper_holes) {
                  for (in_i = [0:len(shell_horizontal_compartments) - 1]) {
                    left(shell_width / 2 - OG_TILE_SIZE / 2) right(in_i == 0 ? 0 : shell_width_divide_cumnums[in_i - 1] * OG_TILE_SIZE) {
                        for (in_j = [0:shell_horizontal_compartments[in_i] == 1 ? 0 : 1]) {
                          left(shell_horizontal_compartments[in_i] == 1 ? 0 : in_j == 0 ? stopper_to_edge_offset : -stopper_to_edge_offset) right(in_j * (shell_horizontal_compartments[in_i] - 1) * OG_TILE_SIZE)
                              tag("rm1") attach(BACK, TOP, align=TOP, inset=stopper_edge_distance, inside=true)
                                  drawer_stopper(hole=true, hole_excess=shell_thickness);
                        }
                      }
                  }
                }
                if (by_width && add_side_magnet_holes) {
                  ycopies(OG_TILE_SIZE, vertical_grids)
                    attach(LEFT, FRONT, align=TOP, inset=shell_side_magnet_edge_distance, inside=true)
                      tag("rm1") teardrop(h=shell_side_magnet_hole_thickness, d=side_magnet_hole_diameter, cap_h=side_magnet_hole_diameter / 2 + 0.2);
                  ycopies(OG_TILE_SIZE, vertical_grids)
                    attach(RIGHT, FRONT, align=TOP, inset=shell_side_magnet_edge_distance, inside=true)
                      tag("rm1") teardrop(h=shell_side_magnet_hole_thickness, d=side_magnet_hole_diameter, cap_h=side_magnet_hole_diameter / 2 + 0.2);
                }
              } else if (container_divider_wall_fillet > 0)
                back(container_bottom_wall_thickness)
                  tag("") edge_mask(container_divider_fillet_edges)
                      rounding_edge_mask(r=container_divider_wall_fillet, spin=by_width ? 90 : -90);
            }
        if (divider_wall_type == "Honeycomb")
          tag_diff(tag="msk0", remove="rm0")
            attach(TOP, RIGHT, align=wall_alignment, inset=compartment_inset, inside=true, spin=hexwall_spin)
              hex_panel([hexwall_depth, hexwall_length, divider_wall_thickness], strut=honeycomb_strut_adj, spacing=honeycomb_unit_space_hyp, frame=shell_thickness) {
                if (is_shell) {
                  if (!by_width && add_stopper_holes)
                    attach(RIGHT, TOP, inside=true)
                      tag("") cuboid([shell_width, divider_wall_thickness, stopper_edge_distance + stopper_height + hex_hole_fill_edge]);
                  if (by_width && add_side_magnet_holes)
                    attach(RIGHT, TOP, inside=true)
                      tag("") cuboid([shell_height, divider_wall_thickness, side_magnet_hole_diameter + hex_hole_fill_edge]);
                }
              }
      }
    }
  }
}
module container_handle() {
  //Calculate honeycomb pattern so I can align the stem of the handle in a way that looks natural. I'm pretty sure some of the calculations are redundant, but I cannot improve the code because I forgot how they work an hour after typing them.
  handle_strut_number = fronthex_width < 100 ? 0 : (fronthex_width_struts - 1) / 2 % 2;
  hexwall_edge_to_strut_offset = hex_or * 2 + honeycomb_strut_hyp / 2 - height_adj_to_width_opp;
  leftcol1_rightcol2 = honeycomb_unit_space_adj * (handle_strut_number - 1) + hexwall_edge_to_strut_offset;
  leftcol2_rightcol1 = honeycomb_unit_space_adj * ( -handle_strut_number + fronthex_width_struts - 2) + hexwall_edge_to_strut_offset;
  left_strut_offset = handle_strut_number % 2 == 0 ? leftcol1_rightcol2 : leftcol2_rightcol1;
  right_strut_offset = handle_strut_number % 2 == 0 ? leftcol2_rightcol1 : leftcol1_rightcol2;
  turtle_start_offset = 0.2;
  pull_handle_transition_depth = handle_depth - handle_thickness - handle_thickness / 2 - turtle_start_offset;

  left_transition_offset = fronthex_width / 2 - left_strut_offset;
  right_transition_offset = fronthex_width / 2 - right_strut_offset;

  left_transition_target_x = ang_adj_to_opp(30, fronthex_bottom_strut_height - handle_chamfer) / 2 - (handle_thickness - honeycomb_strut_hyp);
  right_transition_target_x = fronthex_width - (right_strut_offset + honeycomb_strut_hyp) - (left_strut_offset + left_transition_target_x) - (handle_thickness - honeycomb_strut_hyp);

  left_turtle_offset = fronthex_width / 2 - left_strut_offset - handle_thickness / 2 - left_transition_target_x;
  right_turtle_offset = fronthex_width / 2 - right_strut_offset - handle_thickness / 2 - right_transition_target_x;

  turtle_handle_width =
    handle_strut_number % 2 == 0 ? fronthex_width / 2 - left_strut_offset - left_transition_target_x - handle_thickness - handle_thickness / 2
    : fronthex_width / 2 - right_strut_offset - right_transition_target_x - handle_thickness - handle_thickness / 2;

  handle_sweep_turtle_path_left = ["move", turtle_start_offset, "arcleft", handle_thickness, 90, "move", turtle_handle_width];
  handle_sweep_turtle_path_right = ["move", turtle_start_offset, "arcright", handle_thickness, 90, "move", turtle_handle_width];

  up(pull_handle_transition_depth - EPS) fwd(container_height / 2 - fronthex_bottom_strut_height / 2) left(handle_strut_number % 2 == 0 ? left_turtle_offset : -left_turtle_offset)
        attach(TOP, "start-centroid")
          path_sweep(rect([handle_thickness, fronthex_bottom_strut_height], chamfer=handle_chamfer), path=turtle(handle_sweep_turtle_path_left));
  up(pull_handle_transition_depth - EPS) fwd(container_height / 2 - fronthex_bottom_strut_height / 2) left(handle_strut_number % 2 == 0 ? right_turtle_offset : -right_turtle_offset)
        attach(TOP, "start-centroid")
          path_sweep(rect([handle_thickness, fronthex_bottom_strut_height], chamfer=handle_chamfer), path=turtle(handle_sweep_turtle_path_right));
  //middle truss
  if (turtle_handle_width > 50) {
    up((container_depth) / 2 - EPS) fwd(container_height / 2) {
        left(handle_strut_number % 2 == 0 ? left_transition_offset : -left_transition_offset) {
          if ( (fronthex_width_struts - 1) / 2 % 2 == 0)
            right((fronthex_width_struts - handle_strut_number * 2 - 1) / 2 * honeycomb_unit_space_adj)
              handle_transition(trans_offset=(left_transition_target_x + right_transition_target_x) / 2, starting_thickness=honeycomb_strut_hyp, target_thickness=handle_thickness, add_front=handle_thickness - handle_chamfer);
          else
            right((fronthex_width_struts - handle_strut_number * 2 - 1) / 2 * honeycomb_unit_space_adj)
              xflip() handle_transition(trans_offset=(left_transition_target_x + right_transition_target_x) / 2, starting_thickness=honeycomb_strut_hyp, target_thickness=handle_thickness, add_front=handle_thickness - handle_chamfer);
        }
      }
  }
  up((container_depth) / 2 - EPS) fwd(container_height / 2)
      left(handle_strut_number % 2 == 0 ? left_transition_offset : -left_transition_offset) {
        if (handle_strut_number % 2 == 0)
          handle_transition(trans_offset=left_transition_target_x, starting_thickness=honeycomb_strut_hyp, target_thickness=handle_thickness);
        else
          xflip() handle_transition(trans_offset=left_transition_target_x, starting_thickness=honeycomb_strut_hyp, target_thickness=handle_thickness);
      }
  up((container_depth) / 2 - EPS) fwd(container_height / 2)
      left(handle_strut_number % 2 == 0 ? right_transition_offset : -right_transition_offset) {
        if (handle_strut_number % 2 == 0)
          handle_transition(trans_offset=right_transition_target_x, starting_thickness=honeycomb_strut_hyp, target_thickness=handle_thickness);
        else
          xflip() handle_transition(trans_offset=right_transition_target_x, starting_thickness=honeycomb_strut_hyp, target_thickness=handle_thickness);
      }
  function handle_profile_func(first_ang, second_ang = 30, thickness = honeycomb_strut_hyp) =
    [
      [ang_adj_to_opp(first_ang, handle_chamfer), handle_chamfer],
      [ang_adj_to_opp(first_ang, fronthex_bottom_strut_height - handle_chamfer), fronthex_bottom_strut_height - handle_chamfer],
      [ang_adj_to_opp(first_ang, fronthex_bottom_strut_height - handle_chamfer) + handle_chamfer, fronthex_bottom_strut_height],
      [thickness + ang_adj_to_opp(first_ang, fronthex_bottom_strut_height) - handle_chamfer - ang_adj_to_opp(first_ang, handle_chamfer), fronthex_bottom_strut_height],
      [thickness + ang_adj_to_opp(first_ang, fronthex_bottom_strut_height - handle_chamfer), fronthex_bottom_strut_height - handle_chamfer],
      [thickness + ang_adj_to_opp(first_ang, handle_chamfer) + ang_adj_to_opp(30 - second_ang, fronthex_bottom_strut_height - handle_chamfer * 2), handle_chamfer],
      [thickness + ang_adj_to_opp(first_ang, handle_chamfer) + ang_adj_to_opp(30 - second_ang, fronthex_bottom_strut_height - handle_chamfer * 2) - ang_adj_to_opp(45, handle_chamfer), 0],
      [ang_adj_to_opp(first_ang, handle_chamfer) + handle_chamfer, 0],
    ];
  module handle_transition(steps = 90, trans_offset = "Left", starting_thickness = honeycomb_strut_hyp, target_thickness = honeycomb_strut_hyp, starting_angle = 30, wide_bottom = true, add_front = 0) {
    ang_unit = starting_angle / steps;
    up_unit = pull_handle_transition_depth / steps;
    thickness_unit = (target_thickness - starting_thickness) / steps;
    target_x =
      trans_offset == "Left" ? ang_adj_to_opp(starting_angle, fronthex_bottom_strut_height - handle_chamfer)
      : trans_offset == "Middle" ? ang_adj_to_opp(starting_angle, fronthex_bottom_strut_height - handle_chamfer) / 2 - (target_thickness - starting_thickness)
      : trans_offset == "Right" ? 0
      : trans_offset;
    x_unit = target_x / steps;
    render() {
      if (wide_bottom) {
        down(container_front_wall_thickness - EPS) linear_extrude(container_front_wall_thickness) polygon(handle_profile_func(first_ang=starting_angle, second_ang=0, thickness=starting_thickness));
      }
      for (i = [1:1:steps]) {
        handle_profile1 = handle_profile_func(first_ang=starting_angle - ang_unit * (i - 1), second_ang=wide_bottom ? ang_unit * (i - 1) : starting_angle, thickness=starting_thickness + thickness_unit * (i - 1));
        handle_profile2 = handle_profile_func(first_ang=starting_angle - ang_unit * (i), second_ang=wide_bottom ? ang_unit * (i) : starting_angle, thickness=starting_thickness + thickness_unit * (i));
        hull() {
          right(x_unit * (i - 1)) up(up_unit * (i - 1)) linear_extrude(EPS) polygon(handle_profile1);
          right(x_unit * i) up(up_unit * i) linear_extrude(EPS) polygon(handle_profile2);
        }
      }
      if (add_front > 0) {
        right(x_unit * steps) up(up_unit * steps) linear_extrude(add_front) polygon(handle_profile_func(first_ang=starting_angle - ang_unit * steps, second_ang=wide_bottom ? ang_unit * steps : starting_angle, thickness=starting_thickness + thickness_unit * steps));
      }
    }
  }
}
module container_label_holder() {
  frontplate_width = honeycomb_unit_space_adj * 4;
  frontplate_offset_mode = (fronthex_width_struts - 1) / 2 % 2 == fronthex_height_struts % 1 * 2;
  label_side_clearance = 0.2;
  label_depth_clearance = 0.3;
  label_holder_wall_thickness = 0.8;
  label_holder_width = label_width + label_holder_wall_thickness * 2 + label_side_clearance * 2;
  label_holder_depth = label_thickness + label_depth_clearance + label_holder_wall_thickness;
  label_holder_height = label_height + label_holder_depth + label_side_clearance;
  if (container_front_wall_type == "Honeycomb") {
    left(honeycomb_unit_space_adj / 2 - ang_hyp_to_adj(30, honeycomb_strut_adj) / 2) {
      right(frontplate_offset_mode ? hex_or : hex_or / 2)
        attach(TOP, FRONT, align=FRONT, inset=fronthex_height_offset + (fronthex_height_struts - 0.5) * honeycomb_unit_space_hyp, inside=true)
          tag("keep") prismoid(size1=[frontplate_width, container_front_wall_thickness], xang=frontplate_offset_mode ? [120, 60] : [60, 120], yang=[90, 90], h=honeycomb_unit_space_hyp / 2 + fronthex_height_offset);
      right(frontplate_offset_mode ? hex_or / 2 : hex_or)
        attach(TOP, FRONT, align=FRONT, inset=fronthex_height_offset + (fronthex_height_struts - 1) * honeycomb_unit_space_hyp, inside=true)
          tag("keep") prismoid(size1=[frontplate_width, container_front_wall_thickness], xang=frontplate_offset_mode ? [60, 120] : [120, 60], yang=[90, 90], h=honeycomb_unit_space_hyp / 2);
    }
    attach(TOP, TOP, align=BACK, inset=honeycomb_strut_adj / 2, inside=true)
      tag("keep") cuboid([label_holder_width, label_holder_height, container_front_wall_thickness]);
  }
  tag_diff(tag="keep", remove="label_remove") {
    attach(TOP, BOTTOM, align=BACK, inset=honeycomb_strut_adj / 2)
      tag("") prismoid(size1=[label_holder_width, label_holder_height], xang=[90, 90], yang=[45, 90], h=label_holder_depth, rounding=[0, 0, 0.8, 0.8], $fn=64) {
          edge_mask([TOP + LEFT, TOP + RIGHT])
            tag("label_remove") rounding_edge_mask(r=0.4, l=$edge_length + 5);
          back(EPS) attach(BACK, BACK, align=BOTTOM, inside=true)
              tag("label_remove") cuboid([label_holder_width - label_holder_wall_thickness * 2, label_height + label_side_clearance, label_holder_depth - label_holder_wall_thickness]);
          attach(BACK, BACK, align=TOP, inside=true, shiftout=EPS)
            tag("label_remove") cuboid([label_holder_width - label_holder_wall_thickness * 2 - label_holder_wall_thickness * 4, label_height + label_side_clearance, label_holder_depth - label_holder_wall_thickness]);
        }
  }
}
module drawer_stopper(hole = false, hole_excess = 0, anchor = TOP, orient = UP, spin = 0) {
  stopper_leg_thickness = 1.6;
  stopper_leg_outer_round = min(stopper_rounding, min(stopper_width - stopper_width_clearance * 2, stopper_clip_length) / 2);
  stopper_leg_inner_round = min(stopper_rounding, min(stopper_width - stopper_leg_thickness * 2 - stopper_width_clearance * 2, stopper_clip_length) / 2);
  stopper_leg_nub_length = min(3, stopper_clip_length - stopper_leg_outer_round);
  stopper_leg_nub_width = min(0.6, stopper_leg_nub_length);

  stopper_clip_length_clearance = 0.1;

  tag_scope() cuboid([stopper_width + stopper_flank_width - (hole ? 0 : stopper_width_clearance * 2), stopper_height - (hole ? 0 : stopper_height_clearance * 2), stopper_flank_depth - (hole ? 0 : stopper_clip_length_clearance)], anchor=anchor, orient=orient, spin=spin) {
      attach(BOTTOM, TOP)
        diff() cuboid([stopper_width - (hole ? 0 : stopper_width_clearance * 2), stopper_height - (hole ? 0 : stopper_height_clearance * 2), shell_thickness - stopper_flank_depth + (hole ? EPS * 2 : 0)], rounding=-stopper_rounding, edges=[TOP + LEFT, TOP + RIGHT], $fn=64) {
            if (hole && hole_excess > 0)
              attach(BOTTOM, TOP)
                cuboid([stopper_width + stopper_flank_width, stopper_height, hole_excess]);
            if (!hole && stopper_clip_length > EPS)
              attach(BOTTOM, TOP)
                cuboid([stopper_width - stopper_width_clearance * 2, stopper_height - stopper_height_clearance * 2, stopper_clip_length], rounding=stopper_leg_outer_round, edges=[BOTTOM + LEFT, BOTTOM + RIGHT], $fn=64) {
                  attach(BOTTOM, BOTTOM, inside=true)
                    cuboid([stopper_width - stopper_leg_thickness * 2 - stopper_width_clearance * 2, stopper_height - stopper_height_clearance * 2 + EPS, stopper_clip_length], rounding=stopper_leg_inner_round, edges=[TOP + LEFT, TOP + RIGHT], $fn=64) {
                      edge_mask([BOTTOM + LEFT, BOTTOM + RIGHT])
                        rounding_edge_mask(r=stopper_leg_inner_round, spin=90);
                    }
                  attach(RIGHT, BOTTOM, align=TOP)
                    prismoid(size1=[stopper_height - stopper_height_clearance * 2, stopper_leg_nub_length], size2=[stopper_height - stopper_height_clearance * 2, 0], shift=[0, stopper_leg_nub_length / 2], h=stopper_leg_nub_width);
                  attach(LEFT, BOTTOM, align=TOP)
                    prismoid(size1=[stopper_height - stopper_height_clearance * 2, stopper_leg_nub_length], size2=[stopper_height - stopper_height_clearance * 2, 0], shift=[0, stopper_leg_nub_length / 2], h=stopper_leg_nub_width);
                }
          }
    }
}
