# SPDX-License-Identifier: CC-BY-SA-4.0
"""mitufy's openConnect drawer shell, adapted under CC BY-SA 4.0.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:14-131,1373-1483.
Print BACK-WALL-DOWN in PLA/PCTG for every selected mount face (REV 3d).
Model frame: back Y=0, open front +Y, top +Z; source Left is model +X.
Worst load is a filled drawer pulling the mount away from the wall; the
continuous shell walls carry it. Mount profiles remain library geometry.
"""
from drawer import shell
from holders.registry import ModelSpec, Param, Preset, register

MOUNT = 'openconnect-slot-shallow'


def build(values=None):
    return shell.build(SPEC.resolve_values(values))


def print_frame(values=None):
    return shell.print_frame(values)


def mount_for_values(values):
    # The author's exception rule can remove every slot on a 1x1 Top/side
    # face. Such a shell still builds; it does not claim a nonexistent mount.
    return MOUNT if shell.slot_layout(values)[2] else None


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
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
    description="mitufy's drawer shell (CC BY-SA 4.0). Print back-wall-down; solid walls. Select the mounting face independently of print orientation.",
    build=build, mounts=(MOUNT,), mount_for_values=mount_for_values,
    print_frame=print_frame,
    params=(
        Param('part', 'enum', 'shell', choices=('shell',), group='Drawer Size'),
        Param('horizontal_grids', 'integer', 5, min=1, max=8, step=1, filename=True, group='Drawer Size'),
        Param('vertical_grids', 'integer', 2, min=1, max=8, step=1, filename=True, group='Drawer Size'),
        Param('depth_grids', 'integer', 5, min=1, max=8, step=1, filename=True, group='Drawer Size'),
        Param('shell_slot_position', 'enum', 'Back', choices=shell.SLOT_FACES, group='Shell'),
        Param('shell_top_wall_type', 'enum', 'Solid', choices=('Solid',), group='Shell'),
        Param('shell_bottom_wall_type', 'enum', 'Solid', choices=('Solid',), group='Shell'),
        Param('shell_side_wall_type', 'enum', 'Solid', choices=('Solid',), group='Shell'),
        Param('shell_thickness', 'number', 2.4, min=1.6, max=4, step=.1, group='Shell'),
        Param('shell_outer_chamfer', 'number', 2, min=0, max=4, step=.1, group='Shell'),
        Param('shell_to_slot_wall_thickness', 'number', .9, min=.6, max=2, step=.1, group='Shell'),
        Param('slot_lock_distribution', 'enum', 'Top Corners', choices=('All', 'Staggered', 'Corners', 'Top Corners', 'None'), group='Slots'),
        Param('slot_position', 'enum', 'All', choices=('All', 'Staggered', 'Edge Rows', 'Edge Columns', 'Corners'), group='Slots'),
        Param('slot_entryramp_flip', 'boolean', False, group='Slots'),
        Param('slot_horizontal_offset', 'number', 0, min=-14, max=14, step=.1, group='Slots'),
        Param('slot_vertical_offset', 'number', 0, min=-10, max=10, step=.1, group='Slots'),
        Param('slot_side_clearance', 'number', .1, min=0, max=.5, step=.01, group='Advanced'),
        Param('slot_depth_clearance', 'number', .1, min=0, max=.5, step=.01, group='Advanced'),
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
    ),
    presets=(Preset('default', '5 × 2 × 5 solid shell', {}),
             Preset('small', '2 × 1 × 2 solid shell', {'horizontal_grids': 2, 'vertical_grids': 1, 'depth_grids': 2}),
             Preset('top-slot', 'Underdesk shell', {'shell_slot_position': 'Top'})),
))
