"""Keystone negative tools: nominal window with a recessed rear latch seat."""
from build123d import Align, Box, Pos
from . import constants as c


def keystone_cutout():
    """Front 14.5 x 16 opening; rear relief leaves a 2.5 mm latch wall.

    Original clearance pocket, not an upstream geometry port. Confirm the
    chosen jack's latch on a fit print before fitting a complete panel.
    """
    through = Pos(0, 0, -1)*Box(c.KEYSTONE_WIDTH, c.KEYSTONE_HEIGHT, c.PANEL_THICKNESS+2,
                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    relief = Pos(0, 0, c.KEYSTONE_LATCH_WALL)*Box(
        c.KEYSTONE_WIDTH, c.KEYSTONE_HEIGHT+2*c.KEYSTONE_RELIEF, c.PANEL_THICKNESS,
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    return through+relief


def keystone_row(n):
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= c.MAX_KEYSTONES:
        raise ValueError(f'keystone count must be 1..{c.MAX_KEYSTONES} within USABLE_WIDTH')
    return [Pos((i-(n-1)/2)*c.KEYSTONE_PITCH, 0, 0)*keystone_cutout() for i in range(n)]


def mating_edge(edge, n, center_y):
    """Only the window/latch's edges above the bed chamfer are functional."""
    q = edge.center()
    if q.Z < 1e-6:
        return False
    for i in range(n):
        x = (i-(n-1)/2)*c.KEYSTONE_PITCH
        if (abs(q.X-x) <= c.KEYSTONE_WIDTH/2+1e-6
                and abs(q.Y-center_y) <= c.KEYSTONE_HEIGHT/2+c.KEYSTONE_RELIEF+1e-6):
            return True
    return False
