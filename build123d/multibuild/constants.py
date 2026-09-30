"""Board dimensions with provenance (docs/provenance.md, design-guidelines §7).

[V] = measured from an official file: ``source`` is the source_file_id in
reference/source-manifest.json and ``locator`` the committed measurement in
reference/measured/. Every value here is [V]; the cited SCAD values they
replaced are listed in docs/provenance.md (adopted by pst-ozpae).

Reading order: TILE_THICKNESS and the per-face tapers are roots; the large
band height is derived from them. The small hole is a 45° chamfer from the
mouth to the throat (thread minor) diameter on each face, then the thread,
so its taper depth is derived from those two diameters.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    value: float
    status: str
    source: str
    locator: str


PITCH = 25.0
TILE_THICKNESS = 6.2
SMALL_HOLE_MOUTH_D = 8.0
SMALL_HOLE_THROAT_D = 6.0
# 45° chamfer: the depth equals the radial run.
SMALL_HOLE_TAPER_DEPTH = (SMALL_HOLE_MOUTH_D - SMALL_HOLE_THROAT_D) / 2
LARGE_HOLE_TAPER_DEPTH = 2.0  # per face, octagon mouth to central flats
_M = 'reference/measured/'
_LARGE_CELL = 'multibuild-tile-components/large-octagon-hole-positive-.step'
_MULTIHOLE = 'multibuild-tile-components/multihole-negative-.step'
_SMALL_NEG = 'multibuild-tile-components/small-thread-negative-.step'
_SMALL_CELL = 'multibuild-tile-components/small-thread-hole-positive-.step'
PROVENANCE = {
    'PITCH': Provenance(PITCH, 'V', _LARGE_CELL, _M + 'mb-large-octagon-hole-positive.json'),
    # adopted 6.2 (Δ -0.2, cited 6.4) by pst-ozpae
    'TILE_THICKNESS': Provenance(TILE_THICKNESS, 'V', _LARGE_CELL, _M + 'mb-large-octagon-hole-positive.json'),
    # adopted 8.0 (Δ +0.5, cited 7.5) by pst-ozpae
    'SMALL_HOLE_MOUTH_D': Provenance(SMALL_HOLE_MOUTH_D, 'V', _SMALL_NEG, _M + 'mb-small-thread-negative.json'),
    'SMALL_HOLE_THROAT_D': Provenance(SMALL_HOLE_THROAT_D, 'V', _SMALL_NEG, _M + 'mb-small-thread-negative.json'),
    # adopted 1.0 (Δ -0.75, cited 1.75) by pst-ozpae
    'SMALL_HOLE_TAPER_DEPTH': Provenance(SMALL_HOLE_TAPER_DEPTH, 'V', _SMALL_NEG, _M + 'mb-small-thread-negative.json'),
    'LARGE_HOLE_TAPER_DEPTH': Provenance(LARGE_HOLE_TAPER_DEPTH, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
}
LARGE_HOLE_PROFILE = {
    'mouth_across_flats': Provenance(23.4, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    'central_across_flats': Provenance(21.4, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    # adopted 2.2 (Δ -0.2, cited 2.4) by pst-ozpae
    'band_height': Provenance(TILE_THICKNESS - 2 * LARGE_HOLE_TAPER_DEPTH, 'V', _MULTIHOLE,
                              _M + 'mb-multihole-negative.json'),
    # adopted 22.5 (Δ -0.1, cited 22.6) by pst-ozpae
    'helix_outer_d': Provenance(22.5, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    'helix_inner_d': Provenance(21.4, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    'helix_outer_width': Provenance(0.5, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    # adopted 1.6 (Δ +0.017, cited 1.583) by pst-ozpae; 45° flanks
    'helix_inner_width': Provenance(1.6, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    'helix_pitch': Provenance(2.5, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
}
# (status, source, locator): large cell centred on (0, 0), small-hole cell on
# (12.5, 12.5) in the tile-component files' shared frame.
GRID_PHASE_PROVENANCE = ('V', f'{_LARGE_CELL} + {_SMALL_CELL}',
                         f'{_M}mb-large-octagon-hole-positive.json + {_M}mb-small-thread-hole-positive.json')

def large_hole_center(i: int, j: int) -> tuple[float, float]:
    return (PITCH * i + PITCH / 2, PITCH * j + PITCH / 2)


def small_hole_center(i: int, j: int) -> tuple[float, float]:
    return (PITCH * i + PITCH, PITCH * j + PITCH)
