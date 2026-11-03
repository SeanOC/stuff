"""Original rack keystone panel. Face down; cable pull acts through the face.

PLA/PCTG, support-free. Latch/window edges retain the nominal mating profile.
"""
from build123d import Pos
from holders.registry import ModelSpec, Param, Preset, register
from scripts.thumbnail import PlaneSpec
from rack10 import constants as c
from rack10.keystone import keystone_row, mating_edge
from rack10.panel import finish, panel, panel_height


def build(values=None):
    v = SPEC.resolve_values(values)
    h = panel_height(1)
    part = panel(1, slot_mm=v['slot_mm'], finished=False)
    for cutter in keystone_row(v['count']):
        part -= Pos(0,h/2,0)*cutter
    return finish(part, lambda e: mating_edge(e,v['count'],h/2))


SPEC = register(ModelSpec(
    name='rack10_keystone_panel', title='10-inch rack keystone panel', category_id='rack10', build=build,
    description='A 1U panel with nominal keystone windows and recessed rear latch seats. Print face down; verify jack fit with a test print.',
    params=(Param('count','integer',6,min=1,max=c.MAX_KEYSTONES,step=1,label='Keystone ports'),
            Param('slot_mm','number',0,min=0,max=8,step=1,unit='mm',label='Slot length (0 round; 7–8 slot)')),
    presets=(Preset('1u-6-keystones','1U six keystones',{}), Preset('1u-max','1U maximum ports',{'count':c.MAX_KEYSTONES})),
    review_sections=(PlaneSpec((-c.KEYSTONE_PITCH/2, panel_height(1)/2, 0), (1,0,0),
                               'default six-port panel: left centre latch seat'),),
))
