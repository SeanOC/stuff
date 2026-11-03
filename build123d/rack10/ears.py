"""Clamp ears joined by a floor strap, front down, PETG/PCTG.

Gravity (-Y) runs through the floor into the front ears; reusable straps
close the clamp and retain devices that lack threaded mounting holes.
"""
from . import constants as c
from .device import finish_device, blend_floor
from .device import bezel, box, rear_notch
from .tray import TrayFitError, tray_dimensions, _tie_cutter, tie_mating_edge


def ears(device_w=192,device_d=185,device_h=44,units=2,clearance=1,*,slot_mm=0):
    if clearance<1:
        raise TrayFitError('clamp clearance must be at least 1 mm to clear the root fillets')
    d=tray_dimensions(device_w,device_d,device_h,units,clearance)
    inner,outer,depth=d['inner_width'],d['outer_width'],d['depth']
    part=bezel(units,inner,c.FLOOR,slot_mm)
    part+=box(outer,c.FLOOR,depth)
    for side in (-1,1):
        part+=box(c.RAIL_WALL,c.FLOOR+8,depth,x=side*(inner+c.RAIL_WALL)/2)
    part=blend_floor(part,(-inner/2,inner/2))
    for x in (-device_w/4,device_w/4):
        for z in (3+device_d/3,3+2*device_d/3):
            part-=_tie_cutter(x,z)
    part=rear_notch(part,depth,c.FLOOR)
    return finish_device(part,lambda e:tie_mating_edge(e,device_w,device_d))
