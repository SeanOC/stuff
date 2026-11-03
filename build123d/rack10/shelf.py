"""Open 2U rib-grid shelf, printed front down in PETG/PCTG.

Gravity is -Y. Continuous orthogonal ribs carry the front-rail cantilever
and transverse bending; the upper 3 mm forms the perforated deck. No top
bezel bridges across the open device face in this print orientation.
"""
from math import isfinite, sqrt
from . import constants as c
from .device import box, pad_positions, pads, ramp, rear_notch, finish_device, vent_floor
from .panel import panel, panel_height
from .tray import TrayFitError

RIB_HEIGHT=14.0
DECK_TOP=RIB_HEIGHT+c.FLOOR
STOP_WALL=1.6


def shelf_dimensions(device_w,device_d,device_h,side_stops=True):
    if not all(isfinite(v) and v>0 for v in (device_w,device_d,device_h)):
        raise TrayFitError('shelf dimensions must be finite and positive')
    if not 100<=device_w<=217 or not 100<=device_d<=220:
        raise TrayFitError('shelf device width must be 100..217 and depth 100..220 mm')
    if DECK_TOP+1+device_h+1>panel_height(2):
        raise TrayFitError('shelf height exceeds the 2U envelope')
    width=max(c.TRAY_OUTER_WIDTH_LIMIT,device_w+2+2*STOP_WALL if side_stops else 0)
    if width>c.CLEAR_OPENING:
        raise TrayFitError('shelf stops exceed the clear rail opening')
    return dict(width=width,depth=c.PANEL_THICKNESS+device_d+16)


def longitudinal_sections(device_w, deck_width):
    """Disjoint (X centre, width) rectangles guaranteed solid along the deck.

    Count EVERY internal 3 mm web, plus the two solid bands outside the vent
    field. Deduct edge relief at both boundaries of the outside bands. The
    production endpoint tests intersect each rectangle with the actual BREP.
    """
    vent_width=device_w-24
    columns=int(vent_width//10)
    pitch=vent_width/columns
    aperture=pitch*sqrt(.35)
    sections=[((i-columns/2)*pitch,3.0) for i in range(1,columns)]
    inner=(columns-1)*pitch/2+aperture/2+c.EDGE_CHAMFER
    outer=deck_width/2-c.EDGE_CHAMFER
    band=outer-inner
    sections.extend((side*(outer+inner)/2,band) for side in (-1,1))
    return sections


def beam_deflections(*, device_w, device_d, deck_width, deck_depth):
    """3 kg at the device centre, transferred through the two pad rows.

    Conservatively place reactions at the OUTER edges of the 8 mm pad tops:
    pad_positions returns each pad's start Z, not its centre. Evaluate the
    sum of BOTH point-load deflections at the rear row and at the actual
    free deck tip. Cross ribs are excluded from the longitudinal section.
    PETG E=2000 N/mm². All dimensions are explicit keyword-only arguments.
    """
    height=DECK_TOP-2*c.EDGE_CHAMFER
    transverse_i=2*20*height**3/12
    longitudinal_i=sum(w for x,w in longitudinal_sections(device_w,deck_width))*height**3/12
    positions=pad_positions(device_w,device_d,5)
    front=min(z for x,z in positions)
    rear=max(z+8 for x,z in positions)
    if not isfinite(deck_depth) or deck_depth<rear:
        raise ValueError('deck_depth must include the rear pad contact edge')
    force=3*9.81
    centre=5+device_d/2
    rear_force=force*(centre-front)/(rear-front)
    front_force=force-rear_force

    def deflection_at(x):
        return sum(p*a*a*(3*x-a)/(6*2000*longitudinal_i)
                   for p,a in ((front_force,front),(rear_force,rear)))

    return dict(transverse=force*c.EAR_WIDTH**3/(48*2000*transverse_i),
                rear_pad=deflection_at(rear),cantilever=deflection_at(deck_depth))


def shelf(device_w=217,device_d=217,device_h=64,side_stops=True,*,slot_mm=0):
    d=shelf_dimensions(device_w,device_d,device_h,side_stops)
    width,depth=d['width'],d['depth']
    part=panel(2,width_between_ears=c.USABLE_WIDTH,slot_mm=slot_mm,finished=False)
    part-=box(device_w+2,panel_height(2),6,y=DECK_TOP,z=-1)
    part+=box(width,DECK_TOP,depth)
    # Vent/grid cells stop well clear of the pad seats and cable notch.
    part=vent_floor(part,device_w-24,device_d-24,DECK_TOP,5+device_d/2,.35)
    part=pads(part,device_w,device_d,DECK_TOP,5)
    # 5 mm rear lip and optional side stops, grown straight off the deck.
    lip_segment=(device_w-16)/2
    for side in (-1,1):
        part+=ramp(lip_segment,5,12,side*(14+lip_segment)/2,DECK_TOP,depth-13)
    if side_stops:
        for side in (-1,1):
            part+=box(STOP_WALL,5,depth,x=side*(device_w+2+STOP_WALL)/2,y=DECK_TOP)
    part=rear_notch(part,depth,DECK_TOP)
    return finish_device(part)
