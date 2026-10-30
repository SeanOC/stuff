"""Bench projector mount, step 2 (pst-czxuk.4), flat top pst-czxuk.5 / solid pst-czxuk.6.

A saddle over the cast faux-wood bench top (310 mm across, slab 38 mm
thick; docs/bench-projector-mount.md) that carries an XGIMI Elfin Flip 4K
(1.55 kg) on a 1/4"-20 heat-set insert. The front cheek is the lip clip's C
(bench_lip_clip.lip_clip_profile, the fit Sean printed at height_clearance
+0.2): its hook under the lip is the only locator. The rear cheek is the
width saddle's plain cheek with width_clearance of play, a stop against
rotation, never a locator (the slab's width is uneven).

Model frame = print frame: the profile is the footprint in XY, extruded +Z
by length, so the body is a prism and prints on its side. X runs across the
bench from the spine's outer face (x=0, front) to the rear cheek's outer
face; +Y is up IN USE: the hook bottom at y=0, the slab top at y=slab_top,
the plate (plate thick) on it, two ribs and the boss on the plate. Z runs
along the bench. The boss's axis is +Y, so it prints as a horizontal column:
its section is a teardrop whose 45 degree flanks and TIP_FLAT face -Z, the
insert hole a teardrop whose flat roof faces +Z; nothing faces down steeper
than 45 degrees and no bridge is wider than the hole's roof.

Worst load: the projector's weight (15.2 N) plus a 0.5 g lateral bump at its
centre of mass ~130 mm above the socket, i.e. >= 1 N*m bending the boss at
its root. Along X that stress runs in the layers; along Z the boss root's
bending stress is still in-plane (Y) and only its shear crosses the layers.
The plate rests on the slab, so the weight goes straight into the bench;
the hook under the lip holds the front down against the bump's uplift.
Checking material PCTG (outdoors, sun). Edges: the lip C and the rear cheek
keep the coupons' treatment (root fillets, lead-ins, R 1 outer corners);
rib roots R 1, rib tops R 1, top edges R 1 fillet, bed edges a 45 degree
chamfer; the boss gets 45 degree chamfers (a fillet there would face down
in print) at its root, its top and the insert's mouth. Functional
(sharp-by-spec) faces: the lip C's bearing faces, the plate underside, the
rear cheek's inner face and the insert bore and floor.

top=flat (pst-czxuk.5, solid since pst-czxuk.6) replaces the ribs and boss
with one solid slab the projector's feet stand on: the plate thickened over
its whole footprint, cheek to cheek across the bench and the full length,
up to the deck top. Sean 2026-10-30: no box deck and no bridging; the
slicer's sparse infill is the material saving. A round recess for the
male-to-male adapter's body (flat floor, the insert flush with it) sits over
the insert hole. The deck top is derived: recess_depth + pocket + HOLE_FLOOR
above the slab, pocket = max(insert_length, adapter_thread) + 1 (the
adapter's lower thread runs on through the insert). Set recess_depth = body
height + upper thread - what the projector's socket swallows - foot height
(4 + 8 - ~6 - 0 = 6). Both bores print with flat roofs facing +Z, cut at the
circle's top (recess_d <= 24 keeps that roof <= 9.94 mm); nothing else
bridges. The slab's long top edges get the plate's R 1; the recess floor is
sharp by function (the adapter's body seats on it).
"""
from __future__ import annotations

import math

from build123d import Axis, BuildSketch, Circle, Plane, Polygon, Pos, Rectangle, Sketch, chamfer, extrude, fillet

from holders import bench_lip_clip
from holders.bench_lip_clip import OUTER_RADIUS, TOP_RADIUS, lip_clip_profile
from holders.printer import BED_X, BED_Y, BED_Z
from holders.registry import ModelSpec, Param, Preset, register
from scripts.thumbnail import PlaneSpec

LIP_PARAMS = ('slab_thickness', 'height_clearance', 'hook_depth', 'wall', 'edge_gap', 'lead_in',
              'jaw_root_radius')
