# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Underware for openGrid transitions (width change, height change, bridge),
adapted under CC BY-NC-SA 4.0.

[W] monokini_I_width_change_channel.scad, [H]
monokini_I_height_change_channel.scad, [B] monokini_I_bridge_channel.scad —
Pedro Leite after Hands on Katie and BlackjackDuck; source and reference pins
in assets/underware-opengrid/NOTICE. Geometry: build123d/underware/transition.py.

Parameters are the union of the three files' customizers ([W] :39-104, [H]
:39-103, [B] :37-105); a parameter that does not apply to the selected part is
ignored:
- from_width_units / to_width_units: [W] Channel_Width_in_Units_1 / _2 (from
  at +Y). height_change and bridge use from_width_units as their
  Channel_Width_in_Units and ignore to_width_units.
- from_height / to_height: [H] and [B] Channel_Internal_Height_1 / _2 (for
  the bridge, to_height is the channel height over the crossed channel).
  width_change uses from_height as its Channel_Internal_Height.
- bridge_height, bridge_length_units, half_bridge: [B] only.
- channel_length_units, transition_length_units: [W] Channel_Length_Units /
  Rise_Distance_Units and [H] Channel_Length_Units / Rise_Distance (the [H]
  source takes millimetres in 12.5 mm steps, default 25; the port uses whole
  28 mm cells for both, as the bridge's own hidden Rise_Distance = 28 does).

Print frames: width_change and bridge print as modelled (closed face down,
grips up). height_change prints STANDING ON END, the lower end on the bed
(print_frame): base-down its raised floor is a flat ceiling and on its side the
far wall overhangs the channel (epic pst-fsk8s.4 rev 4). Worst load: cables
pulling the channel off the board (+Z on the grip nubs); the grip rails and
walls carry it (base-down along the layers; standing, the walls run up the
layers and each grip rail is a continuous vertical extrusion).

Domains the author leaves unprintable are named errors, not geometry changes:
- every ruled floor slope must stay within 45 degrees of the print frame's
  vertical: height_change needs |from - to| <= the transition length, and
  the bridge needs its ramps (rise max(bridge, from) + to - from over one
  28 mm cell) at least that steep;
- height_change takes no cord cutouts, label or grip flare: standing, their
  slot ceilings and glyph recesses are flat overhangs;
- grip_flare <= 9.9 and per-cell suppress codes as the I channel.
Not ported: Decorative / Support_Bridging_Separation, Text_x_coordinate,
Font, colours (as the I channel; see its header and the NOTICE).
"""
from math import atan2, degrees, hypot

from build123d import Box, Pos, Rot

from holders.printer import BED_X, BED_Z
from holders.registry import ModelSpec, Param, Preset, register
from labels.constants import MAX_TEXT_LENGTH, TEXT_CHARSET
from underware import constants as c
from underware import transition as t
from underware.channel import MAX_FLARE_DEG, cutout_sill_regions, label_cutter
from underware.grip import end_ramp_regions, slit_floor_regions

PARTS = ('width_change', 'height_change', 'bridge')
HEIGHT_MIN, HEIGHT_MAX, HEIGHT_STEP = 10, 72, 6
# Longest part on the bed (base-down) or under the gantry (standing): 11 cells.
MAX_LENGTH_UNITS = int(min(BED_X, BED_Z) // c.GRID)
# A full bridge is the run plus one rise cell at each end.
MAX_BRIDGE_UNITS = int(BED_X // c.GRID) - 2
MIN_WALL = 0.9   # tests/print_audit.py MIN_WALL_MM
# Steepest bridge ramp whose 2 mm floor stays MIN_WALL thick across its slope:
# SNAP_WALL*G/hypot(rise, G) >= MIN_WALL.
MAX_BRIDGE_RISE = 55


def dimensions(v):
    """(width, length, height) of the part's footprint and grip plane."""
    part = v['part']
    if part == 'width_change':
        width = max(c.channel_width(v['from_width_units']), c.channel_width(v['to_width_units']))
        return width, v['channel_length_units']*c.GRID, v['from_height']
    width = c.channel_width(v['from_width_units'])
    if part == 'height_change':
        return width, v['channel_length_units']*c.GRID, max(v['from_height'], v['to_height'])
    run = t.bridge_run_length(v['bridge_length_units'], v['half_bridge'])
    over = t.over_bridge_height(v['from_height'], v['to_height'], v['bridge_height'])
    length = run/2 + c.GRID if v['half_bridge'] else run + 2*c.GRID
    return width, length, over


def _check_height(name, value):
    if value not in (HEIGHT_MIN, HEIGHT_MAX) and (value - HEIGHT_MIN) % HEIGHT_STEP:
        raise ValueError(f'{name} {value:g} mm is off the {HEIGHT_STEP} mm height steps '
                         f'({HEIGHT_MIN}, {HEIGHT_MIN + HEIGHT_STEP}, ... {HEIGHT_MAX})')


def _check_common(v):
    for name in ('from_height', 'to_height', 'bridge_height'):
        _check_height(name, v[name])
    if v['grip_flare'] > MAX_FLARE_DEG:
        raise ValueError(f'grip_flare above {MAX_FLARE_DEG:g} degrees leaves the flared grip base '
                         f'overhanging the wall chamfer (a flat, unsupported ledge)')
    if v['add_label'] and v['text_depth'] <= 0:
        raise ValueError('text_depth 0 makes no label in a single-material part; use 0.2 or more')


def _cut_args(v):
    return dict(number=v['number_of_cord_cutouts'], side=v['cord_side_cutouts'],
                cutout_width=v['cord_cutout_width'], spacing=v['distance_between_cutouts'],
                shift=v['shift_cutouts'])


def _has_cutouts(v):
    return v['cord_side_cutouts'] != 'None' and v['number_of_cord_cutouts'] > 0


def _cut_walls(side):
    return {'Left Side': (1,), 'Right Side': (-1,), 'Both Sides': (1, -1)}.get(side, ())


def _check_width_change_cutouts(v, length, rise, grips):
    """Each opening must sit on a straight end, cut the wall it names, and clear
    every grip on that wall (the I channel's rule: a crossed grip leaves a
    stub thinner than the wall floor)."""
    if not _has_cutouts(v):
        return
    wide = max(c.channel_width(v['from_width_units']), c.channel_width(v['to_width_units']))
    r = v['cord_cutout_width']/2
    for y in t.cutout_centres(v['number_of_cord_cutouts'], v['distance_between_cutouts'], v['shift_cutouts']):
        if y + r > -rise/2 and y - r < rise/2:
            raise ValueError(f'the cord cutout at y={y:g} mm reaches the {rise:g} mm transition '
                             f'(y {-rise/2:g}..{rise/2:g}); cutouts sit on the straight ends')
        if abs(y) + r > length/2:
            raise ValueError(f'the cord cutout at y={y:g} mm runs past the {length:g} mm channel end')
        units = v['to_width_units'] if y < 0 else v['from_width_units']
        width = c.channel_width(units)
        if v['cord_side_cutouts'] == 'Right Side' and width < wide:
            raise ValueError(f'a Right Side cord cutout at y={y:g} mm misses the narrow end\'s -X wall '
                             f'(the author\'s cutter spans x {-3*wide/4:g}..{-wide/4:g} mm)')
        for gy, side, flared, *_ in grips:
            reach = c.GRIP_SIZE/2 + (c.FLARE_SLIT + 0.9 if flared else 0.)
            if side in _cut_walls(v['cord_side_cutouts']) and abs(y - gy) < r + reach:
                raise ValueError(
                    f'the {v["cord_side_cutouts"]} cord cutout at y={y:g} mm crosses the grip at '
                    f'y={gy:g} mm on the {"+" if side > 0 else "-"}X wall; move it between grips '
                    f'or suppress that grip')


def _check_bridge_cutouts(v, run, over):
    if not _has_cutouts(v):
        return
    r = v['cord_cutout_width']/2
    low = 0. if v['half_bridge'] else -run/2
    wall_top = over - v['bridge_height']
    box_top = max(v['from_height'], v['to_height']) + c.SNAP_WALL
    if box_top < wall_top:
        raise ValueError(f'the cord cutouts stop at z={box_top:g} mm, below the {wall_top:g} mm wall '
                         f'top under the crossed channel, leaving an unsupported wall span over each opening')
    for y in t.cutout_centres(v['number_of_cord_cutouts'], v['distance_between_cutouts'], v['shift_cutouts']):
        if y - r < low or y + r > run/2:
            raise ValueError(f'the cord cutout at y={y:g} mm leaves the bridge run (y {low:g}..{run/2:g}); '
                             f'the author cuts the run only')


def check(values) -> dict:
    """Resolve and validate values; named errors for unprintable domains."""
    v = SPEC.resolve_values(values)
    _check_common(v)
    part = v['part']
    if part == 'bridge':
        run = t.bridge_run_length(v['bridge_length_units'], v['half_bridge'])
        over = t.over_bridge_height(v['from_height'], v['to_height'], v['bridge_height'])
        rise = over - v['from_height']
        if rise > MAX_BRIDGE_RISE:
            raise ValueError(
                f'a bridge rising {rise:g} mm over one {c.GRID:g} mm cell tilts its 2 mm floor to '
                f'{c.SNAP_WALL*c.GRID/hypot(rise, c.GRID):.2f} mm thick (under 0.9): lower to_height or '
                f'bridge_height until max(bridge, from) + to - from <= {MAX_BRIDGE_RISE:g}')
        if rise < c.GRID:
            raise ValueError(
                f'a bridge rising {rise:g} mm over one {c.GRID:g} mm cell leaves its ramp undersides '
                f'{90 - degrees(atan2(rise, c.GRID)):.1f} degrees '
                f'from vertical (over 45): raise to_height or bridge_height until '
                f'max(bridge, from) + to - from >= {c.GRID:g}')
        fields = v['suppress_connectors'].split(',')
        if len(fields) > 2:
            raise ValueError(f'suppress_connectors {v["suppress_connectors"]!r}: a bridge takes two '
                             f'comma fields (+Y end, -Y end)')
        for field in fields:
            t.parse_codes('suppress_connectors', field, t.SUPPRESS_CODES, 1)
        _check_bridge_cutouts(v, run, over)
        if v['add_label'] and v['half_bridge']:
            raise ValueError('a half bridge keeps only y >= 0 of its run, which would halve the '
                             'centred label; label a full bridge')
        return v
    length = v['channel_length_units']*c.GRID
    rise = v['transition_length_units']*c.GRID
    if rise >= length:
        raise ValueError(f'transition_length_units {v["transition_length_units"]} leaves no straight end '
                         f'on the {v["channel_length_units"]}-cell channel: the end face would meet the '
                         f'sloped wall or floor in a thin wedge; use a longer channel')
    if part == 'height_change':
        step = abs(v['from_height'] - v['to_height'])
        if step > rise:
            raise ValueError(
                f'a {step:g} mm height change over a {rise:g} mm transition slopes the floor more than '
                f'45 degrees standing on end; use transition_length_units >= {-(-step//c.GRID):g}')
        for name, on in (('cord cutouts', _has_cutouts(v)), ('a label', v['add_label']),
                         ('grip_flare', v['grip_flare'] > 0)):
            if on:
                raise ValueError(f'height_change prints standing on end, where {name} leave flat '
                                 f'overhangs; use a straight channel next to it instead')
        t.height_change_grips(length, rise, c.channel_width(v['from_width_units']), v['from_height'],
                              v['to_height'], v['suppress_connectors'])
        return v
    jog = abs(c.channel_width(v['from_width_units']) - c.channel_width(v['to_width_units']))
    if c.SNAP_WALL*rise/hypot(rise, jog) < MIN_WALL:
        raise ValueError(
            f'a {jog:g} mm width change over a {rise:g} mm transition slants the -X wall to '
            f'{c.SNAP_WALL*rise/hypot(rise, jog):.2f} mm thick (under {MIN_WALL:g}); use a longer '
            f'transition_length_units')
    grips = t.width_change_grips(length, rise, c.channel_width(v['from_width_units']),
                                 c.channel_width(v['to_width_units']), v['from_height'],
                                 v['suppress_connectors'], v['grip_flare'])
    _check_width_change_cutouts(v, length, rise, grips)
    return v


def _label(v, width, length):
    return label_cutter(v['text'], v['text_size'], v['text_depth'], width, length)


def build(values=None):
    v = check(values)
    part = v['part']
    width, length, height = dimensions(v)
    if part == 'height_change':
        return t.height_change_channel(length, v['transition_length_units']*c.GRID, width,
                                       v['from_height'], v['to_height'],
                                       suppress=v['suppress_connectors'])
    if part == 'bridge':
        run = t.bridge_run_length(v['bridge_length_units'], v['half_bridge'])
        cutters = t.side_cutouts(width, max(v['from_height'], v['to_height']), **_cut_args(v))
        if v['add_label']:
            cutters.append(_label(v, width, run))
        return t.bridge_channel(width, v['from_height'], v['to_height'], v['bridge_height'],
                                v['bridge_length_units'], half=v['half_bridge'],
                                suppress=v['suppress_connectors'], grip_flare=v['grip_flare'],
                                run_cutters=cutters)
    rise = v['transition_length_units']*c.GRID
    body = t.width_change_channel(length, rise, c.channel_width(v['from_width_units']),
                                  c.channel_width(v['to_width_units']), height,
                                  suppress=v['suppress_connectors'], grip_flare=v['grip_flare'])
    cutters = t.side_cutouts(width, height, **_cut_args(v))
    if v['add_label']:
        label = _label(v, width, length)
        if (label - body).volume > 1e-6:
            raise ValueError(f'label {v["text"]!r} at size {v["text_size"]:g} runs off the closed face '
                             f'where the channel narrows; shorten it or use a smaller size')
        cutters.append(label)
    for cutter in cutters:
        body -= cutter
    return body


def print_frame(values):
    """height_change stands on its lower end (from at +Y, to at -Y); the other
    parts print as modelled."""
    v = SPEC.resolve_values(values)
    if v['part'] != 'height_change':
        return Pos(0, 0, 0)
    return Rot(-90, 0, 0) if v['from_height'] <= v['to_height'] else Rot(90, 0, 0)


def grip_list(v):
    """(y, side, flared, width, dx, dz, height) for every grip, model frame."""
    part = v['part']
    width, length, height = dimensions(v)
    if part == 'width_change':
        return [(y, s, f, w, dx, 0., height) for y, s, f, w, dx in t.width_change_grips(
            length, v['transition_length_units']*c.GRID, c.channel_width(v['from_width_units']),
            c.channel_width(v['to_width_units']), height, v['suppress_connectors'], v['grip_flare'])]
    if part == 'height_change':
        return [(y, s, False, width, 0., 0., height) for y, s, *_ in t.height_change_grips(
            length, v['transition_length_units']*c.GRID, width, v['from_height'], v['to_height'],
            v['suppress_connectors'])]
    run = t.bridge_run_length(v['bridge_length_units'], v['half_bridge'])
    over = height
    off = over - v['from_height']
    fields = (v['suppress_connectors'].split(',') + ['', ''])[:2]
    out = []
    ends = ((run/2 + c.GRID/2, fields[0]),) if v['half_bridge'] else (
        (run/2 + c.GRID/2, fields[0]), (-run/2 - c.GRID/2, fields[1]))
    for y, field in ends:
        code = t.parse_codes('suppress_connectors', field, t.SUPPRESS_CODES, 1).ljust(1, 'N')
        flared = v['grip_flare'] > 0 and code != 'S'
        for side in t._sides(code):
            out.append((y, side, flared, width, 0., off if flared else 0.,
                        v['from_height'] if flared else over))
    return out


def audit_exclusions(values=None) -> dict:
    """Published-exception envelopes by family, model frame (exact solids).

    Inherited from the I channel (holders/underware_i_channel.py), the same
    author modules ([W]/[H]/[B] monokiniGrip, monokiniGripFlaredCut and the
    side cord cutout are hash- or geometry-identical to [C]'s):
    grip-end-wedge, flare-slit-fin, cutout-sill, label-recess.
    New for this part (rev 4 §8, mayor-authorised):
    height-change-step-patch: standing on end, the downward 1.30 x 1.40 mm end
      of every grip rail where it starts above the level wall top (selector:
      down-facing planar faces in the print frame, short extent <= 1.5 mm,
      area <= 10 mm2; each envelope is that face's 0.02 mm slab).
    """
    v = check(values)
    width, length, height = dimensions(v)
    out = {'grip-end-wedge': [], 'flare-slit-fin': [], 'cutout-sill': [], 'label-recess': [],
           'height-change-step-patch': []}
    for y, side, flared, w, dx, dz, h in grip_list(v):
        flare = v['grip_flare'] if flared else 0.
        out['grip-end-wedge'] += [Pos(dx, 0, dz)*r for r in end_ramp_regions(w, h, y, side, flare)]
        if flared:
            out['flare-slit-fin'] += [Pos(dx, 0, dz)*r for r in slit_floor_regions(w, h, y, side)]
    if v['part'] == 'height_change':
        out['height-change-step-patch'] = step_patch_regions(v)
    if _has_cutouts(v) and v['part'] == 'bridge':
        out['cutout-sill'] = cutout_sill_regions(width, **_cut_args(v))
    elif _has_cutouts(v):
        # Each opening sits on one straight end; that end's walls are offset.
        args = _cut_args(v)
        for y in t.cutout_centres(args['number'], args['spacing'], args['shift']):
            w = c.channel_width(v['to_width_units'] if y < 0 else v['from_width_units'])
            dx = (width - w)/2
            out['cutout-sill'] += [Pos(dx, 0, 0)*r for r in cutout_sill_regions(
                w, number=1, side=args['side'], cutout_width=args['cutout_width'], spacing=0., shift=-y)]
    if v['add_label']:
        run = length if v['part'] == 'width_change' else t.bridge_run_length(v['bridge_length_units'], False)
        bb = _label(v, width, run).bounding_box()
        d = v['text_depth']
        out['label-recess'].append(Pos(bb.center().X, bb.center().Y, d/2)
                                   * Box(bb.size.X + 0.02, bb.size.Y + 0.02, d + 0.002))
    return out


def step_patch_regions(v, grow=0.02):
    """Exact envelopes of the standing height change's downward grip-rail ends:
    the rail section u 0.7..2 from the wall top to the end ramp, at the grip end
    that faces the bed (model -Y when the lower end is at -Y)."""
    width, length, height = dimensions(v)
    down = 1 if v['from_height'] <= v['to_height'] else -1   # model Y toward the bed (print_frame)
    regions = []
    z0, z1 = height - c.BASE_HEIGHT, height - c.GRIP_RAMP
    for y, side, *_ in grip_list(v):
        y_end = y + down*c.GRIP_SIZE/2
        x0 = side*(width/2 - c.SNAP_WALL)
        x1 = side*(width/2 - c.SNAP_CAPTURE)
        regions.append(Pos((x0 + x1)/2, y_end, (z0 + z1)/2)
                       * Box(abs(x1 - x0) + 2*grow, 2*grow, z1 - z0 + 2*grow))
    return regions


SPEC = register(ModelSpec(
    name='underware_transition',
    title='Underware cable channel transition (openGrid)',
    description=('Underware 2.0 "monokini" transitions that snap into openGrid: a width change '
                 'between channel widths, a height change between channel heights (prints '
                 'standing on end), or a bridge that lifts a channel over a crossing one. By Pedro '
                 'Leite after Hands on Katie and BlackjackDuck, CC BY-NC-SA 4.0 (non-commercial, '
                 'share-alike). No supports.'),
    category_id='multiboard',
    build=build,
    print_frame=print_frame,
    params=(
        Param('part', 'enum', 'width_change', choices=PARTS, filename=True,
              group='Transition', label='Transition'),
        Param('from_width_units', 'integer', 1, min=1, max=4, step=1, filename=True,
              group='Channel Size', label='Width at the +Y end (28 mm units; height change and bridge: width)'),
        Param('to_width_units', 'integer', 2, min=1, max=4, step=1, filename=True,
              group='Channel Size', label='Width at the -Y end (width change)'),
        Param('from_height', 'number', 22, min=HEIGHT_MIN, max=HEIGHT_MAX, step=HEIGHT_STEP, filename=True,
              group='Channel Size', unit='mm',
              label='Height at the +Y end (width change: height; bridge: approach height)'),
        Param('to_height', 'number', 28, min=HEIGHT_MIN, max=HEIGHT_MAX, step=HEIGHT_STEP, filename=True,
              group='Channel Size', unit='mm',
              label='Height at the -Y end (bridge: channel height over the crossed channel)'),
        Param('channel_length_units', 'integer', 3, min=1, max=MAX_LENGTH_UNITS, step=1, filename=True,
              group='Channel Size', label='Length (28 mm units; width and height change)'),
        Param('transition_length_units', 'integer', 1, min=1, max=MAX_LENGTH_UNITS, step=1,
              group='Channel Size', label='Transition length (28 mm units)'),
        Param('bridge_height', 'number', 22, min=HEIGHT_MIN, max=HEIGHT_MAX, step=HEIGHT_STEP,
              group='Bridge', unit='mm', label='Height of the crossed channel'),
        Param('bridge_length_units', 'integer', 1, min=1, max=MAX_BRIDGE_UNITS, step=1,
              group='Bridge', label='Bridge run length (28 mm units)'),
        Param('half_bridge', 'boolean', False, group='Bridge', label='Half bridge (one ramp)'),
        Param('number_of_cord_cutouts', 'integer', 0, min=0, max=12, step=1,
              group='Cord Cutouts', label='Number of cord cutouts'),
        Param('cord_side_cutouts', 'enum', 'Both Sides', choices=t.SIDE_CUTOUTS,
              group='Cord Cutouts', label='Cutout side'),
        Param('cord_cutout_width', 'number', 12, min=6, max=20, step=1,
              group='Cord Cutouts', unit='mm', label='Cutout width'),
        Param('distance_between_cutouts', 'number', 28, min=14, max=56, step=1,
              group='Cord Cutouts', unit='mm', label='Distance between cutouts'),
        Param('shift_cutouts', 'number', 0, min=0, max=28, step=1,
              group='Cord Cutouts', unit='mm', label='Shift cutouts along the channel'),
        Param('add_label', 'boolean', False, group='Text Label', label='Add debossed label'),
        Param('text', 'string', 'CABLES', group='Text Label', label='Label text',
              max_length=MAX_TEXT_LENGTH, charset=TEXT_CHARSET),
        Param('text_size', 'number', 10, min=6, max=16, step=1,
              group='Text Label', unit='mm', label='Font size'),
        Param('text_depth', 'number', 0.2, min=0, max=1, step=0.2,
              group='Text Label', unit='mm', label='Deboss depth'),
        Param('grip_flare', 'number', 0, min=0, max=15, step=0.1,
              group='Advanced', unit='deg', label='Grip flare'),
        Param('suppress_connectors', 'string', '', group='Advanced',
              label='Suppress grips per cell (N/L/R/B/S; bridge: +Y,-Y)', max_length=24,
              charset='printable-ascii'),
    ),
    presets=(
        Preset('widen-1-to-2', '1 → 2 cells wide, 22 mm, 3 cells long', {}),
        Preset('raise-22-to-34', '22 → 34 mm high, 1 cell wide, 3 cells long',
               {'part': 'height_change', 'from_height': 22, 'to_height': 34}),
        Preset('bridge', 'Over a 22 mm channel, 22 → 50 mm',
               {'part': 'bridge'}),
    ),
))
