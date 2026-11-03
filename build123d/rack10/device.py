"""Shared original device-mount construction, front face on the print bed.

Rack up is +Y; rearwards is +Z. All rear features grow off the floor with
45-degree leading ramps so face-down printing requires no supports.
"""
from build123d import Align, Box, Face, Pos, Solid, Vector, Wire, extrude
from . import constants as c
from .panel import panel, panel_height
from .vent import vent_pattern


def box(w, h, d, x=0, y=0, z=0):
    return Pos(x,y,z)*Box(w,h,d,align=(Align.CENTER,Align.MIN,Align.MIN))


def ramp(w, rise, length, x, y, z):
    """Raised feature with a 45-degree leading and trailing ramp."""
    taper=min(rise,(w-1.8)/2)
    profiles=[]
    for y0,w0,start,end in ((y-.1,w+.2,z-.1,z+length+.1),
                            (y+rise,w-2*taper,z+rise,z+length-rise)):
        profiles.append(Wire.make_polygon([Vector(x+dx,y0,zz) for dx,zz in
            ((-w0/2,start),(w0/2,start),(w0/2,end),(-w0/2,end))],close=True))
    return Solid.make_loft(profiles,ruled=True)


def bezel(units, inner, bottom, slot_mm):
    part=panel(units,slot_mm=slot_mm,finished=False)
    # Full device face is exposed; the top beam lies above its envelope.
    return part-box(inner,panel_height(units)-bottom-3,6,y=bottom,z=-1)


def pad_positions(device_w,device_d,front):
    nx,ny=int(device_w//10),int(device_d//10)
    return [(x,z) for x in (-device_w/2+device_w/nx/2,device_w/2-device_w/nx/2)
            for z in (front+device_d/ny/2-4,front+device_d-device_d/ny/2-4)]


def vent_floor(part, width, depth, top, center_z, fraction=.45, reserve_pads=False):
    rows=max(2,int(depth//40))
    grid_depth=10*rows
    stretch=depth/grid_depth
    cutters=vent_pattern((width,grid_depth),fraction)
    keep=[]
    locations=pad_positions(width,depth,center_z-depth/2) if reserve_pads else []
    for p in cutters:
        q=p.center()
        z=stretch*q.Y+center_z
        b=p.bounding_box();w,h=b.size.X,stretch*b.size.Y+b.size.X/4
        if any(abs(q.X-x)<w/2+6 and abs(z-(pz+4))<h/2+6 for x,pz in locations): continue
        # Leave a solid border around the 10 mm rear notch.
        if abs(q.X)<10 and z+h/2>center_z+depth/2-14: continue
        lo=z-h/2
        # Same area as the library slot, with a 45-degree peaked ceiling.
        pts=[Vector(q.X-w/2,top+1,lo),Vector(q.X+w/2,top+1,lo),
             Vector(q.X+w/2,top+1,lo+h-w/2),Vector(q.X,top+1,lo+h),
             Vector(q.X-w/2,top+1,lo+h-w/2)]
        keep.append(extrude(Face(Wire.make_polygon(pts,close=True)),amount=top+2,dir=(0,-1,0)))
    return part.cut(*keep)


def pads(part, device_w, device_d, floor_top, front):
    for x,z in pad_positions(device_w,device_d,front):
        profiles=[]
        for y,w in ((floor_top-.1,10.2),(floor_top+1,8)):
            profiles.append(Wire.make_polygon([Vector(x+dx,y,z+4+dz) for dx,dz in
                ((-w/2,-w/2),(w/2,-w/2),(w/2,w/2),(-w/2,w/2))],close=True))
        part += Solid.make_loft(profiles,ruled=True)
    return part


def rear_notch(part, depth, floor_top, x=0):
    return part-box(10,floor_top+20,11,x=x,y=-1,z=depth-10)

def finish_device(part, functional=None):
    """Keep existing 45-degree ramps; chamfer remaining right-angle edges.

    The ramp is already the edge treatment. Chamfering its shallow end a
    second time creates vanishing slivers at its junction with the floor.
    """
    from build123d import chamfer
    adjacent={}
    for face in part.faces():
        for edge in face.edges(): adjacent.setdefault(edge,[]).append(face)
    edges=[]
    for edge,faces in adjacent.items():
        if len(faces)!=2 or (functional and functional(edge)): continue
        q=edge.center()
        normals=[f.normal_at(q) for f in faces]
        # A peaked aperture's ridge is functional: rounding it introduces a
        # flat downward ceiling. Its two exact 45-degree roofs stay sharp.
        if all(abs(n.Y)<1e-6 and n.Z<-.7 for n in normals): continue
        if faces[0].normal_at(q).dot(faces[1].normal_at(q))<1e-6:
            edges.append(edge)
    return chamfer(edges,c.EDGE_CHAMFER) if edges else part

def blend_floor(part, inner_edges, *, rounded=True):
    """1 mm stress relief where continuous pocket rails meet the floor."""
    from build123d import chamfer, fillet
    roots=[e for e in part.edges() if abs(e.center().Y-c.FLOOR)<1e-6
           and e.center().Z>c.PANEL_THICKNESS
           and any(abs(e.center().X-x)<1e-6 for x in inner_edges)]
    return (fillet(roots,1.0) if rounded else chamfer(roots,1.0)) if roots else part