INSERT_WALL = 2.5      # boss wall around the insert hole (spec)
HOLE_FLOOR = 2.0       # solid under the insert hole, above the slab
RIB_ROOT_RADIUS = 1.0  # rib-to-plate inside fillet, design-guidelines §4
RIB_GAP = 3.0          # clear floor between a rib and the boss
TIP_FLAT = 2.0         # the boss teardrop's flat tip (a 2 mm bridge)
BOSS_CHAMFER = 1.0     # boss root blend and top edge, 45 degrees
MOUTH_CHAMFER = 0.8    # insert hole mouth lead-in
END_MARGIN = 3.0       # boss (with its root chamfer) to either end of the prism

_lip = {q.name: q for q in bench_lip_clip.PARAMS}


def _lip_param(name, default, **overrides):
    q = _lip[name]
    return Param(name, q.kind, default, min=q.min, max=q.max, step=q.step, unit=q.unit,
                 group=q.group, label=q.label, **overrides)


PARAMS = (
    _lip_param('slab_thickness', 38.0),
    _lip_param('height_clearance', 0.2),
    _lip_param('hook_depth', 11.5),
    _lip_param('wall', 5),
    _lip_param('edge_gap', 0.5),
    _lip_param('lead_in', 1.5),
    _lip_param('jaw_root_radius', 1.0),
    Param('bench_width', 'number', 310, min=250, max=315, step=0.5, unit='mm',
          group='Bench', label='Bench top width'),
    Param('width_clearance', 'number', 4.0, min=1.0, max=6.0, step=0.1, unit='mm',
          group='Fit', label='Width clearance (rear play)'),
    Param('cheek_depth', 'number', 11.5, min=6, max=20, step=0.5, unit='mm',
          group='Bench', label='Rear cheek depth'),
    Param('cheek_wall', 'number', 4, min=3, max=6, step=0.5, unit='mm',
          group='Shape', label='Rear cheek wall'),
    Param('length', 'number', 120, min=80, max=300, step=1, unit='mm',
          group='Shape', label='Length along the bench'),
    Param('plate', 'number', 6, min=5, max=10, step=0.5, unit='mm',
          group='Shape', label='Top plate thickness'),
    Param('top', 'enum', 'ribbed', choices=('ribbed', 'flat'), group='Shape', label='Top',
          description='ribbed: two ribs and the insert boss on the plate; flat: one solid slab the '
                      'projector feet rest on, the insert in a recess for the adapter'),
    Param('rib_height', 'number', 15, min=10, max=25, step=0.5, unit='mm',
          group='Shape', label='Rib and boss height', description='Ribbed top only'),
    Param('rib_wall', 'number', 4, min=3, max=8, step=0.5, unit='mm',
          group='Shape', label='Rib wall', description='Ribbed top only'),
    Param('rib_spacing', 'number', 60, min=30, max=150, step=1, unit='mm',
          group='Shape', label='Rib spacing (centres)', description='Ribbed top only'),
    Param('boss_x_offset', 'number', 0, min=-100, max=100, step=1, unit='mm',
          group='Insert', label='Boss front-to-back offset',
          description='From the slab centre line; + is toward the rear cheek'),
    Param('boss_z_offset', 'number', 0, min=-45, max=45, step=1, unit='mm',
          group='Insert', label='Boss offset along the length'),
    Param('boss_od', 'number', 14, min=13, max=24, step=0.5, unit='mm',
          group='Insert', label='Boss outer diameter', description='Ribbed top only'),
    Param('insert_hole', 'number', 8.0, min=6, max=10, step=0.1, unit='mm',
          group='Insert', label='Insert hole (nominal)'),
    Param('hole_compensation', 'number', 0.2, min=0, max=0.5, step=0.05, unit='mm',
          group='Insert', label='Hole compensation (FDM shrink)'),
    Param('insert_length', 'number', 12.7, min=6, max=20, step=0.1, unit='mm',
          group='Insert', label='Insert length'),
    Param('adapter_thread', 'number', 8, min=6, max=25, step=0.5, unit='mm',
          group='Insert', label='Adapter thread length',
          description='Flat top only; the lower thread runs on through the insert into a free bore'),
    Param('recess_d', 'number', 18, min=12, max=24, step=0.5, unit='mm',
          group='Insert', label='Adapter recess diameter',
          description='Flat top only; the adapter body (16) + 1 mm radial'),
    Param('recess_depth', 'number', 6, min=1, max=30, step=0.5, unit='mm',
          group='Insert', label='Adapter recess depth',
          description='Flat top only; body height + upper thread - what the projector socket '
                      'swallows - foot height (4 + 8 - 6 - 0)'),
    Param('bed_chamfer', 'number', 0.4, min=0.3, max=0.5, step=0.1, unit='mm',
          group='Shape', label='Bed chamfer'),
)


