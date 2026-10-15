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
-Z. One arm length drives both arms. It prints rotated 45 degrees about X
(print_frame), both arms rising 45 degrees from the bend and standing on a
bed flat cut across the two arm tips (bed_flat): equal arms put the tips
(cw - w)/(2 sqrt 2) = 0.566 mm apart in that frame, and the cut plane sits
BED_FLAT_MM above the higher tip. Worst load: cables pulling either arm off
its board, along that arm's grips, carried along the layers. A 90 degree bend
has no support-free orientation: the arch underside (the floor's cylinder at
the bend radius) is printed as the author models it, supports optional under
the bend, through one published exception (ArchUnderside, approver: mayor,
pst-1nv9a).

Not ported: the label (U4b, underware_text_label), Decorative /
Support_Bridging_Separation (as underware_i_channel). Deviations are listed in
the NOTICE: S/diagonal cord cutouts cut the bottom run's walls (the source
cuts only its grips), named errors bound the S bend radius and the diagonal
mitre, the mitre has one arm length and a bed flat across its arm tips.
"""
from math import hypot, radians, sin, sqrt

from build123d import Align, Box, Location, Plane, Pos, mirror
from holders.printer import BED_X, BED_Y, BED_Z
from holders.registry import ModelSpec, Param, Preset, register
from underware import constants as c
from underware import junction as j
from underware import path as p
from underware.channel import CUTOUT_SIDES, cell_centres, check_cutouts, cutout_sill_regions, present_grips
from underware.grip import end_ramp_regions, slit_floor_regions

MAX_RUN = 9
MAX_OVER = 10
MAX_UP = 9      # (1 + 1 + 10) cells of the shortest part already pass the 325 mm bed
MAX_ARM = 7     # mitre: 8 cells stand past the 325 mm bed at 45 degrees even at width 1, h 10


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
    l1, l2 = v['length_bottom_units']*c.GRID, v['length_top_units']*c.GRID
    span_x, span_y = abs(dx) + w, l1 + l2 + up*c.GRID
    if v['part'] == 'diagonal':
        # the round outer fill at each vertex reaches (w/2)*sin(turn) past it,
        # beyond a run shorter than that
        e = w/2*sin(radians(turn))
        span_y += max(0., e - l1) + max(0., e - l2)
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


def mitre_values(values=None, *, length_y=None, length_down=None):
    """Registered values plus the builder's two arm lengths, both from
    length_units. Only the parity references pass an unequal pair (the
    author's mesh with a 2-cell first arm): the bed flat needs equal arms, so
    the registered spec cannot express inequality."""
    v = dict(SPEC_MITRE.resolve_values(values))
    v['length_y_units'] = v['length_units'] if length_y is None else length_y
    v['length_down_units'] = v['length_units'] if length_down is None else length_down
    return v


def mitre_extent(v) -> tuple[float, float, float]:
    """(span, width, height) of the finished mitre in its 45 degree print
    frame, from model-frame corners (y' = (y - z)/sqrt 2, z' = (y + z)/sqrt 2).
    The span runs between the arm tips' wall-top corners (the grips stand
    SPACING_FROM_CHANNEL back from each tip), the height from the bed flat to
    the gripless bend's wall top, radius r + h - BASE_HEIGHT, at 45 degrees."""
    h, cw, w = v['channel_total_height'], v['channel_width_units']*c.GRID, c.channel_width(v['channel_width_units'])
    l1, l2 = v['length_y_units']*c.GRID, v['length_down_units']*c.GRID
    r, top = p.mitre_radius(h, v['added_radius']), h - c.BASE_HEIGHT
    span = (l1 + l2 + cw/2 + 2*top + 2*r - w/2)/sqrt(2)
    bed = -min(l1 + cw/2, l2 + w/2)/sqrt(2) + BED_FLAT_MM   # bed_plane: higher tip + the flat
    return span, w, (r + top) - (r + w/2)/sqrt(2) - bed


def _checked_mitre(values, **arms):
    v = mitre_values(values, **arms)
    span, w, height = mitre_extent(v)
    if max(span, w) > BED_X or min(span, w) > BED_Y or height > BED_Z:
        raise ValueError(f'the mitre stands {span:.1f} x {w:.1f} x {height:.1f} mm in its 45 degree '
                         f'print frame, past the {BED_X:g} x {BED_Y:g} x {BED_Z:g} mm build volume; '
                         f'shorten the arms, or lower the height or the added radius')
    first = p.mitre_first(v['channel_width_units'], v['length_y_units'], v['added_radius'],
                          v['suppress_connectors'], v['channel_separators'])
    h = v['channel_total_height']
    check_cutouts(first.width, h, cell_centres(first.length), first.suppress,
                  grip_flare=v['grip_flare'], **_cut_args(v))
    j.check_cutout_span(first, v['number_of_cord_cutouts'], v['distance_between_cutouts'],
                        v['shift_cutouts'], v['cord_cutout_width'])
    return v, first


def author_mitre(values=None, **arms):
    """The author's mitre before the bed flat: the solid the parity
    references are measured against (S8: parity on the pre-treatment solid)."""
    v, first = _checked_mitre(values, **arms)
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


# Cut into the higher arm tip. The plane then sits 0.566 + 0.6 = 1.166 mm
# above the lower tip: ~70 mm2 of bed at width 1 (60 needs 1.05 mm) and a
# 1.19 mm tip wall (MIN_WALL_MM 0.9 holds to ~1.38 mm), both clear of their
# limits; the arm ends only butt against the next channel (NOTICE deviation).
BED_FLAT_MM = 0.6


