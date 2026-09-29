"""Provisional board dimensions; evidence tags are not official measurements.

Source keys and locators: docs/multibuild-research.md §2.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    value: float
    status: str
    source: str
    locator: str


PITCH = 25.0
TILE_THICKNESS = 6.4
SMALL_HOLE_MOUTH_D = 7.5
SMALL_HOLE_THROAT_D = 6.0
SMALL_HOLE_THROAT_BAND = 2.9
SMALL_HOLE_TAPER_DEPTH = (TILE_THICKNESS - SMALL_HOLE_THROAT_BAND) / 2
PROVENANCE = {
    'PITCH': Provenance(PITCH, 'C', 'Core', 'Measurement System; §1 L29,42'),
    'TILE_THICKNESS': Provenance(TILE_THICKNESS, 'C', 'SCAD', 'L56–61'),
    'SMALL_HOLE_MOUTH_D': Provenance(SMALL_HOLE_MOUTH_D, 'C', 'SCAD', 'L96–104,237–265'),
    'SMALL_HOLE_THROAT_D': Provenance(SMALL_HOLE_THROAT_D, 'C', 'SCAD', 'L96–104,237–265'),
    'SMALL_HOLE_THROAT_BAND': Provenance(SMALL_HOLE_THROAT_BAND, 'C', 'SCAD', 'L96–104,237–265'),
    'SMALL_HOLE_TAPER_DEPTH': Provenance(SMALL_HOLE_TAPER_DEPTH, 'V', 'SCAD', 'Arithmetic, L270–280'),
}
LARGE_HOLE_PROFILE = {
    'mouth_across_flats': Provenance(23.4, 'C', 'SCAD', 'L68–83,218–224,270–280'),
    'central_across_flats': Provenance(21.4, 'C', 'SCAD', 'L68–83,218–224,270–280'),
    'band_height': Provenance(2.4, 'C', 'SCAD', 'L68–83,218–224,270–280'),
    'helix_outer_d': Provenance(22.6, 'C', 'SCAD', 'L85–94,228–233'),
    'helix_inner_d': Provenance(21.4, 'C', 'SCAD', 'L85–94,228–233'),
    'helix_outer_width': Provenance(0.5, 'C', 'SCAD', 'L85–94,228–233'),
    'helix_inner_width': Provenance(1.583, 'C', 'SCAD', 'L85–94,228–233'),
    'helix_pitch': Provenance(2.5, 'C', 'SCAD', 'L85–94,228–233'),
}
GRID_PHASE_PROVENANCE = ('V', 'SCAD', 'Arithmetic on coordinates, L135–162,167–193')


def large_hole_center(i: int, j: int) -> tuple[float, float]:
    return (PITCH * i + PITCH / 2, PITCH * j + PITCH / 2)


def small_hole_center(i: int, j: int) -> tuple[float, float]:
    return (PITCH * i + PITCH, PITCH * j + PITCH)
