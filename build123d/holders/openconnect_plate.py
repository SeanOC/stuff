"""openConnect plate — mitufy's CC BY 4.0 generator, in the standing frame.

Print standing (+Z up), back/mount face Y=0, PLA/PCTG. Worst-case load is
an accessory pulling the plate away from the wall; keep >=2.4 mm backing.
The negative preset is a CAD subtraction tool, not a standalone print.
[C] assets/openConnect/openconnect_plate.scad:64-100, upstream 04e2277a71c5.
Reference mode preserves the author's four footprint corners. In shipped
mode lower corners are chamfered, never filleted (pst-zn36d rev 5).
"""
from dataclasses import replace
from math import floor, isfinite

from build123d import Align, Axis, Box, Compound, Solid, Vector, chamfer, fillet
from holders.registry import ModelSpec, Param, Preset, register
from openconnect.constants import EPS, TILE_SIZE
from openconnect.grid import LOCKS, POSITIONS, SLIDES, fixtures, layout
from openconnect.slot import pocket_depth

MOUNT = 'openconnect-slot'
BED_CHAMFER = 0.4
PRINT_ORIENTATION = (0., 0., 1.)


def dimensions(values):
    v = SPEC.resolve_values(values)
    if any(isinstance(n, (int, float)) and not isfinite(n) for n in v.values()):
        raise ValueError('plate dimensions must be finite')
    scale = TILE_SIZE if v['size_unit'] == 'grid' else 1
    w, h = v['horizontal_size']*scale, v['vertical_size']*scale
    if not (28 <= w <= 280 and 28 <= h <= 280):
        raise ValueError('plate width and height must be 28..280 mm (1..10 grids)')
    if v['size_unit'] == 'grid' and any(v[k] != int(v[k]) for k in ('horizontal_size', 'vertical_size')):
        raise ValueError('grid sizes must be whole tile counts')
    nh, nv = floor(w/TILE_SIZE), floor(h/TILE_SIZE)
    dx = {'left': -1, 'center': 0, 'right': 1}[v['horizontal_alignment']]*(w-nh*TILE_SIZE)/2
    dz = {'bottom': -1, 'center': 0, 'top': 1}[v['vertical_alignment']]*(h-nv*TILE_SIZE)/2
    dx += v['horizontal_offset']
    dz += v['vertical_offset']
    # Keep complete tiles within the plate: clipped slots cannot retain a head.
    if abs(dx) > (w-nh*TILE_SIZE)/2+1e-7 or abs(dz) > (h-nv*TILE_SIZE)/2+1e-7:
        raise ValueError('slot offsets/alignment must keep the full grid inside the plate')
    return v, w, h, nh, nv, dx, dz


def placements(values):
    v, w, h, nh, nv, dx, dz = dimensions(values)
    return [replace(p, x=p.x+dx, z=p.z+h/2+dz) for p in layout(
        nh, nv, position=v['position'], lock=v['lock'], slide=v['slide'],
        entryramp_flip=v['entryramp_flip'])]


def _fixtures(values):
    v = SPEC.resolve_values(values)
    return fixtures(placements(v), clearance=(v['side_clearance'], v['depth_clearance']),
                    edge_feature=v['edge_feature'],
                    excess_thickness=0 if v['slot_type'] == 'negslot' else EPS)


def mount_for_values(values):
    return MOUNT if values['slot_type'] == 'slot' else None


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    return _fixtures(values) if mount_for_values(SPEC.resolve_values(values)) else None


def plate_body(values, *, bed_chamfer=True):
    v, w, h, *_ = dimensions(values)
    thickness = pocket_depth((v['side_clearance'], v['depth_clearance'])) + v['extra_thickness']
    part = Box(w, thickness, h, align=(Align.CENTER, Align.MIN, Align.MIN))
    radius, style = v['corner_rounding_size'], v['corner_rounding']
    if style != 'none' and radius:
        edges = part.edges().filter_by(Axis.Y)
        if style == 'fillet' and not bed_chamfer:
            part = fillet(edges, radius)
        elif style == 'fillet':
            part = fillet([e for e in edges if e.center().Z > h/2], radius)
            part = chamfer([e for e in part.edges().filter_by(Axis.Y)
                            if e.center().Z < h/2], radius)
        else:
            part = chamfer(edges, radius)
    if bed_chamfer:
        # Ease the exposed slab edges before cutting; leave library profiles intact.
        edges = list(part.edges()) if style == 'none' or not radius else [
            e for e in part.edges() if e not in part.edges().filter_by(Axis.Y)]
        part = chamfer(edges, BED_CHAMFER)
    return part


