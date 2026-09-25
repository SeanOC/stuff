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

Sean confirmed a small-thread flat-head through-bolt, not a Fix Point
receiver. The front head recess is not implemented yet: the official bolt
listing https://thangs.com/m/974190 shows an octagonal flat seat and does
not publish a conical head angle or diameter. Verify the intended bolt and
seat before adding countersink defaults. The existing center opening has
not been validated against that bolt. The end-standing digital audit passes;
physical fit and print testing remain outstanding.
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
LIP_THICKNESS = 4.0
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
    band = min(p['end_lip_height'], p['shoulder_height'])
    # Roof the upper channel across its axial gap; extend only this end
    # by half that span so both 45-degree planes clear the lid.
    left = -(r + WALL)
    sag = r - math.sqrt(r*r - (p['plate_height']/2)**2)
    front = p['plate_thickness'] + sag + p['shoulder_height'] + CLEARANCE
    right = r + WALL + (front-p['plate_thickness'])/2
    w = right - left
    spacing = float(p['pin_spacing'])
    if spacing + p['pin_diameter'] + 2 * WALL > 2*(r + WALL):
        raise ValueError('pin_spacing does not fit within this lid cradle')
    p.update(radius=r, width=w, left=left, right=right, spacing=spacing,
             engagement=p['shoulder_depth'] - CLEARANCE,
             contact_band=band)
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
    plate = Pos((p['left']+p['right'])/2, 0, 0) * Box(
        w, t+sag, h, align=(Align.CENTER, Align.MIN, Align.CENTER))
    bore = Pos(0, t+r, 0) * Rot(0, 90, 0) * Cylinder(r, 2*w)
    plate = (plate - bore).clean()
    # The lower end is a flat bed face. Its circular INSIDE faces point
    # upward in the print pose; only the old curved outside needed replacing.
    gap = p['shoulder_height'] + CLEARANCE
    front = t + sag + gap
    band = p['contact_band']
    lower_blank = Box(r+WALL, front+WALL, band,
                      align=(Align.MAX, Align.MIN, Align.CENTER))
    inner = Pos(0, (front+WALL)/2, 0) * Rot(90, 0, 0) * Cylinder(r, front+WALL+2)
    lower_wall = lower_blank - inner
    lower_lip_blank = Pos(0, front, 0) * Box(
        r+WALL, WALL, band, align=(Align.MAX, Align.MIN, Align.CENTER))
    lip_inner = Pos(0, front+WALL/2, 0) * Rot(90, 0, 0) * Cylinder(
        r-p['engagement'], WALL+2)
    lower_lip = lower_lip_blank - lip_inner

    # Roof the upper channel across its AXIAL gap. Both 45-degree slopes
    # remain outside radius r, preserving all shoulder clearance; the roof
    # apex extends only this end. Extruding across the full contact band
    # avoids the thin side wedges of a roof across Z.
    with BuildSketch(Plane.XY.offset(-band/2)) as upper_profile:
        Polygon((r, 0), (r, t), (r+(front-t)/2, (front+t)/2),
                (r, front), (p['right'], front), (p['right'], 0), align=None)
    upper_wall = extrude(upper_profile.sketch, amount=band)

    # The 45-degree retaining wedge is 4 mm deep so its diagonal section
    # remains substantial. Engagement is maximal at the shoulder-facing
    # edge and tapers toward the exposed front. No downward circular face.
    lip_tip = r-p['engagement']
    with BuildSketch(Plane.XY.offset(-band/2)) as upper_lip_profile:
        Polygon((lip_tip, front), (lip_tip+LIP_THICKNESS, front+LIP_THICKNESS),
                (p['right'], front+LIP_THICKNESS), (p['right'], front), align=None)
    upper_lip = extrude(upper_lip_profile.sketch, amount=band)
    part = plate.fuse(lower_wall, lower_lip, upper_wall, upper_lip).clean()
    # Treat the entire fused bed-contact perimeter, including the lower lip.
    bed_edges = [e for e in part.edges()
                 if all(abs(v.X-p['left']) < 1e-6 for v in e.vertices())]
    part = part.chamfer(p['bed_chamfer'], None, bed_edges)
    for x, y, z in pin_centers(values):
        part = part.fuse(Pos(x, y, z) * _pin(p['pin_diameter'], p['pin_length']))
    part = part - _center_hole(p['fixed_point_hole_diameter'], 2*(front+LIP_THICKNESS+1))
    return part.clean()


SPEC = register(ModelSpec(
    name='holder_cup_lid', build=lambda values: holder(**values),
    title='Cup lid holder (Multibuild)', category_id='multiboard',
    description='Curved cradle for an 85.3 mm sippy-cup lid, with shoulder-retaining end channels and two locating pins. Prototype: bolt seat and physical fit validation pending.',
    tags=('holder', 'multiboard', 'cup-lid'), params=PARAMS,
    presets=(Preset(id='sippy_cup_85mm', label='Sippy cup (85.3 mm)', values={}),),
    print_orientation=(1.0, 0.0, 0.0),
))
