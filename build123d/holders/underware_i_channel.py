# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Underware for openGrid straight (I) cable channel, adapted under CC BY-NC-SA 4.0.

[C] monokini_I_channel.scad:38-99 (parameters), :130-204 (top level),
:205-531 (modules) — Hands on Katie and BlackjackDuck; source and reference
pins in assets/underware-opengrid/NOTICE. Geometry: build123d/underware/.

Model frame = print frame: X across, Y along (centred), Z up; the closed,
chamfered face lies on the bed and the openGrid grips point up (+Z). Worst
load: cables pulling the channel off the board, i.e. along +Z on the grip
nubs; the grip rails and walls carry it along the layers (each grip is one
continuous extrusion on its wall). PLA or PCTG, no supports.

Not ported: Decorative / Support_Bridging_Separation (:88-92: the author's
render is non-manifold and its 0.4 mm feet are below the 0.9 mm wall floor),
Text_Emboss / Text_x_coordinate / Font / colours (single-material deboss with
the repo's Inter Bold label font). See the NOTICE deviations list.
"""
from labels.constants import MAX_TEXT_LENGTH, TEXT_CHARSET
from holders.registry import ModelSpec, Param, Preset, register
from underware import constants as c
from build123d import Box, Pos
from underware.channel import (CUTOUT_SIDES, cell_centres, check_cutouts, cord_cutouts, cutout_sill_regions,
                               filament_grooves, label_cutter, present_grips, straight_channel)
from underware.grip import end_ramp_regions, slit_floor_regions


def dimensions(v):
    return (c.channel_width(v['channel_width_units']), v['channel_length_units']*c.GRID,
            v['channel_total_height'])


def build(values=None):
    v = SPEC.resolve_values(values)
    width, length, height = dimensions(v)
    cut_args = dict(number=v['number_of_cord_cutouts'], side=v['cord_side_cutouts'],
                    cutout_width=v['cord_cutout_width'], spacing=v['distance_between_cutouts'],
                    shift=v['shift_cutouts'])
    check_cutouts(width, height, cell_centres(length), v['suppress_connectors'],
                  grip_flare=v['grip_flare'], **cut_args)
    cutters = cord_cutouts(width, height, **cut_args)
    if v['add_label']:
        if v['text_depth'] <= 0:
            raise ValueError('text_depth 0 makes no label in a single-material part; use 0.2 or more')
        cutters.append(label_cutter(v['text'], v['text_size'], v['text_depth'], width, length))
    if v['filament_show']:
        cutters += filament_grooves(width, length, diameter=v['filament_diameter'],
                                    depth=v['filament_depth'], offset=v['filament_offset'],
                                    repeat=v['filament_repeat'], spacing=v['filament_spacing'])
    part = straight_channel(length, width, height, suppress=v['suppress_connectors'],
                            separators=v['channel_separators'], grip_flare=v['grip_flare'])
    for cutter in cutters:
        part -= cutter
    return part


def audit_exclusions(values=None) -> dict:
    """Published-exception envelopes by family (exact solids, no bbox growth).

    grip-end-wedge: every grip's two 45 degree end-ramp faces; the ramp meets
      the nub undercut in the author's lead-in wedge ([C] :233-252).
    flare-slit-fin: with grip_flare > 0, each relief slit's floor and inner
      face below the inset chamfer corner ([C] :436-437 start the slit at
      topChamfer, on the exterior chamfer's tip).
    cutout-sill: each side cord cutout's round floor across the wall; it
      bottoms out at z=topChamfer where the exterior chamfer starts ([C]
      :170/:178), so the sill thins to an edge at the outer face.
    label-recess: with a label, the 0..text_depth slab over the ink: glyph
      recess ceilings are flat bridges no wider than a stroke and the islands
      between strokes are first-layer material, not walls (the tombstone
      sign's pocket-roof and raised-text precedent). Tests measure every
      bridge before excluding it.
    """
    v = SPEC.resolve_values(values)
    width, length, height = dimensions(v)
    out = {'grip-end-wedge': [], 'flare-slit-fin': [], 'label-recess': [],
           'cutout-sill': cutout_sill_regions(
               width, number=v['number_of_cord_cutouts'], side=v['cord_side_cutouts'],
               cutout_width=v['cord_cutout_width'], spacing=v['distance_between_cutouts'],
               shift=v['shift_cutouts'])}
    for y, side, flared in present_grips(length, v['suppress_connectors'], v['grip_flare']):
        out['grip-end-wedge'] += end_ramp_regions(width, height, y, side, v['grip_flare'] if flared else 0.)
        if flared:
            out['flare-slit-fin'] += slit_floor_regions(width, height, y, side)
    if v['add_label']:
        bb = label_cutter(v['text'], v['text_size'], v['text_depth'], width, length).bounding_box()
        d = v['text_depth']
        out['label-recess'].append(Pos(bb.center().X, bb.center().Y, d/2)
                                   * Box(bb.size.X + 0.02, bb.size.Y + 0.02, d + 0.002))
    return out


SPEC = register(ModelSpec(
    name='underware_i_channel',
    title='Underware straight cable channel (openGrid)',
    description=('Straight Underware 2.0 "monokini" cable channel that snaps into openGrid: '
                 'set width and length in 28 mm cells and the height, with optional cord '
                 'exits, a debossed label and per-cell grip suppression. By Hands on Katie '
                 'and BlackjackDuck, CC BY-NC-SA 4.0 (non-commercial, share-alike). Prints '
                 'as shown, closed face down, no supports.'),
    category_id='multiboard',
    build=build,
    params=(
        Param('channel_width_units', 'integer', 1, min=1, max=4, step=1, filename=True,
              group='Channel Size', label='Width (28 mm units)'),
        Param('channel_total_height', 'number', 22, min=10, max=72, step=6, filename=True,
              group='Channel Size', unit='mm', label='Height including grips'),
        Param('channel_length_units', 'integer', 5, min=1, max=12, step=1, filename=True,
              group='Channel Size', label='Length (28 mm units)'),
        Param('number_of_cord_cutouts', 'integer', 0, min=0, max=12, step=1,
              group='Cord Cutouts', label='Number of cord cutouts'),
        Param('cord_side_cutouts', 'enum', 'Both Sides', choices=CUTOUT_SIDES,
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
              label='Suppress grips per cell (N/L/R/B/S)', max_length=24, charset='printable-ascii'),
        Param('channel_separators', 'string', '', group='Advanced',
              label='Separator walls (N/S per midline)', max_length=24, charset='printable-ascii'),
        Param('filament_show', 'boolean', False, group='Filament Attachment',
              label='Filament groove'),
        Param('filament_diameter', 'number', 1.75, min=0, max=10, step=0.01,
              group='Filament Attachment', unit='mm', label='Filament diameter'),
        Param('filament_depth', 'number', 0, min=-50, max=50, step=0.01,
              group='Filament Attachment', unit='mm', label='Groove depth (down is +)'),
        Param('filament_offset', 'number', 0, min=-50, max=50, step=0.01,
              group='Filament Attachment', unit='mm', label='Groove offset across'),
        Param('filament_repeat', 'integer', 1, min=1, step=1,
              group='Filament Attachment', label='Groove count'),
        Param('filament_spacing', 'number', 5, min=0, max=50, step=0.01,
              group='Filament Attachment', unit='mm', label='Groove spacing'),
    ),
    presets=(
        Preset('default', '1 × 5 cells, 22 mm', {}),
        Preset('wide-tall', '2 × 3 cells, 34 mm', {'channel_width_units': 2, 'channel_length_units': 3,
                                                    'channel_total_height': 34}),
        Preset('cutouts', '1 × 5 with two cord exits', {'number_of_cord_cutouts': 2}),
        Preset('label', '1 × 5 with a debossed label', {'add_label': True}),
    ),
))
