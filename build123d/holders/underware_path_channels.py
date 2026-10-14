# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Underware for openGrid path channels — S, diagonal and mitre — adapted
under CC BY-NC-SA 4.0.

[C] monokini_S_channel.scad:38-99, monokini_diagonal_channel.scad:38-99 and
monokini_mitre_channel.scad:36-99 (parameters) — Pedro Leite; source and
reference pins in assets/underware-opengrid/NOTICE. Geometry:
build123d/underware/path.py.

Two registered models: S and diagonal share the author's parameter shape
(width, height, two run lengths, units over / up), the mitre does not (one
pair of arm lengths, Mirror_Channel, Added_Radius), and Param is global per
ModelSpec.

S / diagonal frame = print frame: Z up, the closed, chamfered face on the
bed, the openGrid grips up (+Z); the bottom run runs along +Y to the
connector, the top run leaves it along +Y offset units_over cells in X.
Worst load: cables pulling the channel off the board, along +Z on the grip
nubs; the grips and walls carry it along the layers. PLA or PCTG, no supports.

Mitre: the first channel runs along Y as the S's bottom run, then bends 90
degrees down about the width axis (floor inside) into a second channel along
-Z. It prints rotated 45 degrees about X (print_frame), both arms rising 45
degrees from the bend.

Not ported: the label (U4b, underware_text_label), Decorative /
Support_Bridging_Separation (as underware_i_channel). Deviations are listed in
the NOTICE: S/diagonal cord cutouts cut the bottom run's walls (the source
cuts only its grips), and named errors bound the S bend radius and the
diagonal mitre.
"""
from build123d import Location, Plane, mirror
from holders.printer import BED_X, BED_Y
from holders.registry import ModelSpec, Param, Preset, register
from underware import constants as c
from underware import junction as j
from underware import path as p
from underware.channel import CUTOUT_SIDES, cell_centres, check_cutouts, cutout_sill_regions, present_grips
from underware.grip import end_ramp_regions, slit_floor_regions

MAX_RUN = 9
MAX_OVER = 10
MAX_UP = 9      # (1 + 1 + 10) cells of the shortest part already pass the 325 mm bed


def _cut_args(v):
    return dict(number=v['number_of_cord_cutouts'], side=v['cord_side_cutouts'],
                cutout_width=v['cord_cutout_width'], spacing=v['distance_between_cutouts'],
                shift=v['shift_cutouts'])


def path_runs(v):
    return p.runs(v['channel_width_units'], v['length_bottom_units'], v['length_top_units'],
                  v['units_over'], v['units_up'], v['suppress_connectors'])


def check_path(v) -> None:
    """Named errors for the S / diagonal connector, before any geometry."""
    w = c.channel_width(v['channel_width_units'])
    over, up = v['units_over'], v['units_up']
    if over == 0:
        raise ValueError('units_over 0 is a straight channel; use underware_i_channel')
    dx, dy = p.offsets(over, up)
    if v['part'] == 'S':
        r = p.bezier_min_radius(dx, dy)
        if r < w/2:
            raise ValueError(
                f'the S bend over {over} / up {up} cells turns at a {r:.1f} mm radius, under the '
                f'{w/2:g} mm half-width: the inner wall would fold; raise units_up, or lower '
                f'units_over or the width')
    else:
        turn = p.corner_turn(dx, dy)
        back = p.mitre_setback(w, turn)
        if back > p.MAX_SETBACK:
            raise ValueError(
                f'the diagonal turns {turn:.1f} degrees at each corner: the inside wall ends '
                f'{back:.1f} mm before the corner, past the {p.MAX_SETBACK:g} mm the end grip '
                f'stands back, so its foot would overhang; raise units_up, or lower units_over or the width')
    span_x, span_y = abs(dx) + w, (v['length_bottom_units'] + v['length_top_units'] + up)*c.GRID
    a, b = sorted((span_x, span_y), reverse=True)
    if a > BED_X or b > BED_Y:
        raise ValueError(f'the channel is {span_x:.1f} x {span_y:.1f} mm, past the {BED_X:g} x '
                         f'{BED_Y:g} mm bed; shorten a run or move fewer cells')


def _checked_path(values):
    v = SPEC_PATH.resolve_values(values)
    check_path(v)
    first, second = path_runs(v)
    h = v['channel_total_height']
    check_cutouts(first.width, h, cell_centres(first.length), first.suppress,
                  grip_flare=v['grip_flare'], **_cut_args(v))
    j.check_cutout_span(j.Arm(first.length, first.width, first.x, first.y, 0),
                        v['number_of_cord_cutouts'], v['distance_between_cutouts'],
                        v['shift_cutouts'], v['cord_cutout_width'])
    return v, first, second


def build_path_channel(values=None):
    v, first, second = _checked_path(values)
    h = v['channel_total_height']
    cutters = j.first_arm_cutters(first.width, h, **_cut_args(v))
    return p.build_path(v['part'], first, second, h, separators=v['channel_separators'].split(',')[0],
                        grip_flare=v['grip_flare'], cutters=cutters)


def _checked_mitre(values):
    v = SPEC_MITRE.resolve_values(values)
    first = p.mitre_first(v['channel_width_units'], v['length_y_units'], v['added_radius'],
                          v['suppress_connectors'], v['channel_separators'])
    h = v['channel_total_height']
    check_cutouts(first.width, h, cell_centres(first.length), first.suppress,
                  grip_flare=v['grip_flare'], **_cut_args(v))
    j.check_cutout_span(first, v['number_of_cord_cutouts'], v['distance_between_cutouts'],
                        v['shift_cutouts'], v['cord_cutout_width'])
    return v, first


def build_mitre(values=None):
    v, first = _checked_mitre(values)
    h = v['channel_total_height']
    return p.build_mitre(v['channel_width_units'], h, v['length_y_units'], v['length_down_units'],
                         mirrored=v['mirror_channel'], added_radius=v['added_radius'],
                         suppress=v['suppress_connectors'], separators=v['channel_separators'],
                         grip_flare=v['grip_flare'],
                         cutters=j.first_arm_cutters(first.width, h, **_cut_args(v)))


def mitre_print_frame(values) -> Location:
    """45 degrees about X: the (0, -1, -1) diagonal points down, so both arms
    rise 45 degrees from the bend."""
    return Location((0, 0, 0), (45, 0, 0))


def grips(name, values=None):
    """(location, y_cell, side, flared) for every grip, in the model frame."""
    if name == SPEC_PATH.name:
        v, first, second = _checked_path(values)
        return [(run.location, *g) for run in (first, second)
                for g in present_grips(run.length, run.suppress, v['grip_flare'])]
    v, first = _checked_mitre(values)
    f = j.split_fields('suppress_connectors', v['suppress_connectors'], 2)
    second = p.mitre_second_location(v['channel_width_units'], v['channel_total_height'],
                                     v['length_down_units'], v['added_radius'])
    return ([(first.location, *g) for g in first.grips(v['grip_flare'])]
            + [(second, *g) for g in present_grips(v['length_down_units']*c.GRID, f[1], v['grip_flare'])])


def audit_exclusions(name, values=None) -> dict:
    """Published-exception envelopes by family, as underware_i_channel's
    (grip-end-wedge, flare-slit-fin, cutout-sill), placed on each run or arm.
    The connectors add none: the section swept along a path in the bed plane
    keeps every face's angle, and the mitre bend turns it about the width axis
    in the 45 degree frame. Model frame (the audit applies print_frame)."""
    v = (SPEC_PATH if name == SPEC_PATH.name else SPEC_MITRE).resolve_values(values)
    h, flare = v['channel_total_height'], v['grip_flare']
    w = c.channel_width(v['channel_width_units'])
    out = {'grip-end-wedge': [], 'flare-slit-fin': [], 'cutout-sill': []}
    for loc, y, side, flared in grips(name, values):
        out['grip-end-wedge'] += [loc*r for r in end_ramp_regions(w, h, y, side, flare if flared else 0.)]
        if flared:
            out['flare-slit-fin'] += [loc*r for r in slit_floor_regions(w, h, y, side)]
    first_loc = (path_runs(v)[0].location if name == SPEC_PATH.name else
                 _checked_mitre(values)[1].location)
    out['cutout-sill'] = [first_loc*r for r in cutout_sill_regions(w, **_cut_args(v))]
    if name == SPEC_MITRE.name and v['mirror_channel']:
        out = {k: [mirror(r, Plane.YZ) for r in regions] for k, regions in out.items()}
    return out


def _shared_params(cutout_sides, channels):
    return (
        Param('channel_width_units', 'integer', 1, min=1, max=4, step=1, filename=True,
              group='Channel Size', label='Width (28 mm units)'),
        Param('channel_total_height', 'number', 22, min=10, max=72, step=6, filename=True,
              group='Channel Size', unit='mm', label='Height including grips'),
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
        Param('channel_separators', 'string', '', group='Advanced',
              label='Separator walls (N/S per midline)', max_length=24, charset='printable-ascii'),
    )


BLURB = ('Snaps into openGrid; set sizes in 28 mm cells and the height, with optional cord '
         'exits on the first channel and per-cell grip suppression. By Pedro Leite (Underware '
         '2.0), CC BY-NC-SA 4.0 (non-commercial, share-alike).')

SPEC_PATH = register(ModelSpec(
    name='underware_path_channel',
    title='Underware S / diagonal cable channel (openGrid)',
    description='Underware "monokini" channel that jogs sideways: two straight runs joined by '
                'an S curve or a straight diagonal. ' + BLURB + ' Prints as shown, closed face '
                'down, no supports.',
    category_id='multiboard',
    build=build_path_channel,
    params=(
        Param('part', 'enum', 'S', choices=p.PARTS, filename=True, group='Channel Size',
              label='Connector'),
        *_shared_params(j.CUTOUT_SIDES_X, 'bottom run, top run')[:2],
        Param('length_bottom_units', 'integer', 1, min=1, max=MAX_RUN, step=1, filename=True,
              group='Channel Size', label='Bottom run (28 mm units)'),
        Param('length_top_units', 'integer', 1, min=1, max=MAX_RUN, step=1, filename=True,
              group='Channel Size', label='Top run (28 mm units)'),
        Param('units_over', 'integer', 2, min=-MAX_OVER, max=MAX_OVER, step=1, filename=True,
              group='Channel Size', label='Cells over (X)'),
        Param('units_up', 'integer', 2, min=1, max=MAX_UP, step=1, filename=True,
              group='Channel Size', label='Cells up (Y)'),
        *_shared_params(j.CUTOUT_SIDES_X, 'bottom run, top run')[2:],
    ),
    presets=(
        Preset('S', 'S curve, 2 cells over, 2 up', {}),
        Preset('S-wide', 'S curve, 2 wide, 1 over, 2 up', {'channel_width_units': 2, 'units_over': 1}),
        Preset('diagonal', 'Diagonal, 2 cells over, 2 up', {'part': 'diagonal'}),
        Preset('diagonal-wide-tall', 'Diagonal, 2 wide, 34 mm, 1 over, 3 up',
               {'part': 'diagonal', 'channel_width_units': 2, 'channel_total_height': 34,
                'units_over': 1, 'units_up': 3}),
    ),
))

# Deliberately NOT registered (mayor ruling on pst-fsk8s.3, option C): the 45
# degree frame stands the mitre on two edges with no bed face, and the bend's
# arch underside fails the overhang audit there (the author's own mesh too).
# The geometry and its parity tests ship; the print strategy and the catalog
# entry are pst-1nv9a.
SPEC_MITRE = ModelSpec(
    name='underware_mitre',
    title='Underware mitre cable-channel corner (openGrid)',
    description='Underware "monokini" channel that turns 90° from one openGrid board onto a '
                'perpendicular one (inside corner), with an optional larger bend radius. '
                + BLURB,
    category_id='multiboard',
    build=build_mitre,
    print_frame=mitre_print_frame,
    params=(
        *_shared_params(CUTOUT_SIDES, 'first arm, second arm')[:2],
        Param('length_y_units', 'integer', 1, min=1, max=MAX_RUN, step=1, filename=True,
              group='Channel Size', label='First arm (28 mm units)'),
        Param('length_down_units', 'integer', 1, min=1, max=MAX_RUN, step=1, filename=True,
              group='Channel Size', label='Second arm (28 mm units)'),
        Param('mirror_channel', 'boolean', False, group='Channel Size', filename=True,
              label='Mirror'),
        Param('added_radius', 'integer', 0, min=0, max=2, step=1, group='Channel Size', filename=True,
              label='Added bend radius (28 mm units)'),
        *_shared_params(CUTOUT_SIDES, 'first arm, second arm')[2:],
    ),
    presets=(
        Preset('mitre', '1 × 1 arms, 22 mm', {}),
        Preset('mitre-wide', '2 wide, 28 mm, added radius 1', {'channel_width_units': 2,
                                                              'channel_total_height': 28,
                                                              'added_radius': 1}),
    ),
)
