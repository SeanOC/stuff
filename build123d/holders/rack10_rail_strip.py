"""Face-down rails for HomeRacker. Worst load: equipment pull-off at peg roots.

PLA/PCTG, support-free. Test the five-unit coupon in PETG before the full set;
roll every strip-carrying post so its pin-hole axis runs front-to-back.
"""
from holders.registry import ModelSpec, Param, Preset, register
from rack10.rail_strip import rail_print_frame, rail_strip


def build(values=None):
    return rail_strip(**SPEC.resolve_values(values))


SPEC = register(ModelSpec(
    name='rack10_rail_strip', title='10-inch rack rail strip', category_id='storage', build=build,
    description='EIA rail for HomeRacker posts. Print front face down; roll posts so pin holes run front-to-back. Test the coupon before loading equipment.',
    print_frame=rail_print_frame,
    params=(
        Param('pin_units', 'integer', 18, min=5, max=30, step=1, label='Post length (15 mm pin units)',
              description='18 pin units hold 6 rack U; 15 hold 5 U. The longest strips exceed the supported beds.'),
        Param('thickness', 'number', 12, min=10, max=14, step=.5, unit='mm', label='Bar thickness',
              description='Insert mode requires at least 11.5 mm; 10–11 mm is cage-nut-only.'),
        Param('mount', 'enum', 'pegs', choices=('pegs', 'pin_holes'), label='Post attachment'),
        Param('hole', 'enum', 'insert', choices=('insert', 'cage_nut'), label='Equipment fastener'),
    ),
    presets=(
        Preset('18u', '18 pin units / 6U — front-to-back post holes', {}),
        Preset('15u', '15 pin units / 5U — front-to-back post holes', {'pin_units':15}),
        Preset('coupon', '5 pin units — PETG fit coupon; front-to-back post holes', {'pin_units':5}),
    ),
))
