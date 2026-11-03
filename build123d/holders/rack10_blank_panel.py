"""Original rack blank; face down at Z=0. Worst load: handling across ears.

PLA/PCTG, support-free. The rack interface is fixed; units and slots control
coverage and mounting tolerance. No library mount profile is adapted.
"""
from build123d import Pos
from holders.registry import ModelSpec, Param, Preset, register
from rack10 import constants as c
from rack10.panel import finish, panel, panel_height
from rack10.vent import vent_pattern


def build(values=None):
    v = SPEC.resolve_values(values)
    h = panel_height(v['units'])
    part = panel(v['units'], slot_mm=v['slot_mm'], finished=False)
    if v['vented']:
        for cutter in vent_pattern((c.USABLE_WIDTH-10, h-20), .35):
            part -= Pos(0,h/2,0)*cutter
    return finish(part)


SPEC = register(ModelSpec(
    name='rack10_blank_panel', title='10-inch rack blank panel', category_id='rack10', build=build,
    description='A solid or vented rack panel with reinforced ears. Print front face down, without supports.',
    params=(Param('units','integer',1,min=1,max=2,step=1,label='Rack units'),
            Param('vented','boolean',False,label='Ventilation slots'),
            Param('slot_mm','number',0,min=0,max=8,step=1,unit='mm',label='Slot length (0 round; 7–8 slot)')),
    presets=(Preset('1u-solid','1U solid',{}), Preset('1u-vented','1U vented',{'vented':True}),
             Preset('2u-vented','2U vented',{'units':2,'vented':True})),
))