def bed_plane(part, frame) -> tuple[float, float, float]:
    """(lower tip, higher tip, cut plane) heights in the print frame. The
    first arm's tip (y < 0 in that frame) and the second's (y > 0) each meet
    the bed at their lowest vertex, the closed face's tip edge."""
    vs = [tuple(v) for v in (frame*part).vertices()]
    lower, higher = sorted(min(z for _, y, z in vs if side*y > 0) for side in (-1, 1))
    return lower, higher, higher + BED_FLAT_MM


def bed_flat(part, frame):
    """Cut everything below bed_plane, so both arm tips land on one plane."""
    *_, z = bed_plane(part, frame)
    size = 2*part.bounding_box().diagonal
    return part - frame.inverse()*Pos(0, 0, z)*Box(size, size, size,
                                                   align=(Align.CENTER, Align.CENTER, Align.MAX))


def build_mitre(values=None):
    return bed_flat(author_mitre(values), mitre_print_frame(SPEC_MITRE.resolve_values(values)))


class ArchUnderside:
    """Exact surface envelope of the mitre bend's floor underside: the
    cylinder of the bend radius r about the X-parallel axis through
    (y = -w/2, z = -r), the bend's quadrant only (y >= -w/2, z >= -r), within
    the channel's width. The one published exception of underware_mitre
    (overhang 90 degrees at the crown and a downward curved face in the 45
    degree frame); it exempts no chamfer, wall, grip or arm face.

    ``frame * ArchUnderside`` (the audit's print_frame) is the envelope placed
    in that frame; ``inverse`` is the 3x4 row-major map from the current frame
    back to the model frame, plain floats so the audit cache can key it."""
    def __init__(self, x0, x1, axis_y, axis_z, radius, inverse=None):
        self.x0, self.x1, self.axis_y, self.axis_z, self.radius = x0, x1, axis_y, axis_z, radius
        self.inverse = inverse or ((1., 0., 0., 0.), (0., 1., 0., 0.), (0., 0., 1., 0.))

    def __rmul__(self, loc):
        if not isinstance(loc, Location):
            return NotImplemented
        t = loc.inverse().wrapped.Transformation()
        m = [[t.Value(i, k) for k in range(1, 5)] for i in range(1, 4)]
        a = self.inverse   # model point = a(loc^-1(point))
        inverse = tuple(tuple(sum(a[i][k]*m[k][jj] for k in range(3)) + (a[i][3] if jj == 3 else 0.)
                              for jj in range(4)) for i in range(3))
        return ArchUnderside(self.x0, self.x1, self.axis_y, self.axis_z, self.radius, inverse)

    def is_inside(self, point, tolerance=1e-6):
        x, y, z = (sum(r[k]*point[k] for k in range(3)) + r[3] for r in self.inverse)
        return (self.x0 - tolerance <= x <= self.x1 + tolerance
                and y >= self.axis_y - tolerance and z >= self.axis_z - tolerance
                and abs(hypot(y - self.axis_y, z - self.axis_z) - self.radius) <= .001 + tolerance)


def arch_underside(values=None) -> ArchUnderside:
    """The bend's floor underside for these values (model frame, mirrored
    with the part)."""
    v, first = _checked_mitre(values)
    w, r = first.width, p.mitre_radius(v['channel_total_height'], v['added_radius'])
    x0, x1 = first.x - w/2, first.x + w/2
    if v['mirror_channel']:
        x0, x1 = -x1, -x0
    return ArchUnderside(x0, x1, -w/2, -r, r)


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
    The S / diagonal connectors add none: the section swept along a path in
    the bed plane keeps every face's angle. The mitre bend turns it about the
    width axis, so in the 45 degree frame its floor underside overhangs: the
    mitre adds that one surface (arch-underside, ArchUnderside). Model frame
    (the audit applies print_frame)."""
    v = SPEC_PATH.resolve_values(values) if name == SPEC_PATH.name else mitre_values(values)
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
    if name == SPEC_MITRE.name:
        if v['mirror_channel']:
            out = {k: [mirror(r, Plane.YZ) for r in regions] for k, regions in out.items()}
        out['arch-underside'] = [arch_underside(values)]
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

SPEC_MITRE = register(ModelSpec(
    name='underware_mitre',
    title='Underware mitre cable-channel corner (openGrid)',
    description='Underware "monokini" channel that turns 90° from one openGrid board onto a '
                'perpendicular one (inside corner), with an optional larger bend radius. '
                + BLURB + ' Prints standing on its two arm tips at 45°; supports optional '
                'under the bend.',
    category_id='multiboard',
    build=build_mitre,
    print_frame=mitre_print_frame,
    params=(
        *_shared_params(CUTOUT_SIDES, 'first arm, second arm')[:2],
        Param('length_units', 'integer', 1, min=1, max=MAX_ARM, step=1, filename=True,
              group='Channel Size', label='Arm length, both arms (28 mm units)'),
        Param('mirror_channel', 'boolean', False, group='Channel Size', filename=True,
              label='Mirror'),
        Param('added_radius', 'integer', 0, min=0, max=2, step=1, group='Channel Size', filename=True,
              label='Added bend radius (28 mm units)'),
        *_shared_params(CUTOUT_SIDES, 'first arm, second arm')[2:],
    ),
    presets=(
        Preset('mitre', '1 × 1 arms, 22 mm', {}),
        Preset('mitre-r1', '1 × 1 arms, 22 mm, added radius 1', {'added_radius': 1}),
    ),
))
