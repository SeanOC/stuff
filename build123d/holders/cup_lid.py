"""Cup-lid cradle for Multibuild, reconstructed from Sean's reference print.

Coordinates: X runs between the locating pins, +Y points away from the
board, Z is vertical in use. Intended print pose: -X end on the bed (+X
up), as in reference photo 04. Horizontal pins use a rounded upper half
and two 45-degree lower flats; a flat TOP alone does not fix an unsupported
circular underside. The fixed-point clearance hole has a 45-degree roof.

The worst load is a lid pulled forward (+Y), bending the lips and plate;
normal lid weight (-Z) runs along the print layers. PLA/PCTG, H2S.

Dimension evidence:
* https://docs.multibuild.io/beginner-section/core-parts-documentation
  specifies the 25 mm Multi Unit and small-thread holes.
* https://github.com/asciipip/multiboard-parametric-stacked/blob/master/multiboard_base.scad
  lines 51-56 and 87-95 measure the official tile remix STEP
  (https://than.gs/m/994681): board depth 6.4, small-hole throat diameter
  6.0, mouth diameter 7.5, thread major diameter 7.0 mm.
  Pins use 0.2 mm loose clearance PER SIDE: 6.0 - 0.4 = 5.6 mm;
  projection is 6.4 - 0.5 = 5.9 mm, with a 0.5 mm lead-in.

The center opening is provisionally a 7.2 mm small-thread bolt clearance,
NOT a verified Fix Point receiver. The official Fix Point is a slide-on
connector (https://thangs.com/m/1123334); its head/shank dimensions and
required seating profile remain to be verified. Do not claim Fix Point
compatibility or support-free printing until the complete audit is green.
"""
from __future__ import annotations

import math

from build123d import (
    Align, Box, BuildLine, BuildSketch, CenterArc, Cylinder, Line,
    Plane, Polygon, Pos, Rot, extrude, make_face,
)

from holders.registry import ModelSpec, Param, Preset, register

PITCH = 25.0
CLEARANCE = 0.3
WALL = 2.4
SMALL_HOLE_DIAMETER = 6.0
BOARD_DEPTH = 6.4
PIN_DIAMETER = SMALL_HOLE_DIAMETER - 0.4
PIN_LENGTH = BOARD_DEPTH - 0.5

PARAMS = (
    Param('lid_diameter', 'number', 85.3, min=60, max=130, step=0.1, unit='mm', label='Lid diameter'),
    Param('shoulder_height', 'number', 13.0, min=6, max=25, step=0.1, unit='mm', label='Shoulder height'),
    Param('shoulder_depth', 'number', 4.5, min=2, max=10, step=0.1, unit='mm', label='Shoulder radial depth'),
    Param('plate_height', 'number', 28.0, min=20, max=45, step=1, unit='mm', label='Plate height'),
    Param('plate_thickness', 'number', 6.0, min=4, max=10, step=0.1, unit='mm', label='Plate center thickness'),
    Param('end_lip_height', 'number', 6.0, min=3, max=12, step=0.1, unit='mm', label='Lip contact band height'),
    Param('pin_diameter', 'number', PIN_DIAMETER, min=4.8, max=5.8, step=0.1, unit='mm', label='Locating pin diameter'),
    Param('pin_length', 'number', PIN_LENGTH, min=2, max=PIN_LENGTH, step=0.1, unit='mm', label='Locating pin length'),
    # Even multiples only: each pin, not just the pair, must be on the
    # 25 mm lattice relative to the center hole. 25/75 mm spacing is wrong.
    Param('pin_spacing', 'enum', '50', choices=('50', '100'), unit='mm', label='Pin spacing'),
    Param('fixed_point_hole_diameter', 'number', 7.2, min=7.2, max=9, step=0.1, unit='mm', label='Center clearance diameter'),
    Param('bed_chamfer', 'number', 0.4, min=0.3, max=0.5, step=0.1, unit='mm', label='Bed edge chamfer'),
)


def dimensions(values: dict) -> dict:
    """Derived envelope, shoulder clearance, and exact engagement locations."""
    p = {q.name: q.default for q in PARAMS}
    unknown = values.keys() - p.keys()
    if unknown:
        raise ValueError(f'unknown parameters: {sorted(unknown)}')
    p.update(values)
    for q in PARAMS:
        v = p[q.name]
        if q.kind == 'enum':
            if v not in q.choices:
                raise ValueError(f'{q.name} must be one of {q.choices}')
        elif isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not q.min <= v <= q.max:
            raise ValueError(f'{q.name} must be in [{q.min}, {q.max}]')
    r = p['lid_diameter'] / 2 + CLEARANCE
    w = 2 * (r + WALL)
    spacing = float(p['pin_spacing'])
    if spacing + p['pin_diameter'] + 2 * WALL > w:
        raise ValueError('pin_spacing does not fit within this lid cradle')
    p.update(radius=r, width=w, spacing=spacing,
             engagement=p['shoulder_depth'] - CLEARANCE,
             contact_band=min(p['end_lip_height'], p['shoulder_height']))
    return p


