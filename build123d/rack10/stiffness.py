"""Elastic device-mount estimates; N, mm, MPa. Not creep/load ratings.

As in shelf.py, the bezel is an ideal clamp. Centred equipment transfers
weight through two contact rows; no credit for device stiffness, root
fillets, pads, or material omitted from the explicitly probed rectangles.
"""
from dataclasses import dataclass
from math import isfinite, sqrt
from . import constants as c
from .device import pad_positions

# [C] Original equipment list, Sean 2026-11-02 23:25Z; pst-3fob4 rev 2.
STEAM_MACHINE_KG = 2.6
# [C] https://techspecs.ui.com/unifi/switching/usw-lite-16-poe — Mechanical/Weight.
USW_LITE_16_KG = 1.2
# [C] Mayor substitute design loads, pst-3fob4 rev 2; NOT measured masses.
LUTRON_DESIGN_KG = 0.5
AQARA_DESIGN_KG = 0.5
# [C] Existing shelf.py elastic assumption (PETG).
PETG_MPA = 2000.0
# [C] Extrudr PCTG TDS, 2025-06-26, section 3, ISO 178 flexural modulus:
# https://s3.extrudr.com/extrudr-media/datasheets/tds/tds-en/pctg-TDS-en.pdf
PCTG_MPA = 1650.0


@dataclass(frozen=True)
class Beam:
    """A solid probe: X centre, Y/Z starts, and three positive dimensions."""
    x: float
    y: float
    z: float
    width: float
    height: float
    length: float


def inertia(beams):
    """Composite longitudinal I about the common area-weighted neutral axis."""
    area = sum(b.width*b.height for b in beams)
    neutral = sum(b.width*b.height*(b.y+b.height/2) for b in beams)/area
    return sum(b.width*b.height**3/12 + b.width*b.height*(b.y+b.height/2-neutral)**2
               for b in beams)


def reactions(mass, front, rear, centre):
    if not all(isfinite(v) for v in (mass, front, rear, centre)) or not (mass>0 and 0<=front<rear and front<=centre<=rear):
        raise ValueError('positive mass and ordered contacts bracketing the centre required')
    rear_force = mass*9.81*(centre-front)/(rear-front)
    return ((mass*9.81-rear_force, front), (rear_force, rear))


def deflections(beams, loads, tip, modulus):
    if not isfinite(modulus) or modulus<=0 or tip<max(a for p,a in loads):
        raise ValueError('positive modulus and tip beyond contacts required')
    moment = inertia(beams)
    def at(x):
        return sum(p*min(x,a)**2*(3*max(x,a)-min(x,a))/(6*modulus*moment)
                   for p,a in loads)
    return {'rear_contact': at(max(a for p,a in loads)), 'tip': at(tip)}


def floor_sections(inner, depth, top, openings):
    """Subtract all X cut envelopes, including relief, from the floor section."""
    intervals = [(-inner/2+c.EDGE_CHAMFER, inner/2-c.EDGE_CHAMFER)]
    for left,right in openings:
        result=[]
        for a,b in intervals:
            if b<=left or a>=right: result.append((a,b))
            else:
                if a<left: result.append((a,left))
                if b>right: result.append((right,b))
        intervals=result
    # A notch may leave a narrow tail remnant of a wider web. Do not credit
    # that remnant as a load-bearing rib, even if the 0.9 mm print audit passes.
    return [Beam((a+b)/2,.3,.3,b-a,top-.6,depth-.6) for a,b in intervals if b-a>=1.6]


def rails(inner, depth, top):
    return [Beam(side*(inner+c.RAIL_WALL)/2,.3,.3,c.RAIL_WALL-.6,top-.6,depth-.6)
            for side in (-1,1)]


