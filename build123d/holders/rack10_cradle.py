"""Vented cradle with an open bezel, low rails, four pads and rear cable access. Gravity acts along -Y; print front down in PETG/PCTG."""
from holders.registry import ModelSpec, Param, Preset, register
from rack10.cradle import cradle


def build(values=None):
    return cradle(**SPEC.resolve_values(values))


# [C] Steam Machine W/D/H and feet: task equipment list; docs/rack10.md, Device mounts.
SPEC = register(ModelSpec(
    name='rack10_cradle', title='10-inch rack low-rail cradle', category_id='rack10', build=build,
    description='Vented cradle with an open bezel, low rails, four pads and rear cable access.', print_orientation=(0,0,1),
    params=(
        Param('device_w','number',156,min=140,max=200,step=1,unit='mm',label='Device W'),
        Param('device_d','number',162.4,min=140,max=200,step=1,unit='mm',label='Device D'),
        Param('device_h','number',152,min=80,max=152,step=1,unit='mm',label='Device H'),
        Param('units','integer',4,min=3,max=4,step=1,label='Units'),
        Param('clearance','number',2,min=1,max=2,step=1,unit='mm',label='Clearance'),
        Param('slot_mm','number',0,min=0,max=8,step=1,unit='mm',label='Slot length (0 round; 7–8 slot)'),
    ),
    presets=(
        Preset('steam-machine','Steam Machine',{}),
        Preset('generic-3u','Generic 3U',{'device_w': 160, 'device_d': 160, 'device_h': 100, 'units': 3}),
    ),
))
