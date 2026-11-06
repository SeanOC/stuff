"""openGrid tile generator — Full/Lite, optional adhesive back, lattice masks.

Print back down (+Z up); worst load is a cantilevered accessory pulling the
tile away from adhesive. Use light accessories: 1 mm backing is a deliberate
shallow adhesive substrate (five 0.2 mm layers), not a 2.4 mm structural mount
plate. PLA/PCTG both need an adhesive and substrate appropriate to that load.

Design-guidelines §6 checklist:
1. Back down; UNDERSIDE review shows the bed face. Vendor taper is atan(.7/1)
   = 34.99 degrees from vertical; snap opening bevel is 45 degrees.
   Connector ceilings are exact vendor mating pockets: raw local bridge span
   is 5 mm. Only their angle is excluded, never bridge length or wall thickness.
2. No added fillets; every outer bed edge has 0.3 mm 45-degree relief.
3. Mayor-approved 0.80 mm retention-waist and exact vendor lead-in taper
   exceptions ONLY (polyline points 3->4 and mirror); raw audit retained,
   remainder >=0.9 mm. See tests/opengrid_tile_audit.py and endpoint table.
4. 4.2 mm convex XY corner chamfers; reflex corners, opening rims and upper
   perimeter are functional lattice/mating datums. Vendor cutters untouched.
5. Backing follows only kept cells; preset volumes recorded by endpoint tests.
6. Backing and cell walls fuse over the complete wall footprint. No cantilever
   body junction; in-plane adhesive shear is preferred over peeling along Z.
7. Counts/mask/backing and four connector edges tunable; pitch/profile fixed.
   Masked outlines disable ALL connectors (including on still-exterior edges).
8. PLA/PCTG; shallow adhesive backing is not rated for heavy levered loads.
9. Waist/taper inventory pinned to vendor BaseSnapSlotCutter; no exception for
   backing or other faces. Bare Lite waist includes the mandated bed relief.
   Full parity permits only outer bed-edge material removal.
10. Counts 1..11, shorter side <=8: at most 308 x 224 x 9.8 mm, either
    orientation. Derived from scripts/export.py::max_footprint's 323 x 244 mm
    H2C/multi-colour bake envelope; also fits H2S.

omit_cells uses zero-indexed x,y pairs separated by spaces or semicolons.
Examples: 2x2 / "1,1" is an L; duplicates are harmless. Backing may be 0
or 1..3 mm; the discontinuous range is validated before geometry is built.
The nonzero minimum is 1.0 mm (five layers): endpoint audits check the backing
and its bed relief without any wall exception. The smallest unexempt wall at
backing=1 was 1.000 mm across the endpoint table. 0.9 mm is rejected.
"""
from holders.registry import ModelSpec, Param, Preset, register
from opengrid_tile import tile
from opengrid_tile.tile import MAX_COUNT
from scripts.thumbnail import PlaneSpec


def build(values=None):
    return tile(**SPEC.resolve_values(values))


SPEC = register(ModelSpec(
    name='opengrid_tile', title='openGrid tile', category_id='multiboard', build=build,
    description='Full or Lite openGrid tiles, optional solid adhesive backing and omitted-cell shapes. Print back down.',
    print_orientation=(0, 0, 1),
    review_sections=(PlaneSpec((0, 0, 0), (1, 0, 0), 'snap profile and backing'),),
    params=(
        Param('x_count', 'integer', 1, min=1, max=MAX_COUNT, step=1),
        Param('y_count', 'integer', 1, min=1, max=MAX_COUNT, step=1),
        Param('style', 'enum', 'full', choices=('full', 'lite')),
        Param('backing_mm', 'number', 0, min=0, max=3, step=0.1, unit='mm',
              description='0 = open; otherwise 1–3 mm. Adhesive presets use 1 mm.'),
        Param('omit_cells', 'string', '', max_length=256, charset='printable-ascii',
              description='Zero-indexed x,y pairs separated by spaces or semicolons; 1,1 on 2×2 makes an L. Disables connectors.'),
        *(Param('connector_'+edge, 'boolean', True, group='Connectors')
          for edge in ('neg_x', 'pos_x', 'neg_y', 'pos_y')),
    ),
    presets=(
        Preset('full', 'Full 1 × 1', {}),
        Preset('lite', 'Lite 1 × 1', {'style': 'lite'}),
        Preset('lite-backed-1x6', 'Lite adhesive 1 × 6',
               {'style': 'lite', 'y_count': 6, 'backing_mm': 1}),
        Preset('lite-backed-l-2x2', 'Lite adhesive L 2 × 2',
               {'style': 'lite', 'x_count': 2, 'y_count': 2, 'omit_cells': '1,1', 'backing_mm': 1}),
    ),
))
