# Derived from MultiBuild remixing files — Multiboard Licence (non-commercial,
# remixes under the same terms); NOT covered by this repository's MIT licence.
# See build123d/multibuild/LICENSE-MULTIBOARD.md.
"""Regenerated MultiBuild tile, our own B-rep built from measured values.

Attribution: the underlying tile design is by Multiboard LTD (MultiBuild,
https://multibuild.io). No upstream file is loaded or copied. The
dimensions are measured from the official tile-component remixing STEPs
(``reference/measured/mb-*.json``, docs/provenance.md). This is a fixture
for installed-part review renders, so it is not a registered model.

Envelope only: the octagon and small-hole bores are the thread MINOR
diameters, the helical grooves are omitted, and the tile edges are plain
(no teeth or snap features). Nothing threads into this tile.

``TILE_PROFILE`` names the measured [V] records in ``constants`` that the
tile is built from; it holds no values of its own.
"""
from build123d import Align, Box, Cone, Cylinder, Part, Pos, RegularPolygon, Plane, loft
from .constants import LARGE_HOLE_PROFILE, PITCH, PROVENANCE, large_hole_center, small_hole_center

TILE_PROFILE = {
    'thickness': PROVENANCE['TILE_THICKNESS'],
    'large_mouth_across_flats': LARGE_HOLE_PROFILE['mouth_across_flats'],
    'large_central_across_flats': LARGE_HOLE_PROFILE['central_across_flats'],
    'large_taper_depth': PROVENANCE['LARGE_HOLE_TAPER_DEPTH'],
    'small_mouth_d': PROVENANCE['SMALL_HOLE_MOUTH_D'],
    'small_throat_d': PROVENANCE['SMALL_HOLE_THROAT_D'],
    'small_taper_depth': PROVENANCE['SMALL_HOLE_TAPER_DEPTH'],
}


def _v(key: str) -> float:
    return TILE_PROFILE[key].value


def _octagon(across_flats: float, z: float):
    # Flats on the X/Y axes, as in the official files.
    return Plane.XY.offset(z) * RegularPolygon(across_flats / 2, 8, major_radius=False, rotation=22.5)


def large_hole_negative() -> Part:
    t, taper = _v('thickness'), _v('large_taper_depth')
    mouth, central = _v('large_mouth_across_flats'), _v('large_central_across_flats')
    lower = loft([_octagon(mouth, 0), _octagon(central, taper)])
    band = loft([_octagon(central, taper), _octagon(central, t - taper)])
    upper = loft([_octagon(central, t - taper), _octagon(mouth, t)])
    return lower + band + upper


def small_hole_negative() -> Part:
    t, taper = _v('thickness'), _v('small_taper_depth')
    mouth, throat = _v('small_mouth_d') / 2, _v('small_throat_d') / 2
    bottom = (Align.CENTER, Align.CENTER, Align.MIN)
    return (Cone(mouth, throat, taper, align=bottom)
            + Cylinder(throat, t, align=bottom)
            + Pos(0, 0, t - taper) * Cone(throat, mouth, taper, align=bottom))


def tile(cells: tuple[int, int] = (2, 2)) -> Part:
    """Tile of ``cells`` (x, y) at the 25 mm pitch; corner at the origin, Z=0..thickness.

    Large holes sit at every cell centre (``large_hole_center``). Small holes sit
    at every interior lattice point (``small_hole_center``); edge half-holes are omitted."""
    nx, ny = cells
    if not all(isinstance(n, int) and not isinstance(n, bool) and n >= 1 for n in (nx, ny)):
        raise ValueError('cells must be two positive integers')
    part = Box(nx * PITCH, ny * PITCH, _v('thickness'), align=(Align.MIN, Align.MIN, Align.MIN))
    large, small = large_hole_negative(), small_hole_negative()
    for i in range(nx):
        for j in range(ny):
            part -= Pos(*large_hole_center(i, j), 0) * large
    for i in range(nx - 1):
        for j in range(ny - 1):
            part -= Pos(*small_hole_center(i, j), 0) * small
    return part