def dimensions(values: dict) -> dict:
    """Resolved values plus derived sizes; ValueError names the parameter.

    top=flat skips rib_*, boss_od and their guards; the deck top is derived:
    deck_top (above the slab) = recess_depth + pocket + HOLE_FLOOR, pocket =
    max(insert_length, adapter_thread) + 1. boss_r/tip_depth are the boss's
    teardrop (ribbed) or the recess circle (flat).
    """
    p = {q.name: q.default for q in PARAMS}
    unknown = values.keys() - p.keys()
    if unknown:
        raise ValueError(f'unknown parameters: {sorted(unknown)}')
    p.update(values)
    for q in PARAMS:
        v = p[q.name]
        if q.kind == 'enum':
            if v not in q.choices:
                raise ValueError(f'{q.name} must be one of {list(q.choices)}')
        elif isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not q.min <= v <= q.max:
            raise ValueError(f'{q.name} must be in [{q.min}, {q.max}]')
    flat = p['top'] == 'flat'
    # The front cheek is the lip clip's C at the same params (its guards
    # apply); its top jaw sits under the plate, so top_reach is moot.
    reach = max(_lip['top_reach'].min, p['hook_depth'])
    lip = bench_lip_clip.dimensions({**{k: p[k] for k in LIP_PARAMS}, 'top_reach': reach})
    if p['plate'] < p['wall'] - 1e-9:
        raise ValueError('plate must be >= wall (the plate covers the lip clip\'s top jaw)')
    if p['cheek_depth'] - p['lead_in'] - p['jaw_root_radius'] < 3 - 1e-9:
        raise ValueError('cheek_depth - lead_in - jaw_root_radius must be >= 3 '
                         '(flat bearing on the rear edge face)')
    if p['cheek_wall'] - p['lead_in'] < 1.6 - 1e-9:
        raise ValueError('cheek_wall - lead_in must be >= 1.6 (the cheek tip stays load-bearing)')
    if p['width_clearance'] - p['edge_gap'] < 0.5 - 1e-9:
        raise ValueError('width_clearance - edge_gap must be >= 0.5 (the rear cheek must not '
                         'register on the width)')
    w = p['wall']
    slab_top = w + lip['inner_height']
    rear = w + p['bench_width'] + p['width_clearance']
    width = rear + p['cheek_wall']
    top = slab_top + p['plate']
    hole = p['insert_hole'] + p['hole_compensation']
    if flat:
        pocket = max(p['insert_length'], p['adapter_thread']) + 1
        deck_top = p['recess_depth'] + pocket + HOLE_FLOOR
        height = slab_top + deck_top
        p.update(pocket=pocket, deck_top=deck_top, deck_height=height - top)
    else:
        height = top + p['rib_height']
    p.update(lip=lip, inner_height=lip['inner_height'], edge_x=lip['edge_x'], slab_top=slab_top,
             rear_x=rear, inner_width=rear - w, width=width, plate_top=top, height=height)
    footprint = (width, p['height'])
    if footprint[0] > BED_X or footprint[1] > BED_Y:
        raise ValueError(f'footprint {footprint[0]:g} x {footprint[1]:g} mm exceeds the '
                         f'{BED_X:g} x {BED_Y:g} mm bed; reduce bench_width, width_clearance or cheek_wall')
    if p['length'] > BED_Z:
        raise ValueError(f'length exceeds the {BED_Z:g} mm build height')
    p['footprint'] = footprint
    bx = p['edge_x'] + p['bench_width']/2 + p['boss_x_offset']
    bz = p['length']/2 + p['boss_z_offset']
    if flat:
        return _flat_dimensions(p, hole, bx, bz)
    # Insert: compensated hole, the boss wall around it, its depth.
    if p['boss_od'] < hole + 2*INSERT_WALL - 1e-9:
        raise ValueError(f'boss_od must be >= insert_hole + hole_compensation + {2*INSERT_WALL:g} '
                         f'({hole + 2*INSERT_WALL:g})')
    depth = p['insert_length'] + 1
    if p['plate'] + p['rib_height'] - depth < HOLE_FLOOR - 1e-9:
        raise ValueError(f'plate + rib_height - (insert_length + 1) must be >= {HOLE_FLOOR:g} '
                         '(the insert hole stays clear of the slab)')
    r = p['boss_od']/2
    p.update(hole_d=hole, hole_depth=depth, hole_top=p['height'], boss_x=bx, boss_z=bz, boss_r=r,
             boss_top=p['height'], tip_depth=r*math.sqrt(2) - TIP_FLAT/2)
    _end_guard(p, 'boss')
    half = p['rib_spacing']/2
    if half - p['rib_wall']/2 - r - BOSS_CHAMFER < RIB_GAP - 1e-9:
        raise ValueError(f'rib_spacing leaves under {RIB_GAP:g} mm between a rib and the boss; '
                         'increase rib_spacing')
    lo, hi = bx - half - p['rib_wall']/2, bx + half + p['rib_wall']/2
    if lo < OUTER_RADIUS + RIB_ROOT_RADIUS - 1e-9 or hi > width - OUTER_RADIUS - RIB_ROOT_RADIUS + 1e-9:
        raise ValueError('boss_x_offset or rib_spacing puts a rib off the plate')
    p['rib_x'] = (bx - half, bx + half)
    return p


