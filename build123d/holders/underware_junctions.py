# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Underware for openGrid L, T and X cable-channel junctions, adapted under
CC BY-NC-SA 4.0.

[C] monokini_L_channel.scad:38-99, monokini_T_channel.scad:38-99 and
monokini_X_channel.scad:38-99 (parameters) — Pedro Leite; source and
reference pins in assets/underware-opengrid/NOTICE. Geometry:
build123d/underware/junction.py.

Three registered models, not one with a part enum: Param is global per
ModelSpec and the files share no size set (L: one width, Mirror_Channel,
Added_Radius, Channel_Separators; T: three widths; X: one width, four arms,
a four-valued cutout enum).

Model frame = print frame: Z up, the closed, chamfered face on the bed, the
openGrid grips up (+Z); the first channel (L's Y arm, T's stem, X's bottom
arm) runs along -Y from the junction. Worst load: cables pulling the channel
off the board, along +Z on the grip nubs; the grips and walls carry it along
the layers. PLA or PCTG, no supports.

Not ported: the label (the author's label is MakerWorld-3MF-only, L:65 /
T:67 / X:65, and Text_x_coordinate is one-dimensional on a multi-arm part),
Decorative / Support_Bridging_Separation (as underware_i_channel). Arm lengths
stop where a single-parameter change still fits the H2S bed; longer
combinations are named errors. See the NOTICE deviations list.
"""
from holders.printer import BED_X
from holders.registry import ModelSpec, Param, Preset, register
from build123d import Plane, mirror
from underware import constants as c
from underware.channel import CUTOUT_SIDES, cell_centres, check_cutouts, cutout_sill_regions
from underware.grip import end_ramp_regions, slit_floor_regions
from underware import junction as j

# Longest arm a one-parameter change can set: L adds the one-cell corner, T and
# X span the node plus an arm each side (28*(9+1+1) = 308 mm on the 325 mm bed).
MAX_ARM_L = int(BED_X // c.GRID) - 1
MAX_ARM_TX = int(BED_X // c.GRID) - 2


def _cut_args(v):
    return dict(number=v['number_of_cord_cutouts'], side=v['cord_side_cutouts'],
                cutout_width=v['cord_cutout_width'], spacing=v['distance_between_cutouts'],
                shift=v['shift_cutouts'])


def _height(v):
    return v['channel_total_height']


def layout(name, v):
    """Arms (no geometry) for the resolved values of model `name`."""
    if name == 'underware_l':
        return j.l_arms(v['channel_width_units'], v['length_y_units'], v['length_x_units'],
                        v['added_radius'], v['suppress_connectors'], v['channel_separators'])
    if name == 'underware_t':
        return j.t_arms(v['width_bottom_units'], v['width_left_units'], v['width_right_units'],
                        v['stem_length_units'], v['left_length_units'], v['right_length_units'],
                        v['suppress_connectors'])
    return j.x_arms(v['channel_width_units'], v['bottom_length_units'], v['right_length_units'],
                    v['left_length_units'], v['top_length_units'], v['suppress_connectors'])


def _checked(name, values):
    """Resolve, then every named error before any geometry."""
    v = SPECS[name].resolve_values(values)
    arms = layout(name, v)
    j.check_bed(arms)
    first, h = arms[0], _height(v)
    check_cutouts(first.width, h, cell_centres(first.length), first.suppress,
                  grip_flare=v['grip_flare'], **_cut_args(v))
    j.check_cutout_span(first, v['number_of_cord_cutouts'], v['distance_between_cutouts'],
                        v['shift_cutouts'], v['cord_cutout_width'])
    return v, arms


def _build(name, values=None):
    v, arms = _checked(name, values)
    h, flare = _height(v), v['grip_flare']
    cutters = j.first_arm_cutters(arms[0].width, h, **_cut_args(v))
    if name == 'underware_l':
        return j.build_l(v['channel_width_units'], h, v['length_y_units'], v['length_x_units'],
                         mirrored=v['mirror_channel'], added_radius=v['added_radius'],
                         suppress=v['suppress_connectors'], separators=v['channel_separators'],
                         grip_flare=flare, cutters=cutters)
    if name == 'underware_t':
        return j.build_t(v['width_bottom_units'], v['width_left_units'], v['width_right_units'], h,
                         v['stem_length_units'], v['left_length_units'], v['right_length_units'],
                         suppress=v['suppress_connectors'], grip_flare=flare, cutters=cutters)
    return j.build_x(v['channel_width_units'], h, v['bottom_length_units'], v['right_length_units'],
                     v['left_length_units'], v['top_length_units'], suppress=v['suppress_connectors'],
                     grip_flare=flare, cutters=cutters)


def grips(name, values=None):
    """(arm, y_cell, side, flared) for every grip the junction carries."""
    v = SPECS[name].resolve_values(values)
    return [(arm, *g) for arm in layout(name, v) for g in arm.grips(v['grip_flare'])]


def audit_exclusions(name, values=None) -> dict:
    """Published-exception envelopes by family, as underware_i_channel's
    (grip-end-wedge, flare-slit-fin, cutout-sill), placed on each arm. The
    junction bodies add none: they are the channel section swept round the
    corner, open toward +Z, and the inside-corner post's chamfer revolves to
    a 45 degree cone."""
    v, arms = _checked(name, values)
    h = _height(v)
    out = {'grip-end-wedge': [], 'flare-slit-fin': [], 'cutout-sill': []}
    for arm in arms:
        for y, side, flared in arm.grips(v['grip_flare']):
            out['grip-end-wedge'] += [arm.location*r for r in end_ramp_regions(
                arm.width, h, y, side, v['grip_flare'] if flared else 0.)]
            if flared:
                out['flare-slit-fin'] += [arm.location*r for r in slit_floor_regions(arm.width, h, y, side)]
    out['cutout-sill'] = [arms[0].location*r for r in cutout_sill_regions(arms[0].width, **_cut_args(v))]
    if name == 'underware_l' and v['mirror_channel']:
        out = {k: [mirror(r, Plane.YZ) for r in regions] for k, regions in out.items()}
    return out


def _height_param():
    return Param('channel_total_height', 'number', 22, min=10, max=72, step=6, filename=True,
                 group='Channel Size', unit='mm', label='Height including grips')


def _width_param(name, label):
    return Param(name, 'integer', 1, min=1, max=4, step=1, filename=True,
                 group='Channel Size', label=label)


def _arm_param(name, label, maximum):
    return Param(name, 'integer', 1, min=1, max=maximum, step=1, filename=True,
                 group='Channel Size', label=label)


def _shared_params(cutout_sides, channels):
    return (
        Param('number_of_cord_cutouts', 'integer', 0, min=0, max=12, step=1,
              group='Cord Cutouts', label='Number of cord cutouts (first channel)'),
        Param('cord_side_cutouts', 'enum', 'Both Sides', choices=cutout_sides,
              group='Cord Cutouts', label='Cutout side'),
        Param('cord_cutout_width', 'number', 12, min=6, max=20, step=1,
              group='Cord Cutouts', unit='mm', label='Cutout width'),
        Param('distance_between_cutouts', 'number', 28, min=14, max=56, step=1,
              group='Cord Cutouts', unit='mm', label='Distance between cutouts'),
        Param('shift_cutouts', 'number', 0, min=0, max=28, step=1,
              group='Cord Cutouts', unit='mm', label='Shift cutouts along the channel'),
        Param('grip_flare', 'number', 0, min=0, max=15, step=0.1,
              group='Advanced', unit='deg', label='Grip flare'),
        Param('suppress_connectors', 'string', '', group='Advanced',
              label=f'Suppress grips per cell (N/L/R/B/S; comma per channel: {channels})',
              max_length=48, charset='printable-ascii'),
    )


BLURB = ('Snaps into openGrid; set sizes in 28 mm cells and the height, with optional cord '
         'exits on the first channel and per-cell grip suppression. By Pedro Leite (Underware '
         '2.0), CC BY-NC-SA 4.0 (non-commercial, share-alike). Prints as shown, closed face '
         'down, no supports.')

SPEC_L = register(ModelSpec(
    name='underware_l',
    title='Underware L cable-channel corner (openGrid)',
    description='90° Underware "monokini" channel corner with two arms, optional mirroring and '
                'a larger bend radius. ' + BLURB,
    category_id='multiboard',
    build=lambda values=None: _build('underware_l', values),
    params=(
        _width_param('channel_width_units', 'Width (28 mm units)'),
        _height_param(),
        _arm_param('length_y_units', 'Arm along Y (28 mm units)', MAX_ARM_L),
        _arm_param('length_x_units', 'Arm along X (28 mm units)', MAX_ARM_L),
        Param('mirror_channel', 'boolean', False, group='Channel Size', label='Mirror (arm along -X)'),
        Param('added_radius', 'integer', 0, min=0, max=2, step=1, group='Channel Size',
              label='Added bend radius (28 mm units)'),
        *_shared_params(CUTOUT_SIDES, 'Y arm, X arm'),
        Param('channel_separators', 'string', '', group='Advanced',
              label='Separator walls (N/S per midline)', max_length=24, charset='printable-ascii'),
    ),
    presets=(
        Preset('L', '1 × 1 arms, 22 mm', {}),
        Preset('L-mirrored', 'Mirrored, 1 × 1 arms', {'mirror_channel': True}),
        Preset('L-tall', '2 wide, 2 × 2 arms, 34 mm', {'channel_width_units': 2, 'length_y_units': 2,
                                                         'length_x_units': 2, 'channel_total_height': 34}),
    ),
))

SPEC_T = register(ModelSpec(
    name='underware_t',
    title='Underware T cable-channel junction (openGrid)',
    description='Underware "monokini" T junction: a stem and two arms, each with its own width '
                'and length. ' + BLURB,
    category_id='multiboard',
    build=lambda values=None: _build('underware_t', values),
    params=(
        _width_param('width_bottom_units', 'Stem width (28 mm units)'),
        _width_param('width_left_units', 'Left arm width (28 mm units)'),
        _width_param('width_right_units', 'Right arm width (28 mm units)'),
        _height_param(),
        _arm_param('stem_length_units', 'Stem length (28 mm units)', MAX_ARM_L),
        _arm_param('left_length_units', 'Left arm length (28 mm units)', MAX_ARM_TX),
        _arm_param('right_length_units', 'Right arm length (28 mm units)', MAX_ARM_TX),
        *_shared_params(CUTOUT_SIDES, 'stem, right arm, left arm, node'),
    ),
    presets=(
        Preset('T', '1 × 1 × 1 arms, 22 mm', {}),
        Preset('T-tall', '2 × 2 × 2 arms, 34 mm', {'stem_length_units': 2, 'left_length_units': 2,
                                                     'right_length_units': 2, 'channel_total_height': 34}),
    ),
))

SPEC_X = register(ModelSpec(
    name='underware_x',
    title='Underware X cable-channel crossing (openGrid)',
    description='Underware "monokini" four-way crossing with four arm lengths. ' + BLURB,
    category_id='multiboard',
    build=lambda values=None: _build('underware_x', values),
    params=(
        _width_param('channel_width_units', 'Width (28 mm units)'),
        _height_param(),
        _arm_param('bottom_length_units', 'Bottom arm length (28 mm units)', MAX_ARM_TX),
        _arm_param('right_length_units', 'Right arm length (28 mm units)', MAX_ARM_TX),
        _arm_param('left_length_units', 'Left arm length (28 mm units)', MAX_ARM_TX),
        _arm_param('top_length_units', 'Top arm length (28 mm units)', MAX_ARM_TX),
        *_shared_params(j.CUTOUT_SIDES_X, 'bottom, right, left, top'),
    ),
    presets=(
        Preset('X', '1 × 1 × 1 × 1 arms, 22 mm', {}),
        Preset('X-tall', '2 × 2 × 2 × 2 arms, 34 mm', {'bottom_length_units': 2, 'right_length_units': 2,
                                                         'left_length_units': 2, 'top_length_units': 2,
                                                         'channel_total_height': 34}),
    ),
))

SPECS = {s.name: s for s in (SPEC_L, SPEC_T, SPEC_X)}
