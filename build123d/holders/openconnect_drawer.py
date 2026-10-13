# SPDX-License-Identifier: CC-BY-SA-4.0
"""mitufy's openConnect drawer shell, container and stopper clips, adapted under CC BY-SA 4.0.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:14-131,1373-1674,
1807-1837. part=shell: print BACK-WALL-DOWN in PLA/PCTG for every selected
mount face (REV 3d). part=container: print bottom-down, handle toward -Y
(drawer/container.py). part=stopper_clips: flat, 2 mm tall (drawer/stopper.py).
Model frame (shell, container): back Y=0, open front +Y, top +Z; source Left
is model +X. Worst load is a filled drawer pulling the mount away from the
wall; the continuous shell walls carry it, and dividers carry their own
compartment's container. Mount profiles remain library geometry; only the
shell carries a mount. Dividers: drawer/dividers.py and
build123d/docs/openconnect-drawer.md.
"""
from build123d import Location

from drawer import container, shell, stopper
from drawer.constants import SLOT_SIDE_CLEARANCE_MAX, SLOT_DEPTH_CLEARANCE_MAX
from holders.registry import ModelSpec, Param, Preset, register

MOUNT = 'openconnect-slot-shallow'


def _part(values):
    return (values or {}).get('part', 'shell')


def build(values=None):
    if _part(values) == 'container':
        return container.build(SPEC.resolve_values(values))
    if _part(values) == 'stopper_clips':
        return stopper.build(SPEC.resolve_values(values))
    shell.validate_clearances(values)
    return shell.build(SPEC.resolve_values(values))


def print_frame(values=None):
    if _part(values) == 'container':
        return container.print_frame(values)
    if _part(values) == 'stopper_clips':
        return Location()  # built flat on the bed
    return shell.print_frame(values)


def audit_exclusions(values=None):
    if _part(values) == 'container':
        return container.published_ceiling_regions(values)
    if _part(values) == 'stopper_clips':
        return stopper.audit_exclusions(values)
    return shell.published_ceiling_regions(values)


def mount_for_values(values):
    if _part(values) in ('container', 'stopper_clips'):
        return None
    # The author's exception rule can remove every slot on a 1x1 Top/side
    # face. Such a shell still builds; it does not claim a nonexistent mount.
    return MOUNT if shell.slot_layout(values)[2] else None


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    shell.validate_clearances(values)
    v = SPEC.resolve_values(values)
    if mount_for_values(v) is None:
        return None
    fx = shell.slot_fixtures(v)
    before = shell.before_bed_chamfer(v)
    finished = shell.chamfer_bed(before, v)
    # Envelope is the uncut box/cavity minus only mandatory bevel volume.
    # Magnet and stopper cuts remain INSIDE the probe, never clipped away.
    fx.backing_envelope = shell.body(v) - (before-finished)
    return fx


