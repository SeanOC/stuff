"""Optional alignment pin, independent of the cup-lid fixture.

Positive fit is interference PER SIDE. This uses the measured small-hole
envelope (Ø8 mouth, 45° chamfer to the Ø6 thread minor), not its thread;
physical compatibility is not certified. The half-angle floor is 45° because
the bore wall is 45°: a shallower cone cannot be contained (pst-ozpae).
"""
from math import isfinite, radians, tan
from build123d import Align, Cone
from .constants import SMALL_HOLE_MOUTH_D


class SmallHoleConePin(Cone):
    """Base at Z=0; tip at +Z; lengths in mm, half-angle in degrees."""
    def __init__(self, fit_per_side=0.0, tip_diameter=1.8, half_angle=45.0):
        if not all(isfinite(v) for v in (fit_per_side, tip_diameter, half_angle)):
            raise ValueError('pin arguments must be finite')
        base = SMALL_HOLE_MOUTH_D + 2 * fit_per_side
        if not -0.3 <= fit_per_side <= 0.3:
            raise ValueError('fit_per_side must be in [-0.3, 0.3]')
        if not 45 <= half_angle <= 60:
            raise ValueError('half_angle must be in [45, 60]')
        if not 0 < tip_diameter < base:
            raise ValueError('tip_diameter must be positive and smaller than base')
        self.base_diameter = base
        self.tip_diameter = tip_diameter
        self.length = (base - tip_diameter) / (2 * tan(radians(half_angle)))
        super().__init__(base / 2, tip_diameter / 2, self.length,
                         align=(Align.CENTER, Align.CENTER, Align.MIN))
