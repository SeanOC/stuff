"""2U open shelf with a vented 3 mm deck, two-way ribs and four pads. Gravity acts along -Y; print front down in PETG/PCTG."""
from holders.registry import ModelSpec, Param, Preset, register
from rack10.shelf import shelf


def build(values=None):
    return shelf(**SPEC.resolve_values(values))


# [C] Sonos Amp 217 x 217 x 64 mm: task equipment list; docs/rack10.md, Device mounts.
SPEC = register(ModelSpec(
    name='rack10_shelf', title='10-inch rack open shelf', category_id='storage', build=build,
    description='2U open shelf with a vented 3 mm deck, two-way ribs and four pads.', print_orientation=(0,0,1),
    params=(
        Param('device_w','number',217,min=100,max=217,step=1,label='Device W'),
        Param('device_d','number',217,min=100,max=220,step=1,label='Device D'),
        Param('device_h','number',64,min=20,max=64,step=1,label='Device H'),
        Param('side_stops','boolean',True,label='5 mm side stops'),
        Param('slot_mm','number',0,min=0,max=8,step=1,label='Slot length (0 round; 7–8 slot)'),
    ),
    presets=(
        Preset('sonos-amp','Sonos Amp',{}),
        Preset('2u-plain','2U Plain',{'device_w': 180, 'device_d': 180, 'device_h': 50, 'side_stops': False}),
    ),
))
