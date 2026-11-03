"""Face-down rails for HomeRacker. Worst load: equipment pull-off at peg roots.

PLA/PCTG, support-free. Test the five-unit coupon in PETG before the full set;
roll every strip-carrying post so its pin-hole axis runs front-to-back.
"""
from holders.registry import ModelSpec, Param, Preset, register
from rack10 import constants as c
from scripts.thumbnail import PlaneSpec
from rack10.rail_strip import rail_length, rail_print_frame, rail_strip


def build(values=None):
    if values is not None and 'pin_units' in values:
        rail_length(values['pin_units'])  # Keep the actionable bed-limit error at the public entry point.
    return rail_strip(**SPEC.resolve_values(values))


SPEC = register(ModelSpec(
    name='rack10_rail_strip', title='10-inch rack rail strip', category_id='storage', build=build,
    description='EIA rail for HomeRacker posts. Print front face down; roll posts so pin holes run front-to-back. Test the coupon before loading equipment.',
    print_frame=rail_print_frame,
    review_sections=(PlaneSpec((c.RAIL_HOLE_X,0,0),(1,0,0),
                               'insert column: through bores and 45-degree seats'),),
    params=(
        Param('pin_units', 'integer', 18, min=5, max=27, step=1, label='Post length (15 mm pin units)',
              description='18 pin units hold 6 rack U; 15 hold 5 U. Maximum 27 units; segment longer posts at a connector sleeve.'),
        Param('thickness', 'number', 12, min=11, max=14, step=.5, unit='mm', label='Bar thickness',
              description='Insert mode needs 12–14 mm for its load-bearing seat; 11–11.5 mm is cage-nut-only.'),
        Param('mount', 'enum', 'pegs', choices=('pegs', 'pin_holes'), label='Post attachment'),
        Param('hole', 'enum', 'insert', choices=('insert', 'cage_nut'), label='Equipment fastener'),
    ),
    presets=(
        Preset('18u', '18 pin units / 6U — front-to-back post holes', {}),
        Preset('15u', '15 pin units / 5U — front-to-back post holes', {'pin_units':15}),
        Preset('coupon', '5 pin units — PETG fit coupon; front-to-back post holes', {'pin_units':5}),
    ),
))