SPEC = register(ModelSpec(
    name='openconnect_drawer', title='openConnect drawer', category_id='multiboard',
    description="mitufy's openConnect drawer (CC BY-SA 4.0): shell, container and stopper clips. The shell prints back-wall-down with a honeycomb bottom, selectable wall types and any mounting face; the container prints bottom-down with a handle, label holder and magnet pockets. Comma-separated compartment lists add shell dividers (one container per compartment) or container dividers; the clips print flat.",
    build=build, mounts=(MOUNT,), mount_for_values=mount_for_values,
    print_frame=print_frame,
    params=(
        Param('part', 'enum', 'shell', choices=('shell', 'container', 'stopper_clips'), filename=True, group='Drawer Size'),
        Param('horizontal_grids', 'integer', 5, min=1, max=8, step=1, filename=True, group='Drawer Size'),
        Param('vertical_grids', 'integer', 2, min=1, max=8, step=1, filename=True, group='Drawer Size'),
        Param('depth_grids', 'integer', 5, min=1, max=8, step=1, filename=True, group='Drawer Size'),
        Param('shell_slot_position', 'enum', 'Back', choices=shell.SLOT_FACES, group='Shell'),
        Param('shell_top_wall_type', 'enum', 'Solid', choices=('Solid', 'Honeycomb'), group='Shell'),
        Param('shell_bottom_wall_type', 'enum', 'Honeycomb', choices=('Solid', 'Honeycomb'), group='Shell'),
        Param('shell_side_wall_type', 'enum', 'Solid', choices=('Solid', 'Honeycomb'), group='Shell'),
        Param('honeycomb_ceiling', 'enum', 'roofed', choices=('roofed',), group='Shell'),
        Param('honeycomb_strut_hyp', 'number', 5.0, min=1.1, max=16.3, step=.1, group='Shell'),
        Param('shell_thickness', 'number', 2.4, min=1.6, max=4, step=.1, group='Shell'),
        Param('shell_outer_chamfer', 'number', 2, min=0, max=4, step=.1, group='Shell'),
        Param('shell_to_slot_wall_thickness', 'number', .9, min=.6, max=2, step=.1, group='Shell'),
        Param('slot_lock_distribution', 'enum', 'Top Corners', choices=('All', 'Staggered', 'Corners', 'Top Corners', 'None'), group='Slots'),
        Param('slot_position', 'enum', 'All', choices=('All', 'Staggered', 'Edge Rows', 'Edge Columns', 'Corners'), group='Slots'),
        Param('slot_entryramp_flip', 'boolean', False, group='Slots'),
        Param('slot_horizontal_offset', 'number', 0, min=-14, max=14, step=.1, group='Slots'),
        Param('slot_vertical_offset', 'number', 0, min=-10, max=10, step=.1, group='Slots'),
        Param('slot_side_clearance', 'number', .1, min=0, max=SLOT_SIDE_CLEARANCE_MAX, step=.01, group='Advanced'),
        Param('slot_depth_clearance', 'number', .1, min=0, max=SLOT_DEPTH_CLEARANCE_MAX, step=.01, group='Advanced'),
        # The author's drawer dimensions below have steps, but no published
        # finite ranges (:88-100). Preserve that numeric-input contract.
        Param('add_back_magnet_holes', 'boolean', True, group='Magnets'),
        Param('shell_back_magnet_thickness', 'number', 2, step=.1, group='Magnets'),
        Param('back_magnet_diameter', 'number', 6, step=.1, group='Magnets'),
        Param('add_side_magnet_holes', 'boolean', True, group='Magnets'),
        Param('shell_side_magnet_thickness', 'number', 1, step=.1, group='Magnets'),
        Param('side_magnet_diameter', 'number', 6, step=.1, group='Magnets'),
        Param('shell_side_magnet_edge_distance', 'number', 6, step=.1, group='Magnets'),
        Param('add_stopper_holes', 'boolean', True, group='Stoppers'),
        Param('stopper_edge_distance', 'number', 3, step=.1, group='Stoppers'),
        Param('stopper_clip_length', 'number', 6, min=4, max=12, step=.1, group='Stoppers'),
        # Compartment lists: comma-separated tile (shell) or unit (container)
        # counts; drawer/dividers.py gives a named error for anything else.
        Param('add_shell_divider', 'enum', 'None', choices=shell.DIVIDER_MODES, group='Shell Divider'),
        Param('shell_divider_wall_type', 'enum', 'Honeycomb', choices=('Solid', 'Honeycomb'), group='Shell Divider'),
        Param('shell_width_compartment_list', 'string', '3,2', charset='printable-ascii', max_length=32, group='Shell Divider'),
        Param('shell_height_compartment_list', 'string', '1,1', charset='printable-ascii', max_length=32, group='Shell Divider'),
        Param('add_container_divider', 'enum', 'None', choices=container.DIVIDER_MODES, group='Container Divider'),
        Param('container_divider_wall_height_offset', 'number', 10, min=0, max=20, step=.1, group='Container Divider'),
        Param('container_width_grid_count', 'integer', 3, min=1, max=20, step=1, group='Container Divider'),
        Param('container_width_compartment_list', 'string', '1,1,1', charset='printable-ascii', max_length=32, group='Container Divider'),
        Param('container_depth_grid_count', 'integer', 5, min=1, max=20, step=1, group='Container Divider'),
        Param('container_depth_compartment_list', 'string', '2,3', charset='printable-ascii', max_length=32, group='Container Divider'),
        *(Param(f'container_{wall}_wall_type', 'enum', default, choices=container.WALL_TYPES, group='Container')
          for wall, default in (('front', 'Honeycomb'), ('back', 'Solid'), ('side', 'Honeycomb'), ('bottom', 'Solid'))),
        Param('container_solid_wall_thickness', 'number', 1.6, min=1.2, max=3, step=.1, group='Container'),
        Param('container_honeycomb_wall_thickness', 'number', 2.0, min=1.6, max=3, step=.1, group='Container'),
        Param('container_back_side_height_offset', 'number', 3, min=0, max=10, step=.1, group='Container'),
        Param('container_inner_fillet', 'number', 2, min=0, max=4, step=.1, group='Container'),
        Param('add_label_holder', 'boolean', True, group='Container'),
        Param('label_width', 'number', 48, min=20, max=100, step=.1, group='Container'),
        Param('label_height', 'number', 10, min=6, max=20, step=.1, group='Container'),
        Param('label_thickness', 'number', 1, min=.6, max=1.6, step=.1, group='Container'),
        Param('handle_thickness', 'number', 2.4, min=1.6, max=4, step=.1, group='Container'),
        Param('handle_depth', 'number', 12, min=6, max=20, step=.1, group='Container'),
        Param('container_back_magnet_thickness', 'number', 1, min=.6, max=3, step=.1, group='Container'),
        Param('container_side_magnet_thickness', 'number', 1, min=.6, max=3, step=.1, group='Container'),
        Param('container_side_magnet_edge_distance', 'number', 6, min=2, max=12, step=.1, group='Container'),
        Param('container_height_clearance', 'number', .4, min=.1, max=1, step=.01, group='Container'),
        Param('container_width_clearance', 'number', .3, min=.1, max=1, step=.01, group='Container'),
        Param('container_depth_clearance', 'number', .4, min=.1, max=1, step=.01, group='Container'),
    ),
    presets=(Preset('default', '5 × 2 × 5 honeycomb-bottom shell', {}),
             Preset('small', '2 × 1 × 2 honeycomb-bottom shell', {'horizontal_grids': 2, 'vertical_grids': 1, 'depth_grids': 2}),
             Preset('top-slot', 'Underdesk shell', {'shell_slot_position': 'Top'}),
             Preset('container', '5 × 2 × 5 container: honeycomb front and sides', {'part': 'container'}),
             Preset('two-compartments', '5 × 2 × 5 shell split 3 + 2 tiles wide; build a 3- and a 2-wide container', {
                 'add_shell_divider': 'Width', 'shell_width_compartment_list': '3,2'}),
             Preset('organiser', '5 × 2 × 5 container: thirds across, 2/5 + 3/5 deep', {
                 'part': 'container', 'add_container_divider': 'Both',
                 'container_width_grid_count': 3, 'container_width_compartment_list': '1,1,1',
                 'container_depth_grid_count': 5, 'container_depth_compartment_list': '2,3'}),
             Preset('stopper-clips', 'Two stopper clips for 2.4 mm shell walls', {'part': 'stopper_clips'}),
             Preset('container-solid', '5 × 2 × 5 container: all walls solid', {
                 'part': 'container', **{f'container_{wall}_wall_type': 'Solid'
                                         for wall in ('front', 'back', 'side', 'bottom')}})),
))
