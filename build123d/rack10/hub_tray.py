"""Open-front RF/IR hub pockets, front down in PETG/PCTG.

Gravity acts -Y through the floor and pocket dividers into the front ears.
The M3 sits at the front edge with an unobstructed IR/status face.
"""
from math import isfinite
from . import constants as c
from .device import finish_device, blend_floor
from .device import bezel, box, ramp, rear_notch
from .tray import TrayFitError, tray_dimensions


def hub_tray(left_w=70,left_d=70,right_w=105,right_d=105,*,slot_mm=0):
    if not all(isfinite(v) and 40<=v<=110 for v in (left_w,left_d,right_w,right_d)):
        raise TrayFitError('hub pockets require dimensions 40..110 mm')
    # [C] Aqara M3 specs: 105 x 105 x 36.5; Lutron L-BDG2: 70 x 70 x 30.
    inner=left_w+right_w+4+c.RAIL_WALL
    d=tray_dimensions(inner-2,max(left_d,right_d)+32,36.5,1,1)
    depth=d['depth']
    part=bezel(1,inner,c.FLOOR,slot_mm)+box(d['outer_width'],c.FLOOR,depth)
    left_x=-inner/2+(left_w+2)/2
    right_x=inner/2-(right_w+2)/2
    for x in (-inner/2-c.RAIL_WALL/2,left_x+(left_w+2+c.RAIL_WALL)/2,inner/2+c.RAIL_WALL/2):
        part+=box(c.RAIL_WALL,c.FLOOR+5,depth,x=x)
    part=blend_floor(part,(-inner/2,inner/2,left_x+(left_w+2)/2,right_x-(right_w+2)/2),rounded=False)
    for x,w,dep in ((left_x,left_w,left_d),(right_x,right_w,right_d)):
        rear=4+dep
        segment=(w-16)/2
        for side in (-1,1):
            part+=ramp(segment,5,12,x+side*(12+segment)/2,c.FLOOR,rear+1)
        from build123d import Face, Vector, Wire, extrude
        points=[(x-5,-1,rear),(x+5,-1,rear),(x+5,-1,rear+7),
                (x,-1,rear+12),(x-5,-1,rear+7)]
        part-=extrude(Face(Wire.make_polygon([Vector(*p) for p in points],close=True)),
                      amount=c.FLOOR+2,dir=(0,1,0))
    for i in range(int((inner-20)/10)):
        x=-inner/2+10+i*10
        if abs(x)>15 and abs(x-(left_x+(left_w+2+c.RAIL_WALL)/2))>7:
            part-=box(7,c.FLOOR+2,9,x=x,y=-1,z=depth-8)
    part=rear_notch(part,depth,c.FLOOR)
    return finish_device(part)
