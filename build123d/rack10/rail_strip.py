"""HomeRacker rail, X outer edge to flange, Y up the post, Z rearwards.

Front face on Z=0 is the print bed. Equipment weight acts along Y (layers);
cantilever pull-off loads the peg roots across layers. No load rating is claimed.
The two grids are independent: every interior post station has a mount.
"""
from math import isfinite

from build123d import Align, Box, Cone, Cylinder, GeomType, Pos, Rot

from . import constants as c
from .panel import finish


class RailFitError(ValueError):
    """Requested hardware or one-piece print cannot fit the rail envelope."""


def rail_length(pin_units):
    if isinstance(pin_units, bool) or not isinstance(pin_units, int) or pin_units < 5:
        raise ValueError('pin_units must be an integer from 5 to 27')
    if pin_units > c.RAIL_MAX_UNITS:
        raise RailFitError("27-unit bed limit (325 × 320 mm): segment at a connector sleeve")
    return pin_units * c.PEG_PITCH


def peg_stations(pin_units):
    rail_length(pin_units)
    return [c.PEG_PITCH * (k + .5) for k in range(1, pin_units - 1)]


def rail_hole_centres(pin_units):
    """Complete U groups only, centered in each post segment independently."""
    length = rail_length(pin_units)
    units = int(length // c.RACK_UNIT)
    datum = (length - units * c.RACK_UNIT) / 2
    return [(c.RAIL_HOLE_X, datum + u*c.RACK_UNIT + c.HOLE_EDGE + i*c.HOLE_PITCH)
            for u in range(units) for i in range(c.HOLES_PER_UNIT)]


def rail_print_frame(values):
    # Long strips use the diagonal; the endpoint audit still checks bed fit.
    return Rot(0, 0, 45 if values['pin_units'] > 21 else 0)


def rail_strip(pin_units=18, thickness=c.RAIL_THICKNESS, *, mount='pegs', hole='insert'):
    length = rail_length(pin_units)
    if not isfinite(thickness) or not 11 <= thickness <= 14:
        raise ValueError('thickness must be 11..14 mm')
    if mount not in ('pegs', 'pin_holes') or hole not in ('insert', 'cage_nut'):
        raise ValueError('unknown rail mount or hole mode')

    part = Box(c.RAIL_WIDTH, length, thickness, align=(Align.MIN,)*3)
    # Includes the sleeve's 2.1 mm overlap into the flange, not just the post.
    # Concave edge finishing adds material. Extend the cutter by that amount
    # so the finished edge cannot intrude into the sleeve keep-out volume.
    relief = c.EDGE_CHAMFER
    for y in (-relief, length-c.PEG_PITCH-relief):
        part -= Pos(-1, y, thickness-c.SLEEVE_RELIEF_D-relief)*Box(
            c.SLEEVE_RELIEF_W+1+relief, c.PEG_PITCH+2*relief, c.SLEEVE_RELIEF_D+1+relief,
            align=(Align.MIN,)*3)

    if hole == 'cage_nut':
        # A continuous open rear channel permits insertion and release of the
        # cage. It avoids thin partitions between consecutive EIA holes.
        part -= Pos(c.SLEEVE_RELIEF_W, -1, c.CAGE_WEB)*Box(
            c.RAIL_WIDTH-c.SLEEVE_RELIEF_W+1, length+2, thickness, align=(Align.MIN,)*3)
    cone_height = (c.INSERT_M6_HOLE_D-c.SCREW_CLEAR)/2
    for x, y in rail_hole_centres(pin_units):
        if hole == 'insert':
            part -= Pos(x, y, -1)*Cylinder(c.INSERT_M6_HOLE_D/2, c.INSERT_POCKET_DEPTH+1,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
            part -= Pos(x, y, c.INSERT_POCKET_DEPTH)*Cone(
                c.INSERT_M6_HOLE_D/2, c.SCREW_CLEAR/2, cone_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
            part -= Pos(x, y, c.INSERT_POCKET_DEPTH+cone_height)*Cylinder(
                c.SCREW_CLEAR/2, thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
        else:
            part -= Pos(x, y, -1)*Box(c.CAGE_SQUARE, c.CAGE_SQUARE, c.CAGE_WEB+2,
                                     align=(Align.CENTER, Align.CENTER, Align.MIN))

    for y in peg_stations(pin_units):
        if mount == 'pegs':
            part += Pos(c.PEG_PITCH/2, y, thickness-c.PEG_ROOT)*Box(
                c.PEG_SQUARE-c.PEG_TOL, c.PEG_SQUARE-c.PEG_TOL, c.PEG_LENGTH+c.PEG_ROOT,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
        else:
            part -= Pos(c.PEG_PITCH/2, y, -1)*Box(c.PEG_SQUARE, c.PEG_SQUARE, thickness+2,
                                                align=(Align.CENTER, Align.CENTER, Align.MIN))
    # These 45° circular seams define the insert seat. Chamfering them would
    # shorten the specified cylindrical pocket and steepen the conical ceiling.
    def insert_seat(edge):
        return hole == 'insert' and edge.geom_type == GeomType.CIRCLE and any(
            abs(edge.center().Z-z) < 1e-6
            for z in (c.INSERT_POCKET_DEPTH, c.INSERT_POCKET_DEPTH+cone_height))
    return finish(part, functional=insert_seat)
