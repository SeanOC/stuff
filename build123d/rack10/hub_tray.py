"""Open-front RF/IR hub pockets, front down in PETG/PCTG.

Gravity acts -Y through the floor and pocket dividers into the front ears.
The M3 sits at the front edge with an unobstructed IR/status face.
"""
from math import isfinite
from . import constants as c
from .device import finish_device
from .device_ribs import blend
from .device import bezel, box, ramp
from .tray import TrayFitError, tray_dimensions
from .panel import panel_height

FLOOR_TOP = 3.8
RAIL_TOP = 20.0
TOP_BEAM = 2.2  # Retain the original 1.15 mm M3 head clearance after raising the deck.


def hub_tray(left_w=70,left_d=70,right_w=105,right_d=105,*,slot_mm=0):
    if not all(isfinite(v) and 40<=v<=110 for v in (left_w,left_d,right_w,right_d)):
        raise TrayFitError('hub pockets require dimensions 40..110 mm')
    # [C] Aqara M3 specs: 105 x 105 x 36.5; Lutron L-BDG2: 70 x 70 x 30.
    inner=left_w+right_w+4+c.RAIL_WALL
    d=tray_dimensions(inner-2,max(left_d,right_d)+32,36.5,1,1)
    depth=d['depth']
    part=bezel(1,inner,FLOOR_TOP,slot_mm)+box(d['outer_width'],FLOOR_TOP,depth)
    # The top beam is not credited for stiffness. Raising its underside by
    # the same 0.8 mm as the floor preserves the original device opening.
    part-=box(inner,3-TOP_BEAM,6,y=panel_height(1)-3,z=-1)
    left_x=-inner/2+(left_w+2)/2
    right_x=inner/2-(right_w+2)/2
    divider=left_x+(left_w+2+c.RAIL_WALL)/2
    for x in (-inner/2-c.RAIL_WALL/2,divider,inner/2+c.RAIL_WALL/2):
        part+=box(c.RAIL_WALL,RAIL_TOP,depth,x=x)
    part=blend(part,(-inner/2,inner/2,left_x+(left_w+2)/2,right_x-(right_w+2)/2),FLOOR_TOP,rounded=False)
    for x,w,dep in ((left_x,left_w,left_d),(right_x,right_w,right_d)):
        rear=4+dep
        segment=(w-16)/2
        for side in (-1,1):
            part+=ramp(segment,5,12,x+side*(12+segment)/2,FLOOR_TOP,rear+1)
        from build123d import Face, Vector, Wire, extrude
        points=[(x-5,-1,rear),(x+5,-1,rear),(x+5,-1,rear+7),
                (x,-1,rear+12),(x-5,-1,rear+7)]
        part-=extrude(Face(Wire.make_polygon([Vector(*p) for p in points],close=True)),
                      amount=FLOOR_TOP+2,dir=(0,1,0))
    for i in range(int((inner-20)/10)):
        x=-inner/2+10+i*10
        if abs(x)>15 and abs(x-(left_x+(left_w+2+c.RAIL_WALL)/2))>7:
            part-=box(7,FLOOR_TOP+2,9,x=x,y=-1,z=depth-8)
    # A centred notch near the divider's 1 mm root blend can leave a sliver
    # too small for the final 0.3 mm relief (e.g. W=100/105 leaves 0.3 mm).
    # In the unloaded tail only, widen the notch to clear the whole blended
    # rail and leave >=1.6 mm plus both edge treatments on either boundary.
    root_reach=c.RAIL_WALL/2+1
    margin=1.6+2*c.EDGE_CHAMFER
    notch_half=5.0
    if abs(divider)<notch_half+root_reach+margin:
        notch_half=max(notch_half,abs(divider)+root_reach+margin)
    part-=box(2*notch_half,FLOOR_TOP+20,11,y=-1,z=depth-10)
    return finish_device(part)
