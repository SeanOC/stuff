# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Detached, toothed cradle; crown at Z=0 in the local print frame.

The pad peels away with all fins. No sacrificial material touches the cable
channel; cable loads remain on its original walls and grip interfaces.
"""
from dataclasses import dataclass
from math import ceil, cos, pi, sin, sqrt

from build123d import (Align, Box, Edge, Face, Pos, RectangleRounded, Vector,
                      Wire, chamfer, extrude)

PAD_THICKNESS = 0.6
CROWN_RISE = 1.0
MARGIN = 5.0
CORNER_RADIUS = 4.0
FIN_THICKNESS = 0.95
FIN_PITCH_MAX = 6.0  # diagonal of a contact cell stays below the 10 mm bridge limit
TOOTH_LENGTH = 0.95
TOOTH_RELIEF = 0.6
EAR_LENGTH = 10.0
ARM_BACKING = 3.0


@dataclass(frozen=True)
class DesignedSupport:
    """Exact pad/fins plus normal-gap probes and bracketed contact cells.

    Contacts are (tooth-top point, outward normal of the retained surface).
    Cells index their four corners, ordered around the surface footprint.
    The audit verifies these against actual retained faces and support solids;
    declarations alone never exempt material or an unsupported surface.
    """
    gap_mm: float
    pad: object
    fins: tuple
    bridge_axis: tuple = (1., 0., 0.)
    contacts: tuple = ()
    cells: tuple = ()

    def moved(self, frame):
        from build123d import Matrix
        transform = Matrix(frame.wrapped.Transformation())
        origin = Vector(0, 0, 0).transform(transform)
        def direction(v):
            return tuple(Vector(v).transform(transform) - origin)
        return DesignedSupport(self.gap_mm, frame * self.pad,
                               tuple(frame * f for f in self.fins), direction(self.bridge_axis),
                               tuple((tuple(Vector(q).transform(transform)), direction(n))
                                     for q, n in self.contacts), self.cells)


def dimensions(width, radius, gap=.2):
    """Main pad rectangle (pull ear extends EAR_LENGTH in +X)."""
    return width - 8 + 2*MARGIN, sqrt(2)*(radius+gap) + 2*(ARM_BACKING+MARGIN)


def tooth_grid(width, radius, gap):
    flat_width = width - 8
    nx = max(2, ceil((flat_width-FIN_THICKNESS)/FIN_PITCH_MAX)+1)
    xs = [-(flat_width-FIN_THICKNESS)/2 + i*(flat_width-FIN_THICKNESS)/(nx-1)
          for i in range(nx)]
    half = ceil((radius+gap)*pi/4/FIN_PITCH_MAX)
    angles = [i*pi/4/half for i in range(-half, half+1)]
    return xs, angles


def cradle(width, radius, gap, *, mirrored=False):
    """Uniform pad, toothed crown rail and curved flank fins at a normal gap.

    Notches are radial, preserving the normal gap on the remaining lands.
    The rail rises 1 mm above the pad at the crown (mayor rev 2). Its recessed
    web and the pad together are >=1 mm thick; fin walls are 0.95 mm.
    """
    pw, pl = dimensions(width, radius, gap)
    top = -gap-CROWN_RISE
    bottom = top-PAD_THICKNESS
    pad = Pos(0, 0, bottom)*extrude(RectangleRounded(pw, pl, CORNER_RADIUS), PAD_THICKNESS)
    ear = Pos((pw/2+EAR_LENGTH/2-1)*(-1 if mirrored else 1), 0, bottom)*extrude(
        RectangleRounded(EAR_LENGTH+2, 10, CORNER_RADIUS), PAD_THICKNESS)
    pad = pad.fuse(ear)
    pad = chamfer([e for e in pad.edges() if abs(e.center().Z-bottom)<1e-6], length=.3)
    xs, angles = tooth_grid(width, radius, gap)
    rr = radius+gap
    turn = rr/sqrt(2)
    end = turn+ARM_BACKING
    def point(a, r=rr, x=0):
        return (x, r*sin(a), radius-r*cos(a))
    # Whole curved profile, extended under each arm to avoid a thin end wedge.
    a, b = point(-pi/4), point(pi/4)
    left, right = (0, -end, a[2]+ARM_BACKING), (0, end, b[2]+ARM_BACKING)
    outline = Wire([Edge.make_line((0,-end,bottom), left), Edge.make_line(left,a),
                    Edge.make_three_point_arc(a,point(0),b), Edge.make_line(b,right),
                    Edge.make_line(right,(0,end,bottom)),
                    Edge.make_line((0,end,bottom),(0,-end,bottom))])
    profile = Face(outline)
    fins = [Pos(x-FIN_THICKNESS/2,0,0)*extrude(profile, amount=FIN_THICKNESS, dir=(1,0,0))
            for x in xs]
    # Flat crown rail across X. The curved central teeth of the flank fins
    # meet it; a curved rail side would leave a hairline lip at that junction.
    rail = Pos(0,0,bottom)*Box(width-8,FIN_THICKNESS,PAD_THICKNESS+CROWN_RISE,
                             align=(Align.CENTER,Align.CENTER,Align.MIN))
    for x1,x2 in zip(xs,xs[1:]):
        rail -= Pos((x1+x2)/2,0,top+CROWN_RISE-TOOTH_RELIEF)*Box(
            x2-x1-TOOTH_LENGTH, 2, 2*radius+10,
            align=(Align.CENTER,Align.CENTER,Align.MIN))
    # Remove radial bands between adjacent tooth lands from every flank fin.
    notches = []
    half_land = TOOTH_LENGTH/2/rr
    for a1,a2 in zip(angles,angles[1:]):
        lo,hi = a1+half_land,a2-half_land
        r1,r2 = rr-1,rr+TOOTH_RELIEF
        # The inside radius extends into the void; only the outside edge sets relief.
        wire = Wire([Edge.make_three_point_arc(point(lo,r1),point((lo+hi)/2,r1),point(hi,r1)),
                     Edge.make_line(point(hi,r1),point(hi,r2)),
                     Edge.make_three_point_arc(point(hi,r2),point((lo+hi)/2,r2),point(lo,r2)),
                     Edge.make_line(point(lo,r2),point(lo,r1))])
        notches.append(Pos(-pw/2,0,0)*extrude(Face(wire), amount=pw, dir=(1,0,0)))
    # Recess the arm continuations too: only the last half-land touches the gap.
    for sign in (-1,1):
        # Side walls follow the surface normal, keeping the last tooth
        # 0.95 mm thick along its tangent (a vertical notch makes a wedge).
        def arm_point(t, depth):
            return (0, sign*(turn+(t+depth)/sqrt(2)), radius-turn+(t-depth)/sqrt(2))
        pts = [arm_point(TOOTH_LENGTH/2,-1), arm_point(ARM_BACKING*sqrt(2)+2,-1),
               arm_point(ARM_BACKING*sqrt(2)+2,TOOTH_RELIEF),
               arm_point(TOOTH_LENGTH/2,TOOTH_RELIEF)]
        notches.append(Pos(-pw/2,0,0)*extrude(Face(Wire.make_polygon(pts,close=True)),
                                            amount=pw,dir=(1,0,0)))
    fins = [f.cut(*notches) for f in fins]
    fins.append(rail)
    # Include the full X land width at the two outer floor edges in the
    # bracketing mesh. All probes remain on real tooth material.
    probes_x = [-(width-8)/2+1e-5, *xs, (width-8)/2-1e-5]
    contacts = tuple((point(a,x=x),(0,sin(a),-cos(a))) for a in angles for x in probes_x)
    n = len(probes_x)
    cells = tuple((j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i)
                  for j in range(len(angles)-1) for i in range(n-1))
    return DesignedSupport(gap,pad,tuple(fins),contacts=contacts,cells=cells)
