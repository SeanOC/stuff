"""Vent cutters on a regular grid; every aperture stays below 10 mm."""
from math import floor, isfinite, sqrt
from build123d import Pos, Rectangle, extrude
from . import constants as c


def vent_pattern(area, open_fraction):
    """Return centred square-slot cutters for an (X width, Y height) area.

    Fraction is the nominal through-area before edge relief, 0..0.5. The
    grid divides the whole area, with half a web at its outer boundaries.
    """
    width, height = area
    if not all(isfinite(v) for v in (width, height, open_fraction)) or min(width, height) < 10:
        raise ValueError('vent area must have finite width and height >= 10 mm')
    if not 0 <= open_fraction <= .5:
        raise ValueError('open_fraction must be between 0 and 0.5')
    if open_fraction == 0:
        return []
    nx, ny = max(1, floor(width/10)), max(1, floor(height/10))
    dx, dy = width/nx, height/ny
    sx, sy = dx*sqrt(open_fraction), dy*sqrt(open_fraction)
    if min(sx, sy) < 2 or max(sx, sy) > 10 or min(dx-sx, dy-sy) < 1.8+2*c.EDGE_CHAMFER:
        raise ValueError('vent aperture or web is outside the printable range; change area/open_fraction')
    return [Pos((i-(nx-1)/2)*dx, (j-(ny-1)/2)*dy, -1)*extrude(Rectangle(sx, sy), amount=c.EAR_THICKNESS+2)
            for i in range(nx) for j in range(ny)]