def _end_guard(p, what):
    bz, r = p['boss_z'], p['boss_r']
    if bz - p['tip_depth'] - BOSS_CHAMFER < END_MARGIN - 1e-9 or \
            bz + r + BOSS_CHAMFER > p['length'] - END_MARGIN + 1e-9:
        raise ValueError(f'boss_z_offset puts the {what} within '
                         f'{END_MARGIN:g} mm of an end; reduce it or increase length')


def _flat_dimensions(p, hole, bx, bz):
    """The flat top's recess and pocket in the solid slab (pst-czxuk.5/.6)."""
    if p['recess_d'] < hole + 2*INSERT_WALL + 2 - 1e-9:
        raise ValueError(f'recess_d must be >= insert_hole + hole_compensation + {2*INSERT_WALL + 2:g} '
                         f'({hole + 2*INSERT_WALL + 2:g}; the adapter body seats on the floor around the insert)')
    r = p['recess_d']/2
    if bx - r < INSERT_WALL - 1e-9 or bx + r > p['width'] - INSERT_WALL + 1e-9:
        raise ValueError(f'boss_x_offset puts the recess within {INSERT_WALL:g} mm of a side of the slab')
    p.update(hole_d=hole, hole_depth=p['pocket'], hole_top=p['height'] - p['recess_depth'],
             recess_floor=p['height'] - p['recess_depth'], boss_x=bx, boss_z=bz, boss_r=r, tip_depth=r)
    _end_guard(p, 'recess')
    return p


def _at(s, *corners):
    return [v for v in s.vertices() for x, y in corners if abs(v.X - x) < 1e-6 and abs(v.Y - y) < 1e-6]


