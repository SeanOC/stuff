"""Vented low-rail cradle, PETG/PCTG, printed front down.

Gravity acts along -Y; the floor and continuous low side rails transfer the
cantilever moment into the bezel. The full device front and rear stay open.
"""
from . import constants as c
from .device import finish_device
from .device_ribs import blend, check_height
from .device import bezel, box, pads, rear_notch, vent_floor
from .tray import tray_dimensions

FLOOR_TOP = 16.0  # Perforated rib grid; <=1 mm elastic sag at the design load.
RAIL_TOP = 32.0


def cradle(device_w=156,device_d=162.4,device_h=152,units=4,clearance=2,*,slot_mm=0):
    d=tray_dimensions(device_w,device_d,device_h,units,clearance)
    inner,outer,depth=d['inner_width'],d['outer_width'],d['depth']
    check_height(device_h,units,FLOOR_TOP,pad=1)
    part=bezel(units,inner,FLOOR_TOP,slot_mm)
    part+=box(outer,FLOOR_TOP,depth)
    for side in (-1,1):
        part+=box(c.RAIL_WALL,RAIL_TOP,depth,x=side*(inner+c.RAIL_WALL)/2)
    part=blend(part,(-inner/2,inner/2),FLOOR_TOP)
    front=c.PANEL_THICKNESS+clearance
    part=vent_floor(part,device_w,device_d,FLOOR_TOP,front+device_d/2,fraction=.5,reserve_pads=True)
    part=pads(part,device_w,device_d,FLOOR_TOP,front)
    part=rear_notch(part,depth,FLOOR_TOP)
    return finish_device(part)
