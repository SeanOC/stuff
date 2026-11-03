"""Clamp ears joined by a floor strap, front down, PETG/PCTG.

Gravity (-Y) runs through the floor into the front ears; zip ties
close the clamp and retain devices that lack threaded mounting holes.
"""
from . import constants as c
from .device import finish_device
from .device_ribs import blend, check_height, tie_cutter, tie_edge
from .device import bezel, box, rear_notch
from .tray import TrayFitError, tray_dimensions

FLOOR_TOP = 9.0
RAIL_TOP = 21.0


def ears(device_w=192,device_d=185,device_h=44,units=2,clearance=1,*,slot_mm=0):
    if clearance<1:
        raise TrayFitError('clamp clearance must be at least 1 mm to clear the root fillets')
    d=tray_dimensions(device_w,device_d,device_h,units,clearance)
    inner,outer,depth=d['inner_width'],d['outer_width'],d['depth']
    check_height(device_h,units,FLOOR_TOP)
    part=bezel(units,inner,FLOOR_TOP,slot_mm)
    part+=box(outer,FLOOR_TOP,depth)
    for side in (-1,1):
        part+=box(c.RAIL_WALL,RAIL_TOP,depth,x=side*(inner+c.RAIL_WALL)/2)
    part=blend(part,(-inner/2,inner/2),FLOOR_TOP)
    for x in (-device_w/4,device_w/4):
        for z in (3+device_d/3,3+2*device_d/3):
            part-=tie_cutter(x,z,FLOOR_TOP)
    part=rear_notch(part,depth,FLOOR_TOP)
    return finish_device(part,lambda e:tie_edge(e,device_w,device_d,FLOOR_TOP))
