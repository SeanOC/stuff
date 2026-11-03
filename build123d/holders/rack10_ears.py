"""A strapped clamp mount for devices without mounting screw holes. Add two retaining straps. Gravity acts along -Y; print front down in PETG/PCTG."""
from holders.registry import ModelSpec, Param, Preset, register
from rack10.ears import ears


def build(values=None):
    return ears(**SPEC.resolve_values(values))


# [C] USW-Lite-16-PoE Dimensions: https://techspecs.ui.com/unifi/switching/usw-lite-16-poe (192 x 185 x 44 mm). Generic 210 mm example is original.
SPEC = register(ModelSpec(
    name='rack10_ears', title='10-inch rack clamp ears', category_id='storage', build=build,
    description='A strapped clamp mount for devices without mounting screw holes. Add two retaining straps.', print_orientation=(0,0,1),
    params=(
        Param('device_w','number',192,min=140,max=210,step=1,label='Device W'),
        Param('device_d','number',185,min=100,max=200,step=1,label='Device D'),
        Param('device_h','number',44,min=20,max=60,step=1,label='Device H'),
        Param('units','integer',2,min=1,max=2,step=1,label='Units'),
        Param('clearance','number',1,min=1,max=2,step=1,label='Clearance'),
        Param('slot_mm','number',0,min=0,max=8,step=1,label='Slot length (0 round; 7–8 slot)'),
    ),
    presets=(
        Preset('usw-lite-16','Usw Lite 16',{}),
        Preset('wide-box-210','Wide Box 210',{'device_w': 210, 'device_d': 170, 'device_h': 31, 'units': 1}),
    ),
))