def build(values=None, *, reference=False):
    v = SPEC.resolve_values(values)
    fx = _fixtures(v)
    if v['slot_type'] == 'negslot':
        return Compound(children=fx.cutters)
    if not reference and v['extra_thickness'] >= 2.4:
        # The approved thin border is at the author's exact grid edge only.
        # A moved border needs 0.9 mm of wall plus the outer edge relief.
        _, w, h, *_ = dimensions(v)
        for p, cutter in zip(placements(v), fx.cutters):
            bb = cutter.bounding_box()
            grid_gap, wall = {
                'up': (p.z-TILE_SIZE/2, bb.min.Z),
                'down': (h-p.z-TILE_SIZE/2, h-bb.max.Z),
                'left': (w/2-p.x-TILE_SIZE/2, w/2-bb.max.X),
                'right': (w/2+p.x-TILE_SIZE/2, w/2+bb.min.X),
            }[v['slide']]
            if grid_gap > 1e-7 and wall < 0.9+BED_CHAMFER-1e-7:
                raise ValueError('offset on-ramp border must be at least 1.3 mm including edge relief; '
                                 'align to the grid edge or increase the margin')
    part = plate_body(v, bed_chamfer=not reference)
    for cutter in fx.cutters:
        part -= cutter
    return part


def border_exclusions(values):
    """Exact bands under edge-facing ramps only (approved rev 4 exception).

    Extrude the actual ramp-end face out to its tile edge, then require that
    edge to coincide with the plate edge. This preserves the ramp's depth-
    dependent X shift, instead of exempting an oversized axis-aligned box.
    No margin is added; slots away from the plate border yield no exclusion.
    """
    v, w, h, *_ = dimensions(values)
    if v['slot_type'] != 'slot':
        return []
    fx = _fixtures(v)
    axis = Vector(*SLIDES[v['slide']])
    out = -axis
    result = []
    for p, cutter in zip(placements(v), fx.cutters):
        edge = Vector(p.x, 0, p.z) + out*TILE_SIZE/2
        at_border = (abs(edge.Z) < 1e-6 if out.Z < 0 else
                     abs(edge.Z-h) < 1e-6 if out.Z > 0 else
                     abs(edge.X+w/2) < 1e-6 if out.X < 0 else abs(edge.X-w/2) < 1e-6)
        if not at_border:
            continue
        # The extreme planar face is the on-ramp's closed tile-end boundary.
        end = max(cutter.faces(), key=lambda f: f.center().dot(out))
        distance = (edge-end.center()).dot(out)
        if distance > 1e-7:
            strip = Solid.extrude(end, out*distance)
            # EPS outside the mouth is a cutting aid, not plate material.
            strip &= Box(w, pocket_depth((v['side_clearance'], v['depth_clearance'])), h,
                         align=(Align.CENTER, Align.MIN, Align.MIN))
            result.append(strip)
    return result


SPEC = register(ModelSpec(
    name='openconnect_plate', title='openConnect plate', category_id='multiboard',
    description=('openConnect by mitufy (CC BY 4.0): a 28 mm grid of locking slots. '
                 'Print standing with 2.4 mm or more backing; negative slots are CAD tools.'),
    build=build, mounts=(MOUNT,), mount_for_values=mount_for_values,
    print_orientation=PRINT_ORIENTATION,
    params=(
        Param('size_unit', 'enum', 'mm', choices=('grid', 'mm'), label='Size units'),
        Param('horizontal_size', 'number', 84, min=1, max=280, step=1, label='Width (28–280 mm / 1–10 grids)'),
        Param('vertical_size', 'number', 56, min=1, max=280, step=1, label='Height (28–280 mm / 1–10 grids)'),
        Param('extra_thickness', 'number', 2.4, min=0.5, max=6, step=0.1,
              label='Backing (mm; below 2.4 requires another model wall)'),
        Param('corner_rounding', 'enum', 'none', choices=('none', 'chamfer', 'fillet'),
              label='Upper corners (lower corners always chamfered)'),
        Param('corner_rounding_size', 'integer', 0, min=0, max=2, step=1, label='Corner size (mm; up to 2 preserves slot backing)'),
        Param('slot_type', 'enum', 'slot', choices=('slot', 'negslot'), label='Slot / negative CAD tool'),
        Param('lock', 'enum', 'corners', choices=LOCKS, label='Lock distribution'),
        Param('position', 'enum', 'all', choices=POSITIONS, label='Slot positions'),
        Param('slide', 'enum', 'up', choices=tuple(SLIDES), label='Slide direction'),
        Param('entryramp_flip', 'boolean', False, label='Flip entry ramp'),
        Param('horizontal_alignment', 'enum', 'center', choices=('center', 'left', 'right')),
        Param('vertical_alignment', 'enum', 'center', choices=('center', 'top', 'bottom')),
        Param('horizontal_offset', 'number', 0, min=-10, max=10, step=0.1, label='Horizontal slot offset (mm)'),
        Param('vertical_offset', 'number', 0, min=-10, max=10, step=0.1, label='Vertical slot offset (mm)'),
        Param('side_clearance', 'number', 0.1, min=0, max=0.5, step=0.01),
        Param('depth_clearance', 'number', 0.1, min=0, max=0.5, step=0.01),
        Param('edge_feature', 'enum', 'both', choices=('both', 'top', 'side', 'none')),
    ),
    presets=(Preset('default', '84 × 56 mm, corner locks', {}),
             Preset('one-tile', 'One tile', {'horizontal_size': 28, 'vertical_size': 28}),
             Preset('negslot', 'Negative slots (CAD tool)', {'slot_type': 'negslot'})),
))