def plate_profile(p: dict) -> Sketch:
    """Plate + rear cheek + ribs, or the flat top's solid slab (XY), in-plane edge treatment included.

    The plate starts at x=0 so it covers the lip C's top jaw and spine top.
    The flat top is the plate grown to the deck top over its whole width.
    """
    W, ys, xr, cd = p['width'], p['slab_top'], p['rear_x'], p['cheek_depth']
    flat = p['top'] == 'flat'
    yt, yr = (p['height'] if flat else p['plate_top']), p['height']
    pts = [(0, ys), (xr, ys), (xr, ys - cd), (W, ys - cd), (W, yt)]
    t = p['rib_wall']/2
    ribs = [] if flat else sorted(p['rib_x'], reverse=True)
    for x in ribs:
        pts += [(x + t, yt), (x + t, yr), (x - t, yr), (x - t, yt)]
    pts.append((0, yt))
    with BuildSketch() as s:
        Polygon(*pts, align=None)
        fillet(_at(s, (xr, ys)), p['jaw_root_radius'])
        if ribs:
            fillet(_at(s, *[(x + d, yt) for x in ribs for d in (t, -t)]), RIB_ROOT_RADIUS)
        if p['lead_in'] > 0:
            chamfer(_at(s, (xr, ys - cd)), p['lead_in'])
        fillet(_at(s, (W, ys - cd), (W, yt), (0, yt), *[(x + d, yr) for x in ribs for d in (t, -t)]),
               OUTER_RADIUS)
    return s.sketch


def mount_profile(p: dict) -> Sketch:
    """The whole XY footprint: the lip C fused with the plate profile."""
    return lip_clip_profile(p['lip']) + plate_profile(p)


def _teardrop(r: float, flat: float) -> Sketch:
    """A radius-r circle with 45 degree flanks toward local -Y, cut flat `flat` wide."""
    t = r/math.sqrt(2)
    tip = r*math.sqrt(2)
    flanks = Polygon((-t, -t), (0, -tip), (t, -t), align=None)
    keep = Pos(0, (r - (tip - flat/2))/2) * Rectangle(2*r, r + tip - flat/2)
    return (Circle(r) + flanks) & keep