def cradle_case(w, d, clearance, floor_top, rail_top):
    inner=w+2*clearance
    front=3+clearance
    depth=3+d+2*clearance
    nx=int(w//10); pitch=w/nx; aperture=pitch*sqrt(.5)
    openings=[((i-(nx-1)/2)*pitch-aperture/2-.3,
               (i-(nx-1)/2)*pitch+aperture/2+.3) for i in range(nx)]
    openings.append((-5.3,5.3))  # rear notch; omit this material along ALL Z
    sections=floor_sections(inner,depth,floor_top,openings)+rails(inner,depth,rail_top)
    positions=pad_positions(w,d,front)
    contacts=(min(z for x,z in positions),max(z+8 for x,z in positions))
    loads=reactions(STEAM_MACHINE_KG,*contacts,front+d/2)
    rows=max(2,int(d//40)); zpitch=d/rows
    cut_height=zpitch*sqrt(.5)+aperture/4
    first=front+zpitch/2-cut_height/2
    last=front+d-zpitch/2+cut_height/2
    bands=((.3,first-.3),(last+.3,depth-.3))
    cross=[Beam(side*(inner/2+5.3)/2,.3,z,inner/2-5.3,floor_top-.6,end-z)
           for z,end in bands for side in (-1,1)]
    return sections, cross, loads, depth, inner/2


def clamp_case(w, d, clearance, floor_top, rail_top):
    inner=w+2*clearance; depth=3+d+2*clearance; front=3+clearance
    openings=[(-5.3,5.3)]+[(x-c.TIE_WIDTH/2-.3,x+c.TIE_WIDTH/2+.3) for x in (-w/4,w/4)]
    sections=floor_sections(inner,depth,floor_top,openings)+rails(inner,depth,rail_top)
    # Unknown feet: use the outer device edges; each row splits across sides.
    loads=reactions(USW_LITE_16_KG,front,front+d,front+d/2)
    cross=[Beam(side*(inner/2+5.3)/2,.3,z,inner/2-5.3,floor_top-.6,20)
           for z in (front,front+d-20) for side in (-1,1)]
    return sections, cross, loads, depth, inner/2


def hub_cases(left_w,left_d,right_w,right_d,floor_top,rail_top):
    inner=left_w+right_w+4+c.RAIL_WALL
    depth=max(left_d,right_d)+37
    divider=-inner/2+left_w+2+c.RAIL_WALL/2
    for side,w,d,mass in ((-1,left_w,left_d,LUTRON_DESIGN_KG),(1,right_w,right_d,AQARA_DESIGN_KG)):
        outer=side*(inner+c.RAIL_WALL)/2
        # Each pocket owns its outer rail and HALF of the shared divider.
        # Independent cantilevers avoid assuming equal pocket depths/loads.
        # Only the interval up to the last load carries bending moment.
        # The rear notch may cut the divider in the unloaded cable tail.
        # The continuous outer rail carries the tip at the contact's slope;
        # no tail material is credited for bending stiffness.
        loaded_length=4+d-.3
        sections=[Beam(outer,.3,.3,c.RAIL_WALL-.6,rail_top-.6,depth-.6),
                  Beam(divider+side*(c.RAIL_WALL-.6)/4,.3,.3,(c.RAIL_WALL-.6)/2,rail_top-.6,loaded_length)]
        x=-inner/2+(w+2)/2 if side<0 else inner/2-(w+2)/2
        cross=[Beam(x,.3,z,w+2,floor_top-.6,19.4) for z in (4.3,4+d-20+.3)]
        loads=reactions(mass,4,4+d,4+d/2)
        yield sections,cross,loads,depth,w+2+c.RAIL_WALL


def evaluate(case, modulus, *, hub=False):
    sections,cross,loads,depth,span=case
    result=deflections(sections,loads,depth,modulus)
    if hub:
        # Two complete transverse strips, simply supported by pocket rails.
        cross_i=sum(b.length*b.height**3/12 for b in cross)
        result['transverse']=sum(p for p,a in loads)*span**3/(48*modulus*cross_i)
    else:
        # Rear notch interrupts transverse continuity. Treat EACH half-strip
        # as an independent cantilever from its side rail. Put half its row
        # reaction at the centreline (more severe than corner feet/pads).
        result['transverse']=max(loads[i//2][0]/2*span**3 /
                                 (3*modulus*(b.length*b.height**3/12)) for i,b in enumerate(cross))
    return result
