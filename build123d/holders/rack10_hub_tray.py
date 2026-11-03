"""1U open-front pockets with rear cable slots and a cable comb. Gravity acts along -Y; print front down in PETG/PCTG."""
from holders.registry import ModelSpec, Param, Preset, register
from rack10.hub_tray import hub_tray


def build(values=None):
    return hub_tray(**SPEC.resolve_values(values))


# [C] Aqara Hub M3 specifications (Dimensions): https://www.aqara.com/us/product/hub-m3-specs/ ; Lutron 369816 dimensions; docs/rack10.md.
SPEC = register(ModelSpec(
    name='rack10_hub_tray', title='10-inch rack two-hub tray', category_id='rack10', build=build,
    description='1U open-front pockets with rear cable slots and a cable comb.', print_orientation=(0,0,1),
    params=(
        Param('left_w','number',70,min=40,max=105,step=1,unit='mm',label='Left W'),
        Param('left_d','number',70,min=40,max=110,step=1,unit='mm',label='Left D'),
        Param('right_w','number',105,min=40,max=110,step=1,unit='mm',label='Right W'),
        Param('right_d','number',105,min=40,max=110,step=1,unit='mm',label='Right D'),
        Param('slot_mm','number',0,min=0,max=8,step=1,unit='mm',label='Slot length (0 round; 7–8 slot)'),
    ),
    presets=(
        Preset('caseta-aqara-m3','Caseta Aqara M3',{}),
    ),
))
