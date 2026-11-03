"""Raised device decks; separate from the unchanged Sonos shelf helpers."""
from build123d import Face, Vector, Wire, chamfer, extrude, fillet
from . import constants as c
from .panel import panel_height
from .tray import TrayFitError


def check_height(device_h, units, floor_top, pad=0, gap=.6):
    # Preserve the bezel's 3 mm top beam and positive device clearance.
    if floor_top+pad+device_h+gap>panel_height(units)-3:
        raise TrayFitError('stiffened deck and device exceed the open bezel height')


def blend(part, inner_edges, top, *, rounded=True):
    roots=[e for e in part.edges() if abs(e.center().Y-top)<1e-6
           and e.center().Z>c.PANEL_THICKNESS
           and any(abs(e.center().X-x)<1e-6 for x in inner_edges)]
    return (fillet(roots,1.0) if rounded else chamfer(roots,1.0)) if roots else part


def tie_cutter(x,z,top):
    w,length=c.TIE_WIDTH,c.TIE_LENGTH
    points=[(x-w/2,-1,z-length/2),(x+w/2,-1,z-length/2),
            (x+w/2,-1,z+length/2-w/2),(x,-1,z+length/2),(x-w/2,-1,z+length/2-w/2)]
    return extrude(Face(Wire.make_polygon([Vector(*p) for p in points],close=True)),
                   amount=top+2,dir=(0,1,0))


def tie_edge(edge,w,d,top):
    q=edge.center()
    return (-1e-6<=q.Y<=top+1e-6 and any(
        abs(q.X-x)<=c.TIE_WIDTH/2+1e-6 and abs(q.Z-z)<=c.TIE_LENGTH/2+1e-6
        for x in (-w/4,w/4) for z in (3+d/3,3+2*d/3)))