def boss_section(p: dict) -> Sketch:
    """The ribbed top's boss section on the plate top: local x = X, local y = Z, tip toward -Z."""
    plane = Plane(origin=(p['boss_x'], p['plate_top'], p['boss_z']), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
    return plane * _teardrop(p['boss_r'], TIP_FLAT)


def _bore_section(p: dict, r: float, y: float) -> Sketch:
    """A bore's mouth in the plane y: a teardrop whose flat roof faces +Z.

    Cut flat at the circle's top (signs.pin_profile), so the bore stays
    exactly 2r across and tall and the roof is a 2r(sqrt 2 - 1) bridge.
    """
    plane = Plane(origin=(p['boss_x'], y, p['boss_z']), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    # Plane's local y is -Z here, so the teardrop's -y tip points +Z.
    return plane * _teardrop(r, 2*r*(math.sqrt(2) - 1))


def hole_section(p: dict) -> Sketch:
    """The insert hole at its mouth (the boss top, or the recess floor)."""
    return _bore_section(p, p['hole_d']/2, p['hole_top'])


def recess_section(p: dict) -> Sketch:
    """The flat top's adapter recess on the slab top."""
    return _bore_section(p, p['recess_d']/2, p['height'])


def _edges_in(part, y, x0, x1, z0, z1):
    """Edges lying in the plane y whose bounding boxes sit inside [x0, x1] x [z0, z1]."""
    e = 1e-3
    return [d for d in part.edges() for bb in [d.bounding_box()]
            if abs(bb.min.Y - y) < 1e-6 and abs(bb.max.Y - y) < 1e-6
            and bb.min.X > x0 - e and bb.max.X < x1 + e and bb.min.Z > z0 - e and bb.max.Z < z1 + e]


def boss(p: dict):
    """The ribbed top's insert boss, its top edge chamfered."""
    b = extrude(boss_section(p), p['boss_top'] - p['plate_top'], dir=(0, 1, 0))
    return b.chamfer(BOSS_CHAMFER, None, b.edges().filter_by(lambda d: abs(d.center().Y - p['height']) < 1e-6))


def insert_hole(p: dict):
    return extrude(hole_section(p), -p['hole_depth'])


def _cut_bore(part, p, section, depth, r):
    """Cut a bore down from its mouth plane and chamfer the mouth."""
    y = section.faces()[0].center().Y
    part = part - extrude(section, -depth)
    bx, bz = p['boss_x'], p['boss_z']
    return part.chamfer(MOUTH_CHAMFER, None, _edges_in(part, y, bx - r, bx + r, bz - r, bz + r))


def holder(**values):
    p = dimensions(values)
    part = extrude(mount_profile(p), p['length'])
    top = part.faces().sort_by(Axis.Z)[-1]
    part = part.fillet(TOP_RADIUS, top.edges())
    bed = part.faces().sort_by(Axis.Z)[0]
    part = part.chamfer(p['bed_chamfer'], None, bed.edges())
    if p['top'] == 'flat':
        part = _cut_bore(part, p, recess_section(p), p['recess_depth'], p['recess_d']/2)
    else:
        part = part + boss(p)
        # Root blend (concave): a 45 degree chamfer, since a fillet would face down in print.
        bx, bz, r = p['boss_x'], p['boss_z'], p['boss_r']
        part = part.chamfer(BOSS_CHAMFER, None, _edges_in(part, p['plate_top'], bx - r, bx + r,
                                                          bz - p['tip_depth'], bz + r))
    return _cut_bore(part, p, hole_section(p), p['hole_depth'], p['hole_d']/2).clean()


def bridges(p: dict) -> list:
    """The flat ceilings in the print pose, as (name, z, x0, x1, y0, y1).

    boss-tip (ribbed): the teardrop's TIP_FLAT (a 2 mm bridge between its
    flanks); hole-roof and (flat) recess-roof: each bore's flat roof,
    2r(sqrt 2 - 1) wide. The flat top's solid slab has no other ceiling.
    """
    bx, bz = p['boss_x'], p['boss_z']
    out, bores = [], [('hole-roof', p['hole_d']/2, p['hole_top'] - p['hole_depth'], p['hole_top'])]
    if p['top'] == 'flat':
        bores.append(('recess-roof', p['recess_d']/2, p['recess_floor'], p['height']))
    else:
        out.append(('boss-tip', bz - p['tip_depth'], bx - TIP_FLAT/2, bx + TIP_FLAT/2, p['plate_top'], p['boss_top']))
    for n, r, y0, y1 in bores:
        roof = 2*r*(math.sqrt(2) - 1)
        out.append((n, bz + r, bx - roof/2, bx + roof/2, y0, y1))
    return out


def audit_exclusions(values: dict) -> list:
    """Thin exact boxes on the flat bridges (bridges()): each is a flat
    ceiling, which the overhang rule reads as 90 degrees, and each is far
    under the 10 mm bridge limit (the tests measure every span)."""
    p = dimensions(values)
    return [(x0 - 0.001, y0 - 0.001, z - 0.001, x1 + 0.001, y1 + 0.001, z + 0.001)
            for _, z, x0, x1, y0, y1 in bridges(p)]


SPEC = register(ModelSpec(
    name='holder_bench_projector_mount', build=lambda values: holder(**values),
    title='Bench projector mount', category_id='household',
    description=('Saddle mount that clamps over a bench top and carries a projector on a 1/4"-20 '
                 'heat-set insert. The front cheek is the lip clip\'s hook (the only locator), the '
                 'rear cheek a loose stop; a 6 mm plate with two ribs carries the insert boss, or '
                 '(flat top) one solid slab the projector stands on, the insert in a recess for the '
                 'adapter. Prints on its side, no supports.'),
    tags=('holder',), params=PARAMS,
    presets=(Preset(id='short-80', label='Short (80 mm)', values={'length': 80}),
             Preset(id='long-200', label='Long (200 mm)', values={'length': 200}),
             Preset(id='flat-250', label='Flat top (250 mm)', values={'top': 'flat', 'length': 250})),
    review_sections=(PlaneSpec((0, 0, 10), (0, 0, 1), 'profile at Z = 10, clear of the boss'),),
))