def pin_centers(values: dict) -> tuple[tuple[float, float, float], ...]:
    p = dimensions(values)
    return ((-p['spacing']/2, 0.0, 0.0), (p['spacing']/2, 0.0, 0.0))


def _pin(diameter: float, length: float):
    """Upper semicircle + inscribed 45-degree lower V, axis -Y.

    The lower flats stay INSIDE the fit circle, unlike an outward teardrop.
    Their initial ridge is a short cantilever, which needs physical validation.
    """
    r = diameter / 2
    # Local sketch x -> model Z, sketch y -> model X (print up).
    plane = Plane(origin=(0, 0, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0))
    with BuildSketch(plane) as profile:
        with BuildLine():
            CenterArc((0, 0), r, 0, 180)
            Line((-r, 0), (0, -r))
            Line((0, -r), (r, 0))
        make_face()
    pin = extrude(profile.sketch, amount=length, dir=(0, -1, 0))
    tip = [e for e in pin.edges() if abs(e.center().Y + length) < 1e-6]
    return pin.chamfer(0.5, None, tip)


def _center_hole(diameter: float, depth: float):
    """Circular clearance with a tangent 45-degree roof, roof toward +X."""
    r = diameter / 2
    cylinder = Rot(90, 0, 0) * Cylinder(r, depth, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    plane = Plane(origin=(0, 0, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0))
    with BuildSketch(plane) as roof:
        Polygon((-r/math.sqrt(2), r/math.sqrt(2)),
                (0, r*math.sqrt(2)),
                (r/math.sqrt(2), r/math.sqrt(2)), align=None)
    return cylinder.fuse(extrude(roof.sketch, amount=depth/2, both=True))


def holder(**values):
    p = dimensions(values)
    r, w, h, t = p['radius'], p['width'], p['plate_height'], p['plate_thickness']
    # A shallow cylindrical concavity across the plate's short dimension;
    # its generator is parallel to X, so the front is vertical in print.
    sag = r - math.sqrt(r*r - (h/2)**2)
    plate = Box(w, t+sag, h, align=(Align.CENTER, Align.MIN, Align.CENTER))
    bore = Pos(0, t+r, 0) * Rot(0, 90, 0) * Cylinder(r, w+2)
    plate = (plate - bore).clean()
    bed_edges = [e for e in plate.edges()
                 if all(abs(v.X + w/2) < 1e-6 for v in e.vertices())]
    plate = plate.chamfer(p['bed_chamfer'], None, bed_edges)

    # End channels follow the lid's circular perimeter in the wall plane.
    # Axial gap accommodates the shoulder; radial overlap hooks behind it.
    gap = p['shoulder_height'] + CLEARANCE
    front = t + sag + gap
    outer = Pos(0, (front+WALL)/2, 0) * Rot(90, 0, 0) * Cylinder(r+WALL, front+WALL)
    inner = Pos(0, (front+WALL)/2, 0) * Rot(90, 0, 0) * Cylinder(r, front+WALL+2)
    band = Box(w+2, 2*(front+WALL), p['contact_band'])
    walls = (outer-inner) & band
    lip_outer = Pos(0, front+WALL/2, 0) * Rot(90, 0, 0) * Cylinder(r+WALL, WALL)
    lip_inner = Pos(0, front+WALL/2, 0) * Rot(90, 0, 0) * Cylinder(r-p['engagement'], WALL+2)
    lips = (lip_outer-lip_inner) & band
    part = plate.fuse(walls, lips).clean()
    for x, y, z in pin_centers(values):
        part = part.fuse(Pos(x, y, z) * _pin(p['pin_diameter'], p['pin_length']))
    part = part - _center_hole(p['fixed_point_hole_diameter'], 2*(front+WALL+1))
    return part.clean()


SPEC = register(ModelSpec(
    name='holder_cup_lid', build=lambda values: holder(**values),
    title='Cup lid holder (Multibuild)', category_id='multiboard',
    description='Curved cradle for an 85.3 mm sippy-cup lid, with shoulder-retaining end channels and two locating pins. Prototype: mount and print validation pending.',
    tags=('holder', 'multiboard', 'cup-lid'), params=PARAMS,
    presets=(Preset(id='sippy_cup_85mm', label='Sippy cup (85.3 mm)', values={}),),
    print_orientation=(1.0, 0.0, 0.0),
))
