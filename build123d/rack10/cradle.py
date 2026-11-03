"""Vented low-rail cradle, PETG/PCTG, printed front down.

Gravity acts along -Y; the floor and continuous low side rails transfer the
cantilever moment into the bezel. The full device front and rear stay open.
"""
from . import constants as c
from .device import finish_device, blend_floor
from .device import bezel, box, pads, rear_notch, vent_floor
from .tray import tray_dimensions


def cradle(device_w=156,device_d=162.4,device_h=152,units=4,clearance=2,*,slot_mm=0):
    d=tray_dimensions(device_w,device_d,device_h,units,clearance)
    inner,outer,depth=d['inner_width'],d['outer_width'],d['depth']
    part=bezel(units,inner,c.FLOOR,slot_mm)
    part+=box(outer,c.FLOOR,depth)
    for side in (-1,1):
        part+=box(c.RAIL_WALL,c.FLOOR+c.RAIL_HEIGHT,depth,x=side*(inner+c.RAIL_WALL)/2)
    part=blend_floor(part,(-inner/2,inner/2))
    front=c.PANEL_THICKNESS+clearance
    part=vent_floor(part,device_w,device_d,c.FLOOR,front+device_d/2,fraction=.5,reserve_pads=True)
    part=pads(part,device_w,device_d,c.FLOOR,front)
    part=rear_notch(part,depth,c.FLOOR)
    return finish_device(part)
