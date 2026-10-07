# SPDX-License-Identifier: MIT
"""No-lip Gridfinity bin, derived from Gridfinity Rebuilt (MIT).

[C] kennetek/gridfinity-rebuilt-openscad@910e22d8607fd7f5f51ad5e5cbc5287a76810bfd,
src/core/standard.scad:175-229: base profile, pitch, radii, height units.
See assets/gridfinity-rebuilt/NOTICE for licence and reference reproduction.
The bin profile is 4.75 mm tall; the mating socket is independently 4.65 mm.
"""
from itertools import product

from build123d import Pos, RectangleRounded, extrude, fillet, loft

PITCH = 42
TOP_SIZE = 41.5
TOP_RADIUS = 3.75
LOWER_TAPER = 0.8
RISER = 1.8
UPPER_TAPER = 2.15
PROFILE_HEIGHT = LOWER_TAPER + RISER + UPPER_TAPER
BASE_HEIGHT = 7
# [C] standard.scad:4,7,10,20 and bin.scad bin_get_infill_size_mm,
# cutouts.scad cgs(): .95 wall + (1.2/2)/2 divider - .02/2 infill.
REFERENCE_WALL = 1.24
INNER_RADIUS = 2.8


def outline(w_units, d_units):
    return RectangleRounded(w_units*PITCH-.5, d_units*PITCH-.5, TOP_RADIUS)


def base(w_units, d_units):
    """Feet plus the continuous bridge to Z=7; bottom 0.8 mm is 45° relief."""
    for value in (w_units, d_units):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError('cell counts must be positive integers')
    mid = RectangleRounded(TOP_SIZE-2*UPPER_TAPER, TOP_SIZE-2*UPPER_TAPER,
                           TOP_RADIUS-UPPER_TAPER)
    low = RectangleRounded(TOP_SIZE-2*(UPPER_TAPER+LOWER_TAPER),
                           TOP_SIZE-2*(UPPER_TAPER+LOWER_TAPER),
                           TOP_RADIUS-UPPER_TAPER-LOWER_TAPER)
    foot = loft([low, Pos(0, 0, LOWER_TAPER)*mid], ruled=True)
    foot += extrude(Pos(0, 0, LOWER_TAPER)*mid, amount=RISER)
    foot += loft([Pos(0, 0, LOWER_TAPER+RISER)*mid,
                  Pos(0, 0, PROFILE_HEIGHT)*outline(1, 1)], ruled=True)
    part = extrude(Pos(0, 0, PROFILE_HEIGHT)*outline(w_units, d_units),
                   amount=BASE_HEIGHT-PROFILE_HEIGHT)
    feet = [Pos((x-(w_units-1)/2)*PITCH, (y-(d_units-1)/2)*PITCH)*foot
            for x, y in product(range(w_units), range(d_units))]
    return part.fuse(*feet).clean()


def blank(w_units, d_units, height_units):
    """Solid pocket stock; the capture model exposes this before edge treatment."""
    if height_units < 1:
        raise ValueError('height must be at least one unit')
    part = base(w_units, d_units)
    if height_units > 1:
        part += extrude(Pos(0, 0, BASE_HEIGHT)*outline(w_units, d_units),
                        amount=(height_units-1)*BASE_HEIGHT)
    return part


def body(w_units, d_units, height_units, wall=1.6):
    """Open bin with a flat floor and the reference R2.8 inner floor transition.

    This is the pre-treatment parity solid: no top rim edge break.
    """
    part = blank(w_units, d_units, height_units)
    width, depth = w_units*PITCH-.5-2*wall, d_units*PITCH-.5-2*wall
    if min(width, depth) <= 2*INNER_RADIUS or height_units*BASE_HEIGHT <= BASE_HEIGHT+INNER_RADIUS:
        raise ValueError('bin cavity too small')
    # GR's infill exterior is inset .01 from its base bridge. Keeping a single
    # continuous exterior differs by only .01 mm (inside the parity cap).
    cutter = extrude(Pos(0, 0, BASE_HEIGHT+.02)*RectangleRounded(width, depth, INNER_RADIUS),
                     amount=(height_units-1)*BASE_HEIGHT)
    bottom = [e for e in cutter.edges() if e.bounding_box().max.Z < BASE_HEIGHT+.021]
    cutter = fillet(bottom, radius=INNER_RADIUS-.001)
    return part-cutter
