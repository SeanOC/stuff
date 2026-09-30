"""Board dimensions with provenance (docs/provenance.md, design-guidelines §7).

[V] = measured from an official file: ``source`` is the source_file_id in
reference/source-manifest.json and ``locator`` the committed measurement in
reference/measured/. [C] = cited claim: ``source`` is a key in
docs/multibuild-research.md §2 and ``locator`` its lines. [U] = unresolved.
Values that the official files contradict are NOT changed here; they stay [C]
with a follow-up bead (``# measured`` comments; research §2 has the deltas).
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
# 45° Ø8→Ø6 chamfer depth, measured directly (pst-3spc5); no longer
# (TILE_THICKNESS - SMALL_HOLE_THROAT_BAND) / 2 while those two stay cited.
SMALL_HOLE_TAPER_DEPTH = 1.0
_M = 'reference/measured/'
_LARGE_CELL = 'multibuild-tile-components/large-octagon-hole-positive-.step'
_MULTIHOLE = 'multibuild-tile-components/multihole-negative-.step'
_SMALL_NEG = 'multibuild-tile-components/small-thread-negative-.step'
_SMALL_CELL = 'multibuild-tile-components/small-thread-hole-positive-.step'
PROVENANCE = {
    'PITCH': Provenance(PITCH, 'V', _LARGE_CELL, _M + 'mb-large-octagon-hole-positive.json'),
    # measured 6.2 (Δ -0.2): pst-rs70f
    'TILE_THICKNESS': Provenance(TILE_THICKNESS, 'C', 'SCAD', 'L56–61'),
    # measured 8.0 (Δ +0.5): pst-az4hh
    'SMALL_HOLE_MOUTH_D': Provenance(SMALL_HOLE_MOUTH_D, 'C', 'SCAD', 'L96–104,237–265'),
    'SMALL_HOLE_THROAT_D': Provenance(SMALL_HOLE_THROAT_D, 'V', _SMALL_NEG, _M + 'mb-small-thread-negative.json'),
    # measured 4.2 (Δ +1.3): pst-hav1h
    'SMALL_HOLE_THROAT_BAND': Provenance(SMALL_HOLE_THROAT_BAND, 'C', 'SCAD', 'L96–104,237–265'),
    'SMALL_HOLE_TAPER_DEPTH': Provenance(SMALL_HOLE_TAPER_DEPTH, 'V', _SMALL_NEG, _M + 'mb-small-thread-negative.json'),
}
LARGE_HOLE_PROFILE = {
    'mouth_across_flats': Provenance(23.4, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    'central_across_flats': Provenance(21.4, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    # measured 2.2 (Δ -0.2): pst-kooqt
    'band_height': Provenance(2.4, 'C', 'SCAD', 'L68–83,218–224,270–280'),
    # measured 22.5 (Δ -0.1): pst-23uzq
    'helix_outer_d': Provenance(22.6, 'C', 'SCAD', 'L85–94,228–233'),
    'helix_inner_d': Provenance(21.4, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    'helix_outer_width': Provenance(0.5, 'V', _MULTIHOLE, _M + 'mb-multihole-negative.json'),
    # measured 1.6 (Δ +0.017): pst-x5vo8
    'helix_inner_width': Provenance(1.583, 'C', 'SCAD', 'L85–94,228–233'),
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
