"""Original open-rear rack tray. Front face down, rear extending along +Z.

Worst load: device weight (-Y), bending the floor from the front plate;
full-height tapered side webs and 1 mm root fillets carry it into the ears.
PLA/PCTG, support-free. Presets describe fit, not tested equipment load ratings.
"""
from holders.registry import ModelSpec, Param, Preset, register
from rack10.tray import tray


def build(values=None):
    v = SPEC.resolve_values(values)
    return tray(v['device_w'],v['device_d'],v['device_h'],clearance=v['clearance'],slot_mm=v['slot_mm'])


SPEC = register(ModelSpec(
    name='rack10_tray', title='10-inch rack device tray', category_id='storage', build=build,
    description='A fitted open-rear shelf with tapered side webs and zip-tie slots. Rack height follows device height. Print front face down, without supports.',
    params=(Param('device_w','number',98,min=40,max=213.45,step=.1,unit='mm',label='Device width'),
            Param('device_d','number',98,min=40,max=200,step=1,unit='mm',label='Device depth'),
            Param('device_h','number',31,min=10,max=72,step=1,unit='mm',label='Device height'),
            Param('clearance','number',1,min=.5,max=2,step=.1,unit='mm',label='Clearance per side'),
            Param('slot_mm','number',0,min=0,max=8,step=1,unit='mm',label='Slot length (0 round; 7–8 slot)')),
    presets=(Preset('apple-tv-4k','Apple TV 4K fit',{}),
             Preset('switch-8-port','Generic eight-port switch fit',{'device_w':160,'device_d':100,'device_h':28}),
             Preset('mini-pc-nuc','Mini PC / NUC fit',{'device_w':117,'device_d':112,'device_h':51})),
))
